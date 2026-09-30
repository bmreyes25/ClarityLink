"""Offline analysis of a finalized Step 40E host capture bundle."""

from __future__ import annotations

from dataclasses import asdict
import gzip
import argparse
import json
from pathlib import Path
import re
from typing import Any

from parsers import (Mapping, aligned_candidate, decode_signal_mask,
                     mapping_gaps, parse_maps, parse_proc_net, parse_proc_net_unix, parse_smaps,
                     parse_status, parse_task_listing, runtime_address, thumb_bl_range)

STATIC_INFO = 0x28A158
STATIC_SETUP = 0x28AF72
JMCS_PATH = "/system/bin/jmcs"
JMCS_SHA256 = "cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232"
TARGET_CONFIG_KEYS = ("CONFIG_SMP", "CONFIG_PREEMPT", "CONFIG_ARM", "CONFIG_ARCH_TEGRA",
                      "CONFIG_PROC_PAGE_MONITOR", "CONFIG_KALLSYMS", "CONFIG_STACKTRACE",
                      "CONFIG_IKCONFIG", "CONFIG_MODULES")


def _artifact(root: Path, phase: str, category: str, name: str) -> bytes | None:
    path = root / phase / category / f"{name}.raw"
    try:
        return path.read_bytes()
    except OSError:
        return None


def _text(value: bytes | None) -> str:
    return value.decode("utf-8", "replace") if value is not None else ""


def _parse_size(value: str) -> int | None:
    found = re.fullmatch(r"([0-9]+)\s*(kB|KB|bytes|B)?", value.strip())
    if not found:
        return None
    number = int(found.group(1))
    return number * 1024 if found.group(2) and found.group(2).lower() == "kb" else number


def _parse_map_page_sizes(smaps_text: str, target: Mapping) -> set[int]:
    sizes = set()
    for entry in parse_smaps(smaps_text):
        if entry.mapping == target:
            for key in ("KernelPageSize", "MMUPageSize"):
                if key in entry.fields:
                    size = _parse_size(entry.fields[key])
                    if size:
                        sizes.add(size)
    return sizes


def _is_jmcs(mapping: Mapping) -> bool:
    return mapping.pathname.removesuffix(" (deleted)") == JMCS_PATH


def _task_snapshot(root: Path, phase: str, index: int) -> dict[int, dict[str, str]]:
    listing = _text(_artifact(root, phase, "threads", f"snapshot_{index:02d}_task_listing"))
    try:
        tids = parse_task_listing(listing)
    except ValueError:
        return {}
    result = {}
    for tid in tids:
        raw = _artifact(root, phase, "threads", f"snapshot_{index:02d}_tid_{tid}_status")
        if raw is None:
            continue
        status = parse_status(_text(raw))
        wchan = _text(_artifact(root, phase, "threads", f"snapshot_{index:02d}_tid_{tid}_wchan")).strip()
        thread = {"name": status.get("Name", ""), "state": status.get("State", ""),
                  "pid": status.get("Pid", ""), "tgid": status.get("Tgid", ""),
                  "ppid": status.get("PPid", ""), "sigpnd": status.get("SigPnd", ""),
                  "shdpnd": status.get("ShdPnd", ""), "sigblk": status.get("SigBlk", ""),
                  "sigign": status.get("SigIgn", ""), "sigcgt": status.get("SigCgt", ""),
                  "wchan": wchan}
        for key in ("sigpnd", "shdpnd", "sigblk", "sigign", "sigcgt"):
            if thread[key]:
                thread[f"{key}_decoded"] = decode_signal_mask(thread[key].split()[0])
        result[tid] = thread
    return result


