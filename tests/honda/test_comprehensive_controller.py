from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/honda-readonly-preflight"))
import comprehensive_controller as controller
import comprehensive_replay as replay


def test_session_and_authorization_deadlines_provide_two_times_schedule_buffer():
    assert controller.MAX_SESSION_DURATION_SECONDS == 6000
    assert controller.MAX_AUTHORIZATION_DURATION_SECONDS == 6000
    assert controller.MAX_SESSION_DURATION_SECONDS - 2970 == 3030


def _category_permissions(categories):
    return {category: category in set(categories) for category in controller.LIVE_PERMISSION_CATEGORIES}


def test_simulated_dry_run_has_six_profiles_and_45_api17_fixed_command_shapes(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("dry-run attempted process or executable access")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    report = controller.dry_run_report()
    assert report["mode"] == "SIMULATED_DRY_RUN_NO_DEVICE_ACCESS"
    assert report["live_execution_enabled"] is False
    assert report["live_backend"] == "AUTHORIZATION_GATED_PRIVATE_SESSION_ONLY"
    assert (report["phase_count"], report["command_shapes"]) == (6, 45)
    assert report["adb_executable_lookup"] is False
    assert report["device_enumeration"] is False
    assert report["subprocess_calls"] == 0
    assert len({row["id"] for row in report["phases"]}) == 6
    assert report["campaign_command_count"] == 162
    assert report["session_limits"]["session_output_bytes"] == 158400512
    assert report["session_limits"]["session_output_decimal_mb"] == 158.400512
    assert report["session_limits"]["session_output_mib"] == 151.0625
    assert all(row["failure_policy"].startswith("abort phase") for row in report["phases"])
    assert report["coverage_required"] == 19


def test_replay_does_not_claim_approved_but_uncaptured_phase_as_evidence():
    summary = {"approved_phases": ["phase1_ordinary_adb_capability",
        "phase4_three_state_carplay", "phase7_recovery_restoration"],
        "owner_state_confirmations": [{"phase": "phase7_recovery_restoration",
            "status": "FACTORY_RESTORATION_CONFIRMED"}]}
    coverage = replay._session_coverage(summary, [])
    assert coverage["phase1_identity_complete"] is False
    assert coverage["phase4_all_states_recorded"] is False
    assert coverage["phase7_restoration_confirmed"] is False


def test_replay_requires_post_read_owner_restoration_and_all_restoration_commands():
    summary = {"owner_state_confirmations": [
        {"phase": "phase7_recovery_restoration", "status": "FACTORY_RESTORATION_CONFIRMED"},
        {"phase": "phase7_recovery_restoration", "status": "FACTORY_RESTORATION_CONFIRMED_AFTER_READS"}]}
    incomplete = [{"phase": "phase7_recovery_restoration", "state": "factory_restoration",
        "operation": operation, "arguments": list(args), "result_status": "success"}
        for operation, args in replay.LIFECYCLE_OPERATIONS[:-1]]
    assert replay._session_coverage(summary, incomplete)["phase7_restoration_confirmed"] is False
    complete = incomplete + [{"phase": "phase7_recovery_restoration", "state": "factory_restoration",
        "operation": operation, "arguments": list(args), "result_status": "success"}
        for operation, args in replay.LIFECYCLE_OPERATIONS[-1:]]
    assert replay._session_coverage(summary, complete)["phase7_restoration_confirmed"] is True


def test_replay_requires_owner_confirmation_and_successful_commands_for_lifecycle_coverage():
    summary = {"owner_state_confirmations": [
        {"phase": "phase4_three_state_carplay", "state": state,
         "status": "OWNER_CONFIRMED_STABLE"} for state in replay.LIFECYCLE_STATES]}
    records = [{"phase": "phase4_three_state_carplay", "state": state,
        "operation": operation, "arguments": list(args), "result_status": "success"}
        for state in replay.LIFECYCLE_STATES for operation, args in replay.LIFECYCLE_OPERATIONS]
    coverage = replay._session_coverage(summary, records)
    assert coverage["phase4_all_states_recorded"] is True
    records[0]["result_status"] = "permission_denied"
    coverage = replay._session_coverage(summary, records)
    assert coverage["phase4_all_states_recorded"] is False


def test_all_separate_categories_are_present_and_no_phase_inherits_permission():
    assert controller.PHASE_CATEGORIES["phase1_ordinary_adb_capability"] == ("ordinary_unprivileged_adb",)
    assert set(controller.PHASE_CATEGORIES["phase4_three_state_carplay"]) == {
        "ordinary_unprivileged_adb", "stock_carplay_transition", "factory_navigation_observation"}
    assert "phase5_display1_navigation_lifecycle" not in controller.PHASE_CATEGORIES
    assert "phase6_existing_hondahack_casting" not in controller.PHASE_CATEGORIES
    assert "existing_hondahack_observation" not in controller.PHASE_CATEGORIES["phase4_three_state_carplay"]
    assert controller.PHASE_CATEGORIES["phase2_existing_root_supersu_review"] == ("privileged_diagnostics",)


def test_one_session_approval_covers_only_explicit_compatible_phases():
    phases = ["phase1_ordinary_adb_capability", "phase4_three_state_carplay",
              "phase7_recovery_restoration"]
    categories = sorted(set().union(*(set(controller.PHASE_CATEGORIES[p]) for p in phases)))
    record = {"campaign_id": controller.CAMPAIGN_ID, "approved_phases": phases,
              "approved_categories": categories, "category_permissions": _category_permissions(categories), "risk_level": "LEVEL_2",
              "live_execution_enabled": True, "pins": {"pin": "value"},
              "authorization_id": "AUTH-22334455", "run_id": "a" * 32, "nonce": "b" * 32,
              **controller.new_run_identifiers(), "owner_confirmed": True,
              "exact_adb_serial": "owner-private-serial",
              "readiness_checks": {key: True for key in ("stationary_in_park", "parking_brake_set", "owner_present", "approved_power_state", "no_abnormal_warning", "factory_displays_normal", "adb_transport_independent")},
              "adb_transport_details": "synthetic dedicated ADB route independent of CarPlay path and shared hub",
              "evidence_destination_checklist": {key: True for key in ("host_local_outside_repository", "directory_owner_only", "files_owner_only", "cloud_sync_disabled", "hash_inventory_ready")},
              "recovery_prerequisites_confirmed": True, "owner_question": "Which windows own Display 1?",
              "expected_evidence": "Bounded window/display snapshots", "known_risks": ["display state changes"], "stop_conditions": ["unexpected warning"],
              "review_artifacts": {"technical": "/tmp/technical-review.json", "qualified_vehicle_safety": "/tmp/safety-review.json"},
              "technical_reviewer_independence_verified": True,
              "qualified_safety_reviewer_credentials_verified": True,
              "factory_restoration_reference": "initial factory display and Navigation state",
              "exact_vehicle": "2018 Honda Clarity PHEV Touring (MY16ADA; exact unit identity must be owner-verified)",
              "exact_vehicle_identity_confirmed": True, "owner_verified_vehicle_reference": "private-reference", "evidence_directory": "/tmp/cl-private-evidence"}
    controller.validate_session_authorization(record, current_pins={"pin": "value"})
    record["approved_phases"].append("phase2_existing_root_supersu_review")
    with pytest.raises(controller.ControllerError, match="fixed campaign order"):
        controller.validate_session_authorization(record, current_pins={"pin": "value"})


def test_level_one_baseline_does_not_require_an_external_review():
    record = {"campaign_id": controller.CAMPAIGN_ID,
              "approved_phases": ["phase0_baseline_safety_identity"],
              "approved_categories": ["owner_baseline_observation"], "category_permissions": _category_permissions([]), "risk_level": "LEVEL_1",
              "live_execution_enabled": True, "pins": {"pin": "value"},
              "authorization_id": "AUTH-11223344", "run_id": "a" * 32, "nonce": "b" * 32,
              **controller.new_run_identifiers(), "owner_confirmed": True,
                            "readiness_checks": {key: True for key in ("stationary_in_park", "parking_brake_set", "owner_present", "approved_power_state", "no_abnormal_warning", "factory_displays_normal", "adb_transport_independent")},
              "adb_transport_details": "synthetic dedicated ADB route independent of CarPlay path and shared hub",
              "evidence_destination_checklist": {key: True for key in ("host_local_outside_repository", "directory_owner_only", "files_owner_only", "cloud_sync_disabled", "hash_inventory_ready")},
              "recovery_prerequisites_confirmed": True, "owner_question": "What is the baseline?",
              "expected_evidence": "Owner-confirmed baseline state", "known_risks": ["owner observation only"], "stop_conditions": ["unexpected warning"],
              "review_artifacts": {},
              "exact_vehicle": "2018 Honda Clarity PHEV Touring (MY16ADA; exact unit identity must be owner-verified)",
              "exact_vehicle_identity_confirmed": True, "owner_verified_vehicle_reference": "private-reference", "evidence_directory": "/tmp/cl-private-evidence"}
    controller.validate_session_authorization(record, current_pins={"pin": "value"})


def test_existing_fixed_ordinary_adb_identity_subset_is_level_one(tmp_path):
    record = _live_test_record(tmp_path, ["phase0_baseline_safety_identity",
                                         "phase1_ordinary_adb_capability"], controller.pins())
    record["review_artifacts"] = {}
    controller.validate_session_authorization(record, current_pins=controller.pins())
    assert controller.PHASE_RISK_LEVELS["phase1_ordinary_adb_capability"] == 1
    assert len(controller._phase_rows(controller._proposal()["phases"][1])) == 19


def test_level_two_stock_carplay_requires_technical_review_attestation(tmp_path):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["review_artifacts"] = {}
    record["factory_restoration_reference"] = "owner-defined factory baseline"
    with pytest.raises(controller.ControllerError, match="review artifact paths"):
        controller.validate_session_authorization(record, current_pins=controller.pins())


def test_review_record_has_one_path_per_artifact_and_no_copied_commit_or_digest(tmp_path):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["factory_restoration_reference"] = "owner-defined factory baseline"
    assert set(record["review_artifacts"]) == {"technical", "qualified_vehicle_safety"}
    assert all(Path(path).is_absolute() for path in record["review_artifacts"].values())
    assert "review_artifact_paths" not in record
    assert "reviewed_commit_sha" not in record
    assert record["owner_confirmed"] is True
    assert "readiness_answer" not in record
    controller.validate_session_authorization(record, current_pins=controller.pins())


def test_controller_derives_review_digest_and_commit_from_artifact_and_clean_source(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import sys

    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    seen = []

    def fake_validate(path, **kwargs):
        seen.append((path, kwargs["commit_sha"]))
        return {"decision": "APPROVE_ENGINEERING",
                "artifact_sha256": "a" * 64 if "technical" in str(path) else "b" * 64}

    monkeypatch.setattr(controller, "_candidate_commit", lambda: "c" * 40)
    monkeypatch.setitem(sys.modules, "validate_review_artifacts",
                        SimpleNamespace(validate_review_artifact=fake_validate))
    bindings = controller._validate_live_reviews(record, controller.pins())
    assert bindings == {"reviewed_commit_sha": "c" * 40,
                        "review_artifact_sha256": {"qualified_vehicle_safety": "b" * 64,
                                                    "technical": "a" * 64}}
    assert len(seen) == 2
    assert all(commit == "c" * 40 for _, commit in seen)


def test_review_artifact_change_after_owner_yes_stops_before_one_use_consumption(tmp_path, monkeypatch):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["factory_restoration_reference"] = "owner-defined factory baseline"
    first = {"reviewed_commit_sha": "c" * 40,
             "review_artifact_sha256": {"technical": "a" * 64,
                                        "qualified_vehicle_safety": "b" * 64}}
    changed = {"reviewed_commit_sha": "c" * 40,
               "review_artifact_sha256": {"technical": "d" * 64,
                                          "qualified_vehicle_safety": "b" * 64}}
    bindings = iter((first, changed))
    monkeypatch.setattr(controller, "_validate_live_reviews", lambda *_args: next(bindings))
    calls = []
    with pytest.raises(controller.ControllerError, match="changed before one-use authorization"):
        controller._execute_authorized_session(
            record, ledger=tmp_path / "ledger", prompt=lambda _message: "YES",
            output=lambda _message: None,
            executor_factory=lambda _serial: lambda command: calls.append(command),
        )
    assert calls == []
    assert not (tmp_path / "ledger").exists()
    failed_run = Path(record["evidence_directory"]) / record["run_id"]
    assert failed_run.is_dir()
    assert not (failed_run / "authorization-binding.json").exists()


def test_session_authorization_requires_a_private_destination_and_recovery_route():
    record = {"campaign_id": controller.CAMPAIGN_ID,
              "approved_phases": ["phase0_baseline_safety_identity"],
              "approved_categories": ["owner_baseline_observation"], "category_permissions": _category_permissions([]), "risk_level": "LEVEL_1",
              "live_execution_enabled": True, "pins": {"pin": "value"},
              "authorization_id": "AUTH-11223344", "run_id": "a" * 32, "nonce": "b" * 32,
              **controller.new_run_identifiers(), "owner_confirmed": True,
                            "readiness_checks": {key: True for key in ("stationary_in_park", "parking_brake_set", "owner_present", "approved_power_state", "no_abnormal_warning", "factory_displays_normal", "adb_transport_independent")},
              "adb_transport_details": "synthetic dedicated ADB route independent of CarPlay path and shared hub",
              "evidence_destination_checklist": {key: True for key in ("host_local_outside_repository", "directory_owner_only", "files_owner_only", "cloud_sync_disabled", "hash_inventory_ready")},
              "recovery_prerequisites_confirmed": True,
              "owner_question": "What is the initial state?", "expected_evidence": "Baseline state", "known_risks": ["owner observation only"],
              "stop_conditions": ["abnormal warning"], "review_artifacts": {},
              "exact_vehicle": "2018 Honda Clarity PHEV Touring (MY16ADA; exact unit identity must be owner-verified)",
              "exact_vehicle_identity_confirmed": True, "owner_verified_vehicle_reference": "private-reference", "evidence_directory": "/tmp/cl-private-evidence"}
    controller.validate_session_authorization(record, current_pins={"pin": "value"})
    record["evidence_destination_checklist"]["cloud_sync_disabled"] = False
    with pytest.raises(controller.ControllerError, match="evidence destination"):
        controller.validate_session_authorization(record, current_pins={"pin": "value"})


def _live_test_record(tmp_path, phases, pin_values):
    categories = sorted(set().union(*(set(controller.PHASE_CATEGORIES[p]) for p in phases)))
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(mode=0o700)
    evidence_dir.chmod(0o700)
    return {"campaign_id": controller.CAMPAIGN_ID, "approved_phases": phases,
            "approved_categories": categories, "category_permissions": _category_permissions(categories),
            "risk_level": f"LEVEL_{max(controller.PHASE_RISK_LEVELS[p] for p in phases)}",
              "live_execution_enabled": True,
              "pins": pin_values,
            "authorization_id": "AUTH-55667788", "run_id": "f" * 32, "nonce": "e" * 32,
            **controller.new_run_identifiers(), "owner_confirmed": True,             "readiness_checks": {key: True for key in ("stationary_in_park", "parking_brake_set", "owner_present", "approved_power_state", "no_abnormal_warning", "factory_displays_normal", "adb_transport_independent")},
              "adb_transport_details": "synthetic dedicated ADB route independent of CarPlay path and shared hub",
            "evidence_destination_checklist": {key: True for key in ("host_local_outside_repository", "directory_owner_only", "files_owner_only", "cloud_sync_disabled", "hash_inventory_ready")},
            "recovery_prerequisites_confirmed": True, "owner_question": "What exact target and jmcs identity are present?",
            "expected_evidence": "Verified API-17 target properties, shell identity, and stable jmcs PID",
            "known_risks": ["endpoint or process identity may mismatch"],
            "stop_conditions": ["identity mismatch", "permission denied", "abnormal warning"],
            "exact_vehicle": "2018 Honda Clarity PHEV Touring (MY16ADA; exact unit identity must be owner-verified)",
            "exact_vehicle_identity_confirmed": True, "owner_verified_vehicle_reference": "private-reference",
            "exact_adb_serial": "private-owner-serial", "evidence_directory": str(evidence_dir),
            "review_artifacts": {review: str(tmp_path / f"{review}.json")
                                 for review in sorted(set().union(*(set(controller.PHASE_REVIEW_REQUIREMENTS.get(p, ())) for p in phases)))},
            "technical_reviewer_independence_verified": True,
            "qualified_safety_reviewer_credentials_verified": True}


def test_adb_transport_independence_is_required_for_adb_authorization(tmp_path):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["readiness_checks"]["adb_transport_independent"] = False
    with pytest.raises(controller.ControllerError, match="readiness checks are incomplete"):
        controller.validate_session_authorization(record, current_pins=controller.pins())

    record["readiness_checks"]["adb_transport_independent"] = True
    del record["adb_transport_details"]
    with pytest.raises(controller.ControllerError, match="privately describe the exact transport"):
        controller.validate_session_authorization(record, current_pins=controller.pins())

    record["adb_transport_details"] = "\n"
    with pytest.raises(controller.ControllerError, match="privately describe the exact transport"):
        controller.validate_session_authorization(record, current_pins=controller.pins())


def test_live_execution_requires_explicit_one_run_owner_enablement(tmp_path):
    record = _live_test_record(tmp_path, ["phase0_baseline_safety_identity"], controller.pins())
    record["live_execution_enabled"] = False
    with pytest.raises(controller.ControllerError, match="does not authorize live execution"):
        controller.validate_session_authorization(record, current_pins=controller.pins())


def test_candidate_review_pin_rejects_dirty_worktree(monkeypatch):
    class Result:
        returncode = 0
        stdout = " M tools/honda-readonly-preflight/comprehensive_controller.py\n"
    monkeypatch.setattr(controller.subprocess, "run", lambda *_a, **_k: Result())
    with pytest.raises(controller.ControllerError, match="clean worktree"):
        controller._candidate_commit()


def test_hondahack_observation_is_excluded_from_ordinary_scope():
    assert not any("hondahack" in key.lower() for key in controller.PHASE_CATEGORIES)


def _synthetic_phase1_output(argv, stat_tick="99"):
    remote = argv[4:]
    if remote[0] == "getprop":
        values = {"ro.build.version.release": "4.2.2", "ro.build.version.sdk": "17",
                  "ro.product.device": "vcm30t30a", "ro.product.board": "Andromeda",
                  "ro.hardware": "vcm30t30", "ro.secure": "1", "ro.debuggable": "0"}
        return values[remote[1]].encode()
    if remote == ("service", "list"):
        return b"Found 2 services:\n0 navigation: [com.mitsubishielectric.ada.appservice.navigation]\n"
    if len(remote) == 3 and remote[:2] == ("dumpsys", "package"):
        return f"Package [{remote[2]}] (synthetic)\n".encode()
    if remote[:2] == ("pm", "path"):
        return f"package:/system/app/{remote[2]}.apk\n".encode()
    if remote == ("id",):
        return b"uid=2000(shell) gid=2000(shell) groups=1003,1004\n"
    if remote == ("ps",):
        return b"PID NAME\n1234 jmcs\n"
    if remote[0] == "cat" and remote[1].endswith("/stat"):
        fields = ["S"] + ["0"] * 19
        fields[19] = stat_tick
        return f"1234 (jmcs) {' '.join(fields)}\n".encode()
    if remote[0] == "cat" and remote[1].endswith("/cmdline"):
        return b"/system/bin/jmcs\x00"
    if remote[0] == "cat" and remote[1].endswith("/status"):
        return b"Name:\tjmcs\nUid:\t0\t0\t0\t0\nGid:\t0\t0\t0\t0\n"
    if remote[0:2] == ("ls", "-l"):
        return b"lrwxrwxrwx root root 0 2026-10-31 /proc/1234/exe -> /system/bin/jmcs\n"
    return b"synthetic bounded snapshot\n"


def test_authorized_low_risk_session_executes_only_exact_fixed_commands_without_device_access(tmp_path):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    calls = []
    def factory(_serial):
        def execute(command):
            calls.append(command)
            return 0, _synthetic_phase1_output(command.argv), b""
        return execute
    answers = iter(("YES", "READY", "POWERED_OFF"))
    result = controller._execute_authorized_session(
        record, ledger=tmp_path / "ledger", prompt=lambda _message: next(answers),
        output=lambda _message: None, executor_factory=factory,
        review_verifier=lambda _record, _pins: None, notify=lambda _status: "DELIVERED",
    )
    assert result["status"] == "SESSION_COMPLETE_PENDING_OFFLINE_ANALYSIS"
    assert result["campaign_success"] is False
    assert result["command_count"] == 19
    assert result["normal_power_off_confirmed"] is True
    phase1 = next(row for row in result["phase_results"]
                  if row["phase"] == "phase1_ordinary_adb_capability")
    assert phase1["process_identity_confidence"] == "PID_ONLY_NO_START_TIME_OR_EXECUTABLE"
    assert all(command.argv[0] == "adb" and command.argv[1:4] == ("-s", "private-owner-serial", "shell") for command in calls)
    assert not any("su" in command.argv or "root" == command.argv[-1] for command in calls)
    run_dir = Path(record["evidence_directory"]) / record["run_id"]
    assert run_dir.stat().st_mode & 0o777 == 0o700
    assert (run_dir / "session-summary.json").stat().st_mode & 0o777 == 0o600
    assert len(list(run_dir.glob("*.stdout.bin"))) == 19
    archive_summary = json.loads((run_dir / "session-summary.json").read_text())
    binding = json.loads((run_dir / "authorization-binding.json").read_text())
    assert binding == {"review_bindings": {"reviewed_commit_sha": None,
                                            "review_artifact_sha256": {}},
                       "source_pins": controller.pins()}
    assert (run_dir / "authorization-binding.json").stat().st_mode & 0o777 == 0o600
    assert archive_summary["approved_categories"] == ["ordinary_unprivileged_adb", "owner_baseline_observation"]
    assert archive_summary["category_permissions"]["ordinary_unprivileged_adb"] is True
    assert archive_summary["category_permissions"]["privileged_diagnostics"] is False
    assert archive_summary["risk_level"] == "LEVEL_1"
    assert all("started_monotonic_ns" in command and "state" in command
               for command in archive_summary["command_artifacts"])
    assessment = replay.analyze_archive(run_dir)
    assert assessment["verified_artifact_count"] > 0
    assert assessment["confirmed_objective_count"] == 0
    assert assessment["unresolved_objective_count"] == 19
    assert assessment["campaign_success"] is False
    (run_dir / archive_summary["command_artifacts"][0]["stdout_file"]).write_bytes(b"tampered")
    with pytest.raises(replay.ArchiveError, match="digest mismatch"):
        replay.analyze_archive(run_dir)


def test_session_uses_the_single_pinned_proposal_snapshot_after_file_changes(tmp_path, monkeypatch):
    proposal_copy = tmp_path / "proposal.json"
    proposal_raw = controller.PROPOSAL.read_bytes()
    proposal_copy.write_bytes(proposal_raw)
    pin_values = controller.pins()
    record = _live_test_record(tmp_path, ["phase0_baseline_safety_identity",
                                         "phase1_ordinary_adb_capability"], pin_values)
    monkeypatch.setattr(controller, "PROPOSAL", proposal_copy)
    calls = []

    def execute(command):
        calls.append(command)
        if len(calls) == 1:
            proposal_copy.write_text("changed after run binding")
        return 0, _synthetic_phase1_output(command.argv), b""

    answers = iter(("YES", "READY", "POWERED_OFF"))
    result = controller._execute_authorized_session(
        record, current_pins=pin_values, ledger=tmp_path / "ledger",
        prompt=lambda _message: next(answers),
        output=lambda _message: None, executor_factory=lambda _serial: execute,
        review_verifier=lambda _record, _pins: None, notify=lambda _status: "DELIVERED",
    )
    assert result["status"] == "SESSION_COMPLETE_PENDING_OFFLINE_ANALYSIS"
    assert len(calls) == 19
    archive = Path(record["evidence_directory"]) / record["run_id"]
    assert hashlib.sha256((archive / "campaign-proposal.json").read_bytes()).hexdigest() == pin_values["profile_sha256"]


def test_classification_failure_preserves_raw_result_and_aborts(tmp_path, monkeypatch):
    import collector
    monkeypatch.setattr(collector, "classify_command_result",
                        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("classifier failure")))
    record = _live_test_record(tmp_path, ["phase0_baseline_safety_identity",
                                         "phase1_ordinary_adb_capability"], controller.pins())
    result = controller._execute_authorized_session(
        record, ledger=tmp_path / "ledger", prompt=lambda _message: "YES",
        output=lambda _message: None,
        executor_factory=lambda _serial: lambda command: (0, _synthetic_phase1_output(command.argv), b""),
        review_verifier=lambda _record, _pins: None, notify=lambda status: status,
    )
    assert result["status"] == "ABORTED_HOST_ONLY"
    artifact = result["command_artifacts"][0]
    assert artifact["result_status"] == "CLASSIFICATION_ERROR:RuntimeError"
    run_dir = Path(record["evidence_directory"]) / record["run_id"]
    assert (run_dir / artifact["stdout_file"]).read_bytes()


def test_archive_finalization_failure_is_reported_after_vehicle_poweroff(tmp_path, monkeypatch):
    record = _live_test_record(tmp_path, ["phase0_baseline_safety_identity",
                                         "phase1_ordinary_adb_capability"], controller.pins())
    monkeypatch.setattr(controller, "_write_sha256_inventory",
                        lambda _path: (_ for _ in ()).throw(OSError("inventory failed")))
    answers = iter(("YES", "READY", "POWERED_OFF"))
    result = controller._execute_authorized_session(
        record, ledger=tmp_path / "ledger", prompt=lambda _message: next(answers),
        output=lambda _message: None,
        executor_factory=lambda _serial: lambda command: (0, _synthetic_phase1_output(command.argv), b""),
        review_verifier=lambda _record, _pins: None,
        notify=lambda status: status,
    )
    assert result["status"] == "SESSION_COMPLETE_ARCHIVE_INCOMPLETE"
    assert result["normal_power_off_confirmed"] is True
    assert result["notification"] == "archive_failure_complete"
    archive = Path(record["evidence_directory"]) / record["run_id"]
    assert json.loads((archive / "session-summary.json").read_text())["status"] == "SESSION_COMPLETE_ARCHIVE_INCOMPLETE"


def test_replay_uses_existing_display_parsers_for_state_deltas(tmp_path):
    phase = "phase4_three_state_carplay"
    states = {
        "disconnected_baseline": (
            'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n',
            "WINDOW MANAGER WINDOWS (dumpsys window windows)\nWindow #0 Window{aaaa u0 FactoryLauncher}:\n  mDisplayId=1\n",
            "+ Layer 0xaaaa (FactoryLauncher)\n+"),
        "stock_carplay_connected": (
            'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n',
            "WINDOW MANAGER WINDOWS (dumpsys window windows)\nWindow #0 Window{bbbb u0 CarPlayActivity}:\n  mDisplayId=1\n",
            "+ Layer 0xbbbb (CarPlayActivity)\n"),
    }
    records = []
    index = 0
    for state, outputs in states.items():
        for argument, output in zip(("display", "window", "SurfaceFlinger"), outputs):
            filename = f"state-{index}.bin"
            (tmp_path / filename).write_text(output)
            records.append({"phase": phase, "state": state, "exit_code": 0,
                            "operation": "dumpsys", "arguments": [argument],
                            "stdout_file": filename})
            index += 1

    result = replay._compare_states(records, tmp_path)[phase]
    transition = result["deltas"][1]["source_deltas"]
    assert transition["display"]["status"] == "COMPARED"
    assert transition["window"]["windows_by_display_id"]["1"] == {
        "added": ["CarPlayActivity"], "removed": ["FactoryLauncher"], "persisting": []}
    assert transition["surfaceflinger"]["named_layers"] == {
        "added": ["CarPlayActivity"], "removed": ["FactoryLauncher"], "persisting": []}
    assert "physical scanout" in result["interpretation"]


def test_replay_compares_factory_restoration_to_initial_disconnected_state(tmp_path):
    snapshots = {
        ("phase4_three_state_carplay", "disconnected_baseline", "display"):
            'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n',
        ("phase4_three_state_carplay", "disconnected_baseline", "window"):
            "WINDOW MANAGER WINDOWS (dumpsys window windows)\nWindow #0 Window{aaaa u0 FactoryNavigation}:\n  mDisplayId=1\n",
        ("phase4_three_state_carplay", "disconnected_baseline", "SurfaceFlinger"):
            "+ Layer 0xaaaa (FactoryNavigation)\n",
        ("phase7_recovery_restoration", "factory_restoration", "display"):
            'DisplayDeviceInfo{"Built-in": 800 x 480, type BUILT_IN}\n',
        ("phase7_recovery_restoration", "factory_restoration", "window"):
            "WINDOW MANAGER WINDOWS (dumpsys window windows)\nWindow #0 Window{bbbb u0 FactoryNavigation}:\n  mDisplayId=1\n",
        ("phase7_recovery_restoration", "factory_restoration", "SurfaceFlinger"):
            "+ Layer 0xbbbb (FactoryNavigation)\n",
    }
    records = []
    for index, ((phase, state, source), output) in enumerate(snapshots.items()):
        filename = f"restore-{index}.bin"
        (tmp_path / filename).write_text(output)
        records.append({"phase": phase, "state": state, "exit_code": 0,
                        "operation": "dumpsys", "arguments": [source],
                        "stdout_file": filename})
    result = replay._compare_states(records, tmp_path)["phase7_recovery_restoration"]
    assert result["baseline_state"] == "disconnected_baseline"
    assert result["state_order"] == ["disconnected_baseline", "factory_restoration"]
    assert result["deltas"][1]["source_deltas"]["display"]["inventory_unchanged"] is True
    assert result["deltas"][1]["source_deltas"]["window"]["all_named_windows"]["persisting"] == ["FactoryNavigation"]


def test_archive_inventory_rejects_symlink_directories(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir(mode=0o700)
    archive.chmod(0o700)
    outside = tmp_path / "outside"
    outside.mkdir()
    (archive / "linked").symlink_to(outside, target_is_directory=True)
    inventory = archive / "sha256.txt"
    inventory.write_text("")
    inventory.chmod(0o600)
    with pytest.raises(replay.ArchiveError, match="symbolic links"):
        replay._verify_inventory(archive)


def test_replay_compares_network_entries_without_claiming_jmcs_ownership(tmp_path):
    phase = "phase4_three_state_carplay"
    rows = []
    samples = {
        "disconnected_baseline": ("0: 0100007F:1F90 00000000:0000 0A 0:0 00:00000000 00000000 1000 0 111\n", "down\n"),
        "stock_carplay_connected": ("0: 0100007F:1F90 0200007F:0050 01 0:0 00:00000000 00000000 1000 0 222\n", "up\n"),
    }
    for index, (state, (tcp, operstate)) in enumerate(samples.items()):
        for suffix, operation, argument, contents in (
            ("tcp", "read", "/proc/net/tcp", "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n" + tcp),
            ("operstate", "read_net_operstate", "/sys/class/net/usb0/operstate", operstate),
        ):
            filename = f"network-{index}-{suffix}.bin"
            (tmp_path / filename).write_text(contents)
            rows.append({"phase": phase, "state": state, "exit_code": 0,
                         "operation": operation, "arguments": [argument], "stdout_file": filename})
    result = replay._compare_network_states(rows, tmp_path)
    transition = result["deltas"][1]["source_deltas"]
    assert transition["usb0"] == {"status": "COMPARED", "baseline_state": "down",
                                   "state": "up", "changed": True}
    assert transition["tcp4"]["status"] == "COMPARED"
    assert transition["tcp4"]["baseline_entry_count"] == 1
    assert transition["tcp4"]["state_entry_count"] == 1
    assert len(transition["tcp4"]["added_entry_sha256"]) == 1
    assert "FD inode equality" in result["interpretation"]


def test_authorized_session_aborts_on_first_command_failure_and_never_retries(tmp_path):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    calls = []
    def factory(_serial):
        def execute(command):
            calls.append(command)
            return 1, b"", b"permission denied"
        return execute
    answers = iter(("YES",))
    result = controller._execute_authorized_session(
        record, ledger=tmp_path / "ledger", prompt=lambda _message: next(answers),
        output=lambda _message: None, executor_factory=factory,
        review_verifier=lambda _record, _pins: None, notify=lambda status: status,
    )
    assert result["status"] == "ABORTED_HOST_ONLY"
    assert len(calls) == 1
    assert result["vehicle_commands_after_abort"] == 0
    assert result["notification"] == "stopped"
    summary_path = Path(record["evidence_directory"]) / record["run_id"] / "session-summary.json"
    assert "fixed command failed" in summary_path.read_text()


def test_ordinary_observation_manifest_never_retries_known_inaccessible_process_procfs():
    proposal = controller._proposal()
    for phase in proposal["phases"]:
        if phase["id"] in controller.BLOCKED_PHASES:
            continue
        field = controller.COMMAND_FIELDS[phase["id"]]
        for row in phase[field]:
            assert not any("/proc/<verified-jmcs-pid>/" in item for item in row)


def test_transition_requires_restoration_phase_before_any_owner_prompt(tmp_path):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["factory_restoration_reference"] = "initial factory state"
    record["review_artifacts"]["qualified_vehicle_safety"] = "/tmp/safety-review.json"
    record["technical_reviewer_independence_verified"] = True
    record["qualified_safety_reviewer_credentials_verified"] = True
    prompts = []
    with pytest.raises(controller.ControllerError, match="restoration observation"):
        controller._execute_authorized_session(
            record, ledger=tmp_path / "ledger", prompt=lambda message: prompts.append(message) or "YES",
            output=lambda _message: None, executor_factory=lambda _serial: lambda _command: (0, b"", b""),
            review_verifier=lambda _record, _pins: None, notify=lambda _status: "NOT_SENT",
        )
    assert prompts == []
    assert not (tmp_path / "ledger").exists()


def test_abort_after_transition_prompt_records_manual_restoration_requirement(tmp_path, monkeypatch):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["factory_restoration_reference"] = "disconnected factory display baseline"
    answers = iter(("YES", "READY", "READY", "READY", "STOP"))
    def synthetic_batch(**kwargs):
        return kwargs["index"] + len(kwargs["rows"]), {"pid": "1234", "identity_confidence": "PID_ONLY_NO_START_TIME_OR_EXECUTABLE"}
    monkeypatch.setattr(controller, "_execute_batch", synthetic_batch)
    result = controller._execute_authorized_session(
        record, ledger=tmp_path / "ledger", prompt=lambda _message: next(answers),
        output=lambda _message: None,
        executor_factory=lambda _serial: lambda command: (0, _synthetic_phase1_output(command.argv), b""),
        review_verifier=lambda _record, _pins: None, notify=lambda status: status,
    )
    assert result["status"] == "ABORTED_HOST_ONLY"
    assert result["factory_restoration_required"] is True
    summary_path = Path(record["evidence_directory"]) / record["run_id"] / "session-summary.json"
    summary = json.loads(summary_path.read_text())
    assert summary["factory_restoration_required"] is True


def test_authorization_expiry_during_command_batch_aborts_before_next_command(tmp_path):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    calls = []

    def factory(_serial):
        def execute(command):
            calls.append(command)
            if len(calls) == 1:
                from datetime import datetime, timedelta, timezone
                record["expires_at_utc"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
            return 0, _synthetic_phase1_output(command.argv), b""
        return execute

    result = controller._execute_authorized_session(
        record, ledger=tmp_path / "ledger", prompt=lambda _message: "YES",
        output=lambda _message: None, executor_factory=factory,
        review_verifier=lambda _record, _pins: None, notify=lambda _status: "DELIVERED",
    )
    assert result["status"] == "ABORTED_HOST_ONLY"
    assert len(calls) == 1
    assert result["command_count"] == 1


def test_private_run_directory_failure_does_not_consume_authorization(tmp_path):
    record = _live_test_record(tmp_path, ["phase0_baseline_safety_identity"], controller.pins())
    (Path(record["evidence_directory"]) / record["run_id"]).mkdir(mode=0o700)
    with pytest.raises(controller.ControllerError, match="evidence directory"):
        controller._execute_authorized_session(
            record, ledger=tmp_path / "ledger", prompt=lambda _message: "YES",
            output=lambda _message: None, review_verifier=lambda _record, _pins: None,
        )
    assert not (tmp_path / "ledger").exists()


def test_fixed_adb_executor_replans_and_passes_bounds_without_enumeration():
    from collector import FixedAdb
    reader = object.__new__(FixedAdb)
    reader.adb = "/mock/platform-tools/adb"
    reader.serial = "private-serial"
    reader.calls = []
    def run_planned(argv, operation, args, *, timeout, max_bytes):
        reader.calls.append((argv, operation, args, timeout, max_bytes))
        return 0, b"1\n", b""
    reader._run_planned = run_planned
    command = controller.Command("phase1_ordinary_adb_capability",
                                 ("adb", "-s", "private-serial", "shell", "getprop", "ro.secure"),
                                 10, 900000)
    result = controller._fixed_adb_executor(reader, "private-serial")(command)
    assert result == (0, b"1\n", b"")
    assert reader.calls == [((reader.adb, "-s", "private-serial", "shell", "getprop", "ro.secure"),
                             "property", ("ro.secure",), 10, 900000)]


def test_session_output_budget_accepts_exact_limit_once_then_fails_closed():
    budget = controller.SessionOutputBudget(limit_bytes=4)
    assert budget.reserve(4) is True
    assert budget.used_bytes == 4
    assert budget.remaining_bytes == 0
    assert budget.reserve(0) is False
    assert budget.exhausted is True
    assert budget.report()["limit_decimal_mb"] == 0.000004


def test_session_output_budget_is_shared_across_batches_and_blocks_next_adb(tmp_path, monkeypatch):
    proposal = controller._proposal()
    record = {"authorization_id": "AUTH-11223344", "run_id": "a" * 32,
              "nonce": "b" * 32}
    monkeypatch.setattr(controller, "validate_session_authorization", lambda *_a, **_k: None)
    budget = controller.SessionOutputBudget(limit_bytes=132)
    records = []
    calls = []
    execute = lambda command: calls.append(command) or (0, b"4.2.2", b"")
    kwargs = dict(phase_id="phase1_ordinary_adb_capability", serial="SERIAL-1",
        proposal_snapshot=proposal, execute_command=execute, run_dir=tmp_path, records=records,
        prior_identity=None, authorization_record=record, current_pins={},
        session_deadline=controller.time.monotonic() + 30, output_budget=budget, output=lambda _s: None)
    first = [proposal["phases"][1]["commands"][0]]
    next_command = [proposal["phases"][1]["commands"][1]]
    index, _ = controller._execute_batch(state="baseline_a", rows=first, index=0, **kwargs)
    assert index == 1 and budget.used_bytes == 5 and len(calls) == 1
    with pytest.raises(controller.ControllerError, match="output budget exhausted"):
        controller._execute_batch(state="baseline_b", rows=next_command, index=index, **kwargs)
    assert len(calls) == 1
    assert records[-1]["result_status"] == "SESSION_OUTPUT_BUDGET_EXHAUSTED_BEFORE_COMMAND"
    assert records[-1]["stdout_file"] is None and records[-1]["stderr_file"] is None
    assert budget.used_bytes == 5


def test_private_output_write_failure_removes_partial_command_artifacts(tmp_path, monkeypatch):
    command = controller.Command("phase1_ordinary_adb_capability", ("adb",), 1, 100)
    original = controller._write_private_file
    calls = 0
    def fail_second(path, data):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated short storage")
        original(path, data)
    monkeypatch.setattr(controller, "_write_private_file", fail_second)
    with pytest.raises(OSError, match="short storage"):
        controller._save_command_result(tmp_path, command, 0, 0, b"stdout", b"stderr",
            state="baseline", operation="property", arguments=("ro.build.version.release",),
            started_at_utc="start", started_monotonic_ns=1, finished_at_utc="end",
            finished_monotonic_ns=2, result_status="success")
    assert list(tmp_path.iterdir()) == []


def test_incomplete_low_level_write_is_removed_and_never_reported_complete(tmp_path, monkeypatch):
    original_fdopen = controller.os.fdopen
    class ShortWriter:
        def __init__(self, fd):
            self.inner = original_fdopen(fd, "wb", buffering=0)
            self.calls = 0
        def __enter__(self):
            return self
        def __exit__(self, *_exc):
            self.inner.close()
        def fileno(self):
            return self.inner.fileno()
        def write(self, data):
            self.calls += 1
            if self.calls == 1:
                count = max(1, len(data) // 2)
                return self.inner.write(data[:count])
            return 0
    monkeypatch.setattr(controller.os, "fdopen", lambda fd, *_a, **_k: ShortWriter(fd))
    target = tmp_path / "short.bin"
    with pytest.raises(OSError, match="no progress"):
        controller._write_private_file(target, b"incomplete evidence")
    assert not target.exists()


def test_live_route_requires_a_private_owner_authorization_file():
    with pytest.raises(controller.ControllerError, match="private owner authorization"):
        controller.execute_live()


def test_authorization_must_match_phase_and_exact_category_set():
    phase = "phase4_three_state_carplay"
    approval = {"campaign_id": controller.CAMPAIGN_ID, "approved_phases": [phase],
                "approved_categories": list(controller.PHASE_CATEGORIES[phase]),
                "category_permissions": _category_permissions(controller.PHASE_CATEGORIES[phase]),
                "live_execution_enabled": True, "pins": {"pin": "value"},
                "authorization_id": "AUTH-12345678", "nonce": "a" * 32,
                "run_id": "b" * 32, **controller.new_run_identifiers(),
                "exact_adb_serial": "owner-private-serial",
                "risk_level": "LEVEL_2", "owner_confirmed": True,                 "readiness_checks": {key: True for key in ("stationary_in_park", "parking_brake_set", "owner_present", "approved_power_state", "no_abnormal_warning", "factory_displays_normal", "adb_transport_independent")},
              "adb_transport_details": "synthetic dedicated ADB route independent of CarPlay path and shared hub",
                "evidence_destination_checklist": {key: True for key in ("host_local_outside_repository", "directory_owner_only", "files_owner_only", "cloud_sync_disabled", "hash_inventory_ready")},
                "recovery_prerequisites_confirmed": True, "owner_question": "What changes after reconnect?",
                "expected_evidence": "Bounded lifecycle comparison", "known_risks": ["stock CarPlay state transition"], "stop_conditions": ["unexpected warning"],
                "factory_restoration_reference": "initial factory display and Navigation state",
                "review_artifacts": {"technical": "/tmp/technical-review.json", "qualified_vehicle_safety": "/tmp/safety-review.json"},
                "technical_reviewer_independence_verified": True,
                "qualified_safety_reviewer_credentials_verified": True,
                "factory_restoration_reference": "factory baseline",
                "exact_vehicle": "2018 Honda Clarity PHEV Touring (MY16ADA; exact unit identity must be owner-verified)",
              "exact_vehicle_identity_confirmed": True, "owner_verified_vehicle_reference": "private-reference", "evidence_directory": "/tmp/cl-private-evidence"}
    controller.validate_authorization(approval, requested_phase=phase, current_pins={"pin": "value"})
    approval["approved_categories"] = ["ordinary_unprivileged_adb"]
    with pytest.raises(controller.ControllerError, match="exactly its phase category set"):
        controller.validate_authorization(approval, requested_phase=phase, current_pins={"pin": "value"})


@pytest.mark.parametrize("phase", sorted(controller.BLOCKED_PHASES))
def test_privileged_phase_authorization_remains_blocked(phase):
    with pytest.raises(controller.ControllerError, match="no currently justified"):
        controller.validate_authorization({}, requested_phase=phase, current_pins={})


def test_stale_source_pins_rejected():
    phase = "phase1_ordinary_adb_capability"
    approval = {"campaign_id": controller.CAMPAIGN_ID, "approved_phases": [phase],
                "approved_categories": list(controller.PHASE_CATEGORIES[phase]),
                "category_permissions": _category_permissions(controller.PHASE_CATEGORIES[phase]),
                "live_execution_enabled": True, "pins": {},
                "authorization_id": "AUTH-12345678", "nonce": "a" * 32, "run_id": "b" * 32,
                **controller.new_run_identifiers(),
                "risk_level": "LEVEL_1", "owner_confirmed": True,                 "readiness_checks": {key: True for key in ("stationary_in_park", "parking_brake_set", "owner_present", "approved_power_state", "no_abnormal_warning", "factory_displays_normal", "adb_transport_independent")},
              "adb_transport_details": "synthetic dedicated ADB route independent of CarPlay path and shared hub",
                "evidence_destination_checklist": {key: True for key in ("host_local_outside_repository", "directory_owner_only", "files_owner_only", "cloud_sync_disabled", "hash_inventory_ready")},
                "recovery_prerequisites_confirmed": True, "owner_question": "What changes in the receiver?",
                "expected_evidence": "Bounded receiver snapshot", "known_risks": ["receiver state change"], "stop_conditions": ["unexpected warning"],
                "exact_adb_serial": "owner-private-serial",
                "review_artifacts": {"technical": "/tmp/technical-review.json"},
                "factory_restoration_reference": "factory baseline",
                "exact_vehicle": "2018 Honda Clarity PHEV Touring (MY16ADA; exact unit identity must be owner-verified)",
              "exact_vehicle_identity_confirmed": True, "owner_verified_vehicle_reference": "private-reference", "evidence_directory": "/tmp/cl-private-evidence"}
    with pytest.raises(controller.ControllerError, match="stale"):
        controller.validate_authorization(approval, requested_phase=phase, current_pins={"x": "y"})


def test_expired_approval_rejected():
    from datetime import datetime, timedelta, timezone
    phase = "phase1_ordinary_adb_capability"
    old = datetime.now(timezone.utc) - timedelta(hours=1)
    approval = {"campaign_id": controller.CAMPAIGN_ID, "approved_phases": [phase],
                "approved_categories": list(controller.PHASE_CATEGORIES[phase]),
                "category_permissions": _category_permissions(controller.PHASE_CATEGORIES[phase]),
                "live_execution_enabled": True, "pins": {"pin": "value"},
                "authorization_id": "AUTH-12345678", "nonce": "a" * 32,
                "run_id": "b" * 32, "issued_at_utc": old.isoformat(),
                "expires_at_utc": (old + timedelta(minutes=10)).isoformat(),
                "risk_level": "LEVEL_1", "owner_confirmed": True,                 "readiness_checks": {key: True for key in ("stationary_in_park", "parking_brake_set", "owner_present", "approved_power_state", "no_abnormal_warning", "factory_displays_normal", "adb_transport_independent")},
              "adb_transport_details": "synthetic dedicated ADB route independent of CarPlay path and shared hub",
                "evidence_destination_checklist": {key: True for key in ("host_local_outside_repository", "directory_owner_only", "files_owner_only", "cloud_sync_disabled", "hash_inventory_ready")},
                "recovery_prerequisites_confirmed": True, "owner_question": "What changes?",
                "expected_evidence": "Bounded output", "known_risks": ["process state change"], "stop_conditions": ["unexpected warning"],
                "exact_adb_serial": "owner-private-serial",
                "review_artifacts": {"technical": "/tmp/technical-review.json"},
                "factory_restoration_reference": "factory baseline",
                "exact_vehicle": "2018 Honda Clarity PHEV Touring (MY16ADA; exact unit identity must be owner-verified)",
              "exact_vehicle_identity_confirmed": True, "owner_verified_vehicle_reference": "private-reference", "evidence_directory": "/tmp/cl-private-evidence"}
    with pytest.raises(controller.ControllerError, match="expired"):
        controller.validate_authorization(approval, requested_phase=phase, current_pins={"pin": "value"})


def test_invalid_authorization_does_not_consume_a_ledger_marker(tmp_path):
    record = {"authorization_id": "AUTH-12345678", "run_id": "b" * 32, "nonce": "a" * 32}
    with pytest.raises(controller.ControllerError):
        controller.authorize_one_run(record, current_pins={}, ledger=tmp_path / "ledger")
    assert not (tmp_path / "ledger").exists()


def test_one_use_ledger_is_private_and_replay_resistant(tmp_path):
    record = {"authorization_id": "AUTH-12345678", "run_id": "b" * 32, "nonce": "a" * 32}
    ledger = tmp_path / "private-ledger"
    marker = controller.consume_once(record, ledger=ledger)
    assert ledger.stat().st_mode & 0o777 == 0o700
    assert marker.stat().st_mode & 0o777 == 0o600
    with pytest.raises(controller.ControllerError, match="already been consumed"):
        controller.consume_once(record, ledger=ledger)


def test_nonce_cannot_be_reused_under_a_different_authorization_id(tmp_path):
    ledger = tmp_path / "private-ledger"
    controller.consume_once({"authorization_id": "AUTH-12345678", "run_id": "b" * 32, "nonce": "a" * 32}, ledger=ledger)
    with pytest.raises(controller.ControllerError, match="nonce has already been consumed"):
        controller.consume_once({"authorization_id": "AUTH-87654321", "run_id": "c" * 32, "nonce": "a" * 32}, ledger=ledger)


def test_ledger_symlink_refused(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(controller.ControllerError, match="symlink"):
        controller.consume_once({"authorization_id": "AUTH-12345678", "run_id": "b" * 32,
                                 "nonce": "a" * 32}, ledger=link)


def test_pid_start_time_and_receiver_identity_are_revalidated():
    before = {"pid": "1234", "start_time_ticks": "99", "cmdline": "/system/bin/jmcs",
              "uid": "0", "gid": "0", "exe": "/system/bin/jmcs"}
    controller.validate_process_identity(before, dict(before))
    after = dict(before, start_time_ticks="100")
    with pytest.raises(controller.ControllerError, match="changed"):
        controller.validate_process_identity(before, after)


@pytest.mark.parametrize("fault,status", [
    ("interruption", "ABORTED_HOST_ONLY"), ("permission_denied", "ABORTED"),
    ("root_unavailable", "PHASE2_BLOCKED"), ("pid_reuse", "ABORTED"),
    ("command_failure", "ABORTED"), ("unexpected_factory_observation", "ABORTED"),
    ("incomplete_evidence", "INCOMPLETE"),
])
def test_fault_simulation_aborts_without_claiming_live_evidence(fault, status):
    report = controller.simulate_fault(fault)
    assert report["status"] == status
    assert report["live_evidence"] is False
    assert report["campaign_success"] is False


def test_notification_outcomes_do_not_change_terminal_truth():
    success = controller.simulate(notify=lambda _message: None)
    assert success["notification"] == "DELIVERED_BY_INJECTED_SIMULATOR"
    assert "NO DEVICE ACCESS" in success["terminal"]
    failure = controller.simulate(notify=lambda _message: (_ for _ in ()).throw(OSError("denied")))
    assert failure["notification"].startswith("FAILED")
    assert failure["live_evidence"] is False


def test_run_notification_exception_is_reported_without_raising():
    result = controller._safe_notify(
        lambda _message: (_ for _ in ()).throw(OSError("offline")), "complete")
    assert result.startswith("FAILED:OSError")
    assert "terminal output remains authoritative" in result


def test_phase_one_does_not_claim_start_time_objective_from_pid_only():
    assert "jmcs-process-identity-continuity" not in controller.POTENTIAL_OBJECTIVES[
        "phase1_ordinary_adb_capability"]


def test_live_helpers_are_loaded_before_pins(monkeypatch):
    calls = []
    monkeypatch.setattr(controller, "_preload_live_helpers", lambda: calls.append("helpers"))
    monkeypatch.setattr(controller, "pins", lambda: calls.append("pins") or {})
    with pytest.raises((KeyError, controller.ControllerError)):
        controller._execute_authorized_session({}, prompt=lambda _q: "CANCEL")
    assert calls[:2] == ["helpers", "pins"]


def test_macos_notification_is_fixed_bounded_and_never_shell_interpolated():
    calls = []

    class Result:
        returncode = 0

    result = controller.notify_terminal("complete", run=lambda *args, **kwargs: calls.append((args, kwargs)) or Result())
    assert result == "DELIVERED"
    argv = calls[0][0][0]
    assert argv[0] == "/usr/bin/osascript"
    assert "normal vehicle power-off was confirmed" in argv[-1]
    assert calls[0][1]["timeout"] == 5
    assert "shell" not in calls[0][1]
    assert controller.notify_terminal("untrusted-content") == "NOT_SENT_INVALID_STATUS"


def test_macos_notification_failure_is_reported_not_raised():
    result = controller.notify_terminal("stopped", run=lambda *_a, **_k: (_ for _ in ()).throw(OSError("unavailable")))
    assert result.startswith("FAILED")


def test_unknown_fault_rejected():
    with pytest.raises(controller.ControllerError, match="unknown"):
        controller.simulate_fault("make-it-work")


def test_new_run_values_are_fresh_and_shape_valid():
    first = controller.new_run_identifiers()
    second = controller.new_run_identifiers()
    assert len(first["run_id"]) == len(first["nonce"]) == 32
    assert first["issued_at_utc"] and first["expires_at_utc"]


def test_studio_readiness_does_not_turn_simulator_success_into_experiment_success():
    report = controller.dry_run_report()
    studio = report["studio_readiness"]
    assert studio["current_objective"]["question"]
    assert studio["latest_evidence"]["conclusion"].startswith("Zero-persistent-write is not proven")
    assert studio["experiment_ready"]["live_execution"] == "NOT_AUTHORIZED_FOR_ANY_CURRENT_SESSION"
    assert studio["experiment_ready"]["live_backend"] == "AUTHORIZATION_GATED_AND_DISABLED"
    assert studio["run_experiment"]["enabled"] is False
    assert studio["results"]["campaign_success"] is False
    assert studio["next_iteration"]["live_action"] == "NONE_UNTIL_REVIEW_AND_OWNER_AUTHORIZATION"
