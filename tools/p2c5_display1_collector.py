#!/usr/bin/env python3
"""Default-disabled, read-only DisplayManager inventory proposal.

This collector is not authorized for Honda use. Tests inject fake ADB; neither
normal invocation nor --dry-run contacts any target.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research/architecture/p2c5-display1-manifest.json"
EVIDENCE_DIR = ROOT / "build/p2c5/evidence"
TIMEOUT_SECONDS = 12
SERIAL_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


class Stop(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def manifest_valid(manifest_hash: str, collector_hash: str) -> dict:
    if sha256(Path(__file__)) != collector_hash:
        raise Stop("collector hash mismatch")
    if sha256(MANIFEST) != manifest_hash:
        raise Stop("manifest hash mismatch")
    data = json.loads(MANIFEST.read_text())
    if data.get("collector_sha256") != collector_hash:
        raise Stop("manifest collector identity mismatch")
    if data.get("commands") != [
        ["adb", "-s", "<EXACT_SERIAL>", "get-state"],
        ["adb", "-s", "<EXACT_SERIAL>", "shell", "id"],
        ["adb", "-s", "<EXACT_SERIAL>", "shell", "getprop", "ro.build.version.sdk"],
        ["adb", "-s", "<EXACT_SERIAL>", "shell", "dumpsys", "display"],
    ]:
        raise Stop("command contract mismatch")
    return data


def run_one(runner: Callable, command: Sequence[str]) -> tuple[str, str, int]:
    try:
        result = runner(list(command), capture_output=True, text=True,
                        timeout=TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired as exc:
        raise Stop("INSPECTION_TIMEOUT") from exc
    except OSError as exc:
        raise Stop("ADB_EXECUTION_ERROR") from exc
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if result.returncode != 0 or stderr:
        raise Stop("UNEXPECTED_COMMAND_RESULT")
    return stdout, stderr, result.returncode


def execute(serial: str, authorization_ref: str, manifest_hash: str,
            collector_hash: str, evidence_path: Path, runner: Callable) -> dict:
    if not SERIAL_PATTERN.fullmatch(serial) or serial.lower() in {"auto", "any", "all"}:
        raise Stop("invalid exact serial")
    if not authorization_ref.strip():
        raise Stop("missing authorization reference")
    contract = manifest_valid(manifest_hash, collector_hash)
    evidence_root = EVIDENCE_DIR.resolve()
    evidence_path = evidence_path.resolve()
    try:
        evidence_path.relative_to(evidence_root)
    except ValueError as exc:
        raise Stop("evidence must remain under the ignored private evidence directory") from exc
    commands = [
        ["adb", "-s", serial, "get-state"],
        ["adb", "-s", serial, "shell", "id"],
        ["adb", "-s", serial, "shell", "getprop", "ro.build.version.sdk"],
        ["adb", "-s", serial, "shell", "dumpsys", "display"],
    ]
    results = []
    for index, command in enumerate(commands):
        stdout, stderr, rc = run_one(runner, command)
        results.append({"command_index": index + 1, "return_code": rc,
                        "stdout": stdout, "stderr": stderr})
        if index == 0 and stdout.strip() != "device":
            raise Stop("TARGET_STATE_NOT_DEVICE")
        if index == 1 and not re.search(r"(?:^|\s)uid=2000\(shell\)(?:\s|$)", stdout):
            raise Stop("SHELL_UID_MISMATCH")
        if index == 2 and stdout.strip() != "17":
            raise Stop("ANDROID_API_LEVEL_MISMATCH")
        if index == 3 and not stdout.strip():
            raise Stop("EMPTY_DISPLAY_DUMP")

    output = {
        "schema": "P2C5-DISPLAY-OBSERVATION-1",
        "authorization_ref": authorization_ref,
        "serial": serial,
        "timestamp_unix": int(time.time()),
        "classification": "DISPLAY_ENUMERATION_RAW_ONLY",
        "window_admission": "NOT_TESTED",
        "visible_rendering": "NOT_TESTED",
        "display_dump_sha256": hashlib.sha256(results[3]["stdout"].encode()).hexdigest(),
        "results": results,
        "commands_executed": len(results),
        "target_writes": 0,
        "display_operations": 0,
        "retries": 0,
        "contract_sha256": manifest_hash,
    }
    evidence_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(evidence_path.parent, 0o700)
    fd = os.open(evidence_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(output, stream, sort_keys=True, indent=2)
        stream.write("\n")
    return output


def main(argv: Sequence[str] | None = None,
         runner: Callable = subprocess.run) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--execute-authorized-p2c5", action="store_true")
    parser.add_argument("--serial")
    parser.add_argument("--authorization-ref")
    parser.add_argument("--authorized-collector-sha256")
    parser.add_argument("--authorized-manifest-sha256")
    parser.add_argument("--parked-confirmed", action="store_true")
    parser.add_argument("--display-booted-confirmed", action="store_true")
    parser.add_argument("--cluster-normal-confirmed", action="store_true")
    parser.add_argument("--no-warnings-confirmed", action="store_true")
    parser.add_argument("--exclusive-adb-window-confirmed", action="store_true")
    parser.add_argument("--no-manual-adb-confirmed", action="store_true")
    parser.add_argument("--evidence", type=Path, help="new filename under build/p2c5/evidence")
    args = parser.parse_args(argv)
    if args.dry_run:
        print("DRY_RUN_NO_ADB; fixed read-only command plan; no target discovery")
        for command in ("adb -s <EXACT_SERIAL> get-state",
                        "adb -s <EXACT_SERIAL> shell id",
                        "adb -s <EXACT_SERIAL> shell getprop ro.build.version.sdk",
                        "adb -s <EXACT_SERIAL> shell dumpsys display"):
            print(command)
        return 0
    if not args.execute_authorized_p2c5:
        print("NOT_AUTHORIZED; no ADB calls", file=sys.stderr)
        return 2
    confirmations = (args.parked_confirmed, args.display_booted_confirmed,
                     args.cluster_normal_confirmed, args.no_warnings_confirmed,
                     args.exclusive_adb_window_confirmed, args.no_manual_adb_confirmed)
    if not all(confirmations):
        print("MISSING_FRESH_OPERATOR_CONFIRMATION; no ADB calls", file=sys.stderr)
        return 2
    required = (args.serial, args.authorization_ref, args.authorized_collector_sha256,
                args.authorized_manifest_sha256, args.evidence)
    if not all(required):
        print("MISSING_AUTHORIZATION_IDENTITY; no ADB calls", file=sys.stderr)
        return 2
    try:
        result = execute(args.serial, args.authorization_ref,
                         args.authorized_manifest_sha256,
                         args.authorized_collector_sha256,
                         args.evidence, runner)
    except (Stop, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 3
    print(json.dumps({key: result[key] for key in (
        "classification", "commands_executed", "window_admission", "visible_rendering")},
        sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
