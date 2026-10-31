"""Validate and summarize the proposal-only comprehensive campaign offline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any

CAMPAIGN_ID = "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031"
BASELINE_ID = "CL-HONDA-RUNTIME-EVIDENCE-20261030"
HISTORICAL_PROFILE = "c58864a9454f525ac0a4758f8828a92f70208bf2142a2dead261e5545c51b10d"
HISTORICAL_MANIFEST = "9ac4ecce79769880f0628e743fa8a61d9b094f9bcfbc43b244f2e8798bce5388"
PHASES = (
    "phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
    "phase2_existing_root_supersu_review", "phase3_jmcs_maps_libraries_fd_socket_ownership",
    "phase4_three_state_carplay", "phase5_display1_navigation_lifecycle",
    "phase6_existing_hondahack_casting", "phase7_recovery_restoration",
)
EXPECTED_STATES = {
    PHASES[4]: ["disconnected_baseline", "stock_carplay_connected", "disconnected_again",
               "stock_carplay_reconnected", "final_disconnected"],
    PHASES[5]: ["navigation_selected", "navigation_deselected", "navigation_reselected"],
    PHASES[6]: ["casting_disabled", "ordinary_start_casting", "navigation_deselected",
               "navigation_reselected", "ordinary_stop_casting", "factory_baseline_restored"],
}
FIXED_SERIAL = "<private-approved-serial>"
PID = "<verified-jmcs-pid>"
ALLOWED_PROPERTIES = {
    "ro.build.version.release", "ro.build.version.sdk", "ro.product.device",
    "ro.product.board", "ro.hardware", "ro.secure", "ro.debuggable",
}
FORBIDDEN_TOKENS = {"su", "root", "ptrace", "frida", "mem", "environ", "install",
                    "setprop", "tcpdump", "netcfg", "screencap", "input"}
PHASE_TOOLS = {
    PHASES[0]: set(), PHASES[1]: {"id", "ps", "getprop", "cat", "ls", "dumpsys"},
    PHASES[2]: set(), PHASES[3]: set(), PHASES[4]: {"ps", "cat", "ls", "dumpsys", "logcat"},
    PHASES[5]: {"cat", "ls", "dumpsys"}, PHASES[6]: {"cat", "ls", "dumpsys"},
    PHASES[7]: {"ps", "cat", "ls", "dumpsys"},
}
TOP_FIELDS = frozenset({
    "schema", "campaign_id", "requirements_baseline", "historical_campaign",
    "live_execution_enabled", "live_authorization", "controller", "host", "target",
    "execution_bounds_proposal", "global_stop_conditions",
    "required_conditions_for_any_future_run", "process_identity_expectations",
    "phases", "post_session_instrumentation",
})
PHASE_FIELDS = frozenset({
    "id", "category", "authorization_status", "commands", "live_argv", "owner_actions",
    "stop", "per_command_timeout_seconds", "per_command_output_limit_bytes", "failure_policy",
    "states", "commands_apply_at_each_steady_state", "commands_after_each_owner_confirmation",
    "commands_after_each_allowed_state", "owner_checks", "host_checks", "identity_revalidation",
    "process_identity_revalidation", "network_scope", "log_collection_purpose",
    "logcat_capture_count_per_steady_state", "prohibited", "prohibited_reads", "access_decision",
    "required_evidence_to_reconsider", "required_observations_if_reconsidered", "known_side_effect",
    "abort_path", "shared_adb_server", "capture_during_transition", "required_categories",
    "offline_actions", "qualified_vehicle_safety_review",
})
NESTED_FIELDS = {
    "historical_campaign": frozenset({"campaign_id", "state", "profile_sha256", "manifest_sha256", "reuse_allowed"}),
    "execution_bounds_proposal": frozenset({
        "max_command_timeout_seconds", "max_command_output_bytes", "max_total_elapsed_seconds",
        "max_owner_prompt_idle_seconds", "capture_during_owner_ui_transition", "auto_retry",
        "auto_privilege_escalation", "raw_evidence_destination", "evidence_integrity",
        "per_command_bounds", "process_placeholder_binding", "command_form",
    }),
    "process_identity_expectations": frozenset({
        "process_name", "executable_path", "cmdline_identity", "uid", "gid", "start_time", "pid_source",
    }),
    "post_session_instrumentation": frozenset({"authorization", "execution_enabled", "separate_future_categories"}),
}
PER_COMMAND_BOUND_FIELDS = frozenset({"timeout_seconds", "combined_stdout_stderr_bytes", "enforced_by"})
SHELL_LAUNCHERS = {"adb", "su", "sh", "bash", "dash", "zsh", "busybox", "toybox"}


def _commands_in(value: Any) -> list[tuple[str, list[str]]]:
    found: list[tuple[str, list[str]]] = []
    command_keys = {"commands", "commands_after_each_owner_confirmation",
                    "commands_after_each_allowed_state", "live_argv"}
    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if (isinstance(child, str) and re.search(r"(?:command|argv|shell)", key, re.I)
                        and re.search(
                            r"^\s*(?:adb\s|su\s+-c\b|(?:sh|bash|dash|zsh)\s+-c\b|/[^\s]*/(?:adb|su)\s)",
                            child, re.I,
                        )):
                    raise ValueError(f"{path}.{key}: shell command strings are forbidden")
                if key in command_keys:
                    if not isinstance(child, list):
                        raise ValueError(f"{path}.{key}: command collection must be a list")
                    for index, argv in enumerate(child):
                        found.append((f"{path}.{key}[{index}]", argv))
                    continue
                walk(child, f"{path}.{key}")
        elif isinstance(node, list):
            command_like = (node and isinstance(node[0], str) and (
                Path(node[0]).name.lower() in SHELL_LAUNCHERS
                or (len(node) > 1 and isinstance(node[1], str) and node[1].startswith("-"))
            ))
            if command_like:
                found.append((path, node))
                return
            for index, child in enumerate(node):
                walk(child, f"{path}[{index}]")
    walk(value, "profile")
    return found


def _validate_argv(path: str, argv: Any) -> None:
    if (not isinstance(argv, list) or len(argv) < 5 or len(argv) > 16
            or any(not isinstance(part, str) or not part for part in argv)):
        raise ValueError(f"{path}: command must be a bounded fixed argv list")
    if argv[:4] != ["adb", "-s", FIXED_SERIAL, "shell"]:
        raise ValueError(f"{path}: only exact-serial unprivileged adb shell argv is allowed")
    command = argv[4:]
    tokens = {token for part in command for token in re.findall(r"[a-z0-9_./-]+", part.lower())}
    sensitive_procfs = re.search(r"/proc/(?:\d+|<[^>]+>)/(?:mem|environ)(?:\b|$)",
                                " ".join(command), re.IGNORECASE)
    if FORBIDDEN_TOKENS & tokens or sensitive_procfs:
        raise ValueError(f"{path}: forbidden operation token")
    if any(char in part for part in command for char in (";", "|", "&", "$", "`", "\n", "\r")):
        raise ValueError(f"{path}: shell composition is forbidden")
    tool = command[0]
    if tool == "id" and len(command) == 1:
        return
    if tool == "ps" and len(command) == 1:
        return
    if tool == "getprop" and len(command) == 2 and command[1] in ALLOWED_PROPERTIES:
        return
    if tool == "dumpsys" and len(command) == 2 and command[1] in {"display", "SurfaceFlinger", "window"}:
        return
    if tool == "logcat" and command == ["logcat", "-d", "-t", "500"]:
        return
    if tool == "ls" and command == ["ls", "-l", f"/proc/{PID}/exe"]:
        return
    if tool == "cat" and len(command) == 2:
        allowed_exact = {
            f"/proc/{PID}/stat", f"/proc/{PID}/cmdline", f"/proc/{PID}/status",
            "/proc/net/tcp", "/proc/net/tcp6", "/proc/net/udp", "/proc/net/udp6",
            "/proc/net/unix", "/sys/class/net/usb0/operstate",
        }
        if command[1] in allowed_exact:
            return
    raise ValueError(f"{path}: command is outside the fixed read-only allowlist")


def validate_proposal(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != "claritylink-proposed-campaign-scope-v1":
        raise ValueError("unsupported comprehensive proposal schema")
    if set(value) != TOP_FIELDS:
        raise ValueError("proposal fields differ from the fixed schema")
    for field, allowed in NESTED_FIELDS.items():
        nested = value.get(field)
        if not isinstance(nested, dict) or set(nested) != allowed:
            raise ValueError(f"{field} fields differ from the fixed schema")
    bounds = value["execution_bounds_proposal"]
    if (not isinstance(bounds.get("per_command_bounds"), dict)
            or set(bounds["per_command_bounds"]) != PER_COMMAND_BOUND_FIELDS):
        raise ValueError("per_command_bounds fields differ from the fixed schema")
    phases = value.get("phases")
    if isinstance(phases, list) and any(isinstance(phase, dict) and set(phase) - PHASE_FIELDS
                                        for phase in phases):
        raise ValueError("phase contains fields outside the fixed schema")
    if (value.get("campaign_id") != CAMPAIGN_ID
            or value.get("requirements_baseline") != BASELINE_ID):
        raise ValueError("campaign identity differs from the approved requirements baseline")
    if value.get("live_execution_enabled") is not False or value.get("live_authorization") != "NOT_AUTHORIZED":
        raise ValueError("comprehensive proposal must remain non-executable and unauthorized")
    if not str(value.get("controller", "")).startswith("NONE: proposal only"):
        raise ValueError("proposal must not name a live controller")
    if value.get("process_identity_expectations") != {
        "process_name": "jmcs", "executable_path": "/system/bin/jmcs",
        "cmdline_identity": "/system/bin/jmcs", "uid": 0, "gid": 0,
        "start_time": "/proc/PID/stat field 22 (clock ticks)",
        "pid_source": "exactly one jmcs candidate from the fixed ps parser on the approved serial",
    }:
        raise ValueError("exact jmcs executable, command-line, UID/GID, PID, and start-time identity is required")
    historical = value.get("historical_campaign", {})
    if (historical.get("reuse_allowed") is not False
            or historical.get("profile_sha256") != HISTORICAL_PROFILE
            or historical.get("manifest_sha256") != HISTORICAL_MANIFEST):
        raise ValueError("historical C-P baseline must remain frozen and non-reusable")
    bounds = value.get("execution_bounds_proposal", {})
    if (bounds.get("max_command_timeout_seconds") != 20
            or bounds.get("max_command_output_bytes") != 4194304
            or bounds.get("max_total_elapsed_seconds") != 3600
            or bounds.get("max_owner_prompt_idle_seconds") != 300
            or bounds.get("auto_retry") is not False
            or bounds.get("auto_privilege_escalation") is not False
            or bounds.get("capture_during_owner_ui_transition") is not False
            or bounds.get("per_command_bounds", {}).get("timeout_seconds") != 20
            or bounds.get("per_command_bounds", {}).get("combined_stdout_stderr_bytes") != 4194304
            or not isinstance(bounds.get("per_command_bounds", {}).get("enforced_by"), str)):
        raise ValueError("proposal exceeds or omits a required session/command bound")
    binding = bounds.get("process_placeholder_binding", "")
    if (not isinstance(binding, str) or "/system/bin/jmcs" not in binding
            or "single argv element" not in binding or "Revalidate all four identity facts" not in binding):
        raise ValueError("process placeholder must be tied to exact identity and pre/post validation")
    if (not isinstance(phases, list) or any(not isinstance(phase, dict) for phase in phases)
            or [phase.get("id") for phase in phases] != list(PHASES)):
        raise ValueError("proposal must retain the exact ordered eight-phase requirements")
    for phase in phases:
        if (phase.get("per_command_timeout_seconds") != 20
                or phase.get("per_command_output_limit_bytes") != 4194304
                or phase.get("failure_policy") != "stop immediately; do not retry"):
            raise ValueError(f"{phase['id']}: per-command limits and fail-stop policy must be explicit")
        if "capture_during_transition" in phase and phase["capture_during_transition"] is not False:
            raise ValueError(f"{phase['id']}: capture during UI transitions is prohibited")
        if phase["id"] in EXPECTED_STATES and phase.get("states") != EXPECTED_STATES[phase["id"]]:
            raise ValueError(f"{phase['id']}: required observation state sequence changed")
    if phases[4].get("commands_apply_at_each_steady_state") is not True:
        raise ValueError("Phase 4 fixed observations must run at every CarPlay steady state")
    for index in (2, 3):
        if (phases[index].get("authorization_status") != "BLOCKED_NO_JUSTIFIABLE_ACCESS_METHOD"
                or phases[index].get("live_argv") != []):
            raise ValueError("privileged phases must remain blocked with no live argv")
    expected_authorization = {
        1: "SEPARATE_EXACT_RUN_APPROVAL_REQUIRED",
        4: "SEPARATE_ADB_AND_IPHONE_TRANSITION_APPROVALS_REQUIRED",
        5: "SEPARATE_EXACT_RUN_APPROVAL_REQUIRED",
        6: "SEPARATE_HONDAHACK_REVIEW_AND_EXACT_OWNER_APPROVAL_REQUIRED",
    }
    for index, expected in expected_authorization.items():
        if phases[index].get("authorization_status") != expected:
            raise ValueError(f"{PHASES[index]}: authorization gate changed")
    safety_review = phases[6].get("qualified_vehicle_safety_review")
    if (not isinstance(safety_review, str) or "REQUIRED" not in safety_review
            or "Display 1" not in safety_review):
        raise ValueError("HondaHack/Display 1 phase requires qualified vehicle-safety review")
    # Reject unsafe/malformed argv before structural sequence checks so a bad
    # appended command cannot mask the actionable command-level violation.
    discovered_commands = _commands_in(value)
    for command_path, command_argv in discovered_commands:
        _validate_argv(command_path, command_argv)
        command_phase_match = re.search(r"profile\.phases\[(\d+)\]", command_path)
        if command_phase_match:
            command_phase = phases[int(command_phase_match.group(1))]
            command = command_argv[4:]
            if (command[0] == "cat" and command[1].startswith(("/proc/net/", "/sys/class/net/"))
                    and command_phase["id"] != PHASES[4]):
                raise ValueError(f"{command_path}: network observations are restricted to Phase 4")
    identity_ops = [
        ["cat", f"/proc/{PID}/stat"], ["cat", f"/proc/{PID}/cmdline"],
        ["cat", f"/proc/{PID}/status"], ["ls", "-l", f"/proc/{PID}/exe"],
    ]
    def ops(phase: dict[str, Any], field: str) -> list[list[str]]:
        return [argv[4:] for argv in phase.get(field, [])]
    def identity_bracket(sequence: list[list[str]]) -> bool:
        return (len(sequence) >= len(identity_ops) * 2
                and sequence[:len(identity_ops)] == identity_ops
                and sequence[-len(identity_ops):] == identity_ops)
    phase1_ops = ops(phases[1], "commands")
    if (len(phase1_ops) < 9 or phase1_ops[0] != ["ps"]
            or phase1_ops[1:5] != identity_ops
            or phase1_ops[-4:] != identity_ops):
        raise ValueError("Phase 1 must resolve one PID, verify identity, then bracket diagnostics")
    phase4_ops = ops(phases[4], "commands")
    if (not identity_bracket(phase4_ops[1:]) or phase4_ops[0] != ["ps"]
            or sum(item[0] == "logcat" for item in phase4_ops) != 1
            or phase4_ops.index(["logcat", "-d", "-t", "500"]) >= len(phase4_ops) - 4):
        raise ValueError("Phase 4 needs one steady-state log snapshot inside complete identity brackets")
    for phase_index, command_field in ((5, "commands_after_each_owner_confirmation"),
                                       (6, "commands_after_each_allowed_state"),
                                       (7, "commands")):
        sequence = ops(phases[phase_index], command_field)
        if phase_index == 7 and sequence and sequence[0] == ["ps"]:
            sequence = sequence[1:]
        if not identity_bracket(sequence):
            raise ValueError(f"{PHASES[phase_index]} must bracket every stable-state capture with full identity checks")
    command_count = 0
    for path, argv in _commands_in(value):
        _validate_argv(path, argv)
        phase_match = re.search(r"profile\.phases\[(\d+)\]", path)
        phase = phases[int(phase_match.group(1))] if phase_match else None
        if phase is None or argv[4] not in PHASE_TOOLS[phase["id"]]:
            raise ValueError(f"{path}: operation is not approved for its phase")
        if argv[4] == "cat" and argv[5].startswith(("/proc/net/", "/sys/class/net/")) \
                and phase["id"] != PHASES[4]:
            raise ValueError(f"{path}: network observations are restricted to Phase 4")
        if argv[4] == "logcat" and phase["id"] != PHASES[4]:
            raise ValueError(f"{path}: bounded logs are restricted to CarPlay steady states")
        command_count += 1
    return {"campaign_id": CAMPAIGN_ID, "mode": "OFFLINE_PROPOSAL_VALIDATION_NO_ADB",
            "phase_count": len(phases), "fixed_command_count": command_count,
            "privileged_phases_live_argv": 0, "live_execution_enabled": False,
            "authorization": "NOT_AUTHORIZED", "safeForHonda": False,
            "vehicle_deployment": "VEHICLE_DEPLOYMENT_NOT_AUTHORIZED"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposal", type=Path)
    args = parser.parse_args()
    try:
        report = validate_proposal(json.loads(args.proposal.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError, TypeError, AttributeError, KeyError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
