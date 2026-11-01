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


PACKAGE_NOT_INSTALLED_RE = re.compile(
    r"(?i)(?:unable to find package|unknown package|package(?:\s+[^\r\n]*)?\s+not found|no package)"
)


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


def _summarize_baseline_inventory(records: list[dict[str, Any]], root: Path) -> dict[str, Any]:
    """Extract bounded, non-payload identity facts from one-time Phase 1 output."""
    summary: dict[str, Any] = {"service_list": {"status": "NOT_COLLECTED"},
        "graphics_nodes": {"status": "NOT_COLLECTED"}, "packages": []}
    package_rows: dict[str, dict[str, Any]] = {}
    for row in records:
        if row.get("phase") != "phase1_ordinary_adb_capability":
            continue
        operation, args = row.get("operation"), row.get("arguments", [])
        relative = row.get("stdout_file")
        raw = b""
        if isinstance(relative, str):
            candidate = root / relative
            if candidate.is_file() and not candidate.is_symlink():
                raw = candidate.read_bytes()
        stderr = b""
        stderr_relative = row.get("stderr_file")
        if isinstance(stderr_relative, str):
            candidate = root / stderr_relative
            if candidate.is_file() and not candidate.is_symlink():
                stderr = candidate.read_bytes()
        if operation == "service-list":
            match = re.search(rb"(?im)^Found ([0-9]+) services?:\s*$", raw)
            relevant = []
            for line in raw.decode("utf-8", "replace").splitlines():
                service = re.match(r"^\s*[0-9]+\s+(.+?):\s*\[", line)
                if service and re.search(r"navigation|externaldisplay|carplay", service.group(1), re.I):
                    relevant.append(service.group(1))
            summary["service_list"] = {"status": "OBSERVED" if match else row.get("result_status", "UNRESOLVED"),
                "reported_service_count": int(match.group(1)) if match else None,
                "relevant_service_names": sorted(set(relevant)),
                "stdout_sha256": hashlib.sha256(raw).hexdigest() if raw else None}
        elif operation == "list" and args == ["/sys/class/graphics"]:
            output_text = (raw + b"\n" + stderr).decode("utf-8", "replace")
            unavailable = re.search(r"(?i)(no such file|permission denied|not found)", output_text)
            names = sorted({name for name in re.findall(r"(?<![A-Za-z0-9_.-])([A-Za-z0-9_.-]+)(?![A-Za-z0-9_.-])",
                       raw.decode("utf-8", "replace")) if name != "total"}) if not unavailable else []
            summary["graphics_nodes"] = {"status": ("UNAVAILABLE_OR_DENIED" if unavailable else
                "OBSERVED" if row.get("exit_code") == 0 else row.get("result_status", "UNRESOLVED")),
                "entry_names": names, "stdout_sha256": hashlib.sha256(raw).hexdigest() if raw else None,
                "interpretation": "kernel graphics class names only; does not establish access, ownership, or physical scanout"}
        elif operation == "dumpsys" and len(args) == 2 and args[0] == "package":
            package = args[1]
            text = raw.decode("utf-8", "replace")
            entry = package_rows.setdefault(package, {"package": package, "metadata_status": "NOT_COLLECTED",
                "apk_path_status": "NOT_COLLECTED", "apk_path": None})
            version_code = re.search(r"\bversionCode=([0-9]+)", text)
            version_name = re.search(r"\bversionName=([^\s]+)", text)
            code_path = re.search(r"\bcodePath=([^\s]+)", text)
            absent = PACKAGE_NOT_INSTALLED_RE.search(text)
            entry.update({"metadata_status": ("PACKAGE_NOT_INSTALLED" if absent else
                "OBSERVED" if row.get("exit_code") == 0 and package.encode() in raw
                else row.get("result_status", "UNRESOLVED")),
                "version_code": version_code.group(1) if version_code else None,
                "version_name": version_name.group(1) if version_name else None,
                "code_path": code_path.group(1) if code_path else None,
                "metadata_stdout_sha256": hashlib.sha256(raw).hexdigest() if raw else None})
        elif operation == "package-path" and len(args) == 1:
            package = args[0]
            entry = package_rows.setdefault(package, {"package": package, "metadata_status": "NOT_COLLECTED",
                "apk_path_status": "NOT_COLLECTED", "apk_path": None})
            match = re.fullmatch(r"\s*package:(/(?:system|data|vendor|product)/[^\s:]+\.apk)\s*", raw.decode("utf-8", "replace"))
            absent = PACKAGE_NOT_INSTALLED_RE.search(raw.decode("utf-8", "replace"))
            entry.update({"apk_path_status": ("PACKAGE_NOT_INSTALLED" if absent else
                "OBSERVED" if row.get("exit_code") == 0 and match else row.get("result_status", "UNRESOLVED")),
                "apk_path": match.group(1) if match else None,
                "apk_path_stdout_sha256": hashlib.sha256(raw).hexdigest() if raw else None})
    summary["packages"] = [package_rows[name] for name in sorted(package_rows)]
    summary["interpretation"] = "baseline inventory preserves package identity/version/path and relevant binder-service names; it does not prove runtime ownership or Type111 support"
    return summary


