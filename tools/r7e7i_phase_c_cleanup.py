#!/usr/bin/env python3
"""Default-disabled, one-shot exact-path Phase C cleanup collector.

Live use requires a separately reviewed package, fresh identity evidence,
current process-safety evidence, and a distinct one-use authorization. This
module alone grants none of those things.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import r7e6_test_a_collector as test_a

ROOT = Path(__file__).resolve().parents[1]
REMOTE = "/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f"
SIZE = 7904
MODE = "0555"
OWNER_GROUP = "shell:shell"
MD5 = "6137a693a77646aaf9a4cf0f351731d4"
TIMEOUT = 12


class Stop(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_plan() -> list[list[str]]:
    return [
        ["version"], ["devices"],
        ["-s", "<EXACT_SERIAL>", "shell", "ls", "-ld", REMOTE],
        ["-s", "<EXACT_SERIAL>", "shell", "/system/bin/md5", REMOTE],
        ["-s", "<EXACT_SERIAL>", "shell", "/system/bin/rm", REMOTE],
        ["-s", "<EXACT_SERIAL>", "shell", "ls", "-ld", REMOTE],
    ]


def identity(stdout: str) -> bool:
    return (test_a._mode(stdout) == ("-r-xr-xr-x", "shell", "shell", SIZE,
                                    Path(REMOTE).name))


def _call(runner: Callable[..., subprocess.CompletedProcess[str]], argv: list[str],
          records: list[dict[str, object]]) -> subprocess.CompletedProcess[str]:
    try:
        result = runner(argv, capture_output=True, text=True, check=False,
                        timeout=TIMEOUT, cwd=ROOT)
    except subprocess.TimeoutExpired as exc:
        records.append({"argv": argv, "outcome": "TIMEOUT"})
        raise Stop("TIMEOUT_STOP_NO_RETRY") from exc
    except OSError as exc:
        records.append({"argv": argv, "outcome": "HOST_RUNNER_ERROR"})
        raise Stop("HOST_RUNNER_ERROR") from exc
    records.append({"argv": argv, "returncode": result.returncode,
                    "stdout": result.stdout or "", "stderr": result.stderr or ""})
    return result


def execute(args: argparse.Namespace,
            runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> str:
    # This host-only package intentionally has no usable authorization file in
    # the repository. The placeholder validator fails closed until a future
    # separately reviewed schema and signature-verification implementation is
    # approved; tests exercise the command state machine with fake ADB only.
    if not args.authorization_sha256 or not re.fullmatch(r"[0-9a-f]{64}", args.authorization_sha256):
        raise Stop("NEW_SINGLE_USE_AUTHORIZATION_REQUIRED")
    raise Stop("PHASE_C_PACKAGE_NOT_FROZEN_FOR_LIVE_USE")


def rehearse(serial: str, runner: Callable[..., subprocess.CompletedProcess[str]]) -> str:
    if not getattr(runner, "_phase_c_fake_adb", False):
        return "REHEARSAL_REQUIRES_FAKE_ADB"
    records: list[dict[str, object]] = []
    prefix = ["adb", "-s", serial, "shell"]
    try:
        version = _call(runner, ["adb", "version"], records)
        if version.returncode != 0 or version.stderr or f"Version {test_a.ADB_VERSION}" not in version.stdout:
            raise Stop("ADB_VERSION_MISMATCH")
        devices = _call(runner, ["adb", "devices"], records)
        if devices.returncode != 0 or devices.stderr or test_a._devices(devices.stdout) != [(serial, "device")]:
            raise Stop("TARGET_IDENTITY_UNCERTAIN")
        listing = _call(runner, prefix + ["ls", "-ld", REMOTE], records)
        if test_a._is_exact_enoent(listing.stdout, REMOTE, listing.stderr, listing.returncode):
            return "EXACT_PATH_ABSENT_NO_DELETE"
        if listing.returncode != 0 or listing.stderr:
            raise Stop("COMMAND_FAILURE_STOP_NO_RETRY")
        if not identity(listing.stdout):
            raise Stop("FRESH_FILE_IDENTITY_MISMATCH")
        digest = _call(runner, prefix + ["/system/bin/md5", REMOTE], records)
        if digest.returncode != 0 or digest.stderr:
            raise Stop("COMMAND_FAILURE_STOP_NO_RETRY")
        if test_a._digest(digest.stdout) != MD5:
            raise Stop("FRESH_FILE_DIGEST_MISMATCH")
        removal = _call(runner, prefix + ["/system/bin/rm", REMOTE], records)
        if removal.returncode != 0 or removal.stderr:
            raise Stop("DELETE_RESULT_UNKNOWN_NO_RETRY")
        verify = _call(runner, prefix + ["ls", "-ld", REMOTE], records)
        if not test_a._is_exact_enoent(verify.stdout, REMOTE, verify.stderr, verify.returncode):
            raise Stop("POST_DELETE_VERIFICATION_FAILED_NO_RETRY")
        return "EXACT_PATH_ABSENT_AFTER_SINGLE_DELETE"
    except Stop as exc:
        return str(exc)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--execute-authorized-phase-c", action="store_true")
    p.add_argument("--authorization-sha256")
    p.add_argument("--serial")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.dry_run:
        print(json.dumps({"decision": "DRY_RUN_NO_ADB", "commands": command_plan(),
                          "adb_operations": 0}, indent=2))
    elif args.execute_authorized_phase_c:
        try:
            print(execute(args))
        except Stop as exc:
            print(f"PHASE_C_STOP: {exc}", file=sys.stderr)
            return 2
    else:
        print("PHASE_C_NOT_AUTHORIZED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
