"""Fail-closed structural and evidence-completeness checks for campaign matrices."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

from verify_comprehensive_source_lock import verify_lock

OBSERVATION_STATUSES = frozenset({
    "CONFIRMED", "NOT_OBSERVED", "NOT_COLLECTED", "PERMISSION_DENIED",
    "UNSUPPORTED", "BLOCKED_PENDING_AUTHORIZATION", "FAILED", "UNRESOLVED",
})
LIVE_CATEGORIES = frozenset({
    "ordinary_unprivileged_adb", "stock_iphone_carplay_transition",
    "existing_privileged_read", "factory_navigation_observation",
    "existing_hondahack_observation", "temporary_runtime_instrumentation",
    "receiver_display_modification", "offline_historical_evidence_review",
    "host_private_evidence_handling",
})
OWNER_APPROVABLE_LIVE_CATEGORIES = frozenset({
    "ordinary_unprivileged_adb", "stock_iphone_carplay_transition",
    "factory_navigation_observation",
    "existing_hondahack_observation",
})
OFFLINE_CATEGORIES = frozenset({"offline_historical_evidence_review", "host_private_evidence_handling"})
EVIDENCE_PROVENANCE = frozenset({
    "OWNER_PRIVATE_HISTORY_REVIEWED", "PUBLIC_PROJECT_RESEARCH",
    "NON_HONDA_LAB_RESEARCH", "NO_DIRECT_CAPTURE", "HONDA_DIRECT_OBSERVATION",
    "OFFLINE_ANALYSIS_COMPLETE", "CAPTURE_INTEGRITY_VALIDATED",
})
REQUIRED_OBJECTIVE_IDS = frozenset({
    "ordinary-adb-identity", "existing-root-supersu-state",
    "jmcs-process-identity-continuity", "jmcs-maps-smaps-protections-load-bias",
    "jmcs-loaded-library-inventory", "jmcs-fd-socket-owner-correlation",
    "usb0-network-phase-correlation", "carplay-info-setup-observability",
    "type110-session-lifecycle", "type111-negotiation-and-authority",
    "display-manager-inventory", "display1-window-view-lifecycle",
    "surfaceflinger-layer-lifecycle", "factory-navigation-transitions",
    "hondahack-casting-and-withdrawal", "carplay-disconnect-reconnect-restoration",
    "recovery-prerequisites", "instrumentation-decision", "capture-integrity-and-privacy",
})
REQUIRED_OBJECTIVE_CATEGORIES = {
    "ordinary-adb-identity": frozenset({"ordinary_unprivileged_adb"}),
    "existing-root-supersu-state": frozenset({"existing_privileged_read"}),
    "jmcs-process-identity-continuity": frozenset({"ordinary_unprivileged_adb"}),
    "jmcs-maps-smaps-protections-load-bias": frozenset({"existing_privileged_read"}),
    "jmcs-loaded-library-inventory": frozenset({"existing_privileged_read"}),
    "jmcs-fd-socket-owner-correlation": frozenset({"existing_privileged_read"}),
    "usb0-network-phase-correlation": frozenset({"ordinary_unprivileged_adb", "stock_iphone_carplay_transition"}),
    "carplay-info-setup-observability": frozenset({"ordinary_unprivileged_adb", "stock_iphone_carplay_transition"}),
    "type110-session-lifecycle": frozenset({"ordinary_unprivileged_adb", "stock_iphone_carplay_transition"}),
    "type111-negotiation-and-authority": frozenset({"ordinary_unprivileged_adb", "stock_iphone_carplay_transition"}),
    "display-manager-inventory": frozenset({"ordinary_unprivileged_adb", "factory_navigation_observation"}),
    "display1-window-view-lifecycle": frozenset({"ordinary_unprivileged_adb", "factory_navigation_observation"}),
    "surfaceflinger-layer-lifecycle": frozenset({"ordinary_unprivileged_adb", "factory_navigation_observation"}),
    "factory-navigation-transitions": frozenset({"ordinary_unprivileged_adb", "factory_navigation_observation"}),
    "hondahack-casting-and-withdrawal": frozenset({
        "ordinary_unprivileged_adb", "factory_navigation_observation", "existing_hondahack_observation",
    }),
    "carplay-disconnect-reconnect-restoration": frozenset({
        "ordinary_unprivileged_adb", "stock_iphone_carplay_transition",
    }),
    "recovery-prerequisites": frozenset({"offline_historical_evidence_review"}),
    "instrumentation-decision": frozenset({"offline_historical_evidence_review"}),
    "capture-integrity-and-privacy": frozenset({"host_private_evidence_handling"}),
}
CONFIRMATION_PROVENANCE = {
    **{identifier: "HONDA_DIRECT_OBSERVATION" for identifier in REQUIRED_OBJECTIVE_IDS - {
        "recovery-prerequisites", "instrumentation-decision", "capture-integrity-and-privacy"}},
    "recovery-prerequisites": "OFFLINE_ANALYSIS_COMPLETE",
    "instrumentation-decision": "OFFLINE_ANALYSIS_COMPLETE",
    "capture-integrity-and-privacy": "CAPTURE_INTEGRITY_VALIDATED",
}
REQUIRED_FIELDS = (
    "id", "required_observation", "existing_evidence", "planned_evidence_source",
    "evidence_provenance", "evidence_refs", "prepared_collector_or_parser", "offline_test_status", "live_approval_categories",
    "live_authorization_status", "actual_observation_status", "blocker",
    "next_engineering_action", "required",
)


def evaluate_matrix(value: Any, verified_refs: set[tuple[str, str]] | None = None,
                    authorized_categories: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != "claritylink-evidence-coverage-v1":
        raise ValueError("unsupported evidence matrix schema")
    if value.get("safeForHonda") is not False:
        raise ValueError("matrix must keep safeForHonda false")
    if value.get("vehicle_deployment") != "VEHICLE_DEPLOYMENT_NOT_AUTHORIZED":
        raise ValueError("matrix must keep vehicle deployment unauthorized")
    objectives = value.get("objectives")
    if not isinstance(objectives, list) or not objectives:
        raise ValueError("matrix must contain at least one objective")
    ids: set[str] = set()
    required_confirmed = True
    dispositions_complete = True
    for index, objective in enumerate(objectives):
        if not isinstance(objective, dict):
            raise ValueError(f"objective {index} must be an object")
        missing = [field for field in REQUIRED_FIELDS if field not in objective]
        if missing:
            raise ValueError(f"objective {index} lacks fields: {', '.join(missing)}")
        identifier = objective["id"]
        if not isinstance(identifier, str) or not identifier or identifier in ids:
            raise ValueError(f"objective {index} has a missing or duplicate id")
        if identifier not in REQUIRED_OBJECTIVE_IDS:
            raise ValueError(f"objective {identifier} is not in the fixed campaign baseline")
        ids.add(identifier)
        provenance = objective["evidence_provenance"]
        if (not isinstance(provenance, list) or not provenance
                or any(not isinstance(item, str) or item not in EVIDENCE_PROVENANCE
                       for item in provenance)):
            raise ValueError(f"objective {identifier} has invalid evidence provenance")
        refs = objective["evidence_refs"]
        if not isinstance(refs, list):
            raise ValueError(f"objective {identifier} evidence_refs must be a list")
        for ref in refs:
            if (not isinstance(ref, dict) or not isinstance(ref.get("artifact_id"), str)
                    or ref.get("objective_id") != identifier
                    or not ref["artifact_id"].strip()
                    or not isinstance(ref.get("relative_path"), str) or not ref["relative_path"].strip()
                    or not isinstance(ref.get("sha256"), str)
                    or len(ref["sha256"]) != 64
                    or any(char not in "0123456789abcdef" for char in ref["sha256"])):
                raise ValueError(f"objective {identifier} has an invalid evidence reference")
            if not ref["relative_path"].startswith(f"objectives/{identifier}/"):
                raise ValueError(f"objective {identifier} evidence path is not scoped to that objective")
        categories = objective["live_approval_categories"]
        if (not isinstance(categories, list) or not categories
                or any(not isinstance(category, str) or category not in LIVE_CATEGORIES
                       for category in categories)):
            raise ValueError(f"objective {identifier} has invalid live approval categories")
        if len(categories) != len(set(categories)) or set(categories) != REQUIRED_OBJECTIVE_CATEGORIES[identifier]:
            raise ValueError(f"objective {identifier} categories differ from the fixed campaign baseline")
        status = objective["actual_observation_status"]
        if not isinstance(status, str) or status not in OBSERVATION_STATUSES:
            raise ValueError(f"objective {identifier} has an invalid observation status")
        if not isinstance(objective["required"], bool):
            raise ValueError(f"objective {identifier} required must be boolean")
        if not objective["required"]:
            raise ValueError(f"baseline objective {identifier} cannot be marked optional")
        for field in REQUIRED_FIELDS:
            if field in {"required", "evidence_provenance", "evidence_refs", "live_approval_categories"}:
                continue
            item = objective[field]
            if not isinstance(item, str) or not item.strip():
                dispositions_complete = False
        if objective["required"] and status != "CONFIRMED":
            required_confirmed = False
        if status == "CONFIRMED":
            if CONFIRMATION_PROVENANCE[identifier] not in provenance:
                raise ValueError(f"objective {identifier} lacks qualifying confirmation provenance")
            if "CAPTURE_INTEGRITY_VALIDATED" not in provenance:
                raise ValueError(f"objective {identifier} lacks verified artifact integrity provenance")
            live_auth = objective["live_authorization_status"]
            if "NO_DIRECT_CAPTURE" in provenance or not isinstance(live_auth, str):
                raise ValueError(f"objective {identifier} confirmation conflicts with its evidence or authorization")
            row_categories = set(categories)
            row_offline_only = row_categories <= OFFLINE_CATEGORIES
            expected_auth = ("OFFLINE_ANALYSIS_REVIEWED" if row_offline_only
                             else "APPROVED_EXACT_RUN")
            if live_auth != expected_auth:
                raise ValueError(f"objective {identifier} lacks the exact required authorization status")
            live_categories = row_categories - OFFLINE_CATEGORIES
            if live_categories and (authorized_categories is None
                                   or not live_categories <= authorized_categories):
                raise ValueError(f"objective {identifier} categories lack a verified authorization record")
            if not refs:
                raise ValueError(f"objective {identifier} confirmation lacks a SHA-256 evidence reference")
            for ref in refs:
                if verified_refs is None or (ref.get("relative_path"), ref.get("sha256")) not in verified_refs:
                    raise ValueError(f"objective {identifier} evidence reference is not verified in the private evidence root")
            blocker_value = objective["blocker"]
            if not isinstance(blocker_value, str) or not blocker_value.strip():
                raise ValueError(f"objective {identifier} confirmation requires an explicit blocker disposition")
        if status in {"NOT_OBSERVED", "NOT_COLLECTED", "PERMISSION_DENIED",
                      "UNSUPPORTED", "BLOCKED_PENDING_AUTHORIZATION", "FAILED", "UNRESOLVED"}:
            blocker = objective["blocker"]
            action = objective["next_engineering_action"]
            if (not isinstance(blocker, str) or not blocker.strip()
                    or not isinstance(action, str) or not action.strip()):
                dispositions_complete = False
    if ids != REQUIRED_OBJECTIVE_IDS:
        missing_ids = sorted(REQUIRED_OBJECTIVE_IDS - ids)
        extra_ids = sorted(ids - REQUIRED_OBJECTIVE_IDS)
        raise ValueError(f"objective set differs from baseline; missing={missing_ids}, extra={extra_ids}")
    return {
        "campaign_id": value.get("campaign_id"),
        "objective_count": len(objectives),
        "required_observation_count": sum(item["required"] for item in objectives),
        "evidence_classification_complete": dispositions_complete,
        "all_required_observations_confirmed": required_confirmed,
        "campaign_success": dispositions_complete and required_confirmed,
        "interpretation_rule": "NOT_OBSERVED describes only the named source and window; it never proves absence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("--structural-only", action="store_true",
                        help="validate schema/classification without claiming campaign success")
    parser.add_argument("--evidence-root", type=Path,
                        help="owner-only private evidence directory with sha256.txt; required to verify CONFIRMED rows")
    parser.add_argument("--authorization-record", type=Path,
                        help="owner-only one-run authorization record bound to this campaign and source/profile lock")
    parser.add_argument("--authorization-ledger", type=Path,
                        help="owner-only consumed-ID ledger written by the approved one-run controller")
    parser.add_argument("--run-id", help="exact campaign run ID recorded by the controller")
    args = parser.parse_args()
    try:
        matrix_raw = args.matrix.read_bytes()
        matrix = json.loads(matrix_raw)
        objectives = matrix.get("objectives") if isinstance(matrix, dict) else None
        requested_refs = {
            (ref.get("relative_path"), ref.get("sha256"))
            for row in objectives if isinstance(row, dict)
            for ref in (row.get("evidence_refs") if isinstance(row.get("evidence_refs"), list) else [])
            if isinstance(ref, dict)
            and isinstance(ref.get("relative_path"), str) and isinstance(ref.get("sha256"), str)
        } if isinstance(objectives, list) else set()
        verified_refs, evidence_manifest_sha256 = (
            _verify_evidence_root(args.evidence_root, requested_refs)
            if args.evidence_root else (None, None)
        )
        authorized_categories = None
        if args.authorization_record or args.authorization_ledger or args.run_id:
            if not (args.authorization_record and args.authorization_ledger and args.run_id
                    and args.evidence_root and evidence_manifest_sha256):
                raise ValueError("authorization validation requires record, ledger, run ID, and private evidence root")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,127}", args.run_id):
                raise ValueError("run ID must be a bounded opaque identifier")
            repo_root = Path(__file__).resolve().parents[2]
            lock_path = repo_root / "docs/diagnostics/comprehensive-source-lock.json"
            verify_lock(repo_root, lock_path)
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            authorized_categories = _verify_authorization_record(
                args.authorization_record,
                lock.get("profile", {}).get("sha256"),
                hashlib.sha256(lock_path.read_bytes()).hexdigest(),
                args.run_id,
                hashlib.sha256(matrix_raw).hexdigest(),
                evidence_manifest_sha256,
                args.authorization_ledger,
            )
        result = evaluate_matrix(matrix, verified_refs, authorized_categories)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["evidence_classification_complete"]:
        return 1
    if not args.structural_only and not result["campaign_success"]:
        return 1
    return 0


def _verify_evidence_root(root: Path, requested_refs: set[tuple[str, str]]) -> tuple[set[tuple[str, str]], str]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("evidence root must be a real private directory")
    info = root.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("evidence root must be owner-only for the current user")
    manifest = root / "sha256.txt"
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(manifest, flags)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("evidence integrity manifest must be a regular file")
        raw = stream.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("evidence integrity manifest exceeds 4 MiB")
    entries: dict[str, str] = {}
    for line in raw.decode("ascii", "replace").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise ValueError("evidence integrity manifest is malformed")
        digest, relative = match.groups()
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts or candidate.as_posix() != relative or relative in entries:
            raise ValueError("evidence integrity manifest has an unsafe or duplicate path")
        entries[relative] = digest
    verified = set()
    for relative, expected in requested_refs:
        if entries.get(relative) != expected:
            raise ValueError("evidence reference does not match the private integrity manifest")
        path = root / relative
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("evidence artifact is not a regular file")
            content = stream.read(4 * 1024 * 1024 + 1)
        if len(content) > 4 * 1024 * 1024 or hashlib.sha256(content).hexdigest() != expected:
            raise ValueError("evidence artifact exceeds its limit or fails SHA-256 validation")
        verified.add((relative, expected))
    return verified, hashlib.sha256(raw).hexdigest()


def _verify_authorization_record(path: Path, expected_profile_sha256: str,
                                 expected_source_lock_sha256: str, run_id: str,
                                 matrix_sha256: str, evidence_manifest_sha256: str,
                                 ledger_path: Path) -> set[str]:
    if path.is_symlink():
        raise ValueError("authorization record must not be a symlink")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("authorization record must be an owner-only regular file")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(record, dict)
            or record.get("schema") != "claritylink-comprehensive-owner-authorization-v1"
            or record.get("campaign_id") != "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031"
            or record.get("approval_status") != "PASS"
            or record.get("single_run") is not True
            or record.get("profile_sha256") != expected_profile_sha256
            or record.get("source_lock_sha256") != expected_source_lock_sha256
            or record.get("run_id") != run_id
            or record.get("evidence_matrix_sha256") != matrix_sha256
            or record.get("evidence_manifest_sha256") != evidence_manifest_sha256
            or not isinstance(record.get("authorization_id"), str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,127}", record["authorization_id"])
            or not isinstance(record.get("nonce_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", record["nonce_sha256"])
            or not isinstance(record.get("review_packet_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", record["review_packet_sha256"])):
        raise ValueError("authorization record does not prove a consumed exact one-run approval")
    categories = record.get("authorized_categories")
    if (not isinstance(categories, list) or not categories
            or any(not isinstance(category, str) or category not in OWNER_APPROVABLE_LIVE_CATEGORIES
                   for category in categories)):
        raise ValueError("authorization record has invalid categories")
    if len(categories) != len(set(categories)):
        raise ValueError("authorization record has duplicate categories")
    if ledger_path.is_symlink():
        raise ValueError("authorization ledger must not be a symlink")
    ledger_info = ledger_path.stat()
    if (not stat.S_ISREG(ledger_info.st_mode) or ledger_info.st_uid != os.getuid()
            or ledger_info.st_mode & 0o077):
        raise ValueError("authorization ledger must be an owner-only regular file")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(ledger, dict):
        raise ValueError("authorization ledger has an invalid schema")
    entries = ledger.get("entries")
    if not isinstance(entries, list):
        raise ValueError("authorization ledger has an invalid entries list")
    expected_entry = {
        "authorization_id": record["authorization_id"], "run_id": run_id,
        "nonce_sha256": record["nonce_sha256"], "state": "CONSUMED",
    }
    matching_ids = [entry for entry in entries
                    if isinstance(entry, dict)
                    and entry.get("authorization_id") == record["authorization_id"]]
    if (not isinstance(ledger, dict)
            or ledger.get("schema") != "claritylink-comprehensive-consumed-authorization-ledger-v1"
            or ledger.get("campaign_id") != record["campaign_id"]
            or len(matching_ids) != 1
            or entries.count(expected_entry) != 1):
        raise ValueError("authorization ID is not uniquely consumed for this exact run in the ledger")
    return set(categories)


if __name__ == "__main__":
    raise SystemExit(main())
