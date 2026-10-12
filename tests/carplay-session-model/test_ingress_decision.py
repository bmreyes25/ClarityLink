"""P1-C5 offline evidence gates; all fixtures are synthetic and device-free."""

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/carplay-session-model/ingress_decision.py"
MANIFEST = ROOT / "research/architecture/p1c5-ingress-decision.json"
spec = importlib.util.spec_from_file_location("ingress_decision", SOURCE)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def manifest():
    return json.loads(MANIFEST.read_text())


def evaluate(data=None):
    return {result.candidate: result for result in module.evaluate_manifest(data or manifest(), ROOT)}


def test_current_reviewed_manifest_has_no_deployable_or_supported_ingress():
    results = evaluate()
    assert set(results) == set("ABCDEFG")
    assert all(not x.deployment_eligible and not x.supported_for_implementation and
               not x.original_goal_validated for x in results.values())
    assert results["F"].classification is module.DecisionClass.LAB_ONLY_ORACLE
    assert results["A"].model_consistency == "MODEL_ONLY_CONSISTENT"
    assert not results["A"].interface_evidence_sufficient


def test_all_synthetic_gates_claimed_proven_cannot_authorize():
    data = manifest()
    data["kind"] = "SYNTHETIC_FIXTURE"
    for gate in data["candidates"]["A"]["gates"].values():
        gate["status"] = "PROVEN"
    data["candidates"]["A"]["live_validation_status"] = "HONDA_AUTHENTICATED_SESSION_VERIFIED"
    result = evaluate(data)["A"]
    assert not result.deployment_eligible and not result.interface_evidence_sufficient
    assert "synthetic_manifest_cannot_authorize" in result.reasons
    assert any("self_attested_proof" in x for x in result.reasons)


@pytest.mark.parametrize("gate,meaning", [
    ("A", "source"), ("B", "interface"), ("C", "authentication"),
    ("D", "session"), ("E", "permission"), ("H", "cleanup"),
    ("I", "API17"), ("K", "no APK"),
])
def test_missing_mandatory_gate_blocks_deployment(gate, meaning):
    result = evaluate()["A"]
    assert gate in result.blocking_gates, meaning
    assert not result.deployment_eligible


@pytest.mark.parametrize("field,owner_value,expected", [
    ("usb_owners", ["Honda", "ClarityLink"], "conflicting_usb_owner"),
    ("iap2_owners", ["Honda", "ClarityLink"], "conflicting_iap2_owner"),
    ("auth_owners", ["Honda", "ClarityLink"], "conflicting_accessory_identity"),
    ("primary_owners", ["ClarityLink"], "stock_type110_not_preserved"),
])
def test_ownership_conflicts_cannot_be_hidden_by_model_label(field, owner_value, expected):
    data = manifest()
    claim = data["candidates"]["A"]["ownership_claim"]
    claim[field] = owner_value
    with pytest.raises(module.DecisionError, match="model_result_mismatch"):
        evaluate(data)
    data["candidates"]["A"]["model_consistency"] = "MODEL_CONFLICT"
    result = evaluate(data)["A"]
    assert "ownership_model_conflict" in result.reasons
    assert not result.deployment_eligible


def test_type111_setup_cannot_be_promoted_by_status_flag():
    data = manifest()
    data["candidates"]["A"]["gates"]["B"]["status"] = "PROVEN"
    result = evaluate(data)["A"]
    assert "gate_B_self_attested_proof" in result.reasons
    assert not result.interface_evidence_sufficient


def test_wireless_coexistence_needs_apple_admission_not_a_symbolic_model():
    result = evaluate()["E"]
    assert result.model_consistency == "MODEL_ONLY_CONSISTENT"
    assert not result.interface_evidence_sufficient and not result.deployment_eligible


def test_status_only_binder_does_not_prove_guidance():
    result = evaluate()["B"]
    assert "A" in result.blocking_gates and "B" in result.blocking_gates
    assert not result.original_goal_validated


@pytest.mark.parametrize("candidate,label", [
    ("C", "ACTIVE_IPHONE_SECONDARY_VIDEO"),
    ("G", "ACTIVE_IPHONE_SECONDARY_VIDEO"),
    ("F", "ACTIVE_IPHONE_SECONDARY_VIDEO"),
])
def test_relabeling_native_companion_or_lab_data_does_not_validate_original_goal(candidate, label):
    data = manifest()
    data["candidates"][candidate]["source_authenticity"] = label
    result = evaluate(data)[candidate]
    assert not result.original_goal_validated and not result.deployment_eligible


def test_other_receiver_real_iphone_type111_is_not_honda_validation():
    result = evaluate()["F"]
    assert result.live_validation_status == "LAB_OTHER_RECEIVER_ONLY"
    assert not result.deployment_eligible


def test_emulator_success_cannot_substitute_for_honda_admission():
    data = manifest()
    data["evidence"]["EMULATOR_FIXTURE"] = {
        "category": "API17_EMULATOR_VERIFIED", "source": "tests/fixtures/example.json"
    }
    data["candidates"]["A"]["evidence_ids"].append("EMULATOR_FIXTURE")
    result = evaluate(data)["A"]
    assert "unreviewed_or_missing_evidence_reference" in result.reasons
    assert not result.deployment_eligible


def test_missing_provenance_record_fails_closed():
    data = manifest()
    del data["evidence"]["P1C2_NO_EXTENSION"]
    assert "unreviewed_or_missing_evidence_reference" in evaluate(data)["A"].reasons


