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
    "phase4_three_state_carplay", "phase7_recovery_restoration",
)
EXPECTED_STATES = {
    PHASES[4]: ["disconnected_baseline", "stock_carplay_connected", "navigation_selected",
               "navigation_deselected", "navigation_reselected", "disconnected_again",
               "stock_carplay_reconnected", "navigation_selected_after_reconnect",
               "navigation_deselected_after_reconnect", "final_disconnected"],
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
    PHASES[0]: set(), PHASES[1]: {"id", "ps", "getprop", "service", "dumpsys", "pm", "ls"},
    PHASES[2]: set(), PHASES[3]: set(),
    PHASES[4]: {"ps", "cat", "dumpsys", "logcat"},
    PHASES[5]: {"ps", "cat", "dumpsys", "logcat"},
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
    "comparative_purpose",
    "offline_actions", "owner_safety_self_assessment",
    "baseline_inventory", "activity_manager_scope", "owner_confirmation_rule",
})
NESTED_FIELDS = {
    "historical_campaign": frozenset({"campaign_id", "state", "profile_sha256", "manifest_sha256", "reuse_allowed"}),
    "execution_bounds_proposal": frozenset({
        "max_command_timeout_seconds", "max_command_output_bytes", "max_session_output_bytes",
        "max_total_elapsed_seconds",
        "max_owner_prompt_idle_seconds", "capture_during_owner_ui_transition", "auto_retry",
        "auto_privilege_escalation", "raw_evidence_destination", "evidence_integrity",
        "max_campaign_command_count", "max_campaign_command_output_bytes",
        "max_command_time_sum_seconds", "max_owner_prompt_time_sum_seconds",
        "max_bounded_elapsed_seconds", "remaining_elapsed_margin_seconds",
        "minimum_private_evidence_free_bytes",
        "per_command_bounds", "process_placeholder_binding", "command_form",
    }),
    "process_identity_expectations": frozenset({
        "process_name", "executable_path", "cmdline_identity", "uid", "gid", "start_time", "pid_source",
    }),
    "post_session_instrumentation": frozenset({"authorization", "execution_enabled", "separate_future_categories"}),
}
PER_COMMAND_BOUND_FIELDS = frozenset({"timeout_seconds", "combined_stdout_stderr_bytes",
                                      "session_combined_stdout_stderr_bytes", "enforced_by"})
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
    phase_match = re.search(r"profile\.phases\[(\d+)\]", path)
    baseline_phase = phase_match is not None and int(phase_match.group(1)) == 1
    if any(char in part for part in command for char in (";", "|", "&", "$", "`", "\n", "\r")):
        raise ValueError(f"{path}: shell composition is forbidden")
    tool = command[0]
    if tool == "id" and len(command) == 1:
        return
    if tool == "ps" and len(command) == 1:
        return
    if tool == "ls" and command == ["ls", "/sys/class/graphics"] and baseline_phase:
        return
    if tool == "getprop" and len(command) == 2 and command[1] in ALLOWED_PROPERTIES:
        return
    if tool == "service" and command == ["service", "list"] and baseline_phase:
        return
    if tool == "dumpsys" and len(command) == 2 and command[1] in {"display", "SurfaceFlinger", "window"}:
        return
    if tool == "dumpsys" and command in (["dumpsys", "activity", "activities"],
                                          ["dumpsys", "activity", "services"]):
        return
    if (tool == "dumpsys" and len(command) == 3 and command[1] == "package"
            and command[2] in {
                "com.mitsubishielectric.ada.appservice.navigation",
                "com.mitsubishielectric.ada.app.carplay",
                "com.mitsubishielectric.ada.appservice.carplayapservice",
                "com.mitsubishielectric.ada.appservice.externaldisplay",
                "com.mitsubishielectric.ada.app.externaldisplay",
            } and baseline_phase):
        return
    if (tool == "pm" and len(command) == 3 and command[1] == "path"
            and command[2] in {
                "com.mitsubishielectric.ada.appservice.navigation",
                "com.mitsubishielectric.ada.app.carplay",
                "com.mitsubishielectric.ada.appservice.carplayapservice",
                "com.mitsubishielectric.ada.appservice.externaldisplay",
                "com.mitsubishielectric.ada.app.externaldisplay",
            } and baseline_phase):
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
    if value.get("controller") != "tools/honda-readonly-preflight/comprehensive_controller.py; ordinary ADB only; exact owner state confirmations, one-use review-bound authorization, fixed allowlist, and 158400512-byte combined stdout/stderr session limit":
        raise ValueError("proposal must name the fixed authorization-gated controller for ordinary ADB without enabling live execution")
    if value.get("process_identity_expectations") != {
        "process_name": "jmcs", "executable_path": "/system/bin/jmcs",
        "cmdline_identity": "/system/bin/jmcs", "uid": 0, "gid": 0,
        "start_time": "/proc/PID/stat field 22 is required only for Phase 3, which remains blocked; ordinary phases use fixed ps PID continuity only.",
        "pid_source": "exactly one jmcs candidate from the fixed ps parser on the approved serial",
    }:
        raise ValueError("exact jmcs executable, command-line, UID/GID, PID, and start-time identity is required")
    historical = value.get("historical_campaign", {})
    if (historical.get("reuse_allowed") is not False
            or historical.get("profile_sha256") != HISTORICAL_PROFILE
            or historical.get("manifest_sha256") != HISTORICAL_MANIFEST):
        raise ValueError("historical C-P baseline must remain frozen and non-reusable")
    bounds = value.get("execution_bounds_proposal", {})
    if (bounds.get("max_command_timeout_seconds") != 10
            or bounds.get("max_command_output_bytes") != 900000
            or bounds.get("max_session_output_bytes") != 158400512
            or bounds.get("max_total_elapsed_seconds") != 6000
            or bounds.get("max_owner_prompt_idle_seconds") != 90
            or bounds.get("auto_retry") is not False
            or bounds.get("auto_privilege_escalation") is not False
            or bounds.get("capture_during_owner_ui_transition") is not False
            or bounds.get("per_command_bounds", {}).get("timeout_seconds") != 10
            or bounds.get("per_command_bounds", {}).get("combined_stdout_stderr_bytes") != 900000
            or bounds.get("per_command_bounds", {}).get("session_combined_stdout_stderr_bytes") != 158400512
            or not isinstance(bounds.get("per_command_bounds", {}).get("enforced_by"), str)):
        raise ValueError("proposal exceeds or omits a required session/command bound")
    binding = bounds.get("process_placeholder_binding", "")
    if (not isinstance(binding, str) or "/system/bin/jmcs" not in binding
            or "one argv element" not in binding or "Revalidate all four identity facts" not in binding):
        raise ValueError("process placeholder must be tied to exact identity and pre/post validation")
    if (not isinstance(phases, list) or any(not isinstance(phase, dict) for phase in phases)
            or [phase.get("id") for phase in phases] != list(PHASES)):
        raise ValueError("proposal must retain the exact ordered six-phase ordinary campaign")
    for phase in phases:
        if (phase.get("per_command_timeout_seconds") != 10
                or phase.get("per_command_output_limit_bytes") != 900000
                or phase.get("failure_policy") != "stop immediately; do not retry"):
            raise ValueError(f"{phase['id']}: per-command limits and fail-stop policy must be explicit")
        if "capture_during_transition" in phase and phase["capture_during_transition"] is not False:
            raise ValueError(f"{phase['id']}: capture during UI transitions is prohibited")
        if phase["id"] in EXPECTED_STATES and phase.get("states") != EXPECTED_STATES[phase["id"]]:
            raise ValueError(f"{phase['id']}: required observation state sequence changed")
    if phases[4].get("commands_apply_at_each_steady_state") is not True:
        raise ValueError("Phase 4 fixed observations must run at every CarPlay steady state confirmed by the owner")
    for index in (2, 3):
        if (phases[index].get("authorization_status") != "BLOCKED_NO_JUSTIFIABLE_ACCESS_METHOD"
                or phases[index].get("live_argv") != []):
            raise ValueError("privileged phases must remain blocked with no live argv")
    if phases[4].get("authorization_status") != "SEPARATE_EXACT_RUN_APPROVAL_REQUIRED":
        raise ValueError("ordinary lifecycle requires a separate exact session authorization")
    if phases[5].get("authorization_status") != "NORMAL_COMPLETION_ONLY; ABORT PATH IS HOST ONLY":
        raise ValueError("restoration remains a normal-completion-only observation")
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
                    and command_phase["id"] not in {PHASES[4], PHASES[5]}):
                raise ValueError(f"{command_path}: network observations are restricted to lifecycle/restoration")
    expected_packages = (
        "com.mitsubishielectric.ada.appservice.navigation",
        "com.mitsubishielectric.ada.app.carplay",
        "com.mitsubishielectric.ada.appservice.carplayapservice",
        "com.mitsubishielectric.ada.appservice.externaldisplay",
        "com.mitsubishielectric.ada.app.externaldisplay",
    )
    phase1_ops = [argv[4:] for argv in phases[1]["commands"]]
    identity_properties = [["getprop", prop] for prop in (
        "ro.build.version.release", "ro.build.version.sdk", "ro.product.device",
        "ro.product.board", "ro.hardware")]
    expected_phase1 = identity_properties + [["id"], ["ps"], ["service", "list"],
                                             ["ls", "/sys/class/graphics"]]
    for package in expected_packages:
        expected_phase1.extend([["dumpsys", "package", package], ["pm", "path", package]])
    if phase1_ops != expected_phase1:
        raise ValueError("Phase 1 must perform fixed identity and baseline factory package/service inventory")
    expected_state_ops = [
        ["ps"], ["dumpsys", "activity", "activities"], ["dumpsys", "activity", "services"],
        ["dumpsys", "display"], ["dumpsys", "SurfaceFlinger"], ["dumpsys", "window"],
        ["cat", "/proc/net/tcp"], ["cat", "/proc/net/tcp6"], ["cat", "/proc/net/udp"],
        ["cat", "/proc/net/udp6"], ["cat", "/proc/net/unix"],
        ["cat", "/sys/class/net/usb0/operstate"], ["logcat", "-d", "-t", "500"],
    ]
    if [argv[4:] for argv in phases[4]["commands"]] != expected_state_ops:
        raise ValueError("Phase 4 commands must be the exact fixed process/activity/display/network snapshot")
    if [argv[4:] for argv in phases[5]["commands"]] != expected_state_ops:
        raise ValueError("Phase 7 restoration must repeat the approved fixed lifecycle snapshot")
    if len(phases[4]["states"]) * len(expected_state_ops) + len(phase1_ops) + len(expected_state_ops) != 162:
        raise ValueError("fixed campaign must remain within the 162-command elapsed-time calculation")
    command_count = sum(
        len(phase.get("commands", phase.get("live_argv", []))) *
        (len(phase.get("states", [])) if phase["id"] == PHASES[4] else 1)
        for phase in phases
    )
    if command_count != 162:
        raise ValueError("fixed campaign command count changed without recalculating time/storage bounds")
    exact_bounds = {
        "max_campaign_command_count": 162,
        "max_campaign_command_output_bytes": command_count * 900000,
        "max_command_time_sum_seconds": command_count * 10,
        "max_owner_prompt_time_sum_seconds": 15 * 90,
        "max_bounded_elapsed_seconds": command_count * 10 + 15 * 90,
        "remaining_elapsed_margin_seconds": 6000 - (command_count * 10 + 15 * 90),
        "minimum_private_evidence_free_bytes": 158400512 + 8 * 1024 * 1024,
    }
    if any(bounds.get(key) != expected for key, expected in exact_bounds.items()):
        raise ValueError("campaign aggregate time/storage calculations do not match fixed command and prompt counts")
    fixed_command_shape_count = sum(len(phase.get("commands", phase.get("live_argv", []))) for phase in phases)
    return {"campaign_id": CAMPAIGN_ID, "mode": "OFFLINE_PROPOSAL_VALIDATION_NO_ADB",
            "phase_count": len(phases), "fixed_command_shape_count": fixed_command_shape_count,
            **exact_bounds,
            "max_session_output_bytes": 158400512,
            "maximum_captured_output_bytes_at_command_limits": 162 * 900000,
            "maximum_command_seconds": 162 * 10,
            "maximum_owner_prompt_seconds": 15 * 90,
            "maximum_elapsed_upper_bound_seconds": 162 * 10 + 15 * 90,
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
