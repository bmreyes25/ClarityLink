from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/honda-readonly-preflight"))
import validate_review_artifacts as review_validator
from validate_review_artifacts import validate_review_artifact


def make_artifact(path: Path, *, review_type="technical", commit="c" * 40,
                  phases=None, risk_level="LEVEL_2"):
    reviewer = {"reviewer_class": "independent_technical_reviewer", "provider": "Claude"}
    if review_type == "qualified_vehicle_safety":
        reviewer = {"reviewer_class": "qualified_vehicle_safety_reviewer", "provider": "Human"}
    value = {"campaign_id": "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031",
             "review_type": review_type, **reviewer,
             "reviewer_name_or_id": "reviewer-id", "reviewed_commit_sha": commit,
             "profile_sha256": "a" * 64, "source_lock_sha256": "b" * 64,
             "manifest_sha256": "d" * 64, "reviewed_phases": phases or ["phase4_three_state_carplay"],
             "risk_level": risk_level, "review_date": "2026-10-31",
             "decision": "APPROVE_ENGINEERING", "findings": []}
    value["artifact_sha256"] = hashlib.sha256((json.dumps(value, sort_keys=True, indent=2) + "\n").encode()).hexdigest()
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    path.chmod(0o600)
    return value


def test_exact_claude_technical_review_is_structurally_valid(tmp_path):
    path = tmp_path / "claude-review.json"
    value = make_artifact(path)
    pins = {"profile_sha256": value["profile_sha256"],
            "source_lock_sha256": value["source_lock_sha256"],
            "manifest_sha256": value["manifest_sha256"]}
    result = validate_review_artifact(path, review_type="technical", pins=pins,
                                      commit_sha="c" * 40,
                                      approved_phases=["phase4_three_state_carplay"], risk_level="LEVEL_2")
    assert result["decision"] == "APPROVE_ENGINEERING"
    assert result["artifact_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert "does not prove reviewer identity" in result["authenticity_limit"]


def test_review_digest_binds_exact_bytes_not_only_canonical_review_content(tmp_path):
    path = tmp_path / "review.json"
    value = make_artifact(path)
    pins = {"profile_sha256": value["profile_sha256"],
            "source_lock_sha256": value["source_lock_sha256"],
            "manifest_sha256": value["manifest_sha256"]}
    first = validate_review_artifact(path, review_type="technical", pins=pins,
                                    commit_sha="c" * 40,
                                    approved_phases=value["reviewed_phases"], risk_level="LEVEL_2")
    path.write_text(json.dumps(value, separators=(",", ":")) + "\n")
    path.chmod(0o600)
    second = validate_review_artifact(path, review_type="technical", pins=pins,
                                     commit_sha="c" * 40,
                                     approved_phases=value["reviewed_phases"], risk_level="LEVEL_2")
    assert first["artifact_self_digest_sha256"] == second["artifact_self_digest_sha256"]
    assert first["artifact_sha256"] != second["artifact_sha256"]


def test_safety_review_is_separately_typed(tmp_path):
    path = tmp_path / "safety-review.json"
    value = make_artifact(path, review_type="qualified_vehicle_safety")
    result = validate_review_artifact(path, review_type="qualified_vehicle_safety",
                                      pins={"profile_sha256": "a" * 64,
                                            "source_lock_sha256": "b" * 64,
                                            "manifest_sha256": "d" * 64},
                                      commit_sha="c" * 40,
                                      approved_phases=["phase4_three_state_carplay"], risk_level="LEVEL_2")
    assert result["reviewer_class"] == "qualified_vehicle_safety_reviewer"


def test_stale_commit_and_unprivate_artifact_rejected(tmp_path):
    path = tmp_path / "review.json"
    make_artifact(path)
    pins = {"profile_sha256": "a" * 64, "source_lock_sha256": "b" * 64, "manifest_sha256": "d" * 64}
    with pytest.raises(ValueError, match="exact candidate commit"):
        validate_review_artifact(path, review_type="technical", pins=pins, commit_sha="e" * 40,
                                 approved_phases=["phase4_three_state_carplay"], risk_level="LEVEL_2")
    path.chmod(0o644)
    with pytest.raises(ValueError, match="private"):
        validate_review_artifact(path, review_type="technical", pins=pins, commit_sha="c" * 40,
                                 approved_phases=["phase4_three_state_carplay"], risk_level="LEVEL_2")


def test_review_artifact_rejects_repository_path_and_wrong_owner(tmp_path, monkeypatch):
    pins = {"profile_sha256": "a" * 64, "source_lock_sha256": "b" * 64,
            "manifest_sha256": "d" * 64}
    with pytest.raises(ValueError, match="private"):
        validate_review_artifact(Path(__file__).resolve(), review_type="technical",
                                 pins=pins, commit_sha="c" * 40,
                                 approved_phases=["phase4_three_state_carplay"], risk_level="LEVEL_2")
    private_path = tmp_path / "review.json"
    make_artifact(private_path)
    actual_uid = os.getuid()
    monkeypatch.setattr(review_validator.os, "getuid", lambda: actual_uid + 1)
    with pytest.raises(ValueError, match="private"):
        validate_review_artifact(private_path, review_type="technical",
                                 pins=pins, commit_sha="c" * 40,
                                 approved_phases=["phase4_three_state_carplay"], risk_level="LEVEL_2")


@pytest.mark.parametrize("name", ["Codex-1", "codex reviewer", "implementation-agent-2"])
def test_review_artifact_rejects_agent_aliases_as_independent_reviewers(tmp_path, name):
    path = tmp_path / "review.json"
    value = make_artifact(path)
    value["reviewer_name_or_id"] = name
    value.pop("artifact_sha256")
    value["artifact_sha256"] = hashlib.sha256((json.dumps(value, sort_keys=True, indent=2) + "\n").encode()).hexdigest()
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    pins = {"profile_sha256": "a" * 64, "source_lock_sha256": "b" * 64, "manifest_sha256": "d" * 64}
    with pytest.raises(ValueError, match="independent"):
        validate_review_artifact(path, review_type="technical", pins=pins, commit_sha="c" * 40,
                                 approved_phases=["phase4_three_state_carplay"], risk_level="LEVEL_2")


def test_review_artifact_rejects_same_source_but_different_phase_scope(tmp_path):
    path = tmp_path / "review.json"
    make_artifact(path)
    pins = {"profile_sha256": "a" * 64, "source_lock_sha256": "b" * 64, "manifest_sha256": "d" * 64}
    with pytest.raises(ValueError, match="exact approved phases"):
        validate_review_artifact(path, review_type="technical", pins=pins, commit_sha="c" * 40,
                                 approved_phases=["phase6_existing_hondahack_casting"], risk_level="LEVEL_2")


def test_review_artifact_rejects_changed_source_lock_hash(tmp_path):
    path = tmp_path / "review.json"
    make_artifact(path)
    with pytest.raises(ValueError, match="source_lock_sha256"):
        validate_review_artifact(path, review_type="technical",
                                 pins={"profile_sha256": "a" * 64,
                                       "source_lock_sha256": "f" * 64,
                                       "manifest_sha256": "d" * 64},
                                 commit_sha="c" * 40,
                                 approved_phases=["phase4_three_state_carplay"], risk_level="LEVEL_2")


def test_review_artifact_rejects_changed_risk_level(tmp_path):
    path = tmp_path / "review.json"
    make_artifact(path, risk_level="LEVEL_1")
    with pytest.raises(ValueError, match="risk level"):
        validate_review_artifact(path, review_type="technical",
                                 pins={"profile_sha256": "a" * 64,
                                       "source_lock_sha256": "b" * 64,
                                       "manifest_sha256": "d" * 64},
                                 commit_sha="c" * 40,
                                 approved_phases=["phase4_three_state_carplay"], risk_level="LEVEL_2")
