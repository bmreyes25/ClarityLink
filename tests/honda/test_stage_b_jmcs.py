from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "honda-readonly-preflight"
sys.path.insert(0, str(TOOLS))

import stage_b_jmcs as stage_b
import root_identity_stage_a as stage_a
import privileged


SERIAL = "192.0.2.10:5555"
PID = 2468
TEST_SU_BINARY = bytes(range(256)) * 294 + bytes(range(84))
TEST_SU_SHA = hashlib.sha256(TEST_SU_BINARY).hexdigest()
BASE = 0x4008F000

TCP_HEADER = b"  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
UNIX_HEADER = b"Num       RefCount Protocol Flags    Type St Inode Path\n"


def proc_stat(pid: int = PID, start: int = 555) -> bytes:
    fields = ["S"] + ["0"] * 18 + [str(start)]
    return (f"{pid} (jmcs) " + " ".join(fields) + "\n").encode()


def proc_status(pid: int = PID) -> bytes:
    return (f"Name:\tjmcs\nState:\tS (sleeping)\nPid:\t{pid}\nPPid:\t1\n"
            "Uid:\t0\t0\t0\t0\nGid:\t0\t0\t0\t0\n").encode()


def ps_output(pid: int = PID) -> bytes:
    return (b"USER PID PPID VSIZE RSS WCHAN PC NAME\n" +
            f"root {pid} 1 1000 200 ffffffff 00000000 /system/bin/jmcs\n".encode())


def fd_listing() -> bytes:
    return (b"total 0\n"
            b"lrwx------ 1 root root 64 Nov 06 10:00 3 -> socket:[111]\n"
            b"lrwx------ 1 root root 64 Nov 06 10:00 4 -> socket:[222]\n"
            b"lrwx------ 1 root root 64 Nov 06 10:00 5 -> /dev/null\n")


def tcp_table(*, rows: bytes = b"") -> bytes:
    return TCP_HEADER + rows


def tcp_row(local: str, remote: str, state: str, inode: int) -> bytes:
    return f"   0: {local} {remote} {state} 00000000:00000000 00:00000000 00000000 0 0 {inode}\n".encode()


def network_table(table: str) -> bytes:
    if table == "tcp":
        return tcp_table(rows=(tcp_row("00000000:1388", "00000000:0000", "0A", 111) +
                               tcp_row("0100007F:C350", "0100007F:1388", "01", 222)))
    if table == "tcp6":
        return (TCP_HEADER +
                b"   0: 00000000000000000000000000000000:1770 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000 0 0 333\n")
    if table in {"udp", "udp6"}:
        prefix = "00000000" if table == "udp" else "00000000000000000000000000000000"
        return TCP_HEADER + f"   0: {prefix}:0035 {prefix}:0000 07 00000000:00000000 00:00000000 00000000 0 0 444\n".encode()
    return UNIX_HEADER + b"0000000000000000: 00000002 00000000 00010000 0001 01 555\n"


def maps_output(base: int = BASE) -> bytes:
    return (f"{base:08x}-{base + 0x400000:08x} r-xp 00000000 08:01 123 /system/bin/jmcs\n"
            f"{base + 0x400000:08x}-{base + 0x500000:08x} rw-p 00400000 08:01 123 /system/bin/jmcs\n").encode()


