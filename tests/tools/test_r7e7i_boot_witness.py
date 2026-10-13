from __future__ import annotations

import hashlib
import json
import uuid

import pytest

from tools.r7e7i_boot_witness import BootWitnessError, evaluate
from tools.r7e7i_boot_witness import main


def evidence() -> dict[str, object]:
    receipts = {name: hashlib.sha256(name.encode()).hexdigest()
                for name in ("baseline", "later", "ordering", "invocation_relation")}
    return {
        "schema_version": "R7E7I-BOOT-WITNESS-1",
        "source_kind": "SYNTHETIC_FIXTURE",
        "observations": [
            {"label": "baseline", "target": target(), "boot_id": str(uuid.uuid4())},
            {"label": "later", "target": target(), "boot_id": str(uuid.uuid4())},
        ],
        "receipts": receipts,
        "receipt_manifest_sha256": hashlib.sha256(
            json.dumps(receipts, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "kernel_capability": "VERIFIED_FOR_EXACT_HONDA_BUILD",
        "observation_order_verified": True,
        "observation_sequence": [1, 2],
        "invocation_before_baseline_verified": True,
        "historical_timestamp_used": False,
        "review_status": "INDEPENDENT_REVIEW_PASSED",
        "current_references": "CURRENT_REFERENCES_UNKNOWN",
        "relaunch_audit": "UNRESOLVED_EXTERNAL_RELAUNCH_PATH",
        "file_identity": "UNKNOWN",
    }


def target() -> dict[str, str]:
    return {"adb_serial": "fixture-serial", "hardware_id": "fixture-hardware",
            "build_fingerprint": "fixture/vendor/device:4.2.2/fixture/eng"}


def test_different_boot_ids_model_candidate_but_never_authenticate_real_evidence():
    row = evidence()
    result = evaluate(row)
    assert result["decision"] == "MODEL_ONLY_HISTORICAL_INVOCATION_TERMINATED_CANDIDATE"
    assert result["historical_invocation"] == "MODEL_ONLY_HISTORICAL_INVOCATION_TERMINATED"
    assert result["cleanup_authorized"] is False
    assert result["test_a_authorized"] is False


def test_same_boot_id_does_not_establish_later_kernel_boot():
    row = evidence()
    row["observations"][1]["boot_id"] = row["observations"][0]["boot_id"]
    assert evaluate(row)["decision"] == "MODEL_ONLY_BOOT_CONTINUITY_NO_LATER_KERNEL_BOOT"


@pytest.mark.parametrize("mutate", [
    lambda r: r["observations"][0].update(target=target() | {"adb_serial": "other"}),
    lambda r: r["observations"][1].update(boot_id="not-a-uuid"),
    lambda r: r.update(source_kind="LIVE_READ_ONLY_RECEIPT"),
    lambda r: r["receipts"].update(later="z" * 64),
    lambda r: r.update(observation_sequence=[2, 1]),
    lambda r: r.update(kernel_capability="UNKNOWN"),
    lambda r: r.update(review_status="NOT_REVIEWED"),
    lambda r: r.update(invocation_before_baseline_verified=False),
    lambda r: r.update(observation_order_verified=False),
    lambda r: r["observations"][1].update(target=target() | {"hardware_id": "other-device"}),
])
def test_each_missing_or_conflicting_gate_fails_closed(mutate):
    row = evidence()
    mutate(row)
    result = evaluate(row)
    assert result["cleanup_authorized"] is False
    assert result["test_a_authorized"] is False
    assert result["phase_c"] == "PHASE_C_NOT_AUTHORIZED"
    assert result["test_a"] == "TEST_A_BLOCKED"
    assert result["historical_invocation"] != "MODEL_ONLY_HISTORICAL_INVOCATION_TERMINATED" or row["source_kind"] == "SYNTHETIC_FIXTURE"


def test_missing_baseline_and_wrong_observation_labels_fail_closed():
    row = evidence()
    row["observations"][0]["label"] = "later"
    with pytest.raises(BootWitnessError):
        evaluate(row)


def test_missing_baseline_observation_fails_closed():
    row = evidence()
    row["observations"].pop(0)
    with pytest.raises(BootWitnessError):
        evaluate(row)


def test_synthetic_is_always_model_only_even_when_every_fixture_gate_passes():
    assert evaluate(evidence())["decision"].startswith("MODEL_ONLY_")


def test_receipt_manifest_detects_changed_receipt_bytes_digest():
    row = evidence()
    row["receipts"]["later"] = hashlib.sha256(b"changed receipt").hexdigest()
    result = evaluate(row)
    assert result["receipt_sha256"] == {}
    assert result["historical_invocation"] == "NOT_ESTABLISHED"


def test_historical_timestamps_cannot_support_route():
    row = evidence()
    row["historical_timestamp_used"] = True
    assert evaluate(row)["historical_invocation"] == "NOT_ESTABLISHED"


def test_relaunch_after_reboot_remains_independent_and_blocks_cleanup():
    row = evidence()
    row["relaunch_audit"] = "PROJECT_PERSISTENCE_FOUND"
    result = evaluate(row)
    assert result["historical_invocation"] == "MODEL_ONLY_HISTORICAL_INVOCATION_TERMINATED"
    assert result["relaunch_audit"] == "PROJECT_PERSISTENCE_FOUND"
    assert result["phase_c"] == "PHASE_C_NOT_AUTHORIZED"


def test_current_executable_reference_present_does_not_change_boot_fact_or_authorize():
    row = evidence()
    row["current_references"] = "CURRENT_REFERENCES_PRESENT"
    result = evaluate(row)
    assert result["historical_invocation"] == "MODEL_ONLY_HISTORICAL_INVOCATION_TERMINATED"
    assert result["current_references"] == "CURRENT_REFERENCES_PRESENT"
    assert result["cleanup_authorized"] is False


def test_visibility_incomplete_stays_unknown():
    row = evidence()
    row["current_references"] = "VISIBILITY_INCOMPLETE"
    assert evaluate(row)["current_references"] == "CURRENT_REFERENCES_UNKNOWN"


def test_old_file_still_present_after_boot_does_not_affect_historical_termination():
    row = evidence()
    row["file_identity"] = "VERIFIED"
    result = evaluate(row)
    assert result["historical_invocation"] == "MODEL_ONLY_HISTORICAL_INVOCATION_TERMINATED"
    assert result["file_identity"] == "VERIFIED"
    assert result["phase_c"] == "PHASE_C_NOT_AUTHORIZED"


def test_cleanup_without_authorization_is_never_enabled():
    row = evidence()
    row["cleanup_authorization"] = "APPROVED"
    assert evaluate(row)["cleanup_authorized"] is False


def test_test_a_before_recovery_does_not_become_ready():
    row = evidence()
    row["test_a_requested"] = True
    assert evaluate(row)["test_a"] == "TEST_A_BLOCKED"


def test_unknown_target_provenance_is_rejected():
    row = evidence()
    row["observations"][0]["target"] = {"adb_serial": "UNKNOWN", "hardware_id": "x",
                                          "build_fingerprint": "x"}
    result = evaluate(row)
    assert result["historical_invocation"] == "NOT_ESTABLISHED"


def test_unknown_schema_rejected():
    with pytest.raises(BootWitnessError):
        evaluate({"schema_version": "future"})


def test_json_cli_parses_fixture_without_device_access(tmp_path, capsys):
    path = tmp_path / "synthetic.json"
    path.write_text(json.dumps(evidence()))
    assert main([str(path)]) == 0
    assert '"source_kind": "SYNTHETIC_FIXTURE"' in capsys.readouterr().out


def test_unhashable_source_type_is_rejected():
    row = evidence()
    row["source_kind"] = []
    with pytest.raises(BootWitnessError):
        evaluate(row)
