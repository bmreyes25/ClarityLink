import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_proposal():
    return json.loads((ROOT / "docs/diagnostics/comprehensive-campaign-proposal.json")
                      .read_text(encoding="utf-8"))


def collect_commands(node):
    command_keys = {"commands", "commands_after_each_owner_confirmation",
                    "commands_after_each_allowed_state", "live_argv"}
    commands = []
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in command_keys and isinstance(child, list):
                    commands.extend(child)
                else:
                    walk(child)
        elif isinstance(value, list):
            if value and all(isinstance(arg, str) for arg in value) and value[0] in {"adb", "su"}:
                commands.append(value)
            for child in value:
                walk(child)
    walk(node)
    return commands


def commands_are_safe(commands):
    forbidden_tokens = {"su", "root", "ptrace", "frida", "netcfg", "tcpdump"}
    forbidden_paths = re.compile(r"/proc/(?:<[^>]+>|\d+)/(?:mem|environ)(?:\b|$)")
    for argv in commands:
        if not isinstance(argv, list) or not argv or argv[0] != "adb":
            return False
        if not all(isinstance(part, str) for part in argv):
            return False
        tokens = {token for part in argv for token in re.findall(r"[a-z0-9_./-]+", part.lower())}
        if forbidden_tokens.intersection(tokens):
            return False
        if any(forbidden_paths.search(part.lower()) for part in argv):
            return False
    return True


def test_proposal_retains_all_phases_and_is_not_executable():
    proposal = load_proposal()
    assert proposal["live_execution_enabled"] is False
    assert "comprehensive_controller.py" in proposal["controller"]
    assert "one-use authorization" in proposal["controller"]
    assert [phase["id"] for phase in proposal["phases"]] == [
        "phase0_baseline_safety_identity", "phase1_ordinary_adb_capability",
        "phase2_existing_root_supersu_review", "phase3_jmcs_maps_libraries_fd_socket_ownership",
        "phase4_three_state_carplay", "phase5_display1_navigation_lifecycle",
        "phase6_existing_hondahack_casting", "phase7_recovery_restoration",
    ]
    assert proposal["historical_campaign"]["reuse_allowed"] is False
    assert proposal["phases"][2]["authorization_status"] == "BLOCKED_NO_JUSTIFIABLE_ACCESS_METHOD"
    assert proposal["phases"][3]["authorization_status"] == "BLOCKED_NO_JUSTIFIABLE_ACCESS_METHOD"
    assert proposal["phases"][2]["live_argv"] == []
    assert proposal["phases"][3]["live_argv"] == []


def test_command_argv_has_no_privilege_injection_or_unlisted_network_probe():
    proposal = load_proposal()
    commands = collect_commands(proposal["phases"])
    assert commands_are_safe(commands)
    bounds = proposal["execution_bounds_proposal"]
    assert bounds["per_command_bounds"]["timeout_seconds"] == 20
    assert bounds["per_command_bounds"]["combined_stdout_stderr_bytes"] == 4194304
    assert "one argv element" in bounds["process_placeholder_binding"]
    assert all(phase["per_command_timeout_seconds"] == 20
               and phase["per_command_output_limit_bytes"] == 4194304
               and phase["failure_policy"] == "stop immediately; do not retry"
               for phase in proposal["phases"])


def test_reconnect_hondahack_and_abort_boundaries_remain_explicit():
    proposal = load_proposal()
    phase4 = proposal["phases"][4]
    assert phase4["states"] == ["disconnected_baseline", "stock_carplay_connected",
                                "navigation_selected", "navigation_deselected",
                                "navigation_reselected", "disconnected_again",
                                "stock_carplay_reconnected", "final_disconnected"]
    assert phase4["capture_during_transition"] is False
    phase6 = proposal["phases"][6]
    assert {"ordinary_unprivileged_adb", "factory_navigation_observation",
            "existing_hondahack_observation"} == set(phase6["required_categories"])
    assert proposal["phases"][7]["abort_path"].startswith("Host-only")
    assert proposal["global_stop_conditions"]
    assert "REQUIRED" in proposal["phases"][6]["qualified_vehicle_safety_review"]
    assert "logcat" not in str(proposal["phases"][1]["commands"])
    assert "logcat" not in str(proposal["phases"][7]["commands"])
    assert "not a repeated search" in proposal["phases"][4]["log_collection_purpose"]


def test_command_safety_scans_strings_and_nested_command_fields():
    proposal = load_proposal()
    proposal["phases"][0]["future_operations"] = [
        ["adb", "shell", "su -c id"], ["adb", "shell", "/proc/42/mem"],
        ["adb", "shell", "/proc/<pid>/environ"],
    ]
    assert not commands_are_safe(collect_commands(proposal))
    assert not commands_are_safe([["adb", "shell", "cat", "/proc/42/mem"]])
