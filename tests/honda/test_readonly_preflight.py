from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "honda-readonly-preflight"))

import analyze
import collector
import parsers
import pytest


def test_maps_parser_preserves_paths_with_spaces_and_permissions():
    maps = parsers.parse_maps(
        "40000000-40001000 r-xp 00000000 1f:02 42 /system/bin/jmcs\n"
        "40001000-40002000 rw-p 00001000 1f:02 42 /data/app/lib with spaces.so\n")
    assert maps[0].start == 0x40000000
    assert maps[0].permissions == "r-xp"
    assert maps[1].pathname.endswith("lib with spaces.so")
    assert maps[1].inode == 42


def test_maps_rejects_malformed_intervals():
    with pytest.raises(ValueError):
        parsers.parse_maps("40001000-40000000 rw-p 0 00:00 0")


def test_smaps_parser_reads_page_fields_and_vmflags_when_exposed():
    entries = parsers.parse_smaps(
        "40000000-40001000 r-xp 00000000 1f:02 42 /system/bin/jmcs\n"
        "Size:                  4 kB\nKernelPageSize:        4 kB\nMMUPageSize:           4 kB\n"
        "VmFlags: rd ex mr mw me\n")
    assert entries[0].fields["KernelPageSize"] == "4 kB"
    assert entries[0].fields["VmFlags"] == "rd ex mr mw me"


def test_status_and_linux_arm_signal_masks_decode_without_host_signal_abi():
    status = parsers.parse_status("Name:\tjmcs\nSigBlk:\t0000000000000002\nSigCgt:\t0000000080000000\n")
    assert parsers.decode_signal_mask(status["SigBlk"]) == ("2:INT",)
    assert parsers.decode_signal_mask(status["SigCgt"]) == ("32:RTMIN+0",)
    assert parsers.parse_thread_status("Name:\tRender\nState:\tS (sleeping)\n") == {
        "Name": "Render", "State": "S (sleeping)"}


def test_proc_stat_parser_handles_spaces_and_parenthesis_in_comm():
    fields = ["S"] + [str(n) for n in range(4, 23)]
    stat = "123 (jmcs (worker)) " + " ".join(fields)
    assert parsers.parse_proc_stat_start_time(stat) == 22


def test_task_snapshot_listing_is_numeric_sorted_and_unique():
    assert parsers.parse_task_listing("42\n7\n10\n") == (7, 10, 42)
    with pytest.raises(ValueError):
        parsers.parse_task_listing("42\n42\n")


def test_proc_tcp_table_decodes_little_endian_ipv4_and_inode():
    rows = "sl local_address rem_address st tx_queue:rx_queue tr:tm->when retrnsmt uid timeout inode\n"
    rows += "0: 0100007F:1388 0200007F:01BB 01 0:0 00:0 0 0 0 12345\n"
    sockets = parsers.parse_proc_net(rows, "tcp", 4)
    assert (sockets[0].local_hex, sockets[0].local_port) == ("127.0.0.1", 5000)
    assert sockets[0].remote_hex == "127.0.0.2"
    assert sockets[0].inode == 12345


def test_proc_tcp6_table_decodes_four_little_endian_words():
    rows = "sl local_address rem_address st tx_queue:rx_queue tr:tm->when retrnsmt uid timeout inode\n"
    rows += "0: 00000000000000000000000001000000:1F90 "
    rows += "00000000000000000000000001000000:01BB 0A 0:0 00:0 0 0 0 9\n"
    sockets = parsers.parse_proc_net(rows, "tcp", 6)
    assert sockets[0].local_hex == "::1"
    assert sockets[0].local_port == 8080


def test_proc_unix_sockets_parse_inode_and_optional_path():
    rows = "Num RefCount Protocol Flags Type St Inode Path\n"
    rows += "00000000: 00000003 00000000 00010000 0001 01 9876 @/dev/socket/example\n"
    sockets = parsers.parse_proc_net_unix(rows)
    assert sockets[0]["inode"] == "9876"
    assert sockets[0]["path"] == "@/dev/socket/example"


def test_thumb_ranges_mapping_gaps_and_page_candidates_are_snapshot_only():
    mappings = parsers.parse_maps(
        "10000000-10002000 r-xp 00000000 1f:02 42 /system/bin/jmcs\n"
        "10004000-10005000 rw-p 00000000 00:00 0\n")
    assert parsers.thumb_bl_range(0x28A158) == (0, 0x128A15A)
    gaps = parsers.mapping_gaps(mappings, 0x10000000, 0x10005FFF)
    assert gaps == ((0x10002000, 0x10004000), (0x10005000, 0x10006000))
    assert parsers.aligned_candidate(gaps[0], 4096) == (0x10002000, 0x10003000)


