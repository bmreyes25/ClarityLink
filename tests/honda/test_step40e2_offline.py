from pathlib import Path
import hashlib
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "honda-readonly-preflight"
sys.path.insert(0, str(TOOLS))

import bundle_inventory
import collector
import analyze
import privileged
import privileged_session
import session
from parsers import (correlate_process_socket_endpoints, summarize_diagnostic_logs,
                     validate_diagnostic_log_summary)


def _adb(monkeypatch):
    monkeypatch.setattr(collector.shutil, "which", lambda name: "/usr/bin/adb")
    return collector.FixedAdb("TEST-DEVICE", resolve_auto=False)


def test_privileged_command_plan_is_fixed_and_uses_proven_su_c_form(monkeypatch):
    adb = _adb(monkeypatch)
    reader = privileged.PrivilegedRead(adb)
    command = reader.plan(privileged.PrivilegedOperation.PROCESS_READ,
                          pid=42, leaf="maps")
    assert command == ("/usr/bin/adb", "-s", "TEST-DEVICE", "shell", "/system/xbin/su", "-c",
                       "/system/bin/cat /proc/42/maps")
    assert "cat /proc/42/maps" in reader.dry_run_command(
        privileged.PrivilegedOperation.PROCESS_READ, pid=42, leaf="maps")


@pytest.mark.parametrize("kwargs", [
    {"pid": -1, "leaf": "maps"}, {"pid": 1, "leaf": "mem"},
    {"pid": 1, "leaf": "maps;id"}, {"pid": 1, "leaf": "maps", "command": "id"},
])
def test_privileged_allowlist_rejects_unreviewed_operations_and_injection(monkeypatch, kwargs):
    reader = privileged.PrivilegedRead(_adb(monkeypatch))
    with pytest.raises((collector.SafetyStop, TypeError)):
        reader.plan(privileged.PrivilegedOperation.PROCESS_READ, **kwargs)
    with pytest.raises(collector.SafetyStop):
        reader.run("shell", "id")


@pytest.mark.parametrize(("stdout", "code", "ok"), [
    (b"uid=0(root) gid=0(root) groups=0\n", 0, True),
    (b"uid=2000(shell) gid=2000(shell)\n", 0, False),
    (b"uid=0(root) gid=0(root)\n", 1, False),
    (b"", 127, False),
])
def test_root_identity_must_be_exactly_zero(monkeypatch, stdout, code, ok):
    reader = privileged.PrivilegedRead(_adb(monkeypatch))
    monkeypatch.setattr(reader, "run", lambda *args, **kwargs: (code, stdout, b""))
    if ok:
        assert reader.verify_root()[1] == stdout
    else:
        with pytest.raises(collector.SafetyStop):
            reader.verify_root()


def test_base64_kernel_config_requires_valid_gzip_header():
    import base64
    with pytest.raises(collector.SafetyStop):
        privileged.decode_config_base64(b"not-base64!")
    with pytest.raises(collector.SafetyStop):
        privileged.decode_config_base64(base64.b64encode(b"not gzip"))


def test_su_fingerprint_requires_exact_binary_and_nonwritable_privileged_mode():
    digest = (privileged.EXPECTED_SU_SHA256 + "  /system/xbin/su\n").encode()
    privileged.validate_su_fingerprint(digest, b"-rwsr-sr-x root root 75348 /system/xbin/su\n")
    with pytest.raises(collector.SafetyStop, match="non-writable"):
        privileged.validate_su_fingerprint(digest, b"-rwsrwsrwx root root 75348 /system/xbin/su\n")
    with pytest.raises(collector.SafetyStop, match="does not match"):
        privileged.validate_su_fingerprint(b"0" * 64 + b" /system/xbin/su\n",
                                            b"-rwsr-sr-x root root 75348 /system/xbin/su\n")


def test_live_cli_is_disabled_before_constructing_adb(monkeypatch, capsys):
    def unexpected_adb(*args, **kwargs):
        raise AssertionError("ADB must not be initialized while the offline blocker remains")
    monkeypatch.setattr(privileged_session, "FixedAdb", unexpected_adb)
    assert privileged_session.main(["--serial", "SHOULD-NOT-CONNECT"]) == 1
    output = capsys.readouterr()
    assert "Live capture is disabled" in output.err
    assert "CAPTURE STOPPED — YOU CAN TURN THE CAR OFF NOW" in output.err


