#!/usr/bin/env python3
"""Read-only analyzer for the historic R7E7I failure and GitHub run.

It deliberately does not convert a retrospective report or GitHub timestamp
into a numeric error bound. Its result is conditional unless a contemporaneous
authenticated event receipt is available.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = 38196454003
RUN_HEAD = "243ee18fbfa5dd53b64c1c414dade12740a415c8"
RUN_URL = f"https://github.com/bmreyes25/ClarityLink/actions/runs/{RUN_ID}"
HISTORICAL_EVIDENCE = ROOT / "build/r7e6a/test-a/evidence/collector-failure-20261012T021444Z-b64f.json"
HISTORICAL_SHA256 = "21e6551fde4498603dbfc9129aa4f32a61b0f0c7e89f3a70ba5035cfccee430e"
REVIEW_PATH = "research/runtime/r7e7f-test-a-shell-root-cause-review.md"


class ChronologyError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_utc(value: object) -> dt.datetime:
    if not isinstance(value, str):
        raise ChronologyError("timestamp missing")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ChronologyError("timestamp malformed") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ChronologyError("timestamp timezone missing")
    return parsed.astimezone(dt.timezone.utc)


def analyze(run: dict[str, object], commit: dict[str, object],
            historical: dict[str, object], historical_sha256: str) -> dict[str, object]:
    reasons: list[str] = []
    run_matches = (run.get("databaseId") == RUN_ID and run.get("headSha") == RUN_HEAD
                   and run.get("event") == "pull_request" and run.get("url") == RUN_URL)
    commit_matches = (commit.get("sha") == RUN_HEAD and commit.get("review_path") == REVIEW_PATH
                      and isinstance(commit.get("review_text"), str)
                      and "collector-failure-20261012T021444Z-b64f.json" in commit["review_text"]
                      and "TEST_A_PROCESS_STATE_UNCERTAIN" in commit["review_text"])
    evidence_matches = (historical_sha256 == HISTORICAL_SHA256
                        and historical.get("decision") == "TEST_A_PROCESS_STATE_UNCERTAIN"
                        and historical.get("diagnostic_started") is True
                        and isinstance(historical.get("finished_utc"), str))
    try:
        created = parse_utc(run.get("createdAt"))
        finished = parse_utc(historical.get("finished_utc"))
        timestamp_order = finished < created
    except ChronologyError:
        created = finished = None
        timestamp_order = False
    if not run_matches:
        reasons.append("GitHub run identity does not match the reviewed historical event.")
    if not commit_matches:
        reasons.append("The exact run head does not contain the reviewed failure report identity.")
    if not evidence_matches:
        reasons.append("The private historical record is missing, changed, or has unexpected content.")
    if not timestamp_order:
        reasons.append("The record timestamp does not precede the GitHub run timestamp.")
    if run_matches and commit_matches and evidence_matches and timestamp_order:
        decision = "HISTORICAL_UPPER_BOUND_CONDITIONAL"
        reasons.extend([
            "The GitHub run is tied to the exact commit whose report describes the private failure record.",
            "The preserved private record has a matching local SHA-256 and an earlier host timestamp.",
            "The failure-to-report relationship and private record provenance are retrospective assertions, not an authenticated contemporaneous execution receipt.",
            "GitHub run metadata provides no documented maximum server-clock error for this use; no numeric historical error bound is derived.",
        ])
    else:
        decision = "HISTORICAL_UPPER_BOUND_NOT_PROVEN"
    return {
        "schema_version": "R7E7I-HISTORICAL-CHRONOLOGY-1",
        "decision": decision,
        "run_identity_matches": run_matches,
        "commit_report_matches": commit_matches,
        "private_record_matches": evidence_matches,
        "timestamp_values_ordered": timestamp_order,
        "failure_finished_utc_untrusted": historical.get("finished_utc") if evidence_matches else None,
        "github_run_created_utc": run.get("createdAt") if run_matches else None,
        "github_run_head_sha": run.get("headSha") if run_matches else None,
        "source_clock_accuracy_bound_seconds": None,
        "numeric_historical_upper_bound_utc": None,
        "causal_ordering": "CONDITIONAL_RETROSPECTIVE_REPORT_LINK" if decision.endswith("CONDITIONAL") else "NOT_ESTABLISHED",
        "reasons": reasons,
        "limitations": [
            "A local timestamp cannot be promoted to a trusted timestamp by comparison alone.",
            "A GitHub Actions creation time is an independent event record, but no maximum clock error bound was found.",
            "A later RFC 3161 token can timestamp evidence existence only from its own generation time onward; it cannot retroactively timestamp the old execution.",
            "No current host clock bound, Phase S result, process-safety finding, or authorization is produced.",
        ],
    }


def _run(argv: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=False,
                                timeout=timeout, cwd=ROOT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ChronologyError(f"read-only source command failed: {type(exc).__name__}") from exc
    if result.returncode != 0:
        raise ChronologyError(f"read-only source command returned {result.returncode}")
    return result


def collect() -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, bytes]]:
    run_raw = _run(["gh", "run", "view", str(RUN_ID), "-R", "bmreyes25/ClarityLink",
                    "--json", "databaseId,createdAt,headSha,event,url,workflowName,status,conclusion"]).stdout
    run = json.loads(run_raw)
    commit_raw = _run(["git", "show", f"{RUN_HEAD}:{REVIEW_PATH}"]).stdout
    commit = {"sha": RUN_HEAD, "review_path": REVIEW_PATH, "review_text": commit_raw}
    if HISTORICAL_EVIDENCE.is_symlink() or not HISTORICAL_EVIDENCE.is_file():
        raise ChronologyError("preserved private failure record unavailable")
    mode = HISTORICAL_EVIDENCE.stat().st_mode
    if stat.S_IMODE(mode) != 0o600:
        raise ChronologyError("preserved private failure record mode is not 0600")
    record_bytes = HISTORICAL_EVIDENCE.read_bytes()
    record = json.loads(record_bytes)
    receipts = {"github-run.json": run_raw.encode(),
                "historical-review.md": commit_raw.encode(),
                "historical-failure.json": record_bytes}
    return run, commit, record, receipts


def save_private(result: dict[str, object], receipts: dict[str, bytes], directory: Path) -> Path:
    if directory.exists() and directory.is_symlink():
        raise ChronologyError("output directory must not be a symlink")
    directory.mkdir(parents=True, mode=0o700, exist_ok=True)
    directory.chmod(0o700)
    receipt_rows = {}
    for filename, contents in receipts.items():
        path = directory / filename
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(contents)
        receipt_rows[filename] = {"sha256": sha256(contents), "bytes": len(contents)}
    document = dict(result, receipts=receipt_rows)
    path = directory / f"chronology-{time.time_ns()}.json"
    raw = json.dumps(document, sort_keys=True, indent=2).encode() + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run:
        print(json.dumps({"decision": "DRY_RUN_NO_GITHUB_NO_GIT", "run_id": RUN_ID,
                          "head_sha": RUN_HEAD}, indent=2))
        return 0
    try:
        run, commit, historical, receipts = collect()
        result = analyze(run, commit, historical, sha256(receipts["historical-failure.json"]))
        output = args.output_dir or ROOT / "build/r7e7i/historical-chronology"
        path = save_private(result, receipts, output)
        print(json.dumps({"decision": result["decision"], "evidence_path": str(path),
                          "numeric_historical_upper_bound_utc": None}, sort_keys=True))
        return 0
    except (ChronologyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"CHRONOLOGY_INCONCLUSIVE: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
