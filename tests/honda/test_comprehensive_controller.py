from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/honda-readonly-preflight"))
import comprehensive_controller as controller
import comprehensive_replay as replay

_REAL_CANDIDATE_COMMIT = controller._candidate_commit


@pytest.fixture(autouse=True)
def _unit_tests_use_synthetic_main_revision(monkeypatch):
    """Live-path unit tests use an injected local revision; the F5 test exercises the real gate."""
    monkeypatch.setattr(controller, "_candidate_commit", controller._head_sha)


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


def test_full_offline_simulation_walks_all_ten_states_and_162_commands():
    report = controller.simulate()
    assert report["simulated_state_count"] == 10
    assert report["simulated_command_count"] == 162
    assert report["command_shapes"] == 45
    assert len([item for item in report["capture_schedule"]
                if item["phase"] == "phase4_three_state_carplay"]) == 10
    assert all(item["owner_confirmation_required"] for item in report["capture_schedule"])
    assert report["live_evidence"] is False
    assert report["campaign_success"] is False


def test_prepare_migrates_without_overwriting_and_never_sets_readiness_true(tmp_path, monkeypatch):
    runtime = tmp_path / "private runtime with spaces"
    runtime.mkdir(mode=0o700)
    evidence = runtime / "evidence"
    draft = runtime / "authorization-draft.json"
    draft.write_text(json.dumps({
        "campaign_id": controller.CAMPAIGN_ID,
        "review_artifact_paths": {"technical": "/old/review.json"},
        "required_review_types": ["technical", "qualified_vehicle_safety"],
        "reviewed_commit_sha": "d" * 40,
        "readiness_answer": "stale owner answer",
        "live_execution_enabled": False,
        "readiness_checks": {"owner_present": True},
        "evidence_destination_checklist": {"cloud_sync_disabled": True},
        "owner_verified_vehicle_reference": "stale-private-reference",
        "factory_restoration_reference": "stale baseline",
        "adb_transport_details": "private Wi-Fi route; local identifiers omitted",
    }))
    draft.chmod(0o600)
    original = draft.read_bytes()
    monkeypatch.setattr(controller, "PRIVATE_RUNTIME_ROOT", runtime)
    monkeypatch.setattr(controller, "_review_inventory",
                        lambda *_: ({}, {}, [{"review_type": "technical", "structurally_valid": True,
                                          "exact_current_commit": False}]))
    candidate_path = runtime / "candidate.json"
    result = controller.prepare_candidate(draft_path=draft, evidence_path=evidence,
                                          output_path=candidate_path)
    candidate = json.loads(candidate_path.read_text())
    assert draft.read_bytes() == original
    assert candidate_path.stat().st_mode & 0o777 == 0o600
    assert candidate["preparation_only"] is True
    assert candidate["live_execution_enabled"] is False
    assert candidate["owner_confirmed"] is False
    assert candidate["approved_power_mode"] == controller.APPROVED_POWER_MODE
    assert candidate["exact_vehicle_identity_confirmed"] is False
    assert candidate["technical_reviewer_independence_verified"] is False
    assert candidate["owner_safety_assessment_acknowledged"] is False
    assert all(value is False for value in candidate["readiness_checks"].values())
    assert all(value is False for value in candidate["evidence_destination_checklist"].values())
    assert "review_artifact_paths" not in candidate
    assert "required_review_types" not in candidate
    assert candidate["reviewed_commit_sha"] == controller._head_sha()
    assert candidate["review_artifact_sha256"] == {}
    assert candidate["owner_verified_vehicle_reference"] == "stale-private-reference"
    assert candidate["factory_restoration_reference"] == "stale baseline"
    assert candidate["adb_transport_details"] == "private Wi-Fi route; local identifiers omitted"
    assert set(candidate["owner_reconfirmation_required"]) == {
        "owner_verified_vehicle_reference", "factory_restoration_reference", "adb_transport_details"}
    assert "readiness_answer" not in candidate
    assert result["campaign_command_count"] == 162
    assert result["command_shapes"] == 45
    assert result["verified_source_count"] == len(result["source_hashes"]) == 33
    assert result["source_revision"] == controller._head_sha()
    assert result["origin_main_revision"] == controller._origin_main_sha()
    expected_main_match = result["source_revision"] == result["origin_main_revision"]
    assert result["head_matches_origin_main"] is expected_main_match
    if expected_main_match:
        assert result["source_revision_warning"] is None
    else:
        assert "HEAD is not origin/main" in result["source_revision_warning"]
    assert evidence.stat().st_mode & 0o777 == 0o700


def test_prepare_refuses_to_overwrite_candidate(tmp_path, monkeypatch):
    runtime = tmp_path / "private-runtime"
    runtime.mkdir(mode=0o700)
    existing = runtime / "candidate.json"
    existing.write_text("preserve")
    existing.chmod(0o600)
    monkeypatch.setattr(controller, "PRIVATE_RUNTIME_ROOT", runtime)
    monkeypatch.setattr(controller, "_review_inventory", lambda *_: ({}, {}, []))
    with pytest.raises(controller.ControllerError, match="destination already exists"):
        controller.prepare_candidate(draft_path=runtime / "absent.json",
                                     evidence_path=runtime / "evidence", output_path=existing)
    assert existing.read_text() == "preserve"


def test_prepare_rejects_dangling_private_draft_symlink_without_creating_outputs(tmp_path, monkeypatch):
    runtime = tmp_path / "private-runtime"
    runtime.mkdir(mode=0o700)
    draft = runtime / "authorization-draft.json"
    draft.symlink_to(runtime / "missing-target.json")
    evidence = runtime / "evidence"
    output = runtime / "candidate.json"
    monkeypatch.setattr(controller, "PRIVATE_RUNTIME_ROOT", runtime)
    with pytest.raises(controller.ControllerError):
        controller.prepare_candidate(draft_path=draft, evidence_path=evidence,
                                     output_path=output)
    assert draft.is_symlink()
    assert not evidence.exists()
    assert not output.exists()


def test_private_draft_must_be_outside_the_repository(tmp_path, monkeypatch):
    repository = tmp_path / "repository with spaces"
    repository.mkdir()
    draft = repository / "draft.json"
    draft.write_text("{}")
    draft.chmod(0o600)
    monkeypatch.setattr(controller, "ROOT", repository)
    with pytest.raises(controller.ControllerError, match="must stay outside the repository"):
        controller._read_private_json(draft)


def test_prepare_rejects_symlinked_evidence_path(tmp_path, monkeypatch):
    runtime = tmp_path / "private-runtime"
    runtime.mkdir(mode=0o700)
    actual = runtime / "actual"
    actual.mkdir(mode=0o700)
    alias = runtime / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    monkeypatch.setattr(controller, "PRIVATE_RUNTIME_ROOT", runtime)
    monkeypatch.setattr(controller, "_review_inventory", lambda *_: ({}, {}, []))
    with pytest.raises(controller.ControllerError, match="symbolic link"):
        controller.prepare_candidate(draft_path=runtime / "absent.json", evidence_path=alias,
                                     output_path=runtime / "candidate.json")


def test_private_directory_rejects_existing_world_accessible_directory_without_chmod(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=0o700)
    unsuitable = runtime / "already-public"
    unsuitable.mkdir(mode=0o755)
    before = unsuitable.stat()
    with pytest.raises(controller.ControllerError, match="mode 0700"):
        controller._private_directory(unsuitable, create=True)
    after = unsuitable.stat()
    assert after.st_mode == before.st_mode
    assert after.st_mtime_ns == before.st_mtime_ns


