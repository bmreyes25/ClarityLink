"""Offline, default-deny P1-C5 ingress decision tool; never opens a device.

The reviewed catalog is deliberately closed at this milestone. A new positive
interface or live proof requires a reviewed code/catalog update, not a JSON flag.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from hashlib import sha256
import importlib.util
from pathlib import Path
import sys
from typing import Any, Mapping


VERSION = "P1C5-INGRESS-DECISION-1"
SOURCE_HEAD = "dc5d045bfacfcd5bc21b83d822f71b4f4c75df9e"
HONDA_JMCS_SHA256 = "cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232"
GATES = tuple("ABCDEFGHIJKL")
CANDIDATES = tuple("ABCDEFG")


class EvidenceCategory(str, Enum):
    HONDA_STATIC_VERIFIED = "HONDA_STATIC_VERIFIED"
    HONDA_LIVE_READ_ONLY_VERIFIED = "HONDA_LIVE_READ_ONLY_VERIFIED"
    REAL_IPHONE_LAB_VERIFIED = "REAL_IPHONE_LAB_VERIFIED"
    API17_EMULATOR_VERIFIED = "API17_EMULATOR_VERIFIED"
    HOST_SIMULATION_ONLY = "HOST_SIMULATION_ONLY"
    OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION"
    EXTERNAL_PRIOR_ART = "EXTERNAL_PRIOR_ART"
    HYPOTHESIS = "HYPOTHESIS"
    UNKNOWN = "UNKNOWN"


class GateStatus(str, Enum):
    PROVEN = "PROVEN"
    CONDITIONAL = "CONDITIONAL"
    UNKNOWN = "UNKNOWN"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DecisionClass(str, Enum):
    FULLY_SUPPORTED_EXISTING_INTERFACE = "FULLY_SUPPORTED_EXISTING_INTERFACE"
    FEASIBLE_NEW_USER_SPACE = "FEASIBLE_NEW_USER_SPACE"
    ADDITIONAL_APPROVED_DATA_PATH_REQUIRED = "ADDITIONAL_APPROVED_DATA_PATH_REQUIRED"
    CONDITIONAL_MISSING_INTERFACE_PROOF = "CONDITIONAL_MISSING_INTERFACE_PROOF"
    LAB_ONLY_ORACLE = "LAB_ONLY_ORACLE"
    PROHIBITED_STOCK_MODIFICATION_REQUIRED = "PROHIBITED_STOCK_MODIFICATION_REQUIRED"
    UNSUPPORTED_OR_NO_EVIDENCE = "UNSUPPORTED_OR_NO_EVIDENCE"


class DecisionError(ValueError):
    pass


@dataclass(frozen=True)
class DecisionResult:
    candidate: str
    model_consistency: str
    interface_evidence_sufficient: bool
    live_validation_status: str
    deployment_eligible: bool
    supported_for_implementation: bool
    original_goal_validated: bool
    classification: DecisionClass
    blocking_gates: tuple[str, ...]
    reasons: tuple[str, ...]


# These exact reviewed records support bounded claims only. None proves a
# deployable ingress or live Honda coexistence. Source paths are repository-local.
REVIEWED_CATALOG: Mapping[str, Mapping[str, Any]] = {
    "P1C1_STOCK_OWNER": {
        "category": "HONDA_STATIC_VERIFIED", "source": "research/architecture/p1c1-stock-session-ownership.md",
        "source_sha256": "eff11a939c6de73b87c9f12487afed45b06e095b8c9df5a96889e5b9c819424d",
        "artifact_sha256": HONDA_JMCS_SHA256, "verification_method": "hash-matched static callgraph review",
        "supported_claim": "stock session and Type110 ownership", "scope": "2018 Clarity preserved jmcs only",
        "version": "P1-C1", "independent_review": "PASSED", "contradictory_evidence": [],
        "unresolved_conditions": ["external session delegation not established"],
    },
    "P1C2_NO_EXTENSION": {
        "category": "HONDA_STATIC_VERIFIED", "source": "research/architecture/p1c2-jmcs-additive-extension-audit.md",
        "source_sha256": "63dd65b809065d231c1be18ed40839f7bbbad076ab7e0a3fc740f2439a62a498",
        "artifact_sha256": HONDA_JMCS_SHA256, "verification_method": "hash-matched jmcs/proxy ABI and callsite audit",
        "supported_claim": "no supported Type111 seam in reviewed artifacts", "scope": "reviewed firmware only",
        "version": "P1-C2", "independent_review": "PASSED", "contradictory_evidence": [],
        "unresolved_conditions": ["new provenance-verified artifact could change conclusion"],
    },
    "P1C3_STATUS_ONLY": {
        "category": "HONDA_STATIC_VERIFIED", "source": "research/architecture/p1c3-iap2-route-guidance-ingress.md",
        "source_sha256": "03c9807fd1a5cd5c8bdc0d00b3c18c724c2b1addfb929067e7b79e14a25a5585",
        "artifact_sha256": None, "verification_method": "decompiled Binder producer/consumer and hash-matched jmcs ingress audit",
        "supported_claim": "reviewed CarPlay Binder callback is status-only", "scope": "decompiled APK source; original APK hash unavailable; jmcs separately hash-matched",
        "version": "P1-C3", "independent_review": "PASSED", "contradictory_evidence": [],
        "unresolved_conditions": ["actual route-guidance ingress and caller admission unknown"],
    },
    "P1C4_COEXISTENCE_UNKNOWN": {
        "category": "HOST_SIMULATION_ONLY", "source": "research/architecture/p1c4-independent-receiver-coexistence.md",
        "source_sha256": "ff12468bda1e85bebf679fce56143b11fcf42036cb79ff346531263584557b3a",
        "artifact_sha256": None, "verification_method": "offline topology and ownership review",
        "supported_claim": "coexistence not established", "scope": "architecture model; no iPhone or Honda session",
        "version": "P1-C4", "independent_review": "PASSED", "contradictory_evidence": [],
        "unresolved_conditions": ["session admission and Honda delegation unproven"],
    },
    "PLAYPORT_43P_LAB": {
        "category": "REAL_IPHONE_LAB_VERIFIED", "source": "research/lab/current-ios-type111-observation.md",
        "source_sha256": "d3186da461eaec1c166a4159a4f94a0cf4cda5c89b61c1a54ea050e38b301ad9",
        "artifact_sha256": None, "verification_method": "sanitized PlayPort lab session review",
        "supported_claim": "one experimental receiver handled two streams", "scope": "PlayPort profile only; no Honda coexistence",
        "version": "43P", "independent_review": "PASSED", "contradictory_evidence": [],
        "unresolved_conditions": ["ClarityLink/Honda interoperability not tested"],
    },
}

# Deliberately empty: positive gate claims cannot be self-attested by an input
# manifest. Future additions need an independently reviewed catalog change.
APPROVED_POSITIVE_GATE_PROOFS: Mapping[tuple[str, str], frozenset[str]] = {}
APPROVED_HONDA_LIVE_PROOFS: Mapping[str, frozenset[str]] = {}
APPROVED_ACTIVE_IPHONE_SOURCE_PROOFS: Mapping[str, frozenset[str]] = {}
APPROVED_DISPLAY1_PROOFS: Mapping[str, frozenset[str]] = {}

CLASSIFICATION: Mapping[str, DecisionClass] = {
    "A": DecisionClass.CONDITIONAL_MISSING_INTERFACE_PROOF,
    "B": DecisionClass.CONDITIONAL_MISSING_INTERFACE_PROOF,
    "C": DecisionClass.UNSUPPORTED_OR_NO_EVIDENCE,
    "D": DecisionClass.UNSUPPORTED_OR_NO_EVIDENCE,
    "E": DecisionClass.UNSUPPORTED_OR_NO_EVIDENCE,
    "F": DecisionClass.LAB_ONLY_ORACLE,
    "G": DecisionClass.ADDITIONAL_APPROVED_DATA_PATH_REQUIRED,
}
IMPLEMENTABLE_CLASSES = frozenset({
    DecisionClass.FULLY_SUPPORTED_EXISTING_INTERFACE,
    DecisionClass.FEASIBLE_NEW_USER_SPACE,
})


def _require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DecisionError(f"{label} must be an object")
    return value


@lru_cache(maxsize=1)
def _ownership_module() -> Any:
    """Load the existing sibling model without making a second owner validator."""
    module_path = Path(__file__).with_name("receiver_ownership.py")
    spec = importlib.util.spec_from_file_location("_claritylink_decision_ownership", module_path)
    if spec is None or spec.loader is None:
        raise DecisionError("ownership_model_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _model_result(raw_claim: Any) -> str:
    if raw_claim is None:
        return "UNASSESSED"
    claim = _require_dict(raw_claim, "ownership_claim")
    model = _ownership_module()
    values = dict(claim)
    for key in ("usb_owners", "iap2_owners", "auth_owners", "control_owners", "primary_owners"):
        if key in values:
            if not isinstance(values[key], list) or any(not isinstance(x, str) for x in values[key]):
                raise DecisionError(f"invalid_{key}")
            values[key] = frozenset(values[key])
    try:
        values["topology"] = model.Topology(values["topology"])
        ownership = model.OwnershipClaim(**values)
    except (KeyError, TypeError, ValueError) as exc:
        raise DecisionError("invalid_ownership_claim") from exc
    return "MODEL_CONFLICT" if model.validate_claim(ownership) else "MODEL_ONLY_CONSISTENT"


def evaluate_manifest(manifest: Mapping[str, Any], repo_root: Path) -> tuple[DecisionResult, ...]:
    """Evaluate a versioned record; invalid inputs fail closed with DecisionError."""
    doc = _require_dict(manifest, "manifest")
    if doc.get("version") != VERSION or doc.get("source_head") != SOURCE_HEAD:
        raise DecisionError("unsupported_or_stale_manifest_version")
    if doc.get("firmware_sha256") != HONDA_JMCS_SHA256:
        raise DecisionError("incompatible_firmware_identity")
    if doc.get("kind") not in ("REVIEWED_OFFLINE", "SYNTHETIC_FIXTURE"):
        raise DecisionError("unknown_manifest_kind")
    if doc.get("currently_deployable_path") != "NONE":
        raise DecisionError("self_attested_deployment_path")
    evidence = _require_dict(doc.get("evidence"), "evidence")
    accepted: set[str] = set()
    for evidence_id, record in evidence.items():
        expected = REVIEWED_CATALOG.get(evidence_id)
        if expected is not None and record == expected:
            source = repo_root / expected["source"]
            if source.is_file() and sha256(source.read_bytes()).hexdigest() == expected["source_sha256"]:
                accepted.add(evidence_id)
    candidates = _require_dict(doc.get("candidates"), "candidates")
    if set(candidates) != set(CANDIDATES):
        raise DecisionError("candidate_set_mismatch")
    results: list[DecisionResult] = []
    for candidate_id in CANDIDATES:
        candidate = _require_dict(candidates[candidate_id], f"candidate_{candidate_id}")
        if candidate.get("decision_classification") != CLASSIFICATION[candidate_id].value:
            raise DecisionError(f"classification_mismatch_{candidate_id}")
        gates = _require_dict(candidate.get("gates"), f"gates_{candidate_id}")
        if set(gates) != set(GATES):
            raise DecisionError(f"gate_set_mismatch_{candidate_id}")
        model = _model_result(candidate.get("ownership_claim"))
        if candidate.get("model_consistency") != model:
            raise DecisionError(f"model_result_mismatch_{candidate_id}")
        live = candidate.get("live_validation_status")
        if live not in ("NOT_RUN", "LAB_OTHER_RECEIVER_ONLY", "HONDA_AUTHENTICATED_SESSION_VERIFIED"):
            raise DecisionError(f"invalid_live_status_{candidate_id}")
        references = candidate.get("evidence_ids")
        if not isinstance(references, list) or any(not isinstance(x, str) for x in references):
            raise DecisionError(f"invalid_evidence_references_{candidate_id}")
        reasons: list[str] = []
        if not set(references) <= accepted:
            reasons.append("unreviewed_or_missing_evidence_reference")
        blocking: list[str] = []
        all_proven = True
        for gate_id in GATES:
            gate = _require_dict(gates[gate_id], f"gate_{candidate_id}_{gate_id}")
            try:
                status = GateStatus(gate.get("status"))
            except (ValueError, TypeError) as exc:
                raise DecisionError(f"invalid_gate_status_{candidate_id}_{gate_id}") from exc
            ids = gate.get("evidence_ids")
            if not isinstance(ids, list) or any(not isinstance(x, str) for x in ids):
                raise DecisionError(f"invalid_gate_refs_{candidate_id}_{gate_id}")
            if not set(ids) <= set(references):
                reasons.append(f"gate_{gate_id}_unlisted_reference")
            approved = APPROVED_POSITIVE_GATE_PROOFS.get((candidate_id, gate_id), frozenset())
            positive_proof = bool(approved) and approved <= set(ids) and approved <= accepted
            if status is GateStatus.PROVEN and not positive_proof:
                reasons.append(f"gate_{gate_id}_self_attested_proof")
            if status is not GateStatus.PROVEN or not positive_proof:
                all_proven = False
                blocking.append(gate_id)
        if model == "MODEL_CONFLICT":
            reasons.append("ownership_model_conflict")
        if doc["kind"] == "SYNTHETIC_FIXTURE":
            reasons.append("synthetic_manifest_cannot_authorize")
        interface_reasons = tuple(reasons)
        approved_live = APPROVED_HONDA_LIVE_PROOFS.get(candidate_id, frozenset())
        live_proof = (
            bool(approved_live) and approved_live <= accepted and
            approved_live <= set(references) and
            live == "HONDA_AUTHENTICATED_SESSION_VERIFIED"
        )
        if not live_proof:
            reasons.append("honda_live_validation_not_established")
        def proven(gate_id: str) -> bool:
            proof = APPROVED_POSITIVE_GATE_PROOFS.get((candidate_id, gate_id), frozenset())
            return (
                gates[gate_id]["status"] == "PROVEN" and bool(proof) and
                proof <= set(gates[gate_id]["evidence_ids"]) and proof <= accepted
            )

        interface_sufficient = doc["kind"] == "REVIEWED_OFFLINE" and all(
            proven(g) for g in "ABCDE"
        ) and not any(
            "unreviewed" in reason or "unlisted" in reason or "self_attested" in reason
            for reason in interface_reasons
        )
        implementation_supported = (
            interface_sufficient and all(proven(g) for g in "FGHIJKL") and
            model == "MODEL_ONLY_CONSISTENT" and not interface_reasons and
            CLASSIFICATION[candidate_id] in IMPLEMENTABLE_CLASSES
        )
        deployable = (
            doc["kind"] == "REVIEWED_OFFLINE" and all_proven and live_proof and
            model == "MODEL_ONLY_CONSISTENT" and not reasons and
            CLASSIFICATION[candidate_id] in IMPLEMENTABLE_CLASSES
        )
        active_source_proof = APPROVED_ACTIVE_IPHONE_SOURCE_PROOFS.get(candidate_id, frozenset())
        display_proof = APPROVED_DISPLAY1_PROOFS.get(candidate_id, frozenset())
        original_goal = (
            deployable and candidate.get("source_authenticity") == "ACTIVE_IPHONE_SECONDARY_VIDEO" and
            bool(active_source_proof) and active_source_proof <= accepted and
            active_source_proof <= set(references) and
            bool(display_proof) and display_proof <= accepted and display_proof <= set(references)
        )
        results.append(DecisionResult(
            candidate=candidate_id, model_consistency=model,
            interface_evidence_sufficient=interface_sufficient,
            live_validation_status=live, deployment_eligible=deployable,
            supported_for_implementation=implementation_supported,
            original_goal_validated=original_goal,
            classification=CLASSIFICATION[candidate_id], blocking_gates=tuple(blocking),
            reasons=tuple(dict.fromkeys(reasons)),
        ))
    return tuple(results)
