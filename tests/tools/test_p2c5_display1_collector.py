"""P2-C5 collector tests inject fake ADB only; no device discovery occurs."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "p2c5_collector", ROOT / "tools/p2c5_display1_collector.py")
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class FakeAdb:
    def __init__(self, fault=None):
        self.fault = fault
        self.calls = []
        self.responses = ["device\n", "uid=2000(shell) gid=2000(shell)\n", "17\n",
                          "DISPLAY MANAGER STATE\nDisplay 1: HDMI 800 x 480\n"]

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        index = len(self.calls) - 1
        if self.fault == "timeout" and index == 3:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        if self.fault == "transport" and index == 0:
            return subprocess.CompletedProcess(command, 1, "", "offline\n")
        if self.fault == "uid" and index == 1:
            return subprocess.CompletedProcess(command, 0, "uid=0(root)\n", "")
        if self.fault == "stderr" and index == 3:
            return subprocess.CompletedProcess(command, 0, self.responses[index], "warning\n")
        if self.fault == "empty" and index == 3:
            return subprocess.CompletedProcess(command, 0, "", "")
        if self.fault == "api" and index == 2:
            return subprocess.CompletedProcess(command, 0, "19\n", "")
        return subprocess.CompletedProcess(command, 0, self.responses[index], "")


def auth():
    return (collector.sha256(collector.MANIFEST), collector.sha256(Path(collector.__file__)))


def test_default_and_dry_run_make_zero_adb_calls(capsys):
    calls = []
    assert collector.main([], runner=lambda *a, **k: calls.append((a, k))) == 2
    assert "NOT_AUTHORIZED" in capsys.readouterr().err
    assert collector.main(["--dry-run"], runner=lambda *a, **k: calls.append((a, k))) == 0
    assert "DRY_RUN_NO_ADB" in capsys.readouterr().out
    assert calls == []


def test_exact_read_only_sequence_and_private_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "EVIDENCE_DIR", tmp_path / "evidence")
    fake = FakeAdb()
    manifest_hash, collector_hash = auth()
    output = collector.execute("HONDA-EXACT:5555", "P2C5-ONE-SHOT", manifest_hash,
                               collector_hash, tmp_path / "evidence" / "result.json", fake)
    assert [call[0] for call in fake.calls] == [
        ["adb", "-s", "HONDA-EXACT:5555", "get-state"],
        ["adb", "-s", "HONDA-EXACT:5555", "shell", "id"],
        ["adb", "-s", "HONDA-EXACT:5555", "shell", "getprop", "ro.build.version.sdk"],
        ["adb", "-s", "HONDA-EXACT:5555", "shell", "dumpsys", "display"],
    ]
    assert len(fake.calls) == 4
    assert all(call[1]["timeout"] == 12 for call in fake.calls)
    assert output["classification"] == "DISPLAY_ENUMERATION_RAW_ONLY"
    assert output["window_admission"] == output["visible_rendering"] == "NOT_TESTED"
    assert output["target_writes"] == output["display_operations"] == output["retries"] == 0
    assert (tmp_path / "evidence" / "result.json").stat().st_mode & 0o777 == 0o600
    assert json.loads((tmp_path / "evidence" / "result.json").read_text()) == output


@pytest.mark.parametrize("fault,stop_after", [
    ("transport", 1), ("uid", 2), ("api", 3), ("stderr", 4), ("empty", 4), ("timeout", 4),
])
def test_failure_stops_without_retry_or_evidence(tmp_path, monkeypatch, fault, stop_after):
    monkeypatch.setattr(collector, "EVIDENCE_DIR", tmp_path / "evidence")
    fake = FakeAdb(fault=fault)
    manifest_hash, collector_hash = auth()
    destination = tmp_path / "evidence" / "evidence.json"
    with pytest.raises(collector.Stop):
        collector.execute("HONDA-EXACT:5555", "P2C5-ONE-SHOT", manifest_hash,
                          collector_hash, destination, fake)
    assert len(fake.calls) == stop_after
    assert all(call[1]["timeout"] == 12 for call in fake.calls)
    assert not destination.exists()


def test_invalid_serial_or_package_hash_fails_before_adb(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "EVIDENCE_DIR", tmp_path / "evidence")
    fake = FakeAdb()
    manifest_hash, collector_hash = auth()
    with pytest.raises(collector.Stop):
        collector.execute("auto", "P2C5-ONE-SHOT", manifest_hash, collector_hash,
                          tmp_path / "evidence" / "x", fake)
    with pytest.raises(collector.Stop):
        collector.execute("HONDA-EXACT:5555", "P2C5-ONE-SHOT", "0" * 64,
                          collector_hash, tmp_path / "evidence" / "x", fake)
    assert fake.calls == []


def test_missing_fresh_confirmations_cannot_execute(capsys):
    fake = FakeAdb()
    result = collector.main(["--execute-authorized-p2c5", "--serial", "HONDA-EXACT:5555"],
                            runner=fake)
    assert result == 2
    assert "MISSING_FRESH_OPERATOR_CONFIRMATION" in capsys.readouterr().err
    assert fake.calls == []


def test_machine_schema_keeps_enumeration_separate_from_admission():
    schema = json.loads((ROOT / "research/architecture/p2c5-display-observation.schema.json").read_text())
    properties = schema["properties"]
    assert properties["classification"]["const"] == "DISPLAY_ENUMERATION_RAW_ONLY"
    assert properties["window_admission"]["const"] == "NOT_TESTED"
    assert properties["visible_rendering"]["const"] == "NOT_TESTED"
    assert properties["target_writes"]["const"] == 0
    assert properties["commands_executed"]["const"] == 4