def test_private_directory_rejects_repository_docs_before_mutation(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    docs = repository / "docs"
    docs.mkdir(parents=True, mode=0o755)
    docs.chmod(0o755)
    before = docs.stat()
    monkeypatch.setattr(controller, "ROOT", repository)
    with pytest.raises(controller.ControllerError, match="outside the repository"):
        controller._private_directory(docs, create=True)
    after = docs.stat()
    assert after.st_mode == before.st_mode
    assert after.st_mtime_ns == before.st_mtime_ns


def _case_variant_or_skip(path: Path) -> Path:
    variant = Path(str(path).swapcase())
    try:
        aliases_same_directory = os.path.samefile(path, variant)
    except OSError:
        aliases_same_directory = False
    if not aliases_same_directory:
        pytest.skip("case-variant alias requires a case-insensitive filesystem")
    return variant


def test_private_directory_rejects_exact_repository_root(tmp_path, monkeypatch):
    repository = tmp_path / "Repository"
    repository.mkdir(mode=0o700)
    repository.chmod(0o700)
    before = repository.stat()
    monkeypatch.setattr(controller, "ROOT", repository)
    with pytest.raises(controller.ControllerError, match="outside the repository"):
        controller._private_directory(repository, create=True)
    after = repository.stat()
    assert after.st_mode == before.st_mode
    assert after.st_mtime_ns == before.st_mtime_ns


def test_private_directory_rejects_existing_owner_only_directory_inside_repository(tmp_path, monkeypatch):
    repository = tmp_path / "Repository"
    repository.mkdir(mode=0o700)
    repository.chmod(0o700)
    private = repository / "private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    before = private.stat()
    monkeypatch.setattr(controller, "ROOT", repository)

    with pytest.raises(controller.ControllerError, match="outside the repository"):
        controller._private_directory(private, create=True)

    after = private.stat()
    assert after.st_mode == before.st_mode
    assert after.st_mtime_ns == before.st_mtime_ns
    assert list(private.iterdir()) == []


def test_private_directory_rejects_case_variant_existing_private_repository_path(tmp_path, monkeypatch):
    repository = tmp_path / "SyntheticRepository"
    repository.mkdir(mode=0o700)
    repository.chmod(0o700)
    private = repository / "private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    sentinel = private / "keep.json"
    sentinel.write_text("preserve")
    sentinel.chmod(0o600)
    before_repository = repository.stat()
    before_private = private.stat()
    before_sentinel = sentinel.stat()
    monkeypatch.setattr(controller, "ROOT", repository)
    alias = _case_variant_or_skip(repository) / "private"

    with pytest.raises(controller.ControllerError, match="outside the repository"):
        controller._private_directory(alias, create=True)

    assert private.stat().st_mode == before_private.st_mode
    assert private.stat().st_mtime_ns == before_private.st_mtime_ns
    assert repository.stat().st_mtime_ns == before_repository.st_mtime_ns
    assert sentinel.stat().st_mode == before_sentinel.st_mode
    assert sentinel.stat().st_mtime_ns == before_sentinel.st_mtime_ns
    assert sentinel.read_text() == "preserve"


def test_private_directory_rejects_case_variant_missing_repository_leaf_without_creation(
        tmp_path, monkeypatch):
    repository = tmp_path / "SyntheticRepository"
    repository.mkdir(mode=0o700)
    repository.chmod(0o700)
    monkeypatch.setattr(controller, "ROOT", repository)
    alias = _case_variant_or_skip(repository)
    missing = alias / "new-private-leaf"

    with pytest.raises(controller.ControllerError, match="outside the repository"):
        controller._private_directory(missing, create=True)

    assert not (repository / "new-private-leaf").exists()


@pytest.mark.parametrize("guard", ["draft_or_review", "authorization", "evidence"])
def test_case_variant_repository_path_rejected_by_every_private_read_guard(
        tmp_path, monkeypatch, guard):
    repository = tmp_path / "SyntheticRepository"
    repository.mkdir(mode=0o700)
    repository.chmod(0o700)
    private = repository / "private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    file_path = private / "record.json"
    file_path.write_text(json.dumps({"schema": controller.SESSION_AUTHORIZATION_SCHEMA,
                                     "preparation_only": False}))
    file_path.chmod(0o600)
    monkeypatch.setattr(controller, "ROOT", repository)
    alias_path = _case_variant_or_skip(repository) / "private" / "record.json"

    with pytest.raises(controller.ControllerError, match="outside the repository"):
        if guard == "draft_or_review":
            controller._read_private_json(alias_path)
        elif guard == "authorization":
            controller._load_private_authorization(alias_path)
        else:
            controller._private_evidence_directory({"evidence_directory": str(alias_path.parent)})


def test_live_review_validation_rejects_case_variant_repository_artifact(tmp_path, monkeypatch):
    current_pins = controller.pins()
    candidate_commit = controller._candidate_commit()
    repository = tmp_path / "SyntheticRepository"
    repository.mkdir(mode=0o700)
    repository.chmod(0o700)
    private = repository / "private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    artifact = private / "technical-review.json"
    artifact.write_text("{}")
    artifact.chmod(0o600)
    monkeypatch.setattr(controller, "ROOT", repository)
    monkeypatch.setattr(controller, "_candidate_commit", lambda: candidate_commit)
    alias = _case_variant_or_skip(repository) / "private" / artifact.name
    phases = ["phase4_three_state_carplay"]
    required = set(controller.PHASE_REVIEW_REQUIREMENTS[phases[0]])
    record = {
        "approved_phases": phases,
        "risk_level": "LEVEL_2",
        "reviewed_commit_sha": candidate_commit,
        "review_artifacts": {review: str(alias) for review in required},
        "review_artifact_sha256": {review: "a" * 64 for review in required},
    }

    with pytest.raises(controller.ControllerError, match="outside the repository"):
        controller._validate_live_reviews(record, current_pins)


def test_private_directory_rejects_symlinked_repository_alias(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    repository.mkdir(mode=0o700)
    repository.chmod(0o700)
    alias = tmp_path / "repository-alias"
    alias.symlink_to(repository, target_is_directory=True)
    monkeypatch.setattr(controller, "ROOT", repository)
    with pytest.raises(controller.ControllerError, match="symbolic link"):
        controller._private_directory(alias / "private", create=True)
    assert not (repository / "private").exists()


def test_private_directory_rejects_symlinked_private_parent_without_mutation(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir(mode=0o700)
    sentinel = actual / "keep.json"
    sentinel.write_text("preserve")
    sentinel.chmod(0o600)
    before = actual.stat()
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    with pytest.raises(controller.ControllerError, match="symbolic link"):
        controller._private_directory(alias / "new-leaf", create=True)
    assert actual.stat().st_mtime_ns == before.st_mtime_ns
    assert list(actual.iterdir()) == [sentinel]
    assert sentinel.read_text() == "preserve"


def test_private_directory_accepts_existing_owner_only_directory_outside_repository(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    repository.mkdir(mode=0o700)
    repository.chmod(0o700)
    private_root = tmp_path / "private-root"
    private_root.mkdir(mode=0o700)
    private_root.chmod(0o700)
    evidence = private_root / "evidence"
    evidence.mkdir(mode=0o700)
    evidence.chmod(0o700)
    monkeypatch.setattr(controller, "ROOT", repository)

    assert controller._private_directory(evidence) == evidence


def test_owner_private_file_rejects_symlinked_leaf_without_mutation(tmp_path):
    target = tmp_path / "target.json"
    target.write_text("preserve")
    target.chmod(0o600)
    alias = tmp_path / "alias.json"
    alias.symlink_to(target)

    with pytest.raises(controller.ControllerError, match="not safely contained"):
        controller._read_owner_private_file(alias, max_bytes=1024, label="test file")

    assert alias.is_symlink()
    assert target.read_text() == "preserve"
    assert target.stat().st_mode & 0o777 == 0o600


def test_owner_private_file_rejects_non_private_mode_without_chmod(tmp_path):
    path = tmp_path / "public.json"
    path.write_text("{}")
    path.chmod(0o644)
    before = path.stat()

    with pytest.raises(controller.ControllerError, match="owner-only private file"):
        controller._read_owner_private_file(path, max_bytes=1024, label="test file")

    after = path.stat()
    assert after.st_mode == before.st_mode
    assert after.st_mtime_ns == before.st_mtime_ns


def test_owner_private_file_rejects_oversize_without_mutation(tmp_path):
    path = tmp_path / "large.json"
    path.write_text("x" * 16)
    path.chmod(0o600)
    before = path.stat()

    with pytest.raises(controller.ControllerError, match="size bound"):
        controller._read_owner_private_file(path, max_bytes=8, label="test file")

    after = path.stat()
    assert after.st_mode == before.st_mode
    assert after.st_mtime_ns == before.st_mtime_ns
    assert path.read_text() == "x" * 16


def test_owner_private_file_rejects_non_regular_file(tmp_path):
    directory = tmp_path / "not-a-file"
    directory.mkdir(mode=0o700)

    with pytest.raises(controller.ControllerError, match="owner-only private file"):
        controller._read_owner_private_file(directory, max_bytes=1024, label="test file")


def test_owner_private_file_rejects_fifo_without_blocking(tmp_path):
    if not hasattr(os, "mkfifo") or not hasattr(os, "O_NONBLOCK"):
        pytest.skip("FIFO nonblocking open is unavailable on this platform")
    fifo = tmp_path / "review.json"
    os.mkfifo(fifo, 0o600)

    with pytest.raises(controller.ControllerError, match="owner-only private file"):
        controller._read_owner_private_file(fifo, max_bytes=1024, label="test file")


def test_owner_private_file_rejects_wrong_owner_without_mutation(tmp_path, monkeypatch):
    path = tmp_path / "owner.json"
    path.write_text("{}")
    path.chmod(0o600)
    before = path.stat()
    actual_uid = os.getuid()
    monkeypatch.setattr(controller.os, "getuid", lambda: actual_uid + 1)

    with pytest.raises(controller.ControllerError, match="owner-only private file"):
        controller._read_owner_private_file(path, max_bytes=1024, label="test file")

    after = path.stat()
    assert after.st_mode == before.st_mode
    assert after.st_mtime_ns == before.st_mtime_ns


def test_private_directory_revalidation_and_all_output_callers_share_containment(
        tmp_path, monkeypatch):
    repository = tmp_path / "SyntheticRepository"
    repository.mkdir(mode=0o700)
    repository.chmod(0o700)
    private = repository / "private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    before = private.stat()
    monkeypatch.setattr(controller, "ROOT", repository)
    alias = _case_variant_or_skip(repository) / "private"

    # Rechecking a valid outside directory is idempotent and does not chmod it.
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o700)
    outside.chmod(0o700)
    outside_before = outside.stat()
    controller._private_directory(outside)
    controller._private_directory(outside)
    assert outside.stat().st_mode == outside_before.st_mode
    assert outside.stat().st_mtime_ns == outside_before.st_mtime_ns

    # Ledger creation, candidate output, and evidence validation use the same guard.
    record = {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
              "authorization_id": "AUTH-12345678", "run_id": "b" * 32, "nonce": "a" * 32}
    with pytest.raises(controller.ControllerError, match="outside the repository"):
        controller.consume_once(record, ledger=alias / "consumed")
    with pytest.raises(controller.ControllerError, match="outside the repository"):
        controller.prepare_candidate(draft_path=outside / "missing-draft.json",
                                     evidence_path=outside / "missing-evidence",
                                     output_path=alias / "candidate.json")
    candidate = outside / "candidate.json"
    with pytest.raises(controller.ControllerError, match="outside the repository"):
        controller.prepare_candidate(draft_path=outside / "missing-draft.json",
                                     evidence_path=alias,
                                     output_path=candidate)

    assert not (private / "consumed").exists()
    assert not (private / "candidate.json").exists()
    assert not candidate.exists()
    assert private.stat().st_mode == before.st_mode
    assert private.stat().st_mtime_ns == before.st_mtime_ns


def test_private_directory_creates_only_one_new_owner_only_leaf(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=0o700)
    created = controller._private_directory(runtime / "evidence", create=True)
    assert created.is_dir()
    assert created.stat().st_uid == __import__("os").getuid()
    assert created.stat().st_mode & 0o777 == 0o700
    assert list(runtime.iterdir()) == [created]


def test_private_directory_rejects_wrong_owner_without_creation(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=0o700)
    intended = runtime / "evidence"
    actual_uid = __import__("os").getuid()
    monkeypatch.setattr(controller.os, "getuid", lambda: actual_uid + 1)
    with pytest.raises(controller.ControllerError, match="owner-owned"):
        controller._private_directory(intended, create=True)
    assert not intended.exists()


def test_prepare_validates_output_and_evidence_paths_before_any_creation(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=0o700)
    monkeypatch.setattr(controller, "PRIVATE_RUNTIME_ROOT", runtime)
    monkeypatch.setattr(controller, "_review_inventory", lambda *_: ({}, {}, []))
    bad_parent = runtime / "output-parent"
    bad_parent.mkdir(mode=0o755)
    bad_parent.chmod(0o755)
    missing_evidence = runtime / "evidence"
    with pytest.raises(controller.ControllerError, match="mode 0700"):
        controller.prepare_candidate(draft_path=runtime / "missing-draft.json",
                                     evidence_path=missing_evidence,
                                     output_path=bad_parent / "candidate.json")
    assert not missing_evidence.exists()

    bad_evidence = runtime / "bad-evidence"
    bad_evidence.mkdir(mode=0o755)
    bad_evidence.chmod(0o755)
    before = bad_evidence.stat()
    output = runtime / "candidate.json"
    with pytest.raises(controller.ControllerError, match="mode 0700"):
        controller.prepare_candidate(draft_path=runtime / "missing-draft.json",
                                     evidence_path=bad_evidence, output_path=output)
    assert not output.exists()
    assert bad_evidence.stat().st_mode == before.st_mode


def test_repeated_prepare_does_not_mutate_existing_or_unrelated_directories(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=0o700)
    evidence = runtime / "evidence"
    evidence.mkdir(mode=0o700)
    unrelated = runtime / "unrelated"
    unrelated.mkdir(mode=0o755)
    unrelated.chmod(0o755)
    marker = unrelated / "keep.txt"
    marker.write_text("preserve")
    marker.chmod(0o600)
    monkeypatch.setattr(controller, "PRIVATE_RUNTIME_ROOT", runtime)
    monkeypatch.setattr(controller, "_review_inventory", lambda *_: ({}, {}, []))
    evidence_before = evidence.stat()
    unrelated_before = unrelated.stat()
    marker_before = marker.read_bytes()
    for name in ("candidate-one.json", "candidate-two.json"):
        controller.prepare_candidate(draft_path=runtime / "missing-draft.json",
                                     evidence_path=evidence, output_path=runtime / name)
    assert evidence.stat().st_mode == evidence_before.st_mode
    assert evidence.stat().st_mtime_ns == evidence_before.st_mtime_ns
    assert unrelated.stat().st_mode == unrelated_before.st_mode
    assert unrelated.stat().st_mtime_ns == unrelated_before.st_mtime_ns
    assert marker.read_bytes() == marker_before


def test_prepare_stops_on_source_lock_failure_before_writing_candidate(tmp_path, monkeypatch):
    runtime = tmp_path / "private-runtime"
    runtime.mkdir(mode=0o700)
    monkeypatch.setattr(controller, "PRIVATE_RUNTIME_ROOT", runtime)
    monkeypatch.setattr(controller, "pins", lambda: (_ for _ in ()).throw(
        controller.ControllerError("synthetic source pin failure")))
    with pytest.raises(controller.ControllerError, match="synthetic source pin failure"):
        controller.prepare_candidate(draft_path=runtime / "absent.json",
                                     evidence_path=runtime / "evidence",
                                     output_path=runtime / "candidate.json")
    assert not (runtime / "candidate.json").exists()


def test_prepare_stops_when_private_storage_has_insufficient_space(tmp_path, monkeypatch):
    runtime = tmp_path / "private-runtime"
    runtime.mkdir(mode=0o700)
    monkeypatch.setattr(controller, "PRIVATE_RUNTIME_ROOT", runtime)
    monkeypatch.setattr(controller, "_review_inventory", lambda *_: ({}, {}, []))
    usage = controller.shutil.disk_usage(tmp_path)
    monkeypatch.setattr(controller.shutil, "disk_usage",
                        lambda _path: type(usage)(usage.total, usage.used, 1))
    with pytest.raises(controller.ControllerError, match="private evidence storage needs"):
        controller.prepare_candidate(draft_path=runtime / "absent.json",
                                     evidence_path=runtime / "evidence",
                                     output_path=runtime / "candidate.json")
    assert not (runtime / "candidate.json").exists()


def test_cli_preflight_and_prepare_are_offline_and_parseable(tmp_path, monkeypatch, capsys):
    evidence = tmp_path / "offline evidence"
    evidence.mkdir(mode=0o700)
    monkeypatch.setattr(controller, "DEFAULT_EVIDENCE_ROOT", evidence)
    monkeypatch.setattr(controller, "AUTHORIZATION_DRAFT", tmp_path / "missing-draft.json")
    monkeypatch.setattr(controller, "host_preflight", lambda: {
        "status": "HOST READY", "owner_status": "OWNER CHECK REQUIRED",
        "checks": {"fake": {"ok": True}}, "live_adb_launched": False,
        "device_discovery_performed": False, "authorization_consumed": False})
    assert controller.main(["preflight"]) == 0
    preflight = json.loads(capsys.readouterr().out)
    assert preflight["status"] == "HOST READY"
    assert preflight["owner_status"] == "OWNER CHECK REQUIRED"
    assert preflight["device_discovery_performed"] is False
    assert preflight["authorization_consumed"] is False


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


def test_one_session_approval_covers_only_explicit_compatible_phases(tmp_path):
    phases = ["phase1_ordinary_adb_capability", "phase4_three_state_carplay",
              "phase7_recovery_restoration"]
    categories = sorted(set().union(*(set(controller.PHASE_CATEGORIES[p]) for p in phases)))
    record = {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
              "campaign_id": controller.CAMPAIGN_ID, "approved_power_mode": controller.APPROVED_POWER_MODE,
              "approved_phases": phases,
              "approved_categories": categories, "category_permissions": _category_permissions(categories), "risk_level": "LEVEL_2",
              "live_execution_enabled": True, "pins": controller.pins(),
              "reviewed_commit_sha": controller._head_sha(), "review_artifact_sha256": {"technical": "a" * 64},
              "authorization_id": "AUTH-22334455", "run_id": "a" * 32, "nonce": "b" * 32,
              **controller.new_run_identifiers(), "owner_confirmed": True,
              "exact_adb_serial": "owner-private-serial",
              "readiness_checks": {key: True for key in ("stationary_in_park", "parking_brake_set", "owner_present", "approved_power_state", "no_abnormal_warning", "factory_displays_normal", "adb_transport_independent")},
              "adb_transport_details": "synthetic dedicated ADB route independent of CarPlay path and shared hub",
              "evidence_destination_checklist": {key: True for key in ("host_local_outside_repository", "directory_owner_only", "files_owner_only", "cloud_sync_disabled", "hash_inventory_ready")},
              "recovery_prerequisites_confirmed": True, "owner_question": "Which windows own Display 1?",
              "expected_evidence": "Bounded window/display snapshots", "known_risks": ["display state changes"], "stop_conditions": ["unexpected warning"],
              "review_artifacts": {"technical": "/tmp/technical-review.json"},
              "technical_reviewer_independence_verified": True,
              **_owner_assessment_binding(tmp_path),
              "factory_restoration_reference": "initial factory display and Navigation state",
              "exact_vehicle": "2018 Honda Clarity PHEV Touring (MY16ADA; exact unit identity must be owner-verified)",
              "exact_vehicle_identity_confirmed": True, "owner_verified_vehicle_reference": "private-reference", "evidence_directory": "/tmp/cl-private-evidence"}
    controller.validate_session_authorization(record, current_pins=controller.pins())
    record["approved_power_mode"] = "ON_READY_ABSENT"
    with pytest.raises(controller.ControllerError, match="READY-active power mode"):
        controller.validate_session_authorization(record, current_pins=controller.pins())
    record["approved_power_mode"] = controller.APPROVED_POWER_MODE
    record["approved_phases"].append("phase2_existing_root_supersu_review")
    with pytest.raises(controller.ControllerError, match="fixed campaign order"):
        controller.validate_session_authorization(record, current_pins=controller.pins())


def test_stale_inactive_power_mode_cannot_consume_one_use_authorization(tmp_path):
    record = _live_test_record(tmp_path, ["phase0_baseline_safety_identity"], controller.pins())
    record["approved_power_mode"] = "ON_READY_ABSENT"
    ledger = tmp_path / "private-ledger"
    with pytest.raises(controller.ControllerError, match="READY-active power mode"):
        controller.authorize_one_run(record, current_pins=controller.pins(), ledger=ledger)
    assert not ledger.exists()


def test_level_one_baseline_does_not_require_an_external_review():
    record = {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
              "campaign_id": controller.CAMPAIGN_ID,
              "approved_power_mode": controller.APPROVED_POWER_MODE,
              "approved_phases": ["phase0_baseline_safety_identity"],
              "approved_categories": ["owner_baseline_observation"], "category_permissions": _category_permissions([]), "risk_level": "LEVEL_1",
              "live_execution_enabled": True, "pins": controller.pins(),
              "reviewed_commit_sha": controller._head_sha(), "review_artifact_sha256": {},
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
    controller.validate_session_authorization(record, current_pins=controller.pins())


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


def test_review_record_binds_exact_commit_and_digest_for_each_required_artifact(tmp_path):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["factory_restoration_reference"] = "owner-defined factory baseline"
    assert set(record["review_artifacts"]) == {"technical"}
    assert all(Path(path).is_absolute() for path in record["review_artifacts"].values())
    assert "review_artifact_paths" not in record
    assert record["reviewed_commit_sha"] == controller._head_sha()
    assert set(record["review_artifact_sha256"]) == {"technical"}
    assert all(len(value) == 64 for value in record["review_artifact_sha256"].values())
    assert record["owner_confirmed"] is True
    assert "readiness_answer" not in record
    controller.validate_session_authorization(record, current_pins=controller.pins())


def test_controller_checks_artifact_digest_and_commit_against_owner_attestation(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import sys

    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["reviewed_commit_sha"] = "c" * 40
    record["review_artifact_sha256"] = {"technical": "a" * 64}
    seen = []

    def fake_validate(raw, **kwargs):
        seen.append((raw, kwargs["commit_sha"]))
        return {"decision": "APPROVE_ENGINEERING",
                "artifact_sha256": "a" * 64}

    monkeypatch.setattr(controller, "_candidate_commit", lambda: "c" * 40)
    monkeypatch.setitem(sys.modules, "validate_review_artifacts",
                        SimpleNamespace(validate_review_artifact_bytes=fake_validate))
    monkeypatch.setattr(controller, "_read_owner_private_file", lambda *_args, **_kwargs: b"{}")
    bindings = controller._validate_live_reviews(record, controller.pins())
    assert bindings == {"reviewed_commit_sha": "c" * 40,
                        "review_artifact_sha256": {"technical": "a" * 64}}
    assert len(seen) == 1
    assert all(commit == "c" * 40 for _, commit in seen)


def test_review_artifact_change_after_owner_yes_stops_before_one_use_consumption(tmp_path, monkeypatch):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["factory_restoration_reference"] = "owner-defined factory baseline"
    record["reviewed_commit_sha"] = controller._head_sha()
    record["review_artifact_sha256"] = {"technical": "a" * 64}
    first = {"reviewed_commit_sha": controller._head_sha(),
             "review_artifact_sha256": {"technical": "a" * 64}}
    changed = {"reviewed_commit_sha": controller._head_sha(),
               "review_artifact_sha256": {"technical": "d" * 64}}
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
    record = {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
              "campaign_id": controller.CAMPAIGN_ID,
              "approved_power_mode": controller.APPROVED_POWER_MODE,
              "approved_phases": ["phase0_baseline_safety_identity"],
              "approved_categories": ["owner_baseline_observation"], "category_permissions": _category_permissions([]), "risk_level": "LEVEL_1",
              "live_execution_enabled": True, "pins": controller.pins(),
              "reviewed_commit_sha": controller._head_sha(), "review_artifact_sha256": {},
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
    controller.validate_session_authorization(record, current_pins=controller.pins())
    record["evidence_destination_checklist"]["cloud_sync_disabled"] = False
    with pytest.raises(controller.ControllerError, match="evidence destination"):
        controller.validate_session_authorization(record, current_pins=controller.pins())


def _live_test_record(tmp_path, phases, pin_values):
    categories = sorted(set().union(*(set(controller.PHASE_CATEGORIES[p]) for p in phases)))
    required_reviews = set().union(*(set(controller.PHASE_REVIEW_REQUIREMENTS.get(p, ())) for p in phases))
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(mode=0o700)
    evidence_dir.chmod(0o700)
    review_paths = {}
    review_digests = {}
    for review in sorted(required_reviews):
        artifact = tmp_path / f"{review}.json"
        review_digests[review] = _write_review_artifact(artifact, review)
        review_paths[review] = str(artifact)
    owner_binding = _owner_assessment_binding(tmp_path)
    return {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
            "campaign_id": controller.CAMPAIGN_ID, "approved_power_mode": controller.APPROVED_POWER_MODE,
            "approved_phases": phases,
            "approved_categories": categories, "category_permissions": _category_permissions(categories),
            "risk_level": f"LEVEL_{max(controller.PHASE_RISK_LEVELS[p] for p in phases)}",
              "live_execution_enabled": True,
              "pins": pin_values,
            "reviewed_commit_sha": controller._head_sha(),
            "review_artifact_sha256": review_digests,
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
            "review_artifacts": review_paths,
            "technical_reviewer_independence_verified": True,
            **owner_binding}


def _owner_assessment_binding(directory):
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        directory.chmod(0o700)
    except OSError:
        pass
    path = directory / "owner-assessment.json"
    assessment = {
        "schema": controller.OWNER_SELF_ASSESSMENT_SCHEMA,
        "record_type": "owner_self_assessment_not_qualified_review",
        "campaign_id": controller.CAMPAIGN_ID,
        "owner_name": "Test Owner",
        "attestation_date": "2026-11-01",
        "source_commit": controller._head_sha(),
        "pins": {"profile_sha256": controller.pins()["profile_sha256"],
                 "source_lock_sha256": controller.pins()["source_lock_sha256"],
                 "manifest_sha256": controller.pins()["command_manifest_sha256"]},
        "approved_power_mode": controller.APPROVED_POWER_MODE,
        "approved_phases": ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
                            "phase4_three_state_carplay", "phase7_recovery_restoration"],
        "assessment_type": "Owner self-assessment; no separate qualified independent human review was performed.",
        "independent_qualified_review_status": "NOT_SATISFIED",
        "findings_as_reported": ["Owner considers the documented parked READY-active procedure suitable."],
        "qualification_basis_as_reported": "Owner self-assessment; not a professional qualification claim.",
        "measurement_status": "No independent physical measurements are represented.",
    }
    path.write_text(json.dumps(assessment))
    path.chmod(0o600)
    return {"owner_self_assessment_path": str(path),
            "owner_self_assessment_owner": "Test Owner",
            "owner_self_assessment_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "owner_safety_assessment_acknowledged": True}


def test_ready_active_owner_self_assessment_is_bound_and_explicit_not_independent(tmp_path):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["factory_restoration_reference"] = "owner-defined factory baseline"
    assert controller._validate_owner_self_assessment(record) == record["owner_self_assessment_sha256"]
    record["owner_safety_assessment_acknowledged"] = False
    with pytest.raises(controller.ControllerError, match="explicit responsibility acknowledgment"):
        controller.validate_session_authorization(record, current_pins=controller.pins())


def test_phase_four_keeps_exact_source_technical_review_but_drops_qualified_human_gate():
    assert controller.PHASE_REVIEW_REQUIREMENTS["phase4_three_state_carplay"] == ("technical",)


def test_old_session_schema_and_qualified_credential_claim_are_rejected(tmp_path):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["factory_restoration_reference"] = "owner-defined factory baseline"
    record["schema"] = "claritylink-comprehensive-session-authorization-v1"
    with pytest.raises(controller.ControllerError, match="final session schema"):
        controller.validate_session_authorization(record, current_pins=controller.pins())
    record["schema"] = controller.SESSION_AUTHORIZATION_SCHEMA
    record["qualified_safety_reviewer_credentials_verified"] = True
    with pytest.raises(controller.ControllerError, match="not qualified-review credentials"):
        controller.validate_session_authorization(record, current_pins=controller.pins())


@pytest.mark.parametrize("mutation", ["owner", "schema", "campaign", "power", "phases", "review_claim"])
def test_owner_self_assessment_rejects_wrong_identity_or_scope(tmp_path, mutation):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["factory_restoration_reference"] = "owner-defined factory baseline"
    path = Path(record["owner_self_assessment_path"])
    assessment = json.loads(path.read_text())
    field_value = {
        "owner": ("different owner", "owner_name"),
        "schema": ("qualified_vehicle_safety", "record_type"),
        "campaign": ("other campaign", "campaign_id"),
        "power": ("READY_ABSENT", "approved_power_mode"),
        "phases": (["phase4_three_state_carplay"], "approved_phases"),
        "review_claim": ("SATISFIED: independent qualified review", "independent_qualified_review_status"),
    }
    value, key = field_value[mutation]
    assessment[key] = value
    path.write_text(json.dumps(assessment))
    path.chmod(0o600)
    record["owner_self_assessment_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(controller.ControllerError, match="does not match|cannot claim"):
        controller.validate_session_authorization(record, current_pins=controller.pins())


def test_changed_owner_self_assessment_after_ack_fails_before_one_use_ledger(tmp_path):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["factory_restoration_reference"] = "owner-defined factory baseline"
    path = Path(record["owner_self_assessment_path"])
    path.write_text(path.read_text() + " ")
    path.chmod(0o600)
    ledger = tmp_path / "ledger"
    with pytest.raises(controller.ControllerError, match="bytes changed"):
        controller.authorize_one_run(record, current_pins=controller.pins(), ledger=ledger)
    assert not ledger.exists()


def _write_review_artifact(path, review_type, *, decision="APPROVE_ENGINEERING", phases=None,
                           risk="LEVEL_2", reviewer_name="independent-reviewer-1"):
    reviewer = {"reviewer_class": "independent_technical_reviewer", "provider": "Claude"}
    if review_type == "qualified_vehicle_safety":
        reviewer = {"reviewer_class": "qualified_vehicle_safety_reviewer", "provider": "Human"}
    pins = controller.pins()
    value = {"campaign_id": controller.CAMPAIGN_ID, "review_type": review_type, **reviewer,
             "reviewer_name_or_id": reviewer_name,
             "reviewed_commit_sha": controller._head_sha(),
             "profile_sha256": pins["profile_sha256"],
             "source_lock_sha256": pins["source_lock_sha256"],
             "manifest_sha256": pins["command_manifest_sha256"],
             "reviewed_phases": phases or ["phase0_baseline_safety_identity",
                                            "phase1_ordinary_adb_capability",
                                            "phase4_three_state_carplay",
                                            "phase7_recovery_restoration"],
             "risk_level": risk, "review_date": "2026-11-01",
             "decision": decision, "findings": []}
    value["artifact_sha256"] = hashlib.sha256(
        (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()).hexdigest()
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    path.chmod(0o600)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_review_inventory_rejects_request_changes_and_malformed_artifact(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=0o700)
    review_dir = runtime / "reviews"
    review_dir.mkdir(mode=0o700)
    monkeypatch.setattr(controller, "PRIVATE_RUNTIME_ROOT", runtime)
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    _write_review_artifact(review_dir / "technical.json", "technical", decision="REQUEST_CHANGES")
    _write_review_artifact(review_dir / "safety.json", "qualified_vehicle_safety")
    (review_dir / "malformed.json").write_text("{not-json")
    (review_dir / "malformed.json").chmod(0o600)
    paths, digests, report = controller._review_inventory(controller.pins(), phases)
    assert "technical" not in paths and "technical" not in digests
    assert "qualified_vehicle_safety" not in paths
    assert any(item.get("status") == "VALID_NON_APPROVAL"
               and item.get("decision") == "REQUEST_CHANGES" for item in report)
    assert any(item.get("decision") == "INVALID" for item in report)
    assert any("does not prove reviewer identity" in item.get("authenticity_limit", "")
               for item in report)


def test_review_inventory_reports_ambiguity_instead_of_selecting(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=0o700)
    review_dir = runtime / "reviews"
    review_dir.mkdir(mode=0o700)
    monkeypatch.setattr(controller, "PRIVATE_RUNTIME_ROOT", runtime)
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    _write_review_artifact(review_dir / "technical-a.json", "technical")
    _write_review_artifact(review_dir / "technical-b.json", "technical")
    _write_review_artifact(review_dir / "safety.json", "qualified_vehicle_safety")
    paths, digests, report = controller._review_inventory(controller.pins(), phases)
    assert "technical" not in paths and "technical" not in digests
    assert "qualified_vehicle_safety" not in paths
    assert {item.get("status") for item in report if item.get("review_type") == "technical"} == {
        "VALID_APPROVAL", "AMBIGUOUS"}


def test_review_artifact_replacement_with_another_valid_review_fails_digest_binding(tmp_path):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    review_dir = tmp_path / "reviews"
    review_dir.mkdir(mode=0o700)
    technical = review_dir / "technical.json"
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["reviewed_commit_sha"] = controller._head_sha()
    record["review_artifacts"] = {"technical": str(technical)}
    record["review_artifact_sha256"] = {"technical": _write_review_artifact(technical, "technical")}
    first = controller._validate_live_reviews(record, controller.pins())
    assert first["review_artifact_sha256"] == record["review_artifact_sha256"]
    _write_review_artifact(technical, "technical", reviewer_name="independent-reviewer-2")
    with pytest.raises(controller.ControllerError, match="artifact bytes changed"):
        controller._validate_live_reviews(record, controller.pins())


@pytest.mark.parametrize("digest", [None, "not-a-sha256", "a" * 63])
def test_authorization_rejects_missing_or_malformed_review_digest(tmp_path, digest):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["factory_restoration_reference"] = "owner-defined factory baseline"
    if digest is None:
        record.pop("review_artifact_sha256")
    else:
        record["review_artifact_sha256"]["technical"] = digest
    with pytest.raises(controller.ControllerError, match="digest bindings"):
        controller.validate_session_authorization(record, current_pins=controller.pins())


def test_authorization_rejects_review_commit_change_and_extra_manual_review_types(tmp_path):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["factory_restoration_reference"] = "owner-defined factory baseline"
    record["reviewed_commit_sha"] = "0" * 40
    with pytest.raises(controller.ControllerError, match="reviewed source commit"):
        controller.validate_session_authorization(record, current_pins=controller.pins())
    record["reviewed_commit_sha"] = controller._head_sha()
    record["required_review_types"] = ["technical"]
    with pytest.raises(controller.ControllerError, match="derived from the approved phases"):
        controller.validate_session_authorization(record, current_pins=controller.pins())


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
    monkeypatch.setattr(controller, "_candidate_commit", _REAL_CANDIDATE_COMMIT)
    monkeypatch.setattr(controller.subprocess, "run", lambda *_a, **_k: Result())
    with pytest.raises(controller.ControllerError, match="clean worktree"):
        controller._candidate_commit()


def test_live_commit_gate_rejects_clean_unmerged_branch(monkeypatch):
    outputs = iter(("", "c" * 40, "b" * 40))
    class Result:
        returncode = 0
        def __init__(self, stdout):
            self.stdout = stdout
    def run(*_args, **_kwargs):
        return Result(next(outputs))
    monkeypatch.setattr(controller, "_candidate_commit", _REAL_CANDIDATE_COMMIT)
    monkeypatch.setattr(controller.subprocess, "run", run)
    with pytest.raises(controller.ControllerError, match="unmerged checkout"):
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
    prompts = []
    messages = []
    def factory(_serial):
        def execute(command):
            calls.append(command)
            return 0, _synthetic_phase1_output(command.argv), b""
        return execute
    answers = iter(("YES", "READY", "POWERED_OFF"))
    result = controller._execute_authorized_session(
        record, ledger=tmp_path / "ledger", prompt=lambda message: prompts.append(message) or next(answers),
        output=lambda message: messages.append(message), executor_factory=factory,
        review_verifier=lambda _record, _pins: None, notify=lambda _status: "DELIVERED",
    )
    assert result["status"] == "SESSION_COMPLETE_PENDING_OFFLINE_ANALYSIS"
    assert result["campaign_success"] is False
    assert result["command_count"] == 19
    assert result["normal_power_off_confirmed"] is True
    assert "power system is ON with READY active" in prompts[0]
    assert "READY absent" not in prompts[0]
    assert "Confirm READY remains active" in prompts[1]
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
    assert binding == {"review_bindings": {"reviewed_commit_sha": controller._head_sha(),
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
    record["technical_reviewer_independence_verified"] = True
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


def test_preparation_candidate_cannot_run_consume_or_issue_adb_even_if_flags_are_toggled(tmp_path, monkeypatch):
    candidate = tmp_path / "candidate.json"
    value = {"schema": controller.PREPARATION_SCHEMA, "preparation_only": True,
             "owner_confirmed": True, "live_execution_enabled": True}
    candidate.write_text(json.dumps(value))
    candidate.chmod(0o600)
    adb_calls = []
    monkeypatch.setattr(controller, "_execute_authorized_session",
                        lambda *_a, **_k: pytest.fail("candidate reached the executor"))
    with pytest.raises(controller.ControllerError, match="preparation-only candidates"):
        controller.execute_live(candidate)
    with pytest.raises(controller.ControllerError, match="cannot consume one-use"):
        controller.consume_once({**value, "authorization_id": "AUTH-12345678",
                                 "run_id": "a" * 32, "nonce": "b" * 32},
                               ledger=tmp_path / "ledger")
    assert adb_calls == []
    assert not (tmp_path / "ledger").exists()


def test_authorization_must_match_phase_and_exact_category_set(tmp_path):
    phase = "phase4_three_state_carplay"
    approval = {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
                "campaign_id": controller.CAMPAIGN_ID, "approved_power_mode": controller.APPROVED_POWER_MODE,
                "approved_phases": [phase],
                "approved_categories": list(controller.PHASE_CATEGORIES[phase]),
                "category_permissions": _category_permissions(controller.PHASE_CATEGORIES[phase]),
                "live_execution_enabled": True, "pins": controller.pins(),
                "reviewed_commit_sha": controller._head_sha(),
                "review_artifact_sha256": {"technical": "a" * 64},
                "authorization_id": "AUTH-12345678", "nonce": "a" * 32,
                "run_id": "b" * 32, **controller.new_run_identifiers(),
                "exact_adb_serial": "owner-private-serial",
                "risk_level": "LEVEL_2", "owner_confirmed": True,                 "readiness_checks": {key: True for key in ("stationary_in_park", "parking_brake_set", "owner_present", "approved_power_state", "no_abnormal_warning", "factory_displays_normal", "adb_transport_independent")},
              "adb_transport_details": "synthetic dedicated ADB route independent of CarPlay path and shared hub",
                "evidence_destination_checklist": {key: True for key in ("host_local_outside_repository", "directory_owner_only", "files_owner_only", "cloud_sync_disabled", "hash_inventory_ready")},
                "recovery_prerequisites_confirmed": True, "owner_question": "What changes after reconnect?",
                "expected_evidence": "Bounded lifecycle comparison", "known_risks": ["stock CarPlay state transition"], "stop_conditions": ["unexpected warning"],
                "factory_restoration_reference": "initial factory display and Navigation state",
                "review_artifacts": {"technical": "/tmp/technical-review.json"},
                "technical_reviewer_independence_verified": True,
                **_owner_assessment_binding(tmp_path),
                  "factory_restoration_reference": "factory baseline",
                "exact_vehicle": "2018 Honda Clarity PHEV Touring (MY16ADA; exact unit identity must be owner-verified)",
              "exact_vehicle_identity_confirmed": True, "owner_verified_vehicle_reference": "private-reference", "evidence_directory": "/tmp/cl-private-evidence"}
    controller.validate_authorization(approval, requested_phase=phase, current_pins=controller.pins())
    approval["approved_categories"] = ["ordinary_unprivileged_adb"]
    with pytest.raises(controller.ControllerError, match="exactly its phase category set"):
        controller.validate_authorization(approval, requested_phase=phase, current_pins=controller.pins())


@pytest.mark.parametrize("phase", sorted(controller.BLOCKED_PHASES))
def test_privileged_phase_authorization_remains_blocked(phase):
    with pytest.raises(controller.ControllerError, match="no currently justified"):
        controller.validate_authorization({}, requested_phase=phase, current_pins={})


def test_stale_source_pins_rejected():
    phase = "phase1_ordinary_adb_capability"
    approval = {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
                "campaign_id": controller.CAMPAIGN_ID, "approved_power_mode": controller.APPROVED_POWER_MODE,
                "approved_phases": [phase],
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
    approval = {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
                "campaign_id": controller.CAMPAIGN_ID, "approved_power_mode": controller.APPROVED_POWER_MODE,
                "approved_phases": [phase],
                "approved_categories": list(controller.PHASE_CATEGORIES[phase]),
                "category_permissions": _category_permissions(controller.PHASE_CATEGORIES[phase]),
                "live_execution_enabled": True, "pins": controller.pins(),
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
        controller.validate_authorization(approval, requested_phase=phase, current_pins=controller.pins())


def test_invalid_authorization_does_not_consume_a_ledger_marker(tmp_path):
    record = {"authorization_id": "AUTH-12345678", "run_id": "b" * 32, "nonce": "a" * 32}
    with pytest.raises(controller.ControllerError):
        controller.authorize_one_run(record, current_pins={}, ledger=tmp_path / "ledger")
    assert not (tmp_path / "ledger").exists()


def test_one_use_ledger_is_private_and_replay_resistant(tmp_path):
    record = {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
              "authorization_id": "AUTH-12345678", "run_id": "b" * 32, "nonce": "a" * 32}
    ledger = tmp_path / "private-ledger"
    marker = controller.consume_once(record, ledger=ledger)
    assert ledger.stat().st_mode & 0o777 == 0o700
    assert marker.stat().st_mode & 0o777 == 0o600
    with pytest.raises(controller.ControllerError, match="already been consumed"):
        controller.consume_once(record, ledger=ledger)


def test_one_use_ledger_does_not_mutate_existing_unsafe_directory(tmp_path):
    record = {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
              "authorization_id": "AUTH-12345678", "run_id": "b" * 32, "nonce": "a" * 32}
    ledger = tmp_path / "shared-ledger"
    ledger.mkdir(mode=0o755)
    ledger.chmod(0o755)
    before = ledger.stat()
    with pytest.raises(controller.ControllerError, match="mode 0700"):
        controller.consume_once(record, ledger=ledger)
    after = ledger.stat()
    assert after.st_mode == before.st_mode
    assert after.st_mtime_ns == before.st_mtime_ns
    assert list(ledger.iterdir()) == []


def test_one_use_ledger_requires_owner_owned_directory_without_chmod(tmp_path, monkeypatch):
    from types import SimpleNamespace

    record = {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
              "authorization_id": "AUTH-12345678", "run_id": "b" * 32, "nonce": "a" * 32}
    ledger = tmp_path / "private-ledger"
    ledger.mkdir(mode=0o700)
    ledger.chmod(0o700)
    before = ledger.stat()
    actual_uid = os.getuid()
    monkeypatch.setattr(controller.pwd, "getpwuid",
                        lambda _uid: SimpleNamespace(pw_dir=str(tmp_path)))
    monkeypatch.setattr(controller.os, "getuid", lambda: actual_uid + 1)
    with pytest.raises(controller.ControllerError, match="owner-owned"):
        controller.consume_once(record, ledger=ledger)
    after = ledger.stat()
    assert after.st_mode == before.st_mode
    assert after.st_mtime_ns == before.st_mtime_ns
    assert list(ledger.iterdir()) == []


def test_one_use_ledger_does_not_create_missing_parent_directories(tmp_path):
    record = {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
              "authorization_id": "AUTH-12345678", "run_id": "b" * 32, "nonce": "a" * 32}
    ledger = tmp_path / "missing-parent" / "ledger"
    with pytest.raises(controller.ControllerError, match="private preparation directory"):
        controller.consume_once(record, ledger=ledger)
    assert not ledger.parent.exists()


def test_nonce_cannot_be_reused_under_a_different_authorization_id(tmp_path):
    ledger = tmp_path / "private-ledger"
    controller.consume_once({"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
                             "authorization_id": "AUTH-12345678", "run_id": "b" * 32, "nonce": "a" * 32}, ledger=ledger)
    with pytest.raises(controller.ControllerError, match="nonce has already been consumed"):
        controller.consume_once({"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
                                 "authorization_id": "AUTH-87654321", "run_id": "c" * 32, "nonce": "a" * 32}, ledger=ledger)


def test_ledger_symlink_refused(tmp_path):
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    sentinel = real / "sentinel.json"
    sentinel.write_text("preserve")
    sentinel.chmod(0o600)
    before_directory = real.stat()
    before_file = sentinel.stat()
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(controller.ControllerError, match="symbolic link"):
        controller.consume_once({"authorization_id": "AUTH-12345678", "run_id": "b" * 32,
                                 "nonce": "a" * 32, "schema": controller.SESSION_AUTHORIZATION_SCHEMA,
                                 "preparation_only": False}, ledger=link)
    after_directory = real.stat()
    after_file = sentinel.stat()
    assert after_directory.st_mtime_ns == before_directory.st_mtime_ns
    assert after_file.st_mtime_ns == before_file.st_mtime_ns
    assert after_file.st_mode == before_file.st_mode
    assert sentinel.read_text() == "preserve"
    assert list(real.iterdir()) == [sentinel]


def test_ledger_rejects_symlinked_ancestor_without_mutation(tmp_path):
    target = tmp_path / "target"
    target.mkdir(mode=0o700)
    sentinel = target / "sentinel.json"
    sentinel.write_text("preserve")
    sentinel.chmod(0o600)
    before = target.stat()
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    record = {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
              "authorization_id": "AUTH-12345678", "run_id": "b" * 32, "nonce": "a" * 32}
    with pytest.raises(controller.ControllerError, match="symbolic link"):
        controller.consume_once(record, ledger=alias / "ledger")
    after = target.stat()
    assert after.st_mtime_ns == before.st_mtime_ns
    assert list(target.iterdir()) == [sentinel]
    assert sentinel.read_text() == "preserve"


def test_ledger_rejects_dangling_symlink_without_creating_target(tmp_path):
    missing_target = tmp_path / "missing-target"
    alias = tmp_path / "dangling-ledger"
    alias.symlink_to(missing_target)
    record = {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
              "authorization_id": "AUTH-12345678", "run_id": "b" * 32, "nonce": "a" * 32}
    with pytest.raises(controller.ControllerError, match="symbolic link"):
        controller.consume_once(record, ledger=alias)
    assert alias.is_symlink()
    assert not missing_target.exists()


def test_default_one_use_ledger_fails_closed_without_creating_missing_parents(tmp_path, monkeypatch):
    runtime = Path.home() / "Library/Application Support/ClarityLink" / f"missing-ledger-test-{tmp_path.name}"
    ledger = runtime / "consumed"
    monkeypatch.setattr(controller, "PRIVATE_LEDGER", ledger)
    record = {"schema": controller.SESSION_AUTHORIZATION_SCHEMA, "preparation_only": False,
              "authorization_id": "AUTH-12345678", "run_id": "b" * 32, "nonce": "a" * 32}
    assert not runtime.exists()
    with pytest.raises(controller.ControllerError, match="private preparation directory"):
        controller.consume_once(record)
    assert not runtime.exists()


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


@pytest.mark.parametrize("mutation", ["commit", "reviewed_commit", "profile", "source_lock", "manifest", "future_date"])
def test_owner_self_assessment_is_bound_to_exact_source_and_pins(tmp_path, mutation):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["factory_restoration_reference"] = "owner-defined factory baseline"
    path = Path(record["owner_self_assessment_path"])
    assessment = json.loads(path.read_text())
    if mutation == "commit":
        assessment["source_commit"] = "0" * 40
    elif mutation == "reviewed_commit":
        record["reviewed_commit_sha"] = "0" * 40
    elif mutation == "future_date":
        assessment["attestation_date"] = "2099-01-01"
    else:
        assessment["pins"][{"profile": "profile_sha256", "source_lock": "source_lock_sha256",
                            "manifest": "manifest_sha256"}[mutation]] = "f" * 64
    path.write_text(json.dumps(assessment))
    path.chmod(0o600)
    record["owner_self_assessment_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    ledger = tmp_path / "ledger"
    with pytest.raises(controller.ControllerError, match="different source|in the future|reviewed source commit"):
        controller.authorize_one_run(record, current_pins=controller.pins(), ledger=ledger)
    assert not ledger.exists()


def test_historical_owner_assessment_date_is_accepted_without_expiration(tmp_path):
    record = _live_test_record(tmp_path, ["phase0_baseline_safety_identity",
                                         "phase1_ordinary_adb_capability",
                                         "phase4_three_state_carplay",
                                         "phase7_recovery_restoration"], controller.pins())
    record["factory_restoration_reference"] = "owner-defined factory baseline"
    path = Path(record["owner_self_assessment_path"])
    assessment = json.loads(path.read_text())
    assessment["attestation_date"] = "2000-01-01"
    path.write_text(json.dumps(assessment))
    path.chmod(0o600)
    record["owner_self_assessment_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert controller._validate_owner_self_assessment(record) == record["owner_self_assessment_sha256"]


def test_final_interactive_owner_acknowledgment_is_required_before_session(tmp_path):
    phases = ["phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
              "phase4_three_state_carplay", "phase7_recovery_restoration"]
    record = _live_test_record(tmp_path, phases, controller.pins())
    record["factory_restoration_reference"] = "owner-defined factory baseline"
    prompts = []
    commands = []
    with pytest.raises(controller.ControllerError, match="owner did not confirm session readiness"):
        controller._execute_authorized_session(
            record, ledger=tmp_path / "ledger",
            prompt=lambda message: prompts.append(message) or "NOT YET",
            output=lambda _message: None,
            executor_factory=lambda _serial: lambda command: commands.append(command),
            review_verifier=lambda _record, _pins: {
                "reviewed_commit_sha": record["reviewed_commit_sha"],
                "review_artifact_sha256": record["review_artifact_sha256"]},
            notify=lambda _status: "NOT_SENT",
        )
    assert prompts and "own self-assessment" in prompts[0]
    assert "accept responsibility" in prompts[0]
    assert commands == []
    assert not (tmp_path / "ledger").exists()
