"""Fixed-scope offline simulator and authorization-gated session controller.

The live backend is available only for an exact private, one-use owner scope
that passes current source pins, review artifacts, target checks, and readiness
prompts. It never discovers devices, accepts arbitrary commands, invokes root,
or activates HondaHack. A live session is not authorized by this source file.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import selectors
import secrets
import shutil
import subprocess
import stat
import sys
import time
from typing import Callable, Iterable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROPOSAL = ROOT / "docs/diagnostics/comprehensive-campaign-proposal.json"
SOURCE_LOCK = ROOT / "docs/diagnostics/comprehensive-source-lock.json"
EVIDENCE = ROOT / "docs/diagnostics/evidence-coverage.json"
STUDIO_READINESS = ROOT / "docs/development/cl-honda-comprehensive-readiness.json"
CAMPAIGN_ID = "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031"
PROPOSAL_LIVE_EXECUTION_ENABLED = False
MAX_TIMEOUT_SECONDS = 10
MAX_OUTPUT_BYTES = 900_000
MAX_SESSION_OUTPUT_BYTES = 158_400_512
SESSION_OUTPUT_HEADROOM_BYTES = 8 * 1024 * 1024
MIN_EVIDENCE_FREE_BYTES = MAX_SESSION_OUTPUT_BYTES + SESSION_OUTPUT_HEADROOM_BYTES
MAX_SESSION_COMMANDS = 162
MIN_COMMAND_OUTPUT_BUDGET_BYTES = 128
MAX_OWNER_PROMPT_SECONDS = 90
PRIVATE_LEDGER = Path(pwd.getpwuid(os.getuid()).pw_dir) / "Library/Application Support/ClarityLink/comprehensive-runtime/consumed"

COMMAND_FIELDS = {
    "phase0_baseline_safety_identity": "commands",
    "phase1_ordinary_adb_capability": "commands",
    "phase2_existing_root_supersu_review": "live_argv",
    "phase3_jmcs_maps_libraries_fd_socket_ownership": "live_argv",
    "phase4_three_state_carplay": "commands",
    "phase7_recovery_restoration": "commands",
}
PHASE_CATEGORIES = {
    "phase0_baseline_safety_identity": ("owner_baseline_observation",),
    "phase1_ordinary_adb_capability": ("ordinary_unprivileged_adb",),
    "phase2_existing_root_supersu_review": ("privileged_diagnostics",),
    "phase3_jmcs_maps_libraries_fd_socket_ownership": ("privileged_diagnostics",),
    "phase4_three_state_carplay": ("ordinary_unprivileged_adb", "stock_carplay_transition",
                                   "factory_navigation_observation"),
    "phase7_recovery_restoration": ("ordinary_unprivileged_adb",),
}
LIVE_PERMISSION_CATEGORIES = (
    "ordinary_unprivileged_adb", "stock_carplay_transition",
    "factory_navigation_observation", "privileged_diagnostics",
    "existing_hondahack_observation",
)
PHASE_RISK_LEVELS = {
    "phase0_baseline_safety_identity": 1,
    # This fixed identity subset reuses ordinary ADB reads already present in C-P.
    "phase1_ordinary_adb_capability": 1,
    "phase2_existing_root_supersu_review": 2,
    "phase3_jmcs_maps_libraries_fd_socket_ownership": 2,
    "phase4_three_state_carplay": 2,
    "phase7_recovery_restoration": 1,
}
PHASE_REVIEW_REQUIREMENTS = {
    "phase2_existing_root_supersu_review": ("technical",),
    "phase3_jmcs_maps_libraries_fd_socket_ownership": ("technical",),
    "phase4_three_state_carplay": ("technical", "qualified_vehicle_safety"),
}
BLOCKED_PHASES = {
    "phase2_existing_root_supersu_review",
    "phase3_jmcs_maps_libraries_fd_socket_ownership",
}
EXPECTED_TARGET_PROPERTIES = {
    "ro.build.version.release": "4.2.2",
    "ro.build.version.sdk": "17",
    "ro.product.device": "vcm30t30a",
    "ro.product.board": "Andromeda",
    "ro.hardware": "vcm30t30",
}
STATE_PROMPTS = {
    "disconnected_baseline": "Verify normal stock CarPlay is disconnected; no settings changes.",
    "stock_carplay_connected": "Connect stock CarPlay through its normal owner-operated flow and wait for the active steady state.",
    "disconnected_again": "Disconnect through the normal owner-operated flow.",
    "stock_carplay_reconnected": "Reconnect stock CarPlay through its normal owner-operated flow.",
    "final_disconnected": "Disconnect through the normal owner-operated flow.",
    "navigation_selected": "Use the normal factory control to select Navigation.",
    "navigation_deselected": "Use the normal factory control to deselect Navigation.",
    "navigation_reselected": "Use the normal factory control to reselect Navigation.",
    "navigation_selected_after_reconnect": "After CarPlay reconnects, use the normal factory control to select Navigation.",
    "navigation_deselected_after_reconnect": "After reconnect, use the normal factory control to deselect Navigation.",
    "factory_baseline_restored": "Restore the owner-defined factory UI baseline using normal controls.",
}
TRANSITION_ACTION_STATES = frozenset({
    "stock_carplay_connected", "disconnected_again", "stock_carplay_reconnected",
    "final_disconnected", "navigation_selected", "navigation_deselected",
    "navigation_reselected", "navigation_selected_after_reconnect",
    "navigation_deselected_after_reconnect",
})
POTENTIAL_OBJECTIVES = {
    "phase1_ordinary_adb_capability": ("ordinary-adb-identity",),
    "phase4_three_state_carplay": ("type110-session-lifecycle", "carplay-disconnect-reconnect-restoration",
                                    "usb0-network-phase-correlation", "carplay-info-setup-observability",
                                    "type111-negotiation-and-authority", "display-manager-inventory",
                                    "display1-window-view-lifecycle", "surfaceflinger-layer-lifecycle",
                                    "factory-navigation-transitions"),
    "phase7_recovery_restoration": ("recovery-prerequisites", "capture-integrity-and-privacy"),
}
MAX_SESSION_DURATION_SECONDS = 60 * 60
MAX_AUTHORIZATION_DURATION_SECONDS = 60 * 60


class ControllerError(RuntimeError):
    pass


@dataclass
class SessionOutputBudget:
    """Count exact persisted stdout/stderr bytes across every phase."""

    limit_bytes: int = MAX_SESSION_OUTPUT_BYTES
    used_bytes: int = 0
    exhausted: bool = False
    commands_started: int = 0

    def __post_init__(self) -> None:
        if (type(self.limit_bytes) is not int or self.limit_bytes <= 0
                or type(self.used_bytes) is not int or self.used_bytes < 0
                or self.used_bytes > self.limit_bytes
                or type(self.commands_started) is not int or self.commands_started < 0):
            raise ControllerError("session output budget initialization is invalid")

    @property
    def remaining_bytes(self) -> int:
        return self.limit_bytes - self.used_bytes

    def reserve(self, output_bytes: int) -> bool:
        if not isinstance(output_bytes, int) or output_bytes < 0:
            raise ControllerError("command output byte count is invalid")
        if self.exhausted or self.used_bytes >= self.limit_bytes or output_bytes > self.remaining_bytes:
            self.exhausted = True
            return False
        self.used_bytes += output_bytes
        return True

    def start_command(self) -> None:
        if self.commands_started >= MAX_SESSION_COMMANDS:
            self.exhausted = True
            raise ControllerError("fixed campaign command-count ceiling reached before next ADB command")
        self.commands_started += 1

    def report(self) -> dict[str, int | float | bool]:
        return {"limit_bytes": self.limit_bytes, "used_bytes": self.used_bytes,
                "remaining_bytes": self.remaining_bytes, "exhausted": self.exhausted,
                "commands_started": self.commands_started,
                "limit_decimal_mb": self.limit_bytes / 1_000_000,
                "limit_mib": self.limit_bytes / (1024 * 1024)}


@dataclass(frozen=True)
class Command:
    phase: str
    argv: tuple[str, ...]
    timeout_seconds: int
    max_output_bytes: int


@dataclass(frozen=True)
class RunBinding:
    campaign_id: str
    profile_sha256: str
    source_lock_sha256: str
    command_manifest_sha256: str
    source_file_count: int
    phases: tuple[str, ...]
    exact_vehicle: str


def immutable_run_binding() -> RunBinding:
    proposal = _proposal()
    values = pins()
    return RunBinding(CAMPAIGN_ID, values["profile_sha256"], values["source_lock_sha256"],
                      values["command_manifest_sha256"], int(values["source_file_count"]),
                      tuple(p["id"] for p in proposal["phases"]),
                      "2018 Honda Clarity PHEV Touring (MY16ADA; exact unit identity must be owner-verified)")


def validate_process_identity(before: dict, after: dict) -> None:
    """Reject PID reuse or any change to the fixed receiver identity tuple."""
    fields = ("pid", "start_time_ticks", "cmdline", "uid", "gid", "exe")
    if any(before.get(key) in (None, "") for key in fields):
        raise ControllerError("process identity snapshot is incomplete")
    if any(before.get(key) != after.get(key) for key in fields):
        raise ControllerError("jmcs PID/start-time/process identity changed during observation")
    if (not re.fullmatch(r"[1-9][0-9]*", str(before["pid"]))
            or not re.fullmatch(r"[0-9]+", str(before["start_time_ticks"]))
            or before["cmdline"] != "/system/bin/jmcs" or before["exe"] != "/system/bin/jmcs"
            or before["uid"] != "0" or before["gid"] != "0"):
        raise ControllerError("jmcs identity does not match the exact approved receiver")


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_proposal(value: dict) -> dict:
    if (value.get("campaign_id") != CAMPAIGN_ID or value.get("live_execution_enabled") is not False
            or value.get("live_authorization") != "NOT_AUTHORIZED"):
        raise ControllerError("comprehensive proposal identity or disabled-live gate changed")
    try:
        sys.path.insert(0, str(HERE))
        from validate_comprehensive_proposal import validate_proposal
        validate_proposal(value)
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        raise ControllerError("campaign proposal failed its fixed-scope validator") from exc
    finally:
        if sys.path and sys.path[0] == str(HERE):
            sys.path.pop(0)
    phases = value.get("phases")
    if not isinstance(phases, list) or tuple(p.get("id") for p in phases) != tuple(COMMAND_FIELDS):
        raise ControllerError("proposal must retain the six fixed ordinary-campaign phases in order")
    return value


def _proposal() -> dict:
    return _validate_proposal(_load_json(PROPOSAL))


def _load_bound_proposal(expected_sha256: str) -> tuple[bytes, dict]:
    """Read once, pin once, then use this immutable session snapshot."""
    raw = PROPOSAL.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ControllerError("campaign proposal changed after its approved source pin")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ControllerError("pinned campaign proposal could not be parsed") from exc
    return raw, _validate_proposal(value)


def _command_shapes(proposal: dict, serial: str) -> tuple[Command, ...]:
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", serial) or serial == "auto":
        raise ControllerError("dry-run needs a syntactically valid exact serial placeholder")
    try:
        sys.path.insert(0, str(HERE))
        from collector import FixedAdb
    finally:
        if sys.path and sys.path[0] == str(HERE):
            sys.path.pop(0)
    result = []
    for phase in proposal["phases"]:
        field = COMMAND_FIELDS[phase["id"]]
        commands = phase[field]
        if not isinstance(commands, list):
            raise ControllerError(f"{phase['id']} command list is malformed")
        for row in commands:
            if not isinstance(row, list) or len(row) < 5:
                raise ControllerError(f"{phase['id']} has a malformed fixed argv row")
            argv = list(row)
            if argv[:4] != ["adb", "-s", "<private-approved-serial>", "shell"]:
                raise ControllerError("command argv is outside the fixed legacy ADB shell form")
            argv[2] = serial
            argv = [x.replace("<verified-jmcs-pid>", "1234") for x in argv]
            timeout = phase.get("per_command_timeout_seconds")
            maximum = phase.get("per_command_output_limit_bytes")
            if (not isinstance(timeout, int) or not 0 < timeout <= MAX_TIMEOUT_SECONDS
                    or not isinstance(maximum, int) or not 0 < maximum <= MAX_OUTPUT_BYTES):
                raise ControllerError("command timeout or output ceiling is outside reviewed bounds")
            _validate_fixed_argv(tuple(argv), FixedAdb)
            result.append(Command(phase["id"], tuple(argv), timeout, maximum))
    if len(result) != 45:
        raise ControllerError(f"expected 45 reviewed fixed command shapes, found {len(result)}")
    return tuple(result)


def _validate_fixed_argv(argv: tuple[str, ...], fixed_adb) -> None:
    """Round-trip each proposal argv through the existing fixed-operation planner."""
    remote = argv[4:]
    # This single read-only sysfs datum exists in the comprehensive proposal
    # but was not part of the historical C-P collector surface.
    if remote == ("cat", "/sys/class/net/usb0/operstate"):
        if argv != ("adb", "-s", argv[2], "shell", "cat", "/sys/class/net/usb0/operstate"):
            raise ControllerError("usb0 state read differs from the exact fixed argv")
        return
    mapping = {
        ("id",): ("id", ()), ("ps",): ("ps", ()),
        ("service", "list"): ("service-list", ()),
        ("dumpsys", "display"): ("dumpsys", ("display",)),
        ("dumpsys", "SurfaceFlinger"): ("dumpsys", ("SurfaceFlinger",)),
        ("dumpsys", "window"): ("dumpsys", ("window",)),
        ("logcat", "-d", "-t", "500"): ("logcat", ()),
    }
    if len(remote) == 3 and remote[:2] == ("dumpsys", "activity"):
        op = ("dumpsys", remote[1:])
    elif len(remote) == 3 and remote[:2] == ("dumpsys", "package"):
        op = ("dumpsys", remote[1:])
    elif len(remote) == 3 and remote[:2] == ("pm", "path"):
        op = ("package-path", (remote[2],))
    elif len(remote) == 2 and remote[0] == "getprop":
        op = ("property", (remote[1],))
    elif len(remote) == 2 and remote[0] == "cat":
        op = ("read", (remote[1],))
    elif len(remote) == 3 and remote[:2] == ("ls", "-l"):
        op = ("readlink", (remote[2],))
    elif remote == ("ls", "/sys/class/graphics"):
        op = ("list", (remote[1],))
    else:
        op = mapping.get(remote)
    if op is None:
        raise ControllerError(f"unsupported proposal command shape: {remote!r}")
    try:
        planned = fixed_adb.plan_without_adb_lookup(argv[2], op[0], op[1])
    except (ValueError, RuntimeError) as exc:
        raise ControllerError("fixed operation planner rejected proposal argv") from exc
    if planned != argv:
        raise ControllerError(f"proposal argv does not match API-17 fixed planner: {remote!r}")


def pins() -> dict[str, str]:
    lock = _load_json(SOURCE_LOCK)
    profile_hash = hashlib.sha256(PROPOSAL.read_bytes()).hexdigest()
    if lock.get("profile", {}).get("sha256") != profile_hash:
        raise ControllerError("comprehensive profile pin does not match proposal")
    sources = lock.get("sources")
    if not isinstance(sources, dict):
        raise ControllerError("source lock is malformed")
    checked = {}
    for relative, expected in sources.items():
        path = ROOT / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ControllerError(f"source lock mismatch: {relative}")
        checked[relative] = actual
    manifest_hash = hashlib.sha256(json.dumps(
                [[c.phase, c.argv, c.timeout_seconds, c.max_output_bytes]
                 for c in _command_shapes(_proposal(), "EXACT_APPROVED_SERIAL")],
                sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if lock.get("command_manifest_sha256") != manifest_hash:
        raise ControllerError("command manifest pin does not match executable fixed argv")
    return {"profile_sha256": profile_hash, "source_lock_sha256": hashlib.sha256(SOURCE_LOCK.read_bytes()).hexdigest(),
            "command_manifest_sha256": manifest_hash,
            "source_file_count": str(len(checked))}


def dry_run_report(*, serial: str = "EXACT_APPROVED_SERIAL") -> dict:
    proposal = _proposal()
    fixed = _command_shapes(proposal, serial)
    grouped = {phase["id"]: [] for phase in proposal["phases"]}
    for command in fixed:
        grouped[command.phase].append({"argv": list(command.argv), "timeout_seconds": command.timeout_seconds,
                                       "max_output_bytes": command.max_output_bytes})
    phase_rows = []
    for phase in proposal["phases"]:
        key = phase["id"]
        phase_rows.append({
            "id": key, "category": phase["category"],
            "required_categories": list(PHASE_CATEGORIES[key]),
            "authorization_status": phase["authorization_status"],
            "owner_actions": phase.get("owner_actions", []),
            "offline_actions": phase.get("offline_actions", []),
            "required_evidence_to_reconsider": phase.get("required_evidence_to_reconsider", []),
            "required_observations_if_reconsidered": phase.get("required_observations_if_reconsidered", []),
            "states": phase.get("states", []),
            "owner_checks": phase.get("owner_checks", []),
            "host_checks": phase.get("host_checks", []),
            "baseline_inventory": phase.get("baseline_inventory"),
            "comparative_purpose": phase.get("comparative_purpose"),
            "activity_manager_scope": phase.get("activity_manager_scope"),
            "network_scope": phase.get("network_scope"),
            "owner_confirmation_rule": phase.get("owner_confirmation_rule"),
            "stop_conditions": phase.get("stop", ""),
            "commands": grouped[key],
            "commands_per_state": len(grouped[key]) if phase.get("states") else 0,
            "blocked": key in BLOCKED_PHASES or phase["authorization_status"] != "AUTHORIZED",
            "failure_policy": "abort phase and campaign; no retry or next phase",
        })
    execution_bounds = proposal["execution_bounds_proposal"]
    campaign_command_count = sum(
        len(phase.get("commands", phase.get("live_argv", []))) *
        (len(phase.get("states", [])) if phase["id"] == "phase4_three_state_carplay" else 1)
        for phase in proposal["phases"]
    )
    capture_schedule = []
    for phase in proposal["phases"]:
        phase_id = phase["id"]
        commands = grouped[phase_id]
        if phase.get("states"):
            for state in phase["states"]:
                capture_schedule.append({"phase": phase_id, "state": state,
                                         "owner_confirmation_required": True,
                                         "commands": commands})
        elif commands:
            state = "factory_restoration" if phase_id == "phase7_recovery_restoration" else "disconnected_baseline"
            capture_schedule.append({"phase": phase_id, "state": state,
                                     "owner_confirmation_required": True,
                                     "commands": commands})
    studio = _load_json(STUDIO_READINESS)
    if (studio.get("schema") != "claritylink-experiment-readiness-v2"
            or studio.get("campaign_id") != CAMPAIGN_ID
            or studio.get("run_experiment", {}).get("enabled") is not False
            or studio.get("results", {}).get("campaign_success") is not False):
        raise ControllerError("Studio readiness must remain explicit and fail closed")
    return {"campaign_id": CAMPAIGN_ID, "mode": "SIMULATED_DRY_RUN_NO_DEVICE_ACCESS",
            "live_execution_enabled": PROPOSAL_LIVE_EXECUTION_ENABLED,
            "live_backend": "AUTHORIZATION_GATED_PRIVATE_SESSION_ONLY",
            "phases": phase_rows,
            "phase_count": len(phase_rows), "command_shapes": len(fixed),
            "campaign_command_count": campaign_command_count,
            "session_limits": {
                "command_timeout_seconds": execution_bounds["max_command_timeout_seconds"],
                "per_command_output_bytes": execution_bounds["max_command_output_bytes"],
                "per_command_output_unit": "bytes, combined stdout plus stderr including collector failure marker",
                "session_output_bytes": execution_bounds["max_session_output_bytes"],
                "session_output_decimal_mb": execution_bounds["max_session_output_bytes"] / 1_000_000,
                "session_output_mib": execution_bounds["max_session_output_bytes"] / (1024 * 1024),
                "minimum_free_evidence_bytes": execution_bounds["minimum_private_evidence_free_bytes"],
                "max_command_time_sum_seconds": execution_bounds["max_command_time_sum_seconds"],
                "max_owner_prompt_time_sum_seconds": execution_bounds["max_owner_prompt_time_sum_seconds"],
                "bounded_elapsed_seconds": execution_bounds["max_bounded_elapsed_seconds"],
                "deadline_seconds": execution_bounds["max_total_elapsed_seconds"],
            },
            "capture_schedule": capture_schedule,
            "adb_executable_lookup": False, "device_enumeration": False,
            "subprocess_calls": 0, "capture_files_created": False,
            "pins": pins(), "coverage_required": len(_load_json(EVIDENCE)["objectives"]),
            "studio_readiness": studio,
            "completion": "SIMULATION_COMPLETE_NOT_LIVE_EVIDENCE"}


def simulate(*, notify: Callable[[str], None] | None = None) -> dict:
    """Run phase gates and outcome handling entirely in memory."""
    report = dry_run_report()
    events = []
    for phase in report["phases"]:
        events.append({"phase": phase["id"], "status": "BLOCKED_OR_UNAUTHORIZED" if phase["blocked"] else "SIMULATED"})
    terminal = "SIMULATED CAMPAIGN COMPLETE — NO DEVICE ACCESS; NO LIVE EVIDENCE"
    notification = "NOT_SENT_IN_SIMULATION"
    if notify is not None:
        try:
            notify(terminal)
            notification = "DELIVERED_BY_INJECTED_SIMULATOR"
        except Exception:
            notification = "FAILED; terminal output remains authoritative"
    return {"events": events, "terminal": terminal, "notification": notification,
            "live_evidence": False, "campaign_success": False}


def simulate_fault(fault: str) -> dict:
    """Exercise fail-closed terminal states without a device or subprocess."""
    known = {"interruption", "permission_denied", "root_unavailable", "pid_reuse",
             "command_failure", "unexpected_factory_observation", "incomplete_evidence"}
    if fault not in known:
        raise ControllerError("unknown simulated fault")
    outcomes = {
        "interruption": ("ABORTED_HOST_ONLY", "do not resume or contact the vehicle"),
        "permission_denied": ("ABORTED", "no fallback or privilege escalation"),
        "root_unavailable": ("PHASE2_BLOCKED", "Phase 3 remains blocked; no su attempt"),
        "pid_reuse": ("ABORTED", "PID/start-time mismatch; issue no next command"),
        "command_failure": ("ABORTED", "no retry, substitution, or next phase"),
        "unexpected_factory_observation": ("ABORTED", "stop and follow only reviewed factory recovery"),
        "incomplete_evidence": ("INCOMPLETE", "campaign_success remains false"),
    }
    status, action = outcomes[fault]
    return {"fault": fault, "status": status, "required_action": action,
            "live_evidence": False, "campaign_success": False,
            "host_cleanup_only": fault in {"interruption", "command_failure"}}


def notify_terminal(status: str, *, run=subprocess.run) -> str:
    """Send a fixed, non-sensitive macOS notification; terminal output is primary."""
    messages = {
        "complete": "ClarityLink session ended; normal vehicle power-off was confirmed. Review private evidence offline.",
        "stopped": "ClarityLink session stopped. Preserve the private partial record. If a transition occurred, restore the factory baseline with normal controls and verify displays, cluster, Navigation, audio, and warnings. Power-off was not confirmed; do not retry.",
        "archive_failure_complete": "ClarityLink session ended and normal power-off was confirmed, but private evidence finalization failed. Preserve the private folder and inspect it offline; do not repeat the session.",
        "archive_failure_stopped": "ClarityLink session stopped and private evidence finalization failed. Preserve the partial folder. If a transition occurred, restore with normal controls; do not retry.",
    }
    message = messages.get(status)
    if message is None:
        return "NOT_SENT_INVALID_STATUS"
    try:
        result = run(["/usr/bin/osascript", "-e",
                      f'display notification "{message}" with title "ClarityLink"'],
                     capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return "FAILED; terminal output remains authoritative"
    return ("DELIVERED" if result.returncode == 0
            else "FAILED; terminal output remains authoritative")


def validate_session_authorization(record: dict, *, current_pins: dict[str, str]) -> None:
    """Validate one owner decision for an explicit compatible phase group."""
    phases = record.get("approved_phases")
    if (not isinstance(phases, list) or not phases
            or any(not isinstance(p, str) or p not in PHASE_CATEGORIES for p in phases)
            or len(set(phases)) != len(phases)):
        raise ControllerError("approval must name a nonempty set of known experiment phases")
    order = {phase: index for index, phase in enumerate(COMMAND_FIELDS)}
    if phases != sorted(phases, key=order.__getitem__):
        raise ControllerError("approved phases must follow the fixed campaign order")
    if any(p in BLOCKED_PHASES for p in phases):
        raise ControllerError("selected phase has no currently justified access method")
    transition_phases = {"phase4_three_state_carplay"}
    if transition_phases.intersection(phases):
        baseline = record.get("factory_restoration_reference")
        if not isinstance(baseline, str) or not baseline.strip():
            raise ControllerError("factory transition scope lacks its owner-defined restoration baseline")
    if record.get("campaign_id") != CAMPAIGN_ID:
        raise ControllerError("approval does not bind this campaign")
    if record.get("live_execution_enabled") is not True:
        raise ControllerError("this one-run owner record does not authorize live execution")
    if record.get("pins") != current_pins:
        raise ControllerError("approval source/profile/manifest pins are stale")
    required_categories = set().union(*(set(PHASE_CATEGORIES[p]) for p in phases))
    allowed = record.get("approved_categories")
    if (not isinstance(allowed, list) or not all(isinstance(item, str) for item in allowed)
            or len(allowed) != len(set(allowed))
            or set(allowed) != required_categories):
        raise ControllerError("one session approval must enumerate exactly its phase category set")
    category_permissions = record.get("category_permissions")
    if (not isinstance(category_permissions, dict)
            or set(category_permissions) != set(LIVE_PERMISSION_CATEGORIES)
            or any(not isinstance(value, bool) for value in category_permissions.values())):
        raise ControllerError("session must answer each separate live-category permission check")
    expected_live_permissions = required_categories.intersection(LIVE_PERMISSION_CATEGORIES)
    if any(category_permissions[key] != (key in expected_live_permissions)
           for key in LIVE_PERMISSION_CATEGORIES):
        raise ControllerError("live-category permissions must match only the selected approved phases")
    if record.get("owner_confirmed") is not True or record.get("readiness_answer") != "YES":
        raise ControllerError("one affirmative owner session decision is required")
    readiness = record.get("readiness_checks")
    requires_adb = any("ordinary_unprivileged_adb" in PHASE_CATEGORIES[p] for p in phases)
    required_readiness = {"stationary_in_park", "parking_brake_set", "owner_present",
                          "approved_power_state", "no_abnormal_warning", "factory_displays_normal"}
    if requires_adb:
        required_readiness.add("adb_transport_independent")
    if not isinstance(readiness, dict) or any(readiness.get(k) is not True for k in required_readiness):
        raise ControllerError("session readiness checks are incomplete")
    if requires_adb:
        transport_details = record.get("adb_transport_details")
        if (not isinstance(transport_details, str) or not transport_details.strip()
                or len(transport_details) > 512 or any(char in transport_details for char in "\r\n\0")):
            raise ControllerError("ADB session must privately describe the exact transport and its independence from the CarPlay path")
    destination = record.get("evidence_destination_checklist")
    required_destination_checks = {
        "host_local_outside_repository", "directory_owner_only", "files_owner_only",
        "cloud_sync_disabled", "hash_inventory_ready",
    }
    if (not isinstance(destination, dict)
            or any(destination.get(k) is not True for k in required_destination_checks)):
        raise ControllerError("private evidence destination checklist is incomplete")
    if record.get("recovery_prerequisites_confirmed") is not True:
        raise ControllerError("approved restoration prerequisites are not confirmed")
    if (not isinstance(record.get("owner_question"), str) or not record["owner_question"].strip()
            or not isinstance(record.get("expected_evidence"), str) or not record["expected_evidence"].strip()
            or not isinstance(record.get("known_risks"), list) or not record["known_risks"]
            or not all(isinstance(item, str) and item.strip() for item in record["known_risks"])
            or not isinstance(record.get("stop_conditions"), list) or not record["stop_conditions"]):
        raise ControllerError("session must state its evidence question, expected observation, known risks, and stop conditions")
    evidence_directory = record.get("evidence_directory")
    if not isinstance(evidence_directory, str) or not Path(evidence_directory).is_absolute():
        raise ControllerError("session must bind an absolute private evidence directory")
    if not isinstance(record.get("exact_vehicle_identity_confirmed"), bool) or not record["exact_vehicle_identity_confirmed"]:
        raise ControllerError("the owner must bind this session to the exact physical vehicle")
    identity_reference = record.get("owner_verified_vehicle_reference")
    if not isinstance(identity_reference, str) or not identity_reference.strip():
        raise ControllerError("the private approval must reference the owner's exact vehicle identity record")
    expected_risk = max(PHASE_RISK_LEVELS[p] for p in phases)
    if record.get("risk_level") != f"LEVEL_{expected_risk}":
        raise ControllerError("approval risk level does not match the selected scope")
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9-]{7,63}", str(record.get("authorization_id", ""))):
        raise ControllerError("approval identifier is invalid")
    if not re.fullmatch(r"[0-9a-f]{32}", str(record.get("nonce", ""))):
        raise ControllerError("approval nonce is invalid")
    if not re.fullmatch(r"[0-9a-f]{32}", str(record.get("run_id", ""))):
        raise ControllerError("run identifier is invalid")
    try:
        issued = datetime.fromisoformat(str(record["issued_at_utc"]).replace("Z", "+00:00"))
        expires = datetime.fromisoformat(str(record["expires_at_utc"]).replace("Z", "+00:00"))
    except (KeyError, ValueError) as exc:
        raise ControllerError("approval issue/expiry timestamps are invalid") from exc
    now = datetime.now(timezone.utc)
    if (issued.tzinfo is None or expires.tzinfo is None or issued > now + timedelta(minutes=1)
            or expires <= now or expires <= issued
            or expires - issued > timedelta(seconds=MAX_AUTHORIZATION_DURATION_SECONDS)):
        raise ControllerError("approval is expired or outside the one-hour authorization window")
    if record.get("exact_vehicle") != "2018 Honda Clarity PHEV Touring (MY16ADA; exact unit identity must be owner-verified)":
        raise ControllerError("approval vehicle identity is not the exact reviewed target")
    if any("ordinary_unprivileged_adb" in PHASE_CATEGORIES[p] for p in phases):
        serial = record.get("exact_adb_serial")
        if not isinstance(serial, str) or serial == "auto" or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", serial):
            raise ControllerError("ADB phase approval must bind one exact private serial")
    required_reviews = set().union(*(set(PHASE_REVIEW_REQUIREMENTS.get(p, ())) for p in phases))
    declared_reviews = record.get("required_review_types")
    if declared_reviews != sorted(required_reviews):
        raise ControllerError("session review requirements differ from the fixed phase risk policy")
    reviews = record.get("review_artifacts")
    if not isinstance(reviews, dict) or not required_reviews.issubset(reviews):
        raise ControllerError("required exact-source independent review artifacts are missing")
    review_paths = record.get("review_artifact_paths", {})
    if not isinstance(review_paths, dict) or not required_reviews.issubset(review_paths):
        raise ControllerError("required private review artifact paths are missing")
    if required_reviews and not re.fullmatch(r"[0-9a-f]{40}", str(record.get("reviewed_commit_sha", ""))):
        raise ControllerError("reviewed candidate commit pin is missing")
    if "technical" in required_reviews and record.get("technical_reviewer_independence_verified") is not True:
        raise ControllerError("owner has not verified the external technical reviewer and exact-source review")
    if ("qualified_vehicle_safety" in required_reviews
            and record.get("qualified_safety_reviewer_credentials_verified") is not True):
        raise ControllerError("qualified safety reviewer credentials are not independently verified")
    for review in required_reviews:
        digest = reviews[review]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ControllerError("required review artifact digest is invalid")
        path = review_paths[review]
        if not isinstance(path, str) or not Path(path).is_absolute():
            raise ControllerError("required private review artifact path is invalid")


def validate_authorization(record: dict, *, requested_phase: str, current_pins: dict[str, str]) -> None:
    """Compatibility helper for validating a one-phase session scope."""
    single = dict(record)
    if "approved_phases" in single and single["approved_phases"] != [requested_phase]:
        raise ControllerError("requested phase differs from the one-phase authorization")
    single["approved_phases"] = [requested_phase]
    validate_session_authorization(single, current_pins=current_pins)


def new_run_identifiers() -> dict[str, str]:
    """Create fresh one-run values; callers must keep them in private approval storage."""
    issued = datetime.now(timezone.utc)
    expires = issued + timedelta(seconds=MAX_AUTHORIZATION_DURATION_SECONDS)
    return {"run_id": secrets.token_hex(16), "nonce": secrets.token_hex(16),
            "issued_at_utc": issued.isoformat().replace("+00:00", "Z"),
            "expires_at_utc": expires.isoformat().replace("+00:00", "Z")}


def authorize_one_run(record: dict, *, current_pins: dict[str, str], ledger: Path | None = None) -> Path:
    """Validate one session decision, then durably consume it once."""
    validate_session_authorization(record, current_pins=current_pins)
    return consume_once(record, ledger=ledger)


def consume_once(record: dict, *, ledger: Path | None = None) -> Path:
    """Atomically reserve a single authorization ID in a private host ledger."""
    approval_id = record.get("authorization_id")
    if not isinstance(approval_id, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9-]{7,63}", approval_id):
        raise ControllerError("invalid one-run authorization ID")
    run_id, nonce = record.get("run_id"), record.get("nonce")
    if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise ControllerError("invalid one-run ID")
    if not isinstance(nonce, str) or not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise ControllerError("invalid one-use nonce")
    try:
        user_home = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=True)
    except (KeyError, OSError) as exc:
        raise ControllerError("cannot resolve owner home for private authorization ledger") from exc
    requested = (PRIVATE_LEDGER if ledger is None else ledger).expanduser()
    chain = [requested, *requested.parents]
    if any(part.is_symlink() for part in chain if part.exists()):
        raise ControllerError("authorization ledger path cannot contain symlinks")
    if ledger is None and not requested.resolve(strict=False).is_relative_to(user_home):
        raise ControllerError("authorization ledger must stay under the owner home")
    ledger = requested
    ledger.mkdir(parents=True, mode=0o700, exist_ok=True)
    if ledger.stat().st_mode & 0o077:
        raise ControllerError("authorization ledger directory is not private")
    os.chmod(ledger, 0o700)
    nonce_digest = hashlib.sha256(nonce.encode()).hexdigest()
    targets = (ledger / f"authorization-{approval_id}.json", ledger / f"nonce-{nonce_digest}.json")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    payload = json.dumps({"authorization_id": approval_id, "run_id": run_id,
                          "nonce_sha256": nonce_digest}, sort_keys=True).encode() + b"\n"
    try:
        for target in targets:
            try:
                fd = os.open(target, flags, 0o600)
            except FileExistsError as exc:
                raise ControllerError("authorization ID or nonce has already been consumed") from exc
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
    except Exception:
        # Any created marker remains consumed after partial failure.
        raise
    directory_fd = os.open(ledger, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    return targets[0]


def _load_private_authorization(path: Path) -> dict:
    if (path.is_symlink() or not path.is_file() or path.stat().st_size > 128 * 1024
            or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077):
        raise ControllerError("authorization must be a bounded owner-only private file")
    resolved = path.resolve(strict=True)
    if ROOT.resolve() == resolved or ROOT.resolve() in resolved.parents:
        raise ControllerError("authorization file must stay outside the repository")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(resolved, flags)
        with os.fdopen(fd, "rb") as handle:
            metadata = os.fstat(handle.fileno())
            if (metadata.st_uid != os.getuid() or metadata.st_size > 128 * 1024
                    or stat.S_IMODE(metadata.st_mode) & 0o077):
                raise ControllerError("authorization changed or is no longer owner-only")
            value = json.loads(handle.read().decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ControllerError("authorization file could not be parsed") from exc
    if not isinstance(value, dict):
        raise ControllerError("authorization file must contain one session object")
    return value


def _private_evidence_directory(record: dict) -> Path:
    requested = Path(record["evidence_directory"]).expanduser()
    if requested.is_symlink() or not requested.exists() or not requested.is_dir():
        raise ControllerError("owner must prepare the private evidence directory before the session")
    resolved = requested.resolve(strict=True)
    if ROOT.resolve() == resolved or ROOT.resolve() in resolved.parents:
        raise ControllerError("private evidence directory must be outside the repository")
    try:
        fd = os.open(resolved, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                     | getattr(os, "O_NOFOLLOW", 0))
        try:
            metadata = os.fstat(fd)
        finally:
            os.close(fd)
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
            raise ControllerError("private evidence directory must be owner-owned with mode 0700")
        if shutil.disk_usage(resolved).free < MIN_EVIDENCE_FREE_BYTES:
            raise ControllerError(
                f"private evidence volume needs at least {MIN_EVIDENCE_FREE_BYTES} free bytes "
                "for the bounded archive and integrity metadata"
            )
    except OSError as exc:
        raise ControllerError("private evidence directory changed or cannot be opened safely") from exc
    return resolved


def _write_private_file(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise ControllerError("private evidence file could not be created without overwrite") from exc
    written = 0
    try:
        with os.fdopen(fd, "wb", buffering=0) as output:
            os.fchmod(output.fileno(), 0o600)
            view = memoryview(payload)
            while written < len(payload):
                count = output.write(view[written:])
                if count is None or count <= 0:
                    raise OSError("private evidence write made no progress")
                written += count
            os.fsync(output.fileno())
    except BaseException:
        # A partial command artifact must never look complete in the archive.
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _replace_private_file(path: Path, payload: bytes) -> None:
    if path.is_symlink() or not path.is_file():
        raise ControllerError("private summary replacement target is missing or symbolic")
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise ControllerError("private summary replacement target is not owner-only")
    flags = os.O_WRONLY | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "wb") as output:
        os.fchmod(output.fileno(), 0o600)
        output.write(payload)
        output.flush()
        os.fsync(output.fileno())


def _write_sha256_inventory(directory: Path) -> str:
    rows = []
    for path in sorted(p for p in directory.rglob("*") if p.is_file() and p.name != "sha256.txt"):
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise ControllerError("private archive contains a non-private or symbolic-link artifact")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(f"{digest}  {path.relative_to(directory).as_posix()}")
    payload = ("\n".join(rows) + "\n").encode()
    _write_private_file(directory / "sha256.txt", payload)
    return hashlib.sha256(payload).hexdigest()


def _candidate_commit() -> str:
    try:
        status = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                                capture_output=True, text=True, timeout=5, check=False)
        if status.returncode != 0 or status.stdout.strip():
            raise ControllerError("live execution requires the exact reviewed source in a clean worktree")
        result = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ControllerError("cannot verify candidate commit for independent review") from exc
    commit = result.stdout.strip()
    if result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ControllerError("candidate commit identity is unavailable")
    return commit


def _validate_live_reviews(record: dict, current_pins: dict[str, str]) -> None:
    required = set().union(*(set(PHASE_REVIEW_REQUIREMENTS.get(p, ()))
                             for p in record["approved_phases"]))
    if not required:
        return
    if record.get("reviewed_commit_sha") != _candidate_commit():
        raise ControllerError("independent review does not bind the exact candidate commit")
    try:
        sys.path.insert(0, str(HERE))
        from validate_review_artifacts import validate_review_artifact
    finally:
        if sys.path and sys.path[0] == str(HERE):
            sys.path.pop(0)
    for review in required:
        try:
            validated = validate_review_artifact(
                Path(record["review_artifact_paths"][review]), review_type=review,
                pins={"profile_sha256": current_pins["profile_sha256"],
                      "source_lock_sha256": current_pins["source_lock_sha256"],
                      "manifest_sha256": current_pins["command_manifest_sha256"]},
                commit_sha=record["reviewed_commit_sha"],
                approved_phases=record["approved_phases"], risk_level=record["risk_level"],
            )
        except (OSError, ValueError, KeyError) as exc:
            raise ControllerError(f"required {review} review artifact is invalid") from exc
        if validated["decision"] != "APPROVE_ENGINEERING" or validated["artifact_sha256"] != record["review_artifacts"][review]:
            raise ControllerError(f"required {review} review did not approve this exact source")


def _operation_for(argv: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    remote = argv[4:]
    if remote == ("id",):
        return "id", ()
    if remote == ("ps",):
        return "ps", ()
    if remote == ("service", "list"):
        return "service-list", ()
    if len(remote) == 2 and remote[0] == "cat":
        if remote == ("cat", "/sys/class/net/usb0/operstate"):
            return "read_net_operstate", (remote[1],)
        return "read", (remote[1],)
    if len(remote) == 3 and remote[:2] == ("ls", "-l"):
        return "readlink", (remote[2],)
    if remote == ("ls", "/sys/class/graphics"):
        return "list", (remote[1],)
    if len(remote) == 2 and remote[0] == "getprop":
        return "property", (remote[1],)
    if len(remote) == 2 and remote[0] == "dumpsys":
        return "dumpsys", (remote[1],)
    if len(remote) == 3 and remote[:2] == ("dumpsys", "activity"):
        return "dumpsys", remote[1:]
    if len(remote) == 3 and remote[:2] == ("dumpsys", "package"):
        return "dumpsys", remote[1:]
    if len(remote) == 3 and remote[:2] == ("pm", "path"):
        return "package-path", (remote[2],)
    if remote == ("logcat", "-d", "-t", "500"):
        return "logcat", ()
    raise ControllerError("operation is outside the fixed API-17 planner")


def _phase_rows(phase: dict) -> list[list[str]]:
    field = COMMAND_FIELDS[phase["id"]]
    rows = phase.get(field)
    if not isinstance(rows, list):
        raise ControllerError("approved phase command list is malformed")
    return rows


def _fixed_adb_executor(reader, serial: str) -> Callable[[Command], tuple[int, bytes, bytes]]:
    """Bind runtime calls to the exact plan produced by FixedAdb."""
    def execute(command: Command) -> tuple[int, bytes, bytes]:
        operation, args = _operation_for(command.argv)
        if operation == "read_net_operstate":
            planned = (reader.adb, "-s", serial, "shell", "cat", "/sys/class/net/usb0/operstate")
            if planned[1:] != command.argv[1:]:
                raise ControllerError("usb0 read differs from its fixed runtime argv")
            return reader._run_planned(planned, "read", args,
                                       timeout=command.timeout_seconds,
                                       max_bytes=command.max_output_bytes)
        planned = reader.plan(operation, args)
        if planned[1:] != command.argv[1:]:
            raise ControllerError("runtime fixed-operation planner differs from approved argv")
        return reader._run_planned(planned, operation, args,
                                   timeout=command.timeout_seconds,
                                   max_bytes=command.max_output_bytes)
    return execute


def _snapshot_from(raw: dict[str, bytes]) -> dict[str, str] | None:
    if set(raw) != {"stat", "cmdline", "status", "exe"}:
        return None
    try:
        sys.path.insert(0, str(HERE))
        from collector import parse_ls_symlink_target
        from parsers import parse_proc_stat_start_time, parse_status
        start = parse_proc_stat_start_time(raw["stat"].decode("utf-8", "replace"))
        status = parse_status(raw["status"].decode("utf-8", "replace"))
    finally:
        if sys.path and sys.path[0] == str(HERE):
            sys.path.pop(0)
    uid = status.get("Uid", "").split()
    gid = status.get("Gid", "").split()
    cmdline = raw["cmdline"].replace(b"\x00", b" ").decode("utf-8", "replace").strip()
    exe = parse_ls_symlink_target(raw["exe"])
    if not uid or not gid or not cmdline or not exe:
        raise ControllerError("jmcs process identity output is incomplete")
    return {"pid": "", "start_time_ticks": str(start), "cmdline": cmdline,
            "uid": uid[0], "gid": gid[0], "exe": exe}


def _ask_owner(prompt: Callable[[str], str] | None, message: str) -> str:
    """Read one bounded owner response; injectable prompts are test-only seams."""
    if prompt is not None:
        return prompt(message)
    if not sys.stdin.isatty():
        raise ControllerError("owner prompts require an interactive terminal")
    output = sys.stdout
    output.write(message)
    output.flush()
    selector = selectors.DefaultSelector()
    try:
        selector.register(sys.stdin, selectors.EVENT_READ)
        if not selector.select(MAX_OWNER_PROMPT_SECONDS):
            raise ControllerError("owner readiness prompt timed out; session aborted")
        return sys.stdin.readline().rstrip("\r\n")
    finally:
        selector.close()


def _owner_checkpoint(prompt: Callable[[str], str] | None, message: str, *,
                      output: Callable[[str], None], deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise ControllerError("one-hour session bound reached before owner checkpoint")
    output(message)
    answer = _ask_owner(prompt, "When the named state is stable and normal, enter READY. Enter STOP to abort: ").strip()
    if time.monotonic() >= deadline:
        raise ControllerError("one-hour session bound reached during owner checkpoint")
    if answer != "READY":
        raise ControllerError("owner stopped or did not confirm the approved stable state")


def _save_command_result(run_dir: Path, command: Command, index: int,
                         exit_code: int, stdout: bytes, stderr: bytes, *,
                         state: str, operation: str, arguments: tuple[str, ...],
                         started_at_utc: str, started_monotonic_ns: int,
                         finished_at_utc: str, finished_monotonic_ns: int,
                         result_status: str) -> dict:
    stem = f"{command.phase}-{index:03d}"
    stdout_path = run_dir / f"{stem}.stdout.bin"
    stderr_path = run_dir / f"{stem}.stderr.bin"
    try:
        _write_private_file(stdout_path, stdout)
        _write_private_file(stderr_path, stderr)
    except BaseException:
        for path in (stdout_path, stderr_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    return {"phase": command.phase, "state": state, "index": index,
            "operation": operation, "arguments": list(arguments), "argv": list(command.argv),
            "started_at_utc": started_at_utc, "started_monotonic_ns": started_monotonic_ns,
            "finished_at_utc": finished_at_utc, "finished_monotonic_ns": finished_monotonic_ns,
            "result_status": result_status, "exit_code": exit_code,
            "timeout_seconds": command.timeout_seconds,
            "max_output_bytes": command.max_output_bytes,
            "stdout_file": f"{stem}.stdout.bin",
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_file": f"{stem}.stderr.bin",
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "stdout_bytes": len(stdout), "stderr_bytes": len(stderr)}


def _execute_batch(*, phase_id: str, state: str, rows: list[list[str]], serial: str,
                   proposal_snapshot: dict,
                   execute_command: Callable[[Command], tuple[int, bytes, bytes]],
                   run_dir: Path, records: list[dict], index: int,
                   prior_identity: dict[str, str] | None,
                   authorization_record: dict, current_pins: dict[str, str],
                   session_deadline: float, output_budget: SessionOutputBudget,
                   output: Callable[[str], None]) -> tuple[int, dict[str, str] | None]:
    try:
        sys.path.insert(0, str(HERE))
        from collector import FixedAdb, parse_ps_jmcs, validate_legacy_shell_output
    finally:
        if sys.path and sys.path[0] == str(HERE):
            sys.path.pop(0)
    pid = prior_identity["pid"] if prior_identity else None
    identity_fields = {"pid", "start_time_ticks", "cmdline", "uid", "gid", "exe"}
    expected_identity = prior_identity if prior_identity and identity_fields.issubset(prior_identity) else None
    current_snapshot: dict[str, bytes] = {}
    snapshots_seen = 0
    for row in rows:
        validate_session_authorization(authorization_record, current_pins=current_pins)
        if time.monotonic() >= session_deadline:
            raise ControllerError("one-hour session bound reached; no next command started")
        argv = [item.replace("<private-approved-serial>", serial) for item in row]
        if any("<verified-jmcs-pid>" in item for item in argv):
            if pid is None:
                raise ControllerError("jmcs PID is not established by the approved identity phase")
            argv = [item.replace("<verified-jmcs-pid>", pid) for item in argv]
        if argv[:4] != ["adb", "-s", serial, "shell"]:
            raise ControllerError("manifest argv differs from exact approved endpoint")
        phase = next(item for item in proposal_snapshot["phases"] if item["id"] == phase_id)
        timeout = phase.get("per_command_timeout_seconds")
        maximum = phase.get("per_command_output_limit_bytes")
        if (not isinstance(timeout, int) or not 0 < timeout <= MAX_TIMEOUT_SECONDS
                or not isinstance(maximum, int) or not 0 < maximum <= MAX_OUTPUT_BYTES):
            raise ControllerError("manifest command bounds exceed controller limits")
        if output_budget.remaining_bytes < MIN_COMMAND_OUTPUT_BUDGET_BYTES:
            output_budget.exhausted = True
            records.append({"phase": phase_id, "state": state, "index": index,
                            "argv": argv, "result_status": "SESSION_OUTPUT_BUDGET_EXHAUSTED_BEFORE_COMMAND",
                            "session_output_bytes_before": output_budget.used_bytes,
                            "session_output_limit_bytes": output_budget.limit_bytes,
                            "stdout_file": None, "stderr_file": None})
            raise ControllerError("session output budget exhausted before starting the next command")
        command_limit = min(maximum, output_budget.remaining_bytes)
        command = Command(phase_id, tuple(argv), timeout, command_limit)
        operation, args = _operation_for(command.argv)
        if operation == "read_net_operstate":
            if command.argv != ("adb", "-s", serial, "shell", "cat", "/sys/class/net/usb0/operstate"):
                raise ControllerError("usb0 observation differs from its one fixed argv")
        elif FixedAdb.plan_without_adb_lookup(serial, operation, args) != command.argv:
            raise ControllerError("command differs from the fixed-operation planner")
        output_budget.start_command()
        started_at_utc = datetime.now(timezone.utc).isoformat()
        started_monotonic_ns = time.monotonic_ns()
        try:
            exit_code, stdout, stderr = execute_command(command)
        except BaseException as exc:
            records.append({"phase": phase_id, "state": state, "index": index,
                            "operation": operation, "arguments": list(args),
                            "argv": list(command.argv), "started_at_utc": started_at_utc,
                            "started_monotonic_ns": started_monotonic_ns,
                            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                            "finished_monotonic_ns": time.monotonic_ns(),
                            "result_status": "INTERRUPTED_OR_HOST_EXECUTION_ERROR",
                            "error_type": type(exc).__name__, "exit_code": None,
                            "stdout_file": None, "stderr_file": None})
            raise
        finished_at_utc = datetime.now(timezone.utc).isoformat()
        finished_monotonic_ns = time.monotonic_ns()
        output_bytes = len(stdout) + len(stderr)
        if output_bytes > command.max_output_bytes:
            record = {"phase": phase_id, "state": state, "index": index,
                      "operation": operation, "arguments": list(args),
                      "argv": list(command.argv), "started_at_utc": started_at_utc,
                      "started_monotonic_ns": started_monotonic_ns,
                      "finished_at_utc": finished_at_utc,
                      "finished_monotonic_ns": finished_monotonic_ns,
                      "result_status": "PER_COMMAND_OUTPUT_LIMIT_EXCEEDED",
                      "exit_code": exit_code, "stdout_file": None, "stderr_file": None,
                      "stdout_bytes_observed": len(stdout), "stderr_bytes_observed": len(stderr),
                      "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                      "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
                      "command_output_limit_bytes": command.max_output_bytes,
                      "session_output_bytes_before": output_budget.used_bytes,
                      "session_output_limit_bytes": output_budget.limit_bytes}
            records.append(record)
            raise ControllerError("fixed command exceeded its output ceiling; raw output was not archived")
        if not output_budget.reserve(output_bytes):
            output_budget.exhausted = True
            record = {"phase": phase_id, "state": state, "index": index,
                      "operation": operation, "arguments": list(args),
                      "argv": list(command.argv), "started_at_utc": started_at_utc,
                      "started_monotonic_ns": started_monotonic_ns,
                      "finished_at_utc": finished_at_utc,
                      "finished_monotonic_ns": finished_monotonic_ns,
                      "result_status": "SESSION_OUTPUT_BUDGET_EXCEEDED",
                      "exit_code": exit_code, "stdout_file": None, "stderr_file": None,
                      "stdout_bytes_observed": len(stdout), "stderr_bytes_observed": len(stderr),
                      "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                      "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
                      "session_output_bytes_before": output_budget.used_bytes,
                      "session_output_limit_bytes": output_budget.limit_bytes}
            records.append(record)
            raise ControllerError("session output budget exceeded; command output was not archived and campaign cannot succeed")
        try:
            from collector import classify_command_result
            result_status = classify_command_result(
                exit_code, stdout, stderr,
                timed_out=b"command timed out" in stderr,
                output_limited=b"output limit reached" in stderr,
                operation="read" if operation == "read_net_operstate" else operation,
            ).value
            inventory_lookup = operation == "package-path" or (
                operation == "dumpsys" and len(args) == 2 and args[0] == "package")
            if inventory_lookup and re.search(
                r"(?i)(?:unable to find package|unknown package|package(?:\s+[^\r\n]*)?\s+not found|no package)",
                    (stderr + b"\n" + stdout).decode("utf-8", "replace")):
                result_status = "not_exposed"
        except Exception as exc:
            result_status = f"CLASSIFICATION_ERROR:{type(exc).__name__}"
            classification_error = exc
        else:
            classification_error = None
        try:
            saved = _save_command_result(
                run_dir, command, index, exit_code, stdout, stderr,
                state=state, operation=operation, arguments=args,
                started_at_utc=started_at_utc, started_monotonic_ns=started_monotonic_ns,
                finished_at_utc=finished_at_utc, finished_monotonic_ns=finished_monotonic_ns,
                result_status=result_status)
        except BaseException as exc:
            records.append({"phase": phase_id, "state": state, "index": index,
                            "operation": operation, "arguments": list(args),
                            "argv": list(command.argv),
                            "result_status": "PRIVATE_EVIDENCE_WRITE_FAILED",
                            "error_type": type(exc).__name__, "stdout_file": None,
                            "stderr_file": None, "exit_code": exit_code,
                            "started_at_utc": started_at_utc,
                            "started_monotonic_ns": started_monotonic_ns,
                            "finished_at_utc": finished_at_utc,
                            "finished_monotonic_ns": finished_monotonic_ns,
                            "session_output_bytes_reserved": output_bytes,
                            "stdout_bytes_observed": len(stdout), "stderr_bytes_observed": len(stderr),
                            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
                            "session_output_bytes_used": output_budget.used_bytes})
            raise ControllerError("private evidence write failed; session aborted without treating command as successful") from exc
        saved["session_output_bytes_after"] = output_budget.used_bytes
        records.append(saved)
        index += 1
        if classification_error is not None:
            raise ControllerError("fixed command result could not be classified; raw output preserved and session aborted") from classification_error
        try:
            validation_operation = "read" if operation == "read_net_operstate" else operation
            validate_legacy_shell_output(validation_operation, args, exit_code, stdout, stderr)
        except Exception as exc:
            raise ControllerError(f"fixed command failed; session aborted after {index} commands") from exc
        if operation == "property":
            property_name = args[0]
            expected = EXPECTED_TARGET_PROPERTIES.get(property_name)
            actual = stdout.decode("utf-8", "replace").strip()
            if expected is not None and actual != expected:
                raise ControllerError(f"exact target identity mismatch at {property_name}")
        elif operation == "id":
            text = (stdout + b"\n" + stderr).decode("utf-8", "replace")
            if not re.search(r"(?:^|\s)uid=2000\(shell\)\s+gid=2000\(shell\)(?:\s|$)", text):
                raise ControllerError("ADB shell privilege identity is unexpected; no root fallback is allowed")
        elif operation == "ps":
            pids = parse_ps_jmcs(stdout.decode("utf-8", "replace"))
            if len(pids) != 1:
                raise ControllerError("target identity requires exactly one jmcs process")
            observed = str(pids[0])
            if pid is not None and observed != pid:
                raise ControllerError("jmcs PID changed between approved states")
            pid = observed
            records[-1]["process_identity_confidence"] = "PID_ONLY_NO_START_TIME_OR_EXECUTABLE"
        else:
            remote = command.argv[4:]
            process = re.fullmatch(r"/proc/([0-9]+)/(stat|cmdline|status)", remote[-1]) if remote[0] == "cat" else None
            executable = (remote[-1] if remote[0] == "ls" and len(remote) == 3 else "")
            snapshot_key = None
            if process:
                candidate_pid, leaf = process.groups()
                if pid is None or candidate_pid != pid:
                    raise ControllerError("procfs command PID differs from the validated jmcs process")
                snapshot_key = leaf
                if leaf == "stat":
                    current_snapshot = {"stat": stdout}
                else:
                    current_snapshot[snapshot_key] = stdout
            elif pid is not None and executable == f"/proc/{pid}/exe":
                current_snapshot["exe"] = stdout
            if snapshot_key == "stat" and len(current_snapshot) > 1:
                current_snapshot = {"stat": stdout}
            if set(current_snapshot) == {"stat", "cmdline", "status", "exe"}:
                snap = _snapshot_from(current_snapshot)
                assert snap is not None
                snap["pid"] = pid or ""
                validate_process_identity(snap, snap)
                if expected_identity is not None:
                    validate_process_identity(expected_identity, snap)
                else:
                    expected_identity = snap
                snapshots_seen += 1
                current_snapshot = {}
    if rows and any("<verified-jmcs-pid>" in item for row in rows for item in row) and snapshots_seen < 2:
        raise ControllerError("approved batch did not bracket observations with two process identity snapshots")
    if expected_identity is not None:
        return index, expected_identity
    return index, ({"pid": pid, "identity_confidence": "PID_ONLY_NO_START_TIME_OR_EXECUTABLE"}
                   if pid is not None else None)


def _create_run_directory(base: Path, run_id: str) -> Path:
    path = base / run_id
    try:
        path.mkdir(mode=0o700, exist_ok=False)
    except OSError as exc:
        raise ControllerError("one-run private evidence directory could not be created") from exc
    os.chmod(path, 0o700)
    if path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise ControllerError("one-run evidence directory permissions are not private")
    return path


def _execute_authorized_session(record: dict, *, current_pins: dict[str, str] | None = None,
                                ledger: Path | None = None,
                                prompt: Callable[[str], str] | None = None,
                                output: Callable[[str], None] = print,
                                executor_factory: Callable[[str], Callable[[Command], tuple[int, bytes, bytes]]] | None = None,
                                review_verifier: Callable[[dict, dict[str, str]], None] | None = None,
                                notify: Callable[[str], str] = notify_terminal) -> dict:
    _preload_live_helpers()
    current_pins = pins() if current_pins is None else current_pins
    proposal_raw, proposal_snapshot = _load_bound_proposal(current_pins["profile_sha256"])
    source_lock_raw = SOURCE_LOCK.read_bytes()
    if hashlib.sha256(source_lock_raw).hexdigest() != current_pins["source_lock_sha256"]:
        raise ControllerError("source lock changed after run bindings were established")
    evidence_raw = EVIDENCE.read_bytes()
    source_lock_value = json.loads(source_lock_raw)
    expected_evidence = source_lock_value["sources"].get("docs/diagnostics/evidence-coverage.json")
    if hashlib.sha256(evidence_raw).hexdigest() != expected_evidence:
        raise ControllerError("evidence objectives changed after run bindings were established")
    validate_session_authorization(record, current_pins=current_pins)
    phases = list(record["approved_phases"])
    adb_needed = any("ordinary_unprivileged_adb" in PHASE_CATEGORIES[p] for p in phases)
    transition_phases = {"phase4_three_state_carplay"}
    if adb_needed and not {"phase0_baseline_safety_identity", "phase1_ordinary_adb_capability"}.issubset(phases):
        raise ControllerError("execution requires the baseline and exact target-identity phase in the same approval")
    if transition_phases.intersection(phases) and "phase7_recovery_restoration" not in phases:
        raise ControllerError("execution requires the approved restoration observation phase")
    if review_verifier is None:
        _validate_live_reviews(record, current_pins)
    else:
        review_verifier(record, current_pins)
    base = _private_evidence_directory(record)
    output(f"Experiment: {CAMPAIGN_ID}")
    output(f"Question: {record['owner_question']}")
    output(f"Expected observation: {record['expected_evidence']}")
    output(f"Known risks: {'; '.join(record['known_risks'])}")
    output(f"Approved phases: {', '.join(phases)}")
    output(f"Risk: {record['risk_level']} — categories: {', '.join(record['approved_categories'])}")
    output("Separate live permissions: " + ", ".join(
        f"{key}={'YES' if record['category_permissions'][key] else 'NO'}"
        for key in LIVE_PERMISSION_CATEGORIES))
    output("Known limits: commands may complete without answering the question; raw evidence stays private for offline analysis.")
    output("Review artifacts are checked for structure and exact pins only; independently verify reviewer identity and any safety qualifications before owner authorization.")
    output("Phase 1 process evidence is PID-only; start-time, executable and full process identity require the separately blocked Phase 3 access method.")
    proposal_phases = {item["id"]: item for item in proposal_snapshot["phases"]}
    for phase_id in phases:
        phase = proposal_phases[phase_id]
        for action in phase.get("owner_actions", []):
            output(f"Owner action ({phase_id}): {action}")
        output(f"Stop condition ({phase_id}): {phase.get('stop', 'stop on any unexpected behavior')}")
    serial = record.get("exact_adb_serial") if adb_needed else ""
    reader = None
    if adb_needed and executor_factory is None:
        try:
            sys.path.insert(0, str(HERE))
            from collector import FixedAdb
        finally:
            if sys.path and sys.path[0] == str(HERE):
                sys.path.pop(0)
        # Explicit serial only: FixedAdb does not run `adb devices` when
        # resolve_auto=False, and never invokes adb root or su.
        reader = FixedAdb(serial, resolve_auto=False)
    execute_command = executor_factory(serial) if adb_needed and executor_factory is not None else None
    if reader is not None:
        execute_command = _fixed_adb_executor(reader, serial)
    if not adb_needed:
        execute_command = lambda _command: (0, b"", b"")
    readiness_prompt = (
        "Confirm the physical Honda matches your private vehicle reference, the recorded ADB serial names the intended already-authorized endpoint, "
        "the recorded ADB transport is already authorized and independent of the iPhone/CarPlay data path and shared hub, "
        "the car is stationary in Park with parking brake set and power mode ON with READY absent and engine not running, "
        "the manual 50-minute power-on timer is running, you are present, and warnings/displays/audio are normal. "
        "Is the Honda ready? Type YES, NOT YET, or CANCEL: "
    )
    session_started_utc = datetime.now(timezone.utc).isoformat()
    session_started_monotonic_ns = time.monotonic_ns()
    deadline = time.monotonic() + MAX_SESSION_DURATION_SECONDS
    if _ask_owner(prompt, readiness_prompt).strip() != "YES":
        raise ControllerError("owner did not confirm session readiness")
    if time.monotonic() >= deadline:
        raise ControllerError("one-hour session bound reached during readiness confirmation")
    # The private authorization may expire while the owner is reading prompts.
    validate_session_authorization(record, current_pins=current_pins)
    run_dir = _create_run_directory(base, record["run_id"])
    _write_private_file(run_dir / "campaign-proposal.json", proposal_raw)
    _write_private_file(run_dir / "source-lock.json", source_lock_raw)
    _write_private_file(run_dir / "evidence-objectives.json", evidence_raw)
    marker = authorize_one_run(record, current_pins=current_pins, ledger=ledger)
    owner_notes = []
    command_records: list[dict] = []
    output_budget = SessionOutputBudget()
    phase_results: list[dict] = []
    identity: dict[str, str] | None = None
    transition_started = False
    restoration_confirmed = False
    global_index = 0
    try:
        for phase_id in phases:
            validate_session_authorization(record, current_pins=current_pins)
            phase = next(item for item in proposal_snapshot["phases"] if item["id"] == phase_id)
            if phase_id == "phase0_baseline_safety_identity":
                owner_notes.append({"phase": phase_id, "status": "OWNER_BASELINE_CONFIRMED",
                                    "confirmed_at_utc": datetime.now(timezone.utc).isoformat(),
                                    "monotonic_ns": time.monotonic_ns()})
                phase_results.append({"phase": phase_id, "status": "COMPLETE_NO_DEVICE_COMMANDS",
                                      "started_monotonic_ns": time.monotonic_ns(),
                                      "finished_monotonic_ns": time.monotonic_ns()})
                continue
            if phase_id == "phase7_recovery_restoration":
                _owner_checkpoint(prompt,
                                  "Restore the owner-defined factory baseline with normal controls. Confirm displays, cluster, Navigation, audio, and warnings are normal.",
                                  output=output, deadline=deadline)
                restoration_confirmed = True
                owner_notes.append({"phase": phase_id, "status": "FACTORY_RESTORATION_CONFIRMED",
                                    "confirmed_at_utc": datetime.now(timezone.utc).isoformat(),
                                    "monotonic_ns": time.monotonic_ns()})
            if phase_id in transition_phases:
                states = phase.get("states", [])
                if not isinstance(states, list) or not states:
                    raise ControllerError("approved transition phase has no fixed state sequence")
                if phase_id == "phase4_three_state_carplay" and phase.get("commands_apply_at_each_steady_state") is not True:
                    raise ControllerError("stock CarPlay observation is not bound to every approved steady state")
                phase_command_start = global_index
                phase_started_monotonic_ns = time.monotonic_ns()
                for state in states:
                    state_action = STATE_PROMPTS.get(state)
                    if state_action is None:
                        raise ControllerError("approved state is not in the fixed owner-action map")
                    if phase_id in transition_phases and state in TRANSITION_ACTION_STATES:
                        # The owner may perform the named action after seeing
                        # this prompt even if they later answer STOP or time out.
                        transition_started = True
                        if state != "factory_baseline_restored":
                            restoration_confirmed = False
                    _owner_checkpoint(prompt,
                                      f"{phase_id} / {state}: {state_action} Check for unexpected warnings or abnormal display, cluster, Navigation, and audio behavior.",
                                      output=output, deadline=deadline)
                    validate_session_authorization(record, current_pins=current_pins)
                    owner_notes.append({"phase": phase_id, "state": state,
                                        "status": "OWNER_CONFIRMED_STABLE",
                                        "confirmed_at_utc": datetime.now(timezone.utc).isoformat(),
                                        "monotonic_ns": time.monotonic_ns()})
                    if state == "factory_baseline_restored":
                        restoration_confirmed = True
                    if phase_id == "phase4_three_state_carplay":
                        rows = _phase_rows(phase)
                    else:
                        field = COMMAND_FIELDS[phase_id]
                        rows = phase[field]
                    global_index, identity = _execute_batch(
                        phase_id=phase_id, state=state, rows=rows, serial=serial,
                        proposal_snapshot=proposal_snapshot,
                        execute_command=execute_command, run_dir=run_dir,
                        records=command_records, index=global_index,
                        prior_identity=identity, authorization_record=record,
                        current_pins=current_pins, session_deadline=deadline,
                        output_budget=output_budget, output=output,
                    )
                    if time.monotonic() >= deadline:
                        raise ControllerError("one-hour session bound reached after stable-state capture")
                phase_results.append({"phase": phase_id,
                                      "status": "OBSERVATIONS_COLLECTED_PENDING_EVIDENCE_REVIEW",
                                      "state_count": len(states),
                                      "command_count": global_index - phase_command_start,
                                      "started_monotonic_ns": phase_started_monotonic_ns,
                                      "finished_monotonic_ns": time.monotonic_ns()})
            else:
                rows = _phase_rows(phase)
                phase_started_monotonic_ns = time.monotonic_ns()
                global_index, identity = _execute_batch(
                    phase_id=phase_id, state="single_phase_capture", rows=rows, serial=serial,
                    proposal_snapshot=proposal_snapshot,
                    execute_command=execute_command, run_dir=run_dir,
                    records=command_records, index=global_index,
                    prior_identity=identity, authorization_record=record,
                    current_pins=current_pins, session_deadline=deadline,
                    output_budget=output_budget, output=output,
                )
                phase_results.append({"phase": phase_id, "status": "COMMANDS_COMPLETE_PENDING_EVIDENCE_REVIEW",
                                      "command_count": len(rows),
                                          "process_identity_confidence": (
                                              identity.get("identity_confidence", "FULL_PHASE3_PROCESS_TUPLE")
                                              if phase_id == "phase1_ordinary_adb_capability" and identity
                                              else None),
                                      "started_monotonic_ns": phase_started_monotonic_ns,
                                      "finished_monotonic_ns": time.monotonic_ns()})
                if phase_id == "phase1_ordinary_adb_capability" and _ask_owner(prompt,
                        "Confirm the fixed reads caused no abnormal warning, display, cluster, Navigation, or audio behavior. Type READY or STOP: ").strip() != "READY":
                    raise ControllerError("owner reported or did not exclude abnormal behavior")
                if phase_id == "phase1_ordinary_adb_capability" and time.monotonic() >= deadline:
                    raise ControllerError("one-hour session bound reached after Phase 1")
                if phase_id == "phase7_recovery_restoration" and _ask_owner(prompt,
                        "Confirm the owner-defined factory baseline remains restored and no abnormal warning is present. Type READY or STOP: ").strip() != "READY":
                    raise ControllerError("owner did not confirm final restoration")
                if phase_id == "phase7_recovery_restoration":
                    restoration_confirmed = True
                    owner_notes.append({"phase": phase_id, "status": "FACTORY_RESTORATION_CONFIRMED_AFTER_READS",
                                        "confirmed_at_utc": datetime.now(timezone.utc).isoformat(),
                                        "monotonic_ns": time.monotonic_ns()})
                if phase_id == "phase7_recovery_restoration" and time.monotonic() >= deadline:
                    raise ControllerError("one-hour session bound reached after restoration")
        if _ask_owner(prompt,
                      "All captures and approved restoration are complete. Confirm normal vehicle power-off was completed with factory controls. Type POWERED_OFF to finish; otherwise type STOP: ").strip() != "POWERED_OFF":
            raise ControllerError("normal vehicle power-off was not confirmed")
        if time.monotonic() >= deadline:
            raise ControllerError("one-hour session bound reached before terminal completion")
        owner_notes.append({"phase": "terminal", "status": "NORMAL_POWER_OFF_CONFIRMED",
                            "confirmed_at_utc": datetime.now(timezone.utc).isoformat(),
                            "monotonic_ns": time.monotonic_ns()})
        unresolved = sorted({objective["id"] for objective in json.loads(evidence_raw)["objectives"]})
        objective_map = {phase: list(ids) for phase, ids in POTENTIAL_OBJECTIVES.items() if phase in phases}
        summary = {"campaign_id": CAMPAIGN_ID, "run_id": record["run_id"],
                   "authorization_id": record["authorization_id"], "status": "SESSION_COMPLETE_PENDING_OFFLINE_ANALYSIS",
                   "approved_phases": phases, "phase_results": phase_results,
                   "approved_categories": record["approved_categories"],
                   "category_permissions": record["category_permissions"],
                   "risk_level": record["risk_level"],
                   "authorization_issued_at_utc": record["issued_at_utc"],
                   "authorization_expires_at_utc": record["expires_at_utc"],
                   "readiness_checks": record["readiness_checks"],
                   "adb_transport_details": record.get("adb_transport_details"),
                   "evidence_destination_checklist": record["evidence_destination_checklist"],
                   "owner_state_confirmations": owner_notes, "command_count": len(command_records),
                   "session_output_budget": output_budget.report(),
                   "command_artifacts": command_records, "candidate_objectives_pending_analysis": objective_map,
                   "unresolved_objectives": unresolved,
                   "session_started_at_utc": session_started_utc,
                   "session_started_monotonic_ns": session_started_monotonic_ns,
                   "session_finished_at_utc": datetime.now(timezone.utc).isoformat(),
                   "session_finished_monotonic_ns": time.monotonic_ns(),
                   "exact_vehicle": record["exact_vehicle"],
                   "exact_adb_serial": serial or None,
                   "reviewed_commit_sha": record.get("reviewed_commit_sha"),
                   "owner_question": record["owner_question"],
                   "expected_evidence": record["expected_evidence"],
                   "known_risks": record["known_risks"],
                   "stop_conditions": record["stop_conditions"],
                   "normal_power_off_confirmed": True,
                   "campaign_success": False,
                   "limitations": {"carplay_info_setup": "NOT_EXPOSED_BY_THE_APPROVED_PASSIVE_SNAPSHOT_METHOD",
                                   "jmcs_process_identity": "PID_CONTINUITY_ONLY_START_TIME_AND_EXECUTABLE_UNAVAILABLE",
                                   "campaign_success": False,
                                   "confirmed_evidence_objectives": []},
                   "authorization_marker": marker.name, "source_pins": current_pins,
                   "host_finalization_status": "COMPLETE"}
        output("SESSION COMPLETE — commands ran within the approved scope; evidence remains pending offline analysis.")
        finalization_error = None
        try:
            _write_private_file(run_dir / "session-summary.json",
                                (json.dumps(summary, sort_keys=True, indent=2) + "\n").encode())
            summary["archive_inventory_sha256"] = _write_sha256_inventory(run_dir)
        except Exception as exc:
            finalization_error = exc
            summary["status"] = "SESSION_COMPLETE_ARCHIVE_INCOMPLETE"
            summary["host_finalization_status"] = f"FAILED:{type(finalization_error).__name__}"
            output("SESSION ENDED WITH INCOMPLETE PRIVATE EVIDENCE FINALIZATION — vehicle power-off was confirmed; preserve the folder and inspect offline before another session.")
            try:
                _replace_private_file(run_dir / "session-summary.json",
                                      (json.dumps(summary, sort_keys=True, indent=2) + "\n").encode())
            except Exception:
                output("The terminal result is authoritative; the private session summary could not be updated.")
        summary["notification"] = _safe_notify(notify, "complete" if finalization_error is None else "archive_failure_complete")
        return summary
    except BaseException as exc:
        summary = {"campaign_id": CAMPAIGN_ID, "run_id": record["run_id"],
                   "authorization_id": record["authorization_id"], "status": "ABORTED_HOST_ONLY",
                   "approved_phases": phases, "completed_phase_results": phase_results,
                   "approved_categories": record["approved_categories"],
                   "category_permissions": record["category_permissions"],
                   "risk_level": record["risk_level"],
                   "authorization_issued_at_utc": record["issued_at_utc"],
                   "authorization_expires_at_utc": record["expires_at_utc"],
                   "readiness_checks": record["readiness_checks"],
                   "adb_transport_details": record.get("adb_transport_details"),
                   "evidence_destination_checklist": record["evidence_destination_checklist"],
                   "owner_state_confirmations": owner_notes, "command_count": len(command_records),
                   "session_output_budget": output_budget.report(),
                   "command_artifacts": command_records, "campaign_success": False,
                   "session_started_at_utc": session_started_utc,
                   "session_started_monotonic_ns": session_started_monotonic_ns,
                   "session_finished_at_utc": datetime.now(timezone.utc).isoformat(),
                   "session_finished_monotonic_ns": time.monotonic_ns(),
                   "normal_power_off_confirmed": False,
                   "stop_reason": type(exc).__name__, "vehicle_commands_after_abort": 0,
                   "authorization_marker": marker.name, "source_pins": current_pins}
        if isinstance(exc, ControllerError):
            summary["stop_detail"] = str(exc)
        summary["factory_restoration_required"] = transition_started and not restoration_confirmed
        summary["host_finalization_status"] = "COMPLETE"
        output("SESSION STOPPED — no retry or further vehicle command. If a factory transition began, restore with normal controls and verify displays, cluster, Navigation, audio, and warnings. Power-off was not confirmed.")
        try:
            _write_private_file(run_dir / "session-summary.json",
                                (json.dumps(summary, sort_keys=True, indent=2) + "\n").encode())
            summary["archive_inventory_sha256"] = _write_sha256_inventory(run_dir)
        except Exception as finalization_error:
            summary["host_finalization_status"] = f"FAILED:{type(finalization_error).__name__}"
            output("HOST EVIDENCE FINALIZATION FAILED — preserve the private partial directory and inspect it offline before any later session.")
            try:
                _replace_private_file(run_dir / "session-summary.json",
                                      (json.dumps(summary, sort_keys=True, indent=2) + "\n").encode())
            except Exception:
                output("The terminal result is authoritative; the private session summary could not be updated.")
        summary["notification"] = _safe_notify(
            notify, "stopped" if summary["host_finalization_status"] == "COMPLETE"
            else "archive_failure_stopped")
        if isinstance(exc, KeyboardInterrupt):
            return summary
        if isinstance(exc, ControllerError):
            return summary
        raise


def execute_authorized_session(authorization_path: Path) -> dict:
    record = _load_private_authorization(authorization_path)
    return _execute_authorized_session(record)


def execute_live(authorization_path: Path | None = None):
    if authorization_path is None:
        raise ControllerError("live session requires one private owner authorization file")
    return execute_authorized_session(authorization_path)


def _preload_live_helpers() -> None:
    """Load every executable helper before source pins are checked."""
    sys.path.insert(0, str(HERE))
    try:
        import collector  # noqa: F401
        import parsers  # noqa: F401
        import validate_comprehensive_proposal  # noqa: F401
        import validate_review_artifacts  # noqa: F401
        import comprehensive_replay  # noqa: F401
    finally:
        if sys.path and sys.path[0] == str(HERE):
            sys.path.pop(0)


def _safe_notify(notify: Callable[[str], str], status: str) -> str:
    try:
        return str(notify(status))
    except Exception as exc:
        return f"FAILED:{type(exc).__name__}; terminal output remains authoritative"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("dry-run", "simulate", "run", "analyze"))
    parser.add_argument("--authorization", type=Path,
                        help="private owner-approved session record; required for run")
    parser.add_argument("--archive", type=Path,
                        help="private completed/partial session archive; required for analyze")
    args = parser.parse_args(argv)
    try:
        if args.mode == "analyze":
            if args.archive is None:
                parser.error("analyze requires --archive with one owner-only evidence directory")
            sys.path.insert(0, str(HERE))
            from comprehensive_replay import analyze_archive
            try:
                result = analyze_archive(args.archive)
            finally:
                if sys.path and sys.path[0] == str(HERE):
                    sys.path.pop(0)
            print(json.dumps(result, indent=2, sort_keys=True))
        elif args.mode == "run":
            if args.authorization is None:
                parser.error("run requires --authorization with one private owner session record")
            result = execute_live(args.authorization)
            # Owner identity, serial, argv and raw artifact names stay in the
            # private archive, never the possibly logged terminal output.
            print(json.dumps({key: result.get(key) for key in (
                "campaign_id", "status", "campaign_success",
                "host_finalization_status", "notification")}, sort_keys=True))
            return 0 if result.get("status") == "SESSION_COMPLETE_PENDING_OFFLINE_ANALYSIS" else 2
        elif args.mode == "simulate":
            print(json.dumps(simulate(), indent=2, sort_keys=True))
        else:
            print(json.dumps(dry_run_report(), indent=2, sort_keys=True))
        return 0
    except (ControllerError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