class FakeTransport:
    def __init__(self, *, bad: str | None = None, start_times: list[int] | None = None, pid_sequence: list[int] | None = None):
        self.bad = bad
        self.serial = ""
        self.records: list[dict[str, object]] = []
        self.ops: list[tuple[str, str]] = []
        self.root_calls = 0
        self.disconnected = False
        self.start_times = list(start_times or [555] * 20)
        self.identity_reads = 0
        self.snapshot_index = -1
        self.current_pid = PID
        self.pid_sequence = list(pid_sequence or [PID] * 20)
        self.mount_checks = 0
        self.process_hash = stage_b.EXPECTED_JMCS_SHA256

    def enumerate_devices(self):
        if self.bad == "endpoint-empty":
            return stage_b.ReadResult(0, b"List of devices attached\n", b"")
        if self.bad == "endpoint-ambiguous":
            return stage_b.ReadResult(0, f"List of devices attached\n{SERIAL}\tdevice\nother\tdevice\n".encode(), b"")
        if self.bad == "endpoint-usb-metadata":
            return stage_b.ReadResult(0, f"List of devices attached\n{SERIAL}\tdevice usb:1-1 product:MY16ADA\n".encode(), b"")
        selected = "wrong" if self.bad == "endpoint-wrong" else SERIAL
        return stage_b.ReadResult(0, f"List of devices attached\n{selected}\tdevice product:MY16ADA\n".encode(), b"")

    def set_serial(self, serial: str) -> None:
        self.serial = serial

    def observe(self, operation, argument="", *, timeout=5, max_bytes=stage_a.MAX_OUTPUT):
        self.ops.append((operation, argument))
        if operation == "state":
            return stage_a.Result(0, b"device\n", b"")
        if operation == "property":
            if self.bad == "target-mismatch" and argument == "ro.product.model":
                return stage_a.Result(0, b"WRONG\n", b"")
            return stage_a.Result(0, stage_a.TARGET_PROPERTIES[argument].encode() + b"\n", b"")
        if operation == "mounts":
            self.mount_checks += 1
            if self.bad == "mount-rw-connected" and self.mount_checks == 3:
                return stage_a.Result(0, b"/dev/block/system /system ext4 rw,seclabel 0 0\n", b"")
            if self.bad == "mount-jmcs-rw":
                return stage_a.Result(0, b"/dev/block/system /system ext4 ro,seclabel 0 0\n/dev/bin /system/bin ext4 rw,seclabel 0 0\n", b"")
            if self.bad == "mount-rw":
                return stage_a.Result(0, b"/dev/block/system /system ext4 rw,seclabel 0 0\n", b"")
            if self.bad == "mount-ambiguous":
                return stage_a.Result(0, b"/dev/a /system ext4 ro 0 0\noverlay /system/xbin overlay rw 0 0\n", b"")
            return stage_a.Result(0, b"/dev/block/system /system ext4 ro,seclabel 0 0\n", b"")
        if operation == "su-list":
            mode = "-rwsr-xr-x" if self.bad == "root-mode" else "-rwsrwsrwx"
            return stage_a.Result(0, f"{mode} 0 0 75348 2014-01-01 00:00 su\n".encode(), b"")
        if operation == "su-binary":
            binary = b"x" * len(TEST_SU_BINARY) if self.bad == "root-hash" else TEST_SU_BINARY
            return stage_a.Result(0, binary, b"")
        raise AssertionError(operation)

    def root_identity_once(self):
        self.root_calls += 1
        return stage_a.Result(0, b"uid=0(root) gid=0(root) groups=0(root)\n", b"")

    def _identity_result(self, operation, pid):
        self.identity_reads += 1
        index = min(max(self.snapshot_index, 0), len(self.start_times) - 1)
        start = self.start_times[index]
        if operation == "stat":
            return stage_b.ReadResult(0, proc_stat(pid=pid, start=start), b"")
        if operation == "status":
            if self.bad == "permission" and self.snapshot_index >= 3:
                return stage_b.ReadResult(1, b"", b"Permission denied")
            if self.bad == "timeout" and self.snapshot_index >= 3:
                return stage_b.ReadResult(1, b"", b"", timed_out=True)
            return stage_b.ReadResult(0, proc_status(pid), b"")
        if operation == "cmdline":
            payload = b"/system/bin/jmcs\x00--session-label=FIXTURE-ONLY\x00" if self.bad == "cmdline-secret" else b"/system/bin/jmcs\x00"
            return stage_b.ReadResult(0, payload, b"")
        if operation == "maps":
            if self.bad == "maps-truncated":
                return stage_b.ReadResult(0, maps_output()[:-1], b"", output_limited=False)
            if self.bad == "maps-limited":
                return stage_b.ReadResult(0, maps_output()[:-1], b"", output_limited=True)
            if self.bad == "maps-malformed":
                return stage_b.ReadResult(0, b"malformed\n", b"")
            return stage_b.ReadResult(0, maps_output(), b"")
        raise AssertionError(operation)

    def read_process(self, operation, pid):
        self.ops.append((operation, str(pid)))
        if self.bad == "process-missing":
            return stage_b.ReadResult(1, b"", b"No such file or directory")
        return self._identity_result(operation, pid)

    def read_ps(self):
        self.ops.append(("ps", ""))
        self.snapshot_index += 1
        self.current_pid = self.pid_sequence[min(self.snapshot_index, len(self.pid_sequence) - 1)]
        if self.bad == "process-missing":
            return stage_b.ReadResult(0, b"USER PID PPID NAME\nroot 1 0 init\n", b"")
        if self.bad == "process-multiple":
            return stage_b.ReadResult(0, ps_output() + b"root 999 1 1000 200 x x /system/bin/jmcs\n", b"")
        return stage_b.ReadResult(0, ps_output(self.current_pid), b"")

    def hash_jmcs(self):
        digest = "0" * 64 if self.bad == "jmcs-hash" else self.process_hash
        return stage_b.ReadResult(0, f"{digest}  /system/bin/jmcs\n".encode(), b"")

    def read_fd_links(self, pid):
        self.ops.append(("fd_links", str(pid)))
        if self.bad == "fd-malformed":
            return stage_b.ReadResult(0, b"total 1\nthis is malformed\n", b"")
        return stage_b.ReadResult(0, fd_listing(), b"")

    def read_network(self, table):
        self.ops.append(("network", table))
        if self.bad == "network-malformed" and table == "tcp6":
            return stage_b.ReadResult(0, TCP_HEADER + b"bad row\n", b"")
        if self.bad == "network-incomplete" and table == "udp6":
            return stage_b.ReadResult(0, b"", b"Permission denied")
        return stage_b.ReadResult(0, network_table(table), b"")

    def disconnect(self):
        self.disconnected = True
        return self.bad != "disconnect-fail"