def _build_bundle(root: Path):
    items = []
    for phase in ("baseline", "connected", "post-disconnect"):
        target = root / phase / "process" / "maps.raw"
        target.parent.mkdir(parents=True)
        data = b"/system/bin/sh: cat: /proc/42/maps: Permission denied\n"
        target.write_bytes(data)
        items.append({"path": str(target.relative_to(root)), "operation": "read",
                      "kind": "stdout", "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {"capture_id": "fixture", "artifacts": items}
    raw = json.dumps(manifest).encode()
    (root / "manifest.json").write_bytes(raw)
    (root / "sha256.txt").write_text("".join(
        f"{item['sha256']}  {item['path']}\n" for item in items) +
        f"{hashlib.sha256(raw).hexdigest()}  manifest.json\n")


def test_artifact_inventory_is_exhaustive_sanitized_and_hash_checked(tmp_path):
    _build_bundle(tmp_path)
    result = bundle_inventory.artifact_inventory(tmp_path)
    assert result["inventory_entry_count"] == 4
    assert result["source_artifact_count"] == 3
    assert result["hash_entries_expected"] == 4
    assert result["hash_mismatch_count"] == 0
    rows = [row for row in result["rows"] if row["artifact"].endswith("maps.raw")]
    assert all("/proc/42" not in row["artifact"] for row in rows)
    assert all(row["status"] == "permission_denied" for row in rows)
    assert all(row["hash_match"] for row in result["rows"])


def test_socket_endpoint_correlation_requires_process_fd_inode_match():
    owned = {"12": {"class": "socket", "socket_inode": 777}}
    tables = {"tcp6": [{"protocol": "tcp", "local_hex": "", "local_port": 7000,
                        "remote_hex": "", "remote_port": 0, "state": "0A", "inode": 777}],
              "tcp4": [{"protocol": "tcp", "local_hex": "", "local_port": 9000,
                        "remote_hex": "", "remote_port": 0, "state": "0A", "inode": 888}]}
    matches = correlate_process_socket_endpoints(owned, tables, ())
    assert len(matches) == 1
    assert matches[0]["fd"] == 12
    assert matches[0]["socket_inode"] == 777
    assert matches[0]["ownership_evidence"] == "jmcs_fd_symlink_inode_match"
    assert matches[0]["endpoint"]["table"] == "tcp6"
    assert matches[0]["endpoint"]["local_port"] == 7000
    assert correlate_process_socket_endpoints({}, tables, ()) == ()


def test_log_summary_discards_source_lines_and_does_not_overclaim_type111():
    raw = (b"10-30 12:34:56.123 I Receiver: AirPlayCopyServerInfo session connected\n"
           b"10-30 12:34:57.123 I Receiver: SETUP accepted PRIVATE_SENTINEL\n"
           b"10-30 12:34:58.123 I Receiver: <plist>private payload</plist>\n")
    summary = summarize_diagnostic_logs(raw)
    encoded = json.dumps(summary)
    assert summary["type111_status"] == "TYPE111_NOT_OBSERVED_IN_AVAILABLE_LOGS"
    assert summary["event_counts"]["info_boundary"] == 1
    assert summary["event_counts"]["setup_boundary"] == 1
    assert summary["event_counts"]["receiver_session"] == 1
    assert summary["input_line_count"] == 3
    assert "password" not in encoded
    assert "private payload" not in encoded
    assert "AirPlayCopyServerInfo" not in encoded
    assert "protocol negotiation" in summary["interpretation_limit"]


def test_log_summary_marks_type111_mention_without_claiming_request():
    summary = summarize_diagnostic_logs(b"I Receiver: diagnostic mentions Type111\n")
    assert summary["type111_status"] == "TYPE111_MENTIONED_IN_AVAILABLE_LOGS"
    assert "negotiation" in summary["interpretation_limit"]


def test_capture_analysis_embeds_only_redacted_log_summary(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"process_identities": {}}))
    logs = tmp_path / "baseline" / "logs"
    logs.mkdir(parents=True)
    (logs / "logcat_tail.raw").write_bytes(
        b"10-30 12:34:57.123 I Receiver: SETUP accepted SENSITIVE_SENTINEL\n")
    process = tmp_path / "baseline" / "process"
    process.mkdir()
    (process / "fd_links.raw").write_text("lr-x------ 1 root root 64 Oct 30 12:00 12\n")
    (process / "fd_12_target.raw").write_bytes(
        b"lrwx------ 1 root root 64 Oct 30 12:00 /proc/42/fd/12 -> socket:[777]\n")
    network = tmp_path / "baseline" / "network"
    network.mkdir()
    (network / "tcp6.raw").write_text(
        "  sl  local_address                         remote_address                        st tx_queue:rx_queue tr:tm->when retrnsmt uid timeout inode\n"
        "   0: 00000000000000000000000000000000:1B58 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000 1000 0 777 1 0000000000000000 100 0 0 10 0\n")
    result = analyze.analyze_phase(tmp_path, "baseline")
    output = json.dumps(result)
    assert result["log_event_summary"]["type111_status"] == "TYPE111_NOT_OBSERVED_IN_AVAILABLE_LOGS"
    assert len(result["process_owned_socket_endpoints"]) == 1
    assert result["process_owned_socket_endpoints"][0]["fd"] == 12
    assert result["process_owned_socket_endpoints"][0]["endpoint"]["table"] == "tcp6"
    assert result["process_owned_socket_endpoints"][0]["endpoint"]["local_port"] == 7000
    assert "do-not-export" not in output
    assert "SETUP accepted" not in output


