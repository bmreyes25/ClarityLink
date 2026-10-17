import sys
from pathlib import Path
import subprocess
import json


TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))
import check_repo_health  # noqa: E402


def test_only_exact_indexed_image_hash_is_exempt_from_local_source_health():
    unreviewed = "tests/fixtures/repo-health/unreviewed.png"
    tracked_synthetic = "tests/fixtures/repo-health/synthetic-1x1.png"
    generated = "tests/fixtures/repo-health/run.png"
    unrelated = "docs/images/diagram.png"
    assert not check_repo_health.is_health_exempt_image(unreviewed, b"", is_indexed=False)
    assert not check_repo_health.is_health_exempt_image(unreviewed, b"")
    image = Path(tracked_synthetic).read_bytes()
    assert check_repo_health.is_health_exempt_image(tracked_synthetic, image)
    assert not check_repo_health.is_health_exempt_image(generated, b"")
    assert not check_repo_health.is_health_exempt_image(unrelated, b"")


def test_health_exception_is_content_pinned_and_is_not_publication_approval():
    path = "tests/fixtures/repo-health/synthetic-1x1.png"
    assert not check_repo_health.is_health_exempt_image(path, b"different bytes")
    import json
    manifest = json.loads(check_repo_health.PUBLIC_IMAGE_MANIFEST.read_text())
    assert manifest["schema"] == "claritylink-health-only-image-hashes-v1"
    assert "not a privacy" in manifest["classification"]


def test_generated_evidence_exemption_does_not_allow_other_binary_types():
    path = "research/vehicle/test6a-t7-integration/evidence/run.apk"
    assert not check_repo_health.is_health_exempt_image(path, b"")


def test_health_reads_staged_blob_instead_of_modified_worktree(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    candidate = tmp_path / "candidate.md"
    candidate.write_text("staged publication candidate\n")
    subprocess.run(["git", "add", "candidate.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "candidate"], cwd=tmp_path, check=True)
    candidate.write_text("unstaged private edit\n")
    monkeypatch.setattr(check_repo_health, "ROOT", tmp_path)
    assert check_repo_health.indexed_blob("candidate.md") == b"staged publication candidate\n"


def test_missing_worktree_copy_cannot_skip_staged_unsafe_status_manifest(tmp_path, monkeypatch, capsys):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    for relative in check_repo_health.REQUIRED_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if relative == "docs/status/milestones.json":
            milestones = [
                {"id": f"CL-R{number}", "state": "IN_PROGRESS" if number == 1 else "PLANNED",
                 "evidence": ["docs/status/current.md"]}
                for number in range(9)
            ]
            milestones[0]["state"] = "REVIEW_PENDING"
            content = {
                "schema_version": 1, "updated": "2026-10-17", "current_campaign": "test",
                "current_milestone": "CL-R1", "current_milestone_state": "IN_PROGRESS",
                "next_technical_milestone": "CL-R1", "safeForHonda": True,
                "milestones": milestones,
            }
            path.write_text(json.dumps(content))
        elif relative == "docs/status/cl-r0-review-scope.json":
            path.write_text(json.dumps({"approval_claimed": False,
                                        "review_status": "PENDING_INDEPENDENT_ECC_REVIEW",
                                        "files": []}))
        else:
            path.write_text("# Document\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    (tmp_path / "docs/status/milestones.json").unlink()
    monkeypatch.setattr(check_repo_health, "ROOT", tmp_path)
    result = check_repo_health.main()
    assert result == 1
    assert "status manifest must keep safeForHonda false" in capsys.readouterr().err
