"""Structural validator for exact-source review artifacts; not a review oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

REQUIRED_REVIEWERS = {
    "technical": {"reviewer_class": "independent_technical_reviewer"},
    "qualified_vehicle_safety": {"reviewer_class": "qualified_vehicle_safety_reviewer", "provider": "Human"},
}
REQUIRED = {"campaign_id", "review_type", "reviewer_class", "reviewer_name_or_id", "provider",
            "reviewed_commit_sha", "profile_sha256", "source_lock_sha256", "manifest_sha256",
            "reviewed_phases", "risk_level", "review_date", "decision", "findings", "artifact_sha256"}
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def validate_review_artifact(path: Path, *, review_type: str, pins: dict[str, str],
                             commit_sha: str, approved_phases: list[str], risk_level: str) -> dict:
    if review_type not in REQUIRED_REVIEWERS:
        raise ValueError("unknown review type")
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("review artifact must be an absolute regular private file")
    resolved = path.resolve(strict=True)
    if REPOSITORY_ROOT.resolve() == resolved or REPOSITORY_ROOT.resolve() in resolved.parents:
        raise ValueError("review artifact must be a bounded regular private file")
    fd = os.open(resolved, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as handle:
        metadata = os.fstat(handle.fileno())
        if (metadata.st_uid != os.getuid() or metadata.st_size > 2 * 1024 * 1024
                or metadata.st_mode & 0o077):
            raise ValueError("review artifact must be a bounded regular private file")
        value = json.loads(handle.read().decode("utf-8"))
    if not isinstance(value, dict) or not REQUIRED.issubset(value):
        raise ValueError("review artifact is missing required fields")
    if value["review_type"] != review_type or value.get("campaign_id") != "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031":
        raise ValueError("review artifact is for a different campaign or review type")
    if value.get("reviewed_phases") != approved_phases or value.get("risk_level") != risk_level:
        raise ValueError("review artifact does not bind the exact approved phases and risk level")
    for field, expected in REQUIRED_REVIEWERS[review_type].items():
        if value.get(field) != expected:
            raise ValueError(f"review artifact has incorrect {field}")
    if review_type == "technical" and value.get("provider") not in {"Claude", "ECC", "Human"}:
        raise ValueError("technical review provider must be Claude, ECC, or Human")
    reviewer_label = re.sub(r"[-_]+", " ", str(value.get("reviewer_name_or_id", "")).strip().lower())
    if (not reviewer_label or reviewer_label in {"owner", "self", "implementation agent"}
            or re.search(r"\bcodex(?:[-_ ]|$)", reviewer_label)
            or "implementation agent" in reviewer_label):
        raise ValueError("reviewer must be independent of the owner and implementation agent")
    if value.get("decision") not in {"APPROVE_ENGINEERING", "REQUEST_CHANGES", "BLOCKED"}:
        raise ValueError("review decision is invalid")
    if not isinstance(value.get("findings"), list) or not all(isinstance(x, str) for x in value["findings"]):
        raise ValueError("review findings must be a string list")
    if value.get("reviewed_commit_sha") != commit_sha:
        raise ValueError("review is not bound to the exact candidate commit")
    for field in ("profile_sha256", "source_lock_sha256", "manifest_sha256"):
        if value.get(field) != pins.get(field):
            raise ValueError(f"review does not bind current {field}")
    expected_artifact = value.get("artifact_sha256")
    if not isinstance(expected_artifact, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_artifact):
        raise ValueError("artifact digest is malformed")
    content = dict(value)
    content.pop("artifact_sha256")
    actual = hashlib.sha256((json.dumps(content, sort_keys=True, indent=2) + "\n").encode()).hexdigest()
    if actual != expected_artifact:
        raise ValueError("review artifact self-digest mismatch")
    return {"review_type": review_type, "decision": value["decision"],
            "reviewer_class": value["reviewer_class"], "exact_commit": commit_sha,
            "artifact_sha256": actual,
            "authenticity_limit": "structure and pins only; does not prove reviewer identity, independence, competence, or safety certification"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--review-type", required=True, choices=tuple(REQUIRED_REVIEWERS))
    parser.add_argument("--pins", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--phases", required=True, help="JSON array of the exact approved phase IDs")
    parser.add_argument("--risk-level", required=True, choices=("LEVEL_1", "LEVEL_2", "LEVEL_3"))
    args = parser.parse_args(argv)
    try:
        print(json.dumps(validate_review_artifact(args.artifact, review_type=args.review_type,
                                                  pins=json.loads(args.pins.read_text()),
                                                  commit_sha=args.commit,
                                                  approved_phases=json.loads(args.phases),
                                                  risk_level=args.risk_level), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