def test_contradictory_evidence_cannot_match_reviewed_catalog():
    data = manifest()
    data["evidence"]["P1C2_NO_EXTENSION"]["contradictory_evidence"] = ["new unreviewed claim"]
    assert "unreviewed_or_missing_evidence_reference" in evaluate(data)["A"].reasons


def test_changed_report_digest_cannot_match_reviewed_catalog():
    data = manifest()
    data["evidence"]["P1C2_NO_EXTENSION"]["source_sha256"] = "0" * 64
    assert "unreviewed_or_missing_evidence_reference" in evaluate(data)["A"].reasons


def test_incompatible_firmware_and_stale_manifest_rejected():
    data = manifest()
    data["firmware_sha256"] = "0" * 64
    with pytest.raises(module.DecisionError, match="incompatible_firmware_identity"):
        evaluate(data)
    data = manifest()
    data["source_head"] = "older-commit"
    with pytest.raises(module.DecisionError, match="unsupported_or_stale_manifest_version"):
        evaluate(data)


def test_reclassification_without_new_evidence_is_rejected():
    data = manifest()
    data["candidates"]["C"]["gates"]["A"]["status"] = "PROVEN"
    assert "gate_A_self_attested_proof" in evaluate(data)["C"].reasons


def test_valid_conditional_architecture_reports_explicit_dependencies():
    data = manifest()
    assert data["selected_conditional_path"] == "A"
    assert data["candidates"]["A"]["remaining_dependencies"]
    result = evaluate(data)["A"]
    assert result.classification is module.DecisionClass.CONDITIONAL_MISSING_INTERFACE_PROOF
    assert result.blocking_gates and not result.deployment_eligible


def test_self_attested_deployable_path_is_rejected():
    data = manifest()
    data["currently_deployable_path"] = "A"
    with pytest.raises(module.DecisionError, match="self_attested_deployment_path"):
        evaluate(data)


def reclassify_a_for_logic_fixture(monkeypatch, data):
    monkeypatch.setattr(module, "CLASSIFICATION", {
        **module.CLASSIFICATION,
        "A": module.DecisionClass.FULLY_SUPPORTED_EXISTING_INTERFACE,
    })
    data["candidates"]["A"]["decision_classification"] = (
        module.DecisionClass.FULLY_SUPPORTED_EXISTING_INTERFACE.value
    )


@pytest.mark.parametrize("removed_gate", list("FGHIJKL"))
def test_hypothetical_reviewed_proof_keeps_interface_separate_from_safety_gates(
    monkeypatch, removed_gate
):
    # Test-only catalog patch. It is not a claim that these reports prove ingress.
    fake = frozenset({"P1C1_STOCK_OWNER"})
    monkeypatch.setattr(module, "APPROVED_POSITIVE_GATE_PROOFS",
                        {("A", gate): fake for gate in module.GATES})
    monkeypatch.setattr(module, "APPROVED_HONDA_LIVE_PROOFS", {"A": fake})
    data = manifest()
    reclassify_a_for_logic_fixture(monkeypatch, data)
    candidate = data["candidates"]["A"]
    for gate in candidate["gates"].values():
        gate["status"] = "PROVEN"
    candidate["live_validation_status"] = "HONDA_AUTHENTICATED_SESSION_VERIFIED"
    assert evaluate(data)["A"].deployment_eligible  # logic fixture only
    data["candidates"]["A"]["gates"][removed_gate]["status"] = "UNKNOWN"
    result = evaluate(data)["A"]
    assert result.interface_evidence_sufficient
    assert not result.supported_for_implementation and not result.deployment_eligible
    assert removed_gate in result.blocking_gates
    data["kind"] = "SYNTHETIC_FIXTURE"
    assert not evaluate(data)["A"].deployment_eligible


def test_hypothetical_interface_proof_without_live_validation_is_not_deployable(monkeypatch):
    fake = frozenset({"P1C1_STOCK_OWNER"})
    monkeypatch.setattr(module, "APPROVED_POSITIVE_GATE_PROOFS",
                        {("A", gate): fake for gate in module.GATES})
    data = manifest()
    reclassify_a_for_logic_fixture(monkeypatch, data)
    for gate in data["candidates"]["A"]["gates"].values():
        gate["status"] = "PROVEN"
    result = evaluate(data)["A"]
    assert result.interface_evidence_sufficient and result.supported_for_implementation
    assert not result.deployment_eligible and not result.original_goal_validated


def test_positive_gates_without_reviewed_reclassification_remain_non_deployable(monkeypatch):
    fake = frozenset({"P1C1_STOCK_OWNER"})
    monkeypatch.setattr(module, "APPROVED_POSITIVE_GATE_PROOFS",
                        {("A", gate): fake for gate in module.GATES})
    monkeypatch.setattr(module, "APPROVED_HONDA_LIVE_PROOFS", {"A": fake})
    data = manifest()
    for gate in data["candidates"]["A"]["gates"].values():
        gate["status"] = "PROVEN"
    data["candidates"]["A"]["live_validation_status"] = "HONDA_AUTHENTICATED_SESSION_VERIFIED"
    result = evaluate(data)["A"]
    assert result.interface_evidence_sufficient
    assert not result.supported_for_implementation and not result.deployment_eligible


def test_other_candidates_live_proof_cannot_be_reused(monkeypatch):
    fake = frozenset({"P1C1_STOCK_OWNER"})
    monkeypatch.setattr(module, "APPROVED_HONDA_LIVE_PROOFS", {"A": fake})
    data = manifest()
    data["candidates"]["B"]["live_validation_status"] = "HONDA_AUTHENTICATED_SESSION_VERIFIED"
    assert "honda_live_validation_not_established" in evaluate(data)["B"].reasons