def run_fake(*, bad: str | None = None, answers: list[str] | None = None,
             start_times: list[int] | None = None, pid_sequence: list[int] | None = None,
             serial: str = SERIAL):
    transport = FakeTransport(bad=bad, start_times=start_times, pid_sequence=pid_sequence)
    inputs = iter(answers or ["YES", "DISCONNECTED", "CONNECTED", "DISCONNECTED", "CAR POWERED OFF"])
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "private"
        root.mkdir(mode=0o700)
        controller = stage_b.StageB(transport, input_fn=lambda _: next(inputs),
                                    output_fn=lambda _: None, evidence_root=root, repo_root=ROOT, offline_simulation=True)
        with mock.patch.object(stage_a, "EXPECTED_SU_SHA256", TEST_SU_SHA), \
             mock.patch.object(privileged, "EXPECTED_SU_SHA256", TEST_SU_SHA):
            status = controller.run(serial)
        capture = controller.capture
        assert capture is not None
        # Keep the evidence live only within the test's temporary root.
        manifest = json.loads((capture.output / "manifest.json").read_text())
        permissions = (capture.output.stat().st_mode & 0o777,
                       (capture.output / "manifest.json").stat().st_mode & 0o777,
                       (capture.output / "sha256.txt").stat().st_mode & 0o777)
        hashes = []
        for line in (capture.output / "sha256.txt").read_text().splitlines():
            digest, relative = line.split("  ", 1)
            hashes.append(hashlib.sha256((capture.output / relative).read_bytes()).hexdigest() == digest)
        return status, transport, manifest, permissions, hashes


def run_fake_transport(transport, answers):
    inputs = iter(answers)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "private"
        root.mkdir(mode=0o700)
        controller = stage_b.StageB(transport, input_fn=lambda _: next(inputs),
                                    output_fn=lambda _: None, evidence_root=root, repo_root=ROOT, offline_simulation=True)
        with mock.patch.object(stage_a, "EXPECTED_SU_SHA256", TEST_SU_SHA), \
             mock.patch.object(privileged, "EXPECTED_SU_SHA256", TEST_SU_SHA):
            status = controller.run(SERIAL)
        manifest = json.loads((controller.capture.output / "manifest.json").read_text())
        hashes = [hashlib.sha256((controller.capture.output / rel).read_bytes()).hexdigest() == digest
                  for line in (controller.capture.output / "sha256.txt").read_text().splitlines()
                  for digest, rel in [line.split("  ", 1)]]
        return status, transport, manifest, None, hashes


def test_stage_b_successful_three_state_capture_is_bounded_private_and_same_epoch():
    status, transport, manifest, permissions, hashes = run_fake()
    assert status == "COMPLETE_OFFLINE_REVIEW_REQUIRED"
    assert manifest["phases_captured"] == ["baseline_disconnected", "connected_factory_carplay", "post_disconnect"]
    assert manifest["analysis"]["root_identity"] == "UID 0 verified; no other identity fields retained"
    assert manifest["analysis"]["jmcs_file_sha256"] == stage_b.EXPECTED_JMCS_SHA256
    assert "separate owner-authorized Stage B" in manifest["analysis"]["stage_b_scope"]
    eligibility = manifest["analysis"]["root_eligibility"]
    assert "Stage B-specific multi-read" in eligibility["exception"]
    assert "cannot atomically bind" in eligibility["fingerprint_binding"]
    assert transport.mount_checks == 4
    assert sum(operation == "su-binary" for operation, _ in transport.ops) == 4
    assert manifest["analysis"]["connected_runtime_callsites"]["load_bias"] == "0x4008f000"
    assert manifest["analysis"]["connected_runtime_callsites"]["callsites"]["setup_dispatch_call"]["runtime_instruction_address_even"] == "0x40319f72"
    assert manifest["analysis"]["connected_runtime_callsites"]["callsites"]["setup_dispatch_call"]["runtime_thumb_function_pointer_odd"] == "0x40319f73"
    assert permissions == (0o700, 0o600, 0o600)
    assert hashes and all(hashes)
    assert transport.root_calls == 1
    assert transport.disconnected
    assert sum(operation == "maps" for operation, _ in transport.ops) == 1
    assert any(row["operation"] == "process_cmdline" and row["phase"] == "baseline"
                   for row in manifest["commands"])
    assert manifest["analysis"]["executable_binding"].startswith("ps, proc stat PID/comm")
    assert manifest["analysis"]["shutdown_ack"] == "confirmed"
    assert not any(operation in {"mem", "environ", "ptrace", "strace", "debuggerd"}
                   for operation, _ in transport.ops)
    assert manifest["privacy"]["media_or_keys_captured"] is False
    assert manifest["owner_authorization_accepted"] is True


@pytest.mark.parametrize("bad", ["endpoint-empty", "endpoint-ambiguous", "endpoint-wrong", "endpoint-usb-metadata"])
def test_wrong_or_ambiguous_adb_endpoint_fails_before_target_commands(bad):
    status, transport, manifest, _, _ = run_fake(bad=bad)
    assert status == "SAFE_ABORT"
    assert transport.root_calls == 0
    assert transport.ops == []
    assert "endpoint" in manifest["stop_reason"].lower()


@pytest.mark.parametrize("bad", ["target-mismatch", "root-hash", "root-mode", "mount-rw", "mount-ambiguous", "mount-jmcs-rw"])
def test_identity_root_binary_and_mount_gates_fail_closed(bad):
    status, transport, manifest, _, _ = run_fake(bad=bad)
    assert status == "SAFE_ABORT"
    assert transport.root_calls == 0
    assert not any(operation == "ps" for operation, _ in transport.ops)
    assert manifest["commands"]


