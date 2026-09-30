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
import privileged
import privileged_session
import session


def _adb(monkeypatch):
    monkeypatch.setattr(collector.shutil, "which", lambda name: "/usr/bin/adb")
    return collector.FixedAdb("TEST-DEVICE", resolve_auto=False)


def test_privileged_command_plan_is_fixed_and_uses_proven_su_c_form(monkeypatch):
    adb = _adb(monkeypatch)
    reader = privileged.PrivilegedRead(adb)
    command = reader.plan(privileged.PrivilegedOperation.PROCESS_READ,
                          pid=42, leaf="maps")
    assert command == ("/usr/bin/adb", "-s", "TEST-DEVICE", "shell", "/system/xbin/su", "-c",
                       "cat /proc/42/maps")
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
