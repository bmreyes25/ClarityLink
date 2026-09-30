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
    assert "exec-out" in adb.plan("read", ("/proc/version",))
    with pytest.raises(collector.SafetyStop):
        adb.plan("read", ("/proc/1234/mem",))
    with pytest.raises(collector.SafetyStop):
        adb.plan("read", ("/proc/1234/environ",))
    with pytest.raises(collector.SafetyStop):
        adb.plan("shell", ("echo", "bad"))
    with pytest.raises(collector.SafetyStop):
        adb.plan("read", ("/data/local/tmp/probe",))


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
    assert "exec-out shell" in output


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


def json_dumps(value):
    import json
    return json.dumps(value)