@pytest.mark.parametrize("bad", ["process-missing", "process-multiple"])
def test_missing_or_multiple_jmcs_candidates_stop_without_fallback(bad):
    status, transport, manifest, _, _ = run_fake(bad=bad)
    assert status == "SAFE_ABORT"
    assert "jmcs process candidate" in manifest["stop_reason"]
    assert not any(operation == "maps" for operation, _ in transport.ops)


def test_eligibility_is_rechecked_after_owner_connects_before_connected_reads():
    status, transport, manifest, _, _ = run_fake(bad="mount-rw-connected")
    assert status == "SAFE_ABORT"
    assert manifest["phases_captured"] == ["baseline_disconnected"]
    assert not any(operation == "maps" for operation, _ in transport.ops)
    assert transport.mount_checks == 3


def test_cmdline_arguments_are_parsed_transiently_and_never_persisted():
    status, _, manifest, _, _ = run_fake(bad="cmdline-secret")
    assert status == "COMPLETE_OFFLINE_REVIEW_REQUIRED"
    assert manifest["analysis"]["baseline_cmdline_argument_count"] == 2
    assert manifest["analysis"]["baseline_cmdline_raw_persisted"] is False
    assert not any("process_cmdline.raw" in item["path"] for item in manifest["artifacts"])
    row = next(item for item in manifest["commands"] if item["operation"] == "process_cmdline")
    assert row["stdout_redacted"] is True and row["stdout_sha256"] is None and row["stdout_bytes"] is None
    assert all(item["sha256"] != hashlib.sha256(b"/system/bin/jmcs\x00--session-label=FIXTURE-ONLY\x00").hexdigest()
               for item in manifest["artifacts"])


def test_start_time_change_at_connected_and_post_disconnect_gates_stops_exact_phase():
    status, transport, manifest, _, _ = run_fake(start_times=[555, 555, 556, 556, 556, 556])
    assert status == "SAFE_ABORT"
    assert "epoch changed" in manifest["stop_reason"]
    assert manifest["phases_captured"] == ["baseline_disconnected"]
    assert not any(operation == "maps" for operation, _ in transport.ops)
    status, transport, manifest, _, _ = run_fake(start_times=[555, 555, 555, 555, 556, 556])
    assert status == "SAFE_ABORT"
    assert "epoch changed" in manifest["stop_reason"]
    assert manifest["phases_captured"] == ["baseline_disconnected", "connected_factory_carplay"]


def test_pid_change_between_phases_stops_without_socket_reads_for_new_pid():
    status, transport, manifest, _, _ = run_fake(pid_sequence=[PID, PID, PID + 1, PID + 1])
    assert status == "SAFE_ABORT"
    assert "epoch changed" in manifest["stop_reason"]
    assert manifest["phases_captured"] == ["baseline_disconnected"]
    assert not any(operation == "maps" for operation, _ in transport.ops)


@pytest.mark.parametrize("bad", ["permission", "timeout", "maps-truncated", "maps-limited", "maps-malformed", "fd-malformed",
                                  "network-malformed", "network-incomplete", "jmcs-hash"])
def test_privilege_maps_fd_network_or_elf_mismatch_stops_without_retry(bad):
    status, transport, manifest, _, hashes = run_fake(bad=bad)
    assert status == "SAFE_ABORT"
    assert all(left != right for left, right in zip(transport.ops, transport.ops[1:]))
    if bad == "timeout":
        assert manifest["analysis"]["remote_operation_may_still_be_running"] is True
    assert not any(operation in {"install", "push", "pull", "signal", "restart"}
                   for operation, _ in transport.ops)
    assert manifest["stop_reason"]
    assert all(hashes)


def test_cancellation_writes_private_integrity_manifest_without_adb_access():
    status, transport, manifest, permissions, hashes = run_fake(answers=["CANCEL"])
    assert status == "CANCELLED"
    assert transport.ops == []
    assert transport.root_calls == 0
    assert manifest["commands"] == []
    assert permissions == (0o700, 0o600, 0o600)
    assert all(hashes)


def test_invalid_serial_stops_before_endpoint_or_target_access():
    status, transport, manifest, _, _ = run_fake(serial="-x; reboot")
    assert status == "SAFE_ABORT"
    assert transport.ops == []
    assert transport.root_calls == 0
    assert "serial" in manifest["stop_reason"].lower()


@pytest.mark.parametrize("bad,expected", [
    ("disconnect-fail", "INCOMPLETE_SHUTDOWN_OR_DISCONNECT_ACK"),
    (None, "INCOMPLETE_SHUTDOWN_OR_DISCONNECT_ACK"),
])
def test_controller_does_not_claim_complete_without_poweroff_and_adb_disconnect(bad, expected):
    answers = ["YES", "DISCONNECTED", "CONNECTED", "DISCONNECTED",
               "CAR POWERED OFF" if bad == "disconnect-fail" else "NOT POWERED OFF"]
    status, transport, manifest, _, _ = run_fake(bad=bad, answers=answers)
    assert status == expected
    assert not transport.disconnected if bad is None else transport.disconnected
    assert manifest["stop_reason"]


def test_abort_with_abnormal_factory_state_stops_without_poweroff_or_disconnect():
    answers = ["YES", "DISCONNECTED", "CONNECTED", "DISCONNECTED", "STOP"]
    status, transport, manifest, _, _ = run_fake(bad="maps-malformed", answers=answers)
    assert status == "SAFE_ABORT"
    assert not transport.disconnected
    assert manifest["analysis"]["shutdown_ack"] == "not_confirmed"


