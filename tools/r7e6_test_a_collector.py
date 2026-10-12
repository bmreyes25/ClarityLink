#!/usr/bin/env python3
"""Default-disabled, exact-command Test A collector. Never authorizes itself."""
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
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "research/runtime/r7e6-test-a-plan-manifest.json"
ARTIFACT = ROOT / "build/r7e6/test-a/claritylink-target-diag"
REMOTE = "/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f"
PARENT = "/data/local/tmp"
SIZE = 7904
SHA256 = "9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063"
MD5 = "6137a693a77646aaf9a4cf0f351731d4"
TIMEOUT = 12
PARENT_DEADLINE = 4
ADB_VERSION = "37.0.1-15733141"
EXPECTED_PARENT_MODE = "drwxrwx--x"


class Blocked(RuntimeError):
    pass


class TransportAnomaly(Blocked):
    pass


class ProcessExitedFailure(Blocked):
    """Diagnostic returned nonzero after exact process exit was verified."""



def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()


def command_plan() -> list[list[str]]:
    return [
        ["version"],
        ["devices"],
        ["-s", "<EXACT_SERIAL>", "shell", "ls", "-ld", PARENT],
        ["-s", "<EXACT_SERIAL>", "shell", "ls", "-ld", REMOTE],
        ["-s", "<EXACT_SERIAL>", "push", str(ARTIFACT.relative_to(ROOT)), REMOTE],
        ["-s", "<EXACT_SERIAL>", "shell", "ls", "-l", REMOTE],
        ["-s", "<EXACT_SERIAL>", "shell", "/system/bin/md5", REMOTE],
        ["-s", "<EXACT_SERIAL>", "shell", f"{REMOTE} --version; echo __R7E6_STATUS:$?"],
        ["-s", "<EXACT_SERIAL>", "shell", "sh", "-c",
         "test -d /proc/$$ && test -r /proc/$$/stat && test -r /proc/self/stat && "
         "test ! -e /proc/<CHILD_PID> && test ! -e /proc/<PARENT_PID> && "
         "echo R7E6_PIDS_ABSENT:<CHILD_PID>:<PARENT_PID>"],
        ["-s", "<EXACT_SERIAL>", "shell", f"{REMOTE} --self-test; echo __R7E6_STATUS:$?"],
        ["-s", "<EXACT_SERIAL>", "shell", "sh", "-c",
         "test -d /proc/$$ && test -r /proc/$$/stat && test -r /proc/self/stat && "
         "test ! -e /proc/<CHILD_PID> && test ! -e /proc/<PARENT_PID> && "
         "echo R7E6_PIDS_ABSENT:<CHILD_PID>:<PARENT_PID>"],
        ["-s", "<EXACT_SERIAL>", "shell", "/system/bin/rm", REMOTE],
        ["-s", "<EXACT_SERIAL>", "shell", "ls", "-ld", REMOTE],
    ]


def manifest_template() -> dict[str, object]:
    return {
        "manifest_version": "R7E7C-TEST-A-COMMAND-SET-3",
        "collector_source": "tools/r7e6_test_a_collector.py",
        "collector_source_sha256": "FROZEN_AFTER_SOURCE",
        "artifact_path": "build/r7e6/test-a/claritylink-target-diag",
        "artifact_size_bytes": SIZE,
        "artifact_sha256": SHA256,
        "artifact_md5": MD5,
        "staging_mode": "0555",
        "expected_remote_mode": "0555",
        "expected_remote_owner_group": "shell:shell",
        "remote_path": REMOTE,
        "parent_path": PARENT,
        "parent_metadata_requirement": {
            "mode": EXPECTED_PARENT_MODE,
            "owner": "shell",
            "group": "shell",
            "basename": "tmp",
            "format": "one ls -ld line; Android legacy output may omit size and print basename only",
        },
        "child_deadline_seconds": PARENT_DEADLINE - 2,
        "parent_deadline_seconds": PARENT_DEADLINE,
        "host_command_timeout_seconds": TIMEOUT,
        "required_adb_version": ADB_VERSION,
        "push_timeout_seconds": 30,
        "maximum_target_command_wall_seconds": 174,
        "retries": 0,
        "fallbacks": [],
        "target_chmod": False,
        "external_ps": False,
        "external_kill": False,
        "commands": command_plan(),
        "exceptional_recovery": (
            "Host timeout is TEST_A_WATCHDOG_OR_TRANSPORT_ANOMALY: stop, preserve local evidence, "
            "and issue no more target commands. Post-push failures permit one exact rm and exact "
            "ENOENT verification only while no diagnostic was started or after its exact supervisor "
            "lifecycle and PID absence were confirmed. If process state is uncertain, do not remove "
            "the executable; preserve evidence and require separate recovery review."
        ),
        "operator_gates": ["stationary", "safely parked", "center display fully booted",
                           "cluster normal", "no unexpected warnings", "exact power-state observation",
                           "exact audio-state observation", "exclusive ADB window"],
        "post_test_gate": "direct observation STOCK_STATE_UNCHANGED",
        "success_proves": ["ARMv7/API17 diagnostic launched", "--version passed",
                           "bounded --self-test passed", "child and parent processes absent",
                           "exact cleanup and final absence passed", "operator observed stock state unchanged"],
        "success_does_not_prove": ["Display1", "Presentation", "visual output", "CarPlay", "MFi",
                                   "iAP2", "USB ownership", "Test B", "root", "jmcs changes"],
        "authorization": "separate explicit user authorization required; Test A remains NOT_AUTHORIZED",
    }


