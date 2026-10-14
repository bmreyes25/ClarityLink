#!/usr/bin/env python3
"""Offline model for a prospective, receipt-bound kernel boot witness.

This module never contacts ADB or a target. Its output is a model result only;
it cannot authenticate signatures, provenance, a reviewer, or authorize action.
"""
from __future__ import annotations

import hashlib
import argparse
import json
import re
import sys
import uuid
from pathlib import Path

SCHEMA = "R7E7I-BOOT-WITNESS-1"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
REQUIRED_RECEIPTS = {"baseline", "later", "ordering", "invocation_relation"}


class BootWitnessError(ValueError):
    """Malformed boot-witness input."""


def _valid_boot_id(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    # Linux generates an RFC 4122 random UUID; canonical spelling is required.
    return str(parsed) == value and parsed.version == 4 and parsed.int != 0


def _receipts_valid(receipts: object) -> bool:
    return (isinstance(receipts, dict) and set(receipts) == REQUIRED_RECEIPTS
            and all(isinstance(v, str) and SHA256.fullmatch(v) for v in receipts.values()))


def _receipt_manifest_valid(evidence: dict[str, object]) -> bool:
    receipts = evidence.get("receipts")
    declared = evidence.get("receipt_manifest_sha256")
    if not _receipts_valid(receipts) or not isinstance(declared, str) or not SHA256.fullmatch(declared):
        return False
    canonical = json.dumps(receipts, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest() == declared


def _identity_valid(identity: object) -> bool:
    return (isinstance(identity, dict)
            and set(identity) == {"adb_serial", "hardware_id", "build_fingerprint"}
            and all(isinstance(identity[k], str) and identity[k].strip()
                    and not identity[k].startswith(("<", "SYNTHETIC", "UNKNOWN"))
                    for k in identity))


def evaluate(evidence: dict[str, object]) -> dict[str, object]:
    """Evaluate structure and logic; never upgrade unverified evidence to fact.

    `observation_order_verified` and `invocation_before_baseline_verified` are
    reviewer assertions in this model, not cryptographic checks. The result
    always remains MODEL_ONLY or REVIEW_REQUIRED.
    """
    if not isinstance(evidence, dict) or evidence.get("schema_version") != SCHEMA:
        raise BootWitnessError("unsupported boot-witness schema")
    source = evidence.get("source_kind")
    if not isinstance(source, str) or source not in {"SYNTHETIC_FIXTURE", "PRESERVED_RECEIPT", "LIVE_READ_ONLY_RECEIPT"}:
        raise BootWitnessError("invalid source_kind")
    observations = evidence.get("observations")
    if not isinstance(observations, list) or len(observations) != 2:
        raise BootWitnessError("exactly baseline and later observations are required")
    a, b = observations
    if not all(isinstance(row, dict) for row in observations):
        raise BootWitnessError("observation must be an object")
    if [row.get("label") for row in observations] != ["baseline", "later"]:
        raise BootWitnessError("observations must be ordered baseline then later")

    reasons: list[str] = []
    decision = "BOOT_WITNESS_CANDIDATE_BLOCKED"
    same_target = (_identity_valid(a.get("target")) and _identity_valid(b.get("target"))
                   and a["target"] == b["target"])
    if not same_target:
        reasons.append("Target identity is missing, malformed, or differs between observations.")
    ids_valid = _valid_boot_id(a.get("boot_id")) and _valid_boot_id(b.get("boot_id"))
    if not ids_valid:
        reasons.append("Both boot IDs must be canonical Linux UUIDv4 values.")
    if not _receipt_manifest_valid(evidence):
        reasons.append("Four hash-bound evidence receipts are required.")
    if evidence.get("kernel_capability") != "VERIFIED_FOR_EXACT_HONDA_BUILD":
        reasons.append("boot_id support is not verified for the exact Honda kernel build.")
    if evidence.get("observation_order_verified") is not True:
        reasons.append("Independent observation ordering is not verified.")
    if evidence.get("observation_sequence") != [1, 2]:
        reasons.append("Observation sequence must be exactly [1, 2].")
    if evidence.get("invocation_before_baseline_verified") is not True:
        reasons.append("The original invocation is not independently established before baseline A.")
    if evidence.get("historical_timestamp_used") is not False:
        reasons.append("Historical wall-clock timestamps must not support this route.")
    if evidence.get("review_status") != "INDEPENDENT_REVIEW_PASSED":
        reasons.append("Independent provenance and semantic review is missing.")

    if same_target and ids_valid and a["boot_id"] == b["boot_id"]:
        decision = "BOOT_CONTINUITY_NO_LATER_KERNEL_BOOT"
        reasons.append("The two observations report the same boot identity.")
    elif same_target and ids_valid and a["boot_id"] != b["boot_id"]:
        decision = "LATER_KERNEL_BOOT_CANDIDATE"
        reasons.append("Different boot IDs are consistent with a later kernel boot, subject to all proof gates.")

    gates = (same_target and ids_valid and a["boot_id"] != b["boot_id"]
             and _receipt_manifest_valid(evidence)
             and evidence.get("kernel_capability") == "VERIFIED_FOR_EXACT_HONDA_BUILD"
             and evidence.get("observation_order_verified") is True
             and evidence.get("observation_sequence") == [1, 2]
             and evidence.get("invocation_before_baseline_verified") is True
             and evidence.get("historical_timestamp_used") is False
             and evidence.get("review_status") == "INDEPENDENT_REVIEW_PASSED")
    if gates:
        decision = "HISTORICAL_INVOCATION_TERMINATED_CANDIDATE"
        reasons.append("All modeled gates pass; external verification is still required before factual reliance.")

    if source == "SYNTHETIC_FIXTURE":
        decision = "MODEL_ONLY_" + decision
    elif gates:
        decision = "BOOT_WITNESS_REVIEW_REQUIRED"
    elif same_target and ids_valid and a["boot_id"] == b["boot_id"]:
        decision = "BOOT_CONTINUITY_REVIEW_REQUIRED"
    elif same_target and ids_valid and a["boot_id"] != b["boot_id"]:
        decision = "LATER_KERNEL_BOOT_REVIEW_REQUIRED"
    else:
        decision = "BOOT_WITNESS_REVIEW_REQUIRED"

    # Independent subsystem decisions are intentionally never collapsed.
    references = evidence.get("current_references", "CURRENT_REFERENCES_UNKNOWN")
    allowed_references = {"CURRENT_REFERENCES_UNKNOWN", "CURRENT_REFERENCES_PRESENT",
                          "CURRENT_REFERENCES_ABSENT_WITH_COMPLETE_VISIBILITY"}
    if not isinstance(references, str) or references not in allowed_references:
        references = "CURRENT_REFERENCES_UNKNOWN"
    relaunch = evidence.get("relaunch_audit", "RELAUNCH_RISK_UNKNOWN")
    if not isinstance(relaunch, str) or relaunch not in {"NO_PROJECT_PERSISTENCE_EVIDENCED", "PROJECT_PERSISTENCE_FOUND",
                        "UNRESOLVED_EXTERNAL_RELAUNCH_PATH", "RELAUNCH_AUDIT_INCOMPLETE"}:
        relaunch = "RELAUNCH_AUDIT_INCOMPLETE"
    file_identity = evidence.get("file_identity", "UNKNOWN")
    if not isinstance(file_identity, str) or file_identity not in {"UNKNOWN", "VERIFIED", "ABSENT", "MISMATCH"}:
        file_identity = "UNKNOWN"

    return {
        "schema_version": "R7E7I-BOOT-WITNESS-DECISION-1",
        "decision": decision,
        "source_kind": source,
        "receipt_sha256": evidence.get("receipts") if _receipt_manifest_valid(evidence) else {},
        "historical_invocation": ("MODEL_ONLY_HISTORICAL_INVOCATION_TERMINATED"
                                  if gates and source == "SYNTHETIC_FIXTURE"
                                  else "REVIEW_REQUIRED" if gates else "NOT_ESTABLISHED"),
        "current_references": references,
        "relaunch_audit": relaunch,
        "file_identity": file_identity,
        "phase_c": "PHASE_C_NOT_AUTHORIZED",
        "test_a": "TEST_A_BLOCKED",
        "cleanup_authorized": False,
        "test_a_authorized": False,
        "reasons": reasons,
    }


def receipt_digest(data: bytes) -> str:
    """Convenience for fixture construction; a digest is not provenance."""
    return hashlib.sha256(data).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_json", type=Path)
    args = parser.parse_args(argv)
    try:
        evidence = json.loads(args.evidence_json.read_text())
        result = evaluate(evidence)
    except (OSError, json.JSONDecodeError, BootWitnessError) as exc:
        print(f"BOOT_WITNESS_INCONCLUSIVE: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
