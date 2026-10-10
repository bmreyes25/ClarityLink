#!/usr/bin/env python3
"""Default-disabled, fail-closed A0-W inert-marker lifecycle collector.

The runtime gate does not grant user authorization. Execution requires the
separate authorization reference and hashes from the frozen packet.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time
from typing import Callable, Sequence

VERSION = "R7E5A-A0W-1"
PLAN_VERSION = "R7E5A-A0W-COMMAND-SET-1"
TIMEOUT_SECONDS = 15
REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "research/runtime/r7e5a-a0w-plan-manifest.json"
MARKER_PATH = REPO_ROOT / "build/r7e/a0w/claritylink-a0w-marker.txt"
MARKER_RELATIVE_PATH = "build/r7e/a0w/claritylink-a0w-marker.txt"
EVIDENCE_ROOT = REPO_ROOT / "build/r7e/a0w/evidence"
PARENT_PATH = "/data/local/tmp"
REMOTE_PATH = "/data/local/tmp/claritylink_a0w_r7e5a_5f9ffbe9dc38eaa3f98fb387f35109bd.probe"
MARKER_BYTES = b"ClarityLink A0-W inert transfer marker\nR7E5A\nNO EXECUTION\n"
MARKER_SHA256 = "6b0693fdcff5be76f10a0886ee0e82efeed070e493abaf28633775d8979706df"
MARKER_MD5 = "395de139036f88640ad5acf7c6f6230e"
EXPECTED_PARENT_MODE = "drwxrwx--x"
EXPECTED_PARENT_OWNER = "shell"
EXPECTED_PARENT_GROUP = "shell"


def manifest_commands() -> list[dict[str, object]]:
    host = "build/r7e/a0w/claritylink-a0w-marker.txt"
    base = Path(REMOTE_PATH).name
    return [
        {"id": "A0W-00", "argv": ["devices"], "scope": "host adb inventory"},
        {"id": "A0W-01", "argv": ["-s", "TARGET", "shell", "ls", "-ld", PARENT_PATH],
         "scope": "target read; destination revalidation"},
        {"id": "A0W-02", "argv": ["-s", "TARGET", "shell", "ls", "-l", REMOTE_PATH],
         "scope": "target read; exact-path pre-existence gate"},
        {"id": "A0W-03", "argv": ["-s", "TARGET", "push", host, REMOTE_PATH],
         "scope": "single target write; one inert data file"},
        {"id": "A0W-04", "argv": ["-s", "TARGET", "shell", "ls", "-l", REMOTE_PATH],
         "scope": "target read; exact marker metadata"},
        {"id": "A0W-05", "argv": ["-s", "TARGET", "shell", "/system/bin/md5", REMOTE_PATH],
         "scope": "target read; optional-tool metadata previously present; transport consistency only"},
        {"id": "A0W-06", "argv": ["-s", "TARGET", "shell", "/system/bin/rm", REMOTE_PATH],
         "scope": "single exact-path cleanup mutation"},
        {"id": "A0W-07", "argv": ["-s", "TARGET", "shell", "ls", "-l", REMOTE_PATH],
         "scope": "target read; exact absence verification"},
    ]


def manifest_template() -> dict[str, object]:
    return {
        "manifest_version": PLAN_VERSION,
        "collector_source": "tools/r7e5a_a0w_collector.py",
        "collector_source_sha256": "FROZEN_AFTER_SOURCE",
        "host_marker_path": "build/r7e/a0w/claritylink-a0w-marker.txt",
        "marker_content_ascii": MARKER_BYTES.decode("ascii"),
        "marker_size_bytes": len(MARKER_BYTES),
        "marker_mode": "0644",
        "marker_sha256": MARKER_SHA256,
        "marker_md5": MARKER_MD5,
        "remote_path": REMOTE_PATH,
        "target_writes": ["A0W-03: one adb push of the exact inert marker"],
        "target_cleanup": ["A0W-06: /system/bin/rm of the exact marker path"],
        "timeout_seconds": TIMEOUT_SECONDS,
        "retries": 0,
        "fallbacks": [],
        "exclusive_adb_window_required": True,
        "required_operator_gate": "--exclusive-adb-window-confirmed",
        "push_semantics_note": (
            "AOSP 4.2.2 ADB sync unlinks the exact destination before creating it; "
            "the absence precheck is not atomic, so this plan requires a unique path "
            "and an operator-confirmed exclusive ADB window. Stop if that condition cannot be met."
        ),
        "commands": manifest_commands(),
        "success_proves": [
            "one exact ADB sync transfer succeeded",
            "the exact regular marker was observed with expected bytes, mode, and ownership",
            "optional MD5 transport consistency matched",
            "the exact marker path was removed and verified absent",
        ],
        "success_does_not_prove": [
            "executable mapping or launch", "ClarityLink operation", "Display1 or Presentation",
            "CarPlay", "USB/iAP2", "MFi", "any Test A result",
        ],
    }


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_package(args: argparse.Namespace) -> tuple[bool, str]:
    source = Path(__file__).resolve()
    if not source.is_file() or not MANIFEST_PATH.is_file() or not MARKER_PATH.exists():
        return False, "required frozen package file is missing"
    if MARKER_PATH.is_symlink() or not stat.S_ISREG(MARKER_PATH.lstat().st_mode):
        return False, "host marker is not a regular file"
    if (MARKER_PATH.stat().st_mode & 0o777) != 0o644:
        return False, "host marker mode is not exactly 0644"
    marker = MARKER_PATH.read_bytes()
    if marker != MARKER_BYTES:
        return False, "host marker bytes differ from the frozen bytes"
    if hashlib.sha256(marker).hexdigest() != MARKER_SHA256 or hashlib.md5(marker).hexdigest() != MARKER_MD5:
        return False, "host marker digest differs from the frozen identity"
    source_sha = _sha(source)
    manifest_bytes = MANIFEST_PATH.read_bytes()
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    if args.expected_source_sha256 != source_sha:
        return False, "collector source SHA-256 does not match the authorization binding"
    if args.expected_manifest_sha256 != manifest_sha:
        return False, "manifest SHA-256 does not match the authorization binding"
    try:
        actual = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False, "manifest is not valid UTF-8 JSON"
    expected = manifest_template()
    expected["collector_source_sha256"] = source_sha
    if actual != expected:
        return False, "manifest contents differ from the frozen A0-W plan"
    return True, "OK"


def _safe_ref(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value))


def _parse_devices(output: str) -> tuple[str | None, str]:
    entries = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0] != "List" and "\t" in line:
            entries.append((fields[0], fields[1]))
    if len(entries) != 1:
        return None, "A0W_BLOCKED_TARGET_IDENTITY"
    selector, state = entries[0]
    if state != "device" or not selector or any(ch.isspace() for ch in selector):
        return None, "A0W_BLOCKED_TARGET_IDENTITY"
    return selector, "OK"


def _record(run_dir: Path, command_id: str, operation: str, argv: Sequence[str],
            runner: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, object]:
    start = time.monotonic_ns()
    utc = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        result = runner(list(argv), capture_output=True, text=True,
                        timeout=TIMEOUT_SECONDS, check=False, cwd=REPO_ROOT)
        code, stdout, stderr = result.returncode, result.stdout or "", result.stderr or ""
        classification = "COMMAND_OK" if code == 0 else "COMMAND_FAILED"
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = "TIMEOUT", exc.stdout or "", exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
        classification = "COMMAND_TIMEOUT"
    result_dir = run_dir / "command-results"
    result_dir.mkdir(mode=0o700, exist_ok=True)
    values = {}
    for suffix, value in (("stdout", stdout), ("stderr", stderr)):
        path = result_dir / f"{command_id}.{suffix}.txt"
        path.write_text(value, encoding="utf-8", errors="replace")
        path.chmod(0o600)
        values[suffix] = value
    return {
        "command_id": command_id, "operation": operation,
        "start_utc": utc, "start_monotonic_ns": start,
        "end_monotonic_ns": time.monotonic_ns(), "exit_status": code,
        "stdout_file": f"command-results/{command_id}.stdout.txt",
        "stderr_file": f"command-results/{command_id}.stderr.txt",
        "classification": classification,
        **values,
    }


def _write_metadata(run_dir: Path, metadata: dict[str, object], records: list[dict[str, object]]) -> None:
    stored = []
    for record in records:
        stored.append({k: v for k, v in record.items() if k not in {"stdout", "stderr"}})
    path = run_dir / "metadata.json"
    path.write_text(json.dumps({**metadata, "command_records": stored}, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    path.chmod(0o600)


def _inventory_absent(rec: dict[str, object], path: str) -> bool:
    combined = (str(rec.get("stderr", "")) + "\n" + str(rec.get("stdout", ""))).strip()
    if rec.get("exit_status") not in (0, 1):
        return False
    pattern = rf"(?:/system/bin/sh:\s*)?(?:ls:\s*)?{re.escape(path)}: No such file or directory"
    return len(combined.splitlines()) == 1 and re.fullmatch(pattern, combined) is not None


def _parse_parent(output: str) -> dict[str, str] | None:
    lines = [line.split() for line in output.splitlines() if line.strip()]
    if len(lines) != 1 or len(lines[0]) < 5:
        return None
    fields = lines[0]
    if len(fields[0]) != 10 or fields[0][0] != "d":
        return None
    return {"mode": fields[0], "owner": fields[1], "group": fields[2], "name": fields[-1]}


def _parse_marker_listing(output: str) -> dict[str, object] | None:
    lines = [line.split() for line in output.splitlines() if line.strip()]
    if len(lines) != 1 or len(lines[0]) < 7:
        return None
    fields = lines[0]
    if len(fields[0]) != 10 or fields[0][0] != "-":
        return None
    try:
        size = int(fields[3])
    except ValueError:
        return None
    return {"mode": fields[0], "owner": fields[1], "group": fields[2],
            "size": size, "name": fields[-1], "executable": any(c in "xstST" for c in fields[0][3::3])}


def _md5_matches(output: str) -> bool:
    lines = [line.split() for line in output.splitlines() if line.strip()]
    return len(lines) == 1 and len(lines[0]) == 2 and lines[0][0].lower() == MARKER_MD5 and lines[0][1] == REMOTE_PATH


def _absent_state(rec: dict[str, object]) -> bool:
    return _inventory_absent(rec, REMOTE_PATH)


def _dry_run() -> list[str]:
    commands = ["adb devices"]
    commands.extend([
        f"adb -s TARGET_REDACTED shell ls -ld {PARENT_PATH}",
        f"adb -s TARGET_REDACTED shell ls -l {REMOTE_PATH}  # must report exact ENOENT",
        f"adb -s TARGET_REDACTED push {MARKER_RELATIVE_PATH} {REMOTE_PATH}",
        f"adb -s TARGET_REDACTED shell ls -l {REMOTE_PATH}",
        f"adb -s TARGET_REDACTED shell /system/bin/md5 {REMOTE_PATH}",
        f"adb -s TARGET_REDACTED shell /system/bin/rm {REMOTE_PATH}",
        f"adb -s TARGET_REDACTED shell ls -l {REMOTE_PATH}  # must report exact ENOENT",
    ])
    return commands


def _run(args: argparse.Namespace, runner=subprocess.run, input_fn=input) -> int:
    if args.dry_run:
        print("A0-W DRY RUN — zero adb calls and zero target discovery")
        print("\n".join(_dry_run()))
        return 0
    if not args.execute_authorized_a0_write_delete:
        print("NOT_AUTHORIZED: A0-W requires separate explicit user authorization. No adb commands were run.", file=sys.stderr)
        return 2
    required = {
        "--authorization-ref": _safe_ref(args.authorization_ref),
        "--expected-source-sha256": bool(args.expected_source_sha256),
        "--expected-manifest-sha256": bool(args.expected_manifest_sha256),
        "--observed-power-state": bool(args.observed_power_state and not re.search(r"[\x00-\x1f\x7f]", args.observed_power_state)),
        "--audio-state-before": bool(args.audio_state_before and not re.search(r"[\x00-\x1f\x7f]", args.audio_state_before)),
        "--stationary": args.stationary,
        "--parked": args.parked,
        "--center-display-booted": args.center_display_booted,
        "--cluster-normal": args.cluster_normal,
        "--no-unexpected-warnings": args.no_unexpected_warnings,
        "--confirm-intended-honda-target": args.confirm_intended_honda_target,
        "--exclusive-adb-window-confirmed": args.exclusive_adb_window_confirmed,
    }
    missing = [name for name, ok in required.items() if not ok]
    if missing:
        print("A0W_BLOCKED_OPERATOR_GATE: missing/invalid inputs: " + ", ".join(missing), file=sys.stderr)
        return 2
    valid, reason = _verify_package(args)
    if not valid:
        print("A0W_AUTHORIZATION_BINDING_MISMATCH: " + reason, file=sys.stderr)
        return 2
    if runner is subprocess.run and not shutil.which("adb"):
        print("A0W_BLOCKED_COMMAND_FAILURE: adb unavailable; no target discovery occurred.", file=sys.stderr)
        return 2

    source_sha = _sha(Path(__file__).resolve())
    manifest_sha = _sha(MANIFEST_PATH)
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + os.urandom(4).hex()
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    if EVIDENCE_ROOT.is_symlink():
        print("A0W_BLOCKED_LOCAL_EVIDENCE: evidence root must not be a symlink.", file=sys.stderr)
        return 2
    EVIDENCE_ROOT.chmod(0o700)
    run_dir = EVIDENCE_ROOT / run_id
    run_dir.mkdir(mode=0o700)
    run_dir.chmod(0o700)
    try:
        repo_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                                   capture_output=True, text=True, timeout=3,
                                   check=False).stdout.strip() or "UNKNOWN"
    except (OSError, subprocess.TimeoutExpired):
        repo_head = "UNKNOWN"
    metadata: dict[str, object] = {
        "collector_version": VERSION,
        "plan_version": PLAN_VERSION,
        "collector_source_sha256": source_sha,
        "plan_manifest_sha256": manifest_sha,
        "marker_sha256": MARKER_SHA256,
        "marker_md5": MARKER_MD5,
        "marker_size_bytes": len(MARKER_BYTES),
        "marker_mode": "0644",
        "remote_path": REMOTE_PATH,
        "repo_head": repo_head,
        "run_id": run_id,
        "authorization_ref": args.authorization_ref,
        "observed_power_state_exact": args.observed_power_state,
        "audio_state_before_exact": args.audio_state_before,
        "operator_confirmations_before": {
            "stationary": True, "parked": True, "center_display_fully_booted": True,
            "cluster_normal": True, "no_unexpected_warnings": True,
        },
        "target_identity": "REDACTED",
        "target_identity_local_sha256": None,
        "target_writes": 0,
        "cleanup_verified": False,
        "cleanup_command_success": False,
        "decision": "A0W_BLOCKED_COMMAND_FAILURE",
        "a0r": "REVIEWED_A0R_PASS_FOR_REVIEW",
        "a0w": "IN_PROGRESS",
        "test_a": "NOT_AUTHORIZED",
    }
    records: list[dict[str, object]] = []

    def record(command_id: str, operation: str, argv: Sequence[str]) -> dict[str, object]:
        rec = _record(run_dir, command_id, operation, argv, runner)
        records.append(rec)
        _write_metadata(run_dir, metadata, records)
        return rec

    inv = record("A0W-00", "adb inventory", ["adb", "devices"])
    if inv["exit_status"] != 0:
        metadata["decision"] = "A0W_BLOCKED_COMMAND_FAILURE"
        _write_metadata(run_dir, metadata, records)
        print(f"{metadata['decision']} — local evidence: {run_dir}")
        return 1
    target, status = _parse_devices(str(inv["stdout"]))
    if target is None:
        metadata["decision"] = status
        _write_metadata(run_dir, metadata, records)
        print(f"{metadata['decision']} — no target shell or write ran; local evidence: {run_dir}")
        return 1
    metadata["target_identity_local_sha256"] = hashlib.sha256(target.encode()).hexdigest()
    identity = run_dir / "target-identity.local.txt"
    identity.write_text(target + "\n", encoding="utf-8")
    identity.chmod(0o600)

    parent = record("A0W-01", "revalidate exact destination directory",
                    ["adb", "-s", target, "shell", "ls", "-ld", PARENT_PATH])
    parent_info = _parse_parent(str(parent["stdout"])) if parent["exit_status"] == 0 else None
    metadata["destination_observed"] = parent_info
    if not parent_info or parent_info != {
        "mode": EXPECTED_PARENT_MODE, "owner": EXPECTED_PARENT_OWNER,
        "group": EXPECTED_PARENT_GROUP, "name": "tmp",
    }:
        metadata["decision"] = "A0W_BLOCKED_DESTINATION_MISMATCH"
        _write_metadata(run_dir, metadata, records)
        print(f"{metadata['decision']} — no push ran; local evidence: {run_dir}")
        return 1

    pre = record("A0W-02", "exact-path pre-existence check",
                 ["adb", "-s", target, "shell", "ls", "-l", REMOTE_PATH])
    if not _absent_state(pre):
        metadata["decision"] = "A0W_BLOCKED_PATH_NOT_CONFIRMED_ABSENT"
        _write_metadata(run_dir, metadata, records)
        print(f"{metadata['decision']} — no push ran; local evidence: {run_dir}")
        return 1
    pre["classification"] = "FILE_ABSENT_EXPECTED"

    metadata["target_writes"] = 1
    metadata["target_write_attempts"] = 1
    _write_metadata(run_dir, metadata, records)
    push = record("A0W-03", "single exact-marker ADB sync push",
                  ["adb", "-s", target, "push", MARKER_RELATIVE_PATH, REMOTE_PATH])
    metadata["push_success"] = push["exit_status"] == 0
    _write_metadata(run_dir, metadata, records)

    marker_info = None
    md5_ok = False
    verification_ok = False
    if push["exit_status"] == 0:
        verify = record("A0W-04", "exact marker metadata verification",
                        ["adb", "-s", target, "shell", "ls", "-l", REMOTE_PATH])
        marker_info = _parse_marker_listing(str(verify["stdout"])) if verify["exit_status"] == 0 else None
        metadata["marker_observed"] = marker_info
        verification_ok = bool(marker_info and marker_info == {
            "mode": "-rw-r--r--", "owner": "shell", "group": "shell",
            "size": len(MARKER_BYTES), "name": Path(REMOTE_PATH).name, "executable": False,
        })
        if verification_ok:
            md5 = record("A0W-05", "exact marker MD5 transport consistency",
                         ["adb", "-s", target, "shell", "/system/bin/md5", REMOTE_PATH])
            md5_ok = md5["exit_status"] == 0 and _md5_matches(str(md5["stdout"]))
        metadata["marker_metadata_verified"] = verification_ok
        metadata["md5_transport_consistency_verified"] = md5_ok

    cleanup = record("A0W-06", "remove exact marker path",
                     ["adb", "-s", target, "shell", "/system/bin/rm", REMOTE_PATH])
    metadata["cleanup_command_success"] = cleanup["exit_status"] == 0
    absence = record("A0W-07", "verify exact marker path absent",
                     ["adb", "-s", target, "shell", "ls", "-l", REMOTE_PATH])
    metadata["cleanup_verified"] = _absent_state(absence)
    if metadata["cleanup_verified"]:
        absence["classification"] = "FILE_ABSENT_CONFIRMED"

    try:
        after = input_fn("Record after-run center UI/cluster/warning/audio observations; enter STOCK_STATE_UNCHANGED only if all match: ")
    except (EOFError, KeyboardInterrupt):
        after = ""
    metadata["operator_confirmations_after"] = {
        "stock_state_observation_exact": after,
        "stock_state_unchanged": after == "STOCK_STATE_UNCHANGED",
    }
    if not metadata["cleanup_verified"]:
        metadata["decision"] = "A0W_CLEANUP_NOT_VERIFIED"
    elif after != "STOCK_STATE_UNCHANGED" or not metadata["cleanup_command_success"]:
        metadata["decision"] = "A0W_STOP_CONDITION"
    elif not metadata["push_success"] or not verification_ok or not md5_ok:
        metadata["decision"] = "A0W_STOP_CONDITION"
    else:
        metadata["decision"] = "A0W_PASS_FOR_REVIEW"
    _write_metadata(run_dir, metadata, records)
    print(f"{metadata['decision']} — local evidence: {run_dir}")
    print("Test A remains NOT_AUTHORIZED. No automatic continuation is available.")
    return 0 if metadata["decision"] == "A0W_PASS_FOR_REVIEW" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="print the frozen sequence; zero adb calls")
    modes.add_argument("--execute-authorized-a0-write-delete", action="store_true",
                       help="runtime gate only; separate human authorization is required")
    parser.add_argument("--authorization-ref")
    parser.add_argument("--expected-source-sha256")
    parser.add_argument("--expected-manifest-sha256")
    parser.add_argument("--observed-power-state")
    parser.add_argument("--audio-state-before")
    parser.add_argument("--stationary", action="store_true")
    parser.add_argument("--parked", action="store_true")
    parser.add_argument("--center-display-booted", action="store_true")
    parser.add_argument("--cluster-normal", action="store_true")
    parser.add_argument("--no-unexpected-warnings", action="store_true")
    parser.add_argument("--confirm-intended-honda-target", action="store_true")
    parser.add_argument("--exclusive-adb-window-confirmed", action="store_true",
                        help="operator confirms no concurrent ADB writer during the exact marker lifecycle")
    return parser


def main(argv: Sequence[str] | None = None, *, runner=subprocess.run,
         input_fn=input) -> int:
    return _run(build_parser().parse_args(argv), runner=runner, input_fn=input_fn)


if __name__ == "__main__":
    raise SystemExit(main())
