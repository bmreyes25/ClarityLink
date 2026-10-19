#!/usr/bin/env python3
"""Exact-source, resumable API17 CL-R4 fault acceptance orchestrator."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


CASES = [
    ("CL-R4-01", "In-flight PFD producer death", "default", [
        "CL_R4_TYPE111_INFLIGHT_PRODUCER_DEATH_CLEANUP_PASS",
        "CL_R4_TYPE111_PRODUCER_DEATH_RESTART_PASS",
    ]),
    ("CL-R4-02", "Type111 View death and reattachment", "reattach", [
        "CL_R4A_VIEW_REATTACH_PASS",
        "CL_R4_TYPE111_CONSUMER_REATTACH_PASS",
    ]),
    ("CL-R4-03", "Type110-only sink failure", "type110-failure", [
        "CL_R4B_TYPE110_ONLY_FAILURE_PASS",
    ]),
    ("CL-R4-04", "Unexpected compositor-owner death", "owner-death", [
        "CL_R4B_PARENT_OWNER_DEATH_API17_PASS",
        "CL_R4B_OWNER_DEATH_FRESH_SESSION_RECOVERY_PASS",
    ]),
    ("CL-R4-05", "Reentrant teardown", "reentrant", [
        "CL_R4B_REENTRANT_TEARDOWN_API17_PASS",
        "CL_R4B_REENTRANT_PARENT_TEARDOWN_PASS",
    ]),
    ("CL-R4-06", "Delayed Binder callback", "delayed-callback", [
        "CL_R4B_DELAYED_CALLBACK_POST_TEARDOWN_PASS",
        "CL_R4B_DELAYED_SINK_CALLBACK_PASS",
    ]),
    ("CL-R4-07", "Generation, ownership, and replay attacks", "default", [
        "CL_R4B_SAME_UID_REGISTRATION_ATTACK_PASS",
        "CL_R4_STREAM_GENERATION_ISOLATION_PASS",
        "CL_R4B_OWNER_DEATH_SESSION_CAPACITY_PASS",
    ]),
    ("CL-R4-08", "Queue saturation during failure", "default", [
        "CL_R4_QUEUE_PRODUCER_DEATH_SATURATED",
        "CL_R4_QUEUE_PRODUCER_DEATH_PASS",
        "CL_R4_API17_DUAL_STREAM_SATURATION_PASS",
    ]),
    ("CL-R4-09", "Cross-UID security", "type110-failure", [
        "CL_R4_CROSS_UID_ATTACKS_PASS",
    ]),
    ("CL-R4-10", "Aggregate resource cleanup across the required matrix", "aggregate", []),
    ("CL-R4-11", "Warning preemption", "reattach", [
        "CL_R6_DECODED_TYPE111_WARNING_BLOCK_PASS",
        "CL_R6_DECODED_TYPE111_WARNING_RECOVERY_PASS",
    ]),
    ("CL-R4-12", "Type111 crash recovery with a saturated View queue", "view-crash-queue", [
        "CL_R4B_QUEUE_SATURATED_VIEW_DEATH_REQUEST",
        "CL_R4B_TYPE111_CRASH_RECOVERY_API17_PASS",
    ]),
]

MODES = {
    "default": None,
    "reattach": "--cl-r4-type111-reattach",
    "type110-failure": "--cl-r4b-type110-failure",
    "owner-death": "--cl-r4b-parent-owner-death",
    "reentrant": "--cl-r4b-reentrant-teardown",
    "delayed-callback": "--cl-r4b-delayed-callback",
    "view-crash": "--cl-r4b-view-crash",
    "view-crash-queue": "--cl-r4b-view-crash-queue-saturated",
    "queue-parent-teardown": "--cl-r4b-reentrant-teardown-queue-saturated",
}

REQUIRED_COMBINATIONS = [
    ("CL-R4B-P01", "Saturated Type111 queue plus actual View-process death"),
    ("CL-R4B-P02", "Saturated Type111 queue plus parent teardown"),
    ("CL-R4B-P03", "Producer death during teardown"),
    ("CL-R4B-P04", "View death during teardown"),
    ("CL-R4B-P05", "Compositor-owner death during child cleanup"),
    ("CL-R4B-P06", "Decoder shutdown during active frame delivery"),
    ("CL-R4B-P07", "Callback timeout and delayed callback"),
    ("CL-R4B-P08", "Multiple consecutive View replacements"),
    ("CL-R4B-P09", "View replacement racing parent shutdown"),
    ("CL-R4B-P10", "Final-source registration and security regression"),
    ("CL-R4B-P11", "Final-source crash-recovery regression"),
    ("CL-R4B-P12", "Aggregate cleanup over the complete fault matrix"),
]

PRIORITY_RUNS = {
    "CL-R4B-P02": ("queue-parent-teardown", [
        "CL_R4B_QUEUE_SATURATED_PARENT_TEARDOWN_REQUEST",
        "CL_R4B_QUEUE_SATURATED_PARENT_TEARDOWN_PASS",
        "CL_R4B_REENTRANT_TEARDOWN_API17_PASS",
        "TYPE111_PARENT_TEARDOWN_COMPLETED",
        "IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true active_pfd_transfers=0 retained_frame_bytes=0",
    ]),
}


def run(repo: Path, args: list[str], log_path: Path, env: dict[str, str] | None = None) -> int:
    with log_path.open("wb") as log:
        proc = subprocess.Popen(args, cwd=repo, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        assert proc.stdout is not None
        for chunk in iter(proc.stdout.readline, b""):
            log.write(chunk)
            log.flush()
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
        return proc.wait()


def fingerprint(repo: Path) -> tuple[str, list[str]]:
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=repo).split(b"\0")
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=repo
    ).split(b"\0")
    paths = sorted({p.decode() for p in tracked + untracked if p})
    digest = hashlib.sha256()
    for rel in paths:
        path = repo / rel
        if path.is_file():
            digest.update(rel.encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest(), paths


def atomic_json(path: Path, data: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    temp.replace(path)
    if path.name == "checkpoint.json":
        write_report(path.parent / "acceptance-report.md", data)


def execution_status(exit_code: int) -> str:
    # 5 is the emulator's bounded boot timeout: the required scenario never
    # started, so this is an execution blocker rather than a product failure.
    return "BLOCKED" if exit_code in (2, 5, 7, 8) else "FAIL"


def case_evidence_valid(case: dict, markers: list[str], source_hash: str,
                        apk_hash: str) -> bool:
    log_path = Path(case.get("log", ""))
    if (case.get("source_sha256") != source_hash or case.get("apk_sha256") != apk_hash or
            not log_path.is_file() or not case.get("evidence_log_sha256")):
        return False
    content = log_path.read_text(errors="replace")
    return (hashlib.sha256(log_path.read_bytes()).hexdigest() == case["evidence_log_sha256"] and
            all(marker in content for marker in markers))


def write_report(path: Path, data: dict) -> None:
    lines = ["# CL-R4 API17 acceptance", "", f"Overall: **{data.get('overall', 'NOT_RUN')}**", "",
             f"Source revision: `{data['source']['git_head']}`",
             f"Source fingerprint: `{data['source']['fingerprint_sha256']}`",
             f"APK SHA-256: `{data.get('apk_sha256', 'NOT_BUILT')}`",
             f"Evidence: `{data['evidence_dir']}`", "", "## Required CL-R4 matrix", "",
             "| ID | Scenario | Status | Evidence |", "|---|---|---|---|"]
    for case in data.get("cases", []):
        lines.append(f"| {case['id']} | {case['name']} | **{case['status']}** | `{case.get('log', 'none')}` |")
    lines += ["", "## Remaining priority combinations", "",
              "These exact interleavings are acceptance gates. Component tests do not count as substitutes.", "",
              "| ID | Scenario | Status |", "|---|---|---|"]
    for case in data.get("combinations", []):
        lines.append(f"| {case['id']} | {case['name']} | **{case['status']}** |")
    lines += ["", "A PASS is emitted only when all 12 required CL-R4 cases and all 12 priority combinations pass on this exact source and APK.", ""]
    path.write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", type=Path, help="resume an existing evidence directory")
    parser.add_argument("--retry-failed", action="store_true", help="rerun failed cases after diagnosis")
    parser.add_argument("--only", action="append", help="run only named case IDs (repeatable)")
    ns = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=repo, text=True).strip()
    source_hash, source_files = fingerprint(repo)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    evidence = ns.resume.resolve() if ns.resume else repo / "build" / f"cl-r4-acceptance-{stamp}-{os.getpid()}"
    candidate_build = repo / "build" / f"cl-r4-candidate-{stamp}-{os.getpid()}"
    if ns.resume and not evidence.is_dir():
        parser.error(f"resume directory does not exist: {evidence}")
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / ".claritylink-r4-acceptance").write_text("CL-R4\n")
    checkpoint_path = evidence / "checkpoint.json"
    if checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text())
        if checkpoint.get("source", {}).get("fingerprint_sha256") != source_hash:
            parser.error("source fingerprint changed; refusing to reuse checkpoint evidence")
        if checkpoint.get("source", {}).get("git_head") != head:
            parser.error("Git HEAD changed; refusing to reuse checkpoint evidence")
    else:
        checkpoint = {
            "schema": "claritylink.cl-r4-acceptance.v1",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "evidence_dir": str(evidence),
            "build_dir": str(candidate_build),
            "source": {"git_head": head, "branch": branch,
                       "fingerprint_sha256": source_hash, "files": source_files},
            "build": {"status": "NOT_RUN"},
            "apk_sha256": None,
            "cases": [{"id": case_id, "name": name, "status": "NOT_RUN"}
                      for case_id, name, _mode, _markers in CASES],
            "mode_runs": {},
            "combinations": [{"id": case_id, "name": name, "status": "NOT_RUN",
                               "reason": "Dedicated runtime interleaving is not implemented in the canonical API17 harness."}
                              for case_id, name in REQUIRED_COMBINATIONS],
        }
        atomic_json(checkpoint_path, checkpoint)

    # The guarded Android build tool accepts a fresh direct child of repo/build.
    # Its output and the resumable acceptance evidence are separate ignored directories.
    build_dir = Path(checkpoint["build_dir"])
    build_env = os.environ.copy()
    build_env["CL_IMP_03_BUILD_DIR"] = str(build_dir)
    build_log = evidence / "build.log"
    if checkpoint["build"].get("status") != "PASS":
        code = run(repo, [str(repo / "tools/build_cl_imp_03_apks.sh")], build_log, build_env)
        checkpoint["build"] = {"status": "PASS" if code == 0 else "FAIL",
                               "exit_code": code, "log": str(build_log)}
        apk = build_dir / "claritylink-display-lab.apk"
        if code == 0 and apk.is_file():
            checkpoint["apk_sha256"] = hashlib.sha256(apk.read_bytes()).hexdigest()
            checkpoint["apk_path"] = str(apk)
        else:
            checkpoint["build"]["status"] = "FAIL"
        atomic_json(checkpoint_path, checkpoint)
    if checkpoint["build"]["status"] != "PASS":
        checkpoint["overall"] = "BLOCKED" if checkpoint["build"].get("exit_code") in (2, 7, 8) else "FAIL"
        write_report(evidence / "acceptance-report.md", checkpoint)
        return 1
    recorded_apk = Path(checkpoint.get("apk_path", ""))
    if not recorded_apk.is_file() or hashlib.sha256(recorded_apk.read_bytes()).hexdigest() != checkpoint["apk_sha256"]:
        parser.error("built APK changed or disappeared; refusing to reuse checkpoint evidence")

    selected = set(ns.only or [case[0] for case in CASES])
    known = {case[0] for case in CASES}
    unknown = selected - known
    if unknown:
        parser.error("unknown case ID(s): " + ", ".join(sorted(unknown)))
    by_id = {case["id"]: case for case in checkpoint["cases"]}
    for case_id, name, mode, markers in CASES:
        if case_id not in selected or case_id == "CL-R4-10":
            continue
        old = by_id.get(case_id)
        old_log = Path(old.get("log", "")) if old else Path()
        old_log_valid = bool(old and old_log.is_file() and old.get("evidence_log_sha256") ==
                             hashlib.sha256(old_log.read_bytes()).hexdigest())
        if old and old.get("status") == "PASS" and old.get("apk_sha256") == checkpoint["apk_sha256"] and \
                old.get("source_sha256") == source_hash and old_log_valid:
            print(f"{case_id} CHECKPOINT_PASS evidence_reused=true")
            continue
        if old and old.get("status") == "FAIL" and not ns.retry_failed:
            print(f"{case_id} CHECKPOINT_FAIL evidence_reused=true (use --retry-failed after diagnosis)")
            continue
        cached_mode = checkpoint.setdefault("mode_runs", {}).get(mode)
        cached_log = Path(cached_mode.get("log", "")) if cached_mode else Path()
        cached_log_valid = bool(cached_mode and cached_log.is_file() and
                                cached_mode.get("evidence_log_sha256") ==
                                hashlib.sha256(cached_log.read_bytes()).hexdigest())
        if cached_mode and cached_mode.get("apk_sha256") == checkpoint["apk_sha256"] and \
                cached_mode.get("source_sha256") == source_hash and \
                cached_mode.get("status") in ("PASS", "FAIL", "BLOCKED") and \
                cached_log_valid and not ns.retry_failed:
            log_path = Path(cached_mode["log"])
            code = cached_mode["exit_code"]
            print(f"MODE_CHECKPOINT mode={mode} evidence_reused=true log={log_path}")
        else:
            run_args = [str(repo / "tools/run_cl_imp_03_emulator.sh")]
            if MODES[mode]:
                run_args.append(MODES[mode])
            log_path = evidence / f"mode-{mode}.log"
            checkpoint["mode_runs"][mode] = {"status": "NOT_RUN", "log": str(log_path),
                                              "apk_sha256": checkpoint["apk_sha256"],
                                              "source_sha256": source_hash,
                                              "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
            by_id[case_id] = {"id": case_id, "name": name, "mode": mode, "status": "NOT_RUN",
                              "log": str(log_path), "source_sha256": source_hash,
                              "apk_sha256": checkpoint["apk_sha256"]}
            checkpoint["cases"] = [by_id.get(item[0], {"id": item[0], "name": item[1],
                                                       "status": "NOT_RUN"}) for item in CASES]
            atomic_json(checkpoint_path, checkpoint)
            run_env = os.environ.copy()
            run_env["CL_IMP_03_BUILD_DIR"] = str(build_dir)
            code = run(repo, run_args, log_path, run_env)
            checkpoint["mode_runs"][mode] = {"status": "PASS" if code == 0 else
                                              execution_status(code),
                                              "exit_code": code, "log": str(log_path),
                                              "apk_sha256": checkpoint["apk_sha256"],
                                              "source_sha256": source_hash,
                                              "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        mode_log_hash = hashlib.sha256(log_path.read_bytes()).hexdigest()
        checkpoint["mode_runs"][mode]["evidence_log_sha256"] = mode_log_hash
        output = log_path.read_text(errors="replace")
        missing = [marker for marker in markers if marker not in output]
        status = "PASS" if code == 0 and not missing else (
            execution_status(code))
        by_id[case_id] = {"id": case_id, "name": name, "mode": mode, "status": status,
                          "exit_code": code, "missing_markers": missing,
                          "log": str(log_path), "source_sha256": source_hash,
                          "apk_sha256": checkpoint["apk_sha256"],
                          "evidence_log_sha256": mode_log_hash,
                          "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        checkpoint["cases"] = [by_id.get(item[0], {"id": item[0], "name": item[1],
                                                   "status": "NOT_RUN"}) for item in CASES]
        atomic_json(checkpoint_path, checkpoint)
        print(f"{case_id} {status} exit_code={code} missing_markers={len(missing)} log={log_path}")

    # Audit every cached PASS before deriving any aggregate or priority result.
    case_markers = {case_id: markers for case_id, _name, _mode, markers in CASES}
    for case_record in checkpoint["cases"]:
        if case_record.get("status") != "PASS" or case_record.get("id") == "CL-R4-10":
            continue
        if not case_evidence_valid(case_record, case_markers[case_record["id"]],
                                   source_hash, checkpoint["apk_sha256"]):
            case_record.update({"status": "NOT_RUN", "reason":
                                "Cached PASS evidence failed source, APK, log-hash, or marker audit."})
    by_id = {case["id"]: case for case in checkpoint["cases"]}

    # Priority interleavings are separate runtime cases; unsupported ones remain NOT_RUN.
    priority = {case["id"]: case for case in checkpoint["combinations"]}
    for derived_id in ("CL-R4B-P01", "CL-R4B-P07", "CL-R4B-P09", "CL-R4B-P10",
                       "CL-R4B-P11", "CL-R4B-P12"):
        priority[derived_id].update({"status": "NOT_RUN", "reason":
                                     "Recomputed from audited case evidence for this run."})
    view_crash = by_id.get("CL-R4-12", {})
    if view_crash.get("status") == "PASS":
        priority["CL-R4B-P01"].update({"status": "PASS", "evidence_case": "CL-R4-12",
                                       "log": view_crash.get("log"),
                                       "apk_sha256": checkpoint["apk_sha256"]})
    def derive_priority(combo_id: str, required_cases: tuple[str, ...], required_markers: tuple[str, ...]) -> None:
        selected_cases = [by_id.get(case_id, {}) for case_id in required_cases]
        if not selected_cases or any(case.get("status") != "PASS" for case in selected_cases):
            return
        logs = "\n".join(Path(case.get("log", "")).read_text(errors="replace")
                           for case in selected_cases if Path(case.get("log", "")).is_file())
        if all(marker in logs for marker in required_markers):
            priority[combo_id].update({"status": "PASS", "evidence_cases": list(required_cases),
                                       "evidence_markers": list(required_markers),
                                       "apk_sha256": checkpoint["apk_sha256"]})

    derive_priority("CL-R4B-P07", ("CL-R4-06",),
                    ("CL_R4B_DELAYED_CALLBACK_POST_TEARDOWN_PASS", "CL_R4B_DELAYED_SINK_CALLBACK_PASS"))
    derive_priority("CL-R4B-P09", ("CL-R4-05",),
                    ("CL_R4B_TEARDOWN_REPLACEMENT_REJECTED", "replacement_during_shutdown_rejected=true"))
    derive_priority("CL-R4B-P10", ("CL-R4-07", "CL-R4-09"),
                    ("CL_R4B_SAME_UID_REGISTRATION_ATTACK_PASS", "CL_R4_CROSS_UID_ATTACKS_PASS"))
    derive_priority("CL-R4B-P11", ("CL-R4-04", "CL-R4-12"),
                    ("CL_R4B_OWNER_DEATH_FRESH_SESSION_RECOVERY_PASS",
                     "CL_R4B_TYPE111_CRASH_RECOVERY_API17_PASS"))
    checkpoint["combinations"] = [priority[cid] for cid, _ in REQUIRED_COMBINATIONS]
    for combo_id, (mode, markers) in PRIORITY_RUNS.items():
        current = priority[combo_id]
        invalid_prior_evidence = False
        if current.get("status") == "PASS" and \
                current.get("source_sha256") == source_hash and \
                current.get("apk_sha256") == checkpoint["apk_sha256"]:
            previous_log = Path(current.get("log", ""))
            intact = previous_log.is_file() and current.get("evidence_log_sha256") == \
                hashlib.sha256(previous_log.read_bytes()).hexdigest()
            has_markers = intact and all(marker in previous_log.read_text(errors="replace")
                                         for marker in markers)
            if has_markers:
                continue
            current.update({"status": "NOT_RUN", "reason":
                            "Prior PASS evidence missing, altered, or missing required markers."})
            invalid_prior_evidence = True
        elif current.get("status") == "PASS":
            current.update({"status": "NOT_RUN", "reason":
                            "Prior PASS belongs to a different source or APK."})
            invalid_prior_evidence = True
        if current.get("status") in ("FAIL", "BLOCKED") and not ns.retry_failed:
            continue
        cached_mode = checkpoint.setdefault("mode_runs", {}).get(mode)
        cached_log = Path(cached_mode.get("log", "")) if cached_mode else Path()
        cached_log_valid = bool(cached_mode and cached_log.is_file() and
                                cached_mode.get("evidence_log_sha256") ==
                                hashlib.sha256(cached_log.read_bytes()).hexdigest())
        if cached_mode and cached_mode.get("apk_sha256") == checkpoint["apk_sha256"] and \
                cached_mode.get("source_sha256") == source_hash and \
                cached_mode.get("status") in ("PASS", "FAIL", "BLOCKED") and \
                cached_log_valid and not ns.retry_failed and \
                not invalid_prior_evidence:
            log_path = Path(cached_mode["log"])
            code = cached_mode["exit_code"]
        else:
            run_args = [str(repo / "tools/run_cl_imp_03_emulator.sh"), MODES[mode]]
            log_path = evidence / f"mode-{mode}.log"
            checkpoint["mode_runs"][mode] = {"status": "NOT_RUN", "log": str(log_path),
                                              "apk_sha256": checkpoint["apk_sha256"],
                                              "source_sha256": source_hash,
                                              "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
            checkpoint["combinations"] = [priority[cid] for cid, _ in REQUIRED_COMBINATIONS]
            atomic_json(checkpoint_path, checkpoint)
            run_env = os.environ.copy()
            run_env["CL_IMP_03_BUILD_DIR"] = str(build_dir)
            code = run(repo, run_args, log_path, run_env)
            checkpoint["mode_runs"][mode] = {"status": "PASS" if code == 0 else
                                              execution_status(code),
                                              "exit_code": code, "log": str(log_path),
                                              "apk_sha256": checkpoint["apk_sha256"],
                                              "source_sha256": source_hash,
                                              "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        mode_log_hash = hashlib.sha256(log_path.read_bytes()).hexdigest()
        checkpoint["mode_runs"][mode]["evidence_log_sha256"] = mode_log_hash
        output = log_path.read_text(errors="replace")
        missing = [marker for marker in markers if marker not in output]
        priority[combo_id] = {"id": combo_id, "name": dict(REQUIRED_COMBINATIONS)[combo_id],
                              "status": "PASS" if code == 0 and not missing else
                              execution_status(code),
                              "exit_code": code, "missing_markers": missing,
                              "log": str(log_path), "source_sha256": source_hash,
                              "apk_sha256": checkpoint["apk_sha256"],
                              "evidence_log_sha256": mode_log_hash}
    checkpoint["combinations"] = [priority[cid] for cid, _ in REQUIRED_COMBINATIONS]
    ordinary = [by_id.get(case[0], {}).get("status", "NOT_RUN") for case in CASES
                if case[0] != "CL-R4-10"]
    combinations = [item.get("status", "NOT_RUN") for item in checkpoint["combinations"]
                    if item.get("id") != "CL-R4B-P12"]
    cleanup_requirements = {
        "CL-R4-01": ("CL_R4_TYPE111_INFLIGHT_PRODUCER_DEATH_CLEANUP_PASS", "active_pfd=0", "retained_bytes=0"),
        "CL-R4-02": ("CL_R4A_VIEW_REATTACH_PASS", "parent_teardown_request=accepted", "cleanup=pass"),
        "CL-R4-03": ("CL_R4B_TYPE110_ONLY_FAILURE_PASS", "streams_unregistered=2", "active_pfd_transfers=0", "retained_frame_bytes=0"),
        "CL-R4-04": ("CL_R4B_PARENT_OWNER_DEATH_API17_PASS", "old_pid_absent=true",
                     "old_registrations_cleared_by_process_exit=true",
                     "old_process_resources_reclaimed_by_exit=true",
                     "predeath_pfd_transfers=0", "predeath_retained_bytes=0",
                     "resource_state=not_observable_after_owner_death"),
        "CL-R4-05": ("CL_R4B_REENTRANT_TEARDOWN_API17_PASS", "streams_unregistered=2", "active_pfd_transfers=0", "retained_bytes=0"),
        "CL-R4-06": ("CL_R4B_DELAYED_CALLBACK_POST_TEARDOWN_PASS", "stale_release_rejected=true", "session_not_resurrected=true",
                     "IPC_STREAM_UNREGISTERED session_id=", "stream_type=110", "active_pfd_transfers=0",
                     "stream_type=111", "IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true",
                     "retained_frame_bytes=0"),
        "CL-R4-07": ("CL_R4B_SAME_UID_REGISTRATION_ATTACK_PASS", "CL_R4_STREAM_GENERATION_ISOLATION_PASS", "cleanup=pass"),
        "CL-R4-08": ("CL_R4_QUEUE_PRODUCER_DEATH_PASS", "queue_frames_after=0", "queue_bytes_after=0"),
        "CL-R4-09": ("CL_R4_CROSS_UID_ATTACKS_PASS", "active_services_before_after=true",
                     "explicit_denials=23", "unverified_no_effect=0", "pids_unchanged=true"),
        "CL-R4-11": ("CL_R6_DECODED_TYPE111_WARNING_BLOCK_PASS", "CL_R6_DECODED_TYPE111_WARNING_RECOVERY_PASS", "cleanup=pass"),
        "CL-R4-12": ("CL_R4B_QUEUE_SATURATED_VIEW_DEATH_REQUEST", "CL_R4B_TYPE111_CRASH_RECOVERY_API17_PASS", "resources=zero"),
    }
    cleanup_line_requirements = {
        "CL-R4-06": (
            ("IPC_STREAM_UNREGISTERED", "stream_type=110", "active_pfd_transfers=0"),
            ("IPC_STREAM_UNREGISTERED", "stream_type=111", "active_pfd_transfers=0"),
            ("IPC_REMOTE_PROCESS_DESTROYED", "resources_cleared=true",
             "active_pfd_transfers=0", "retained_frame_bytes=0"),
        ),
        "CL-R4-09": (
            ("IPC_STREAM_UNREGISTERED", "stream_type=110", "active_pfd_transfers=0"),
            ("IPC_STREAM_UNREGISTERED", "stream_type=111", "active_pfd_transfers=0"),
            ("IPC_REMOTE_PROCESS_DESTROYED", "resources_cleared=true",
             "active_pfd_transfers=0", "retained_frame_bytes=0"),
        ),
    }
    cleanup_receipts = []
    cleanup_logs = []
    for case in CASES:
        if case[0] == "CL-R4-10":
            continue
        case_result = by_id.get(case[0], {})
        case_log = Path(case_result.get("log", ""))
        if case_result.get("status") != "PASS" or not case_log.is_file():
            cleanup_receipts.append(False)
            continue
        case_output = case_log.read_text(errors="replace")
        cleanup_logs.append(case_output)
        required_cleanup = cleanup_requirements[case[0]]
        required_lines = cleanup_line_requirements.get(case[0], ())
        lines = case_output.splitlines()
        cleanup_receipts.append(
            all(marker in case_output for marker in required_cleanup) and
            all(any(all(term in line for term in group) for line in lines)
                for group in required_lines)
        )
    all_cleanup_evidence = "\n".join(cleanup_logs)
    aggregate_dimensions = (
        "registrations=0" in all_cleanup_evidence and
        ("queue_frames_after=0" in all_cleanup_evidence or "queue=zero" in all_cleanup_evidence) and
        ("stale_type110_frame=rejected" in all_cleanup_evidence or
         "stale_frame_rejected=true" in all_cleanup_evidence)
    )
    aggregate_status = "PASS" if (ordinary and all(x == "PASS" for x in ordinary) and
                                    all(x == "PASS" for x in combinations) and
                                    cleanup_receipts and all(cleanup_receipts) and
                                    aggregate_dimensions) else "NOT_RUN"
    by_id["CL-R4-10"] = {"id": "CL-R4-10", "name": CASES[9][1],
                         "status": aggregate_status,
                         "reason": "All component cases and priority interleavings must pass with zero resource receipts."}
    if aggregate_status == "PASS":
        priority["CL-R4B-P12"].update({"status": "PASS", "evidence_case": "CL-R4-01..12",
                                       "cleanup_receipts": "all_required_cases",
                                       "apk_sha256": checkpoint["apk_sha256"]})
        checkpoint["combinations"] = [priority[cid] for cid, _ in REQUIRED_COMBINATIONS]
    checkpoint["cases"] = [by_id.get(item[0], {"id": item[0], "name": item[1],
                                               "status": "NOT_RUN"}) for item in CASES]
    final_source_hash, _final_source_files = fingerprint(repo)
    if final_source_hash != source_hash:
        checkpoint["source_changed_during_run"] = {"initial": source_hash,
                                                   "final": final_source_hash}
        for case in checkpoint["cases"]:
            if case.get("status") == "PASS":
                case["status"] = "FAIL"
                case["reason"] = "Source fingerprint changed during acceptance run."
        for case in checkpoint["combinations"]:
            if case.get("status") == "PASS":
                case["status"] = "FAIL"
                case["reason"] = "Source fingerprint changed during acceptance run."
    checkpoint["overall"] = "PASS" if final_source_hash == source_hash and (
        all(c.get("status") == "PASS" for c in checkpoint["cases"]) and
        all(c.get("status") == "PASS" for c in checkpoint["combinations"])
    ) else ("BLOCKED" if any(c.get("status") == "BLOCKED" for c in
                             checkpoint["cases"] + checkpoint["combinations"]) else "PARTIAL")
    if checkpoint["overall"] == "PASS":
        r7_log = evidence / "cl-r7-regression.log"
        r7_build = repo / "build" / f"cl-r7-regression-{stamp}-{os.getpid()}"
        r7_env = os.environ.copy()
        r7_env["CL_R7_BUILD_DIR"] = str(r7_build)
        code = run(repo, [str(repo / "tools/run_cl_r7_lab.sh")], r7_log, r7_env)
        r7_output = r7_log.read_text(errors="replace")
        r7_status = "PASS" if code == 0 and "CL_R7_END_TO_END_LAB_PASS" in r7_output else "FAIL"
        checkpoint["cl_r7_regression"] = {
            "status": r7_status, "exit_code": code, "log": str(r7_log),
            "build_dir": str(r7_build), "source_sha256": source_hash,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
        checkpoint["overall"] = "PASS" if r7_status == "PASS" else "FAIL"
        post_r7_source_hash, _post_r7_source_files = fingerprint(repo)
        if post_r7_source_hash != source_hash:
            checkpoint["source_changed_during_run"] = {
                "initial": source_hash, "final": post_r7_source_hash,
                "phase": "cl_r7_regression"}
            checkpoint["overall"] = "FAIL"
    checkpoint["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    atomic_json(checkpoint_path, checkpoint)
    write_report(evidence / "acceptance-report.md", checkpoint)
    print(f"CL_R4_ACCEPTANCE_{checkpoint['overall']} evidence={evidence}")
    return 0 if checkpoint["overall"] == "PASS" else (2 if checkpoint["overall"] == "BLOCKED" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