def test_load_bias_and_runtime_callsite_require_executable_mapping():
    mapping, = parsers.parse_maps("40000000-40300000 r-xp 00000000 1f:02 42 /system/bin/jmcs\n")
    assert parsers.load_bias_from_mapping(mapping, segment_offset=0, segment_vaddr=0,
                                          page_size=4096) == 0x40000000
    assert parsers.runtime_address(0x28A158, 0x40000000, (mapping,)) == 0x4028A158
    with pytest.raises(ValueError):
        parsers.runtime_address(0x40A00000, 0x40000000, (mapping,))


def test_privacy_sanitizer_redacts_common_identifiers_and_secrets():
    raw = "VIN 1HGCM82633A004352 phone=Driver token=abc123 11:22:33:44:55:66 10.1.2.3"
    clean = parsers.sanitize_summary_text(raw)
    assert "1HGCM82633A004352" not in clean
    assert "Driver" not in clean
    assert "abc123" not in clean
    assert "11:22:33:44:55:66" not in clean
    assert "10.1.2.3" not in clean


def test_fixed_adb_allowlist_rejects_writes_mem_and_arbitrary_commands():
    adb = collector.FixedAdb("SERIAL-42")
    assert adb.plan("read", ("/proc/version",))[3:] == ("shell", "cat", "/proc/version")
    assert adb.plan("list", ("/proc/1234/task",))[3:] == ("shell", "ls", "/proc/1234/task")
    with pytest.raises(collector.SafetyStop):
        adb.plan("read", ("/proc/1234/mem",))
    with pytest.raises(collector.SafetyStop):
        adb.plan("read", ("/proc/1234/environ",))
    with pytest.raises(collector.SafetyStop):
        adb.plan("shell", ("echo", "bad"))
    with pytest.raises(collector.SafetyStop):
        adb.plan("read", ("/data/local/tmp/probe",))
    assert adb.plan("readlink", ("/proc/1234/exe",))[3:] == (
        "shell", "ls", "-l", "/proc/1234/exe")


def test_ls_symlink_target_parser_handles_api17_toolbox_output():
    assert collector.parse_ls_symlink_target(
        b"lrwxrwxrwx root root 0 2026-09-29 19:00 /proc/6276/exe -> /system/bin/jmcs\r\n"
    ) == "/system/bin/jmcs"
    assert collector.parse_ls_symlink_target(b"ls: /proc/1/exe: Permission denied\n") == ""
    assert collector.classify_command_result(
        0, b"", b"", operation="readlink") == collector.CommandResult.NOT_EXPOSED


def test_auto_adb_serial_requires_exactly_one_authorized_device(monkeypatch):
    class Result:
        returncode = 0
        stdout = "List of devices attached\nSERIAL-42 device product:clarity\n"
        stderr = ""
    monkeypatch.setattr(collector.shutil, "which", lambda name: "/opt/homebrew/bin/adb")
    monkeypatch.setattr(collector.subprocess, "run", lambda *args, **kwargs: Result())
    adb = collector.FixedAdb("auto")
    assert adb.serial == "SERIAL-42"
    assert adb.records[0]["candidate_count"] == 1
    assert "SERIAL-42" not in str(adb.records)


def test_auto_adb_serial_refuses_ambiguous_devices(monkeypatch):
    class Result:
        returncode = 0
        stdout = "List of devices attached\nONE device\nTWO device\n"
        stderr = ""
    monkeypatch.setattr(collector.shutil, "which", lambda name: "/opt/homebrew/bin/adb")
    monkeypatch.setattr(collector.subprocess, "run", lambda *args, **kwargs: Result())
    with pytest.raises(collector.SafetyStop):
        collector.FixedAdb("auto")