def _devices(output: str) -> list[tuple[str, str]]:
    rows = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0] != "List" and "\t" in line:
            rows.append((fields[0], fields[1]))
    return rows


def _run(runner: Callable[..., subprocess.CompletedProcess[str]], argv: Sequence[str],
         label: str, timeout: float = TIMEOUT,
         allow_stderr: bool = False) -> subprocess.CompletedProcess[str]:
    try:
        result = runner(list(argv), capture_output=True, text=True, timeout=timeout,
                        check=False, cwd=ROOT)
    except subprocess.TimeoutExpired as exc:
        raise TransportAnomaly(f"{label}: TEST_A_WATCHDOG_OR_TRANSPORT_ANOMALY") from exc
    if result.returncode != 0:
        raise Blocked(f"{label}: command failed with status {result.returncode}")
    if result.stderr and result.stderr.strip() and not allow_stderr:
        raise Blocked(f"{label}: unexpected stderr output")
    return result


def _shell(runner: Callable[..., subprocess.CompletedProcess[str]], adb: str,
           serial: str, *argv: str, label: str) -> str:
    return _run(runner, [adb, "-s", serial, "shell", *argv], label).stdout.replace("\r", "")


def _mode(output: str) -> tuple[str, str, str, int, str] | None:
    lines = output.replace("\r", "").splitlines()
    if len(lines) != 1:
        return None
    match = re.fullmatch(r"(-[rwx-]{9})\s+(\w+)\s+(\w+)\s+(\d+)\s+.*\s+(\S+)", lines[0])
    if not match:
        return None
    return (match.group(1), match.group(2), match.group(3), int(match.group(4)), match.group(5))


def _valid_parent_metadata(output: str) -> bool:
    """Accept one shell-owned /data/local/tmp ls line across Android formats."""
    lines = output.replace("\r", "").splitlines()
    if len(lines) != 1:
        return False
    fields = lines[0].split()
    return (len(fields) >= 5 and fields[0] == EXPECTED_PARENT_MODE
            and fields[1] == "shell" and fields[2] == "shell"
            and fields[-1] in {"tmp", PARENT})


def _digest(output: str) -> str | None:
    lines = output.splitlines()
    if len(lines) != 1:
        return None
    match = re.fullmatch(r"([0-9a-fA-F]{32}) (\S+)", lines[0])
    if not match or match.group(2) != REMOTE:
        return None
    return match.group(1).lower()


def _is_exact_enoent(output: str, path: str = REMOTE,
                     stderr: str = "", returncode: int = 0) -> bool:
    """Recognize only one exact legacy ls ENOENT line, never remote status."""
    if returncode not in (0, 1) or (output and stderr):
        return False
    line = stderr if stderr else output
    if line.endswith("\r\n"):
        line = line[:-2]
    elif line.endswith("\n"):
        line = line[:-1]
    if not line or "\n" in line or "\r" in line:
        return False
    prefixes = ("", "ls: ", "/system/bin/ls: ", "/system/bin/sh: ",
                "/system/bin/sh: ls: ", "/system/bin/sh: /system/bin/ls: ")
    return any(line == f"{prefix}{path}: No such file or directory"
               for prefix in prefixes)