LIFECYCLE_STATES = (
    "disconnected_baseline", "stock_carplay_connected", "navigation_selected",
    "navigation_deselected", "navigation_reselected", "disconnected_again",
    "stock_carplay_reconnected", "navigation_selected_after_reconnect",
    "navigation_deselected_after_reconnect", "final_disconnected",
)
LIFECYCLE_OPERATIONS = (
    ("ps", ()), ("dumpsys", ("activity", "activities")),
    ("dumpsys", ("activity", "services")), ("dumpsys", ("display",)),
    ("dumpsys", ("SurfaceFlinger",)), ("dumpsys", ("window",)),
    ("read", ("/proc/net/tcp",)), ("read", ("/proc/net/tcp6",)),
    ("read", ("/proc/net/udp",)), ("read", ("/proc/net/udp6",)),
    ("read", ("/proc/net/unix",)),
    ("read_net_operstate", ("/sys/class/net/usb0/operstate",)), ("logcat", ()),
)


def _session_coverage(summary: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive evidence presence from recorded owner confirmations and results."""
    confirmations = summary.get("owner_state_confirmations", [])
    confirmed_states = {(row.get("phase"), row.get("state")) for row in confirmations
                        if isinstance(row, dict) and row.get("status") == "OWNER_CONFIRMED_STABLE"}
    by_command = {(row.get("phase"), row.get("state"), row.get("operation"),
                   tuple(row.get("arguments", []))): row for row in records if isinstance(row, dict)}
    phase4_state_rows: dict[str, dict[str, Any]] = {}
    for state in LIFECYCLE_STATES:
        state_rows = [by_command.get(("phase4_three_state_carplay", state, operation, args))
                      for operation, args in LIFECYCLE_OPERATIONS]
        present = [row for row in state_rows if row is not None]
        successful_core = all(
            (row := by_command.get(("phase4_three_state_carplay", state, operation, args))) is not None
            and row.get("result_status") == "success"
            for operation, args in LIFECYCLE_OPERATIONS[:6]
        )
        phase4_state_rows[state] = {"owner_confirmed": ("phase4_three_state_carplay", state) in confirmed_states,
            "commands_expected": len(LIFECYCLE_OPERATIONS), "commands_recorded": len(present),
            "core_process_activity_display_success": successful_core,
            "all_commands_success": len(present) == len(LIFECYCLE_OPERATIONS)
                and all(row.get("result_status") == "success" for row in present)}
    phase4_complete = all(row["owner_confirmed"] and row["commands_recorded"] == row["commands_expected"]
                          and row["all_commands_success"]
                          for row in phase4_state_rows.values())
    phase4_core_complete = all(row["owner_confirmed"] and row["core_process_activity_display_success"]
                               for row in phase4_state_rows.values())
    phase7_confirmed = any(isinstance(row, dict) and row.get("phase") == "phase7_recovery_restoration"
        and row.get("status") == "FACTORY_RESTORATION_CONFIRMED" for row in confirmations)
    phase7_final_confirmed = any(isinstance(row, dict) and row.get("phase") == "phase7_recovery_restoration"
        and row.get("status") == "FACTORY_RESTORATION_CONFIRMED_AFTER_READS" for row in confirmations)
    phase7_records = [row for row in records if row.get("phase") == "phase7_recovery_restoration"
                      and row.get("state") == "factory_restoration"]
    phase7_complete = (phase7_confirmed and phase7_final_confirmed
        and len(phase7_records) == len(LIFECYCLE_OPERATIONS)
        and all(row.get("result_status") == "success" for row in phase7_records))
    phase1_identity_ops = [
        ("property", (name,)) for name in ("ro.build.version.release", "ro.build.version.sdk",
            "ro.product.device", "ro.product.board", "ro.hardware")
    ] + [("id", ()), ("ps", ())]
    phase1_identity_complete = all(
        (row := by_command.get(("phase1_ordinary_adb_capability", "single_phase_capture", operation, args))) is not None
        and row.get("result_status") == "success" for operation, args in phase1_identity_ops
    )
    network_all_states = all(
        (row := by_command.get(("phase4_three_state_carplay", state, operation, args))) is not None
        and row.get("result_status") == "success"
        for state in LIFECYCLE_STATES for operation, args in LIFECYCLE_OPERATIONS[6:12]
    )
    return {"phase1_identity_complete": phase1_identity_complete,
        "phase4_state_coverage": phase4_state_rows, "phase4_all_states_recorded": phase4_complete,
        "phase4_core_snapshots_complete": phase4_core_complete,
        "phase4_network_snapshots_complete": network_all_states,
        "phase7_restoration_confirmed": phase7_complete}


def _compare_states(records: list[dict[str, Any]], root: Path) -> dict[str, Any]:
    """Compare display snapshots and ActivityManager component mentions."""
    import sys
    sys.path.insert(0, str(HERE))
    try:
        from display_compare import SOURCES as DISPLAY_SOURCES, _set_delta, parse_snapshot
    finally:
        if sys.path and sys.path[0] == str(HERE):
            sys.path.pop(0)

    comparisons: dict[str, Any] = {}
    for phase in ("phase4_three_state_carplay", "phase7_recovery_restoration"):
        phase_records = [r for r in records if r.get("phase") == phase]
        if phase == "phase7_recovery_restoration":
            phase_records += [r for r in records if r.get("phase") == "phase4_three_state_carplay"
                              and r.get("state") == "disconnected_baseline"]
        states: dict[str, dict[str, Any]] = {}
        for row in phase_records:
            if row.get("exit_code") != 0:
                continue
            operation = row.get("operation")
            source_filename = None
            if operation == "dumpsys" and row.get("arguments", [""])[0] in {"display", "window", "SurfaceFlinger"}:
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
        state_order = list(dict.fromkeys(r.get("state") for r in phase_records))
        if phase == "phase7_recovery_restoration" and "disconnected_baseline" in states:
            state_order = ["disconnected_baseline"] + [state for state in state_order
                if state != "disconnected_baseline"]
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
    # ActivityManager output is variable OEM text. Compare normalized token sets
    # and hashes only; do not interpret tokens as authoritative ownership edges.
    activity_deltas: dict[str, Any] = {}
    for phase in ("phase1_ordinary_adb_capability", "phase4_three_state_carplay",
                  "phase7_recovery_restoration"):
        snapshots: dict[str, dict[str, set[str]]] = {}
        for row in records:
            in_phase = row.get("phase") == phase
            restoration_baseline = (phase == "phase7_recovery_restoration"
                and row.get("phase") == "phase4_three_state_carplay"
                and row.get("state") == "disconnected_baseline")
            if (not in_phase and not restoration_baseline) or row.get("exit_code") != 0 or row.get("operation") != "dumpsys":
                continue
            args = row.get("arguments", [])
            label = {("activity", "activities"): "activities",
                     ("activity", "services"): "services"}.get(tuple(args))
            if not label:
                continue
            path = root / row.get("stdout_file", "")
            if not path.is_file() or path.is_symlink():
                continue
            raw = path.read_bytes()
            tokens = set(re.findall(rb"[A-Za-z0-9_.$]+", raw))
            snapshots.setdefault(str(row.get("state", "")), {})[label] = {
                hashlib.sha256(token).hexdigest() for token in tokens
            }
        order = list(dict.fromkeys(r.get("state") for r in records
                     if r.get("phase") == phase or (phase == "phase7_recovery_restoration"
                     and r.get("phase") == "phase4_three_state_carplay"
                     and r.get("state") == "disconnected_baseline")))
        if phase == "phase7_recovery_restoration" and "disconnected_baseline" in snapshots:
            order = ["disconnected_baseline"] + [state for state in order
                if state != "disconnected_baseline"]
        if not order:
            continue
        baseline = snapshots.get(order[0], {})
        deltas = []
        for state in order:
            current = snapshots.get(state, {})
            row_delta = {}
            for source in ("activities", "services"):
                left, right = baseline.get(source), current.get(source)
                row_delta[source] = ({"status": "COMPARED", "baseline_token_count": len(left),
                    "state_token_count": len(right), "added_token_sha256": sorted(right - left),
                    "removed_token_sha256": sorted(left - right)} if left is not None and right is not None
                    else {"status": "UNRESOLVED", "baseline_collected": left is not None,
                          "state_collected": right is not None})
            deltas.append({"state": state, "component_token_deltas": row_delta})
        activity_deltas[phase] = {"baseline_state": order[0], "state_order": order,
            "deltas": deltas, "interpretation": "normalized ActivityManager text-token deltas are correlation clues only; they do not prove service ownership, display assignment, or protocol handling"}
    comparisons["activity_service_relationship_proxies"] = activity_deltas
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
        if (row.get("phase") not in {"phase4_three_state_carplay", "phase7_recovery_restoration"}
                or row.get("exit_code") != 0 or row.get("operation") not in {"read", "read_net_operstate"}):
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

    state_order = list(dict.fromkeys(row.get("state") for row in records
                       if row.get("phase") in {"phase4_three_state_carplay", "phase7_recovery_restoration"}))
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
    budget = summary.get("session_output_budget")
    if (not isinstance(budget, dict) or budget.get("limit_bytes") != 158400512
            or type(budget.get("used_bytes")) is not int
            or not 0 <= budget["used_bytes"] <= budget["limit_bytes"]
            or type(budget.get("commands_started")) is not int
            or not 0 <= budget["commands_started"] <= 162):
        raise ArchiveError("aggregate output budget ledger is missing or outside the reviewed bounds")
    seen_indices = set()
    accounted_output_bytes = 0
    started_commands = 0
    for row in records:
        if not isinstance(row, dict):
            raise ArchiveError("command ledger row is malformed")
        index = row.get("index")
        if not isinstance(index, int) or index in seen_indices:
            raise ArchiveError("command indices are missing or duplicated")
        seen_indices.add(index)
        if isinstance(row.get("started_monotonic_ns"), int):
            started_commands += 1
        if tuple(row.get("argv", [])) not in allowed.get(row.get("phase"), set()):
            raise ArchiveError("captured command does not match the pinned API-17 allowlist")
        failure_status = row.get("result_status")
        if failure_status in {"SESSION_OUTPUT_BUDGET_EXCEEDED",
                              "SESSION_OUTPUT_BUDGET_EXHAUSTED_BEFORE_COMMAND",
                              "PER_COMMAND_OUTPUT_LIMIT_EXCEEDED",
                              "PRIVATE_EVIDENCE_WRITE_FAILED"}:
            if row.get("stdout_file") is not None or row.get("stderr_file") is not None:
                raise ArchiveError("failed budget/write command must not claim archived output")
            if failure_status == "PRIVATE_EVIDENCE_WRITE_FAILED":
                observed = row.get("stdout_bytes_observed", -1) + row.get("stderr_bytes_observed", -1)
                if (observed != row.get("session_output_bytes_reserved")
                        or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("stdout_sha256", "")))
                        or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("stderr_sha256", "")))):
                    raise ArchiveError("private write failure lacks truthful output accounting metadata")
                accounted_output_bytes += observed
            elif failure_status in {"SESSION_OUTPUT_BUDGET_EXCEEDED", "PER_COMMAND_OUTPUT_LIMIT_EXCEEDED"}:
                observed = row.get("stdout_bytes_observed", -1) + row.get("stderr_bytes_observed", -1)
                if (observed < 0
                        or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("stdout_sha256", "")))
                        or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("stderr_sha256", "")))):
                    raise ArchiveError("rejected output lacks truthful failure metadata")
            continue
        if row.get("exit_code") is None:
            if row.get("result_status") != "INTERRUPTED_OR_HOST_EXECUTION_ERROR":
                raise ArchiveError("command failure status is ambiguous")
            if row.get("stdout_file") is not None or row.get("stderr_file") is not None:
                raise ArchiveError("interrupted command unexpectedly references output files")
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
            accounted_output_bytes += len(raw)
    if (accounted_output_bytes != budget["used_bytes"]
            or started_commands != budget["commands_started"]):
        raise ArchiveError("aggregate output/command counters do not match archived bytes and explicit write-failure accounting")
    if seen_indices and seen_indices != set(range(max(seen_indices) + 1)):
        raise ArchiveError("command ledger has a gap")

    comparisons = _compare_states(records, root)
    network_comparisons = _compare_network_states(records, root)
    baseline_inventory = _summarize_baseline_inventory(records, root)
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

    coverage_status = _session_coverage(summary, records)
    lifecycle_observed = coverage_status["phase4_core_snapshots_complete"]
    lifecycle_full = coverage_status["phase4_all_states_recorded"]
    nav_states = coverage_status["phase4_state_coverage"]
    nav_transitions = all(nav_states[state]["owner_confirmed"]
        and nav_states[state]["core_process_activity_display_success"] for state in (
            "navigation_selected", "navigation_deselected", "navigation_reselected",
            "navigation_selected_after_reconnect", "navigation_deselected_after_reconnect"))
    display_status = "OBSERVED_PENDING_COMPARISON" if lifecycle_observed else "PARTIAL_OR_NOT_COLLECTED"
    lifecycle_status = "OWNER_CONFIRMED_CORE_SNAPSHOTS_PENDING_COMPARISON" if lifecycle_observed else "PARTIAL_OR_NOT_COLLECTED"
    objective_status = {
        "ordinary-adb-identity": "IDENTITY_COMMANDS_CAPTURED_PENDING_TARGET_REVIEW" if coverage_status["phase1_identity_complete"] else "PARTIAL_OR_NOT_COLLECTED",
        "existing-root-supersu-state": "ARCHIVE_ONLY_CURRENT_RUNTIME_STATE_UNKNOWN",
        "jmcs-process-identity-continuity": "PID_SNAPSHOTS_CAPTURED_START_TIME_UNAVAILABLE" if any(row.get("operation") == "ps" and row.get("result_status") == "success" for row in records) else "NOT_COLLECTED",
        "jmcs-maps-smaps-protections-load-bias": "BLOCKED_PHASE3_ACCESS_METHOD_UNJUSTIFIED",
        "jmcs-loaded-library-inventory": "BLOCKED_PHASE3_ACCESS_METHOD_UNJUSTIFIED",
        "jmcs-fd-socket-owner-correlation": "BLOCKED_PHASE3_ACCESS_METHOD_UNJUSTIFIED",
        "usb0-network-phase-correlation": "ALL_STATE_TABLE_COMMANDS_CAPTURED_PENDING_DELTA_ANALYSIS" if coverage_status["phase4_network_snapshots_complete"] else "PARTIAL_OR_PERMISSION_OR_PARSE_GAPS",
        "carplay-info-setup-observability": "PASSIVE_LOG_MARKERS_ONLY_VALUES_NOT_EXPOSED",
        "type110-session-lifecycle": "OWNER_CONFIRMED_CORE_SNAPSHOTS_PENDING_COMPARISON" if lifecycle_full else "PARTIAL_OR_NOT_COLLECTED",
        "type111-negotiation-and-authority": "NOT_ESTABLISHED_PASSIVE_SOURCE_HAS_NO_NEGOTIATION_AUTHORITY",
        "display-manager-inventory": display_status,
        "display1-window-view-lifecycle": "WINDOW_AND_LAYER_DELTAS_ONLY_VIEW_LIFETIME_NOT_EXPOSED" if lifecycle_observed else "PARTIAL_OR_NOT_COLLECTED",
        "surfaceflinger-layer-lifecycle": "LAYER_NAME_DELTAS_ONLY_PHYSICAL_SCANOUT_NOT_PROVEN" if lifecycle_observed else "PARTIAL_OR_NOT_COLLECTED",
        "factory-navigation-transitions": "SELECTED_DESELECTED_TRANSITIONS_CAPTURED_PENDING_COMPARISON" if nav_transitions else "PARTIAL_OR_NOT_COLLECTED",
        "hondahack-casting-and-withdrawal": "EXCLUDED_FROM_ORDINARY_ADB_CAMPAIGN",
        "carplay-disconnect-reconnect-restoration": "OWNER_CONFIRMED_SEQUENCE_PENDING_COMPARISON" if lifecycle_full and coverage_status["phase7_restoration_confirmed"] else "PARTIAL_OR_NOT_COLLECTED",
        "recovery-prerequisites": "OWNER_RESTORATION_CONFIRMED_AND_SNAPSHOTS_CAPTURED" if coverage_status["phase7_restoration_confirmed"] else "NOT_CONFIRMED_OR_INCOMPLETE",
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
        "baseline_inventory": baseline_inventory,
        "session_coverage": coverage_status,
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
