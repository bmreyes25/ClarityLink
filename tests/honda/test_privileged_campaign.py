from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "honda-readonly-preflight"
sys.path.insert(0, str(TOOLS))

import collector
import privileged
import privileged_campaign as campaign


def test_profile_and_source_pins_are_exact_and_live_requires_review_gate():
    digest = campaign.verify_profile()
    assert digest == campaign.PROFILE_HASH_PATH.read_text().split()[0]
    assert set(campaign.source_hashes()) == {
        "analyze.py", "privileged.py", "privileged_campaign.py", "collector.py", "parsers.py",
        "privileged_campaign_static_dependencies.json",
    }
    dry_run = campaign.dry_run_report()
    assert dry_run["live_capture_enabled"] is False
    assert dry_run["live_capture_gate"] == "exact stage-specific human review plus separate owner authorization"


def test_dry_run_is_complete_bounded_and_never_initializes_adb(monkeypatch):
    monkeypatch.setattr(collector.shutil, "which", lambda _name: pytest.fail("ADB lookup"))
    plan = campaign.dry_run_report("SYNTHETIC-SERIAL")
    assert plan["live_capture_enabled"] is False
    assert {row["stage"] for row in plan["commands"]} == {
        "R0_nonexecuting", "R1_minimum_privilege_check", *campaign.PHASE_IDS
    }
    assert all(0 < row["timeout_seconds"] <= campaign.MAX_COMMAND_TIMEOUT for row in plan["commands"])
    assert all(0 < row["max_output_bytes"] <= campaign.MAX_COMMAND_OUTPUT for row in plan["commands"])
    joined = " ".join(" ".join(row["argv"]) for row in plan["commands"])
    for forbidden in ("/proc/1234/mem", "ptrace", "kill ", "chmod ", "busybox base64"):
        assert forbidden not in joined
    assert "/proc/1234/exe" in joined
    assert "/proc/1234/fd/3" in joined


def test_phase_manifest_includes_each_elevated_identity_and_process_table_check():
    operations = [row[0] for row in campaign.PHASE_OPERATIONS]
    assert operations.count("identity") == 2
    assert operations.count("ps") == 2
    assert operations[-1] == "identity"


def test_fixed_executable_and_fd_link_commands_allow_only_numeric_paths(monkeypatch):
    monkeypatch.setattr(collector.shutil, "which", lambda _name: "/usr/bin/adb")
    adb = collector.FixedAdb("SYNTHETIC", resolve_auto=False)
    reader = privileged.PrivilegedRead(adb)
    assert reader.plan(privileged.PrivilegedOperation.PROCESS_EXE_LINK, pid=23)[-1] == "/system/bin/ls -l /proc/23/exe"
    assert reader.plan(privileged.PrivilegedOperation.FD_LINK, pid=23, fd=0)[-1] == "/system/bin/ls -l /proc/23/fd/0"
    for pid, fd in ((0, 0), (23, -1), (True, 3), (23, "3;id"), (2**31, 0)):
        with pytest.raises(collector.SafetyStop):
            reader.plan(privileged.PrivilegedOperation.FD_LINK, pid=pid, fd=fd)


def test_reader_compatibility_paths_translate_to_fixed_absolute_su_commands(monkeypatch):
    monkeypatch.setattr(collector.shutil, "which", lambda _name: "/usr/bin/adb")
    adb = collector.FixedAdb("SYNTHETIC", resolve_auto=False)
    calls = []

    def record(command, operation, arguments, *, timeout, max_bytes):
        calls.append((command, operation, arguments, timeout, max_bytes))
        return 0, b"ok\n", b""

    monkeypatch.setattr(adb, "_run_planned", record)
    reader = privileged.PrivilegedRead(adb)
    assert reader.run("read", "/proc/23/maps", timeout=5, max_bytes=64)[0] == 0
    assert reader.run("list", "/proc/23/fd", timeout=5, max_bytes=64)[0] == 0
    assert reader.run("readlink", "/proc/23/fd/4", timeout=5, max_bytes=64)[0] == 0
    assert reader.run("readlink", "/proc/23", "exe", timeout=5, max_bytes=64)[0] == 0
    remotes = [call[0][-1] for call in calls]
    assert remotes == [
        "/system/bin/cat /proc/23/maps",
        "/system/bin/ls -l /proc/23/fd",
        "/system/bin/ls -l /proc/23/fd/4",
        "/system/bin/ls -l /proc/23/exe",
    ]
    assert all(call[1].startswith("privileged_") for call in calls)


