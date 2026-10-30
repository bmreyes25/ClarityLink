"""Pinned, fixed-surface Honda observation campaign controller.

`dry-run` is purely local: it does not locate ADB, inspect connected devices, or
create capture files. Live execution requires a private approval attestation
which binds three exact-source AI engineering reviews (not human safety
certification), owner risk acceptance, adopted policy, profile/source hashes,
phases and exact pre-approved ADB serial. This module does not itself grant
that approval.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
from typing import Callable

from collector import (Capture, FixedAdb, ProcessIdentity, SafetyStop,
                       REPO_ROOT, SAFE_DUMPSYS, EXPECTED_ANDROID_RELEASE,
                       EXPECTED_ANDROID_SDK, EXPECTED_PRODUCT_DEVICE,
                       validate_legacy_shell_output,
                       EXPECTED_PRODUCT_BOARD, EXPECTED_HARDWARE)


HERE = Path(__file__).resolve().parent
PROFILE_FILE = HERE / "campaign_profile.json"
PROFILE_HASH_FILE = HERE / "campaign_profile.sha256"
SOURCE_LOCK_FILE = HERE / "campaign_source_hashes.json"
POLICY_FILES = (REPO_ROOT / "AGENTS.md", REPO_ROOT / "docs/safety/vehicle-testing.md",
                REPO_ROOT / "docs/security/vehicle-safety-gates.md",
                REPO_ROOT / "docs/security/single-owner-cp-review-policy.md")
MAX_COMMAND_TIMEOUT = 20
MAX_COMMAND_OUTPUT = 4 * 1024 * 1024
PROCESS_PID_PLACEHOLDER = "<JMCS_PID>"
IDENTITY_PROPERTIES = ("ro.build.version.release", "ro.build.version.sdk",
                       "ro.product.device", "ro.product.board", "ro.hardware")
CAMPAIGN_ID = "CL-HONDA-RUNTIME-DIAGNOSTIC-EXECUTION"
AUTHORIZATION_CATEGORY = "C-P-MA-OWNER-ASSUMED-RISK"
REQUIRED_REVIEW_AGENTS = ("codex", "claude", "ecc")
APPROVED_POWER_STATE = "ON mode; brake pedal not pressed; READY indicator absent"
BASELINE_COMMAND_MANIFEST_SHA256 = "9ac4ecce79769880f0628e743fa8a61d9b094f9bcfbc43b244f2e8798bce5388"
SCOPE_EXCLUSIONS = ["root_or_su", "adb_root", "instrumentation_or_process_attachment",
                    "HondaHack", "receiver_or_display_modification", "firmware", "CAN_or_vehicle_control",
                    "warning_interference", "driving_test", "deployment"]


@dataclass(frozen=True)
class Phase:
    key: str
    title: str
    owner_action: str
    expected_state: str
    operations: tuple[tuple[str, tuple[str, ...], int, int], ...]
    artifacts: tuple[str, ...]
    attestations: tuple[str, ...]


class ManifestEnforcedReader:
    """Campaign-only view that rejects any command outside the current phase."""

    def __init__(self, reader: FixedAdb):
        self._reader = reader
        self.serial = reader.serial
        self.expected: tuple[tuple[str, tuple[str, ...], int, int], ...] = ()
        self.index = 0

    @property
    def records(self):
        return self._reader.records

    def begin_phase(self, phase: Phase) -> None:
        if self.index != len(self.expected):
            raise SafetyStop("prior campaign phase did not consume its complete command manifest")
        self.expected = phase.operations
        self.index = 0

    def assert_phase_complete(self) -> None:
        if self.index != len(self.expected):
            raise SafetyStop("campaign phase ended before consuming its complete command manifest")

    def run(self, operation: str, *args: str, timeout: int = 20,
            max_bytes: int = 32 * 1024 * 1024):
        if self.index >= len(self.expected):
            raise SafetyStop("campaign attempted a command beyond the pinned phase manifest")
        expected_op, expected_args, expected_timeout, expected_bytes = self.expected[self.index]
        actual_args = tuple(args)
        if expected_args and "<JMCS_PID>" in expected_args[0]:
            pattern = re.escape(expected_args[0]).replace(re.escape("<JMCS_PID>"), r"[1-9][0-9]*")
            args_match = len(actual_args) == 1 and re.fullmatch(pattern, actual_args[0]) is not None
        else:
            args_match = actual_args == expected_args
        if (operation, timeout, max_bytes) != (expected_op, expected_timeout, expected_bytes) or not args_match:
            raise SafetyStop("campaign command does not match the next pinned manifest entry")
        self.index += 1
        result = self._reader.run(operation, *args, timeout=timeout, max_bytes=max_bytes)
        validate_legacy_shell_output(operation, actual_args, result[0], result[1], result[2])
        return result


def _identity_operations() -> tuple[tuple[str, tuple[str, ...], int, int], ...]:
    return (("ps", (), 20, 2 * 1024 * 1024),) + (
        ("read", (f"/proc/{PROCESS_PID_PLACEHOLDER}/stat",), 20, 64 * 1024),
        ("read", (f"/proc/{PROCESS_PID_PLACEHOLDER}/status",), 20, 256 * 1024),
        ("read", (f"/proc/{PROCESS_PID_PLACEHOLDER}/cmdline",), 20, 64 * 1024),
    ) * 2


def _display_operations() -> tuple[tuple[str, tuple[str, ...], int, int], ...]:
    return tuple(("dumpsys", (service,), 15, 4 * 1024 * 1024)
                 for service in SAFE_DUMPSYS) + (("logcat", (), 15, 4 * 1024 * 1024),)


def phases() -> tuple[Phase, ...]:
    identity = (
        ("read", ("/proc/version",), 5, 64 * 1024),
        *(("property", (prop,), 5, 64 * 1024) for prop in IDENTITY_PROPERTIES),
        ("id", (), 5, 64 * 1024),
        ("property", ("ro.secure",), 5, 64 * 1024),
        ("property", ("ro.debuggable",), 5, 64 * 1024),
    ) + _identity_operations() + _display_operations()
    observation = _identity_operations() + _display_operations() + _identity_operations()
    return (
        Phase("phase0_baseline", "Factory baseline", "Outdoors, confirm Park/stationary, parking brake, ON mode with brake pedal not pressed and READY absent; confirm normal stock display, cluster, navigation and audio; phone disconnected; no unexpected warning.",
              "All stated baseline conditions are normal.", (), ("owner_observation.json",),
              ("Vehicle stationary and in Park", "Center screen is operating normally",
               "Instrument cluster is operating normally", "No unexpected warning is present",
               "Vehicle power system is ON with READY absent; do not proceed if this changes",
               "Factory Navigation is operating normally", "Audio is operating normally",
               "iPhone is disconnected", "No ClarityLink modification is running")),
        Phase("phase1_identity", "Target identity", "Proceed only after baseline is recorded; use the existing approved ADB transport.",
              "Honda Android/API, board/hardware, shell identity, selected debug properties and one stable jmcs identity match the approved target.",
              identity + _identity_operations(), ("identity/", "platform/", "properties/", "display/", "logs/"),
              ("Existing exact ADB transport is already authorized",)),
        Phase("phase3_connected", "Stock CarPlay connected", "Connect iPhone normally and wait for factory Type110 CarPlay; do not launch ClarityLink.",
              "Center display and audio remain normal; jmcs identity is unchanged.", observation,
              ("identity/", "display/", "logs/"),
              ("Factory CarPlay is visible on the center display", "Center display and audio remain normal")),
        Phase("phase4_navigation_selected", "Factory Navigation selected", "Select factory Navigation using ordinary controls.",
              "Navigation is selected and stock behavior remains normal.", observation,
              ("identity/", "display/", "logs/"),
              ("Factory Navigation is selected", "No abnormal center display, cluster, audio, or warning behavior")),
        Phase("phase4_navigation_deselected", "Factory Navigation deselected", "Leave Navigation using ordinary factory controls.",
              "Page withdrawal/ownership is observed; no warning or abnormal behavior occurs.", observation,
              ("identity/", "display/", "logs/"),
              ("Factory Navigation has been deselected", "No unexpected factory page or warning behavior")),
        Phase("phase4_navigation_reselected", "Factory Navigation reselected", "Reselect Navigation using ordinary factory controls.",
              "Factory Navigation returns normally; jmcs identity is unchanged.", observation,
              ("identity/", "display/", "logs/"),
              ("Factory Navigation returned normally",)),
        Phase("phase6_disconnect", "Normal CarPlay disconnect", "Disconnect CarPlay through the ordinary phone/user flow.",
              "Phone is disconnected; stock display and audio remain normal.", observation,
              ("identity/", "display/", "logs/"),
              ("iPhone is disconnected normally", "Stock display and audio remain normal")),
        Phase("final_restoration", "Final restoration", "Confirm stock center display, cluster, Navigation and audio are normal; no campaign command remains active. The host ADB server may remain running.",
              "Owner confirms no campaign command/client remains active; a shared host ADB server may remain. jmcs remains the same process instance.", observation,
              ("identity/", "display/", "logs/", "owner_observation.json"),
              ("Center display is normal", "Instrument cluster is normal", "Factory Navigation is normal",
               "Audio is normal", "No campaign command/client remains active; a shared host ADB server may remain")),
    )


def _phase_dict(phase: Phase) -> dict[str, object]:
    return {
        "id": phase.key,
        "title": phase.title,
        "owner_action": phase.owner_action,
        "expected_state": phase.expected_state,
        "attestations": list(_phase_attestations(phase)),
        "operations": [
            {"operation": op, "arguments": list(args), "timeout_seconds": timeout,
             "max_output_bytes": maximum, "expected_output": expected_output(op, args),
             "failure_policy": "stop_campaign"}
            for op, args, timeout, maximum in phase.operations
        ],
        "artifacts": list(phase.artifacts),
    }


def _phase_attestations(phase: Phase) -> tuple[str, ...]:
    invariants = ("Vehicle remains stationary in Park", "READY indicator remains absent",
                  "No unexpected warning or abnormal cluster behavior is present",
                  "Center display and instrument cluster remain visibly normal")
    initial = ("Parking brake is set", "Brake pedal is not pressed") if phase.key == "phase0_baseline" else ()
    return tuple(dict.fromkeys((*invariants, *initial, *phase.attestations)))


def profile_payload() -> dict[str, object]:
    return {
        "campaign_id": CAMPAIGN_ID,
        "schema_version": 1,
        "transport": "existing legacy adb shell; exact serial only; no device enumeration",
        "target": {"android_release": EXPECTED_ANDROID_RELEASE,
                   "android_sdk": EXPECTED_ANDROID_SDK,
                   "product_device": EXPECTED_PRODUCT_DEVICE,
                   "product_board": EXPECTED_PRODUCT_BOARD,
                   "hardware": EXPECTED_HARDWARE,
                   "vehicle": "2018 Honda Clarity PHEV Touring (owner-identified)",
                   "platform_family": "Tegra (historical evidence; exact properties checked above)"},
        "privacy": {"raw_output_root": "outside-git-worktree", "directory_mode": "0700",
                    "file_mode": "0600", "logcat": "bounded in-memory summary; no source lines or stderr persisted"},
        "source_lock_sha256": hashlib.sha256(SOURCE_LOCK_FILE.read_bytes()).hexdigest(),
        "policy_documents_sha256": {
            path.relative_to(REPO_ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in POLICY_FILES
        },
        "authorization_category": AUTHORIZATION_CATEGORY,
        "review_semantics": "three hash-bound AI engineering reviews plus separate owner-assumed-risk authorization; not independent human safety certification and not a safety finding",
        "approved_vehicle_power_state": APPROVED_POWER_STATE,
        "scope_exclusions": SCOPE_EXCLUSIONS,
        "campaign_bounds": {
            "max_command_timeout_seconds_sum": sum(op[2] for phase in phases() for op in phase.operations),
            "max_output_bytes_sum": sum(op[3] for phase in phases() for op in phase.operations),
            "max_single_command_timeout_seconds": MAX_COMMAND_TIMEOUT,
            "max_single_command_output_bytes": MAX_COMMAND_OUTPUT,
            "owner_guided_ui_transitions_only": [
                "normal CarPlay connect/disconnect", "factory Navigation select/deselect/reselect"
            ],
            "no_collection_during_operator_transition_waits": True,
        },
        "approval_semantics": "owner risk acceptance is separate from three hash-bound AI review records; records do not authenticate agent identity, independence, competence, or vehicle safety",
        "host_adb_server": "may remain running after the adb client exits; campaign does not stop a shared host server",
        "prohibitions": ["auto_serial", "adb_devices", "network_scan", "su", "adb_root",
                         "setting_changes", "install", "write", "signal", "ptrace",
                         "proc_pid_mem", "injection", "receiver_patch", "can"],
        "phases": [_phase_dict(phase) for phase in phases()],
        "command_manifest_sha256": command_manifest_sha256(),
        "optional_phase": {"id": "hondahack", "included": False,
                           "requires_separate_review_and_owner_approval": True},
    }


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def expected_output(operation: str, args: tuple[str, ...]) -> str:
    if operation == "id":
        return "exit 0 and uid=2000(shell)"
    if operation == "property":
        if args[0] == "ro.secure":
            return "exact expected prior value: 1"
        if args[0] == "ro.debuggable":
            return "exact expected prior value: 0"
        target = {"ro.build.version.release": EXPECTED_ANDROID_RELEASE,
                  "ro.build.version.sdk": EXPECTED_ANDROID_SDK,
                  "ro.product.device": EXPECTED_PRODUCT_DEVICE,
                  "ro.product.board": EXPECTED_PRODUCT_BOARD,
                  "ro.hardware": EXPECTED_HARDWARE}
        return f"exact expected target identity value: {target.get(args[0], 'fixed property value')}"
    if operation == "ps":
        return "exactly one jmcs candidate; /proc identity must confirm root:root /system/bin/jmcs and stable start time"
    if operation == "read" and args == ("/proc/version",):
        return "expected 3.1.10+ kernel-family marker; reject recognized remote errors"
    if operation == "read" and "/proc/" in args[0]:
        return "parser pins PID to root:root /system/bin/jmcs, validates start time, and rejects recognized remote errors"
    if operation == "dumpsys":
        return "nonempty bounded snapshot without recognized remote error/usage output; target-specific response remains unverified"
    if operation == "logcat":
        return "empty output or Android log-line framing; only allowlisted summary and digest are persisted"
    return "exit 0; fixed parser validates the expected result"


def profile_sha256() -> str:
    return hashlib.sha256(canonical_json(profile_payload())).hexdigest()


def command_manifest_sha256() -> str:
    manifest = [{"id": phase.key, "operations": _phase_dict(phase)["operations"]}
                for phase in phases()]
    digest = hashlib.sha256(canonical_json(manifest)).hexdigest()
    if digest != BASELINE_COMMAND_MANIFEST_SHA256:
        raise SafetyStop("fixed C-P command manifest differs from the original PR #118 scope")
    return digest


def verify_pinned_profile() -> str:
    expected = PROFILE_HASH_FILE.read_text(encoding="ascii").split()[0]
    profile_bytes = PROFILE_FILE.read_bytes()
    if profile_bytes != canonical_json(profile_payload()):
        raise SafetyStop("campaign profile file does not match the executable fixed profile")
    actual = hashlib.sha256(profile_bytes).hexdigest()
    for phase in phases():
        for operation, arguments, timeout, maximum in phase.operations:
            planned_args = tuple(arg.replace(PROCESS_PID_PLACEHOLDER, "1234") for arg in arguments)
            FixedAdb.plan_without_adb_lookup("EXACT_APPROVED_SERIAL", operation, planned_args)
            if not (0 < timeout <= MAX_COMMAND_TIMEOUT and 0 < maximum <= MAX_COMMAND_OUTPUT):
                raise SafetyStop("campaign command exceeds the reviewed timeout or output ceiling")
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or actual != expected:
        raise SafetyStop("campaign profile hash does not match its committed pin")
    return actual


def source_hashes() -> dict[str, str]:
    lock = json.loads(SOURCE_LOCK_FILE.read_text(encoding="utf-8"))
    expected_sources = {"analyze.py", "campaign_runner.py", "collector.py", "parsers.py", "session.py"}
    if not isinstance(lock, dict) or set(lock) != expected_sources:
        raise SafetyStop("campaign source hash lock is malformed")
    actual: dict[str, str] = {}
    for relative, expected in sorted(lock.items()):
        path = (HERE / relative).resolve()
        if HERE not in path.parents or not path.is_file():
            raise SafetyStop("campaign source lock contains an invalid path")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if not isinstance(expected, str) or digest != expected:
            raise SafetyStop(f"pinned campaign source hash mismatch: {relative}")
        actual[relative] = digest
    return actual


def _planned_ops(phase: Phase, adb: str, serial: str) -> tuple[dict[str, object], ...]:
    result = []
    for operation, arguments, timeout, maximum in phase.operations:
        display_args = tuple(arg.replace(PROCESS_PID_PLACEHOLDER, "1234") for arg in arguments)
        command = FixedAdb.plan_without_adb_lookup(serial, operation, display_args)
        result.append({"argv": list(command), "timeout_seconds": timeout,
                       "max_output_bytes": maximum,
                       "expected_output": expected_output(operation, arguments),
                       "note": "PID 1234 is a display placeholder; runtime uses validated jmcs PID."})
    return tuple(result)


def dry_run_report(serial: str = "EXACT_APPROVED_SERIAL") -> dict[str, object]:
    """Build full phase plan without importing an ADB executable or making a subprocess call."""
    profile_hash = verify_pinned_profile()
    source_lock = json.loads(SOURCE_LOCK_FILE.read_text(encoding="utf-8"))
    locked_sources = source_hashes()
    phase_rows = []
    for phase in phases():
        phase_rows.append({
            "id": phase.key, "owner_action": phase.owner_action,
            "expected_state": phase.expected_state,
            "attestations": list(_phase_attestations(phase)),
            "commands": list(_planned_ops(phase, "adb", serial)),
            "failure_behavior": "stop immediately; no retry or next phase; save partial evidence",
            "artifact_destination": f"<private-capture-root>/<capture-id>/{phase.key}/",
        })
    return {"campaign_id": "CL-HONDA-RUNTIME-DIAGNOSTIC-EXECUTION",
            "mode": "DRY_RUN_NO_ADB_CONTACT", "profile_sha256": profile_hash,
            "source_hash_lock": source_lock, "verified_source_sha256": locked_sources,
            "phase_count": len(phase_rows), "phases": phase_rows,
            "optional_hondahack": "excluded; separate review and approval required",
            "adb_contact": False, "device_enumeration": False, "files_created": False}


def _path_outside_repo(path: Path, description: str) -> Path:
    requested = path.expanduser()
    if requested.is_symlink():
        raise SafetyStop(f"{description} cannot be a symlink")
    resolved = requested.resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        return resolved
    raise SafetyStop(f"{description} must remain outside the Git worktree")


def verify_effective_policy(policy_commit_sha: str,
                            *, run: Callable[..., object] = subprocess.run) -> None:
    """Require the exact adopted policy on a fresh, clean protected-main checkout.

    This uses fixed local git operations only. Fetch failure or stale/divergent
    checkout fails closed before an ADB client or capture directory is created.
    """
    if not re.fullmatch(r"[0-9a-f]{40}", policy_commit_sha):
        raise SafetyStop("effective policy commit is malformed")
    commands = (
        (["git", "fetch", "--quiet", "origin", "main"], "unable to refresh origin/main"),
        (["git", "branch", "--show-current"], "unable to verify current branch"),
        (["git", "status", "--porcelain", "--untracked-files=normal"], "unable to verify checkout cleanliness"),
        (["git", "rev-parse", "HEAD"], "unable to verify current commit"),
        (["git", "rev-parse", "origin/main"], "unable to verify refreshed origin/main"),
        (["git", "merge-base", "--is-ancestor", policy_commit_sha, "origin/main"],
         "policy commit is not adopted on origin/main"),
    )
    values: list[str] = []
    for argv, error in commands:
        try:
            result = run(argv, cwd=REPO_ROOT, check=False, capture_output=True,
                         text=True, timeout=20)
        except (OSError, subprocess.SubprocessError) as exc:
            raise SafetyStop(error) from exc
        if getattr(result, "returncode", 1) != 0:
            raise SafetyStop(error)
        values.append(getattr(result, "stdout", "").strip())
    branch, dirty, head, remote_main = values[1], values[2], values[3], values[4]
    if branch != "main" or dirty:
        raise SafetyStop("live C-P requires a clean checkout on main")
    if not re.fullmatch(r"[0-9a-f]{40}", head) or head != remote_main:
        raise SafetyStop("local HEAD must exactly match freshly fetched origin/main")


def _review_report(path_value: object, expected_sha: object, agent: str, *,
                   profile_hash: str, sources: dict[str, str], commit_sha: str) -> dict[str, object]:
    if not isinstance(path_value, str) or not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        raise SafetyStop(f"{agent} review artifact path/hash is missing or invalid")
    report_path = _path_outside_repo(Path(path_value), f"{agent} review artifact")
    if report_path.is_symlink() or not report_path.is_file() or report_path.stat().st_size > 2 * 1024 * 1024:
        raise SafetyStop(f"{agent} review artifact must be a bounded regular file")
    if report_path.stat().st_mode & 0o777 != 0o600:
        raise SafetyStop(f"{agent} review artifact must be owner-only (mode 0600)")
    if report_path.stat().st_uid != os.getuid():
        raise SafetyStop(f"{agent} review artifact must be owned by the current host user")
    raw = report_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise SafetyStop(f"{agent} review artifact hash mismatch")
    try:
        report = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SafetyStop(f"{agent} review artifact must be JSON") from exc
    if not isinstance(report, dict) or report.get("agent_id") != agent:
        raise SafetyStop(f"{agent} review artifact identity label is invalid")
    if report.get("review_type") != "ai_engineering_review_not_human_certification":
        raise SafetyStop(f"{agent} report must be labeled as AI engineering review")
    if report.get("reviewed_commit_sha") != commit_sha or report.get("profile_sha256") != profile_hash:
        raise SafetyStop(f"{agent} review does not bind the exact commit and profile")
    if report.get("source_hashes") != sources or report.get("command_manifest_sha256") != command_manifest_sha256():
        raise SafetyStop(f"{agent} review does not bind the exact source and command manifest")
    if report.get("phase_ids") != [phase.key for phase in phases()]:
        raise SafetyStop(f"{agent} review does not bind the exact phase list")
    if report.get("recommendation") != "GO":
        raise SafetyStop(f"{agent} review recommendation is not GO")
    findings = report.get("findings")
    if not isinstance(findings, list) or any(not isinstance(item, dict) for item in findings):
        raise SafetyStop(f"{agent} findings must be a list of structured records")
    allowed_severities = {"critical", "high", "medium", "low", "info"}
    if any(item.get("severity") not in allowed_severities
           or item.get("status") not in {"open", "resolved"}
           or not isinstance(item.get("finding"), str) or not item["finding"].strip()
           for item in findings):
        raise SafetyStop(f"{agent} findings require severity, status and description")
    if any(item.get("severity") in {"critical", "high"} and item.get("status") != "resolved" for item in findings):
        raise SafetyStop(f"{agent} has unresolved critical/high findings")
    if not isinstance(report.get("tool_version"), str) or not report["tool_version"].strip():
        raise SafetyStop(f"{agent} review report requires a nonblank tool/model version or explicit unavailable value")
    for field in ("tests_executed", "unverified_assumptions", "proposed_changes"):
        values = report.get(field)
        if (not isinstance(values, list) or not values
                or any(not isinstance(item, str) or not item.strip() for item in values)):
            raise SafetyStop(f"{agent} review report requires nonblank entries for {field}; state none explicitly")
    return report


def authorize_owner_one_run(approval: dict[str, object], serial: str, profile_hash: str,
                           source_hashes_verified: dict[str, str], capture_id: str,
                           capture_path: Path, *,
                           input_fn: Callable[[str], str] | None = None,
                           output_fn: Callable[[str], None] = print,
                           nonce_fn: Callable[[int], str] = secrets.token_hex) -> dict[str, object]:
    """Ask for fresh, exact owner authorization after all static/effective gates.

    The review/risk file cannot authorize execution by itself and never stores
    a reusable YES. Each invocation creates a fresh challenge before capture or
    ADB setup; only the resulting private capture records that one-run decision.
    """
    if input_fn is None:
        input_fn = input
    nonce = nonce_fn(6)
    if not re.fullmatch(r"[0-9a-f]{12}", nonce):
        raise SafetyStop("one-run authorization challenge generator failed")
    phrase = f"YES {nonce}"
    output_fn("FINAL ONE-RUN AUTHORIZATION — review, do not infer any scope beyond this prompt.")
    output_fn("Owner: Ben Reyes | Vehicle: 2018 Honda Clarity PHEV Touring")
    output_fn(f"Exact ADB serial: {serial}")
    output_fn(f"Profile SHA-256: {profile_hash}")
    output_fn(f"Command manifest SHA-256: {command_manifest_sha256()}")
    output_fn(f"Source SHA-256 map: {json.dumps(source_hashes_verified, sort_keys=True)}")
    output_fn(f"Policy commit: {approval['policy_effective_commit_sha']}")
    output_fn(f"Power state: {APPROVED_POWER_STATE}; outdoors, stationary in Park, parking brake set")
    output_fn(f"Private evidence directory: {capture_path}")
    output_fn("Scope: the fixed eight-phase passive profile only. AI reviews are not human safety certification.")
    output_fn("No root, su, HondaHack, instrumentation, receiver/display modification, firmware, CAN, warning changes, driving, or deployment.")
    response = input_fn(f'Type exactly "{phrase}" to authorize this one run; anything else stops: ')
    if response != phrase:
        raise SafetyStop("owner did not confirm the fresh one-run authorization challenge")
    return {"owner": "Ben Reyes", "decision": "YES", "authorized_utc": datetime.now(timezone.utc).isoformat(),
            "authorization_nonce": nonce, "single_run": True,
            "vehicle": "2018 Honda Clarity PHEV Touring", "adb_serial": serial,
            "capture_id": capture_id, "capture_path": str(capture_path),
            "profile_sha256": profile_hash, "source_hashes": source_hashes_verified,
            "command_manifest_sha256": command_manifest_sha256(),
            "phase_ids": [phase.key for phase in phases()],
            "policy_effective_commit_sha": approval["policy_effective_commit_sha"],
            "authorization_category": AUTHORIZATION_CATEGORY,
            "owner_risk_acceptance_recorded": True,
            "vehicle_power_state": APPROVED_POWER_STATE,
            "hondahack_authorized": False, "scope_exclusions": SCOPE_EXCLUSIONS}


def validate_approval(path: Path, *, profile_hash: str,
                      source_hashes_verified: dict[str, str]) -> tuple[str, dict[str, object]]:
    approval_path = _path_outside_repo(path, "approval record")
    if approval_path.is_symlink() or not approval_path.is_file() or approval_path.stat().st_size > 1024 * 1024:
        raise SafetyStop("approval record must be a bounded regular file")
    mode = approval_path.stat().st_mode & 0o777
    if mode != 0o600:
        raise SafetyStop("approval record must be owner-only (mode 0600)")
    if approval_path.stat().st_uid != os.getuid():
        raise SafetyStop("approval record must be owned by the current host user")
    try:
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SafetyStop("approval record is missing or invalid") from exc
    if not isinstance(approval, dict):
        raise SafetyStop("approval record must be a JSON object")
    if approval.get("campaign_id") != CAMPAIGN_ID or approval.get("authorization_category") != AUTHORIZATION_CATEGORY:
        raise SafetyStop("approval record campaign does not match")
    if approval.get("owner_identity") != "Ben Reyes" or approval.get("vehicle") != "2018 Honda Clarity PHEV Touring":
        raise SafetyStop("owner or exact vehicle identification does not match the fixed campaign")
    if approval.get("owner_risk_acceptance") is not True:
        raise SafetyStop("owner risk acceptance is not recorded for this bounded passive category")
    if approval.get("owner_authorization") != "PENDING_INTERACTIVE_CONFIRMATION" or "owner_authorized_utc" in approval:
        raise SafetyStop("stored approval cannot authorize a run; fresh one-run confirmation is required")
    if approval.get("profile_sha256") != profile_hash:
        raise SafetyStop("approval profile hash does not match the pinned campaign")
    if approval.get("source_hashes") != source_hashes_verified:
        raise SafetyStop("approved source hashes do not match the verified campaign sources")
    if approval.get("phase_ids") != [phase.key for phase in phases()]:
        raise SafetyStop("approved phase scope does not exactly match the fixed campaign")
    if approval.get("command_manifest_sha256") != command_manifest_sha256():
        raise SafetyStop("owner approval command manifest digest does not match the fixed campaign")
    if approval.get("scope_exclusions") != SCOPE_EXCLUSIONS:
        raise SafetyStop("approval must preserve all higher-risk scope exclusions")
    if approval.get("policy_effective") is not True:
        raise SafetyStop("C-P policy adoption is not attested")
    if not isinstance(approval.get("policy_effective_commit_sha"), str) or not re.fullmatch(
            r"[0-9a-f]{40}", approval["policy_effective_commit_sha"]):
        raise SafetyStop("effective C-P policy commit is not recorded")
    reviewed_commit = approval.get("reviewed_commit_sha")
    if not isinstance(reviewed_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", reviewed_commit):
        raise SafetyStop("exact multi-agent reviewed commit is not recorded")
    if approval.get("owner_confirmed_park") is not True or approval.get("owner_confirmed_parking_brake") is not True:
        raise SafetyStop("owner has not attested stationary Park and parking brake conditions")
    if approval.get("hondahack_authorized") is not False:
        raise SafetyStop("HondaHack is excluded from this campaign and requires separate approval")
    approved_power_state = approval.get("approved_vehicle_power_state")
    if approved_power_state != APPROVED_POWER_STATE:
        raise SafetyStop("C-P owner-assumed-risk category requires the pinned ON/non-READY power state")
    if approval.get("owner_confirmed_vehicle_power_state") != approved_power_state:
        raise SafetyStop("owner has not confirmed the reviewer-approved vehicle power state")
    if approval.get("review_disclaimer_acknowledged") is not True:
        raise SafetyStop("owner must acknowledge AI review is not independent human safety certification")
    reviews = approval.get("multi_agent_reviews")
    if not isinstance(reviews, dict) or set(reviews) != set(REQUIRED_REVIEW_AGENTS):
        raise SafetyStop("exact Codex, Claude, and ECC review records are required")
    for agent in REQUIRED_REVIEW_AGENTS:
        row = reviews[agent]
        if not isinstance(row, dict):
            raise SafetyStop(f"{agent} review record is malformed")
        _review_report(row.get("artifact_path"), row.get("artifact_sha256"), agent,
                       profile_hash=profile_hash, sources=source_hashes_verified,
                       commit_sha=approval["reviewed_commit_sha"])
    serial = approval.get("adb_serial")
    if not isinstance(serial, str) or serial == "auto" or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", serial):
        raise SafetyStop("approval must contain one exact pre-approved ADB serial")
    return serial, approval


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.chmod(0o600)
    os.replace(temp, path)


def _write_hash_inventory(root: Path) -> None:
    paths = sorted(root.rglob("*"))
    if any(path.is_symlink() for path in paths):
        raise SafetyStop("capture contains a symlink; refusing hash inventory")
    entries = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}"
               for path in paths if path.is_file() and path.name != "sha256.txt"]
    target = root / "sha256.txt"
    target.write_text("\n".join(entries) + "\n", encoding="ascii")
    target.chmod(0o600)


def verify_capture_hashes(root: Path) -> tuple[str, ...]:
    """Verify a complete private capture inventory, rejecting missing/extra/changed files."""
    if root.expanduser().is_symlink():
        raise SafetyStop("capture root cannot be a symlink")
    root = root.resolve()
    if not root.is_dir() or root.stat().st_mode & 0o777 != 0o700:
        raise SafetyStop("capture root must be a private mode-0700 directory")
    if any(path.is_symlink() for path in root.rglob("*")):
        raise SafetyStop("capture contains a symlink")
    manifest_path = root / "sha256.txt"
    rows: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match or match.group(2) in rows:
            raise SafetyStop("capture hash manifest is malformed or has duplicate paths")
        relative = Path(match.group(2))
        if relative.is_absolute() or ".." in relative.parts:
            raise SafetyStop("capture hash manifest contains an unsafe path")
        rows[relative.as_posix()] = match.group(1)
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*")
              if path.is_file() and path.name != "sha256.txt"}
    if actual != set(rows):
        raise SafetyStop("capture hash manifest does not exactly cover capture files")
    for relative, expected in rows.items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise SafetyStop(f"capture artifact hash mismatch: {relative}")
    return tuple(sorted(rows))


def recover_interrupted_capture(capture_dir: Path) -> dict[str, object]:
    """Offline integrity recovery; never invokes ADB or edits/removes artifacts."""
    requested_root = capture_dir.expanduser()
    if requested_root.is_symlink():
        raise SafetyStop("capture recovery root cannot be a symlink")
    root = requested_root.resolve()
    try:
        root.relative_to(REPO_ROOT)
    except ValueError:
        pass
    else:
        raise SafetyStop("capture recovery path must remain outside the Git worktree")
    if not root.is_dir() or root.stat().st_mode & 0o777 != 0o700:
        raise SafetyStop("capture recovery root must be a private mode-0700 directory")
    if any(path.is_symlink() for path in root.rglob("*")):
        raise SafetyStop("capture recovery refuses symlink artifacts")
    state_path = root / "campaign_state.json"
    if state_path.is_symlink() or not state_path.is_file() or state_path.stat().st_size > 8 * 1024 * 1024:
        raise SafetyStop("capture checkpoint must be a bounded regular file")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SafetyStop("capture has no readable campaign checkpoint") from exc
    if not isinstance(state, dict):
        raise SafetyStop("capture checkpoint must be a JSON object")
    expected = state.get("artifacts", [])
    if not isinstance(expected, list):
        raise SafetyStop("capture checkpoint artifacts must be a list")
    verified = []
    failures = []
    known = set()
    for item in expected:
        if not isinstance(item, dict):
            failures.append("malformed artifact entry")
            continue
        relative = item.get("path")
        if not isinstance(relative, str):
            failures.append("malformed artifact entry")
            continue
        path = (root / relative).resolve()
        if root not in path.parents:
            failures.append("artifact path escapes capture root")
            continue
        known.add(relative)
        if not path.is_file():
            failures.append(f"missing:{relative}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != item.get("sha256"):
            failures.append(f"hash_mismatch:{relative}")
        else:
            verified.append(relative)
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*")
              if path.is_file() and path.name not in {"campaign_state.json", "sha256.txt"}
              and not path.name.endswith(".tmp")}
    orphaned = sorted(actual - known)
    return {"campaign_id": state.get("campaign_id"), "status": "INTERRUPTED_INCOMPLETE",
            "phase_order": state.get("phase_order", []), "current_phase": state.get("current_phase"),
            "verified_artifacts": verified, "orphaned_artifacts": orphaned,
            "integrity_failures": failures,
            "next_step": "preserve this directory; owner/reviewer must decide; do not resume or contact vehicle"}


class Campaign:
    def __init__(self, capture: Capture, output: Path, profile_hash: str,
                 source_hashes_verified: dict[str, str], serial: str,
                 input_fn: Callable[[str], str] = input,
                 output_fn: Callable[[str], None] = print,
                 run_authorization: dict[str, object] | None = None):
        self.capture = capture
        self.output = output
        self.profile_hash = profile_hash
        self.source_hashes = source_hashes_verified
        self.serial = serial
        self.run_authorization = run_authorization
        self.input = input_fn
        self.output_fn = output_fn
        self.phase_order: list[str] = []
        self.completed: list[str] = []
        self.current_phase: str | None = None
        self.expected_identity: ProcessIdentity | None = None
        self.owner_observations: dict[str, dict[str, object]] = {}
        self.state_path = output / "campaign_state.json"
        self.capture.campaign_metadata = {"profile_sha256": profile_hash,
                                          "source_hashes": source_hashes_verified,
                                          "owner_run_authorization": run_authorization}
        original_record_result = self.capture.record_result

        def recording_checkpoint(*args: object, **kwargs: object) -> None:
            original_record_result(*args, **kwargs)
            self._checkpoint("in_progress")

        self.capture.record_result = recording_checkpoint  # type: ignore[method-assign]
        self._checkpoint("initialized")

    def _checkpoint(self, status: str) -> None:
        state = {"campaign_id": "CL-HONDA-RUNTIME-DIAGNOSTIC-EXECUTION",
                 "status": status, "profile_sha256": self.profile_hash,
                 "source_hashes": self.source_hashes, "phase_order": self.phase_order,
                 "owner_run_authorization": self.run_authorization,
                 "completed_phases": self.completed, "current_phase": self.current_phase,
                 "phase_times": self.capture.phase_times,
                 "owner_observations": self.owner_observations,
                 "artifacts": self.capture.files,
                 "command_count": len(self.capture.reader.records),
                 "updated_utc": datetime.now(timezone.utc).isoformat()}
        _atomic_json(self.state_path, state)

    def _write_owner_observation(self, phase: Phase, observation: dict[str, object]) -> None:
        path = self.output / phase.key / "owner_observation.json"
        _atomic_json(path, observation)
        relative = path.relative_to(self.output).as_posix()
        row = {"path": relative, "size": path.stat().st_size,
               "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
               "kind": "owner_observation", "phase": phase.key}
        self.capture.files = [item for item in self.capture.files if item.get("path") != relative]
        self.capture.files.append(row)

    def _attest(self, phase: Phase, *, after_capture: bool = False) -> None:
        if not after_capture:
            self.current_phase = phase.key
            self.phase_order.append(phase.key)
            self.capture.phase_times.setdefault(phase.key, {})["started_utc"] = datetime.now(timezone.utc).isoformat()
            self._checkpoint("phase_started")
        answers: dict[str, bool] = {}
        for check in _phase_attestations(phase):
            answer = self.input(f"{phase.title}\n{phase.owner_action}\nCheck: {check}\n"
                                "Type YES only if true; otherwise type NO: ").strip().upper()
            answers[check] = answer == "YES"
            if answer != "YES":
                self.owner_observations[phase.key] = {
                    "affirmed": False, "attestations": answers,
                    "observed_utc": datetime.now(timezone.utc).isoformat(),
                    "result": "aborted_owner_did_not_confirm"}
                self._write_owner_observation(phase, self.owner_observations[phase.key])
                raise SafetyStop("owner did not affirm every required physical-state check")
        self.owner_observations[phase.key] = {"affirmed": True, "attestations": answers,
                                              "observed_utc": datetime.now(timezone.utc).isoformat()}
        self.capture.phase_times.setdefault(phase.key, {})["owner_attested_utc"] = \
            self.owner_observations[phase.key]["observed_utc"]
        self._write_owner_observation(phase, self.owner_observations[phase.key])
        self._checkpoint("phase_attested")

    def run(self) -> bool:
        phase_rows = phases()
        # Live construction is the concrete FixedAdb adapter. Test doubles and
        # offline replay readers remain injectable without opening a second
        # execution path for the live controller.
        manifest_reader = None
        if isinstance(self.capture.reader, FixedAdb):
            self.capture.reader = ManifestEnforcedReader(self.capture.reader)
            manifest_reader = self.capture.reader
        try:
            if manifest_reader:
                manifest_reader.begin_phase(phase_rows[0])
            self._attest(phase_rows[0])
            if manifest_reader:
                manifest_reader.assert_phase_complete()
            self.completed.append(phase_rows[0].key)
            self.capture.phase_times[phase_rows[0].key]["finished_utc"] = datetime.now(timezone.utc).isoformat()
            self._checkpoint("phase_complete")
            for phase in phase_rows[1:]:
                if manifest_reader:
                    manifest_reader.begin_phase(phase)
                is_final_restoration = phase.key == "final_restoration"
                if is_final_restoration:
                    self.current_phase = phase.key
                    self.phase_order.append(phase.key)
                    self.capture.phase_times.setdefault(phase.key, {})["started_utc"] = datetime.now(timezone.utc).isoformat()
                    self._checkpoint("phase_started")
                else:
                    self._attest(phase)
                if phase.key == "phase1_identity":
                    target = self.capture.verify_target_identity(phase.key)
                    self.capture.target_identity = target
                    _, shell_raw = self.capture.store_required(
                        phase.key, "platform", "shell_identity", "id",
                        timeout=5, max_bytes=64 * 1024)
                    if not re.search(rb"(?:^|\s)uid=2000\(shell\)(?:\s|$)", shell_raw):
                        raise SafetyStop("ordinary ADB shell identity did not match UID 2000")
                    for prop in ("ro.secure", "ro.debuggable"):
                        _, value = self.capture.store_required(
                            phase.key, "properties", prop.replace(".", "_"),
                            "property", prop, timeout=5, max_bytes=64 * 1024)
                        expected = b"1" if prop == "ro.secure" else b"0"
                        if value.strip() != expected:
                            raise SafetyStop(f"selected debug property did not match prior target value: {prop}")
                self.expected_identity = self.capture.collect_campaign_observation(
                    phase.key, expected_identity=self.expected_identity)
                # Prove that the process identity remained stable after the phase snapshot.
                self.capture.assert_same_instance(self.expected_identity, phase=phase.key)
                if manifest_reader:
                    manifest_reader.assert_phase_complete()
                if is_final_restoration:
                    self._attest(phase, after_capture=True)
                self.completed.append(phase.key)
                self.capture.phase_times[phase.key]["finished_utc"] = datetime.now(timezone.utc).isoformat()
                self._checkpoint("phase_complete")
            self._checkpoint("complete")
            self.capture.finalize(self.phase_order)
            verify_capture_hashes(self.output)
            report = {"status": "CAPTURE_COMPLETE_RESTORATION_ATTESTED",
                      "campaign_id": "CL-HONDA-RUNTIME-DIAGNOSTIC-EXECUTION",
                      "profile_sha256": self.profile_hash,
                      "source_hashes": self.source_hashes,
                      "expected_phases": [phase.key for phase in phase_rows],
                      "completed_phases": self.completed,
                      "owner_restoration_attestations": self.owner_observations.get("final_restoration", {}),
                      "capture_hashes_verified": True,
                      "created_utc": datetime.now(timezone.utc).isoformat()}
            report_path = self.output / "completeness_report.json"
            _atomic_json(report_path, report)
            relative = report_path.relative_to(self.output).as_posix()
            report_row = {"path": relative, "size": report_path.stat().st_size,
                          "sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
                          "kind": "completeness_report"}
            self.capture.files.append(report_row)
            self.capture.finalize(self.phase_order)
            verify_capture_hashes(self.output)
            return True
        except (Exception, KeyboardInterrupt, EOFError) as exc:
            self.capture.stop_result = type(exc).__name__
            self.capture.phase_times.setdefault(self.current_phase, {})["finished_utc"] = datetime.now(timezone.utc).isoformat()
            last_command = self.capture.reader.records[-1] if self.capture.reader.records else {}
            self.capture.failure_card = {
                "phase": self.current_phase,
                "action": next((p.owner_action for p in phase_rows if p.key == self.current_phase), "host setup"),
                "expected": next((p.expected_state for p in phase_rows if p.key == self.current_phase), "capture initialized"),
                "actual": type(exc).__name__,
                "operation": last_command.get("operation"),
                "arguments": last_command.get("arguments", []),
                "stock_behavior": "requires owner assessment; software cannot determine physical factory behavior",
                "completed_phases": list(self.completed),
                "recommended_response": "stop and preserve current factory behavior",
                "owner_decision_required": True,
                "partial_hash_verification": "pending",
            }
            failure_path = self.output / "failure_card.json"
            _atomic_json(failure_path, self.capture.failure_card)
            self.capture.files.append({"path": "failure_card.json", "size": failure_path.stat().st_size,
                                      "sha256": hashlib.sha256(failure_path.read_bytes()).hexdigest(),
                                      "kind": "failure_card"})
            self._checkpoint("aborted")
            try:
                self.capture.finalize(self.phase_order)
                verify_capture_hashes(self.output)
                self.capture.failure_card["partial_hash_verification"] = "verified"
                self.capture.failure_card["partial_hash_error"] = None
                _atomic_json(failure_path, self.capture.failure_card)
                failure_row = next(item for item in self.capture.files if item.get("path") == "failure_card.json")
                failure_row.update(size=failure_path.stat().st_size,
                                   sha256=hashlib.sha256(failure_path.read_bytes()).hexdigest())
                self._checkpoint("aborted_partial_hashes_verified")
                self.capture.finalize(self.phase_order)
                verify_capture_hashes(self.output)
                self.output_fn("Partial capture hashes verified; campaign remains incomplete.")
            except Exception as finalize_error:
                self.capture.failure_card["partial_hash_verification"] = "incomplete"
                self.capture.failure_card["partial_hash_error"] = type(finalize_error).__name__
                try:
                    _atomic_json(failure_path, self.capture.failure_card)
                    failure_row = next(item for item in self.capture.files if item.get("path") == "failure_card.json")
                    failure_row.update(size=failure_path.stat().st_size,
                                       sha256=hashlib.sha256(failure_path.read_bytes()).hexdigest())
                    self._checkpoint("aborted_partial_hashes_incomplete")
                    self.capture.finalize(self.phase_order)
                except Exception:
                    pass
                self.output_fn(f"Partial capture hash verification/finalization incomplete ({type(finalize_error).__name__}); preserve partial files.")
            self.output_fn("OWNER DECISION REQUIRED — NO RETRY OR NEXT PHASE STARTED.")
            self.output_fn(f"Phase: {self.current_phase}")
            self.output_fn(f"Action: {next((p.owner_action for p in phase_rows if p.key == self.current_phase), 'host setup')}")
            self.output_fn(f"Expected: {next((p.expected_state for p in phase_rows if p.key == self.current_phase), 'capture initialized')}")
            self.output_fn(f"Actual: stopped ({type(exc).__name__}); private checkpoint preserved at {self.output}")
            self.output_fn(f"Last fixed operation: {last_command.get('operation', 'none')} {last_command.get('arguments', [])}")
            self.output_fn("Factory behavior: owner assessment required before deciding what to do next.")
            self.output_fn(f"Evidence saved: {len(self.capture.files)} private artifacts; incomplete phase manifest retained.")
            self.output_fn("Recommended response: stop and preserve stock factory behavior.")
            self.output_fn("Owner decision required before any new phase or retry.")
            return False


def _approval_template(profile: str, sources: dict[str, str]) -> dict[str, object]:
    return {"campaign_id": CAMPAIGN_ID,
            "authorization_category": AUTHORIZATION_CATEGORY,
            "owner_identity": "Ben Reyes",
            "owner_risk_acceptance": False,
            "vehicle": "2018 Honda Clarity PHEV Touring",
            "owner_authorization": "PENDING_INTERACTIVE_CONFIRMATION",
            "profile_sha256": profile,
            "command_manifest_sha256": command_manifest_sha256(),
            "policy_effective": False,
            "policy_effective_commit_sha": "",
            "owner_confirmed_park": False,
            "owner_confirmed_parking_brake": False,
            "owner_confirmed_vehicle_power_state": "",
            "source_hashes": sources,
            "phase_ids": [phase.key for phase in phases()],
            "adb_serial": "<filled only after separate explicit owner approval>",
            "approved_vehicle_power_state": APPROVED_POWER_STATE,
            "hondahack_authorized": False,
            "scope_exclusions": SCOPE_EXCLUSIONS,
            "review_disclaimer_acknowledged": False,
            "reviewed_commit_sha": "",
            "multi_agent_reviews": {agent: {"artifact_path": "", "artifact_sha256": ""}
                                    for agent in REQUIRED_REVIEW_AGENTS}}


def _print_dry_run() -> int:
    report = dry_run_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("dry-run", help="show pinned plan; never contacts ADB or creates files")
    recover = sub.add_parser("recover", help="offline verification of an interrupted private capture")
    recover.add_argument("capture_dir", type=Path)
    run = sub.add_parser("run", help="live execution; requires adopted policy, private AI reviews and owner authorization")
    run.add_argument("--approval-file", required=True, type=Path)
    run.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "dry-run":
            return _print_dry_run()
        if args.command == "recover":
            print(json.dumps(recover_interrupted_capture(args.capture_dir), indent=2, sort_keys=True))
            return 0
        profile_hash = verify_pinned_profile()
        verified_sources = source_hashes()
        serial, approval = validate_approval(args.approval_file, profile_hash=profile_hash,
                                             source_hashes_verified=verified_sources)
        verify_effective_policy(approval["policy_effective_commit_sha"])
        output_root = _path_outside_repo(args.output_root, "private capture root")
        if output_root.exists() and (output_root.is_symlink() or not output_root.is_dir()):
            raise SafetyStop("private capture root must be a real directory")
        if output_root.exists() and output_root.stat().st_mode & 0o777 != 0o700:
            raise SafetyStop("existing private capture root must already have mode 0700")
        capture_id = ("CLARITY_RUNTIME_CAMPAIGN_" + datetime.now().strftime("%Y%m%d_%H%M%S")
                      + "_" + secrets.token_hex(6))
        output = output_root / capture_id
        if output.exists() or output.is_symlink():
            raise SafetyStop("private capture destination already exists")
        run_authorization = authorize_owner_one_run(
            approval, serial, profile_hash, verified_sources, capture_id, output,
            input_fn=input, output_fn=print)
        output_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if output_root.stat().st_mode & 0o777 != 0o700:
            raise SafetyStop("existing private capture root must already have mode 0700")
        output.mkdir(mode=0o700)
        _atomic_json(output / "campaign_state.json", {
            "campaign_id": "CL-HONDA-RUNTIME-DIAGNOSTIC-EXECUTION",
            "status": "initialized_before_adb_client_creation",
            "profile_sha256": profile_hash, "source_hashes": verified_sources,
            "owner_run_authorization": run_authorization,
            "phase_order": [], "completed_phases": [], "current_phase": None,
            "artifacts": []})
        reader = FixedAdb(serial, resolve_auto=False)
        capture = Capture(reader, output)
        return 0 if Campaign(capture, output, profile_hash, verified_sources, serial,
                             run_authorization=run_authorization).run() else 1
    except (OSError, ValueError, SafetyStop) as exc:
        print(f"refusing/stopped: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
