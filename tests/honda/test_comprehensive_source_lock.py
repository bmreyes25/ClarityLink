import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "honda-readonly-preflight"))

import verify_comprehensive_source_lock as verifier


def make_lock(tmp_path: Path) -> tuple[Path, Path]:
    sources = {}
    for relative in verifier.REQUIRED_SOURCE_PATHS:
        source = tmp_path / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("pass\n")
        sources[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
    profile = tmp_path / verifier.PROFILE_PATH
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_bytes((ROOT / verifier.PROFILE_PATH).read_bytes())
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({
        "schema": "claritylink-comprehensive-source-lock-v1",
        "campaign_id": "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031",
        "base_main_commit": "0136ac241d94e1ebb1cc4403c07fd480728b47d6",
        "requirements_baseline": verifier.REQUIREMENTS_BASELINE,
        "live_execution_enabled": False,
        "profile": {"path": verifier.PROFILE_PATH, "sha256": hashlib.sha256(profile.read_bytes()).hexdigest()},
        "command_manifest_sha256": verifier.command_manifest_sha256(json.loads(profile.read_text())),
        "sources": sources,
    }))
    return lock, tmp_path / "AGENTS.md"


def test_source_and_profile_hashes_are_verified(tmp_path):
    lock, _ = make_lock(tmp_path)
    result = verifier.verify_lock(tmp_path, lock, verify_git_ancestry=False)
    assert result["verified_source_count"] == len(verifier.REQUIRED_SOURCE_PATHS)
    assert result["live_execution_enabled"] is False


def test_repository_comprehensive_profile_and_sources_match_pins():
    lock = ROOT / "docs/diagnostics/comprehensive-source-lock.json"
    result = verifier.verify_lock(ROOT, lock)
    assert result["campaign_id"] == "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031"
    assert result["verified_source_count"] == len(verifier.REQUIRED_SOURCE_PATHS)
    assert result["live_execution_enabled"] is False


def test_lock_cannot_drop_a_required_policy_file(tmp_path):
    lock, _ = make_lock(tmp_path)
    data = json.loads(lock.read_text())
    data["sources"].pop("AGENTS.md")
    lock.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="fixed reviewed scope"):
        verifier.verify_lock(tmp_path, lock, verify_git_ancestry=False)


def test_source_change_fails_hash_lock(tmp_path):
    lock, source = make_lock(tmp_path)
    source.write_text("changed\n")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verifier.verify_lock(tmp_path, lock, verify_git_ancestry=False)


def test_profile_path_traversal_is_rejected_before_file_access(tmp_path):
    lock, _ = make_lock(tmp_path)
    data = json.loads(lock.read_text())
    data["profile"]["path"] = "../outside"
    lock.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="unsafe source path"):
        verifier.verify_lock(tmp_path, lock, verify_git_ancestry=False)


def test_live_enabled_lock_is_rejected(tmp_path):
    lock, _ = make_lock(tmp_path)
    data = json.loads(lock.read_text())
    data["live_execution_enabled"] = True
    lock.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="must not enable live execution"):
        verifier.verify_lock(tmp_path, lock, verify_git_ancestry=False)


@pytest.mark.parametrize("key, value, expected", [
    ("campaign_id", "OTHER_CAMPAIGN", "campaign id does not match"),
    ("requirements_baseline", "OTHER_BASELINE", "requirements baseline does not match"),
    ("base_main_commit", "0" * 40, "base main commit does not match"),
])
def test_scope_and_exact_main_base_are_pinned(tmp_path, key, value, expected):
    lock, _ = make_lock(tmp_path)
    data = json.loads(lock.read_text())
    data[key] = value
    lock.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=expected):
        verifier.verify_lock(tmp_path, lock, verify_git_ancestry=False)


def test_profile_content_must_keep_live_execution_disabled(tmp_path):
    lock, _ = make_lock(tmp_path)
    data = json.loads(lock.read_text())
    profile = tmp_path / data["profile"]["path"]
    payload = json.loads(profile.read_text())
    payload["live_execution_enabled"] = True
    profile.write_text(json.dumps(payload) + "\n")
    data["profile"]["sha256"] = hashlib.sha256(profile.read_bytes()).hexdigest()
    lock.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="profile content does not match"):
        verifier.verify_lock(tmp_path, lock, verify_git_ancestry=False)


def test_source_symlink_is_rejected(tmp_path):
    lock, source = make_lock(tmp_path)
    alias_target = tmp_path / "alias-target.py"
    alias_target.write_text(source.read_text())
    source.unlink()
    source.symlink_to(alias_target)
    data = json.loads(lock.read_text())
    lock.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="must not be a symlink"):
        verifier.verify_lock(tmp_path, lock, verify_git_ancestry=False)
