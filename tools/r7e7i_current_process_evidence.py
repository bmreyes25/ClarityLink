#!/usr/bin/env python3
"""Offline parser for supplied procfs evidence; never enumerates live /proc.

The contract is designed for fixtures and preserved receipts. It classifies
one bounded snapshot; it cannot exclude a later launch or authorize cleanup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

TARGET = "/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f"
SHA_RE = re.compile(r"[a-f0-9]{64}")


class ProcessEvidenceError(ValueError):
    pass


def parse_proc_stat(raw: str) -> dict[str, object]:
    """Parse Linux /proc/PID/stat fields 3 and 22 despite ')' in comm."""
    raw = raw.rstrip("\n")
    left = raw.find(" (")
    right = raw.rfind(") ")
    if left < 1 or right <= left:
        raise ProcessEvidenceError("malformed proc stat")
    try:
        pid = int(raw[:left])
    except ValueError as exc:
        raise ProcessEvidenceError("invalid proc stat pid") from exc
    fields = raw[right + 2:].split()  # starts at field 3 (state)
    if pid <= 1 or len(fields) <= 19 or len(fields[0]) != 1:
        raise ProcessEvidenceError("proc stat lacks state or starttime")
    try:
        starttime = int(fields[19])  # field 22, counted from field 3
    except ValueError as exc:
        raise ProcessEvidenceError("invalid proc stat starttime") from exc
    if starttime < 0:
        raise ProcessEvidenceError("negative proc stat starttime")
    return {"pid": pid, "state": fields[0], "starttime_ticks": starttime}


def parse_maps(raw: str) -> list[dict[str, object]]:
    rows = []
    for line in raw.splitlines():
        match = re.fullmatch(r"([0-9a-f]+)-([0-9a-f]+)\s+([rwxps-]{4})\s+[0-9a-f]+\s+([0-9a-f]+:[0-9a-f]+)\s+(\d+)(?:\s+(.*))?", line)
        if not match:
            raise ProcessEvidenceError("malformed proc maps line")
        start, end = int(match.group(1), 16), int(match.group(2), 16)
        if start >= end:
            raise ProcessEvidenceError("invalid proc maps address interval")
        rows.append({"start": start, "end": end, "permissions": match.group(3),
                     "device": match.group(4).lower(), "inode": int(match.group(5)),
                     "path": match.group(6) or ""})
    return rows


def _valid_identity(value: object) -> bool:
    return (isinstance(value, dict) and set(value) == {"device", "inode"}
            and isinstance(value["device"], str) and bool(re.fullmatch(r"[0-9a-f]+:[0-9a-f]+", value["device"].lower()))
            and type(value["inode"]) is int and value["inode"] > 0)


def _same_identity(value: object, expected: dict[str, object]) -> bool:
    return (_valid_identity(value) and value["device"].lower() == expected["device"].lower()
            and value["inode"] == expected["inode"])


def _sha_receipts(receipts: object) -> bool:
    return (isinstance(receipts, list) and bool(receipts)
            and all(isinstance(row, dict) and set(row) == {"name", "sha256"}
                    and isinstance(row["name"], str) and row["name"]
                    and isinstance(row["sha256"], str) and SHA_RE.fullmatch(row["sha256"])
                    for row in receipts))


def classify(evidence: dict[str, object]) -> dict[str, object]:
    reasons: list[str] = []
    if evidence.get("schema_version") != "R7E7I-CURRENT-PROCESS-EVIDENCE-1":
        raise ProcessEvidenceError("unsupported process evidence schema")
    source_kind = evidence.get("source_kind")
    if source_kind not in {"SYNTHETIC_FIXTURE", "PRESERVED_RECEIPT", "LIVE_READ_ONLY_RECEIPT"}:
        raise ProcessEvidenceError("unknown source kind")
    if not isinstance(evidence.get("evidence_id"), str) or not evidence["evidence_id"]:
        raise ProcessEvidenceError("evidence id required")
    if not _sha_receipts(evidence.get("receipts")):
        raise ProcessEvidenceError("hash-bound source receipts required")
    if evidence.get("target_path") != TARGET:
        return _result(source_kind, "WRONG_TARGET_PATH", ["Evidence path is not the exact historical target."], evidence)
    before_identity = evidence.get("target_identity_before")
    after_identity = evidence.get("target_identity_after")
    if not _valid_identity(before_identity) or not _valid_identity(after_identity):
        return _result(source_kind, "TARGET_IDENTITY_UNAVAILABLE", ["Device/inode identity is required; basename, size, or MD5 alone is insufficient."], evidence)
    if before_identity != after_identity:
        return _result(source_kind, "FILE_IDENTITY_CHANGED", ["Target device/inode changed during observation."], evidence)
    if evidence.get("target_file_type") != "REGULAR":
        return _result(source_kind, "TARGET_NOT_VERIFIED_REGULAR", ["Target is not positively identified as a regular file."], evidence)
    if evidence.get("boot_id_before") != evidence.get("boot_id_after") or not isinstance(evidence.get("boot_id_before"), str):
        return _result(source_kind, "BOOT_OR_SNAPSHOT_CONFLICT", ["Boot identity changed or is unavailable across the sample."], evidence)
    before = evidence.get("processes_before")
    after = evidence.get("processes_after")
    if not isinstance(before, list) or not isinstance(after, list):
        return _result(source_kind, "PROCESS_SET_UNAVAILABLE", ["Both process inventories are required."], evidence)
    if evidence.get("proc_visibility") != "COMPLETE" or evidence.get("enumerated_count") != len(before):
        return _result(source_kind, "VISIBILITY_INCOMPLETE", ["Procfs visibility or inventory coverage is incomplete."], evidence)
    if any(not isinstance(p, dict) or type(p.get("pid")) is not int
           or type(p.get("starttime_ticks")) is not int or p["starttime_ticks"] < 0
           for p in before + after):
        return _result(source_kind, "MALFORMED_PROCESS_RECORD", ["PID and starttime generation must be integer fields."], evidence)
    if sorted(p["pid"] for p in before) != sorted(p["pid"] for p in after):
        return _result(source_kind, "PROCESS_SET_CHANGED", ["PID inventory changed between snapshots."], evidence)
    before_by_pid = {p["pid"]: p for p in before}
    after_by_pid = {p["pid"]: p for p in after}
    if len(before_by_pid) != len(before) or len(after_by_pid) != len(after):
        return _result(source_kind, "MALFORMED_PROCESS_RECORD", ["Duplicate or malformed PID records."], evidence)
    if any(before_by_pid[pid].get("starttime_ticks") != after_by_pid[pid].get("starttime_ticks")
           for pid in before_by_pid):
        return _result(source_kind, "PID_REUSE_OR_PROCESS_REPLACED", ["A PID generation changed between snapshots."], evidence)
    if evidence.get("unreadable_processes"):
        return _result(source_kind, "VISIBILITY_INCOMPLETE", ["At least one process or required procfs object was unreadable."], evidence)
    if evidence.get("readlink_available") is not True or evidence.get("maps_available") is not True or evidence.get("fd_directory_covered") is not True:
        return _result(source_kind, "REQUIRED_PROC_FIELD_UNAVAILABLE", ["exe, maps, and fd evidence must all be available for every enumerated process."], evidence)

    references = []
    zombies = []
    same_basename_different_inode = []
    for pid, row in after_by_pid.items():
        if not isinstance(pid, int) or pid <= 1:
            return _result(source_kind, "MALFORMED_PROCESS_RECORD", ["Invalid PID."], evidence)
        if not isinstance(row.get("state"), str) or len(row["state"]) != 1:
            return _result(source_kind, "MALFORMED_PROCESS_RECORD", ["Process state must be a single procfs state character."], evidence)
        if row.get("state") == "Z":
            zombies.append(pid)
        observations = []
        exe = row.get("exe")
        if row.get("state") != "Z":
            if not isinstance(exe, dict) or not _valid_identity(exe.get("identity")):
                return _result(source_kind, "REQUIRED_PROC_FIELD_UNAVAILABLE", [f"PID {pid} executable identity is unreadable or invalid."], evidence)
            observations.append(("exe", exe["identity"], exe.get("path", "")))
        elif isinstance(exe, dict) and _valid_identity(exe.get("identity")):
            observations.append(("exe", exe["identity"], exe.get("path", "")))
        for field in ("maps", "fds"):
            values = row.get(field)
            if not isinstance(values, list) or any(not isinstance(item, dict) for item in values):
                return _result(source_kind, "MALFORMED_PROCESS_RECORD", [f"{field} must be a fully parsed list."], evidence)
            if any(item.get("identity") is not None and not _valid_identity(item.get("identity"))
                   for item in values):
                return _result(source_kind, "MALFORMED_PROCESS_RECORD", [f"{field} contains an invalid file identity."], evidence)
            if any(item.get("identity") is None and
                   (item.get("path") == TARGET or item.get("path", "").startswith(TARGET + " ("))
                   for item in values if isinstance(item.get("path"), str)):
                return _result(source_kind, "REQUIRED_PROC_FIELD_UNAVAILABLE", [f"{field} target-like path has no verified inode identity."], evidence)
            observations.extend((field, item.get("identity"), item.get("path", "")) for item in values)
        for kind, identity, path in observations:
            if _same_identity(identity, after_identity):
                references.append({"pid": pid, "starttime_ticks": row.get("starttime_ticks"),
                                   "reference_kind": kind, "path": path})
            elif isinstance(path, str) and (path == TARGET or path.startswith(TARGET + " (")):
                same_basename_different_inode.append(pid)
    if references:
        decision = "CURRENT_REFERENCES_PRESENT"
        reasons.append("At least one executable mapping, exe link, or open fd matches the exact target device/inode.")
    elif zombies:
        decision = "ZOMBIE_PROCESS_PRESENT"
        reasons.append("A zombie PID is visible; its former address space is gone, but its parent has not reaped its status.")
    elif evidence.get("relaunch_audit") == "PRESENT":
        decision = "RELAUNCH_SOURCE_PRESENT"
        reasons.append("A reviewed launch mechanism remains and can recreate the target execution.")
    elif evidence.get("relaunch_audit") != "NONE_REVIEWED":
        decision = "RELAUNCH_RISK_UNKNOWN"
        reasons.append("No complete independent audit excludes automatic and operator relaunch sources.")
    else:
        decision = "CURRENT_REFERENCES_ABSENT_WITH_COMPLETE_VISIBILITY"
        reasons.append("The exact device/inode was not observed in the supplied complete, bounded snapshot.")
        reasons.append("A snapshot does not prevent a later launch; future-launch exclusion is not proven.")
    if same_basename_different_inode:
        reasons.append("A matching pathname with a different device/inode was not treated as the target executable.")
    return _result(source_kind, decision, reasons, evidence,
                   references=references, zombies=zombies,
                   same_basename_different_inode=sorted(set(same_basename_different_inode)))


def _result(source_kind: str, decision: str, reasons: list[str], evidence: dict[str, object], **extra) -> dict[str, object]:
    model_only = source_kind == "SYNTHETIC_FIXTURE"
    return {"schema_version": "R7E7I-CURRENT-PROCESS-CLASSIFICATION-1",
            "decision": ("MODEL_ONLY_" + decision if model_only else decision),
            "evidence_id": evidence.get("evidence_id"),
            "source_kind": source_kind,
            "source_receipt_sha256": [row["sha256"] for row in evidence.get("receipts", [])
                                      if isinstance(row, dict) and "sha256" in row],
            "reasons": reasons,
            "future_launch_exclusion": "NOT_PROVEN_BY_SNAPSHOT",
            "cleanup_authorized": False,
            "test_a_authorized": False,
            **extra}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_json", type=Path)
    args = parser.parse_args(argv)
    try:
        evidence = json.loads(args.evidence_json.read_text())
        result = classify(evidence)
    except (OSError, json.JSONDecodeError, ProcessEvidenceError) as exc:
        print(f"PROCESS_EVIDENCE_INCONCLUSIVE: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