def test_usb_adb_endpoint_is_rejected_before_privileged_access():
    status, transport, manifest, _, _ = run_fake(serial="USB123456")
    assert status == "SAFE_ABORT"
    assert transport.root_calls == 0
    assert transport.ops == []
    assert "TCP/IP" in manifest["stop_reason"]


def test_stagea_observe_bounds_and_root_identity_does_not_use_stale_records(monkeypatch):
    monkeypatch.setattr(stage_b, "LIVE_COLLECTION_ENABLED", True)
    monkeypatch.setattr(stage_b.shutil, "which", lambda name: "/usr/bin/adb")
    transport = stage_b.AdbTransport()
    observed = []
    def observe(operation, argument="", *, timeout=5, max_bytes=stage_a.MAX_OUTPUT):
        observed.append((operation, argument, timeout, max_bytes))
        return stage_a.Result(0, b"device\n", b"")
    monkeypatch.setattr(transport.stage_a_transport, "observe", observe)
    transport.observe("state", timeout=100, max_bytes=10**7)
    assert observed == [("state", "", stage_b.MAX_TIMEOUT_SECONDS, stage_b.MAX_SMALL_OPERATION_BYTES)]
    monkeypatch.setattr(transport.stage_a_transport, "root_identity_once",
                        lambda: stage_a.Result(0, b"uid=0(root) gid=0(root)\n", b"", False, False))
    transport.serial = SERIAL
    transport.fixed = stage_b.FixedAdb(SERIAL, resolve_auto=False)
    transport.fixed.records.append({"result": "timeout", "truncated": True})
    result = transport.root_identity_once()
    assert result.code == 0 and not result.timed_out and not result.output_limited


def test_stagea_mount_su_metadata_binary_pull_and_root_id_use_fixed_plans(monkeypatch):
    monkeypatch.setattr(stage_b, "LIVE_COLLECTION_ENABLED", True)
    monkeypatch.setattr(stage_b.shutil, "which", lambda name: "/usr/bin/adb")
    transport = stage_b.AdbTransport()
    transport.set_serial(SERIAL)
    calls = []

    def fake_run(self, command, operation, args, *, timeout, max_bytes):
        calls.append((command, operation, args, timeout, max_bytes))
        self.records.append({"result": "success", "truncated": False})
        if operation == "stage_a_su_binary_pull":
            Path(command[-1]).write_bytes(TEST_SU_BINARY)
            return 0, b"", b""
        if operation == "stage_a_root_identity":
            return 0, b"uid=0(root) gid=0(root)\n", b""
        return 0, b"fixed observation\n", b""

    monkeypatch.setattr(stage_b.FixedAdb, "_run_planned", fake_run)
    for operation in ("mounts", "su-list", "su-binary"):
        result = transport.observe(operation)
        assert result.code == 0 and not result.timed_out and not result.output_limited
    root_result = transport.root_identity_once()
    assert root_result.stdout == b"uid=0(root) gid=0(root)\n"

    assert [row[1] for row in calls] == [
        "read", "ls-su-n", "stage_a_su_binary_pull",
        "stage_a_root_identity"]
    assert calls[0][0][1:5] == ("-s", SERIAL, "shell", "cat")
    assert calls[0][0][5] == "/proc/self/mounts"
    assert calls[1][0][1:5] == ("-s", SERIAL, "shell", "ls")
    assert calls[1][0][5:] == ("-n", "/system/xbin/su")
    assert calls[2][0][1:5] == ("-s", SERIAL, "pull", "/system/xbin/su")
    assert calls[3][0][1:7] == ("-s", SERIAL, "shell", "/system/xbin/su", "-c", "id")
    assert [row[3:] for row in calls[:3]] == [
        (stage_b.MAX_TIMEOUT_SECONDS, stage_b.MAX_SMALL_OPERATION_BYTES),
        (stage_b.MAX_TIMEOUT_SECONDS, stage_b.MAX_SMALL_OPERATION_BYTES),
        (stage_b.MAX_TIMEOUT_SECONDS, stage_a.MAX_OUTPUT)]
    assert calls[3][3:] == (stage_a.ROOT_TIMEOUT, stage_a.MAX_OUTPUT)

def test_proc_stat_pid_and_comm_must_match_selected_jmcs():
    identity = stage_b.parse_process_identity(ps_output(), proc_stat(), proc_status())
    assert identity.pid == PID
    with pytest.raises(stage_b.SafetyStop):
        stage_b.parse_process_identity(ps_output(), proc_stat(pid=PID + 1), proc_status())
    with pytest.raises(stage_b.SafetyStop):
        stage_b.parse_process_identity(ps_output(), proc_stat().replace(b"(jmcs)", b"(other)"), proc_status())


def test_owned_socket_delta_reports_only_exact_fd_inode_table_changes():
    row = {"fd": 3, "socket_inode": 111, "endpoint": {"table": "tcp", "local": "a"}}
    added = {"fd": 4, "socket_inode": 222, "endpoint": {"table": "tcp", "local": "b"}}
    delta = stage_b.compare_socket_snapshots({"owned_socket_matches": [row]},
                                              {"owned_socket_matches": [row, added]})
    assert delta["added_owned_socket_rows"] == [added]
    assert delta["removed_owned_socket_rows"] == []
    assert delta["unchanged_owned_socket_row_count"] == 1
    assert "no stream role" in delta["interpretation_limit"]


