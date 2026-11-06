from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/honda-readonly-preflight"))
import root_identity_stage_a as stage
from privileged import validate_su_fingerprint


class FakeTransport:
    serial = "192.0.2.10:5555"

    def __init__(self, *, bad=None, root=None):
        self.bad = bad
        self.root = root or stage.Result(0, b"uid=0(root) gid=0(root) groups=0(root)\n", b"")
        self.root_calls = 0
        self.observed = []
        self.disconnected = False

    def observe(self, operation, argument="", *, timeout=5, max_bytes=stage.MAX_OUTPUT):
        self.observed.append((operation, argument))
        if self.bad == "offline":
            return stage.Result(1, b"", b"device offline")
        if self.bad == "wrong-target" and operation == "property" and argument == "ro.product.device":
            return stage.Result(0, b"other-device\n", b"")
        if self.bad == "wrong-model" and operation == "property" and argument == "ro.product.model":
            return stage.Result(0, b"other-model\n", b"")
        if self.bad == "unknown-mount" and operation == "mounts":
            return stage.Result(0, b"", b"")
        if self.bad == "rw-mount" and operation == "mounts":
            return stage.Result(0, b"/dev/block/system /system ext4 rw,seclabel 0 0\n", b"")
        if self.bad == "binary-mismatch" and operation == "su-hash":
            return stage.Result(0, b"0" * 64 + b"  /system/xbin/su\n", b"")
        if operation == "state":
            return stage.Result(0, b"device\n", b"")
        if operation == "property":
            return stage.Result(0, stage.TARGET_PROPERTIES[argument].encode() + b"\n", b"")
        if operation == "mounts":
            return stage.Result(0, b"/dev/block/system /system ext4 ro,seclabel 0 0\n", b"")
        if operation == "su-hash":
            return stage.Result(0, stage.EXPECTED_SU_SHA256.encode() + b"  /system/xbin/su\n", b"")
        if operation == "su-list":
            mode = "-rwsrwsrwx" if self.bad != "bad-mode" else "-rwsr-xr-x"
            return stage.Result(0, f"{mode} root root 75348 2014-01-01 00:00 /system/xbin/su\n".encode(), b"")
        raise AssertionError((operation, argument))

    def root_identity_once(self):
        self.root_calls += 1
        if self.root_calls > 1:
            raise AssertionError("root called more than once")
        return self.root

    def disconnect(self):
        self.disconnected = True


