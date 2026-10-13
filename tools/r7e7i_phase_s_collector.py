#!/usr/bin/env python3
"""Default-disabled, read-only Phase S boot-continuity inspection.

No authorization is supplied by this file. Its execute mode requires a
separate, single-use package-bound approval and reviewed host-clock bounds.
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
from typing import Callable

if __package__:
    from . import r7e7i_clock_attestation as clock_attestation
else:  # Direct host invocation: tools/ is sys.path[0].
    import r7e7i_clock_attestation as clock_attestation


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research/runtime/r7e7i-phase-s-manifest.json"
OLD_EVIDENCE = ROOT / "build/r7e6a/test-a/evidence/collector-failure-20261012T021444Z-b64f.json"
PHASE_R_EVIDENCE = ROOT / "build/r7e7g/phase-r/evidence/phase-r-20261012T143126461753Z-reviewed.json"
CLOCK_ATTESTATION = ROOT / "build/r7e7i/phase-s/clock-bound-attestation.json"
CLOCK_SIGNATURE = ROOT / "build/r7e7i/phase-s/clock-bound-attestation.json.asc"
OLD_EVIDENCE_SHA256 = "21e6551fde4498603dbfc9129aa4f32a61b0f0c7e89f3a70ba5035cfccee430e"
PHASE_R_EVIDENCE_SHA256 = "001e13ba7c5911a5d03e10114d6d8925cb3e3fa4c619b2ce2ba396bd1cae3ddd"
OLD_FINISHED_UTC = "2026-10-12T02:14:44.929697+00:00"
REMOTE = "/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f"
ARTIFACT_SHA256 = "9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063"
ARTIFACT_MD5 = "6137a693a77646aaf9a4cf0f351731d4"
ADB_VERSION = "37.0.1-15733141"
BOOT_ID = "/proc/sys/kernel/random/boot_id"
UPTIME = "/proc/uptime"
TIMEOUT = 12
MAX_CLOCK_ERROR_SECONDS = 86400
MIN_HISTORICAL_ERROR_SECONDS = 1800
CLOCK_STEP_TOLERANCE_SECONDS = 1.0
UPTIME_ROUNDING_SECONDS = 0.01
BOOT_PROOF_GUARD_SECONDS = 1.0


class PhaseSStop(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_plan() -> list[list[str]]:
    return [
        ["version"], ["devices"],
        ["-s", "<EXACT_SERIAL>", "shell", "/system/bin/cat", BOOT_ID],
        ["-s", "<EXACT_SERIAL>", "shell", "/system/bin/cat", UPTIME],
        ["-s", "<EXACT_SERIAL>", "shell", "/system/bin/cat", BOOT_ID],
    ]


def manifest_template() -> dict[str, object]:
    return {
        "manifest_version": "R7E7I-PHASE-S-READ-ONLY-1",
        "collector_source": "tools/r7e7i_phase_s_collector.py",
        "collector_source_sha256": "FROZEN_AFTER_SOURCE",
        "clock_validation_tool": "tools/r7e7i_clock_attestation.py",
        "clock_validation_tool_sha256": sha(ROOT / "tools/r7e7i_clock_attestation.py"),
        "old_failure_evidence_sha256": OLD_EVIDENCE_SHA256,
        "phase_r_reviewed_evidence_sha256": PHASE_R_EVIDENCE_SHA256,
        "old_failure_finished_utc": OLD_FINISHED_UTC,
        "exact_prior_path": REMOTE,
        "expected_artifact_sha256": ARTIFACT_SHA256,
        "observed_remote_md5": ARTIFACT_MD5,
        "commands": command_plan(),
        "host_command_timeout_seconds": TIMEOUT,
        "max_clock_error_seconds_per_bound": MAX_CLOCK_ERROR_SECONDS,
        "minimum_historical_error_seconds": MIN_HISTORICAL_ERROR_SECONDS,
        "historical_upper_bound_reference": "GitHub Actions run 38196454003 created 2026-10-12T02:36:36Z on R7E7F review head 243ee18fbfa5dd53b64c1c414dade12740a415c8",
        "retries": 0, "fallbacks": 0, "writes": 0,
        "executable_launches": 0, "cleanup": 0,
        "authorization": "separate explicit single-use Phase S authorization required",
    }


def _preflight(args: argparse.Namespace) -> tuple[int, int, dt.datetime]:
    source = Path(__file__)
    if source.is_symlink() or not stat.S_ISREG(source.stat().st_mode):
        raise PhaseSStop("COLLECTOR_SOURCE_UNSAFE")
    if sha(OLD_EVIDENCE) != OLD_EVIDENCE_SHA256 or sha(PHASE_R_EVIDENCE) != PHASE_R_EVIDENCE_SHA256:
        raise PhaseSStop("PRIOR_EVIDENCE_IDENTITY_MISMATCH")
    old = json.loads(OLD_EVIDENCE.read_text(encoding="utf-8"))
    phase_r = json.loads(PHASE_R_EVIDENCE.read_text(encoding="utf-8"))
    if (old.get("decision") != "TEST_A_PROCESS_STATE_UNCERTAIN"
            or old.get("finished_utc") != OLD_FINISHED_UTC
            or old.get("diagnostic_started") is not True
            or phase_r.get("phase_r_decision") != "EXPECTED_REGULAR_FILE_PRESENT"
            or phase_r.get("process_safety_established") is not False
            or phase_r.get("remote_file_classification") != {
                "status": "EXPECTED_REGULAR_FILE_PRESENT", "mode": "0555",
                "owner_group": "shell:shell", "size": 7904,
                "md5": ARTIFACT_MD5, "identity_verified_by_md5": True}
            or phase_r.get("package", {}).get("expected_executable_sha256") != ARTIFACT_SHA256
            or phase_r.get("raw_collector_evidence", {}).get("path") != REMOTE):
        raise PhaseSStop("PRIOR_EVIDENCE_CONTENT_MISMATCH")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = manifest_template()
    expected["collector_source_sha256"] = sha(source)
    if manifest != expected or args.authorized_collector_sha256 != sha(source):
        raise PhaseSStop("COLLECTOR_OR_MANIFEST_IDENTITY_MISMATCH")
    if args.authorized_manifest_sha256 != sha(MANIFEST):
        raise PhaseSStop("MANIFEST_AUTHORIZATION_MISMATCH")
    if not args.serial or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", args.serial):
        raise PhaseSStop("EXACT_SERIAL_REQUIRED")
    if args.adb != "adb":
        raise PhaseSStop("ADB_EXECUTABLE_OVERRIDE_FORBIDDEN")
    if not all((args.stationary, args.parked, args.display_booted,
                args.cluster_normal, args.no_warnings,
                args.head_unit_confirmed, args.adb_stable,
                args.no_other_adb_issuer, args.operator_no_manual_adb,
                args.exclusive_adb_window)):
        raise PhaseSStop("OPERATOR_OR_CLOCK_GATES_INCOMPLETE")
    if (not args.authorized_clock_attestation_sha256
            or not re.fullmatch(r"[0-9a-f]{64}", args.authorized_clock_attestation_sha256)):
        raise PhaseSStop("REVIEWED_CLOCK_BOUNDS_REQUIRED")
    if (any(component.is_symlink() for component in
            (ROOT / "build", ROOT / "build/r7e7i", ROOT / "build/r7e7i/phase-s", CLOCK_ATTESTATION))
            or not stat.S_ISREG(CLOCK_ATTESTATION.stat().st_mode)
            or (CLOCK_ATTESTATION.stat().st_mode & 0o777) != 0o600):
        raise PhaseSStop("CLOCK_ATTESTATION_UNSAFE")
    if sha(CLOCK_ATTESTATION) != args.authorized_clock_attestation_sha256:
        raise PhaseSStop("CLOCK_ATTESTATION_IDENTITY_MISMATCH")
    if (not args.clock_reviewer_keyring or not args.clock_reviewer_fingerprint
            or not re.fullmatch(r"[A-Fa-f0-9]{40,64}", args.clock_reviewer_fingerprint)):
        raise PhaseSStop("TRUSTED_CLOCK_REVIEWER_REQUIRED")
    try:
        validated_clock = clock_attestation.validate(
            CLOCK_ATTESTATION, CLOCK_SIGNATURE, args.clock_reviewer_keyring,
            args.clock_reviewer_fingerprint,
        )
    except (clock_attestation.AttestationError, OSError, ValueError,
            KeyError, TypeError, json.JSONDecodeError) as exc:
        raise PhaseSStop("CLOCK_ATTESTATION_VALIDATION_FAILED") from exc
    return (validated_clock["historical_error_seconds"],
            validated_clock["current_error_seconds"],
            dt.datetime.fromisoformat(validated_clock["expires_utc"]))


def _redact(argv: list[str]) -> list[str]:
    copy = argv.copy()
    if len(copy) > 2 and copy[1] == "-s":
        copy[2] = "<REDACTED_SERIAL>"
    return copy


def _call(runner: Callable[..., subprocess.CompletedProcess[str]], argv: list[str],
          records: list[dict[str, object]]) -> str:
    try:
        result = runner(argv, capture_output=True, text=True, check=False,
                        timeout=TIMEOUT, cwd=ROOT)
    except subprocess.TimeoutExpired as exc:
        records.append({"argv": _redact(argv), "outcome": "TIMEOUT",
                        "partial_stdout": repr(exc.stdout), "partial_stderr": repr(exc.stderr)})
        raise PhaseSStop("INSPECTION_TIMEOUT") from exc
    except OSError as exc:
        records.append({"argv": _redact(argv), "outcome": "HOST_RUNNER_ERROR",
                        "error_type": type(exc).__name__})
        raise PhaseSStop("HOST_RUNNER_ERROR") from exc
    records.append({"argv": _redact(argv), "returncode": result.returncode,
                    "stdout": result.stdout or "", "stderr": result.stderr or ""})
    if result.returncode != 0 or result.stderr:
        raise PhaseSStop("UNEXPECTED_COMMAND_RESPONSE")
    return result.stdout or ""


def _inventory(output: str, serial: str) -> bool:
    lines = output.replace("\r", "").splitlines()
    return lines == ["List of devices attached", f"{serial}\tdevice"]


def _boot_id(output: str) -> str | None:
    normalized = output.replace("\r", "")
    if not re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\n", normalized):
        return None
    value = normalized.strip().lower()
    return value if value != "00000000-0000-0000-0000-000000000000" else None


def _version(output: str) -> bool:
    lines = output.replace("\r", "").splitlines()
    return (len(lines) == 4 and lines[0] == "Android Debug Bridge version 1.0.41"
            and lines[1] == f"Version {ADB_VERSION}"
            and lines[2].startswith("Installed as /")
            and lines[3].startswith("Running on ") and len(lines[3]) > len("Running on "))


def _uptime(output: str) -> float | None:
    normalized = output.replace("\r", "")
    match = re.fullmatch(r"(\d+\.\d{2}) (\d+\.\d{2})\n", normalized)
    if not match:
        return None
    value = float(match.group(1))
    return value if 0 < value < 1_000_000_000 else None


def classify_boot(prior_finished: dt.datetime, started: dt.datetime,
                  uptime_seconds: float, historical_error: int,
                  current_error: int) -> tuple[str, float]:
    # The actual uptime may be rounded down by the old kernel's two-decimal
    # formatter. Using its upper limit makes the inferred boot conservatively old.
    latest_prior = prior_finished + dt.timedelta(seconds=historical_error)
    earliest_current = started - dt.timedelta(seconds=current_error)
    earliest_boot = earliest_current - dt.timedelta(
        seconds=uptime_seconds + UPTIME_ROUNDING_SECONDS)
    margin = (earliest_boot - latest_prior).total_seconds()
    return ("PREVIOUS_PROCESS_TERMINATION_ESTABLISHED" if margin > BOOT_PROOF_GUARD_SECONDS
            else "PROCESS_POSSIBLY_ACTIVE"), margin


def _save(decision: str, records: list[dict[str, object]], detail: dict[str, object]) -> Path:
    private = ROOT / "build/r7e7i/phase-s/evidence"
    for component in (ROOT / "build", ROOT / "build/r7e7i", ROOT / "build/r7e7i/phase-s", private):
        if component.is_symlink():
            raise PhaseSStop("PRIVATE_EVIDENCE_PATH_UNSAFE")
    private.mkdir(parents=True, mode=0o700, exist_ok=True)
    private.chmod(0o700)
    name = f"phase-s-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{os.getpid():x}.json"
    path = private / name
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump({"decision": decision, "records": records, "detail": detail,
                   "old_failure_evidence_sha256": OLD_EVIDENCE_SHA256,
                   "phase_r_reviewed_evidence_sha256": PHASE_R_EVIDENCE_SHA256,
                   "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat()},
                  stream, sort_keys=True, indent=2)
        stream.write("\n")
    return path


def execute(args: argparse.Namespace,
            runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
            now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.timezone.utc),
            monotonic: Callable[[], float] = time.monotonic) -> str:
    historical_error, current_error, valid_until = _preflight(args)
    records: list[dict[str, object]] = []
    detail: dict[str, object] = {
        "historical_clock_error_seconds": historical_error,
        "current_clock_error_seconds": current_error,
        "clock_attestation_sha256": args.authorized_clock_attestation_sha256,
        "prior_finished_utc": OLD_FINISHED_UTC,
    }
    decision = "BOOT_CONTINUITY_UNKNOWN"
    started, monotonic_start = now(), monotonic()
    if started + dt.timedelta(seconds=current_error) > valid_until:
        raise PhaseSStop("CLOCK_ATTESTATION_EXPIRED")
    try:
        version = _call(runner, [args.adb, "version"], records)
        if not _version(version):
            raise PhaseSStop("INSPECTION_IDENTITY_MISMATCH")
        inventory = _call(runner, [args.adb, "devices"], records)
        if not _inventory(inventory, args.serial):
            raise PhaseSStop("INSPECTION_IDENTITY_MISMATCH")
        detail["target_identity_classification"] = "ONE_EXACT_CONFIRMED_DEVICE"
        prefix = [args.adb, "-s", args.serial, "shell", "/system/bin/cat"]
        first = _boot_id(_call(runner, prefix + [BOOT_ID], records))
        if first is None:
            raise PhaseSStop("BOOT_CONTINUITY_UNKNOWN")
        uptime = _uptime(_call(runner, prefix + [UPTIME], records))
        if uptime is None:
            raise PhaseSStop("BOOT_CONTINUITY_UNKNOWN")
        second = _boot_id(_call(runner, prefix + [BOOT_ID], records))
        if second is None:
            raise PhaseSStop("BOOT_CONTINUITY_UNKNOWN")
        if first != second:
            raise PhaseSStop("PROCESS_EVIDENCE_CONFLICT")
        ended, monotonic_end = now(), monotonic()
        if ended + dt.timedelta(seconds=current_error) > valid_until:
            raise PhaseSStop("CLOCK_ATTESTATION_EXPIRED")
        clock_elapsed = (ended - started).total_seconds()
        monotonic_elapsed = monotonic_end - monotonic_start
        if (monotonic_elapsed < 0 or abs(clock_elapsed - monotonic_elapsed) > CLOCK_STEP_TOLERANCE_SECONDS):
            raise PhaseSStop("PROCESS_EVIDENCE_CONFLICT")
        prior = dt.datetime.fromisoformat(OLD_FINISHED_UTC)
        decision, margin = classify_boot(prior, started, uptime,
                                         historical_error, current_error)
        detail.update({"boot_id": first, "uptime_seconds": uptime,
                       "host_started_utc": started.isoformat(),
                       "host_ended_utc": ended.isoformat(),
                       "host_monotonic_elapsed_seconds": monotonic_elapsed,
                       "boot_after_prior_margin_seconds": margin,
                       "scope": "previous diagnostic invocation only; no current process scan"})
    except PhaseSStop as exc:
        decision = str(exc)
    evidence = _save(decision, records, detail)
    print(json.dumps({"decision": decision,
                      "evidence": str(evidence.relative_to(ROOT)),
                      "commands": len(records)}, sort_keys=True))
    return decision


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--execute-authorized-phase-s", action="store_true")
    p.add_argument("--authorized-collector-sha256")
    p.add_argument("--authorized-manifest-sha256")
    p.add_argument("--serial")
    p.add_argument("--adb", default="adb")
    p.add_argument("--authorized-clock-attestation-sha256")
    p.add_argument("--clock-reviewer-keyring", type=Path)
    p.add_argument("--clock-reviewer-fingerprint")
    for name in ("stationary", "parked", "display-booted", "cluster-normal",
                 "no-warnings", "head-unit-confirmed", "adb-stable",
                 "no-other-adb-issuer", "operator-no-manual-adb",
                 "exclusive-adb-window"):
        p.add_argument("--" + name, action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.dry_run:
        print(json.dumps({"decision": "DRY_RUN_NO_ADB", "commands": command_plan(),
                          "adb_operations": 0}, indent=2))
        return 0
    if not args.execute_authorized_phase_s:
        print("PHASE_S_NOT_AUTHORIZED")
        return 0
    try:
        result = execute(args)
        return 0 if result in {"PREVIOUS_PROCESS_TERMINATION_ESTABLISHED",
                               "PROCESS_POSSIBLY_ACTIVE"} else 2
    except (PhaseSStop, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"PHASE_S_STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
