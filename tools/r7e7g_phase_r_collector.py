#!/usr/bin/env python3
"""Default-disabled, single-use, read-only exact-path recovery inspection.

The implementation prepares a future Phase R package. This program is not
authorization to contact the Honda; the operator must receive a separate,
package-bound approval before using its execute flag.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Callable

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import r7e6_test_a_collector as test_a

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research/runtime/r7e7g-phase-r-manifest.json"
REMOTE = test_a.REMOTE
PARENT = test_a.PARENT
TIMEOUT = 12
EXPECTED_TEST_A_COLLECTOR_SHA256 = "acee02afd1eaef3aab5b4d4b24ded8044fce67e6461c1d4883b552c87465deb5"


class PhaseRStop(RuntimeError):
    pass


def command_plan() -> list[list[str]]:
    return [
        ["version"], ["devices"],
        ["-s", "<EXACT_SERIAL>", "shell", "ls", "-ld", PARENT],
        ["-s", "<EXACT_SERIAL>", "shell", "ls", "-ld", REMOTE],
        ["-s", "<EXACT_SERIAL>", "shell", "/system/bin/md5", REMOTE],
    ]


def manifest_template() -> dict[str, object]:
    return {
        "manifest_version": "R7E7G-PHASE-R-READ-ONLY-1",
        "collector_source": "tools/r7e7g_phase_r_collector.py",
        "collector_source_sha256": "FROZEN_AFTER_SOURCE",
        "imported_test_a_collector_sha256": EXPECTED_TEST_A_COLLECTOR_SHA256,
        "test_a_artifact_sha256": test_a.SHA256,
        "test_a_artifact_md5": test_a.MD5,
        "expected_size": test_a.SIZE,
        "expected_mode": "0555",
        "expected_owner_group": "shell:shell",
        "exact_path": REMOTE,
        "commands": command_plan(),
        "max_target_commands_if_absent": 2,
        "max_target_commands_if_present": 3,
        "host_command_timeout_seconds": TIMEOUT,
        "retries": 0,
        "writes": 0,
        "executable_launches": 0,
        "authorization": "separate explicit, single-use Phase R authorization required",
    }


def _call(runner: Callable[..., subprocess.CompletedProcess[str]], argv: list[str],
          records: list[dict[str, object]]) -> subprocess.CompletedProcess[str]:
    try:
        result = runner(argv, capture_output=True, text=True, check=False,
                        timeout=TIMEOUT, cwd=ROOT)
    except subprocess.TimeoutExpired as exc:
        records.append({"argv": _redact(argv), "outcome": "TIMEOUT"})
        raise PhaseRStop("TIMEOUT_OR_TRANSPORT_UNKNOWN") from exc
    except OSError as exc:
        records.append({"argv": _redact(argv), "outcome": "HOST_RUNNER_ERROR"})
        raise PhaseRStop("HOST_RUNNER_ERROR") from exc
    records.append({"argv": _redact(argv), "returncode": result.returncode,
                    "stdout": (result.stdout or "")[:test_a.MAX_EVIDENCE_TEXT],
                    "stderr": (result.stderr or "")[:test_a.MAX_EVIDENCE_TEXT]})
    return result


def _redact(argv: list[str]) -> list[str]:
    result = argv.copy()
    if len(result) > 2 and result[1] == "-s":
        result[2] = "<REDACTED_SERIAL>"
    return result


def _regular_file(output: str) -> bool:
    return test_a._mode(output) == ("-r-xr-xr-x", "shell", "shell",
                                     test_a.SIZE, Path(REMOTE).name)


def _save(decision: str, records: list[dict[str, object]]) -> Path:
    private = ROOT / "build/r7e7g/phase-r/evidence"
    if private.is_symlink():
        raise PhaseRStop("PRIVATE_EVIDENCE_PATH_UNSAFE")
    private.mkdir(parents=True, mode=0o700, exist_ok=True)
    private.chmod(0o700)
    path = private / (f"phase-r-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{os.getpid():x}.json")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump({"decision": decision, "path": REMOTE, "target": "REDACTED",
                   "records": records, "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat()},
                  stream, indent=2, sort_keys=True)
        stream.write("\n")
    return path


def execute(args: argparse.Namespace,
            runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> str:
    source = Path(__file__).resolve()
    if source.is_symlink() or not stat.S_ISREG(source.stat().st_mode):
        raise PhaseRStop("COLLECTOR_SOURCE_UNSAFE")
    if test_a.sha(Path(test_a.__file__).resolve()) != EXPECTED_TEST_A_COLLECTOR_SHA256:
        raise PhaseRStop("IMPORTED_TEST_A_COLLECTOR_IDENTITY_MISMATCH")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = manifest_template()
    expected["collector_source_sha256"] = test_a.sha(source)
    if manifest != expected or args.authorized_collector_sha256 != test_a.sha(source):
        raise PhaseRStop("COLLECTOR_OR_MANIFEST_IDENTITY_MISMATCH")
    if args.authorized_manifest_sha256 != test_a.sha(MANIFEST):
        raise PhaseRStop("MANIFEST_AUTHORIZATION_MISMATCH")
    if not args.serial or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", args.serial):
        raise PhaseRStop("EXACT_SERIAL_REQUIRED")
    if not all((args.stationary, args.parked, args.display_booted,
                args.cluster_normal, args.no_warnings, args.exclusive_adb_window)):
        raise PhaseRStop("OPERATOR_GATES_INCOMPLETE")
    records: list[dict[str, object]] = []
    decision = "UNKNOWN_OR_AMBIGUOUS_STATE"
    try:
        version = _call(runner, [args.adb, "version"], records)
        if (version.returncode != 0 or version.stderr or
                f"Version {test_a.ADB_VERSION}" not in version.stdout):
            raise PhaseRStop("ADB_VERSION_MISMATCH")
        inventory = _call(runner, [args.adb, "devices"], records)
        if (inventory.returncode != 0 or inventory.stderr or
                test_a._devices(inventory.stdout) != [(args.serial, "device")]):
            raise PhaseRStop("TARGET_IDENTITY_UNCERTAIN")
        prefix = [args.adb, "-s", args.serial, "shell"]
        parent = _call(runner, prefix + ["ls", "-ld", PARENT], records)
        if (parent.returncode != 0 or parent.stderr or
                not test_a._valid_parent_metadata(parent.stdout)):
            raise PhaseRStop("PARENT_CONTEXT_UNEXPECTED")
        listing = _call(runner, prefix + ["ls", "-ld", REMOTE], records)
        if test_a._is_exact_enoent(listing.stdout or "", REMOTE,
                                   listing.stderr or "", listing.returncode):
            decision = "EXACT_PATH_ABSENT"
        elif (listing.returncode == 0 and not listing.stderr
              and _regular_file(listing.stdout)):
            digest = _call(runner, prefix + ["/system/bin/md5", REMOTE], records)
            if (digest.returncode != 0 or digest.stderr or
                    test_a._digest(digest.stdout) != test_a.MD5):
                decision = "UNEXPECTED_FILE_STATE"
            else:
                decision = "EXPECTED_REGULAR_FILE_PRESENT"
        elif (listing.returncode == 0 and not listing.stderr
              and len(listing.stdout.replace("\r", "").splitlines()) == 1
              and listing.stdout[:1] in {"-", "l", "d"}
              and Path(REMOTE).name in listing.stdout):
            decision = "UNEXPECTED_FILE_STATE"
        else:
            decision = "UNKNOWN_OR_AMBIGUOUS_STATE"
    except PhaseRStop as exc:
        decision = str(exc)
    evidence = _save(decision, records)
    print(json.dumps({"decision": decision,
                      "evidence": str(evidence.relative_to(ROOT)),
                      "commands": len(records)}, sort_keys=True))
    return decision


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--execute-authorized-phase-r", action="store_true")
    p.add_argument("--authorized-collector-sha256")
    p.add_argument("--authorized-manifest-sha256")
    p.add_argument("--serial")
    p.add_argument("--adb", default="adb")
    for name in ("stationary", "parked", "display-booted", "cluster-normal",
                 "no-warnings", "exclusive-adb-window"):
        p.add_argument("--" + name, action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.dry_run:
        print(json.dumps({"decision": "DRY_RUN_NO_ADB", "commands": command_plan(),
                          "adb_operations": 0}, indent=2))
        return 0
    if not args.execute_authorized_phase_r:
        print("PHASE_R_NOT_AUTHORIZED")
        return 0
    try:
        return 0 if execute(args) in {"EXACT_PATH_ABSENT", "EXPECTED_REGULAR_FILE_PRESENT"} else 2
    except (PhaseRStop, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"PHASE_R_STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
