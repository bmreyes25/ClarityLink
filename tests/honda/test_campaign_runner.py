"""Offline tests for the pinned parked-observation campaign harness."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "honda-readonly-preflight"
sys.path.insert(0, str(TOOLS))

import campaign_runner as campaign
import collector


def test_dry_run_is_complete_and_never_contacts_adb(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("dry-run attempted host/device process access")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(collector.shutil, "which", forbidden)
    report = campaign.dry_run_report()
    assert report["mode"] == "DRY_RUN_NO_ADB_CONTACT"
    assert report["adb_contact"] is False
    assert report["device_enumeration"] is False
    assert report["files_created"] is False
    assert report["phase_count"] == len(campaign.phases()) == 8
    assert sum(len(phase["commands"]) for phase in report["phases"]) == 135
    assert campaign.command_manifest_sha256() == campaign.BASELINE_COMMAND_MANIFEST_SHA256
    assert report["source_hash_lock"] == json.loads(campaign.SOURCE_LOCK_FILE.read_text())
    for phase in report["phases"]:
        assert phase["failure_behavior"].startswith("stop immediately")
        assert phase["artifact_destination"].startswith("<private-capture-root>")
        for command in phase["commands"]:
            assert "--serial" not in command["argv"]
            assert command["argv"][0:3] == ["adb", "-s", "EXACT_APPROVED_SERIAL"]
            assert 0 < command["timeout_seconds"] <= 20
            assert 0 < command["max_output_bytes"] <= 4 * 1024 * 1024
            assert command["expected_output"]
    assert report["optional_hondahack"].startswith("excluded")


def test_legacy_collector_live_route_is_closed_before_adb(monkeypatch, capsys):
    monkeypatch.setattr(collector.shutil, "which",
                        lambda *_: pytest.fail("legacy route must not locate ADB"))
    assert collector.main(["--serial", "EXACT", "--phase", "baseline",
                           "--vehicle-parked-confirmed", "--iphone-disconnected-confirmed"]) == 2
    assert "legacy collector live execution is disabled" in capsys.readouterr().err


def test_profile_manifest_is_exact_and_all_operations_use_fixed_legacy_shell():
    profile = json.loads(campaign.PROFILE_FILE.read_text())
    assert profile == campaign.profile_payload()
    assert campaign.verify_pinned_profile() == hashlib.sha256(campaign.PROFILE_FILE.read_bytes()).hexdigest()
    operations = {"id", "property", "read", "ps", "dumpsys", "logcat"}
    for phase in campaign.phases():
        for operation, args, timeout, maximum in phase.operations:
            assert operation in operations
            planned_args = tuple(arg.replace(campaign.PROCESS_PID_PLACEHOLDER, "1234") for arg in args)
            command = collector.FixedAdb.plan_without_adb_lookup(
                "EXACT_APPROVED_SERIAL", operation, planned_args)
            assert command[2:5] == ("EXACT_APPROVED_SERIAL", "shell", command[4])
            assert "shell" in command
            assert 0 < timeout <= campaign.MAX_COMMAND_TIMEOUT
            assert 0 < maximum <= campaign.MAX_COMMAND_OUTPUT


def test_real_capture_operation_trace_matches_fixed_phase_profile(tmp_path):
    class RecordingReader:
        serial = "SYNTHETIC"

        def __init__(self):
            self.records = []

        def run(self, operation, *args, timeout=collector.COMMAND_TIMEOUT,
                max_bytes=collector.MAX_COMMAND_OUTPUT):
            self.records.append({"operation": operation, "arguments": list(args),
                                 "timeout_seconds": timeout, "max_output_bytes": max_bytes,
                                 "result": collector.CommandResult.SUCCESS.value})
            if operation == "ps":
                output = b"PID NAME\n42 jmcs\n"
            elif args == ("/proc/42/stat",):
                output = (b"42 (jmcs) " + b" ".join([b"S"] * 19 + [b"100"]))
            elif args == ("/proc/42/status",):
                output = b"Name:\tjmcs\nPid:\t42\nPPid:\t1\nUid:\t0 0 0 0\nGid:\t0 0 0 0\n"
            elif args == ("/proc/42/cmdline",):
                output = b"/system/bin/jmcs\0--service\0"
            else:
                output = b""
            return 0, output, b""

    output = tmp_path / "trace-capture"
    output.mkdir(mode=0o700)
    reader = RecordingReader()
    capture = collector.Capture(reader, output)
    identity = capture.collect_campaign_observation("phase3_connected")
    capture.assert_same_instance(identity, phase="phase3_connected")
    expected = campaign.phases()[2].operations
    expected_trace = [(op, tuple(arg.replace(campaign.PROCESS_PID_PLACEHOLDER, str(identity.pid)) for arg in args),
                       timeout, maximum) for op, args, timeout, maximum in expected]
    actual_trace = [(row["operation"], tuple(row["arguments"]), row["timeout_seconds"],
                     row["max_output_bytes"]) for row in reader.records]
    assert actual_trace == expected_trace


def test_real_identity_phase_trace_matches_fixed_profile(tmp_path):
    target = {"ro.build.version.release": collector.EXPECTED_ANDROID_RELEASE,
              "ro.build.version.sdk": collector.EXPECTED_ANDROID_SDK,
              "ro.product.device": collector.EXPECTED_PRODUCT_DEVICE,
              "ro.product.board": collector.EXPECTED_PRODUCT_BOARD,
              "ro.hardware": collector.EXPECTED_HARDWARE,
              "ro.secure": "1", "ro.debuggable": "0"}

    class RecordingReader:
        serial = "SYNTHETIC"

        def __init__(self):
            self.records = []

        def run(self, operation, *args, timeout=collector.COMMAND_TIMEOUT,
                max_bytes=collector.MAX_COMMAND_OUTPUT):
            self.records.append({"operation": operation, "arguments": list(args),
                                 "timeout_seconds": timeout, "max_output_bytes": max_bytes,
                                 "result": collector.CommandResult.SUCCESS.value})
            if operation == "read" and args == ("/proc/version",):
                output = b"Linux version 3.1.10+"
            elif operation == "property":
                output = target[args[0]].encode()
            elif operation == "id":
                output = b"uid=2000(shell) gid=2000(shell) groups=1003,1004"
            elif operation == "ps":
                output = b"PID NAME\n42 jmcs\n"
            elif args == ("/proc/42/stat",):
                output = b"42 (jmcs) " + b" ".join([b"S"] * 19 + [b"100"])
            elif args == ("/proc/42/status",):
                output = b"Name:\tjmcs\nPid:\t42\nPPid:\t1\nUid:\t0 0 0 0\nGid:\t0 0 0 0\n"
            elif args == ("/proc/42/cmdline",):
                output = b"/system/bin/jmcs\0--service\0"
            else:
                output = b""
            return 0, output, b""

    output = tmp_path / "identity-trace"
    output.mkdir(mode=0o700)
    reader = RecordingReader()
    capture = collector.Capture(reader, output)
    capture.target_identity = capture.verify_target_identity("phase1_identity")
    _, shell = capture.store_required("phase1_identity", "platform", "shell_identity", "id",
                                      timeout=5, max_bytes=64 * 1024)
    assert b"uid=2000(shell)" in shell
    for prop in ("ro.secure", "ro.debuggable"):
        capture.store_required("phase1_identity", "properties", prop.replace(".", "_"),
                               "property", prop, timeout=5, max_bytes=64 * 1024)
    identity = capture.collect_campaign_observation("phase1_identity")
    capture.assert_same_instance(identity, phase="phase1_identity")
    expected = campaign.phases()[1].operations
    expected_trace = [(op, tuple(arg.replace(campaign.PROCESS_PID_PLACEHOLDER, str(identity.pid)) for arg in args),
                       timeout, maximum) for op, args, timeout, maximum in expected]
    actual_trace = [(row["operation"], tuple(row["arguments"]), row["timeout_seconds"],
                     row["max_output_bytes"]) for row in reader.records]
    assert actual_trace == expected_trace
    assert campaign.source_hashes() == json.loads(campaign.SOURCE_LOCK_FILE.read_text())


def test_profile_tampering_is_rejected(tmp_path, monkeypatch):
    changed = tmp_path / "campaign_profile.json"
    changed.write_bytes(campaign.PROFILE_FILE.read_bytes() + b" ")
    monkeypatch.setattr(campaign, "PROFILE_FILE", changed)
    with pytest.raises(collector.SafetyStop, match="does not match the executable"):
        campaign.verify_pinned_profile()


def _approval(tmp_path: Path) -> tuple[Path, str, dict[str, str]]:
    profile_hash = campaign.verify_pinned_profile()
    sources = campaign.source_hashes()
    row = campaign._approval_template(profile_hash, sources)
    reviewed_commit = "b" * 40
    row.update({"owner_authorization": "YES", "owner_authorized_utc": "2026-10-30T12:00:00Z",
                "adb_serial": "SYNTHETIC-EXACT-SERIAL", "policy_effective": True,
                "policy_effective_commit_sha": "a" * 40, "reviewed_commit_sha": reviewed_commit,
                "owner_risk_acceptance": True,
                "owner_confirmed_park": True, "owner_confirmed_parking_brake": True,
                "approved_vehicle_power_state": campaign.APPROVED_POWER_STATE,
                "owner_confirmed_vehicle_power_state": campaign.APPROVED_POWER_STATE,
                "review_disclaimer_acknowledged": True})
    reviews = {}
    for agent in campaign.REQUIRED_REVIEW_AGENTS:
        review_path = tmp_path / f"{agent}-review.json"
        report = {"agent_id": agent, "tool_version": f"synthetic-{agent}-fixture",
                  "review_type": "ai_engineering_review_not_human_certification",
                  "reviewed_commit_sha": reviewed_commit, "profile_sha256": profile_hash,
                  "source_hashes": sources,
                  "command_manifest_sha256": campaign.command_manifest_sha256(),
                  "phase_ids": [phase.key for phase in campaign.phases()],
                  "findings": [], "tests_executed": ["synthetic fixture only"],
                  "unverified_assumptions": ["synthetic test data"], "proposed_changes": [],
                  "recommendation": "GO"}
        review_path.write_text(json.dumps(report, sort_keys=True))
        review_path.chmod(0o600)
        reviews[agent] = {"artifact_path": str(review_path),
                          "artifact_sha256": hashlib.sha256(review_path.read_bytes()).hexdigest()}
    row["multi_agent_reviews"] = reviews
    approval_path = tmp_path / "owner-approval.json"
    approval_path.write_text(json.dumps(row))
    approval_path.chmod(0o600)
    return approval_path, profile_hash, sources


def test_approval_requires_exact_owner_and_three_hash_bound_ai_reviews(tmp_path):
    approval_path, profile_hash, sources = _approval(tmp_path)
    serial, _ = campaign.validate_approval(approval_path, profile_hash=profile_hash,
                                           source_hashes_verified=sources)
    assert serial == "SYNTHETIC-EXACT-SERIAL"
    record = json.loads(approval_path.read_text())
    record["adb_serial"] = "auto"
    approval_path.write_text(json.dumps(record))
    approval_path.chmod(0o600)
    with pytest.raises(collector.SafetyStop, match="exact pre-approved"):
        campaign.validate_approval(approval_path, profile_hash=profile_hash,
                                   source_hashes_verified=sources)


def test_approval_requires_effective_policy_attestation(tmp_path):
    approval_path, profile_hash, sources = _approval(tmp_path)
    record = json.loads(approval_path.read_text())
    record["policy_effective"] = False
    approval_path.write_text(json.dumps(record))
    approval_path.chmod(0o600)
    with pytest.raises(collector.SafetyStop, match="policy adoption"):
        campaign.validate_approval(approval_path, profile_hash=profile_hash,
                                   source_hashes_verified=sources)


def test_owner_power_state_must_match_pinned_on_non_ready_state(tmp_path):
    approval_path, profile_hash, sources = _approval(tmp_path)
    record = json.loads(approval_path.read_text())
    record["approved_vehicle_power_state"] = "READY"
    approval_path.write_text(json.dumps(record))
    approval_path.chmod(0o600)
    with pytest.raises(collector.SafetyStop, match="power state"):
        campaign.validate_approval(approval_path, profile_hash=profile_hash,
                                   source_hashes_verified=sources)


@pytest.mark.parametrize("mutation, message", [
    (lambda record: record["multi_agent_reviews"].pop("ecc"), "Codex, Claude, and ECC"),
    (lambda record: record["multi_agent_reviews"]["claude"].update(artifact_sha256="0" * 64), "hash mismatch"),
    (lambda record: record["multi_agent_reviews"]["codex"].update(artifact_path="/does/not/exist"), "bounded regular file"),
])
def test_missing_or_tampered_ai_review_stops(tmp_path, mutation, message):
    approval_path, profile_hash, sources = _approval(tmp_path)
    record = json.loads(approval_path.read_text())
    mutation(record)
    approval_path.write_text(json.dumps(record))
    approval_path.chmod(0o600)
    with pytest.raises(collector.SafetyStop, match=message):
        campaign.validate_approval(approval_path, profile_hash=profile_hash,
                                   source_hashes_verified=sources)


def test_unresolved_high_finding_and_human_certification_claim_are_rejected(tmp_path):
    approval_path, profile_hash, sources = _approval(tmp_path)
    record = json.loads(approval_path.read_text())
    review = Path(record["multi_agent_reviews"]["ecc"]["artifact_path"])
    report = json.loads(review.read_text())
    report["findings"] = [{"severity": "high", "status": "open", "finding": "synthetic unresolved finding"}]
    review.write_text(json.dumps(report, sort_keys=True))
    review.chmod(0o600)
    record["multi_agent_reviews"]["ecc"]["artifact_sha256"] = hashlib.sha256(review.read_bytes()).hexdigest()
    approval_path.write_text(json.dumps(record))
    approval_path.chmod(0o600)
    with pytest.raises(collector.SafetyStop, match="unresolved critical/high"):
        campaign.validate_approval(approval_path, profile_hash=profile_hash,
                                   source_hashes_verified=sources)


def test_review_record_cannot_be_mislabeled_as_human_certification(tmp_path):
    approval_path, profile_hash, sources = _approval(tmp_path)
    record = json.loads(approval_path.read_text())
    review = Path(record["multi_agent_reviews"]["codex"]["artifact_path"])
    report = json.loads(review.read_text())
    report["review_type"] = "independent_human_safety_certification"
    review.write_text(json.dumps(report, sort_keys=True))
    review.chmod(0o600)
    record["multi_agent_reviews"]["codex"]["artifact_sha256"] = hashlib.sha256(review.read_bytes()).hexdigest()
    approval_path.write_text(json.dumps(record))
    approval_path.chmod(0o600)
    with pytest.raises(collector.SafetyStop, match="labeled as AI engineering review"):
        campaign.validate_approval(approval_path, profile_hash=profile_hash,
                                   source_hashes_verified=sources)


def test_review_disclaimer_is_required_even_when_all_reports_are_go(tmp_path):
    approval_path, profile_hash, sources = _approval(tmp_path)
    record = json.loads(approval_path.read_text())
    record["review_disclaimer_acknowledged"] = False
    approval_path.write_text(json.dumps(record))
    approval_path.chmod(0o600)
    with pytest.raises(collector.SafetyStop, match="not independent human safety certification"):
        campaign.validate_approval(approval_path, profile_hash=profile_hash,
                                   source_hashes_verified=sources)


def test_effective_policy_gate_requires_fresh_clean_main_and_adopted_policy():
    responses = iter([
        SimpleNamespace(returncode=0, stdout=""),
        SimpleNamespace(returncode=0, stdout="main\n"),
        SimpleNamespace(returncode=0, stdout=""),
        SimpleNamespace(returncode=0, stdout="a" * 40),
        SimpleNamespace(returncode=0, stdout="a" * 40),
        SimpleNamespace(returncode=0, stdout=""),
    ])
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)
        return next(responses)

    campaign.verify_effective_policy("b" * 40, run=fake_run)
    assert calls[0] == ["git", "fetch", "--quiet", "origin", "main"]
    assert calls[-1] == ["git", "merge-base", "--is-ancestor", "b" * 40, "origin/main"]


@pytest.mark.parametrize("branch, dirty, head, remote, message", [
    ("feature", "", "a" * 40, "a" * 40, "clean checkout on main"),
    ("main", " M source.py", "a" * 40, "a" * 40, "clean checkout on main"),
    ("main", "", "a" * 40, "c" * 40, "exactly match freshly fetched origin/main"),
])
def test_effective_policy_gate_rejects_wrong_checkout_state(branch, dirty, head, remote, message):
    outputs = iter(["", branch, dirty, head, remote, ""])

    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout=next(outputs))

    with pytest.raises(collector.SafetyStop, match=message):
        campaign.verify_effective_policy("b" * 40, run=fake_run)


def test_live_runner_stops_at_policy_gate_before_adb_or_capture(tmp_path, monkeypatch):
    approval_path, _, _ = _approval(tmp_path)

    def fail_policy(*args, **kwargs):
        raise collector.SafetyStop("policy has not been adopted")

    monkeypatch.setattr(campaign, "verify_effective_policy", fail_policy)
    monkeypatch.setattr(collector.shutil, "which",
                        lambda *_: pytest.fail("ADB lookup occurred before policy gate"))
    output_root = tmp_path / "private-output"
    result = campaign.main(["run", "--approval-file", str(approval_path),
                            "--output-root", str(output_root)])
    assert result == 2
    assert not output_root.exists()


def test_missing_approval_stops_before_adb_client_or_capture_creation(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("ADB client lookup occurred before approval validation")

    monkeypatch.setattr(collector.shutil, "which", forbidden)
    output_root = tmp_path / "private-output"
    result = campaign.main(["run", "--approval-file", str(tmp_path / "missing.json"),
                            "--output-root", str(output_root)])
    assert result == 2
    assert not output_root.exists()


def test_unavailable_adb_preserves_initialized_private_recovery_checkpoint(tmp_path, monkeypatch):
    approval_path, _, _ = _approval(tmp_path)
    output_root = tmp_path / "private-output"
    monkeypatch.setattr(campaign, "verify_effective_policy", lambda *_: None)
    monkeypatch.setattr(collector.shutil, "which", lambda _: None)
    result = campaign.main(["run", "--approval-file", str(approval_path),
                            "--output-root", str(output_root)])
    assert result == 2
    capture_dir = next(output_root.iterdir())
    state = json.loads((capture_dir / "campaign_state.json").read_text())
    assert state["status"] == "initialized_before_adb_client_creation"
    assert campaign.recover_interrupted_capture(capture_dir)["status"] == "INTERRUPTED_INCOMPLETE"


@pytest.mark.parametrize(("code", "reason"), [
    (127, "unavailable"), (1, "permission"), (124, "timeout"), (125, "output limit"),
])
def test_any_fixed_command_failure_stops_campaign(tmp_path, code, reason):
    class FakeReader:
        serial = "SYNTHETIC"
        records = []

        def run(self, operation, *args, **kwargs):
            self.records.append({"operation": operation, "arguments": list(args), "result": reason})
            return code, b"", b""

    capture = collector.Capture(FakeReader(), tmp_path / "private-capture")
    with pytest.raises(collector.SafetyStop, match="required fixed diagnostic operation failed"):
        capture.store_required("phase1_identity", "identity", "probe", "id", timeout=5,
                               max_bytes=64 * 1024)


class FakeCapture:
    def __init__(self, output: Path, *, fail_phase: str | None = None, restart_phase: str | None = None):
        self.output = output
        self.reader = type("Reader", (), {"records": [], "serial": "SYNTHETIC"})()
        self.files = []
        self.phase_times = {}
        self.calls = []
        self.fail_phase = fail_phase
        self.restart_phase = restart_phase
        self.identity = collector.ProcessIdentity(42, 100, "/system/bin/jmcs", "/system/bin/jmcs", "0", "0", "1")

    def record_result(self, *args, **kwargs):
        self.calls.append(("record", args))

    def verify_target_identity(self, phase="preflight"):
        self.calls.append(("verify", phase))
        return {"android_release": "4.2.2"}

    def store_required(self, phase, category, name, operation, *args, **kwargs):
        self.calls.append(("required", phase, operation, args))
        if operation == "id":
            return 0, b"uid=2000(shell) gid=2000(shell)\n"
        if args == ("ro.debuggable",):
            return 0, b"0\n"
        return 0, b"1\n"

    def collect_campaign_observation(self, phase, expected_identity=None):
        self.calls.append(("collect", phase))
        if phase == self.fail_phase:
            raise collector.SafetyStop("synthetic fixed-command failure")
        if phase == self.restart_phase:
            return collector.ProcessIdentity(43, 101, "/system/bin/jmcs", "/system/bin/jmcs", "0", "0", "1")
        return self.identity

    def assert_same_instance(self, identity, phase="identity-check"):
        self.calls.append(("assert", identity.pid))
        if identity.pid != self.identity.pid:
            raise collector.SafetyStop("jmcs process instance changed")

    def finalize(self, phase_order):
        (self.output / "manifest.json").write_text(json.dumps({"phase_order": phase_order}))
        campaign._write_hash_inventory(self.output)


def _campaign(tmp_path: Path, **kwargs):
    output = tmp_path / "private-capture"
    output.mkdir(mode=0o700)
    fake = FakeCapture(output, **kwargs)
    runner = campaign.Campaign(fake, output, "a" * 64, {"source.py": "b" * 64}, "SYNTHETIC",
                               input_fn=lambda _: "YES", output_fn=lambda _: None)
    return runner, fake, output


def test_controller_orders_phases_and_writes_complete_hash_verified_manifest(tmp_path):
    runner, fake, output = _campaign(tmp_path)
    assert runner.run() is True
    assert runner.completed == [phase.key for phase in campaign.phases()]
    assert runner.capture.phase_times["phase0_baseline"]["finished_utc"]
    assert [call[1] for call in fake.calls if call[0] == "collect"] == [
        "phase1_identity", "phase3_connected", "phase4_navigation_selected",
        "phase4_navigation_deselected", "phase4_navigation_reselected",
        "phase6_disconnect", "final_restoration"]
    report = json.loads((output / "completeness_report.json").read_text())
    assert report["status"] == "CAPTURE_COMPLETE_RESTORATION_ATTESTED"
    assert report["capture_hashes_verified"] is True
    assert "completeness_report.json" in campaign.verify_capture_hashes(output)


@pytest.mark.parametrize(("fail_phase", "restart_phase"), [
    ("phase4_navigation_deselected", None), (None, "phase3_connected"),
])
def test_phase_failure_or_process_restart_aborts_without_next_phase(tmp_path, fail_phase, restart_phase):
    runner, fake, output = _campaign(tmp_path, fail_phase=fail_phase, restart_phase=restart_phase)
    assert runner.run() is False
    collect_phases = [call[1] for call in fake.calls if call[0] == "collect"]
    assert collect_phases[-1] in {fail_phase, restart_phase}
    assert "final_restoration" not in collect_phases
    failure = json.loads((output / "failure_card.json").read_text())
    assert failure["owner_decision_required"] is True
    assert failure["partial_hash_verification"] == "verified"


def test_failed_partial_hash_verification_is_persisted(tmp_path, monkeypatch):
    runner, fake, output = _campaign(tmp_path, fail_phase="phase3_connected")
    monkeypatch.setattr(campaign, "verify_capture_hashes",
                        lambda *_: (_ for _ in ()).throw(collector.SafetyStop("synthetic hash failure")))
    assert runner.run() is False
    failure = json.loads((output / "failure_card.json").read_text())
    assert failure["partial_hash_verification"] == "incomplete"
    assert failure["partial_hash_error"] == "SafetyStop"


def test_user_cancellation_aborts_before_any_collector_call(tmp_path):
    output = tmp_path / "private-capture"
    output.mkdir(mode=0o700)
    fake = FakeCapture(output)
    answers = iter(["NO"])
    runner = campaign.Campaign(fake, output, "a" * 64, {"source.py": "b" * 64}, "SYNTHETIC",
                               input_fn=lambda _: next(answers), output_fn=lambda _: None)
    assert runner.run() is False
    assert not [call for call in fake.calls if call[0] == "collect"]


def test_capture_hash_verification_detects_tampering_and_recovery_is_offline(tmp_path, monkeypatch):
    capture_dir = tmp_path / "interrupted"
    capture_dir.mkdir(mode=0o700)
    artifact = capture_dir / "phase1_identity" / "identity.raw"
    artifact.parent.mkdir()
    artifact.write_bytes(b"synthetic private bytes")
    row = {"path": "phase1_identity/identity.raw", "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}
    (capture_dir / "campaign_state.json").write_text(json.dumps({
        "campaign_id": "CL-HONDA-RUNTIME-DIAGNOSTIC-EXECUTION",
        "phase_order": ["phase1_identity"], "current_phase": "phase1_identity",
        "artifacts": [row]}))
    orphan = capture_dir / "orphan.raw"
    orphan.write_bytes(b"partial uncheckpointed artifact")
    result = campaign.recover_interrupted_capture(capture_dir)
    assert result["status"] == "INTERRUPTED_INCOMPLETE"
    assert result["verified_artifacts"] == ["phase1_identity/identity.raw"]
    assert result["orphaned_artifacts"] == ["orphan.raw"]
    valid_dir = tmp_path / "finalized"
    valid_dir.mkdir(mode=0o700)
    verified_file = valid_dir / "artifact.raw"
    verified_file.write_bytes(b"original")
    campaign._write_hash_inventory(valid_dir)
    assert campaign.verify_capture_hashes(valid_dir) == ("artifact.raw",)
    verified_file.write_bytes(b"tampered")
    with pytest.raises(collector.SafetyStop, match="artifact hash mismatch"):
        campaign.verify_capture_hashes(valid_dir)


def test_capture_recovery_rejects_symlink_root_and_malformed_checkpoint(tmp_path):
    real_dir = tmp_path / "real"
    real_dir.mkdir(mode=0o700)
    (real_dir / "campaign_state.json").write_text('{"artifacts": []}')
    link = tmp_path / "capture-link"
    link.symlink_to(real_dir, target_is_directory=True)
    with pytest.raises(collector.SafetyStop, match="cannot be a symlink"):
        campaign.recover_interrupted_capture(link)
    (real_dir / "campaign_state.json").write_text('{"artifacts": [1]}')
    assert campaign.recover_interrupted_capture(real_dir)["integrity_failures"] == ["malformed artifact entry"]