def test_live_root_cli_stays_disabled_before_authorization_or_adb(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(campaign, "FixedAdb", lambda *_a, **_k: pytest.fail("ADB constructed"))
    assert campaign.main(["--stage", "R0_nonexecuting", "--authorization", str(tmp_path / "auth.json")]) == 2
    assert "live root capture is disabled" in capsys.readouterr().err.lower()


def test_live_root_library_entrypoint_stays_disabled_before_adb(monkeypatch, tmp_path):
    monkeypatch.setattr(campaign, "FixedAdb", lambda *_a, **_k: pytest.fail("ADB constructed"))
    with pytest.raises(collector.SafetyStop, match="live root capture is disabled"):
        campaign.execute_approved_stage({"adb_serial": "SYNTHETIC"}, "R0_nonexecuting", tmp_path)


def test_saved_elf_dependencies_are_not_misreported_as_runtime_loaded():
    result = campaign.compare_runtime_dependencies(
        ["/system/lib/libc.so", "/system/lib/libdecoder.so"],
        ["libc.so", "libm.so", "libdecoder.so"],
    )
    assert result["saved_dependencies_currently_mapped"] == ["libc.so", "libdecoder.so"]
    assert result["saved_dependencies_not_seen_in_runtime_maps"] == ["libm.so"]
    assert "do not prove runtime loading" in result["interpretation"]


def test_authorization_requires_external_private_bound_artifacts(tmp_path):
    profile_hash = campaign.verify_profile()
    review = tmp_path / "review.txt"
    review.write_text("synthetic human-review fixture\n")
    review.chmod(0o600)
    record = {
        "campaign_id": campaign.CAMPAIGN_ID,
        "profile_sha256": profile_hash,
        "source_hashes": campaign.source_hashes(),
        "stage_id": "R0_nonexecuting",
        "phase_ids": [],
        "owner_authorized": True,
        "owner_authorized_utc": "2026-10-30T12:00:00Z",
        "adb_serial": "SYNTHETIC-SERIAL",
        "owner_confirmed_park": True,
        "owner_confirmed_parking_brake": True,
        "owner_present": True,
        "owner_confirmed_factory_baseline": True,
        "owner_confirmed_vehicle_power_state": "synthetic fixture power state",
        "independent_review": {
            "decision": "APPROVED", "reviewer_identity": "synthetic fixture only",
            "reviewer_competence": "synthetic fixture only", "independence_attested": True,
            "profile_sha256": profile_hash, "source_hashes": campaign.source_hashes(),
            "stage_id": "R0_nonexecuting",
            "phase_ids": [],
            "reviewed_vehicle_power_state": "synthetic fixture power state",
            "artifact_path": str(review),
            "artifact_sha256": hashlib.sha256(review.read_bytes()).hexdigest(),
        },
    }
    auth = tmp_path / "authorization.json"
    auth.write_text(json.dumps(record))
    auth.chmod(0o600)
    assert campaign.validate_authorization(auth, stage_id="R0_nonexecuting")["adb_serial"] == "SYNTHETIC-SERIAL"
    record["source_hashes"]["privileged.py"] = "0" * 64
    auth.write_text(json.dumps(record))
    with pytest.raises(collector.SafetyStop, match="does not bind"):
        campaign.validate_authorization(auth, stage_id="R0_nonexecuting")


def test_live_cli_requires_stage_authorization_before_any_adb_construction(monkeypatch, capsys):
    monkeypatch.setattr(campaign, "FixedAdb", lambda *_a, **_k: pytest.fail("ADB constructed"))
    assert campaign.main(["--serial", "SYNTHETIC-SERIAL"]) == 2
    assert "authorization record and one explicit --stage are required" in capsys.readouterr().err.lower()


def test_r0_only_reads_su_metadata_and_rejects_archived_writable_mode(monkeypatch, tmp_path):
    class Reader:
        serial = "SYNTHETIC"

        def __init__(self):
            self.records = []

        def run(self, operation, *args, **kwargs):
            self.records.append((operation, args))
            if operation == "id":
                return 0, b"uid=2000(shell) gid=2000(shell) groups=2000\n", b""
            if operation == "hash-su":
                return 0, (privileged.EXPECTED_SU_SHA256 + "  /system/xbin/su\n").encode(), b""
            if operation == "ls-su":
                return 0, b"-rwsrwsrwx root root 75348 /system/xbin/su\n", b""
            raise AssertionError(f"R0 must not run {operation} {args}")

    reader = Reader()
    output = tmp_path / "private-r0"
    output.mkdir(mode=0o700)
    capture = collector.Capture(reader, output)
    monkeypatch.setattr(capture, "verify_target_identity", lambda _phase: {
        "android_release": "4.2.2", "android_sdk": "17", "device": "vcm30t30a",
        "board": "Andromeda", "hardware": "vcm30t30", "kernel_version": "3.1.10+",
    })
    with pytest.raises(collector.SafetyStop, match="non-writable"):
        campaign.run_r0_nonexecuting_preflight(capture)
    assert [operation for operation, _args in reader.records] == ["id", "hash-su", "ls-su"]


def test_r0_never_invokes_superuser(monkeypatch, tmp_path):
    class Reader:
        serial = "SYNTHETIC"
        records = []

        def run(self, operation, *args, **kwargs):
            self.records.append(operation)
            if operation == "id":
                return 0, b"uid=2000(shell) gid=2000(shell)\n", b""
            if operation == "hash-su":
                return 0, (privileged.EXPECTED_SU_SHA256 + "  /system/xbin/su\n").encode(), b""
            if operation == "ls-su":
                return 0, b"-rwsr-sr-x root root 75348 /system/xbin/su\n", b""
            raise AssertionError(f"unexpected R0 operation: {operation}")

    reader = Reader()
    output = tmp_path / "private-r0"
    output.mkdir(mode=0o700)
    capture = collector.Capture(reader, output)
    monkeypatch.setattr(capture, "verify_target_identity", lambda _phase: {"target": "synthetic"})
    campaign.run_r0_nonexecuting_preflight(capture)
    assert reader.records == ["id", "hash-su", "ls-su"]


def _proc_stat(start: int = 42) -> bytes:
    tail = " ".join(["S"] + ["0"] * 18 + [str(start), "0"])
    return f"123 (jmcs) {tail}\n".encode()


class _FixturePrivilegedReader:
    serial = "SYNTHETIC"

    def __init__(self, *, map_result: int = 0, after_start: int = 42,
                 status_name: str = "jmcs", fd_count: int = 2):
        self.records = []
        self.map_result = map_result
        self.after_start = after_start
        self.status_name = status_name
        self.fd_count = fd_count
        self.stat_calls = 0

    def verify_root(self):
        self.records.append({"operation": "privileged_identity", "result": "success"})
        return 0, b"uid=0(root) gid=0(root)\n", b""

    def run(self, operation, *args, timeout=20, max_bytes=1 << 20, **kwargs):
        self.records.append({"operation": str(operation), "arguments": list(args),
                             "timeout_seconds": timeout, "max_output_bytes": max_bytes})
        if operation == privileged.PrivilegedOperation.PS:
            return 0, b"PID NAME\n123 jmcs\n", b""
        if operation == privileged.PrivilegedOperation.PROCESS_READ:
            leaf = kwargs["leaf"]
            if leaf == "stat":
                self.stat_calls += 1
                start = self.after_start if self.stat_calls > 1 else 42
                return 0, _proc_stat(start), b""
            if leaf == "status":
                return 0, (f"Name:\t{self.status_name}\nPid:\t123\nUid:\t0\t0\t0\t0\nGid:\t0\t0\t0\t0\nPPid:\t1\n").encode(), b""
            if leaf == "cmdline":
                return 0, b"/system/bin/jmcs\0", b""
            raise AssertionError(leaf)
        if operation == privileged.PrivilegedOperation.PROCESS_EXE_LINK:
            return 0, b"lrwxrwxrwx root root 0 Jan 1 00:00 /proc/123/exe -> /system/bin/jmcs\n", b""
        if operation == "read" and args == ("/proc/123/maps",):
            return (self.map_result, b"permission denied\n" if self.map_result else
                    b"1000-2000 r-xp 00000000 08:01 1 /system/bin/jmcs\n", b"")
        if operation == "read" and args == ("/proc/123/smaps",):
            return 0, b"1000-2000 r-xp 00000000 08:01 1 /system/bin/jmcs\nKernelPageSize: 4 kB\nMMUPageSize: 4 kB\n", b""
        if operation == "list":
            rows = [f"lrwx------ 1 root root 64 Oct 30 01:00 {fd} -> /dev/null"
                    for fd in range(self.fd_count)]
            return 0, ("\n".join(rows) + "\n").encode(), b""
        if operation == "readlink":
            fd = args[0].rsplit("/", 1)[-1]
            target = "socket:[55]" if fd == "1" else "/dev/null"
            return 0, f"lrwx------ 1 root root 64 Oct 30 01:00 {fd} -> {target}\n".encode(), b""
        if operation == "read" and args[0].startswith("/proc/net/"):
            if args[0].endswith("/unix"):
                return 0, b"Num RefCount Protocol Flags Type St Inode Path\n0000000000000000: 00000002 00000000 00010000 0001 01 55 /run/socket\n", b""
            return 0, b"sl local_address rem_address st tx_queue:rx_queue tr:tm->when retrnsmt uid timeout inode\n", b""
        raise AssertionError((operation, args, kwargs))


def _capture(tmp_path, reader):
    output = tmp_path / "private"
    output.mkdir(mode=0o700)
    return collector.Capture(reader, output)


def test_synthetic_bounded_phase_collects_identity_maps_pages_and_fd_inode(tmp_path):
    reader = _FixturePrivilegedReader()
    capture = _capture(tmp_path, reader)
    capture.privileged_mode = True
    identity = campaign.collect_bounded_phase(capture, reader, campaign.PHASE_IDS[0])
    assert identity.pid == 123
    assert identity.start_time_ticks == 42
    assert identity.uid == "0" and identity.gid == "0"
    assert capture.phase_identities[campaign.PHASE_IDS[0]] == identity
    correlation = json.loads((capture.output / campaign.PHASE_IDS[0] / "network" /
                              "jmcs_socket_inode_correlations.raw").read_text())
    assert correlation["attribution"] == "verified_fd_inode_match_only"
    assert correlation["owned_socket_count"] == 1
    assert correlation["sockets"][0]["fd"] == 1
    assert correlation["sockets"][0]["socket_inode"] == 55
    campaign._finalize_root_capture(capture, [campaign.PHASE_IDS[0]])
    manifest = json.loads((capture.output / "manifest.json").read_text())
    assert "no target file writes" not in manifest["guarantees"]
    assert "does not prove zero target-side effects" in manifest["target_side_effect_assessment"]
    analysis = campaign.analyze_privileged_capture(capture.output, [campaign.PHASE_IDS[0]])
    summary = analysis["phases"][campaign.PHASE_IDS[0]]
    assert summary["target_page_size"] == 4096
    assert "libcarplay_proxy.so" in summary["runtime_dependency_comparison"]["saved_elf_needed_names"]
    assert "do not prove runtime loading" in summary["runtime_dependency_comparison"]["interpretation"]


def test_r3_phase_controller_requires_owner_transitions_and_preserves_identity(tmp_path):
    reader = _FixturePrivilegedReader()
    capture = _capture(tmp_path, reader)
    steps = iter(("BASELINE", "CONNECTED", "DISCONNECTED", "RESTORED"))
    campaign.run_r3_interactive_sequence(capture, reader, lambda _prompt: next(steps), lambda _line: None)
    assert list(capture.phase_identities) == list(campaign.PHASE_IDS[1:])
    identities = list(capture.phase_identities.values())
    assert all((item.pid, item.start_time_ticks, item.executable) ==
               (identities[0].pid, identities[0].start_time_ticks, identities[0].executable)
               for item in identities)


def test_r3_wrong_owner_confirmation_stops_before_collection(tmp_path):
    reader = _FixturePrivilegedReader()
    capture = _capture(tmp_path, reader)
    with pytest.raises(collector.SafetyStop, match="owner did not confirm"):
        campaign.run_r3_interactive_sequence(capture, reader, lambda _prompt: "skip", lambda _line: None)
    assert reader.records == []


@pytest.mark.parametrize(("reader", "message"), [
    (_FixturePrivilegedReader(map_result=1), "maps failed"),
    (_FixturePrivilegedReader(map_result=124), "maps failed"),
    (_FixturePrivilegedReader(map_result=125), "maps failed"),
    (_FixturePrivilegedReader(after_start=99), "identity changed"),
    (_FixturePrivilegedReader(status_name="other"), "comm or executable"),
    (_FixturePrivilegedReader(fd_count=257), "FD count exceeds"),
])
def test_synthetic_phase_stops_on_permission_denial_or_identity_change(tmp_path, reader, message):
    capture = _capture(tmp_path, reader)
    with pytest.raises(collector.SafetyStop, match=message):
        campaign.collect_bounded_phase(capture, reader, campaign.PHASE_IDS[0])
