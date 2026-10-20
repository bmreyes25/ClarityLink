"""Offline-only Phase S contract and failure-injection tests."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import subprocess

import pytest

from tests.tools.local_tool_gate import require_local_tools

require_local_tools(__file__, "r7e7i_clock_attestation.py")

from tools import r7e7i_phase_s_collector as s


UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
BOOT = "aa12bc34-de56-4f78-9012-34567890abcd"
VERSION = ("Android Debug Bridge version 1.0.41\n"
           "Version 37.0.1-15733141\n"
           "Installed as /usr/bin/adb\n"
           "Running on Darwin 27.2.0 (arm64)\n")


class FakeADB:
    def __init__(self, mutation: str = "", stage: int = -1, uptime: str = "100.00 50.00\r\n"):
        self.calls: list[list[str]] = []
        self.mutation = mutation
        self.stage = stage
        self.uptime = uptime

    def __call__(self, argv: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        index = len(self.calls)
        normalized = argv[1:].copy()
        if normalized[:2] == ["-s", "TESTSER"]:
            normalized[1] = "<EXACT_SERIAL>"
        assert argv[0] == "adb"
        assert index < 5 and normalized == s.command_plan()[index]
        assert kwargs["timeout"] == 12
        self.calls.append(argv.copy())
        if index == self.stage and self.mutation == "timeout":
            raise subprocess.TimeoutExpired(argv, 12, output=b"partial")
        responses = [VERSION, "List of devices attached\nTESTSER\tdevice\n",
                     BOOT + "\r\n", self.uptime, BOOT + "\r\n"]
        out, err, rc = responses[index], "", 0
        if index == self.stage:
            if self.mutation == "wrong_version": out = out.replace(s.ADB_VERSION, "0.0.0")
            if self.mutation == "extra_version": out += "unexpected\n"
            if self.mutation == "wrong_device": out = out.replace("TESTSER", "OTHER")
            if self.mutation == "multiple_devices": out += "OTHER\tdevice\n"
            if self.mutation == "missing_boot_id": out = "cat: not found\n"
            if self.mutation == "bad_boot_id": out = "00000000-0000-0000-0000-000000000000\n"
            if self.mutation == "boot_conflict": out = "bb12bc34-de56-4f78-9012-34567890abcd\n"
            if self.mutation == "malformed_uptime": out = "unknown\n"
            if self.mutation == "unavailable_uptime": out, err, rc = "", "Permission denied\n", 1
            if self.mutation == "stderr": err = "unexpected warning\n"
            if self.mutation == "empty": out = ""
        assert "rm" not in argv and "push" not in argv
        assert not any("claritylink-target-diag" in arg for arg in argv)
        return subprocess.CompletedProcess(argv, rc, out, err)


@pytest.fixture
def package(tmp_path, monkeypatch):
    monkeypatch.setattr(s, "ROOT", tmp_path)
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/r7e7i_clock_attestation.py").write_text("synthetic test validator\n")
    old = tmp_path / "old.json"
    old.write_text(json.dumps({"decision": "TEST_A_PROCESS_STATE_UNCERTAIN",
                               "finished_utc": s.OLD_FINISHED_UTC,
                               "diagnostic_started": True}))
    phase_r = tmp_path / "phase-r.json"
    phase_r.write_text(json.dumps({
        "phase_r_decision": "EXPECTED_REGULAR_FILE_PRESENT",
        "process_safety_established": False,
        "remote_file_classification": {
            "status": "EXPECTED_REGULAR_FILE_PRESENT", "mode": "0555",
            "owner_group": "shell:shell", "size": 7904,
            "md5": s.ARTIFACT_MD5, "identity_verified_by_md5": True},
        "package": {"expected_executable_sha256": s.ARTIFACT_SHA256},
        "raw_collector_evidence": {"path": s.REMOTE},
    }))
    monkeypatch.setattr(s, "OLD_EVIDENCE", old)
    monkeypatch.setattr(s, "PHASE_R_EVIDENCE", phase_r)
    monkeypatch.setattr(s, "OLD_EVIDENCE_SHA256", s.sha(old))
    monkeypatch.setattr(s, "PHASE_R_EVIDENCE_SHA256", s.sha(phase_r))
    manifest = tmp_path / "manifest.json"
    expected = s.manifest_template()
    expected["collector_source_sha256"] = s.sha(Path(s.__file__))
    manifest.write_text(json.dumps(expected))
    monkeypatch.setattr(s, "MANIFEST", manifest)
    clock = tmp_path / "clock.json"
    clock.write_text(json.dumps({
        "schema_version": "R7E7I-CLOCK-ATTESTATION-2",
        "attestation_id": "TEST-ONLY-SYNTHETIC-FIXTURE",
        "issued_utc": "2026-10-12T00:00:00+00:00",
        "expires_utc": "2026-10-16T00:00:00+00:00",
        "historical": {"conservative_error_seconds": 3600},
        "current": {"conservative_error_seconds": 60},
    }))
    clock.chmod(0o600)
    monkeypatch.setattr(s, "CLOCK_ATTESTATION", clock)
    monkeypatch.setattr(s, "CLOCK_SIGNATURE", tmp_path / "clock.json.asc")
    def validate_test_fixture(*_args, **_kwargs):
        data = json.loads(clock.read_text())
        if data["historical"]["conservative_error_seconds"] < s.MIN_HISTORICAL_ERROR_SECONDS:
            raise s.clock_attestation.AttestationError("synthetic narrow-bound fixture")
        return {"decision": "TEST_FIXTURE_ONLY",
                "historical_error_seconds": data["historical"]["conservative_error_seconds"],
                "current_error_seconds": data["current"]["conservative_error_seconds"],
                "expires_utc": data["expires_utc"]}
    monkeypatch.setattr(s.clock_attestation, "validate", validate_test_fixture)
    return s.parser().parse_args([
        "--execute-authorized-phase-s", "--authorized-collector-sha256",
        s.sha(Path(s.__file__)), "--authorized-manifest-sha256", s.sha(manifest),
        "--authorized-clock-attestation-sha256", s.sha(clock),
        "--clock-reviewer-keyring", str(tmp_path / "reviewers.gpg"),
        "--clock-reviewer-fingerprint", "A" * 40,
        "--serial", "TESTSER", "--stationary", "--parked", "--display-booted",
        "--cluster-normal", "--no-warnings", "--head-unit-confirmed",
        "--adb-stable", "--no-other-adb-issuer", "--operator-no-manual-adb",
        "--exclusive-adb-window",
    ])


def clock(start: dt.datetime = NOW, elapsed: float = 1.0):
    ticks = iter([start, start + dt.timedelta(seconds=elapsed)])
    monotonic_ticks = iter([100.0, 100.0 + elapsed])
    return lambda: next(ticks), lambda: next(monotonic_ticks)


def run(package, fake: FakeADB, start: dt.datetime = NOW, elapsed: float = 1.0):
    now, monotonic = clock(start, elapsed)
    return s.execute(package, runner=fake, now=now, monotonic=monotonic)


def saved(package):
    files = list((s.ROOT / "build/r7e7i/phase-s/evidence").glob("*.json"))
    assert len(files) == 1
    assert files[0].stat().st_mode & 0o777 == 0o600
    return json.loads(files[0].read_text())


def test_default_and_dry_run_zero_adb(monkeypatch, capsys):
    monkeypatch.setattr(s.subprocess, "run", lambda *_a, **_k: pytest.fail("ADB called"))
    assert s.main([]) == 0
    assert s.main(["--dry-run"]) == 0
    assert '"decision": "DRY_RUN_NO_ADB"' in capsys.readouterr().out


def test_full_frozen_simulated_inspection_establishes_prior_termination(package):
    fake = FakeADB()
    assert run(package, fake) == "PREVIOUS_PROCESS_TERMINATION_ESTABLISHED"
    assert len(fake.calls) == 5
    evidence = saved(package)
    assert evidence["decision"] == "PREVIOUS_PROCESS_TERMINATION_ESTABLISHED"
    assert all(row["returncode"] == 0 and row["stderr"] == "" for row in evidence["records"])
    assert evidence["detail"]["target_identity_classification"] == "ONE_EXACT_CONFIRMED_DEVICE"
    assert not any("rm" in call or "push" in call for call in fake.calls)


def test_long_uptime_does_not_establish_termination(package):
    fake = FakeADB(uptime="500000.00 800000.00\n")
    assert run(package, fake) == "PROCESS_POSSIBLY_ACTIVE"
    assert len(fake.calls) == 5


@pytest.mark.parametrize("stage,mutation,decision", [
    (0, "wrong_version", "INSPECTION_IDENTITY_MISMATCH"),
    (0, "extra_version", "INSPECTION_IDENTITY_MISMATCH"),
    (1, "wrong_device", "INSPECTION_IDENTITY_MISMATCH"),
    (1, "multiple_devices", "INSPECTION_IDENTITY_MISMATCH"),
    (2, "missing_boot_id", "BOOT_CONTINUITY_UNKNOWN"),
    (2, "bad_boot_id", "BOOT_CONTINUITY_UNKNOWN"),
    (3, "malformed_uptime", "BOOT_CONTINUITY_UNKNOWN"),
    (3, "unavailable_uptime", "UNEXPECTED_COMMAND_RESPONSE"),
    (4, "boot_conflict", "PROCESS_EVIDENCE_CONFLICT"),
    (3, "stderr", "UNEXPECTED_COMMAND_RESPONSE"),
    (3, "empty", "BOOT_CONTINUITY_UNKNOWN"),
    (3, "timeout", "INSPECTION_TIMEOUT"),
])
def test_failure_injection_stops_at_exact_command(package, stage, mutation, decision):
    fake = FakeADB(mutation=mutation, stage=stage)
    assert run(package, fake) == decision
    assert len(fake.calls) == stage + 1
    assert saved(package)["decision"] == decision


@pytest.mark.parametrize("stage", [0, 1, 2, 4])
def test_every_other_command_timeout_stops_without_retry(package, stage):
    fake = FakeADB(mutation="timeout", stage=stage)
    assert run(package, fake) == "INSPECTION_TIMEOUT"
    assert len(fake.calls) == stage + 1
    assert saved(package)["decision"] == "INSPECTION_TIMEOUT"


@pytest.mark.parametrize("mutation", ["collector_hash", "manifest_hash", "clock_hash",
                                      "wrong_serial", "missing_parked", "adb_override",
                                      "prior_evidence", "phase_r_evidence", "manifest_content",
                                      "missing_reviewer", "bad_attestation_signature",
                                      "clock_expired", "narrow_clock_bound"])
def test_preflight_failure_never_calls_adb(package, mutation, monkeypatch):
    if mutation == "collector_hash": package.authorized_collector_sha256 = "0" * 64
    if mutation == "manifest_hash": package.authorized_manifest_sha256 = "0" * 64
    if mutation == "clock_hash": package.authorized_clock_attestation_sha256 = "0" * 64
    if mutation == "wrong_serial": package.serial = "bad serial"
    if mutation == "missing_parked": package.parked = False
    if mutation == "adb_override": package.adb = "/bin/true"
    if mutation == "prior_evidence": s.OLD_EVIDENCE.write_text("{}")
    if mutation == "phase_r_evidence": s.PHASE_R_EVIDENCE.write_text("{}")
    if mutation == "manifest_content":
        manifest = json.loads(s.MANIFEST.read_text())
        manifest["commands"] = [["version"]]
        s.MANIFEST.write_text(json.dumps(manifest))
        package.authorized_manifest_sha256 = s.sha(s.MANIFEST)
    if mutation == "missing_reviewer": package.clock_reviewer_fingerprint = None
    if mutation == "bad_attestation_signature":
        def reject_signature(*_args, **_kwargs):
            raise s.clock_attestation.AttestationError("synthetic invalid signature")
        monkeypatch.setattr(s.clock_attestation, "validate", reject_signature)
    if mutation == "narrow_clock_bound":
        attestation = json.loads(s.CLOCK_ATTESTATION.read_text())
        attestation["historical"]["conservative_error_seconds"] = 0
        s.CLOCK_ATTESTATION.write_text(json.dumps(attestation))
        package.authorized_clock_attestation_sha256 = s.sha(s.CLOCK_ATTESTATION)
    fake = FakeADB()
    start = dt.datetime(2026, 10, 17, tzinfo=UTC) if mutation == "clock_expired" else NOW
    with pytest.raises(s.PhaseSStop):
        run(package, fake, start=start)
    assert fake.calls == []


def test_clock_step_conflict_and_ambiguous_time(package):
    fake = FakeADB()
    now, _ = clock(elapsed=10.0)
    monotonic_ticks = iter([100.0, 101.0])
    assert s.execute(package, runner=fake, now=now,
                     monotonic=lambda: next(monotonic_ticks)) == "PROCESS_EVIDENCE_CONFLICT"
    assert len(fake.calls) == 5


def test_timestamp_overlap_cannot_prove_reboot():
    prior = dt.datetime.fromisoformat(s.OLD_FINISHED_UTC)
    result, margin = s.classify_boot(prior, prior + dt.timedelta(hours=2),
                                     3600.0, 3600, 60)
    assert result == "PROCESS_POSSIBLY_ACTIVE"
    assert margin < 0


def test_pid_reuse_and_guest_clock_cannot_enter_proof():
    plan = s.command_plan()
    assert len(plan) == 5
    assert all("/proc/stat" not in row and "/proc/self" not in row for row in plan)
    assert all("ps" not in row and "kill" not in row for row in plan)
    assert all("/proc/uptime" not in row for row in plan[:3])