def analyze_phase(root: Path, phase: str, mmap_min_addr: int = 0) -> dict[str, Any]:
    identity = None
    manifest_path = root / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text())
        raw_identity = manifest.get("process_identities", {}).get(phase)
        if raw_identity:
            identity = raw_identity
    except (OSError, json.JSONDecodeError):
        manifest = {}
    maps_text = _text(_artifact(root, phase, "process", "maps"))
    mappings = parse_maps(maps_text) if maps_text else ()
    jmcs_maps = tuple(mapping for mapping in mappings if _is_jmcs(mapping))
    executable = tuple(mapping for mapping in jmcs_maps if "x" in mapping.permissions)
    smaps_text = _text(_artifact(root, phase, "process", "smaps"))
    smaps_entries = parse_smaps(smaps_text) if smaps_text else ()
    page_size_values = set()
    for mapping in executable:
        page_size_values.update(_parse_map_page_sizes(smaps_text, mapping))
    page_sizes = sorted(page_size_values)
    page_size = page_sizes[0] if len(page_sizes) == 1 else None
    bias = None
    address_results: dict[str, int | None] = {"info": None, "setup": None}
    bias_evidence = None
    for mapping in executable:
        if mapping.offset == 0:
            # Pinned ELF evidence has p_offset=p_vaddr=0 for the RX PT_LOAD;
            # load bias therefore requires no guessed target page size.
            bias = mapping.start
            bias_evidence = {"mapping": asdict(mapping), "pt_load_offset": 0,
                             "pt_load_vaddr": 0,
                             "relationship": "mapping.start - align_down(p_vaddr,page_size), with p_vaddr=0"}
            break
    if bias is not None:
        for label, static in (("info", STATIC_INFO), ("setup", STATIC_SETUP)):
            try:
                address_results[label] = runtime_address(static, bias, executable)
            except ValueError:
                address_results[label] = None
    thread_snapshots = [_task_snapshot(root, phase, index) for index in range(5)]
    tids_by_snapshot = [set(snapshot) for snapshot in thread_snapshots]
    tids_union = set().union(*tids_by_snapshot) if tids_by_snapshot else set()
    stable = bool(tids_by_snapshot) and all(tids == tids_by_snapshot[0] for tids in tids_by_snapshot)
    process_status = parse_status(_text(_artifact(root, phase, "process", "status")))
    network = {}
    for name, proto, family in (("tcp4", "tcp", 4), ("tcp6", "tcp", 6),
                                ("udp4", "udp", 4), ("udp6", "udp", 6)):
        raw = _artifact(root, phase, "network", name)
        try:
            network[name] = [asdict(sock) for sock in parse_proc_net(_text(raw), proto, family)] if raw else []
        except ValueError:
            network[name] = []
    fd_targets = {}
    for path in sorted((root / phase / "process").glob("fd_*_target.raw")):
        target = path.read_text(errors="replace").strip()
        match = re.fullmatch(r"socket:\[([0-9]+)\]", target)
        fd = path.name.removeprefix("fd_").removesuffix("_target.raw")
        fd_targets[fd] = {"class": "socket" if match else target.split(":", 1)[0],
                          "socket_inode": int(match.group(1)) if match else None}
    tcp_inodes = {int(sock["inode"]) for values in network.values() for sock in values}
    fd_socket_inodes = {item["socket_inode"] for item in fd_targets.values()
                        if item["socket_inode"] is not None}
    unix_raw = _artifact(root, phase, "network", "unix")
    try:
        unix_sockets = [dict(sock) for sock in parse_proc_net_unix(_text(unix_raw))] if unix_raw else []
    except ValueError:
        unix_sockets = []
    unix_inodes = {int(sock["inode"]) for sock in unix_sockets}
    config_bytes = _artifact(root, phase, "platform", "proc_config.gz")
    config_summary = {}
    if config_bytes:
        try:
            config_data = gzip.decompress(config_bytes).decode("ascii", "replace")
            for key in TARGET_CONFIG_KEYS:
                match = re.search(rf"^{re.escape(key)}=(.+)$|^# {re.escape(key)} is not set$",
                                  config_data, re.MULTILINE)
                if match:
                    config_summary[key] = match.group(1) or "n"
        except (OSError, EOFError):
            config_summary = {"parse_status": "malformed or unsupported gzip"}
    hash_output = _text(_artifact(root, phase, "platform", "jmcs_file_sha256")).strip()
    hash_match = re.match(r"([0-9a-fA-F]{64})\s+", hash_output)
    property_values = {}
    for prop in ("ro_build_fingerprint", "ro_build_id", "ro_build_version_release",
                 "ro_build_version_sdk", "ro_product_board", "ro_product_device",
                 "ro_product_model", "ro_hardware", "ro_secure", "ro_debuggable"):
        value = _text(_artifact(root, phase, "properties", prop)).strip()
        if value:
            property_values[prop] = value
    aslr = _text(_artifact(root, phase, "platform", "proc_sys_kernel_randomize_va_space")).strip()
    selinux = _text(_artifact(root, phase, "platform", "sys_fs_selinux_enforce")).strip()
    cpu_values = {}
    for path in sorted((root / phase / "cpu").glob("*.raw")):
        key = path.stem.removesuffix(".raw")
        if key.endswith("listing"):
            continue
        cpu_values[key] = path.read_text(errors="replace").strip()
    text_regions = [{"start": f"0x{mapping.start:x}", "end": f"0x{mapping.end:x}",
                     "permissions": mapping.permissions, "offset": f"0x{mapping.offset:x}",
                     "device": mapping.device, "inode": mapping.inode,
                     "private_shared": "private" if mapping.permissions.endswith("p") else "shared",
                     "pathname": mapping.pathname}
                    for mapping in jmcs_maps]
    page_fields = []
    for entry in smaps_entries:
        if _is_jmcs(entry.mapping) and "x" in entry.mapping.permissions:
            page_fields.append({key: entry.fields[key] for key in
                                ("KernelPageSize", "MMUPageSize", "VmFlags") if key in entry.fields})
    info_range = thumb_bl_range(address_results["info"]) if address_results["info"] is not None else None
    setup_range = thumb_bl_range(address_results["setup"]) if address_results["setup"] is not None else None
    site_ranges = {"info": info_range, "setup": setup_range}
    ordered_maps = sorted(mappings, key=lambda mapping: mapping.start)
    site_gaps = {}
    for label, reach in site_ranges.items():
        records = []
        if reach:
            for start, end in mapping_gaps(mappings, max(reach[0], mmap_min_addr), reach[1]):
                candidate = aligned_candidate((start, end), page_size) if page_size else None
                previous = next((mapping for mapping in reversed(ordered_maps) if mapping.end <= start), None)
                following = next((mapping for mapping in ordered_maps if mapping.start >= end), None)
                records.append({"start": f"0x{start:x}", "end_exclusive": f"0x{end:x}",
                                "size": end - start,
                                "whole_pages": (end - start) // page_size if page_size else None,
                                "previous_mapping": asdict(previous) if previous else None,
                                "next_mapping": asdict(following) if following else None,
                                "one_page_candidate": ([f"0x{candidate[0]:x}", f"0x{candidate[1]:x}"]
                                                       if candidate else None)})
        site_gaps[label] = records
    common_range = None
    gaps: tuple[tuple[int, int], ...] = ()
    gap_records = []
    if info_range and setup_range:
        common_range = (max(info_range[0], setup_range[0]), min(info_range[1], setup_range[1]))
        if common_range[0] <= common_range[1]:
            gaps = mapping_gaps(mappings, max(common_range[0], mmap_min_addr), common_range[1])
            for start, end in gaps:
                page_candidate = aligned_candidate((start, end), page_size) if page_size else None
                previous = next((mapping for mapping in reversed(ordered_maps) if mapping.end <= start), None)
                following = next((mapping for mapping in ordered_maps if mapping.start >= end), None)
                gap_records.append({"start": f"0x{start:x}", "end_exclusive": f"0x{end:x}",
                                    "size": end - start,
                                    "whole_pages": (end - start) // page_size if page_size else None,
                                    "info_distance": abs(start - (address_results["info"] + 4)),
                                    "setup_distance": abs(start - (address_results["setup"] + 4)),
                                    "previous_mapping": asdict(previous) if previous else None,
                                    "next_mapping": asdict(following) if following else None,
                                    "one_page_candidate": ([f"0x{page_candidate[0]:x}",
                                                            f"0x{page_candidate[1]:x}"]
                                                           if page_candidate else None)})
    config_bytes = _artifact(root, phase, "platform", "proc_config.gz")
    proc_net_sockets = [entry for items in network.values() for entry in items]
    return {
        "phase": phase,
        "process_identity": identity,
        "maps_available": bool(maps_text),
        "jmcs_mappings": text_regions,
        "jmcs_executable_mappings": [r for r in text_regions if "x" in r["permissions"]],
        "any_jmcs_rwx": any("w" in m.permissions and "x" in m.permissions for m in jmcs_maps),
        "smaps_available": bool(smaps_text),
        "smaps_page_fields": page_fields,
        "smaps_page_size_values": page_sizes,
        "target_page_size": page_size,
        "page_size_evidence": "direct smaps field" if page_size else "unknown",
        "load_bias": f"0x{bias:x}" if bias is not None else None,
        "load_bias_evidence": bias_evidence,
        "runtime_callsites": {key: (f"0x{value:x}" if value is not None else None)
                              for key, value in address_results.items()},
        "process_signals": {key: {"raw": process_status[key],
                                   "decoded": decode_signal_mask(process_status[key].split()[0])}
                            for key in ("SigPnd", "ShdPnd", "SigBlk", "SigIgn", "SigCgt")
                            if key in process_status},
        "thread_snapshots": [{str(tid): record for tid, record in snapshot.items()}
                             for snapshot in thread_snapshots],
        "thread_count_first": len(tids_by_snapshot[0]) if tids_by_snapshot else 0,
        "thread_count_union": len(tids_union),
        "thread_population_stable_within_phase": stable,
        "process_signal_masks_complete": all(key in process_status for key in
                                              ("SigPnd", "ShdPnd", "SigBlk", "SigIgn", "SigCgt")),
        "per_thread_signal_masks_complete": bool(tids_union) and all(
            all(thread.get(key) for key in ("sigpnd", "shdpnd", "sigblk", "sigign", "sigcgt"))
            for snapshot in thread_snapshots for thread in snapshot.values()),
        "wchan_reads_available": bool(thread_snapshots) and all(
            bool(thread.get("wchan")) for snapshot in thread_snapshots for thread in snapshot.values()),
        "network": network,
        "unix_sockets": unix_sockets,
        "common_veneer_range": ([f"0x{common_range[0]:x}", f"0x{common_range[1]:x}"]
                                 if common_range else None),
        "site_veneer_ranges": {key: ([f"0x{value[0]:x}", f"0x{value[1]:x}"] if value else None)
                               for key, value in site_ranges.items()},
        "site_candidate_unmapped_gaps": site_gaps,
        "candidate_unmapped_gaps": gap_records,
        "candidate_gap_page_alignment_evidence": "smaps" if page_size else "unavailable",
        "target_config_present": config_bytes is not None and len(config_bytes) > 0,
        "target_config_gzip_bytes": len(config_bytes) if config_bytes is not None else 0,
        "target_config_selected_keys": config_summary,
        "jmcs_file_sha256": hash_match.group(1).lower() if hash_match else None,
        "jmcs_file_exact_pinned_build_match": bool(hash_match and hash_match.group(1).lower() == JMCS_SHA256),
        "jmcs_file_hash_readable": bool(hash_match),
        "selected_properties": property_values,
        "aslr_randomize_va_space": aslr or None,
        "selinux_enforce": selinux or None,
        "cpu_topology_cache_reads": cpu_values,
        "fd_targets": fd_targets,
        "network_fd_inodes_with_tcp_udp_table_match": sorted(fd_socket_inodes & tcp_inodes),
        "network_fd_inodes_with_unix_table_match": sorted(fd_socket_inodes & unix_inodes),
        "network_socket_entry_count": len(proc_net_sockets),
        "mmap_min_addr": mmap_min_addr,
        "disclaimer": "Unmapped VA is only a snapshot candidate; no allocation or safety is implied.",
    }