def test_capture_analysis_rejects_oversized_log_before_reading_contents(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"process_identities": {}}))
    logs = tmp_path / "baseline" / "logs"
    logs.mkdir(parents=True)
    (logs / "logcat_tail.raw").write_bytes(b"x" * (4 * 1024 * 1024 + 1))
    result = analyze.analyze_phase(tmp_path, "baseline")
    assert result["log_event_summary"]["status"] == "over_limit"
    assert result["log_event_summary"]["type111_status"] == "LOGS_OVER_LIMIT"


def test_capture_filters_log_lines_before_persisting_artifacts(tmp_path):
    secret_log = b"I Receiver: SETUP accepted NEVER_PERSIST_SENTINEL\n"
    secret_stderr = b"sensitive error detail\n"

    class FakeReader:
        serial = "SYNTHETIC"

        def __init__(self):
            self.records = []

        def run(self, operation, **kwargs):
            assert operation == "logcat"
            self.records.append({"operation": operation, "result": "success"})
            return 0, secret_log, secret_stderr

    reader = FakeReader()
    capture = collector.Capture(reader, tmp_path / "private-capture")
    capture.store_log_summary("baseline")
    persisted = b"".join(path.read_bytes() for path in (tmp_path / "private-capture").rglob("*.*")
                         if path.is_file())
    summary_path = tmp_path / "private-capture" / "baseline" / "logs" / "log_event_summary.raw"
    summary = json.loads(summary_path.read_text())
    assert summary["event_counts"]["setup_boundary"] == 1
    assert b"NEVER_PERSIST_SENTINEL" not in persisted
    assert b"sensitive error detail" not in persisted
    assert not list((tmp_path / "private-capture").rglob("*.stderr.raw"))
    assert summary_path.stat().st_mode & 0o777 == 0o600


def test_generic_capture_store_rejects_raw_logcat_before_command_execution(tmp_path):
    class FakeReader:
        serial = "SYNTHETIC"
        records = []

        def run(self, *args, **kwargs):
            raise AssertionError("raw logcat must be blocked before execution")

    capture = collector.Capture(FakeReader(), tmp_path / "capture")
    with pytest.raises(collector.SafetyStop, match="raw logcat persistence is disabled"):
        capture.store("baseline", "logs", "raw", "logcat")


def test_live_collector_rejects_auto_serial_before_adb_initialization(monkeypatch, capsys):
    def unexpected_adb(*args, **kwargs):
        raise AssertionError("live auto selection must not enumerate ADB devices")

    monkeypatch.setattr(collector, "FixedAdb", unexpected_adb)
    result = collector.main(["--serial", "auto", "--vehicle-parked-confirmed",
                             "--iphone-disconnected-confirmed"])
    assert result == 2
    assert "exact pre-authorized --serial" in capsys.readouterr().err


def test_analyzer_allowlists_fields_from_persisted_log_summary(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"process_identities": {}}))
    logs = tmp_path / "baseline" / "logs"
    logs.mkdir(parents=True)
    (logs / "log_event_summary.raw").write_text(json.dumps({
        "status": "available",
        "event_counts": {"setup_boundary": 1, "private_secret": 1},
        "event_timestamp_first_seen_last_seen": {},
        "type111_status": "TYPE111_NOT_OBSERVED_IN_AVAILABLE_LOGS",
        "unrecognized_payload": "never-propagate-this",
    }))
    result = analyze.analyze_phase(tmp_path, "baseline")
    encoded = json.dumps(result)
    assert result["log_event_summary"]["event_counts"] == {"setup_boundary": 1}
    assert "never-propagate-this" not in encoded
    assert "private_secret" not in encoded


@pytest.mark.parametrize("mutation", ["contradictory_type111", "too_many_lines"])
def test_log_summary_validator_rejects_inconsistent_evidence(mutation):
    summary = {
        "status": "available",
        "event_counts": {},
        "event_timestamp_first_seen_last_seen": {},
        "type111_status": "TYPE111_NOT_OBSERVED_IN_AVAILABLE_LOGS",
        "input_line_count": 2,
    }
    if mutation == "contradictory_type111":
        summary["event_counts"] = {"type111_mention": 1}
    else:
        summary["input_line_count"] = 5001
    with pytest.raises(ValueError):
        validate_diagnostic_log_summary(summary)


@pytest.mark.parametrize("raw", [b"x" * (4 * 1024 * 1024 + 1), b"x\n" * 5001,
                                  b"x\r" * 5001])
