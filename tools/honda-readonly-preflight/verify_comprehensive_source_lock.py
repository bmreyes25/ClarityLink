"""Verify the proposal-only comprehensive campaign profile and source pins."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from validate_comprehensive_proposal import validate_proposal

CAMPAIGN_ID = "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031"
BASE_MAIN_COMMIT = "563d3a9896b33f653282be97b083ef93c42c2f1a"
REQUIREMENTS_BASELINE = "CL-HONDA-RUNTIME-EVIDENCE-20261030"
PROFILE_PATH = "docs/diagnostics/comprehensive-campaign-proposal.json"
REQUIRED_SOURCE_PATHS = frozenset({
    "AGENTS.md", "docs/safety/vehicle-testing.md",
    "tools/honda-readonly-preflight/README.md",
    "docs/diagnostics/comprehensive-runtime-campaign.md",
    "docs/diagnostics/evidence-coverage.json",
    "tools/honda-readonly-preflight/display_compare.py",
    "tools/honda-readonly-preflight/evidence_coverage.py",
    "tools/honda-readonly-preflight/verify_comprehensive_source_lock.py",
    "tools/honda-readonly-preflight/validate_comprehensive_proposal.py",
    "tests/honda/test_campaign_runner.py", "tests/honda/test_display_compare.py",
    "tests/honda/test_evidence_coverage.py", "tests/honda/test_comprehensive_source_lock.py",
    "tests/honda/test_comprehensive_proposal.py",
    "tests/honda/test_validate_comprehensive_proposal.py",
    "tools/honda-readonly-preflight/campaign_runner.py",
    "tools/honda-readonly-preflight/collector.py", "tools/honda-readonly-preflight/parsers.py",
    "tools/honda-readonly-preflight/analyze.py", "tools/honda-readonly-preflight/session.py",
    "tools/honda-readonly-preflight/privileged.py",
})


def verify_lock(root: Path, lock_path: Path, *, verify_git_ancestry: bool = True) -> dict[str, Any]:
    root = root.resolve(strict=True)
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if not isinstance(lock, dict) or lock.get("schema") != "claritylink-comprehensive-source-lock-v1":
        raise ValueError("unsupported comprehensive source-lock schema")
    if lock.get("live_execution_enabled") is not False:
        raise ValueError("proposal source lock must not enable live execution")
    if lock.get("campaign_id") != CAMPAIGN_ID:
        raise ValueError("campaign id does not match the reviewed follow-up scope")
    if lock.get("requirements_baseline") != REQUIREMENTS_BASELINE:
        raise ValueError("requirements baseline does not match the approved source")
    if lock.get("base_main_commit") != BASE_MAIN_COMMIT:
        raise ValueError("base main commit does not match the approved source baseline")
    if verify_git_ancestry:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "merge-base", "--is-ancestor", BASE_MAIN_COMMIT, "HEAD"],
                capture_output=True, text=True, check=False, timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ValueError("cannot verify approved base ancestry") from error
        if result.returncode != 0:
            raise ValueError("approved main commit is not an ancestor of this checkout")
    profile = lock.get("profile")
    if not isinstance(profile, dict):
        raise ValueError("profile pin must be an object")
    profile_path = _safe_file(root, profile.get("path"))
    if profile.get("path") != PROFILE_PATH:
        raise ValueError("profile path does not match the fixed proposal path")
    profile_hash = profile.get("sha256")
    _verify_digest(profile_path, profile_hash)
    profile_data = json.loads(profile_path.read_text(encoding="utf-8"))
    try:
        validate_proposal(profile_data)
    except (ValueError, TypeError, AttributeError, KeyError) as error:
        raise ValueError("profile content does not match the validated non-executable campaign scope") from error
    sources = lock.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("source pins must be a non-empty object")
    if set(sources) != REQUIRED_SOURCE_PATHS:
        raise ValueError("source lock path set differs from the fixed reviewed scope")
    verified: dict[str, str] = {}
    for relative, digest in sorted(sources.items()):
        source_path = _safe_file(root, relative)
        _verify_digest(source_path, digest)
        verified[relative] = digest
    return {
        "campaign_id": lock.get("campaign_id"),
        "profile_sha256": profile_hash,
        "verified_source_count": len(verified),
        "source_hashes": verified,
        "live_execution_enabled": False,
    }


def _safe_file(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("source path must be a non-empty relative string")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != relative:
        raise ValueError(f"unsafe source path: {relative}")
    candidate = root / path
    if candidate.is_symlink():
        raise ValueError(f"source path must not be a symlink: {relative}")
    resolved = candidate.resolve(strict=True)
    if root not in resolved.parents or not resolved.is_file():
        raise ValueError(f"source path is not a regular repository file: {relative}")
    return resolved


def _verify_digest(path: Path, expected: Any) -> None:
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError(f"invalid SHA-256 pin for {path.name}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch: {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lock", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        result = verify_lock(args.root, args.lock)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
