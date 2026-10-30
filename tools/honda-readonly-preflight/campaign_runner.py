"""Pinned, fixed-surface Honda observation campaign controller.

`dry-run` is purely local: it does not locate ADB, inspect connected devices, or
create capture files. Live execution requires a private approval attestation
which binds an independent-technical-review artifact, exact profile/source hashes, phases,
and the exact pre-approved ADB serial. This module does not itself grant that
approval.
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
import sys
from typing import Callable

from collector import (Capture, FixedAdb, ProcessIdentity, SafetyStop,
                       REPO_ROOT, SAFE_DUMPSYS, EXPECTED_ANDROID_RELEASE,
                       EXPECTED_ANDROID_SDK, EXPECTED_PRODUCT_DEVICE,
                       EXPECTED_PRODUCT_BOARD, EXPECTED_HARDWARE)


HERE = Path(__file__).resolve().parent
PROFILE_FILE = HERE / "campaign_profile.json"
PROFILE_HASH_FILE = HERE / "campaign_profile.sha256"
SOURCE_LOCK_FILE = HERE / "campaign_source_hashes.json"
POLICY_FILES = (REPO_ROOT / "AGENTS.md", REPO_ROOT / "docs/safety/vehicle-testing.md",
                REPO_ROOT / "docs/security/vehicle-safety-gates.md")
MAX_COMMAND_TIMEOUT = 20
MAX_COMMAND_OUTPUT = 4 * 1024 * 1024
PROCESS_PID_PLACEHOLDER = "<JMCS_PID>"
IDENTITY_PROPERTIES = ("ro.build.version.release", "ro.build.version.sdk",
                       "ro.product.device", "ro.product.board", "ro.hardware")


@dataclass(frozen=True)
class Phase:
    key: str
    title: str
    owner_action: str
    expected_state: str
    operations: tuple[tuple[str, tuple[str, ...], int, int], ...]
    artifacts: tuple[str, ...]
    attestations: tuple[str, ...]


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
        Phase("phase0_baseline", "Factory baseline", "Confirm Park/stationary, normal stock display, cluster, navigation and audio; phone disconnected; no unexpected warning.",
              "All stated baseline conditions are normal.", (), ("owner_observation.json",),
              ("Vehicle stationary and in Park", "Center screen is operating normally",
               "Instrument cluster is operating normally", "No unexpected warning is present",
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
        "attestations": list(phase.attestations),
        "operations": [
            {"operation": op, "arguments": list(args), "timeout_seconds": timeout,
             "max_output_bytes": maximum, "expected_output": expected_output(op, args),
             "failure_policy": "stop_campaign"}
            for op, args, timeout, maximum in phase.operations
        ],
        "artifacts": list(phase.artifacts),
    }


def profile_payload() -> dict[str, object]:
    return {
        "campaign_id": "CL-HONDA-RUNTIME-DIAGNOSTIC-EXECUTION",
        "schema_version": 1,
        "transport": "existing legacy adb shell; exact serial only; no device enumeration",
        "target": {"android_release": EXPECTED_ANDROID_RELEASE,
                   "android_sdk": EXPECTED_ANDROID_SDK,
                   "product_device": EXPECTED_PRODUCT_DEVICE,
                   "product_board": EXPECTED_PRODUCT_BOARD,
                   "hardware": EXPECTED_HARDWARE,
                   "platform_family": "Tegra (historical evidence; exact properties checked above)"},
        "privacy": {"raw_output_root": "outside-git-worktree", "directory_mode": "0700",
                    "file_mode": "0600", "logcat": "bounded in-memory summary; no source lines or stderr persisted"},
        "source_lock_sha256": hashlib.sha256(SOURCE_LOCK_FILE.read_bytes()).hexdigest(),
        "policy_documents_sha256": {
            path.relative_to(REPO_ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in POLICY_FILES
        },
        "authorization_category": "C-P",
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
        "approval_semantics": "owner and independent technical reviewer records are hash-bound human attestations; this tool does not verify identity, independence, or competence",
        "host_adb_server": "may remain running after the adb client exits; campaign does not stop a shared host server",
        "prohibitions": ["auto_serial", "adb_devices", "network_scan", "su", "adb_root",
                         "setting_changes", "install", "write", "signal", "ptrace",
                         "proc_pid_mem", "injection", "receiver_patch", "can"],
        "phases": [_phase_dict(phase) for phase in phases()],
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
        return "exit 0 and exactly one jmcs process identity"
    if operation == "read" and args == ("/proc/version",):
        return "exit 0 and expected 3.1.10+ kernel-family marker"
    if operation == "read" and "/proc/" in args[0]:
        return "exit 0; parser validates PID, UID/GID fields, cmdline and process start time"
    if operation == "dumpsys":
        return "exit 0; preserve bounded output for offline display/window/layer analysis"
    if operation == "logcat":
        return "exit 0; only allowlisted event summary and digest are persisted"
    return "exit 0; fixed parser validates the expected result"


def profile_sha256() -> str:
    return hashlib.sha256(canonical_json(profile_payload())).hexdigest()


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
            "attestations": list(phase.attestations),
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


def validate_approval(path: Path, *, profile_hash: str,
                      source_hashes_verified: dict[str, str]) -> tuple[str, dict[str, object]]:
    approval_path = _path_outside_repo(path, "approval record")
    if approval_path.is_symlink() or not approval_path.is_file() or approval_path.stat().st_size > 1024 * 1024:
        raise SafetyStop("approval record must be a bounded regular file")
    mode = approval_path.stat().st_mode & 0o777
    if mode != 0o600:
        raise SafetyStop("approval record must be owner-only (mode 0600)")
    try:
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SafetyStop("approval record is missing or invalid") from exc
    if not isinstance(approval, dict):
        raise SafetyStop("approval record must be a JSON object")
    if approval.get("campaign_id") != "CL-HONDA-RUNTIME-DIAGNOSTIC-EXECUTION":
        raise SafetyStop("approval record campaign does not match")
    if approval.get("owner_authorization") != "YES":
        raise SafetyStop("exact owner authorization is not recorded")
    try:
        datetime.fromisoformat(str(approval.get("owner_authorized_utc", "")).replace("Z", "+00:00"))
    except ValueError as exc:
        raise SafetyStop("owner authorization timestamp is missing or invalid") from exc
    if approval.get("profile_sha256") != profile_hash:
        raise SafetyStop("approval profile hash does not match the pinned campaign")
    if approval.get("source_hashes") != source_hashes_verified:
        raise SafetyStop("approved source hashes do not match the verified campaign sources")
    if approval.get("phase_ids") != [phase.key for phase in phases()]:
        raise SafetyStop("approved phase scope does not exactly match the fixed campaign")
    if approval.get("policy_effective") is not True:
        raise SafetyStop("C-P policy adoption is not attested")
    if not isinstance(approval.get("policy_effective_commit_sha"), str) or not re.fullmatch(
            r"[0-9a-f]{40}", approval["policy_effective_commit_sha"]):
        raise SafetyStop("effective C-P policy commit is not recorded")
    if approval.get("owner_confirmed_park") is not True or approval.get("owner_confirmed_parking_brake") is not True:
        raise SafetyStop("owner has not attested stationary Park and parking brake conditions")
    if approval.get("hondahack_authorized") is not False:
        raise SafetyStop("HondaHack is excluded from this campaign and requires separate approval")
    reviewer = approval.get("independent_technical_review")
    if not isinstance(reviewer, dict) or reviewer.get("review_type") != "independent_technical":
        raise SafetyStop("C-P independent technical review is not recorded")
    if not isinstance(reviewer.get("reviewer_competence"), str) or not reviewer["reviewer_competence"].strip():
        raise SafetyStop("reviewer competence for Android/ADB and vehicle diagnostics is not recorded")
    if reviewer.get("reviewer_independence_attested") is not True:
        raise SafetyStop("reviewer independence is not attested")
    if not isinstance(reviewer.get("reviewer_identity"), str) or not reviewer["reviewer_identity"].strip():
        raise SafetyStop("independent technical reviewer identity is not recorded")
    approved_power_state = approval.get("approved_vehicle_power_state")
    if not isinstance(approved_power_state, str) or not approved_power_state.strip():
        raise SafetyStop("review-approved vehicle electrical power state is not recorded")
    if reviewer.get("reviewed_vehicle_power_state") != approved_power_state:
        raise SafetyStop("technical review does not bind the exact vehicle electrical power state")
    if approval.get("owner_confirmed_vehicle_power_state") != approved_power_state:
        raise SafetyStop("owner has not confirmed the reviewer-approved vehicle power state")
    if reviewer.get("review_decision") != "APPROVED":
        raise SafetyStop("independent technical reviewer has not approved this exact C-P procedure")
    if reviewer.get("reviewed_profile_sha256") != profile_hash:
        raise SafetyStop("technical review does not bind the pinned profile hash")
    if reviewer.get("reviewed_source_hashes") != source_hashes_verified:
        raise SafetyStop("technical review does not bind the verified source hashes")
    if reviewer.get("reviewed_phase_ids") != [phase.key for phase in phases()]:
        raise SafetyStop("technical review does not bind the exact phase list")
    if not isinstance(reviewer.get("artifact_path"), str):
        raise SafetyStop("exact procedure review artifact is not recorded")
    review_path = _path_outside_repo(Path(reviewer["artifact_path"]), "safety review artifact")
    if review_path.is_symlink() or not review_path.is_file() or review_path.stat().st_size > 8 * 1024 * 1024:
        raise SafetyStop("safety review artifact must be a bounded regular file")
    if review_path.stat().st_mode & 0o777 != 0o600:
        raise SafetyStop("safety review artifact must be owner-only (mode 0600)")
    expected_review_sha = reviewer.get("artifact_sha256")
    if not isinstance(expected_review_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_review_sha):
        raise SafetyStop("safety review artifact hash is invalid")
    if hashlib.sha256(review_path.read_bytes()).hexdigest() != expected_review_sha:
        raise SafetyStop("safety review artifact hash mismatch")
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
                 output_fn: Callable[[str], None] = print):
        self.capture = capture
        self.output = output
        self.profile_hash = profile_hash
        self.source_hashes = source_hashes_verified
        self.serial = serial
        self.input = input_fn
        self.output_fn = output_fn
        self.phase_order: list[str] = []
        self.completed: list[str] = []
        self.current_phase: str | None = None
        self.expected_identity: ProcessIdentity | None = None
        self.owner_observations: dict[str, dict[str, object]] = {}
        self.state_path = output / "campaign_state.json"
        self.capture.campaign_metadata = {"profile_sha256": profile_hash,
                                          "source_hashes": source_hashes_verified}
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

    def _attest(self, phase: Phase) -> None:
        self.current_phase = phase.key
        self.phase_order.append(phase.key)
        self.capture.phase_times.setdefault(phase.key, {})["started_utc"] = datetime.now(timezone.utc).isoformat()
        self._checkpoint("phase_started")
        answers: dict[str, bool] = {}
        for check in phase.attestations:
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
        try:
            self._attest(phase_rows[0])
            self.completed.append(phase_rows[0].key)
            self.capture.phase_times[phase_rows[0].key]["finished_utc"] = datetime.now(timezone.utc).isoformat()
            self._checkpoint("phase_complete")
            for phase in phase_rows[1:]:
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
    return {"campaign_id": "CL-HONDA-RUNTIME-DIAGNOSTIC-EXECUTION",
            "owner_authorization": "NO",
            "owner_authorized_utc": "",
            "profile_sha256": profile,
            "policy_effective": False,
            "policy_effective_commit_sha": "",
            "owner_confirmed_park": False,
            "owner_confirmed_parking_brake": False,
            "owner_confirmed_vehicle_power_state": "",
            "source_hashes": sources,
            "phase_ids": [phase.key for phase in phases()],
            "adb_serial": "<filled only after separate explicit owner approval>",
            "approved_vehicle_power_state": "",
            "hondahack_authorized": False,
            "independent_technical_review": {"review_type": "not_obtained",
                                         "reviewer_identity": "",
                                         "reviewer_competence": "",
                                         "reviewer_independence_attested": False,
                                         "review_decision": "NOT_APPROVED",
                                         "reviewed_profile_sha256": "",
                                         "reviewed_source_hashes": {},
                                         "reviewed_phase_ids": [],
                                         "reviewed_vehicle_power_state": "",
                                         "artifact_path": "",
                                         "artifact_sha256": ""}}


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
    run = sub.add_parser("run", help="live execution; requires private review and owner attestations")
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
        serial, _ = validate_approval(args.approval_file, profile_hash=profile_hash,
                                      source_hashes_verified=verified_sources)
        output_root = _path_outside_repo(args.output_root, "private capture root")
        if output_root.exists() and (output_root.is_symlink() or not output_root.is_dir()):
            raise SafetyStop("private capture root must be a real directory")
        output_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if output_root.stat().st_mode & 0o777 != 0o700:
            raise SafetyStop("existing private capture root must already have mode 0700")
        capture_id = "CLARITY_RUNTIME_CAMPAIGN_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        output = output_root / capture_id
        output.mkdir(mode=0o700)
        _atomic_json(output / "campaign_state.json", {
            "campaign_id": "CL-HONDA-RUNTIME-DIAGNOSTIC-EXECUTION",
            "status": "initialized_before_adb_client_creation",
            "profile_sha256": profile_hash, "source_hashes": verified_sources,
            "phase_order": [], "completed_phases": [], "current_phase": None,
            "artifacts": []})
        reader = FixedAdb(serial, resolve_auto=False)
        capture = Capture(reader, output)
        return 0 if Campaign(capture, output, profile_hash, verified_sources, serial).run() else 1
    except (OSError, ValueError, SafetyStop) as exc:
        print(f"refusing/stopped: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
