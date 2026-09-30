"""Sanitized, exhaustive host-side inventory for a finalized capture bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from analyze import _observation_status
from parsers import (decode_signal_mask, parse_proc_net, parse_proc_net_unix,
                     parse_status, parse_task_listing)


def _safe_path(path: str) -> str:
    path = re.sub(r"(?<=/)(?:[0-9]+)(?=/)", "<pid>", path)
    path = re.sub(r"(?<=tid_)[0-9]+(?=_)", "<tid>", path)
    path = re.sub(r"(?<=snapshot_)[0-9]{2}(?=_)", "<snapshot>", path)
    return path


def _usefulness(path: str) -> list[str]:
    p = path.lower()
    tags = []
    for needle, tag in (
        ("maps", "mappings/load-bias/veneer-space"),
        ("smaps", "page-size/mapping-metadata"),
        ("stat", "process-identity/lifecycle"),
        ("status", "uid-gid/signals/thread-state"),
        ("thread", "thread-population/signal-rendezvous"),
        ("wchan", "thread-wait-state"),
        ("fd", "descriptor/socket-attribution"),
        ("/net/", "global-network-deltas"),
        ("tcp", "global-network-deltas"),
        ("udp", "global-network-deltas"),
        ("meminfo", "memory/page-size-indirect-evidence"),
        ("cpu", "cpu-topology/cache"),
        ("mount", "mount-and-proc-policy"),
        ("selinux", "security-policy"),
        ("randomize_va_space", "aslr-state"),
        ("config", "kernel-configuration"),
        ("cmdline", "process-identity"),
        ("limits", "process-limits"),
        ("logcat", "bounded-system-diagnostics"),
        ("property", "platform-identity"),
        ("identity", "platform/process-identity"),
    ):
        if needle in p and tag not in tags:
            tags.append(tag)
    return tags or ["capture-integrity/provenance"]


def artifact_inventory(root: Path) -> dict[str, Any]:
    """Inventory each manifest artifact plus the hashed manifest itself.

    Raw paths and argument values are not copied into this report; numeric
    process/thread identifiers are replaced. Data bytes are never modified.
    """
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    rows = []
    expected_hashes = {}
    hash_path = root / "sha256.txt"
    if hash_path.is_file():
        for line in hash_path.read_text(errors="replace").splitlines():
            match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(.+)", line)
            if match:
                expected_hashes[match.group(2).strip()] = match.group(1).lower()
    for item in manifest.get("artifacts", []):
        path = str(item["path"])
        file = root / path
        raw = file.read_bytes() if file.is_file() else b""
        stored_status = _observation_status(raw)
        if item.get("kind") == "stderr" and stored_status == "available":
            stored_status = "diagnostic_output"
        actual_hash = hashlib.sha256(raw).hexdigest() if file.is_file() else None
        rows.append({
            "artifact": _safe_path(path),
            "phase": path.split("/", 1)[0],
            "command": item.get("operation", "unknown"),
            "status": stored_status if file.is_file() else "artifact_missing",
            "size": len(raw) if file.is_file() else None,
            "sha256": actual_hash,
            "hash_match": actual_hash is not None and actual_hash == item.get("sha256")
                          and expected_hashes.get(path) == actual_hash,
            "useful_for": _usefulness(path),
        })
    manifest_raw = manifest_path.read_bytes()
    manifest_hash = hashlib.sha256(manifest_raw).hexdigest()
    rows.append({"artifact": "manifest.json", "phase": "capture", "command": "manifest",
                 "status": "available", "size": len(manifest_raw),
                 "sha256": manifest_hash,
                 "hash_match": expected_hashes.get("manifest.json") == manifest_hash,
                 "useful_for": ["capture-integrity/provenance"]})
    rows.sort(key=lambda row: row["artifact"])
    mismatches = sum(1 for row in rows if not row["hash_match"])
    return {"source_capture_id": "redacted", "source_artifact_count": len(manifest.get("artifacts", [])),
            "inventory_entry_count": len(rows), "path_identifiers_redacted": True,
            "hash_entries_expected": len(expected_hashes), "hash_mismatch_count": mismatches,
            "rows": rows}


def thread_analysis(root: Path) -> dict[str, Any]:
    phases = ("baseline", "connected", "post-disconnect")
    all_observations: dict[str, dict[int, list[dict[str, Any]]]] = {}
    snapshot_summary = {}
    mask_records: list[dict[str, Any]] = []
    for phase in phases:
        directory = root / phase / "threads"
        phase_obs: dict[int, list[dict[str, Any]]] = {}
        listed_by_snapshot: dict[int, set[int]] = {}
        for listing_path in sorted(directory.glob("snapshot_*_task_listing.raw")):
            match = re.search(r"snapshot_([0-9]{2})_task_listing", listing_path.name)
            if not match:
                continue
            snapshot = int(match.group(1))
            try:
                tids = parse_task_listing(listing_path.read_text(errors="replace"))
            except ValueError:
                continue
            listed_by_snapshot[snapshot] = set(tids)
            for tid in tids:
                prefix = f"snapshot_{snapshot:02d}_tid_{tid}_"
                status_path = directory / f"{prefix}status.raw"
                if not status_path.exists() or _observation_status(status_path.read_bytes()) != "available":
                    continue
                st = parse_status(status_path.read_text(errors="replace"))
                wchan_path = directory / f"{prefix}wchan.raw"
                wchan = (wchan_path.read_text(errors="replace").strip()
                         if wchan_path.exists() and _observation_status(wchan_path.read_bytes()) == "available"
                         else None)
                record = {"phase": phase, "snapshot": snapshot, "tid": tid,
                          "name": st.get("Name"), "state": st.get("State"), "wchan": wchan,
                          "sigpnd": st.get("SigPnd"), "shdpnd": st.get("ShdPnd"),
                          "sigblk": st.get("SigBlk"), "sigign": st.get("SigIgn"),
                          "sigcgt": st.get("SigCgt")}
                phase_obs.setdefault(tid, []).append(record)
                mask_records.append(record)
        for snapshot, listed in listed_by_snapshot.items():
            for tid in listed - phase_obs.keys():
                phase_obs.setdefault(tid, []).append({"phase": phase, "snapshot": snapshot,
                                                       "tid": tid, "status_missing": True})
        all_observations[phase] = phase_obs
        listed_sets = [listed_by_snapshot[i] for i in sorted(listed_by_snapshot)]
        status_sets = []
        for snapshot, listed in sorted(listed_by_snapshot.items()):
            present = set()
            for tid in listed:
                path = directory / f"snapshot_{snapshot:02d}_tid_{tid}_status.raw"
                if path.exists() and _observation_status(path.read_bytes()) == "available":
                    present.add(tid)
            status_sets.append(present)
        snapshot_summary[phase] = {
            "task_listing_counts": [len(x) for x in listed_sets],
            "status_readable_counts": [len(x) for x in status_sets],
            "stable_status_tids_across_snapshots": len(set.intersection(*status_sets)) if status_sets else 0,
            "listed_but_status_missing_by_snapshot": [
                {"snapshot": index, "tids": sorted(listed_sets[index] - status_sets[index])}
                for index in range(len(listed_sets)) if listed_sets[index] - status_sets[index]],
        }

    tids = sorted({tid for phase in all_observations.values() for tid in phase})
    rows = []
    baseline = all_observations["baseline"]
    connected = all_observations["connected"]
    post = all_observations["post-disconnect"]
    for tid in tids:
        per_phase = {phase: all_observations[phase].get(tid, []) for phase in phases}
        phases_seen = {phase for phase in phases if per_phase[phase]}
        if per_phase["baseline"] and per_phase["connected"] and per_phase["post-disconnect"]:
            category = "always-present-in-observed-phases"
        elif phases_seen == {"baseline"}:
            category = "baseline-only-observed-disappears-after-connect"
        elif phases_seen == {"connected"}:
            category = "connected-only-observed"
        elif phases_seen == {"connected", "post-disconnect"}:
            category = "appears-connected-and-persists-post-disconnect"
        else:
            category = "unknown-due-missing-observation"
        for phase in phases:
            observations = per_phase[phase]
            if not observations:
                rows.append({"tid": tid, "name": None, "phase": phase, "state": None,
                             "wchan": None, "sigblk": None, "sigign": None, "sigcgt": None,
                             "first_observed": None, "last_observed": None,
                             "observation_count": 0, "category": category,
                             "completeness": "unknown-due-missing-data"})
                continue
            present_observations = [item for item in observations if not item.get("status_missing")]
            if not present_observations:
                rows.append({"tid": tid, "name": None, "phase": phase, "state": None,
                             "wchan": None, "sigblk": None, "sigign": None, "sigcgt": None,
                             "first_observed": min(x["snapshot"] for x in observations),
                             "last_observed": max(x["snapshot"] for x in observations),
                             "observation_count": len(observations), "category": category,
                             "completeness": "listed-but-status-disappeared-before-read"})
                continue
            def stable_value(key: str) -> Any:
                vals = [item.get(key) for item in present_observations if item.get(key) is not None]
                return vals[-1] if vals else None
            rows.append({"tid": tid, "name": stable_value("name"), "phase": phase,
                         "state": stable_value("state"), "wchan": stable_value("wchan"),
                         "sigblk": stable_value("sigblk"), "sigign": stable_value("sigign"),
                         "sigcgt": stable_value("sigcgt"),
                         "first_observed": min(x["snapshot"] for x in present_observations),
                         "last_observed": max(x["snapshot"] for x in present_observations),
                         "observation_count": len(present_observations), "category": category,
                         "completeness": "complete-for-observed-snapshots"})

    decoded = {}
    for field in ("sigpnd", "shdpnd", "sigblk", "sigign", "sigcgt"):
        decoded[field] = []
        for rec in mask_records:
            value = rec.get(field)
            if value:
                decoded[field].append(set(decode_signal_mask(value.split()[0])))
    def union_for(field: str) -> set[str]:
        result: set[str] = set()
        for group in decoded[field]:
            result.update(group)
        return result
    def intersection_for(field: str) -> set[str]:
        return set.intersection(*decoded[field]) if decoded[field] else set()
    observed = set().union(*(union_for(x) for x in ("sigpnd", "shdpnd", "sigblk", "sigign", "sigcgt")))
    all_bits = {f"{n}:{signal_name(n)}" for n in range(1, 65)}
    process_masks = {}
    for phase in phases:
        status_path = root / phase / "process" / "status.raw"
        status = parse_status(status_path.read_text(errors="replace")) if status_path.exists() else {}
        process_masks[phase] = {field: sorted(decode_signal_mask(status[field].split()[0]))
                                for field in ("SigPnd", "ShdPnd", "SigBlk", "SigIgn", "SigCgt")
                                if field in status}
    return {"phases": list(phases), "thread_rows": rows,
            "thread_phase_counts": {p: len(all_observations[p]) for p in phases},
            "thread_snapshot_summary": snapshot_summary,
            "signal_analysis": {
                "mask_record_count": len(mask_records),
                "caught_everywhere": sorted(intersection_for("sigcgt")),
                "blocked_anywhere": sorted(union_for("sigblk")),
                "ignored_anywhere": sorted(union_for("sigign")),
                "pending_anywhere": sorted(union_for("sigpnd") | union_for("shdpnd")),
                "apparently_unused_in_observed_records": sorted(all_bits - observed),
                "candidate_signals": "none-designated; no signal is declared safe",
                "process_signal_masks_by_phase": process_masks,
                "scope_note": "thread masks include captured status records only; five transient connected TIDs had no status record; process masks are listed separately"}}


def signal_name(number: int) -> str:
    from parsers import _SIGNALS
    return _SIGNALS.get(number, f"RTMIN+{number - 32}" if number >= 32 else f"SIG{number}")


def network_analysis(root: Path) -> dict[str, Any]:
    phases = ("baseline", "connected", "post-disconnect")
    parsed: dict[str, dict[str, list[dict[str, Any]]]] = {}
    counts = {}
    for phase in phases:
        parsed[phase] = {}
        for label, proto, family in (("tcp4", "tcp", 4), ("tcp6", "tcp", 6),
                                     ("udp4", "udp", 4), ("udp6", "udp", 6)):
            raw = root / phase / "network" / f"{label}.raw"
            parsed[phase][label] = []
            if raw.exists() and _observation_status(raw.read_bytes()) == "available":
                parsed[phase][label] = [row.__dict__ for row in parse_proc_net(
                    raw.read_text(errors="replace"), proto, family)]
        unix_raw = root / phase / "network" / "unix.raw"
        parsed[phase]["unix"] = (list(parse_proc_net_unix(unix_raw.read_text(errors="replace")))
                                  if unix_raw.exists() and _observation_status(unix_raw.read_bytes()) == "available" else [])
        counts[phase] = {name: len(rows) for name, rows in parsed[phase].items()}
    delta = {}
    for left, right, label in (("baseline", "connected", "A_to_B"),
                               ("connected", "post-disconnect", "B_to_C")):
        delta[label] = {}
        for table in ("tcp4", "tcp6", "udp4", "udp6", "unix"):
            def key(row: dict[str, Any]) -> tuple[Any, ...]:
                if table == "unix":
                    return (row.get("inode"), row.get("path"), row.get("type"), row.get("state"))
                return (row.get("local_hex"), row.get("local_port"), row.get("remote_hex"),
                        row.get("remote_port"), row.get("state"), row.get("inode"))
            lmap = {key(row): row for row in parsed[left][table]}
            rmap = {key(row): row for row in parsed[right][table]}
            delta[label][table] = {"appeared": [rmap[k] for k in rmap.keys() - lmap.keys()],
                                   "disappeared": [lmap[k] for k in lmap.keys() - rmap.keys()],
                                   "retained": len(lmap.keys() & rmap.keys())}
    lifecycles = {}
    for table in ("tcp4", "tcp6", "udp4", "udp6", "unix"):
        def endpoint(row: dict[str, Any]) -> tuple[Any, ...]:
            if table == "unix":
                return (row.get("path"), row.get("type"), row.get("inode"))
            return (row.get("local_hex"), row.get("local_port"), row.get("remote_hex"),
                    row.get("remote_port"), row.get("inode"))
        phase_maps = {p: {endpoint(row): row for row in parsed[p][table]} for p in phases}
        bkeys, ckeys, pkeys = (set(phase_maps[p]) for p in phases)
        lifecycles[table] = {
            "connected_only_then_absent": [phase_maps["connected"][k] for k in ckeys - bkeys - pkeys],
            "persists_after_disconnect": [phase_maps["connected"][k] for k in ckeys & pkeys - bkeys],
            "baseline_endpoint_returns_after_connected_absence": [phase_maps["post-disconnect"][k]
                for k in (bkeys & pkeys) - ckeys],
            "present_all_phases": len(bkeys & ckeys & pkeys),
            "state_or_peer_tuple_changes": [
                {"baseline": phase_maps["baseline"][k], "connected": phase_maps["connected"][k],
                 "post_disconnect": phase_maps["post-disconnect"].get(k)}
                for k in bkeys & ckeys
                if phase_maps["baseline"][k] != phase_maps["connected"][k]]}
    return {"global_tables_by_phase": parsed, "row_counts": counts, "deltas": delta,
            "socket_lifecycles": lifecycles,
            "attribution": "system-wide proc tables only; no jmcs attribution without fd inode match"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output-prefix", type=Path)
    args = parser.parse_args()
    root = args.capture.expanduser().resolve()
    prefix = args.output_prefix or root.with_name(root.name + "_derived")
    prefix = prefix.expanduser().resolve()
    inventory = artifact_inventory(root)
    (prefix.parent).mkdir(parents=True, exist_ok=True)
    prefix.with_name(prefix.name + "_inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    thread_report = thread_analysis(root)
    network_report = network_analysis(root)
    (prefix.with_name(prefix.name + "_threads.json")).write_text(json.dumps(thread_report, indent=2) + "\n")
    (prefix.with_name(prefix.name + "_network.json")).write_text(json.dumps(network_report, indent=2) + "\n")
    print(json.dumps({"inventory_entries": inventory["inventory_entry_count"],
                      "hash_entries_expected": inventory["hash_entries_expected"],
                      "hash_mismatch_count": inventory["hash_mismatch_count"],
                      "thread_rows": len(thread_report["thread_rows"]),
                      "derived_prefix": str(prefix)}, indent=2))


if __name__ == "__main__":
    main()