def _absence_gate(runner: Callable[..., subprocess.CompletedProcess[str]],
                  adb: str, serial: str, label: str) -> None:
    try:
        result = runner([adb, "-s", serial, "shell", "ls", "-ld", REMOTE],
                        capture_output=True, text=True, timeout=TIMEOUT,
                        check=False, cwd=ROOT)
    except subprocess.TimeoutExpired as exc:
        raise TransportAnomaly(f"{label}: TEST_A_WATCHDOG_OR_TRANSPORT_ANOMALY") from exc
    if not _is_exact_enoent(result.stdout or "", REMOTE, result.stderr or "", result.returncode):
        raise Blocked(f"{label}: TEST_A_REMOTE_PATH_STATE_UNCERTAIN")


def _invocation(runner: Callable[..., subprocess.CompletedProcess[str]], adb: str,
                serial: str, mode: str) -> tuple[str, list[int]]:
    command = _shell(runner, adb, serial, f"{REMOTE} {mode}; echo __R7E6_STATUS:$?",
                     label=f"diagnostic {mode}")
    statuses = re.findall(r"(?m)^__R7E6_STATUS:(\d+)\s*$", command)
    started = re.findall(r"SUPERVISOR_CHILD_STARTED parent_pid=(\d+) child_pid=(\d+)", command)
    reaped = re.findall(r"SUPERVISOR_CHILD_REAPED parent_pid=(\d+) child_pid=(\d+)", command)
    if len(started) != 1 or len(reaped) != 1 or started[0] != reaped[0]:
        raise Blocked(f"diagnostic {mode}: exact supervisor lifecycle not proven")
    parent, child = map(int, started[0])
    if parent <= 1 or child <= 1 or parent == child:
        raise Blocked(f"diagnostic {mode}: invalid reported process identity")
    absent = _shell(runner, adb, serial, "sh", "-c",
                    "test -d /proc/$$ && test -r /proc/$$/stat && test -r /proc/self/stat && "
                    f"test ! -e /proc/{child} && test ! -e /proc/{parent} && "
                    f"echo R7E6_PIDS_ABSENT:{child}:{parent}", label=f"{mode} exact process absence")
    if absent.strip() != f"R7E6_PIDS_ABSENT:{child}:{parent}":
        raise Blocked(f"diagnostic {mode}: process state remains or is uncertain")
    if statuses != ["0"]:
        raise ProcessExitedFailure(f"diagnostic {mode}: nonzero or missing exact guest status")
    return command, [parent, child]


def _confirm_stock_state() -> bool:
    return input("Directly observe vehicle state unchanged; type STOCK_STATE_UNCHANGED: ").strip() == "STOCK_STATE_UNCHANGED"