def analyze_bundle(root: Path) -> dict[str, Any]:
    root = root.resolve()
    try:
        manifest = json.loads((root / "manifest.json").read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("capture manifest missing or malformed") from exc
    phases = [phase for phase in ("baseline", "connected", "post-disconnect")
              if phase in manifest.get("process_identities", {})]
    output = {"capture_id": manifest.get("capture_id"), "phases": {},
              "phase_deltas": {}, "privacy_note": "analysis is host-local; review before any repository export"}
    mmap_min = 0
    for phase in phases:
        raw_min = _text(_artifact(root, "baseline", "platform", "proc_sys_vm_mmap_min_addr")).strip()
        try:
            mmap_min = int(raw_min, 0)
        except ValueError:
            mmap_min = 0
        output["phases"][phase] = analyze_phase(root, phase, mmap_min)
    for left, right in (("baseline", "connected"), ("connected", "post-disconnect")):
        if left not in output["phases"] or right not in output["phases"]:
            continue
        a, b = output["phases"][left], output["phases"][right]
        ia, ib = a.get("process_identity"), b.get("process_identity")
        same_instance = bool(ia and ib and ia.get("pid") == ib.get("pid") and
                             ia.get("start_time_ticks") == ib.get("start_time_ticks"))
        maps_a = {(m["start"], m["end"], m["permissions"], m["offset"], m["pathname"])
                  for m in a["jmcs_mappings"]}
        maps_b = {(m["start"], m["end"], m["permissions"], m["offset"], m["pathname"])
                  for m in b["jmcs_mappings"]}
        threads_a = set().union(*(set(map(int, snap)) for snap in a["thread_snapshots"]))
        threads_b = set().union(*(set(map(int, snap)) for snap in b["thread_snapshots"]))
        output["phase_deltas"][f"{left}_to_{right}"] = {
            "same_process_instance": same_instance,
            "pid_changed": ia is None or ib is None or ia.get("pid") != ib.get("pid"),
            "start_time_changed": ia is None or ib is None or ia.get("start_time_ticks") != ib.get("start_time_ticks"),
            "mappings_added": sorted(maps_b - maps_a),
            "mappings_removed": sorted(maps_a - maps_b),
            "thread_tids_added": sorted(threads_b - threads_a),
            "thread_tids_removed": sorted(threads_a - threads_b),
            "thread_counts": [len(threads_a), len(threads_b)],
        }
    phases_data = list(output["phases"].values())
    masks = []
    signals_complete = bool(phases_data) and all(
        phase["process_signal_masks_complete"] and phase["per_thread_signal_masks_complete"]
        for phase in phases_data)
    for phase_data in phases_data:
        for signal_key in ("SigPnd", "ShdPnd", "SigBlk", "SigIgn", "SigCgt"):
            if signal_key in phase_data["process_signals"]:
                masks.extend(number for item in phase_data["process_signals"][signal_key]["decoded"]
                             for number in (int(item.split(":", 1)[0]),))
        for snapshot in phase_data["thread_snapshots"]:
            for thread in snapshot.values():
                for key in ("sigpnd_decoded", "shdpnd_decoded", "sigblk_decoded",
                            "sigign_decoded", "sigcgt_decoded"):
                    masks.extend(int(item.split(":", 1)[0]) for item in thread.get(key, ()))
    observed_signal_numbers = set(masks)
    output["observed_signal_candidate_unmasked_unignored_uncaught"] = [
        number for number in range(1, 65) if number not in (9, 19) and number not in observed_signal_numbers
    ] if signals_complete else None
    gap_sets = [tuple((item["start"], item["end_exclusive"]) for item in phase["candidate_unmapped_gaps"])
                for phase in phases_data]
    output["common_candidate_gaps_stable_all_phases"] = (
        bool(gap_sets) and all(gaps == gap_sets[0] for gaps in gap_sets[1:])
    ) if len(phases_data) == 3 else None
    within_phase_stability = [phase.get("thread_population_stable_within_phase") for phase in phases_data]
    output["thread_population_overall"] = (
        "MIXED" if any(within_phase_stability) and not all(within_phase_stability)
        else "STABLE" if phases_data and all(within_phase_stability)
        else "CHURNING" if phases_data else "UNKNOWN")
    analysis_path = root.parent / f"{root.name}_analysis.json"
    analysis_path.write_text(json.dumps(output, indent=2, sort_keys=True, default=list) + "\n")
    analysis_path.chmod(0o600)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path, help="host-side CLARITY_RUNTIME_ capture directory")
    args = parser.parse_args()
    result = analyze_bundle(args.capture)
    print(json.dumps({"capture_id": result["capture_id"],
                      "phases": list(result["phases"]),
                      "phase_deltas": list(result["phase_deltas"]),
                      "analysis_path": str(args.capture.parent / f"{args.capture.name}_analysis.json")}, indent=2))