def test_owner_consent_prompt_discloses_exact_bound_endpoint(tmp_path):
    transport = FakeTransport()
    transport.set_serial(SERIAL)
    outputs = []
    controller = stage_b.StageB(transport, input_fn=lambda _: "YES", output_fn=outputs.append,
                                evidence_root=tmp_path, repo_root=ROOT, offline_simulation=True)
    assert controller._owner_gate() == "YES"
    prompt = "\n".join(outputs)
    assert f"Exact ADB endpoint: {SERIAL}" in prompt
    assert "cannot atomically bind" in prompt
    assert "four bounded temporary su binary pulls" in prompt
    assert "NOT YET defers" in prompt and "CANCEL declines" in prompt


@pytest.mark.parametrize(("answer", "expected"), [("NOT YET", "NOT_YET"), ("CANCEL", "CANCELLED")])
def test_owner_deferral_and_cancellation_are_distinct_and_precede_target_access(answer, expected):
    status, transport, manifest, _, _ = run_fake(answers=[answer])
    assert status == expected
    assert manifest["owner_decision"] == answer
    assert not manifest["owner_authorization_accepted"]
    assert transport.ops == []
    assert transport.root_calls == 0


def test_socket_delta_fails_closed_on_incomplete_snapshot():
    with pytest.raises(stage_b.SafetyStop, match="incomplete"):
        stage_b.compare_socket_snapshots({}, {"owned_socket_matches": []})


def test_real_transport_uses_bounded_fixed_host_and_privileged_plans(monkeypatch):
    monkeypatch.setattr(stage_b, "LIVE_COLLECTION_ENABLED", True)
    monkeypatch.setattr(stage_b.shutil, "which", lambda name: "/usr/bin/adb")
    transport = stage_b.AdbTransport()
    transport.set_serial(SERIAL)
    calls = []
    responses = iter([
        (0, b"List of devices attached\n", b""),
        (0, b"disconnected 192.0.2.10:5555\n", b""),
    ])
    def fake_run(self, command, operation, args, *, timeout, max_bytes):
        calls.append((command, operation, args, timeout, max_bytes))
        code, out, err = next(responses)
        self.records.append({"result": "success", "truncated": False})
        return code, out, err
    monkeypatch.setattr(stage_b.FixedAdb, "_run_planned", fake_run)
    result = transport.enumerate_devices()
    assert result.stdout.startswith(b"List of devices attached")
    assert calls[-1][0][1:3] == ("devices", "-l")
    assert calls[-1][3:] == (stage_b.MAX_TIMEOUT_SECONDS, stage_b.MAX_SMALL_OPERATION_BYTES)
    assert transport.disconnect()
    assert calls[-1][0][-2:] == ("disconnect", SERIAL)
    assert calls[-1][0] == (transport.adb_path, "disconnect", SERIAL)
    assert calls[-1][3:] == (stage_b.MAX_TIMEOUT_SECONDS, stage_b.MAX_SMALL_OPERATION_BYTES)


@pytest.mark.parametrize(("code", "stdout", "stderr", "result", "truncated"), [
    (1, b"", b"offline", "error", False),
    (0, b"disconnected other:5555\n", b"", "success", False),
    (0, b"", b"", "timeout", False),
    (0, b"disconnected 192.0.2.10:5555\n", b"", "output_limit", True),
])
def test_disconnect_failure_shapes_are_not_reported_as_success(
        monkeypatch, code, stdout, stderr, result, truncated):
    monkeypatch.setattr(stage_b, "LIVE_COLLECTION_ENABLED", True)
    monkeypatch.setattr(stage_b.shutil, "which", lambda name: "/usr/bin/adb")
    transport = stage_b.AdbTransport()
    transport.set_serial(SERIAL)
    calls = []

    def fake_run(self, command, operation, args, *, timeout, max_bytes):
        calls.append((command, operation, timeout, max_bytes))
        self.records.append({"result": result, "truncated": truncated})
        return code, stdout, stderr

    monkeypatch.setattr(stage_b.FixedAdb, "_run_planned", fake_run)
    assert transport.disconnect() is False
    assert len(calls) == 1
    assert calls[0][0] == (transport.adb_path, "disconnect", SERIAL)
    assert calls[0][1:] == ("stage_b_adb_disconnect", stage_b.MAX_TIMEOUT_SECONDS,
                            stage_b.MAX_SMALL_OPERATION_BYTES)


