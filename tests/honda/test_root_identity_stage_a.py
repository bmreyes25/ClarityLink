from pathlib import Path
import hashlib
import json
import sys
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/honda-readonly-preflight"))
import root_identity_stage_a as stage
import privileged
from collector import FixedAdb
from privileged import EXPECTED_SU_SHA256 as ARCHIVED_SHA256, validate_su_fingerprint

TEST_BINARY = bytes(range(256)) * 294 + bytes(range(84))


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
        if self.bad == "duplicate-mount" and operation == "mounts":
            return stage.Result(0, b"/dev/a /system ext4 ro 0 0\n/dev/b /system ext4 rw 0 0\n", b"")
        if self.bad == "xbin-overlay" and operation == "mounts":
            return stage.Result(0, b"/dev/a /system ext4 ro 0 0\noverlay /system/xbin overlay rw,lowerdir=/lower,upperdir=/upper 0 0\n", b"")
        if self.bad == "truncated-mount" and operation == "mounts":
            return stage.Result(0, b"/dev/a /system ext4 ro 0 0\n", b"", output_limited=True)
        if self.bad == "binary-mismatch" and operation == "su-binary":
            return stage.Result(0, b"x" * len(TEST_BINARY), b"")
        if operation == "state":
            return stage.Result(0, b"device\n", b"")
        if operation == "property":
            return stage.Result(0, stage.TARGET_PROPERTIES[argument].encode() + b"\n", b"")
        if operation == "mounts":
            return stage.Result(0, b"/dev/block/system /system ext4 ro,seclabel 0 0\n", b"")
        if operation == "su-binary":
            return stage.Result(0, TEST_BINARY,
                                b"[100%] /system/xbin/su\n1 file pulled\n"
                                if self.bad == "pull-progress-stderr" else b"")
        if operation == "su-list":
            mode = "-rwsrwsrwx" if self.bad != "bad-mode" else "-rwsr-xr-x"
            return stage.Result(0, f"{mode} 0 0 75348 2014-01-01 00:00 su\n".encode(), b"")
        raise AssertionError((operation, argument))

    def root_identity_once(self):
        self.root_calls += 1
        if self.root_calls > 1:
            raise AssertionError("root called more than once")
        if isinstance(self.root, Exception):
            raise self.root
        return self.root

    def disconnect(self):
        self.disconnected = True