def test_log_summary_rejects_over_limit_input(raw):
    with pytest.raises(ValueError, match="limit"):
        summarize_diagnostic_logs(raw)


def test_session_success_prints_exact_completion_message_and_finalizes():
    calls, output, prompts = [], [], []
    def input_fn(prompt):
        prompts.append(prompt)
        return ""
    complete = session.run_three_phase_session(
        verify_preflight=lambda: calls.append("preflight"),
        collect_phase=lambda phase: calls.append(phase),
        finalize=lambda succeeded: calls.append(("finalize", succeeded)),
        input_fn=input_fn, output_fn=output.append)
    assert complete is True
    assert calls == ["preflight", "baseline", "connected", "post-disconnect", ("finalize", True)]
    assert prompts[0].startswith("PHASE A")
    assert "CENTER DISPLAY" in prompts[1]
    assert output[-1] == session.SUCCESS_MESSAGE
    assert "CAPTURE COMPLETE — YOU CAN TURN THE CAR OFF NOW" in output[-1]


@pytest.mark.parametrize(("fail_at", "message"), [
    ("preflight", "ADB unavailable / wrong target / root unavailable / wrong UID"),
    ("baseline", "maps denied / smaps absent / command unavailable / timeout / output limit"),
    ("connected", "thread disappeared / PID restart / start-time changed / FD denied"),
    ("post-disconnect", "network table absent / disconnect mid-phase"),
])
def test_simulated_session_failures_stop_and_emit_abort_car_off_message(fail_at, message):
    calls, output = [], []
    def preflight():
        calls.append("preflight")
        if fail_at == "preflight":
            raise collector.SafetyStop(message)
    def collect(phase):
        calls.append(phase)
        if fail_at == phase:
            raise collector.SafetyStop(message)
    complete = session.run_three_phase_session(
        verify_preflight=preflight, collect_phase=collect,
        finalize=lambda success: calls.append(("finalize", success)),
        input_fn=lambda prompt: "", output_fn=output.append)
    assert complete is False
    assert calls[-1] == ("finalize", False)
    assert output[-2] == session.ABORT_MESSAGE
    assert "CAPTURE STOPPED — YOU CAN TURN THE CAR OFF NOW" in output[-2]


def test_hash_finalization_failure_emits_abort_and_attempts_final_manifest():
    calls, output = [], []
    def finalize(success):
        calls.append(success)
        if success:
            raise OSError("hash finalization failure")
    result = session.run_three_phase_session(
        verify_preflight=lambda: None, collect_phase=lambda _: None,
        finalize=finalize, input_fn=lambda _: "", output_fn=output.append)
    assert result is False
    assert calls == [True, False]
    assert output[-2] == session.ABORT_MESSAGE


def test_campaign_controller_runs_fixed_phases_and_keeps_hondahack_separate():
    calls, output = [], []
    result = session.run_diagnostic_campaign(
        verify_preflight=lambda: calls.append("preflight"),
        collect_phase=lambda phase: calls.append(phase),
        finalize=lambda success, failure: calls.append(("finalize", success, failure)),
        input_fn=lambda prompt: "",
        output_fn=output.append,
    )
    assert result is True
    assert calls == ["preflight", "baseline", "connected", "navigation_selected",
                     "navigation_deselected", "navigation_reselected", "post_disconnect",
                     "restoration", ("finalize", True, None)]
    assert "HondaHack" not in " ".join(output)


def test_campaign_controller_stops_on_failure_without_starting_next_phase():
    calls, output = [], []
    def collect(phase):
        calls.append(phase)
        if phase == "navigation_selected":
            raise collector.SafetyStop("unexpected page transition")
    result = session.run_diagnostic_campaign(
        verify_preflight=lambda: calls.append("preflight"),
        collect_phase=collect,
        finalize=lambda success, failure: calls.append(("finalize", success, failure)),
        input_fn=lambda prompt: "",
        output_fn=output.append,
    )
    assert result is False
    assert calls == ["preflight", "baseline", "connected", "navigation_selected",
                     ("finalize", False, "navigation_selected:SafetyStop")]
    assert any("OWNER DECISION REQUIRED" in line for line in output)
    assert output[-1] == session.ABORT_MESSAGE


def test_campaign_controller_requires_separate_hondahack_gate():
    calls, output = [], []
    result = session.run_diagnostic_campaign(
        verify_preflight=lambda: calls.append("preflight"),
        collect_phase=lambda phase: calls.append(phase),
        finalize=lambda success, failure: calls.append(("finalize", success, failure)),
        include_hondahack=True,
        hondahack_separately_authorized=False,
        input_fn=lambda prompt: "",
        output_fn=output.append,
    )
    assert result is False
    assert calls == []
    assert "separate approval" in output[0]