def test_real_transport_privileged_plans_and_bounds_are_fixed(monkeypatch):
    monkeypatch.setattr(stage_b, "LIVE_COLLECTION_ENABLED", True)
    monkeypatch.setattr(stage_b.shutil, "which", lambda name: "/usr/bin/adb")
    transport = stage_b.AdbTransport()
    transport.set_serial(SERIAL)
    calls = []

    def fake_run(self, command, operation, args, *, timeout, max_bytes):
        calls.append((command, operation, args, timeout, max_bytes))
        self.records.append({"result": "success", "truncated": False})
        return 0, b"fixed response\n", b""

    monkeypatch.setattr(stage_b.FixedAdb, "_run_planned", fake_run)
    for operation in ("stat", "status", "cmdline", "maps"):
        assert transport.read_process(operation, PID).code == 0
    assert transport.read_ps().code == 0
    assert transport.read_fd_links(PID).code == 0
    for table in stage_b.NETWORK_TABLES:
        assert transport.read_network(table).code == 0
    assert transport.hash_jmcs().code == 0

    assert len(calls) == 12
    for command, operation, args, timeout, max_bytes in calls:
        assert timeout == stage_b.MAX_TIMEOUT_SECONDS
        assert max_bytes in {stage_b.MAX_OPERATION_BYTES, stage_b.MAX_SMALL_OPERATION_BYTES}
        if operation.startswith("stage_b_process_") or operation in {"stage_b_fd_links"} or operation.startswith("stage_b_network_"):
            assert command[1:6] == ("-s", SERIAL, "shell", "/system/xbin/su", "-c")
            remote = command[6]
            assert max_bytes == stage_b.MAX_OPERATION_BYTES
            if operation.startswith("stage_b_process_"):
                assert remote in {f"cat /proc/{PID}/{leaf}" for leaf in ("stat", "status", "cmdline", "maps")}
            elif operation == "stage_b_fd_links":
                assert remote == f"ls -l /proc/{PID}/fd"
            elif operation.startswith("stage_b_network_"):
                assert remote in {f"cat {path}" for path in privileged.NETWORK_PATHS.values()}
        elif operation == "stage_b_ps":
            assert command[1:5] == ("-s", SERIAL, "shell", "ps")
            assert max_bytes == stage_b.MAX_SMALL_OPERATION_BYTES
        elif operation == "stage_b_jmcs_hash":
            assert command[1:5] == ("-s", SERIAL, "shell", "sha256sum")
            assert command[5] == "/system/bin/jmcs"
            assert max_bytes == stage_b.MAX_SMALL_OPERATION_BYTES


def test_real_transport_privileged_timeout_is_reported_without_retry(monkeypatch):
    monkeypatch.setattr(stage_b, "LIVE_COLLECTION_ENABLED", True)
    monkeypatch.setattr(stage_b.shutil, "which", lambda name: "/usr/bin/adb")
    transport = stage_b.AdbTransport()
    transport.set_serial(SERIAL)
    calls = []

    def timeout_run(self, command, operation, args, *, timeout, max_bytes):
        calls.append(operation)
        self.records.append({"result": "timeout", "truncated": False})
        return 0, b"", b""

    monkeypatch.setattr(stage_b.FixedAdb, "_run_planned", timeout_run)
    result = transport.read_network("tcp")
    assert result.timed_out
    assert calls == ["stage_b_network_tcp"]


def test_private_evidence_root_rejects_checkout_and_symlink(tmp_path):
    with pytest.raises(stage_b.SafetyStop):
        stage_b.verify_private_root(ROOT / "private-evidence-test", ROOT)
    target = tmp_path / "real"
    target.mkdir(mode=0o700)
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(stage_b.SafetyStop):
        stage_b.verify_private_root(link, ROOT)


def test_live_transport_direct_invocation_stays_disabled(tmp_path):
    with pytest.raises(stage_b.SafetyStop):
        stage_b.AdbTransport()
    transport = object.__new__(stage_b.AdbTransport)
    outputs = []
    controller = stage_b.StageB(transport, input_fn=lambda _: "YES", output_fn=outputs.append,
                                evidence_root=tmp_path, repo_root=ROOT)
    with mock.patch.object(stage_b, "LIVE_COLLECTION_ENABLED", False):
        with pytest.raises(stage_b.SafetyStop, match="disabled"):
            controller.run(SERIAL)
    assert list(tmp_path.iterdir()) == []
    with mock.patch.object(stage_b, "LIVE_COLLECTION_ENABLED", False), mock.patch.object(
            stage_b, "AdbTransport", side_effect=AssertionError("must not construct live transport")):
        assert stage_b.main(["--serial", SERIAL]) == 2