class StageATests(unittest.TestCase):
    def setUp(self):
        self.sha_patcher = mock.patch.object(
            stage, "EXPECTED_SU_SHA256", hashlib.sha256(TEST_BINARY).hexdigest())
        self.sha_patcher.start()
        self.addCleanup(self.sha_patcher.stop)
        self.generic_sha_patcher = mock.patch.object(
            privileged, "EXPECTED_SU_SHA256", hashlib.sha256(TEST_BINARY).hexdigest())
        self.generic_sha_patcher.start()
        self.addCleanup(self.generic_sha_patcher.stop)

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

    def test_model_identity_read_uses_fixed_adb_allowlist(self):
        class FakeAdb:
            adb = "adb"
            serial = "192.0.2.10:5555"
            records = []
            def plan(self, operation, args):
                if operation == "property" and args == ("ro.product.model",):
                    return ("adb", "-s", self.serial, "shell", "getprop", "ro.product.model")
                if operation == "device-state" and not args:
                    return ("adb", "-s", self.serial, "get-state")
                raise stage.SafetyStop("not allowlisted")
            def run(self, operation, *args, timeout, max_bytes):
                command = self.plan(operation, args)
                self.records.append({"command": command, "result": "success"})
                return 0, b"MY16ADA\n", b""
        adapter = stage.AdbTransport()
        adapter.adb = FakeAdb()
        adapter.serial = FakeAdb.serial
        self.assertEqual(adapter.observe("property", "ro.product.model").stdout, b"MY16ADA\n")
        self.assertEqual(adapter.adb.records[0]["command"],
                         ("adb", "-s", adapter.serial, "shell", "getprop", "ro.product.model"))
        adapter._fixed_host_plan("state")
        self.assertEqual(adapter._fixed_host_plan("state"),
                         ("adb", "-s", adapter.serial, "get-state"))
        with self.assertRaises(stage.SafetyStop):
            adapter._fixed_host_plan("arbitrary", "id; reboot")
        with self.assertRaises(stage.SafetyStop):
            adapter.observe("arbitrary", "id; reboot")

    def test_binary_fingerprint_is_a_bounded_host_read(self):
        adapter = stage.AdbTransport()
        class FakeAdb:
            adb = "adb"
            serial = "192.0.2.10:5555"
            records = []
            def _run_planned(self, command, operation, parameters, *, timeout, max_bytes):
                self.assert_command = command
                Path(command[-1]).write_bytes(TEST_BINARY)
                self.records.append({"result": "success", "truncated": False})
                return 0, b"1 file pulled", b""
        fake_adb = FakeAdb()
        adapter.adb = fake_adb
        adapter.serial = FakeAdb.serial
        result = adapter.observe("su-binary")
        self.assertEqual(result.stdout, TEST_BINARY)
        self.assertEqual(fake_adb.assert_command[0:6],
                         ("adb", "-s", FakeAdb.serial, "pull", "/system/xbin/su", fake_adb.assert_command[-1]))
        self.assertLessEqual(len(result.stdout), stage.EXPECTED_SU_SIZE)
        transport = FakeTransport()
        _controller, _output, manifest = self.run_session(
            transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]))
        row = next(row for row in manifest["commands"] if row["name"] == "su-host-fingerprint")
        self.assertEqual(row["sha256"], hashlib.sha256(TEST_BINARY).hexdigest())
        self.assertNotIn(TEST_BINARY[:50].decode("latin1"), json.dumps(manifest))

    def test_adb_pull_progress_on_stderr_does_not_reject_a_valid_binary(self):
        transport = FakeTransport(bad="pull-progress-stderr")
        _controller, _output, manifest = self.run_session(
            transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]))
        row = next(row for row in manifest["commands"] if row["name"] == "su-host-fingerprint")
        self.assertEqual(row["sha256"], hashlib.sha256(TEST_BINARY).hexdigest())

    def test_success_invokes_root_once_finalizes_and_disconnects_after_ack(self):
        transport = FakeTransport()
        controller, output, manifest = self.run_session(transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]))
        self.assertEqual(transport.root_calls, 1)
        self.assertEqual(controller.command_count, 1)
        self.assertTrue(transport.disconnected)
        self.assertEqual(manifest["eligibility_state"], "CONTROLLED_ROOT_IDENTITY_CANDIDATE")
        self.assertFalse(next(row for row in manifest["commands"] if row["name"] == "eligibility-decision")["generic_integrity_pass"])
        self.assertEqual([x for x in transport.observed if x[0] == "property"].__len__(), len(stage.TARGET_PROPERTIES))
        self.assertEqual([x for x in transport.observed if x[0] not in {"state", "property", "mounts", "su-binary", "su-list"}], [])
        self.assertTrue(any("ROOT TEST COMPLETE" in line and "CAR POWERED OFF" in line for line in output))

    def test_owner_cancellation_sends_no_target_commands(self):
        transport = FakeTransport()
        controller, output, _ = self.run_session(transport, iter(["CANCEL"]), expected="CANCELLED")
        self.assertEqual(transport.observed, [])
        self.assertEqual(transport.root_calls, 0)
        self.assertEqual(controller.command_count, 0)
        self.assertFalse(any("ROOT TEST COMPLETE" in line for line in output))

    def test_not_yet_is_distinct_and_sends_no_target_commands(self):
        transport = FakeTransport()
        controller = stage.StageA(transport, input_fn=lambda _: "NOT YET", output_fn=lambda _: None)
        self.assertEqual(controller.run(), "NOT_YET")
        self.assertEqual(transport.observed, [])
        self.assertEqual(transport.root_calls, 0)

    def test_invalid_serial_stops_before_transport_commands(self):
        transport = FakeTransport()
        self.run_session(transport, iter(["YES", "bad;id", "CAR POWERED OFF"]), expected="FAIL")
        self.assertEqual(transport.observed, [])
        self.assertEqual(transport.root_calls, 0)

    def test_leading_option_serial_is_rejected_before_transport_commands(self):
        transport = FakeTransport()
        self.run_session(transport, iter(["YES", "-x", "CAR POWERED OFF"]), expected="FAIL")
        self.assertEqual(transport.observed, [])
        self.assertEqual(transport.root_calls, 0)

    def test_private_evidence_root_is_checked_before_any_target_command(self):
        transport = FakeTransport()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "unsafe"
            root.mkdir(mode=0o755)
            root.chmod(0o755)
            answers = iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"])
            controller = stage.StageA(transport, input_fn=lambda _: next(answers),
                                      output_fn=lambda _: None, evidence_root=root)
            self.assertEqual(controller.run(), "INCOMPLETE")
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
        for bad in ("rw-mount", "unknown-mount", "duplicate-mount", "xbin-overlay", "truncated-mount"):
            with self.subTest(bad=bad):
                transport = FakeTransport(bad=bad)
                self.run_session(transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]), expected="FAIL")
                self.assertEqual(transport.root_calls, 0)

    def test_anomalous_06777_is_controlled_candidate_not_generic_integrity_pass(self):
        self.assertEqual(stage.parse_su_listing(
            b"-rwsrwsrwx 0 0 75348 2014-01-01 00:00 su\n"), (0o6777, "75348"))
        with self.assertRaises(stage.SafetyStop):
            validate_su_fingerprint(ARCHIVED_SHA256.encode() + b"  /system/xbin/su\n",
                                    b"-rwsrwsrwx root root\n")
        self.assertEqual(stage.parse_su_listing(
            b"-rwsr-xr-x 0 0 75348 2014-01-01 00:00 su\n"), (0o4755, "75348"))

    def test_mode_parser_handles_special_bits_only_in_valid_positions(self):
        valid = stage.parse_su_listing(b"-rwsrwsrwt 0 0 75348 2014-01-01 00:00 su\n")
        self.assertEqual(valid, (0o7777, "75348"))
        for mode in ("-rwSrwsrwx", "-rwsrwsrwT"):
            with self.subTest(mode=mode):
                self.assertNotEqual(stage.parse_su_listing(
                    f"{mode} 0 0 75348 2014-01-01 00:00 su\n".encode()), (0o6777, "75348"))
        for mode in ("-rwtrwsrwx", "-rwsrwsrws"):
            with self.subTest(mode=mode):
                self.assertIsNone(stage.parse_su_listing(
                    f"{mode} 0 0 75348 2014-01-01 00:00 su\n".encode()))

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
            stage.Result(0, b"uid=0(root) gid=0(root)\n\xff", b""),
        ):
            self.assertFalse(stage.root_is_uid_zero(result))

    def test_root_exception_after_invocation_is_incomplete_and_still_prompts_shutdown(self):
        transport = FakeTransport(root=OSError("host adb interrupted after dispatch"))
        controller, output, manifest = self.run_session(
            transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]), expected="INCOMPLETE")
        self.assertEqual(transport.root_calls, 1)
        self.assertEqual(manifest["result"], "INCOMPLETE")
        self.assertTrue(transport.disconnected)
        self.assertTrue(any("ROOT TEST COMPLETE" in line for line in output))

    def test_finalization_does_not_leave_pass_manifest_when_hash_commit_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = stage.StageA(FakeTransport(), evidence_root=Path(tmp))
            replace = stage.os.replace
            calls = 0
            def fail_manifest_commit(source, destination):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated manifest commit failure")
                return replace(source, destination)
            with mock.patch.object(stage.os, "replace", side_effect=fail_manifest_commit):
                with self.assertRaisesRegex(OSError, "manifest commit"):
                    controller.finalize("PASS")
            folders = list(Path(tmp).glob("CL-STAGEA-*"))
            self.assertEqual(len(folders), 1)
            self.assertFalse((folders[0] / "manifest.json").exists())
            self.assertFalse((folders[0] / "sha256.txt").exists())

    def test_evidence_folder_collision_never_overwrites_existing_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            controller = stage.StageA(FakeTransport(), evidence_root=Path(tmp))
            class FrozenDateTime:
                @classmethod
                def now(cls, tz=None):
                    return datetime(2026, 11, 5, tzinfo=timezone.utc)
            with mock.patch.object(stage, "datetime", FrozenDateTime):
                controller.finalize("PASS")
                manifest_path = controller.output_dir / "manifest.json"
                before = manifest_path.read_bytes()
                second = stage.StageA(FakeTransport(), evidence_root=Path(tmp))
                with self.assertRaises(FileExistsError):
                    second.finalize("FAIL")
                self.assertEqual(manifest_path.read_bytes(), before)

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
        controller, output, manifest = self.run_session(transport, iter(["YES", "192.0.2.10:5555", "CAR POWERED OFF"]), expected="INCOMPLETE")
        self.assertEqual(transport.root_calls, 1)
        self.assertFalse(manifest["timeout_remote_termination_verified"])
        self.assertTrue(any("Stage A result: INCOMPLETE" in line and "remote termination is unverified" in line
                            for line in output))
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

    def test_auto_serial_is_rejected_without_any_target_command(self):
        transport = FakeTransport()
        self.run_session(transport, iter(["YES", "auto", "CAR POWERED OFF"]), expected="FAIL")
        self.assertEqual(transport.observed, [])
        self.assertEqual(transport.root_calls, 0)

    def test_host_disconnect_is_exact_and_requires_success_response(self):
        adapter = stage.AdbTransport()
        class FakeAdb:
            adb = "adb"
        adapter.adb = FakeAdb()
        adapter.serial = "192.0.2.10:5555"
        success = subprocess.CompletedProcess([], 0, b"disconnected 192.0.2.10:5555\n", b"")
        with mock.patch.object(stage.subprocess, "run", return_value=success) as run:
            adapter.disconnect()
        self.assertEqual(run.call_args.args[0], ("adb", "disconnect", adapter.serial))
        self.assertEqual(run.call_args.kwargs["timeout"], 5)
        failed = subprocess.CompletedProcess([], 1, b"", b"error")
        with mock.patch.object(stage.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(stage.SafetyStop, "not confirmed"):
                adapter.disconnect()


if __name__ == "__main__":
    unittest.main()