def execute(args: argparse.Namespace,
            runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
            confirm_stock_state: Callable[[], bool] = _confirm_stock_state) -> int:
    source = Path(__file__).resolve()
    if not ARTIFACT.is_file() or ARTIFACT.is_symlink() or not stat.S_ISREG(ARTIFACT.lstat().st_mode):
        raise Blocked("staging artifact is missing or not a regular file")
    if stat.S_IMODE(ARTIFACT.stat().st_mode) != 0o555 or ARTIFACT.stat().st_size != SIZE:
        raise Blocked("staging artifact mode or size differs from frozen identity")
    if sha(ARTIFACT) != SHA256 or md5(ARTIFACT) != MD5:
        raise Blocked("staging artifact hash differs from frozen identity")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_sha = sha(MANIFEST)
    expected_manifest = manifest_template()
    expected_manifest["collector_source_sha256"] = sha(source)
    if manifest != expected_manifest:
        raise Blocked("collector source SHA-256 does not match manifest")
    if args.authorized_manifest_sha256 != manifest_sha:
        raise Blocked("manifest SHA-256 does not match the separately authorized package")
    if args.authorized_collector_sha256 != sha(source):
        raise Blocked("collector SHA-256 does not match the separately authorized package")
    if not args.serial or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", args.serial):
        raise Blocked("an exact ADB serial is required")
    if not all((args.stationary, args.parked, args.display_booted, args.cluster_normal,
                args.no_warnings, args.exclusive_adb_window)):
        raise Blocked("all operator and direct-observation gates must be confirmed")
    if not args.power_state or not args.audio_state:
        raise Blocked("exact directly observed power and audio states are required")

    adb = args.adb
    state: dict[str, object] = {
        "push_attempted": False, "diagnostic_started": False,
        "process_state": "NOT_STARTED", "cleanup": "NOT_ATTEMPTED",
        "final_absence": "NOT_CHECKED",
    }
    command_results: list[dict[str, object]] = []

    def classify_operation(argv: Sequence[str]) -> str:
        if argv[-1:] == ["version"]:
            return "HOST_ADB_VERSION"
        if argv[-1:] == ["devices"]:
            return "TARGET_INVENTORY"
        if "push" in argv:
            return "SINGLE_ARTIFACT_PUSH"
        if argv[-3:] == ["ls", "-ld", PARENT]:
            return "PARENT_METADATA"
        if argv[-3:] == ["ls", "-ld", REMOTE]:
            return "EXACT_PATH_ABSENCE_OR_METADATA"
        if argv[-2:] == ["/system/bin/md5", REMOTE]:
            return "REMOTE_MD5"
        if argv[-2:] == ["/system/bin/rm", REMOTE]:
            return "EXACT_PATH_CLEANUP"
        if argv and isinstance(argv[-1], str) and REMOTE in argv[-1] and ("--version" in argv[-1] or "--self-test" in argv[-1]):
            return "DIAGNOSTIC_" + ("VERSION" if "--version" in argv[-1] else "SELF_TEST")
        if "/proc/" in " ".join(argv):
            return "EXACT_PROCESS_ABSENCE"
        return "FROZEN_COMMAND"

    def recorded_runner(argv, **kwargs):
        operation = classify_operation(argv)
        record: dict[str, object] = {
            "command_id": f"R7E6A-{len(command_results) + 1:02d}",
            "operation": operation,
            "push_attempted": bool(state["push_attempted"]),
            "diagnostic_started": bool(state["diagnostic_started"]),
            "process_state": state["process_state"],
        }
        try:
            result = runner(argv, **kwargs)
        except subprocess.TimeoutExpired as exc:
            record.update({"exit_status": "TIMEOUT", "output_classification": "INCOMPLETE",
                           "stderr_classification": "UNKNOWN"})
            command_results.append(record)
            raise
        except OSError:
            record.update({"exit_status": "RUNNER_ERROR", "output_classification": "UNKNOWN",
                           "stderr_classification": "UNKNOWN"})
            command_results.append(record)
            raise
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        if operation == "EXACT_PATH_ABSENCE_OR_METADATA":
            output_classification = (
                "ENOENT" if _is_exact_enoent(stdout, REMOTE, stderr, result.returncode)
                else "EMPTY" if not stdout and not stderr else "PRESENT_OR_UNRECOGNIZED"
            )
        else:
            output_classification = "EMPTY" if not stdout else "NONEMPTY"
        record.update({"exit_status": result.returncode,
                       "output_classification": output_classification,
                       "stderr_classification": "EMPTY" if not stderr else "NONEMPTY"})
        command_results.append(record)
        return result

    def write_failure_evidence(decision: str) -> str:
        evidence_root = ROOT / "build/r7e6a/test-a/evidence"
        evidence_root.mkdir(parents=True, mode=0o700, exist_ok=True)
        if evidence_root.is_symlink():
            raise Blocked("private evidence directory must not be a symlink")
        evidence_root.chmod(0o700)
        evidence_path = evidence_root / (
            f"collector-failure-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{os.getpid():x}.json"
        )
        evidence = {"decision": decision, "target_selector": "REDACTED",
                    "remote_path": REMOTE, "artifact_sha256": SHA256,
                    "collector_sha256": sha(source), "manifest_sha256": manifest_sha,
                    **state, "command_results": command_results,
                    "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
        evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        evidence_path.chmod(0o600)
        return str(evidence_path.relative_to(ROOT))

    push_attempted = False
    cleanup_attempted = False
    process_state_uncertain = False
    try:
        adb_version = _run(recorded_runner, [adb, "version"], "host ADB version")
        if f"Version {ADB_VERSION}" not in adb_version.stdout:
            raise Blocked("host ADB version differs from the frozen command environment")
        inventory = _run(recorded_runner, [adb, "devices"], "exact target inventory")
        if _devices(inventory.stdout) != [(args.serial, "device")]:
            raise Blocked("target inventory is absent, ambiguous, or differs from the supplied exact serial")
        parent = _shell(recorded_runner, adb, args.serial, "ls", "-ld", PARENT,
                        label="destination metadata")
        if not _valid_parent_metadata(parent):
            raise Blocked("destination metadata differs from the frozen shell-owned directory")
        _absence_gate(recorded_runner, adb, args.serial, "exact destination absence")

        push_attempted = True
        state["push_attempted"] = True
        push_result = _run(recorded_runner, [adb, "-s", args.serial, "push", str(ARTIFACT), REMOTE],
                           "single artifact push", 30, allow_stderr=True)
        transfer_lines = [line.strip() for line in (push_result.stdout + "\n" + push_result.stderr).splitlines()
                          if line.strip()]
        expected_transfer = re.compile(
            re.escape(str(ARTIFACT)) + r": 1 file pushed, 0 skipped\. "
            r"[0-9.]+ [KMG]?B/s \([0-9]+ bytes in [0-9.]+s\)"
        )
        if len(transfer_lines) != 1 or not expected_transfer.fullmatch(transfer_lines[0]):
            raise Blocked("single push returned an unrecognized transfer result")
        metadata = _shell(recorded_runner, adb, args.serial, "ls", "-l", REMOTE,
                          label="remote artifact metadata")
        observed = _mode(metadata)
        if observed != ("-r-xr-xr-x", "shell", "shell", SIZE, Path(REMOTE).name):
            raise Blocked("remote artifact type, owner, group, size, or exact mode mismatch")
        remote_md5 = _shell(recorded_runner, adb, args.serial, "/system/bin/md5", REMOTE,
                            label="remote artifact MD5")
        if _digest(remote_md5) != MD5:
            raise Blocked("remote artifact MD5 mismatch")
        process_state_uncertain = True
        state["diagnostic_started"] = True
        state["process_state"] = "UNCERTAIN"
        try:
            version, version_pids = _invocation(recorded_runner, adb, args.serial, "--version")
        except ProcessExitedFailure:
            process_state_uncertain = False
            state["process_state"] = "PROCESS_CONFIRMED_EXITED"
            raise
        process_state_uncertain = False
        state["process_state"] = "PROCESS_CONFIRMED_EXITED"
        if ("CLARITYLINK_DIAG_VERSION=1.0.0" not in version or
                "API_TARGET=17" not in version or "ABI=armeabi-v7a" not in version):
            raise Blocked("--version output differs from the frozen ARMv7/API17 diagnostic")
        process_state_uncertain = True
        state["process_state"] = "UNCERTAIN"
        try:
            self_test, test_pids = _invocation(recorded_runner, adb, args.serial, "--self-test")
        except ProcessExitedFailure:
            process_state_uncertain = False
            state["process_state"] = "PROCESS_CONFIRMED_EXITED"
            raise
        process_state_uncertain = False
        state["process_state"] = "PROCESS_CONFIRMED_EXITED"
        if "SELF_TEST_PASS" not in self_test or "RESOURCE_COUNTS final=0" not in self_test:
            raise Blocked("--self-test did not report bounded success and zero resources")
        cleanup_attempted = True
        state["cleanup"] = "ATTEMPTED"
        rm = _shell(recorded_runner, adb, args.serial, "/system/bin/rm", REMOTE,
                    label="exact artifact cleanup")
        if rm.strip():
            raise Blocked("exact cleanup returned unexpected output")
        _absence_gate(recorded_runner, adb, args.serial, "final exact absence")
        state["cleanup"] = "RM_COMMAND_RETURNED"
        state["final_absence"] = "ENOENT_CONFIRMED"
        if not confirm_stock_state():
            raise Blocked("direct post-test stock-state observation did not confirm unchanged state")
    except TransportAnomaly as exc:
        try:
            evidence_ref = write_failure_evidence("TEST_A_WATCHDOG_OR_TRANSPORT_ANOMALY")
        except Exception:
            evidence_ref = "PRIVATE_EVIDENCE_WRITE_FAILED"
        raise TransportAnomaly(f"{exc}; evidence={evidence_ref}") from exc
    except (Blocked, OSError, ValueError, json.JSONDecodeError) as exc:
        if push_attempted and not cleanup_attempted:
            if process_state_uncertain:
                state["cleanup"] = "NOT_ATTEMPTED_PROCESS_STATE_UNCERTAIN"
                state["process_state"] = "PROCESS_STATE_UNCERTAIN"
                try:
                    evidence_ref = write_failure_evidence("TEST_A_PROCESS_STATE_UNCERTAIN")
                except Exception:
                    evidence_ref = "PRIVATE_EVIDENCE_WRITE_FAILED"
                raise Blocked(
                    f"{exc}; TEST_A_PROCESS_STATE_UNCERTAIN; executable cleanup was not attempted; evidence={evidence_ref}"
                ) from exc
            try:
                cleanup_attempted = True
                state["cleanup"] = "ATTEMPTED"
                _shell(recorded_runner, adb, args.serial, "/system/bin/rm", REMOTE,
                       label="single exact-path failure cleanup")
                _absence_gate(recorded_runner, adb, args.serial, "failure cleanup exact absence")
                state["cleanup"] = "RM_COMMAND_RETURNED"
                state["final_absence"] = "ENOENT_CONFIRMED"
            except Exception as cleanup_error:
                state["cleanup"] = "FAILED_OR_UNCERTAIN"
                state["final_absence"] = "NOT_CONFIRMED"
                try:
                    evidence_ref = write_failure_evidence("TEST_A_CLEANUP_NOT_VERIFIED")
                except Exception:
                    evidence_ref = "PRIVATE_EVIDENCE_WRITE_FAILED"
                raise Blocked(
                    f"{exc}; TEST_A_CLEANUP_NOT_VERIFIED: {cleanup_error}; evidence={evidence_ref}"
                ) from exc
        try:
            evidence_ref = write_failure_evidence("TEST_A_BLOCKED")
        except Exception:
            evidence_ref = "PRIVATE_EVIDENCE_WRITE_FAILED"
        raise Blocked(f"{exc}; evidence={evidence_ref}") from exc
    evidence_root = ROOT / "build/r7e6/test-a/evidence"
    evidence_root.mkdir(parents=True, mode=0o700, exist_ok=True)
    evidence_path = evidence_root / f"test-a-result-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{os.getpid():x}.json"
    evidence = {
        "decision": "TEST_A_PASS_FOR_REVIEW",
        "started_target": True,
        "target_selector": "REDACTED",
        "observed_power_state": args.power_state,
        "observed_audio_state": args.audio_state,
        "artifact_size": SIZE,
        "artifact_sha256": SHA256,
        "artifact_md5": MD5,
        "remote_path": REMOTE,
        "remote_mode": "0555",
        "remote_owner_group": "shell:shell",
        "version_output_sha256": hashlib.sha256(version.encode()).hexdigest(),
        "self_test_output_sha256": hashlib.sha256(self_test.encode()).hexdigest(),
        "version_process_pids": version_pids,
        "self_test_process_pids": test_pids,
        "stock_state": "directly observed unchanged",
        "collector_source_sha256": sha(source),
        "manifest_sha256": manifest_sha,
        "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "command_results": command_results,
        "push_attempted": bool(state["push_attempted"]),
        "diagnostic_started": bool(state["diagnostic_started"]),
        "process_state": state["process_state"],
        "cleanup": state["cleanup"],
        "final_absence": state["final_absence"],
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    evidence_path.chmod(0o600)
    print(json.dumps({"decision": "TEST_A_PASS_FOR_REVIEW", "target": "REDACTED",
                      "artifact_sha256": SHA256, "remote_path": REMOTE,
                      "remote_mode": "0555", "version_child_pids": version_pids,
                      "self_test_child_pids": test_pids,
                      "cleanup": "exact rm succeeded; exact absence verified",
                      "stock_state": "directly observed unchanged",
                      "evidence": str(evidence_path.relative_to(ROOT))}, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true", help="print the frozen plan; zero ADB calls")
    p.add_argument("--execute-authorized-test-a", action="store_true",
                   help="runtime gate only; a separate explicit user authorization is still required")
    p.add_argument("--authorized-collector-sha256")
    p.add_argument("--authorized-manifest-sha256")
    p.add_argument("--serial")
    p.add_argument("--adb", default="adb")
    for flag in ("stationary", "parked", "display-booted", "cluster-normal", "no-warnings",
                 "exclusive-adb-window"):
        p.add_argument("--" + flag, action="store_true")
    p.add_argument("--power-state", help="exact direct observation; do not infer")
    p.add_argument("--audio-state", help="exact direct observation; do not infer")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.dry_run:
        print(json.dumps({"decision": "DRY_RUN_NO_ADB", "adb_operations": 0,
                          "remote_path": REMOTE, "commands": command_plan()}, indent=2))
        return 0
    if not args.execute_authorized_test_a:
        print("NOT_AUTHORIZED")
        return 0
    try:
        return execute(args)
    except (Blocked, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"TEST_A_BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