def test_dry_run_mentions_postdisconnect_hash_and_cmdline_validation(capsys):
    assert stage_b.main(["--serial", SERIAL, "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "post-disconnect: repeat process identity plus transient cmdline validation and jmcs hash" in output


def test_adb_transport_cannot_enter_offline_simulation(monkeypatch, tmp_path):
    monkeypatch.setattr(stage_b, "LIVE_COLLECTION_ENABLED", True)
    monkeypatch.setattr(stage_b.shutil, "which", lambda name: "/usr/bin/adb")
    transport = stage_b.AdbTransport()
    with pytest.raises(stage_b.SafetyStop, match="cannot use the offline-simulation path"):
        stage_b.StageB(transport, evidence_root=tmp_path, repo_root=ROOT, offline_simulation=True)


def test_unexpected_internal_exception_reaches_owner_abort_path():
    transport = FakeTransport()
    transport.bad = "unexpected-exception"
    original = transport.read_fd_links
    def fail(pid):
        raise AssertionError("simulated unexpected transport defect")
    transport.read_fd_links = fail
    answers = ["YES", "DISCONNECTED", "NORMAL", "CAR POWERED OFF"]
    status, transport, manifest, _, hashes = run_fake_transport(transport, answers)
    assert status == "SAFE_ABORT"
    assert "AssertionError" in manifest["stop_reason"]
    assert manifest["analysis"]["shutdown_ack"] == "confirmed"
    assert transport.disconnected and all(hashes)


def test_failed_privileged_operation_has_no_retry_or_followup():
    status, transport, manifest, _, _ = run_fake(bad="network-incomplete")
    assert status == "SAFE_ABORT"
    assert transport.ops.count(("network", "udp6")) == 1
    assert ("network", "unix") not in transport.ops
    assert "network_udp6" in [row["operation"] for row in manifest["commands"]]


def test_fd_inode_join_does_not_claim_unowned_sockets_and_separates_tcp_states():
    fds = stage_b.parse_fd_links(fd_listing())
    network = {table: stage_b.parse_network_table(table, network_table(table)) for table in stage_b.NETWORK_TABLES}
    owned = stage_b.attribute_sockets(fds, network)
    assert {(x["fd"], x["socket_inode"], x["state"]) for x in owned} == {
        (3, 111, "LISTEN"), (4, 222, "ESTABLISHED")}
    assert all(x["ownership"] == "jmcs_fd_symlink_inode_exact_match" for x in owned)
    assert all(x["socket_inode"] != 333 for x in owned)
    assert network["tcp"][0]["local_port"] == 5000
    assert network["tcp"][1]["local_address"] == "127.0.0.1"
    assert network["tcp6"][0]["local_port"] == 6000
    assert network["tcp6"][0]["local_address"] == "::"
    assert network["udp6"][0]["local_port"] == 53


@pytest.mark.parametrize("table,raw", [
    ("tcp", TCP_HEADER + b"bad row\n"),
    ("tcp6", b"wrong header\n"),
    ("udp", TCP_HEADER.replace(b" inode", b"")),
    ("udp6", TCP_HEADER + b"   0: abc:0001 00000000000000000000000000000000:0000 07 0 0 0 0 0 0 9\n"),
    ("unix", UNIX_HEADER + b"malformed\n"),
])
def test_network_parser_rejects_malformed_or_incomplete_tables(table, raw):
    with pytest.raises(stage_b.SafetyStop):
        stage_b.parse_network_table(table, raw)


def test_toolbox_fd_listing_shape_and_kernel_extended_udp_header():
    raw_fd = (b"lrwx------ root     root              2026-09-29 09:09 11 -> socket:[255825]\n"
              b"lr-x------ root     root              2026-09-29 09:09 15 -> /dev/urandom\n")
    parsed = stage_b.parse_fd_links(raw_fd)
    assert parsed == {"11": {"kind": "socket", "socket_inode": 255825},
                      "15": {"kind": "other"}}
    udp_header = (b"  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode ref pointer drops\n")
    udp_row = b"   0: 00000000:0035 00000000:0000 07 00000000:00000000 00:00000000 00000000 0 0 444 1 00000000 0\n"
    rows = stage_b.parse_network_table("udp", udp_header + udp_row)
    assert rows[0]["inode"] == 444


def test_ipv6_header_alias_and_unix_path_with_spaces():
    tcp6_header = TCP_HEADER.replace(b"rem_address", b"remote_address")
    tcp6_rows = network_table("tcp6").splitlines()[1:]
    decoded = stage_b.parse_network_table("tcp6", tcp6_header + b"\n".join(tcp6_rows) + b"\n")
    assert decoded[0]["local_port"] == 6000
    unix_path = (UNIX_HEADER +
        b"0000000000000000: 00000002 00000000 00010000 0001 01 555 /tmp/name with spaces\n")
    unix = stage_b.parse_network_table("unix", unix_path)
    assert unix[0]["path_present"] is True


def test_maps_load_bias_requires_exact_elf_path_and_preserves_thumb_bit():
    result = stage_b.calculate_runtime_callsites(maps_output())
    assert result["load_bias"] == "0x4008f000"
    setup = result["callsites"]["setup_dispatch_call"]
    assert setup["static_instruction_va"] == "0x0028af72"
    assert setup["runtime_instruction_address_even"] == "0x40319f72"
    assert setup["runtime_thumb_function_pointer_odd"] == "0x40319f73"
    with pytest.raises(stage_b.SafetyStop):
        stage_b.calculate_runtime_callsites(maps_output().replace(b"/system/bin/jmcs", b"/tmp/not-jmcs"))


def test_cmdline_and_fd_links_reject_malformed_identity():
    assert stage_b.parse_cmdline(b"/system/bin/jmcs\x00") == ("/system/bin/jmcs",)
    with pytest.raises(stage_b.SafetyStop):
        stage_b.parse_cmdline(b"/system/bin/other\x00")
    with pytest.raises(stage_b.SafetyStop):
        stage_b.parse_cmdline(b"/system/bin/jmcs")
    with pytest.raises(stage_b.SafetyStop):
        stage_b.parse_fd_links(b"total 1\nthis is malformed\n")


def test_controller_exposes_no_arbitrary_process_or_network_reads():
    transport = object.__new__(stage_b.AdbTransport)
    transport.fixed = None
    with pytest.raises(stage_b.SafetyStop):
        transport.read_process("environ", PID)
    with pytest.raises(stage_b.SafetyStop):
        stage_b.parse_network_table("route", b"anything\n")
