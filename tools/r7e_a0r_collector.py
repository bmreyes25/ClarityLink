#!/usr/bin/env python3
"""Fail-closed host collector for the separately authorized R7E A0-R plan.

This tool is intentionally disabled unless the operator supplies the exact
execution gate. That gate is not user authorization; authorization is a
separate decision tied to the reviewed collector commit and manifest hash.
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
import subprocess
import sys
import time
from typing import Callable, Sequence

VERSION = "R7E3-A0R-1"
PLAN_VERSION = "R7E3-A0R-COMMAND-SET-1"
TIMEOUT_SECONDS = 15
REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "research" / "runtime" / "r7e3-a0r-plan-manifest.json"
COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("A0R-01", ("shell", "id")),
    ("A0R-02", ("shell", "getprop", "ro.build.version.release")),
    ("A0R-03", ("shell", "getprop", "ro.build.version.sdk")),
    ("A0R-04", ("shell", "getprop", "ro.product.cpu.abi")),
    ("A0R-05", ("shell", "pwd")),
    ("A0R-06", ("shell", "ls", "-ld", "/data")),
    ("A0R-07", ("shell", "ls", "-ld", "/data/local")),
    ("A0R-08", ("shell", "ls", "-ld", "/data/local/tmp")),
    ("A0R-09", ("shell", "cat", "/proc/mounts")),
    ("A0R-10", ("shell", "cat", "/proc/self/status")),
    ("A0R-11", ("shell", "cat", "/sys/fs/selinux/enforce")),
)
ADB_INVENTORY = ("devices",)
RELEASE_EXPECTED = "4.2.2"
SDK_EXPECTED = "17"
ABI_RE = re.compile(r"^armeabi-v7a(\s|$)")


def parse_devices(output: str) -> tuple[str | None, str]:
    """Return one pinned selector only when inventory is exactly one device."""
    entries: list[tuple[str, str]] = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0] != "List" and "\t" in line:
            entries.append((fields[0], fields[1]))
    if len(entries) != 1:
        return None, "A0R_BLOCKED_TARGET_IDENTITY"
    selector, state = entries[0]
    if state != "device" or not selector or any(c.isspace() for c in selector):
        return None, "A0R_BLOCKED_TARGET_IDENTITY"
    return selector, "OK"


def classify_id(output: str) -> str:
    match = re.search(r"\buid=(\d+)", output)
    if match and match.group(1) == "2000":
        return "ORDINARY_SHELL_OBSERVED"
    return "A0R_BLOCKED_SHELL_IDENTITY"


def parse_mounts(output: str) -> dict[str, object] | None:
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 4 and fields[1] == "/data":
            options = set(fields[3].split(","))
            return {
                "mount_point": "/data",
                "filesystem": fields[2],
                "options": sorted(options),
                "rw": "rw" in options,
                "ro": "ro" in options,
                "noexec": "noexec" in options,
                "nosuid": "nosuid" in options,
                "nodev": "nodev" in options,
                "exec_observation": "NO_NOEXEC_FLAG_OBSERVED" if "noexec" not in options else "NOEXEC_OBSERVED",
            }
    return None


def dry_run_lines() -> list[str]:
    lines = ["adb devices"]
    lines.extend("adb -s TARGET_REDACTED " + " ".join(args) for _, args in COMMANDS)
    return lines


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _record_command(
    run_dir: Path,
    command_id: str,
    operation: str,
    argv: Sequence[str],
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> dict[str, object]:
    start = time.monotonic_ns()
    start_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        result = runner(list(argv), capture_output=True, text=True,
                        timeout=TIMEOUT_SECONDS, check=False)
        code = result.returncode
        stdout, stderr = result.stdout or "", result.stderr or ""
        classification = "COMMAND_OK" if code == 0 else "COMMAND_FAILED"
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = "TIMEOUT", exc.stdout or "", exc.stderr or ""
        if isinstance(stdout, bytes): stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes): stderr = stderr.decode("utf-8", "replace")
        classification = "COMMAND_TIMEOUT"
    end = time.monotonic_ns()
    result_dir = run_dir / "command-results"
    result_dir.mkdir(mode=0o700, exist_ok=True)
    for suffix, data in (("stdout", stdout), ("stderr", stderr)):
        path = result_dir / f"{command_id}.{suffix}.txt"
        path.write_text(data, encoding="utf-8", errors="replace")
        path.chmod(0o600)
    record = {
        "command_id": command_id,
        "operation": operation,
        "start_utc": start_utc,
        "start_monotonic_ns": start,
        "end_monotonic_ns": end,
        "exit_status": code,
        "stdout_file": f"command-results/{command_id}.stdout.txt",
        "stderr_file": f"command-results/{command_id}.stderr.txt",
        "classification": classification,
    }
    return {**record, "stdout": stdout, "stderr": stderr}


def _run(args: argparse.Namespace, runner=subprocess.run, input_fn=input) -> int:
    if args.dry_run:
        print("A0-R DRY RUN — zero adb calls and zero target discovery")
        print("\n".join(dry_run_lines()))
        return 0
    if not args.execute_authorized_a0_readonly:
        print("NOT_AUTHORIZED: A0-R requires separate explicit user authorization. No adb commands were run.", file=sys.stderr)
        return 2
    required = {
        "--authorization-ref": args.authorization_ref,
        "--observed-power-state": args.observed_power_state,
        "--audio-state-before": args.audio_state_before,
        "--stationary": args.stationary,
        "--parked": args.parked,
        "--center-display-booted": args.center_display_booted,
        "--cluster-normal": args.cluster_normal,
        "--no-unexpected-warnings": args.no_unexpected_warnings,
        "--confirm-intended-honda-target": args.confirm_intended_honda_target,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        label = "A0R_BLOCKED_TARGET_IDENTITY" if "--confirm-intended-honda-target" in missing else "A0R_BLOCKED_POWER_STATE"
        print(label + ": missing affirmative operator inputs: " + ", ".join(missing), file=sys.stderr)
        return 2
    if runner is subprocess.run and not shutil.which(args.adb):
        print("A0R_BLOCKED_COMMAND_FAILURE: adb executable unavailable; no target discovery occurred.", file=sys.stderr)
        return 2

    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + os.urandom(4).hex()
    evidence_root = Path(args.evidence_root)
    evidence_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    evidence_root.chmod(0o700)
    run_dir = evidence_root / run_id
    run_dir.mkdir(parents=True, mode=0o700)
    run_dir.chmod(0o700)
    os.umask(0o077)
    repo_head = "UNKNOWN"
    try:
        repo_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                   text=True, timeout=3, check=False).stdout.strip() or "UNKNOWN"
    except (OSError, subprocess.TimeoutExpired):
        pass
    metadata: dict[str, object] = {
        "collector_version": VERSION,
        "plan_version": PLAN_VERSION,
        "collector_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "plan_manifest_sha256": hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
        if MANIFEST_PATH.is_file() else "UNAVAILABLE",
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
        "command_records": [],
        "decision": "A0R_BLOCKED_COMMAND_FAILURE",
        "rollback_commands": "NONE; any mutation is STOP/INCIDENT",
        "a0w": "WRITE_DELETE_EVIDENCE_STILL_REQUIRED; separate authorization only",
        "test_a": "NOT_AUTHORIZED",
    }
    records: list[dict[str, object]] = []
    inventory = _record_command(run_dir, "A0R-00", "adb inventory", [args.adb, *ADB_INVENTORY], runner)
    records.append(inventory)
    if inventory["exit_status"] != 0:
        metadata["decision"] = "A0R_BLOCKED_COMMAND_FAILURE"
        _finish(run_dir, metadata, records)
        return 1
    target, target_state = parse_devices(str(inventory["stdout"]))
    if target_state != "OK" or target is None:
        metadata["decision"] = "A0R_BLOCKED_TARGET_IDENTITY"
        _finish(run_dir, metadata, records)
        print("A0R_BLOCKED_TARGET_IDENTITY: expected exactly one target in device state; no shell command ran.")
        return 1
    metadata["target_identity"] = "REDACTED"
    metadata["target_identity_local_sha256"] = hashlib.sha256(target.encode()).hexdigest()
    # Raw selector is retained only in the private local evidence directory.
    raw = run_dir / "target-identity.local.txt"
    raw.write_text(target + "\n", encoding="utf-8")
    raw.chmod(0o600)

    values: dict[str, str] = {}
    decision = "A0R_BLOCKED_COMMAND_FAILURE"
    for command_id, operation in COMMANDS:
        command_name = " ".join(operation)
        rec = _record_command(run_dir, command_id, command_name,
                              [args.adb, "-s", target, *operation], runner)
        records.append(rec)
        if rec["exit_status"] == "TIMEOUT":
            decision = "A0R_BLOCKED_COMMAND_FAILURE"
            break
        if command_id == "A0R-01":
            decision = classify_id(str(rec["stdout"]))
            if rec["exit_status"] != 0 or decision != "ORDINARY_SHELL_OBSERVED":
                decision = "A0R_BLOCKED_SHELL_IDENTITY"
                break
        elif command_id in {"A0R-02", "A0R-03", "A0R-04"}:
            if rec["exit_status"] != 0:
                decision = "A0R_BLOCKED_COMMAND_FAILURE"
                break
            values[command_id] = str(rec["stdout"]).strip()
            if command_id == "A0R-04":
                if values.get("A0R-02") != RELEASE_EXPECTED or values.get("A0R-03") != SDK_EXPECTED or not ABI_RE.match(values[command_id]):
                    decision = "A0R_BLOCKED_PLATFORM_MISMATCH"
                    break
        elif command_id == "A0R-05" and rec["exit_status"] != 0:
            decision = "A0R_BLOCKED_COMMAND_FAILURE"
            break
        elif command_id in {"A0R-06", "A0R-07", "A0R-08"} and rec["exit_status"] != 0:
            rec["classification"] = "LS_LD_UNAVAILABLE"
            decision = "A0R_BLOCKED_DESTINATION_METADATA"
            break
        elif command_id == "A0R-09":
            if rec["exit_status"] != 0:
                decision = "A0R_BLOCKED_COMMAND_FAILURE"
                break
            mounts = parse_mounts(str(rec["stdout"]))
            metadata["data_mount"] = mounts
            if mounts is None:
                decision = "A0R_BLOCKED_COMMAND_FAILURE"
                break
            if mounts["noexec"]:
                decision = "A0R_BLOCKED_NOEXEC"
                break
        elif command_id == "A0R-10" and rec["exit_status"] != 0:
            decision = "A0R_BLOCKED_COMMAND_FAILURE"
            break
        elif command_id == "A0R-11" and rec["exit_status"] != 0:
            # Missing, unreadable, and denied are all unavailable, never disabled.
            rec["classification"] = "SELINUX_STATE_UNAVAILABLE"
            metadata["selinux_state"] = "SELINUX_STATE_UNAVAILABLE"
        elif command_id == "A0R-11":
            val = str(rec["stdout"]).strip()
            metadata["selinux_state"] = val if val in {"0", "1"} else "SELINUX_STATE_UNAVAILABLE"

    if decision == "ORDINARY_SHELL_OBSERVED":
        decision = "A0R_PASS_FOR_REVIEW"
    if metadata.get("selinux_state") == "SELINUX_STATE_UNAVAILABLE" and decision == "A0R_PASS_FOR_REVIEW":
        decision = "A0R_SELINUX_STATE_UNAVAILABLE"
    metadata["decision"] = decision
    metadata["platform_observed"] = {
        "android_release": values.get("A0R-02"),
        "sdk": values.get("A0R-03"),
        "abi": values.get("A0R-04"),
    }
    try:
        after = input_fn("Record after-run center UI/cluster/warning/audio observations; enter STOCK_STATE_UNCHANGED only if they match the before observations: ")
    except (EOFError, KeyboardInterrupt):
        after = ""
    metadata["operator_confirmations_after"] = {"stock_state_observation_exact": after,
                                                 "stock_state_unchanged": after == "STOCK_STATE_UNCHANGED"}
    if after != "STOCK_STATE_UNCHANGED":
        metadata["decision"] = "A0R_STOP_CONDITION"
    _finish(run_dir, metadata, records)
    print(f"{metadata['decision']} — local evidence: {run_dir}")
    print("A0-W remains separately gated. Test A remains NOT_AUTHORIZED.")
    return 0 if metadata["decision"] in {"A0R_PASS_FOR_REVIEW", "A0R_SELINUX_STATE_UNAVAILABLE"} else 1


def _finish(run_dir: Path, metadata: dict[str, object], records: list[dict[str, object]]) -> None:
    for record in records:
        record.pop("stdout", None)
        record.pop("stderr", None)
    metadata["command_records"] = records
    _write_json(run_dir / "metadata.json", metadata)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="print the fixed sequence; zero adb calls")
    modes.add_argument("--execute-authorized-a0-readonly", action="store_true",
                       help="runtime gate only; does not itself grant user authorization")
    parser.add_argument("--authorization-ref")
    parser.add_argument("--observed-power-state")
    parser.add_argument("--audio-state-before")
    parser.add_argument("--stationary", action="store_true")
    parser.add_argument("--parked", action="store_true")
    parser.add_argument("--center-display-booted", action="store_true")
    parser.add_argument("--cluster-normal", action="store_true")
    parser.add_argument("--no-unexpected-warnings", action="store_true")
    parser.add_argument("--confirm-intended-honda-target", action="store_true")
    parser.add_argument("--adb", default="adb", help=argparse.SUPPRESS)
    parser.add_argument("--evidence-root", default="build/r7e/a0r", help=argparse.SUPPRESS)
    return parser


def main(argv: Sequence[str] | None = None, *, runner=subprocess.run,
         input_fn=input) -> int:
    args = build_parser().parse_args(argv)
    return _run(args, runner=runner, input_fn=input_fn)


if __name__ == "__main__":
    raise SystemExit(main())
