import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "honda-readonly-preflight"))

import validate_comprehensive_proposal as validator


def load_proposal():
    return json.loads((ROOT / "docs/diagnostics/comprehensive-campaign-proposal.json")
                      .read_text(encoding="utf-8"))


def test_proposal_offline_validation_has_no_vehicle_or_adb_side_effect():
    result = validator.validate_proposal(load_proposal())
    assert result["mode"] == "OFFLINE_PROPOSAL_VALIDATION_NO_ADB"
    assert result["phase_count"] == 6
    assert result["fixed_command_shape_count"] == 45
    assert result["max_campaign_command_count"] == 162
    assert result["max_campaign_command_output_bytes"] == 145800000
    assert result["max_session_output_bytes"] == 158400512
    assert result["privileged_phases_live_argv"] == 0
    assert result["live_execution_enabled"] is False
    assert "comprehensive_controller.py" in load_proposal()["controller"]
    assert result["safeForHonda"] is False
    assert result["vehicle_deployment"] == "VEHICLE_DEPLOYMENT_NOT_AUTHORIZED"


@pytest.mark.parametrize("mutate, message", [
    (lambda p: p.update(live_execution_enabled=True), "non-executable and unauthorized"),
    (lambda p: p.update(controller="unrestricted ADB"), "fixed authorization-gated controller"),
    (lambda p: p["phases"].pop(), "exact ordered six-phase"),
    (lambda p: p["phases"][2].update(live_argv=[["adb", "shell", "su"]]), "privileged phases"),
    (lambda p: p["phases"][1]["commands"].append(
        ["adb", "-s", "<private-approved-serial>", "shell", "cat", "/proc/42/mem"]),
        "forbidden operation token"),
    (lambda p: p["phases"][1]["commands"].append(
        ["adb", "-s", "<private-approved-serial>", "shell", "id; su -c id"]),
        "forbidden operation token"),
    (lambda p: p["execution_bounds_proposal"].update(max_command_timeout_seconds=11),
        "session/command bound"),
    (lambda p: p["phases"][4].update(per_command_timeout_seconds=11),
        "per-command limits"),
    (lambda p: p["phases"][4].update(capture_during_transition=True),
        "capture during UI transitions"),
    (lambda p: p["phases"][4]["states"].pop(), "required observation state sequence"),
    (lambda p: p["phases"][4].update(commands_apply_at_each_steady_state=False),
        "every CarPlay steady state"),
    (lambda p: p["phases"][4]["states"].remove("navigation_selected_after_reconnect"),
        "required observation state sequence"),
    (lambda p: p["execution_bounds_proposal"].update(max_session_output_bytes=1),
        "session/command bound"),
    (lambda p: p["execution_bounds_proposal"].update(max_campaign_command_output_bytes=1),
        "aggregate time/storage calculations"),
    (lambda p: p["execution_bounds_proposal"].update(max_bounded_elapsed_seconds=3600),
        "aggregate time/storage calculations"),
])
def test_validator_rejects_scope_or_command_drift(mutate, message):
    proposal = copy.deepcopy(load_proposal())
    mutate(proposal)
    with pytest.raises(ValueError, match=message):
        validator.validate_proposal(proposal)


def test_validator_rejects_unknown_argv_operation():
    proposal = load_proposal()
    proposal["phases"][1]["commands"].append(
        ["adb", "-s", "<private-approved-serial>", "shell", "cat", "/etc/passwd"])
    with pytest.raises(ValueError, match="outside the fixed read-only allowlist"):
        validator.validate_proposal(proposal)


def test_validator_scans_commands_under_unexpected_keys_and_string_values():
    proposal = load_proposal()
    proposal["phases"][1]["future_operations"] = [
        ["adb", "-s", "<private-approved-serial>", "shell", "su", "-c", "id"]]
    with pytest.raises(ValueError, match="fields outside the fixed schema"):
        validator.validate_proposal(proposal)
    proposal = load_proposal()
    proposal["post_session_instrumentation"]["command_text"] = "adb shell su -c id"
    with pytest.raises(ValueError, match="post_session_instrumentation fields differ"):
        validator.validate_proposal(proposal)
    with pytest.raises(ValueError, match="command strings are forbidden"):
        validator._commands_in({"command_text": "adb shell su -c id"})


def test_command_scanner_finds_nonstandard_launchers_under_unknown_keys():
    commands = validator._commands_in({"unreviewed": [["python", "-c", "print(1)"],
                                                         ["/opt/tools/custom", "--read"]]})
    assert len(commands) == 2
    for path, argv in commands:
        with pytest.raises(ValueError):
            validator._validate_argv(path, argv)


def test_strict_nested_schema_rejects_unreviewed_command_fields():
    proposal = load_proposal()
    proposal["post_session_instrumentation"]["extra_shell"] = ["sh", "-c", "id"]
    with pytest.raises(ValueError, match="post_session_instrumentation fields differ"):
        validator.validate_proposal(proposal)


@pytest.mark.parametrize("argv", [
    ["/system/xbin/su", "-c", "id"],
    ["sh", "-c", "id"],
    ["adb", "-s", 42, "shell", "id"],
])
def test_validator_rejects_launcher_aliases_and_malformed_argv(argv):
    proposal = load_proposal()
    proposal["phases"][1]["commands"].append(argv)
    with pytest.raises(ValueError):
        validator.validate_proposal(proposal)


def test_phase1_identity_validation_precedes_every_diagnostic():
    proposal = load_proposal()
    commands = proposal["phases"][1]["commands"]
    commands[0], commands[1] = commands[1], commands[0]
    with pytest.raises(ValueError, match="fixed identity and baseline factory package/service inventory"):
        validator.validate_proposal(proposal)


def test_validator_rejects_network_reads_outside_carplay_phase():
    proposal = load_proposal()
    proposal["phases"][1]["commands"].append(
        ["adb", "-s", "<private-approved-serial>", "shell", "cat", "/proc/net/tcp"])
    with pytest.raises(ValueError, match="network observations are restricted"):
        validator.validate_proposal(proposal)


def test_validator_handles_malformed_phase_without_traceback():
    proposal = load_proposal()
    proposal["phases"][0] = None
    with pytest.raises(ValueError, match="exact ordered six-phase"):
        validator.validate_proposal(proposal)