class StageATests(unittest.TestCase):
    def run_session(self, transport, answers, *, expected="PASS"):
        with tempfile.TemporaryDirectory() as tmp:
            output = []
            controller = stage.StageA(transport, input_fn=lambda _: next(answers),
                                      output_fn=output.append, evidence_root=Path(tmp))
            actual = controller.run()
            self.assertEqual(actual, expected)
            if actual != "CANCELLED":
                self.assertIsNotNone(controller.output_dir)
                self.assertTrue((controller.output_dir / "manifest.json").is_file())
                self.assertEqual((controller.output_dir.stat().st_mode & 0o777), 0o700)
                self.assertEqual(((controller.output_dir / "manifest.json").stat().st_mode & 0o777), 0o600)
                self.assertTrue((controller.output_dir / "sha256.txt").is_file())
                import json
                manifest = json.loads((controller.output_dir / "manifest.json").read_text())
            else:
                manifest = None
            return controller, output, manifest

    def test_correct_fixed_command_plan_and_no_argument_path(self):
        self.assertEqual(stage.ROOT_COMMAND, "/system/xbin/su -c id")
        class Planner:
            adb = "adb"
            serial = "192.0.2.10:5555"
            records = []
        planned = stage.PrivilegedRead(Planner()).plan(stage.PrivilegedOperation.IDENTITY)
        self.assertEqual(planned[-3:], ("/system/xbin/su", "-c", "id"))
        self.assertEqual(stage.main(["--dry-run"]), 0)

    def test_arbitrary_privileged_commands_are_rejected(self):
        class Planner:
            adb = "adb"
            serial = "192.0.2.10:5555"
            records = []
        reader = stage.PrivilegedRead(Planner())
        for operation in ("whoami", "shell", "id; reboot", "read"):
            with self.subTest(operation=operation), self.assertRaises(stage.SafetyStop):
                reader.plan(operation)

    def test_model_identity_read_is_one_literal_allowlisted_getprop(self):
        class FakeAdb:
            adb = "adb"
            serial = "192.0.2.10:5555"
            records = []
            def _run_planned(self, command, operation, args, *, timeout, max_bytes):
                self.records.append({"command": command, "result": "success"})
                return 0, b"MY16ADA\n", b""
        adapter = stage.AdbTransport()
        adapter.adb = FakeAdb()
        adapter.serial = FakeAdb.serial
        self.assertEqual(adapter.observe("property", "ro.product.model").stdout, b"MY16ADA\n")
        self.assertEqual(adapter.adb.records[0]["command"],
                         ("adb", "-s", adapter.serial, "shell", "getprop", "ro.product.model"))
        with self.assertRaises(stage.SafetyStop):
            adapter.observe("arbitrary", "id; reboot")

    def test_success_invokes_root_once_finalizes_and_disconnects_after_ack(self):
        transport = FakeTransport()
        controller, output, manifest = self.run_session(transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]))
        self.assertEqual(transport.root_calls, 1)
        self.assertEqual(controller.command_count, 1)
        self.assertTrue(transport.disconnected)
        self.assertEqual(manifest["eligibility_state"], "CONTROLLED_ROOT_IDENTITY_CANDIDATE")
        self.assertFalse(next(row for row in manifest["commands"] if row["name"] == "eligibility-decision")["generic_integrity_pass"])
        self.assertEqual([x for x in transport.observed if x[0] == "property"].__len__(), len(stage.TARGET_PROPERTIES))
        self.assertEqual([x for x in transport.observed if x[0] not in {"state", "property", "mounts", "su-hash", "su-list"}], [])
        self.assertTrue(any("ROOT TEST COMPLETE" in line and "CAR POWERED OFF" in line for line in output))

    def test_owner_cancellation_sends_no_target_commands(self):
        transport = FakeTransport()
        controller, _, _ = self.run_session(transport, iter(["no", "CAR POWERED OFF"]), expected="CANCELLED")
        self.assertEqual(transport.observed, [])
        self.assertEqual(transport.root_calls, 0)
        self.assertEqual(controller.command_count, 0)

    def test_invalid_serial_stops_before_transport_commands(self):
        transport = FakeTransport()
        self.run_session(transport, iter(["YES", "bad;id", "CAR POWERED OFF"]), expected="FAIL")
        self.assertEqual(transport.observed, [])
        self.assertEqual(transport.root_calls, 0)

    def test_wrong_target_rejects_before_root(self):
        for bad in ("wrong-target", "wrong-model"):
            with self.subTest(bad=bad):
                transport = FakeTransport(bad=bad)
                self.run_session(transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]), expected="FAIL")
                self.assertEqual(transport.root_calls, 0)

    def test_unavailable_transport_rejects_before_root(self):
        transport = FakeTransport(bad="offline")
        self.run_session(transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]), expected="FAIL")
        self.assertEqual(transport.root_calls, 0)

    def test_binary_mismatch_rejects_before_root(self):
        transport = FakeTransport(bad="binary-mismatch")
        self.run_session(transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]), expected="FAIL")
        self.assertEqual(transport.root_calls, 0)

    def test_read_write_or_unknown_mount_rejects_before_root(self):
        for bad in ("rw-mount", "unknown-mount"):
            with self.subTest(bad=bad):
                transport = FakeTransport(bad=bad)
                self.run_session(transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]), expected="FAIL")
                self.assertEqual(transport.root_calls, 0)

    def test_anomalous_06777_is_controlled_candidate_not_generic_integrity_pass(self):
        listing = b"-rwsrwsrwx root root 75348 2014-01-01 00:00 /system/xbin/su\n"
        self.assertEqual(stage.parse_su_listing(listing), (0o6777, 75348))
        with self.assertRaises(stage.SafetyStop):
            validate_su_fingerprint(
                stage.EXPECTED_SU_SHA256.encode() + b"  /system/xbin/su\n", listing)
        self.assertEqual(stage.parse_su_listing(
            b"-rwsr-xr-x root root 75348 2014-01-01 00:00 /system/xbin/su\n"), (0o4755, 75348))

    def test_uid_zero_success_is_strict(self):
        self.assertTrue(stage.root_is_uid_zero(stage.Result(0, b"uid=0(root) gid=0(root)\n", b"")))
        for result in (
            stage.Result(0, b"uid=2000(shell) gid=2000(shell)\n", b""),
            stage.Result(0, b"uid=0(root)\nextra\n", b""),
            stage.Result(0, b"nonsense uid=0(root)\n", b""),
            stage.Result(0, b"uid=0(root) gid=0(root)\n" + b"x" * stage.MAX_OUTPUT, b""),
            stage.Result(1, b"uid=0(root) gid=0(root)\n", b""),
            stage.Result(0, b"uid=0(root) gid=0(root)\n", b"", timed_out=True),
            stage.Result(0, b"uid=0(root) gid=0(root)\n", b"", output_limited=True),
        ):
            self.assertFalse(stage.root_is_uid_zero(result))

    def test_full_session_rejects_nonroot_malformed_nonzero_and_supersu_denial(self):
        cases = (
            stage.Result(0, b"uid=2000(shell) gid=2000(shell)\n", b""),
            stage.Result(0, b"not an id response\n", b""),
            stage.Result(1, b"uid=0(root) gid=0(root)\n", b"permission denied"),
            stage.Result(0, b"SuperSU authorization denied\n", b""),
        )
        for root in cases:
            with self.subTest(root=root):
                transport = FakeTransport(root=root)
                controller, _, manifest = self.run_session(
                    transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]), expected="FAIL")
                self.assertEqual(transport.root_calls, 1)
                self.assertEqual(manifest["command_count"], 1)
                self.assertEqual(manifest["root_command"], stage.ROOT_COMMAND)
                self.assertTrue(transport.disconnected)

    def test_root_timeout_is_incomplete_and_does_not_retry(self):
        transport = FakeTransport(root=stage.Result(124, b"", b"timeout", timed_out=True))
        controller, _, manifest = self.run_session(transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]), expected="INCOMPLETE")
        self.assertEqual(transport.root_calls, 1)
        self.assertFalse(manifest["timeout_remote_termination_verified"])
        self.assertTrue(transport.disconnected)

    def test_transport_timeout_and_binary_failures_have_no_retry_or_fallback(self):
        transport = FakeTransport(bad="offline")
        self.run_session(transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]), expected="FAIL")
        self.assertEqual(transport.root_calls, 0)
        self.assertEqual([name for name, _ in transport.observed].count("state"), 1)
        self.assertNotIn("reconnect", [name for name, _ in transport.observed])

    def test_transport_enforces_at_most_once_root_invocation(self):
        class FakeAdb:
            adb = "adb"
            serial = "192.0.2.10:5555"
            records = []
            def _run_planned(self, command, operation, args, *, timeout, max_bytes):
                return 0, b"uid=0(root) gid=0(root)\n", b""
        adapter = stage.AdbTransport()
        adapter.adb = FakeAdb()
        adapter.serial = FakeAdb.serial
        self.assertEqual(adapter.root_identity_once().code, 0)
        with self.assertRaises(stage.SafetyStop):
            adapter.root_identity_once()

    def test_wrong_mode_rejects_before_root(self):
        transport = FakeTransport(bad="bad-mode")
        self.run_session(transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]), expected="FAIL")
        self.assertEqual(transport.root_calls, 0)

    def test_missing_power_off_ack_does_not_disconnect(self):
        transport = FakeTransport()
        self.run_session(transport, iter(["YES", "192.0.2.10:5555", "abnormal display"]), expected="PASS")
        self.assertFalse(transport.disconnected)


if __name__ == "__main__":
    unittest.main()
