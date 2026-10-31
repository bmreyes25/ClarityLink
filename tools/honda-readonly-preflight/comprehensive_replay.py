"""Verify and analyze a private comprehensive-session archive offline.

The replay reports integrity, command provenance, and state deltas. It never
contacts ADB and never promotes a command result into a Type111 success claim.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAMPAIGN_ID = "CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031"
MAX_ARCHIVE_FILE_BYTES = 4 * 1024 * 1024
OBJECTIVES = (
    "ordinary-adb-identity", "existing-root-supersu-state",
    "jmcs-process-identity-continuity", "jmcs-maps-smaps-protections-load-bias",
    "jmcs-loaded-library-inventory", "jmcs-fd-socket-owner-correlation",
    "usb0-network-phase-correlation", "carplay-info-setup-observability",
    "type110-session-lifecycle", "type111-negotiation-and-authority",
    "display-manager-inventory", "display1-window-view-lifecycle",
    "surfaceflinger-layer-lifecycle", "factory-navigation-transitions",
    "hondahack-casting-and-withdrawal", "carplay-disconnect-reconnect-restoration",
    "recovery-prerequisites", "instrumentation-decision", "capture-integrity-and-privacy",
)


class ArchiveError(ValueError):
    pass


def _private_archive(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ArchiveError("archive must be a non-symlink private directory")
    resolved = path.resolve(strict=True)
    if ROOT.resolve() == resolved or ROOT.resolve() in resolved.parents:
        raise ArchiveError("archive must remain outside the repository")
    metadata = resolved.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise ArchiveError("archive directory must be owner-owned with mode 0700")
    return resolved


def _verify_inventory(root: Path) -> dict[str, str]:
    inventory = root / "sha256.txt"
    if (inventory.is_symlink() or not inventory.is_file()
            or inventory.stat().st_uid != os.getuid()
            or stat.S_IMODE(inventory.stat().st_mode) != 0o600):
        raise ArchiveError("archive SHA-256 inventory is missing or not private")
    descendants = tuple(root.rglob("*"))
    if any(path.is_symlink() for path in descendants):
        raise ArchiveError("archive must not contain symbolic links")
    actual_files = {p.relative_to(root).as_posix() for p in descendants
                    if p.is_file() and p.name != "sha256.txt"}
    recorded: dict[str, str] = {}
    for line in inventory.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9._/-]+)", line)
        if not match:
            raise ArchiveError("archive inventory contains a malformed row")
        digest, relative = match.groups()
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts or relative in recorded:
            raise ArchiveError("archive inventory path is unsafe or duplicated")
        path = root / candidate
        if path.is_symlink() or not path.is_file():
            raise ArchiveError(f"archive file is missing or symbolic: {relative}")
        metadata = path.stat()
        if (metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600
                or metadata.st_size > MAX_ARCHIVE_FILE_BYTES):
            raise ArchiveError(f"archive file is not private or exceeds its bound: {relative}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            raise ArchiveError(f"archive digest mismatch: {relative}")
        recorded[relative] = digest
    if set(recorded) != actual_files:
        raise ArchiveError("archive inventory does not cover the complete capture package")
    return recorded


def _load_archive(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, str]]:
    root = _private_archive(root)
    inventory = _verify_inventory(root)
    try:
        summary = json.loads((root / "session-summary.json").read_text(encoding="utf-8"))
        proposal = json.loads((root / "campaign-proposal.json").read_text(encoding="utf-8"))
        source_lock = json.loads((root / "source-lock.json").read_text(encoding="utf-8"))
        coverage = json.loads((root / "evidence-objectives.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArchiveError("archive is missing its pinned source or session metadata") from exc
    if (summary.get("campaign_id") != CAMPAIGN_ID
            or summary.get("run_id") != root.name
            or summary.get("campaign_success") is not False):
        raise ArchiveError("archive campaign/run binding is invalid or claims execution success")
    pins = summary.get("source_pins")
    if (not isinstance(pins, dict)
            or hashlib.sha256((root / "campaign-proposal.json").read_bytes()).hexdigest()
            != pins.get("profile_sha256")
            or hashlib.sha256((root / "source-lock.json").read_bytes()).hexdigest()
            != pins.get("source_lock_sha256")):
        raise ArchiveError("archive source/profile pins do not match the captured metadata")
    if not isinstance(coverage.get("objectives"), list) or {
            row.get("id") for row in coverage["objectives"]} != set(OBJECTIVES):
        raise ArchiveError("archive does not contain the complete 19-objective baseline")
    return summary, proposal, source_lock, inventory


def _command_rows(proposal: dict[str, Any], serial: str) -> dict[str, set[tuple[str, ...]]]:
    try:
        import sys
        sys.path.insert(0, str(HERE))
        from comprehensive_controller import COMMAND_FIELDS, _command_shapes
        try:
            shapes = _command_shapes(proposal, serial)
        finally:
            if sys.path and sys.path[0] == str(HERE):
                sys.path.pop(0)
    except Exception as exc:
        raise ArchiveError("current pinned fixed-command planner cannot replay this archive") from exc
    result: dict[str, set[tuple[str, ...]]] = {}
    for row in shapes:
        result.setdefault(row.phase, set()).add(row.argv)
    return result


def _verify_source_revision(root: Path, source_lock: dict[str, Any], pins: dict[str, Any]) -> None:
    if (not isinstance(source_lock.get("sources"), dict)
            or source_lock.get("campaign_id") != CAMPAIGN_ID):
        raise ArchiveError("captured source lock is malformed")
    for relative, expected in source_lock["sources"].items():
        path = ROOT / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ArchiveError(f"replay requires the exact pinned public source revision: {relative}")
    if source_lock.get("command_manifest_sha256") != pins.get("command_manifest_sha256"):
        raise ArchiveError("archive manifest pin differs from the executed session")


def _compare_states(records: list[dict[str, Any]], root: Path) -> dict[str, Any]:
    """Compare raw steady-state display snapshots with the existing parser."""
    import sys
    sys.path.insert(0, str(HERE))
    try:
        from display_compare import SOURCES as DISPLAY_SOURCES, _set_delta, parse_snapshot
    finally:
        if sys.path and sys.path[0] == str(HERE):
            sys.path.pop(0)

    comparisons: dict[str, Any] = {}
    for phase in ("phase4_three_state_carplay", "phase5_display1_navigation_lifecycle",
                  "phase6_existing_hondahack_casting"):
        states: dict[str, dict[str, Any]] = {}
        for row in records:
            if row.get("phase") != phase or row.get("exit_code") != 0:
                continue
            operation = row.get("operation")
            source_filename = None
            if operation == "dumpsys":
                source_filename = {
                    "display": DISPLAY_SOURCES["display"],
                    "window": DISPLAY_SOURCES["window"],
                    "SurfaceFlinger": DISPLAY_SOURCES["surfaceflinger"],
                }.get(str(row.get("arguments", [""])[0]))
            if source_filename is None:
                continue
            state = row.get("state", "")
            raw_path = root / row.get("stdout_file", "")
            if not raw_path.is_file() or raw_path.is_symlink():
                continue
            states.setdefault(state, {})[source_filename] = raw_path.read_bytes()
        state_order = list(dict.fromkeys(r.get("state") for r in records if r.get("phase") == phase))
        if not state_order:
            continue
        baseline = state_order[0]
        base_inputs = states.get(baseline, {})
        parsed: dict[str, dict[str, Any]] = {}
        for state, raw in states.items():
            parsed[state] = parse_snapshot(root, raw_snapshots=raw)
        deltas = []
        for state in state_order:
            current = parsed.get(state, {}).get("sources", {})
            base = parsed.get(baseline, {}).get("sources", {})
            source_deltas = {}
            for source in DISPLAY_SOURCES:
                left = base.get(source, {})
                right = current.get(source, {})
                if left.get("status") != "CONFIRMED" or right.get("status") != "CONFIRMED":
                    source_deltas[source] = {"status": "UNRESOLVED",
                                             "baseline_status": left.get("status", "NOT_COLLECTED"),
                                             "state_status": right.get("status", "NOT_COLLECTED")}
                elif source == "display":
                    left_inventory = left["inventory"]
                    right_inventory = right["inventory"]
                    source_deltas[source] = {"status": "COMPARED",
                        "inventory_unchanged": left_inventory == right_inventory,
                        "baseline_inventory": left_inventory, "state_inventory": right_inventory}
                elif source == "window":
                    ids = sorted(set(left["windows_by_display_id"]) | set(right["windows_by_display_id"]))
                    source_deltas[source] = {"status": "COMPARED",
                        "windows_by_display_id": {display_id: _set_delta(
                            left["windows_by_display_id"].get(display_id, []),
                            right["windows_by_display_id"].get(display_id, [])) for display_id in ids},
                        "all_named_windows": _set_delta(left["all_named_windows"],
                                                         right["all_named_windows"])}
                else:
                    source_deltas[source] = {"status": "COMPARED",
                        "named_layers": _set_delta(left["named_layers"], right["named_layers"])}
            deltas.append({"state": state, "source_deltas": source_deltas})
        comparisons[phase] = {"baseline_state": baseline, "state_order": state_order,
                              "baseline_source_count": len(base_inputs), "deltas": deltas,
                              "interpretation": "existing bounded display parsers compare reported display inventory, WindowManager names, and SurfaceFlinger layer names; they do not establish View class/lifetime, physical scanout, protocol acceptance, or OEM ownership"}
    return comparisons


def _compare_network_states(records: list[dict[str, Any]], root: Path) -> dict[str, Any]:
    """Compare approved proc-net and usb0 snapshots without claiming FD ownership."""
    import sys
    sys.path.insert(0, str(HERE))
    try:
        from parsers import parse_proc_net, parse_proc_net_unix
    finally:
        if sys.path and sys.path[0] == str(HERE):
            sys.path.pop(0)

    table_specs = {
        "/proc/net/tcp": ("tcp4", "tcp", 4),
        "/proc/net/tcp6": ("tcp6", "tcp", 6),
        "/proc/net/udp": ("udp4", "udp", 4),
        "/proc/net/udp6": ("udp6", "udp", 6),
        "/proc/net/unix": ("unix", "unix", 0),
    }
    snapshots: dict[str, dict[str, list[str] | str]] = {}
    for row in records:
        if row.get("exit_code") != 0 or row.get("operation") not in {"read", "read_net_operstate"}:
            continue
        args = row.get("arguments", [])
        if not args:
            continue
        source = args[0]
        raw_path = root / row.get("stdout_file", "")
        if not raw_path.is_file() or raw_path.is_symlink():
            continue
        raw = raw_path.read_bytes()
        state = row.get("state", "")
        if source == "/sys/class/net/usb0/operstate":
            value = raw.decode("utf-8", "replace").strip()
            snapshots.setdefault(state, {})["usb0"] = value if value in {"up", "down", "unknown", "dormant", "lowerlayerdown", "notpresent", "testing"} else "UNRECOGNIZED"
            continue
        if source not in table_specs:
            continue
        label, protocol, family = table_specs[source]
        try:
            text = raw.decode("utf-8", "strict")
            if protocol == "unix":
                parsed = parse_proc_net_unix(text)
                rows_hashed = [hashlib.sha256(json.dumps(item, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                               for item in parsed]
            else:
                parsed = parse_proc_net(text, protocol, family)
                rows_hashed = [hashlib.sha256(json.dumps(item.__dict__, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                               for item in parsed]
            snapshots.setdefault(state, {})[label] = sorted(rows_hashed)
        except (UnicodeDecodeError, ValueError):
            snapshots.setdefault(state, {})[label] = "UNPARSEABLE"

    state_order = list(dict.fromkeys(row.get("state") for row in records))
    if not any(snapshots.values()):
        return {}
    baseline = state_order[0] if state_order else ""
    base = snapshots.get(baseline, {})
    deltas = []
    for state in state_order:
        current = snapshots.get(state, {})
        source_deltas = {}
        for source in sorted(set(base) | set(current)):
            left, right = base.get(source), current.get(source)
            if isinstance(left, list) and isinstance(right, list):
                left_set, right_set = set(left), set(right)
                source_deltas[source] = {"status": "COMPARED",
                    "baseline_entry_count": len(left), "state_entry_count": len(right),
                    "added_entry_sha256": sorted(right_set - left_set),
                    "removed_entry_sha256": sorted(left_set - right_set)}
            elif source == "usb0" and isinstance(left, str) and isinstance(right, str):
                source_deltas[source] = {"status": "COMPARED", "baseline_state": left,
                                         "state": right, "changed": left != right}
            else:
                source_deltas[source] = {"status": "UNRESOLVED",
                    "baseline_status": "COLLECTED" if left is not None else "NOT_COLLECTED",
                    "state_status": "COLLECTED" if right is not None else "NOT_COLLECTED"}
        deltas.append({"state": state, "source_deltas": source_deltas})
    return {"baseline_state": baseline, "state_order": state_order, "deltas": deltas,
            "interpretation": "proc-net tuple hashes and usb0 operational-state changes are comparative only; socket ownership requires same-phase PID-bound FD inode equality and is not inferred here"}


def analyze_archive(path: Path) -> dict[str, Any]:
    """Validate provenance/integrity and return a sanitized evidence assessment."""
    root = _private_archive(path)
    summary, proposal, source_lock, inventory = _load_archive(root)
    pins = summary["source_pins"]
    _verify_source_revision(root, source_lock, pins)
    serial = summary.get("exact_adb_serial")
    if not isinstance(serial, str) or not serial:
        raise ArchiveError("archive has no exact target serial binding")
    allowed = _command_rows(proposal, serial)
    records = summary.get("command_artifacts")
    if not isinstance(records, list) or len(records) != summary.get("command_count"):
        raise ArchiveError("command ledger is incomplete")
    seen_indices = set()
    for row in records:
        if not isinstance(row, dict):
            raise ArchiveError("command ledger row is malformed")
        index = row.get("index")
        if not isinstance(index, int) or index in seen_indices:
            raise ArchiveError("command indices are missing or duplicated")
        seen_indices.add(index)
        if tuple(row.get("argv", [])) not in allowed.get(row.get("phase"), set()):
            raise ArchiveError("captured command does not match the pinned API-17 allowlist")
        if row.get("exit_code") is None:
            if row.get("result_status") != "INTERRUPTED_OR_HOST_EXECUTION_ERROR":
                raise ArchiveError("command failure status is ambiguous")
            continue
        if (row.get("finished_monotonic_ns", 0) < row.get("started_monotonic_ns", 0)
                or row.get("stdout_bytes", 0) + row.get("stderr_bytes", 0) > MAX_ARCHIVE_FILE_BYTES):
            raise ArchiveError("command timing or output size is invalid")
        for kind in ("stdout", "stderr"):
            relative = row.get(f"{kind}_file")
            if not isinstance(relative, str) or Path(relative).name != relative:
                raise ArchiveError("command artifact path is malformed")
            raw = (root / relative).read_bytes()
            if (len(raw) != row.get(f"{kind}_bytes")
                    or hashlib.sha256(raw).hexdigest() != row.get(f"{kind}_sha256")):
                raise ArchiveError(f"command {kind} does not match the command ledger")
    if seen_indices and seen_indices != set(range(max(seen_indices) + 1)):
        raise ArchiveError("command ledger has a gap")

    comparisons = _compare_states(records, root)
    network_comparisons = _compare_network_states(records, root)
    try:
        import sys
        sys.path.insert(0, str(HERE))
        from parsers import summarize_diagnostic_logs
        try:
            log_results = []
            for row in records:
                if row.get("operation") == "logcat" and row.get("exit_code") == 0:
                    raw = (root / row["stdout_file"]).read_bytes()
                    safe = summarize_diagnostic_logs(raw)
                    log_results.append({"phase": row["phase"], "state": row["state"],
                                        "status": safe["status"],
                                        "event_counts": safe["event_counts"],
                                        "type111_status": safe["type111_status"],
                                        "interpretation_limit": safe["interpretation_limit"]})
        finally:
            if sys.path and sys.path[0] == str(HERE):
                sys.path.pop(0)
    except Exception as exc:
        raise ArchiveError("bounded offline log parser rejected the archive") from exc

    phase_set = set(summary.get("approved_phases", []))
    objective_status = {
        "ordinary-adb-identity": "COLLECTED_PENDING_OWNER_AND_TARGET_REVIEW" if "phase1_ordinary_adb_capability" in phase_set else "NOT_COLLECTED",
        "existing-root-supersu-state": "ARCHIVE_ONLY_CURRENT_RUNTIME_STATE_UNKNOWN",
        "jmcs-process-identity-continuity": "PID_CONTINUITY_ONLY_START_TIME_UNAVAILABLE" if phase_set & {"phase1_ordinary_adb_capability", "phase4_three_state_carplay", "phase5_display1_navigation_lifecycle", "phase6_existing_hondahack_casting"} else "NOT_COLLECTED",
        "jmcs-maps-smaps-protections-load-bias": "BLOCKED_PHASE3_ACCESS_METHOD_UNJUSTIFIED",
        "jmcs-loaded-library-inventory": "BLOCKED_PHASE3_ACCESS_METHOD_UNJUSTIFIED",
        "jmcs-fd-socket-owner-correlation": "BLOCKED_PHASE3_ACCESS_METHOD_UNJUSTIFIED",
        "usb0-network-phase-correlation": "COLLECTED_PENDING_STATE_DELTA_ANALYSIS" if "phase4_three_state_carplay" in phase_set else "NOT_COLLECTED",
        "carplay-info-setup-observability": "PASSIVE_LOG_MARKERS_ONLY_VALUES_NOT_EXPOSED",
        "type110-session-lifecycle": "VISIBLE_LIFECYCLE_DELTAS_ONLY" if "phase4_three_state_carplay" in phase_set else "NOT_COLLECTED",
        "type111-negotiation-and-authority": "NOT_ESTABLISHED_PASSIVE_SOURCE_HAS_NO_NEGOTIATION_AUTHORITY",
        "display-manager-inventory": "DISPLAY_SNAPSHOT_ONLY" if phase_set & {"phase5_display1_navigation_lifecycle", "phase6_existing_hondahack_casting"} else "NOT_COLLECTED",
        "display1-window-view-lifecycle": "WINDOW_AND_LAYER_DELTAS_ONLY_VIEW_LIFETIME_NOT_EXPOSED" if phase_set & {"phase5_display1_navigation_lifecycle", "phase6_existing_hondahack_casting"} else "NOT_COLLECTED",
        "surfaceflinger-layer-lifecycle": "LAYER_NAME_DELTAS_ONLY_PHYSICAL_SCANOUT_NOT_PROVEN" if phase_set & {"phase5_display1_navigation_lifecycle", "phase6_existing_hondahack_casting"} else "NOT_COLLECTED",
        "factory-navigation-transitions": "OWNER_CONFIRMED_STATES_PENDING_COMPARISON" if phase_set & {"phase4_three_state_carplay", "phase5_display1_navigation_lifecycle", "phase6_existing_hondahack_casting"} else "NOT_COLLECTED",
        "hondahack-casting-and-withdrawal": "OWNER_CONFIRMED_EXISTING_UI_STATES_PENDING_REVIEW" if "phase6_existing_hondahack_casting" in phase_set else "NOT_COLLECTED_OR_NOT_APPROVED",
        "carplay-disconnect-reconnect-restoration": "OWNER_CONFIRMED_SEQUENCE_PENDING_COMPARISON" if "phase4_three_state_carplay" in phase_set else "NOT_COLLECTED",
        "recovery-prerequisites": "OWNER_RESTORATION_CONFIRMED" if "phase7_recovery_restoration" in phase_set else "NOT_CONFIRMED",
        "instrumentation-decision": "OFFLINE_DECISION_REQUIRED_FOR_INFO_SETUP_AND_TYPE111",
        "capture-integrity-and-privacy": "SHA256_INVENTORY_AND_COMMAND_LEDGER_VERIFIED",
    }
    return {
        "campaign_id": CAMPAIGN_ID,
        "run_id": summary["run_id"],
        "archive_inventory_sha256": hashlib.sha256((root / "sha256.txt").read_bytes()).hexdigest(),
        "verified_artifact_count": len(inventory),
        "command_count": len(records),
        "approved_phases": summary.get("approved_phases", []),
        "phase_state_comparisons": comparisons,
        "network_state_comparison": network_comparisons,
        "bounded_log_summaries": log_results,
        "objective_assessment": [{"id": key, "status": value} for key, value in objective_status.items()],
        "confirmed_objective_count": 0,
        "unresolved_objective_count": len(OBJECTIVES),
        "campaign_success": False,
        "interpretation": "Execution and integrity do not establish evidence completeness. Review raw private outputs and objective-specific usability criteria offline.",
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="owner-only session archive directory")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(analyze_archive(args.archive), sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"INVALID_ARCHIVE: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
