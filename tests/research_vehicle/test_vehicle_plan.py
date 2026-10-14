import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "research/vehicle"


def load(name):
    return json.loads((PLAN / name).read_text())


def test_vehicle_matrix_schema_and_required_test_fields():
    matrix = load("vehicle-test-matrix.json")
    schema = load("vehicle-test-matrix.schema.json")
    assert matrix["schema_version"] == schema["properties"]["schema_version"]["const"]
    assert matrix["repository"] == schema["properties"]["repository"]["const"]
    assert matrix["pull_request"] == schema["properties"]["pull_request"]["const"]
    assert len(matrix["starting_head"]) == 40
    assert matrix["planning_only"] is True
    assert matrix["authorization_in_force"] is False
    candidates = matrix["candidates"]
    assert len(candidates) == 9
    assert len({row["test_id"] for row in candidates}) == len(candidates)
    required = set(schema["definitions"]["candidate"]["required"])
    for row in candidates:
        assert set(row) == required
        assert row["retry_count"] == 0
        assert row["fallback_count"] == 0
        assert row["execution_in_this_milestone"] is False
        for field in ("required_evidence", "authorization_requirements", "stop_conditions",
                      "success_criteria", "failure_criteria", "what_remains_unproven"):
            assert row[field]
        assert row["existing_artifacts"]
        for ref in row["existing_artifacts"]:
            path = ROOT / ref["path"]
            assert path.is_file(), ref["path"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == ref["sha256"], ref["path"]


def test_authorization_and_device_operation_boundaries_are_fail_closed():
    matrix = load("vehicle-test-matrix.json")
    assert matrix["authorization_in_force"] is False
    for row in matrix["candidates"]:
        assert row["execution_in_this_milestone"] is False
        assert "single-use" in " ".join(row["authorization_requirements"]).lower()
    by_id = {row["test_id"]: row for row in matrix["candidates"]}
    passive = by_id["V0-PASSIVE-BASELINE"]
    assert passive["proposed_commands"] == []
    assert passive["adb_required"] is False
    assert passive["target_write_required"] is False
    assert passive["target_execution_required"] is False
    assert passive["root_required"] is False
    assert passive["apk_install_required"] is False
    assert by_id["V3-EXACT-PATH-CLEANUP"]["proposed_commands"] == []
    assert by_id["V3-EXACT-PATH-CLEANUP"]["target_write_required"] is True
    assert by_id["V7-SEPARATE-WINDOW-ADMISSION"]["proposed_commands"] == []
    assert by_id["V7-SEPARATE-WINDOW-ADMISSION"]["apk_install_required"] is True


def test_display_command_list_is_identical_to_existing_frozen_manifest():
    matrix = load("vehicle-test-matrix.json")
    row = next(r for r in matrix["candidates"] if r["test_id"] == "V5-LOGICAL-DISPLAY-INVENTORY")
    manifest = json.loads((ROOT / "research/architecture/p2c5-display1-manifest.json").read_text())
    expected = [" ".join(command) for command in manifest["commands"]]
    assert row["proposed_commands"] == expected
    assert manifest["retries"] == 0
    assert manifest["fallbacks"] == 0
    assert manifest["target_writes"] == 0
    assert manifest["display_operations"] == 0


def test_passive_evidence_schema_rejects_unmeasured_claims_by_required_provenance():
    schema = load("passive-observation.schema.json")
    required = set(schema["required"])
    template = load("passive-observation-template.json")
    assert set(template) == required
    assert template["vehicle_stationary"] is True
    assert template["center_display"] == "not_observed"
    assert template["instrument_cluster"] == "not_observed"
    observation_fields = set(schema["definitions"]["observation"]["required"])
    assert observation_fields == {"feature", "value", "evidence_kind", "measurement_method", "uncertainty", "notes"}
    assert schema["definitions"]["observation"]["properties"]["evidence_kind"]["enum"] == [
        "DIRECTLY_MEASURED", "VISUALLY_ESTIMATED", "OPERATOR_REPORTED", "NOT_OBSERVED"
    ]