def test_dry_run_builds_command_plan_without_invoking_adb(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("dry run attempted external execution")
    monkeypatch.setattr(collector.subprocess, "run", forbidden)
    collector.dry_run(collector.FixedAdb("SERIAL-42"))
    output = capsys.readouterr().out
    assert "SERIAL-42" in output
    assert "--dry-run" not in output
    assert "No command has been sent" in output
    assert " shell cat /proc/version" in output


@pytest.mark.parametrize(("code", "out", "err", "expected"), [
    (0, b"Linux version 3.1.10+", b"", collector.CommandResult.SUCCESS),
    (127, b"", b"/system/bin/sh: uname: not found", collector.CommandResult.COMMAND_UNAVAILABLE),
    (1, b"", b"cat: /proc/9/maps: Permission denied", collector.CommandResult.PERMISSION_DENIED),
    (255, b"", b"error: closed", collector.CommandResult.TRANSPORT_FAILURE),
    (1, b"", b"error: device offline", collector.CommandResult.TRANSPORT_FAILURE),
    (1, b"", b"error: device unauthorized", collector.CommandResult.TRANSPORT_FAILURE),
    (124, b"", b"", collector.CommandResult.TIMEOUT),
    (125, b"", b"", collector.CommandResult.OUTPUT_LIMIT),
    (2, b"", b"bad option", collector.CommandResult.OTHER_COMMAND_FAILURE),
    (124, b"", b"remote command exit", collector.CommandResult.OTHER_COMMAND_FAILURE),
])
def test_command_result_classification(code, out, err, expected):
    assert collector.classify_command_result(
        code, out, err, timed_out=expected == collector.CommandResult.TIMEOUT,
        output_limited=expected == collector.CommandResult.OUTPUT_LIMIT) == expected


def test_not_found_is_not_transport_failure():
    result = collector.classify_command_result(
        127, b"", b"/system/bin/sh: uname: not found")
    assert result == collector.CommandResult.COMMAND_UNAVAILABLE


def test_process_identity_change_is_distinguished_from_command_failure():
    assert collector.classify_stop_reason("jmcs process instance changed") == \
        collector.CommandResult.PROCESS_IDENTITY_CHANGE


def test_target_identity_requires_kernel_and_android_properties(tmp_path):
    class FakeReader:
        def __init__(self):
            self.results = {
                ("read", "/proc/version"): b"Linux version 3.1.10+ (builder) #1 SMP PREEMPT\n",
                ("property", "ro.build.version.release"): b"4.2.2\n",
                ("property", "ro.build.version.sdk"): b"17\n",
                ("property", "ro.product.device"): b"vcm30t30a\n",
                ("property", "ro.product.board"): b"Andromeda\n",
                ("property", "ro.hardware"): b"vcm30t30\n",
                ("property", "ro.product.model"): b"MY16ADA\n",
            }
        def run(self, operation, argument, **kwargs):
            return 0, self.results[(operation, argument)], b""

    capture = collector.Capture(FakeReader(), tmp_path / "capture")
    identity = capture.verify_target_identity()
    assert identity["android_release"] == "4.2.2"
    assert identity["android_sdk"] == "17"
    assert identity["kernel_version"].startswith("Linux version 3.1.10+")


def test_process_identity_uses_proc_status_cmdline_and_stat_when_exe_link_is_unexposed():
    class FakeReader:
        def __init__(self):
            self.calls = []
        def run(self, operation, argument, **kwargs):
            self.calls.append((operation, argument))
            if argument == "/proc/42/stat":
                fields = ["S"] + [str(n) for n in range(4, 23)]
                return 0, ("42 (jmcs) " + " ".join(fields)).encode(), b""
            if argument == "/proc/42/status":
                return 0, b"Name:\tjmcs\nPid:\t42\nPPid:\t1\nUid:\t0\t0\t0\t0\nGid:\t0\t0\t0\t0\n", b""
            if argument == "/proc/42/cmdline":
                return 0, b"/system/bin/jmcs\x00", b""
            raise AssertionError(f"unexpected identity operation: {operation} {argument}")

    reader = FakeReader()
    identity = collector.read_process_identity(reader, 42)
    assert identity.executable == "/system/bin/jmcs"
    assert identity.pid == 42
    assert all(operation == "read" for operation, _ in reader.calls)


def test_adb_output_limit_stops_host_client_before_unbounded_capture(monkeypatch):
    class FinishedProcess:
        def __init__(self, stdout, stderr):
            self.stdout, self.stderr = stdout, stderr
            self.killed = False
        def kill(self):
            self.killed = True
        def wait(self, timeout=None):
            return 0

    out_read, out_write = os.pipe()
    err_read, err_write = os.pipe()
    os.write(out_write, b"abcdefgh")
    os.close(out_write)
    os.close(err_write)
    fake = FinishedProcess(os.fdopen(out_read, "rb"), os.fdopen(err_read, "rb"))
    monkeypatch.setattr(collector.subprocess, "Popen", lambda *args, **kwargs: fake)
    reader = collector.FixedAdb("SERIAL-42")
    code, out, err = reader.run("read", "/proc/version", max_bytes=4)
    assert (code, out) == (125, b"abcd")
    assert b"output limit" in err
    assert fake.killed is True


def test_adb_timeout_kills_only_the_host_adb_client(monkeypatch):
    class TimedProcess:
        def __init__(self, stdout, stderr):
            self.stdout, self.stderr = stdout, stderr
            self.killed = False
        def kill(self):
            self.killed = True
        def wait(self, timeout=None):
            return -9

    out_read, out_write = os.pipe()
    err_read, err_write = os.pipe()
    fake = TimedProcess(os.fdopen(out_read, "rb"), os.fdopen(err_read, "rb"))
    monkeypatch.setattr(collector.subprocess, "Popen", lambda *args, **kwargs: fake)
    reader = collector.FixedAdb("SERIAL-42")
    code, out, err = reader.run("read", "/proc/version", timeout=0)
    os.close(out_write)
    os.close(err_write)
    assert code == 124
    assert b"timed out" in err
    assert fake.killed is True


def test_analyze_phase_uses_direct_smaps_page_and_exact_elf_bias(tmp_path):
    phase = tmp_path / "baseline"
    (phase / "process").mkdir(parents=True)
    (phase / "threads").mkdir()
    (phase / "network").mkdir()
    (phase / "platform").mkdir()
    (tmp_path / "manifest.json").write_text(json_dumps({
        "capture_id": "synthetic", "process_identities": {
            "baseline": {"pid": 10, "start_time_ticks": 55}}}))
    map_line = "40000000-4033f000 r-xp 00000000 1f:02 42 /system/bin/jmcs\n"
    (phase / "process" / "maps.raw").write_text(map_line)
    (phase / "process" / "smaps.raw").write_text(map_line + "KernelPageSize: 4 kB\nMMUPageSize: 4 kB\n")
    (phase / "process" / "status.raw").write_text("Pid:\t10\nSigBlk:\t0000000000000000\n")
    for index in range(5):
        (phase / "threads" / f"snapshot_{index:02d}_task_listing.raw").write_text("10\n")
        (phase / "threads" / f"snapshot_{index:02d}_tid_10_status.raw").write_text(
            "Name:\tjmcs\nState:\tS (sleeping)\nPid:\t10\nSigBlk:\t0000000000000000\n")
        (phase / "threads" / f"snapshot_{index:02d}_tid_10_wchan.raw").write_text("futex_wait_queue\n")
    analyzed = analyze.analyze_phase(tmp_path, "baseline")
    assert analyzed["target_page_size"] == 4096
    assert analyzed["load_bias"] == "0x40000000"
    assert analyzed["runtime_callsites"]["info"] == "0x4028a158"
    assert analyzed["thread_count_first"] == 1
    assert analyzed["thread_population_stable_within_phase"] is True
    assert analyzed["thread_snapshots"][0]["10"]["sigblk_decoded"] == ()
    (phase / "platform" / "jmcs_file_sha256.raw").write_text(
        "cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232  /system/bin/jmcs\n")
    analyzed = analyze.analyze_phase(tmp_path, "baseline")
    assert analyzed["jmcs_file_exact_pinned_build_match"] is True


def test_analyzer_preserves_proc_maps_permission_denial_as_unavailable(tmp_path):
    phase = tmp_path / "baseline"
    for category in ("process", "threads", "network", "platform", "cpu"):
        (phase / category).mkdir(parents=True)
    (phase / "process" / "maps.raw").write_text(
        "/system/bin/sh: cat: /proc/42/maps: Permission denied\n")
    (phase / "process" / "smaps.raw").write_text(
        "/system/bin/sh: cat: /proc/42/smaps: Permission denied\n")
    (phase / "threads" / "snapshot_00_task_listing.raw").write_text(
        "ls: Unknown option '-1'. Aborting.\n")
    analyzed = analyze.analyze_phase(tmp_path, "baseline")
    assert analyzed["maps_available"] is False
    assert analyzed["maps_status"] == "permission_denied"
    assert analyzed["smaps_available"] is False
    assert analyzed["smaps_status"] == "permission_denied"
    assert analyzed["target_page_size"] is None
    assert analyzed["jmcs_mappings"] == []
    assert analyzed["thread_snapshots_available"] is False
    assert analyzed["thread_population_stable_within_phase"] is False
    assert analyzed["wchan_reads_available"] is False
    assert analyzed["thread_listing_statuses"][0] == "other_command_failure"


def json_dumps(value):
    import json
    return json.dumps(value)
