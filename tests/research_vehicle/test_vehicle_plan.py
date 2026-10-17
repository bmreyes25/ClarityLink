"""Public synthetic tests for the vehicle-plan safety contract.

These fixtures contain no target commands, identifiers, or private evidence.
They verify that a proposed plan remains inert until separately authorized.
"""

import json


def synthetic_matrix():
    ids = [
        "V0-PASSIVE-BASELINE", "V1-CAPABILITY-REVIEW", "V2-SESSION-BOUNDARY",
        "V3-EXACT-PATH-CLEANUP", "V4-OUTPUT-HOST", "V5-LOGICAL-DISPLAY-INVENTORY",
        "V6-WARNING-PREEMPTION", "V7-SEPARATE-WINDOW-ADMISSION", "V8-RECOVERY",
    ]
    fields = {
        "test_id", "objective", "required_evidence", "authorization_requirements",
        "stop_conditions", "success_criteria", "failure_criteria", "what_remains_unproven",
        "existing_artifacts", "retry_count", "fallback_count", "execution_in_this_milestone",
        "proposed_commands", "adb_required", "target_write_required",
        "target_execution_required", "root_required", "apk_install_required",
    }
    candidates = []
    for test_id in ids:
        candidates.append({
            "test_id": test_id,
            "objective": "synthetic planning contract only",
            "required_evidence": ["independent review"],
            "authorization_requirements": ["separate single-use authorization"],
            "stop_conditions": ["authorization absent"],
            "success_criteria": ["no execution in this test"],
            "failure_criteria": ["any attempted execution"],
            "what_remains_unproven": ["all target-specific behavior"],
            "existing_artifacts": [{"path": "synthetic-fixture", "sha256": "0" * 64}],
            "retry_count": 0,
            "fallback_count": 0,
            "execution_in_this_milestone": False,
            "proposed_commands": [],
            "adb_required": False,
            "target_write_required": False,
            "target_execution_required": False,
            "root_required": False,
            "apk_install_required": False,
        })
        assert set(candidates[-1]) == fields
    schema = {
        "properties": {
            "schema_version": {"const": 1},
            "repository": {"const": "synthetic/public-fixture"},
            "pull_request": {"const": 0},
        },
        "definitions": {"candidate": {"required": sorted(fields)},
                        "observation": {"required": ["feature", "value", "evidence_kind",
                                                     "measurement_method", "uncertainty", "notes"],
                                        "properties": {"evidence_kind": {"enum": [
                                            "DIRECTLY_MEASURED", "VISUALLY_ESTIMATED",
                                            "OPERATOR_REPORTED", "NOT_OBSERVED"]}}}},
        "required": ["vehicle_stationary", "center_display", "instrument_cluster"],
    }
    matrix = {"schema_version": 1, "repository": "synthetic/public-fixture", "pull_request": 0,
              "starting_head": "0" * 40, "planning_only": True,
              "authorization_in_force": False, "candidates": candidates}
    template = {"vehicle_stationary": True, "center_display": "not_observed",
                "instrument_cluster": "not_observed"}
    return matrix, schema, template


def test_synthetic_vehicle_matrix_schema_and_required_fields():
    matrix, schema, _ = synthetic_matrix()
    assert matrix["schema_version"] == schema["properties"]["schema_version"]["const"]
    assert matrix["repository"] == schema["properties"]["repository"]["const"]
    assert matrix["pull_request"] == schema["properties"]["pull_request"]["const"]
    assert len(matrix["starting_head"]) == 40
    assert matrix["planning_only"] and matrix["authorization_in_force"] is False
    assert len(matrix["candidates"]) == 9
    for row in matrix["candidates"]:
        assert row["retry_count"] == row["fallback_count"] == 0
        assert row["execution_in_this_milestone"] is False
        assert row["existing_artifacts"] == [{"path": "synthetic-fixture", "sha256": "0" * 64}]


def test_synthetic_plan_has_no_device_commands_or_write_operations():
    matrix, _, _ = synthetic_matrix()
    assert matrix["authorization_in_force"] is False
    for row in matrix["candidates"]:
        assert row["execution_in_this_milestone"] is False
        assert "single-use" in " ".join(row["authorization_requirements"])
        assert row["proposed_commands"] == []
        assert row["adb_required"] is False
        assert row["target_write_required"] is False
        assert row["target_execution_required"] is False
        assert row["root_required"] is False
        assert row["apk_install_required"] is False


def test_display_and_cleanup_scenarios_remain_unexecuted():
    matrix, _, _ = synthetic_matrix()
    by_id = {row["test_id"]: row for row in matrix["candidates"]}
    assert by_id["V0-PASSIVE-BASELINE"]["proposed_commands"] == []
    assert by_id["V3-EXACT-PATH-CLEANUP"]["proposed_commands"] == []
    assert by_id["V3-EXACT-PATH-CLEANUP"]["target_write_required"] is False
    assert by_id["V7-SEPARATE-WINDOW-ADMISSION"]["proposed_commands"] == []
    assert by_id["V7-SEPARATE-WINDOW-ADMISSION"]["apk_install_required"] is False


def test_passive_observation_template_is_explicitly_unobserved():
    _, schema, template = synthetic_matrix()
    assert set(template) == set(schema["required"])
    assert template["vehicle_stationary"] is True
    assert template["center_display"] == "not_observed"
    assert template["instrument_cluster"] == "not_observed"
    observation = schema["definitions"]["observation"]
    assert set(observation["required"]) == {
        "feature", "value", "evidence_kind", "measurement_method", "uncertainty", "notes"
    }
    assert observation["properties"]["evidence_kind"]["enum"] == [
        "DIRECTLY_MEASURED", "VISUALLY_ESTIMATED", "OPERATOR_REPORTED", "NOT_OBSERVED"
    ]
