"""Compare bounded Android display snapshots without claiming causal ownership.

The input is a host capture directory. Raw Honda snapshots and the generated
comparison are private evidence and must remain outside public Git.
"""

from __future__ import annotations

import argparse
from collections import Counter
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from typing import Any

MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024
MAX_SNAPSHOT_LINE_CHARS = 64 * 1024
SOURCES = {
    "display": "dumpsys_display.raw",
    "window": "dumpsys_window.raw",
    "surfaceflinger": "dumpsys_SurfaceFlinger.raw",
}
WINDOW_RE = re.compile(r"Window\{[0-9a-fA-F]+\s+u\d+\s*([^}]{0,512})\}")
LAYER_RE = re.compile(r"^\s*\+ Layer\s+0x[0-9a-fA-F]+\s+\((.*)\)\s*$")
LAYER_ID_SUFFIX_RE = re.compile(r"#\d+\b")
DEVICE_RE = re.compile(
    r'DisplayDeviceInfo\{"([^\"]+)":\s*(\d+)\s*x\s*(\d+).*?type\s+([A-Z_]+)'
)
BASE_INFO_RE = re.compile(
    r'mBaseDisplayInfo=DisplayInfo\{"([^\"]+)".*?layerStack\s+(\d+),\s*type\s+([A-Z_]+)'
)
DISPLAY_SECTION_RE = re.compile(r"^\s*Display:\s*mDisplayId=(\d+)\s*$")
LOGICAL_DISPLAY_ID_RE = re.compile(r"\bmDisplayId\s*=\s*(\d+)\b")
WINDOW_STATE_RE = re.compile(r"^\s*Window #\d+\s+(Window\{[0-9a-fA-F]+\s+u\d+\s*[^}]{0,512}\})\s*:")
WINDOW_STATE_DISPLAY_RE = re.compile(r"\bmDisplayId\s*=\s*(\d+)\b")


def _read_snapshot(path: Path, raw_override: bytes | None = None) -> tuple[str, dict[str, Any]]:
    if raw_override is None:
        try:
            flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(path, flags)
        except FileNotFoundError:
            return "NOT_COLLECTED", {}
        except OSError as error:
            if error.errno in {errno.EACCES, errno.EPERM}:
                return "PERMISSION_DENIED", {}
            return "FAILED", {"reason": f"snapshot_open_failed:{error.__class__.__name__}"}
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                return "FAILED", {"reason": "snapshot_not_regular_file"}
            raw = stream.read(MAX_SNAPSHOT_BYTES + 1)
    else:
        raw = raw_override
    if len(raw) > MAX_SNAPSHOT_BYTES:
        return "FAILED", {"reason": "snapshot_exceeds_4_MiB_limit"}
    if not raw.strip():
        return "FAILED", {"reason": "empty_snapshot"}
    text = raw.decode("utf-8", "replace")
    if any(len(line) > MAX_SNAPSHOT_LINE_CHARS for line in text.splitlines()):
        return "FAILED", {"reason": "snapshot_line_exceeds_64_KiB_limit"}
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if (re.match(r"(?i)^(?:permission denied|operation not permitted)\b", first)
            or re.match(r"(?i)^(?:/system/bin/sh|sh|mksh):.*\b(?:permission denied|operation not permitted)\b", first)
            or re.match(r"(?i)^(?:dumpsys: )?permission denial\b", first)):
        return "PERMISSION_DENIED", {"sha256": hashlib.sha256(raw).hexdigest()}
    if re.match(r"(?i)^(?:Can't find service:|Service .+ not found)", first):
        return "UNSUPPORTED", {"sha256": hashlib.sha256(raw).hexdigest()}
    if re.match(r"(?i)^(?:adb|error):\s*error\b", first):
        return "FAILED", {"sha256": hashlib.sha256(raw).hexdigest()}
    if text.lstrip().startswith(("/system/bin/sh:", "sh:", "mksh:")):
        return "FAILED", {"sha256": hashlib.sha256(raw).hexdigest()}
    return "CONFIRMED", {"sha256": hashlib.sha256(raw).hexdigest(), "text": text}


def _require_private_directory(path: Path, label: str) -> None:
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    try:
        info = path.stat()
    except OSError as error:
        raise ValueError(f"{label} is unavailable: {error}") from error
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077):
        raise ValueError(f"{label} must be an owner-only directory for the current user")


def _git_worktree_roots(repository: Path) -> list[Path]:
    try:
        result = subprocess.run(["git", "-C", str(repository), "worktree", "list", "--porcelain"],
                                text=True, capture_output=True, check=False, timeout=5)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError("cannot verify Git worktree locations") from error
    if result.returncode:
        raise ValueError("cannot verify Git worktree locations")
    roots = []
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            roots.append(Path(line.removeprefix("worktree ")).resolve())
    return roots


def _containing_git_root(path: Path) -> Path | None:
    try:
        result = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                                text=True, capture_output=True, check=False, timeout=5)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError("cannot verify output is outside Git repositories") from error
    if result.returncode == 0:
        return Path(result.stdout.strip()).resolve()
    return None


def _window_entities(text: str) -> tuple[dict[str, list[str]], list[str]]:
    by_display: dict[str, set[str]] = {}
    all_windows: set[str] = set()
    current_display: str | None = None
    current_window: str | None = None
    in_window_state_dump = False
    for line in text.splitlines():
        if line.startswith("WINDOW MANAGER WINDOWS ("):
            in_window_state_dump = True
            current_window = None
            current_display = None
            continue
        if line.startswith("WINDOW MANAGER ") and not line.startswith("WINDOW MANAGER WINDOWS ("):
            in_window_state_dump = False
            current_window = None
            current_display = None
            continue
        state = WINDOW_STATE_RE.match(line) if in_window_state_dump else None
        if state:
            current_window = state.group(1)
            name_match = WINDOW_RE.search(current_window)
            if name_match:
                all_windows.add(name_match.group(1).strip() or "<unnamed>")
            current_display = None
            continue
        if in_window_state_dump and current_window is not None:
            owner = WINDOW_STATE_DISPLAY_RE.search(line)
            if owner:
                current_display = owner.group(1)
                match = WINDOW_RE.search(current_window)
                if match:
                    name = match.group(1).strip() or "<unnamed>"
                    by_display.setdefault(current_display, set()).add(name)
                current_display = None
                current_window = None
                continue
            if line.strip() == "DisplayContents:":
                current_window = None
                current_display = None
                continue
        section = DISPLAY_SECTION_RE.match(line)
        if section:
            current_display = section.group(1)
            by_display.setdefault(current_display, set())
            continue
        if line and not line[0].isspace():
            current_display = None
        if re.match(r"^\s*(?:mCurrentFocus|mFocusedApp|mTopFullscreenOpaqueWindowState|Policy:)", line):
            current_display = None
        for match in WINDOW_RE.finditer(line):
            name = match.group(1).strip() or "<unnamed>"
            all_windows.add(name)
            if current_display is not None:
                by_display.setdefault(current_display, set()).add(name)
    return ({key: sorted(value) for key, value in sorted(by_display.items())},
            sorted(all_windows))


def _surface_layers(text: str) -> list[str]:
    layers = []
    for line in text.splitlines():
        match = LAYER_RE.match(line)
        if match:
            name = LAYER_ID_SUFFIX_RE.sub("#<id>", match.group(1).strip()) or "<unnamed>"
            layers.append(name)
    return sorted(layers)


def _display_inventory(text: str) -> dict[str, list[dict[str, Any]]]:
    devices = []
    base_info = []
    display_ids: set[str] = set()
    in_logical_displays = False
    for line in text.splitlines():
        if line.startswith("Logical Displays:"):
            in_logical_displays = True
        elif line and not line[0].isspace():
            in_logical_displays = False
        if in_logical_displays:
            display_ids.update(LOGICAL_DISPLAY_ID_RE.findall(line))
        device = DEVICE_RE.search(line)
        if device:
            devices.append({"name": device.group(1), "width": int(device.group(2)),
                            "height": int(device.group(3)), "type": device.group(4)})
        info = BASE_INFO_RE.search(line)
        if info:
            base_info.append({"name": info.group(1), "layer_stack": int(info.group(2)),
                              "type": info.group(3)})
    return {"display_ids": sorted(display_ids),
            "devices": sorted(devices, key=lambda item: (item["type"], item["name"])),
            "base_info": sorted(base_info, key=lambda item: (item["layer_stack"], item["name"]))}


def parse_snapshot(directory: Path, raw_snapshots: dict[str, bytes] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"sources": {}}
    for source, filename in SOURCES.items():
        raw = None if raw_snapshots is None else raw_snapshots.get(filename)
        status, payload = _read_snapshot(directory / filename, raw_override=raw)
        record: dict[str, Any] = {"status": status}
        if status != "CONFIRMED":
            record.update(payload)
            result["sources"][source] = record
            continue
        text = payload.pop("text")
        record.update(payload)
        if source == "display":
            record["inventory"] = _display_inventory(text)
            if not any(record["inventory"].values()):
                record["status"] = "UNSUPPORTED"
        elif source == "window":
            by_display, all_windows = _window_entities(text)
            record["windows_by_display_id"] = by_display
            record["all_named_windows"] = all_windows
            if not any(by_display.values()) and "WINDOW MANAGER WINDOWS (" not in text:
                record["status"] = "UNSUPPORTED"
        else:
            record["named_layers"] = _surface_layers(text)
            if not record["named_layers"]:
                record["status"] = "UNSUPPORTED"
        result["sources"][source] = record
    return result


def _set_delta(left: list[str], right: list[str]) -> dict[str, list[str]]:
    left_count, right_count = Counter(left), Counter(right)
    added = list((right_count - left_count).elements())
    removed = list((left_count - right_count).elements())
    persisting = list((left_count & right_count).elements())
    return {"added": sorted(added), "removed": sorted(removed),
            "persisting": sorted(persisting)}


def compare_capture(capture: Path, phases: list[str], target_display_id: str | None = None) -> dict[str, Any]:
    if capture.is_symlink():
        raise ValueError("capture root must not be a symlink")
    if not capture.is_dir():
        raise ValueError("capture root must be a directory")
    if len(phases) < 2 or len(phases) != len(set(phases)):
        raise ValueError("provide at least two unique ordered phases")
    if target_display_id is not None and (not re.fullmatch(r"[1-9]\d{0,3}", target_display_id)):
        raise ValueError("factory Display 1 mapping must use a positive numeric display id")
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", phase)
           or phase in {".", ".."} for phase in phases):
        raise ValueError("phase names must be safe single path segments")
    for phase in phases:
        phase_path = capture / phase
        display_path = phase_path / "display"
        if phase_path.is_symlink() or display_path.is_symlink():
            raise ValueError("phase and display directories must not be symlinks")
    integrity_status, integrity_details, verified_inputs = _verify_snapshot_hashes(capture, phases)
    if integrity_status == "VERIFIED":
        snapshots = {
            phase: parse_snapshot(
                capture / phase / "display",
                {filename: verified_inputs[f"{phase}/display/{filename}"]
                 for filename in SOURCES.values()},
            )
            for phase in phases
        }
    else:
        source_status = (integrity_status if integrity_status in {
            "NOT_COLLECTED", "PERMISSION_DENIED", "FAILED"} else "UNRESOLVED")
        snapshots = {
            phase: {"sources": {source: {"status": source_status,
                                         "reason": integrity_details.get("reason", "integrity_not_verified")}
                                 for source in SOURCES}}
            for phase in phases
        }
    deltas: dict[str, Any] = {}
    for left, right in zip(phases, phases[1:]):
        key = f"{left}_to_{right}"
        pair: dict[str, Any] = {}
        a, b = snapshots[left]["sources"], snapshots[right]["sources"]
        for source in SOURCES:
            if a[source]["status"] != "CONFIRMED" or b[source]["status"] != "CONFIRMED":
                pair[source] = {"status": "UNRESOLVED", "left_status": a[source]["status"],
                                "right_status": b[source]["status"]}
                continue
            if source == "display":
                pair[source] = {"status": "COMPARED",
                                "inventory_unchanged": a[source]["inventory"] == b[source]["inventory"],
                                "left_inventory": a[source]["inventory"],
                                "right_inventory": b[source]["inventory"]}
            elif source == "window":
                display_ids = sorted(set(a[source]["windows_by_display_id"]) |
                                     set(b[source]["windows_by_display_id"]))
                pair[source] = {
                    "status": "COMPARED",
                    "windows_by_display_id": {
                        display_id: _set_delta(
                            a[source]["windows_by_display_id"].get(display_id, []),
                            b[source]["windows_by_display_id"].get(display_id, []))
                        for display_id in display_ids
                    },
                    "all_named_windows": _set_delta(a[source]["all_named_windows"],
                                                      b[source]["all_named_windows"]),
                }
            else:
                pair[source] = {"status": "COMPARED",
                                "named_layers": _set_delta(a[source]["named_layers"],
                                                           b[source]["named_layers"])}
        deltas[key] = pair
    logical_display_id_present = bool(target_display_id) and all(
        target_display_id in snapshots[phase]["sources"]["display"].get("inventory", {}).get("display_ids", [])
        and snapshots[phase]["sources"]["window"]["status"] == "CONFIRMED"
        for phase in phases
    )
    return {
        "schema": "claritylink-display-comparison-v1",
        "phases": phases,
        "snapshots": snapshots,
        "deltas": deltas,
        "capture_integrity": {"status": integrity_status, **integrity_details},
        "target_display_id": target_display_id,
        "target_display_attribution_status": (
            "LOGICAL_DISPLAY_ID_PRESENT" if logical_display_id_present else "UNRESOLVED"
        ),
        "factory_display1_mapping_status": "NOT_VERIFIED_BY_SNAPSHOT_COMPARATOR",
        "window_presence_by_phase": {
            phase: ("WINDOWS_REPORTED" if snapshots[phase]["sources"]["window"]
                    .get("windows_by_display_id", {}).get(target_display_id or "")
                    else "NO_WINDOW_REPORTED") for phase in phases
        },
        "campaign_identity_status": "NOT_CHECKED_BY_SNAPSHOT_COMPARATOR",
        "surfaceflinger_display_attribution": "UNAVAILABLE_GLOBAL_LAYER_DUMP",
        "integrity_scope": "Only the compared snapshot files are SHA-256 checked against sha256.txt; this is not a full campaign evidence-completeness verification.",
        "comparison_status": "SNAPSHOT_COMPARISON_COMPLETE" if logical_display_id_present and integrity_status == "VERIFIED" and all(
            source["status"] == "CONFIRMED"
            for snapshot in snapshots.values() for source in snapshot["sources"].values()
        ) else "INCOMPLETE",
        "interpretation_limit": (
            "WindowManager and SurfaceFlinger names are phase-correlated observations. "
            "SurfaceFlinger names are not attributed to a display. These observations "
            "do not verify that the supplied logical display ID is factory Display 1 and do not "
            "establish causality, process identity, physical scanout, pixel contribution, "
            "or OEM-supported frame ownership."
        ),
        "privacy_note": "Output contains derived private display metadata; keep outside public Git.",
    }


def _verify_snapshot_hashes(capture: Path, phases: list[str]) -> tuple[str, dict[str, Any], dict[str, bytes]]:
    manifest = capture / "sha256.txt"
    try:
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(manifest, flags)
    except FileNotFoundError:
        return "NOT_COLLECTED", {"reason": "integrity_manifest_missing"}, {}
    except OSError as error:
        if error.errno in {errno.EACCES, errno.EPERM}:
            return "PERMISSION_DENIED", {}, {}
        return "FAILED", {"reason": f"integrity_manifest_unreadable:{error.__class__.__name__}"}, {}
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            return "FAILED", {"reason": "integrity_manifest_not_regular_file"}, {}
        raw = stream.read(MAX_SNAPSHOT_BYTES + 1)
    if len(raw) > MAX_SNAPSHOT_BYTES or not raw.strip():
        return "FAILED", {"reason": "invalid_integrity_manifest_size"}, {}
    entries: dict[str, str] = {}
    for line in raw.decode("ascii", "replace").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            return "FAILED", {"reason": "malformed_integrity_manifest"}, {}
        digest, relative = match.groups()
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != relative or relative in entries:
            return "FAILED", {"reason": "unsafe_or_duplicate_integrity_path"}, {}
        entries[relative] = digest
    checked: list[str] = []
    verified_inputs: dict[str, bytes] = {}
    for phase in phases:
        for filename in SOURCES.values():
            relative = f"{phase}/display/{filename}"
            path = capture / relative
            expected = entries.get(relative)
            if expected is None:
                return "NOT_COLLECTED", {"reason": "snapshot_missing_from_integrity_manifest"}, {}
            try:
                flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
                if hasattr(os, "O_NOFOLLOW"):
                    flags |= os.O_NOFOLLOW
                descriptor = os.open(path, flags)
            except OSError as error:
                return ("PERMISSION_DENIED" if error.errno in {errno.EACCES, errno.EPERM}
                        else "FAILED"), {"reason": "snapshot_unreadable_or_symlink"}, {}
            with os.fdopen(descriptor, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode):
                    return "FAILED", {"reason": "snapshot_not_regular_file"}, {}
                raw_snapshot = stream.read(MAX_SNAPSHOT_BYTES + 1)
            if len(raw_snapshot) > MAX_SNAPSHOT_BYTES:
                return "FAILED", {"reason": "snapshot_exceeds_4_MiB_limit"}, {}
            if not raw_snapshot.strip():
                return "FAILED", {"reason": "empty_snapshot"}, {}
            digest = hashlib.sha256(raw_snapshot).hexdigest()
            if digest != expected:
                return "FAILED", {"reason": "snapshot_hash_mismatch"}, {}
            checked.append(relative)
            verified_inputs[relative] = raw_snapshot
    return "VERIFIED", {"manifest_sha256": hashlib.sha256(raw).hexdigest(),
                         "verified_snapshot_count": len(checked)}, verified_inputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--phase", action="append", dest="phases",
                        help="phase directory, repeated in intended chronological order")
    parser.add_argument("--target-display-id", required=True,
                        help="reviewed Android display id corresponding to factory Display 1")
    parser.add_argument("--output", type=Path,
                        help="private output path (default: inside the owner-only capture directory)")
    args = parser.parse_args()
    if args.phases is None:
        parser.error("at least two --phase values are required in chronological order")
    try:
        if args.capture.is_symlink():
            raise ValueError("capture root must not be a symlink")
        _require_private_directory(args.capture, "capture root")
        result = compare_capture(args.capture, args.phases, args.target_display_id)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    output = args.output or args.capture / "display-comparison.json"
    repository = Path(__file__).resolve().parents[2]
    output_resolved = output.resolve()
    try:
        parent = output.parent.resolve(strict=True)
        if any(output_resolved == root or root in output_resolved.parents
               for root in _git_worktree_roots(repository)):
            parser.error("comparison output must remain outside all Git worktrees")
        if _containing_git_root(parent) is not None:
            parser.error("comparison output parent is inside a Git worktree")
        _require_private_directory(parent, "comparison output directory")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    if output.exists():
        parser.error("refusing to overwrite an existing comparison")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(output, flags, 0o600)
    except FileExistsError:
        parser.error("refusing to overwrite an existing comparison")
    except OSError as error:
        parser.error(f"cannot create private comparison output: {error.__class__.__name__}")
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException as error:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            output.unlink()
        except OSError:
            pass
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        parser.error(f"cannot write private comparison output; partial file removed: {error.__class__.__name__}")
    print(json.dumps({"comparison_status": result["comparison_status"],
                      "phase_count": len(result["phases"]),
                      "delta_count": len(result["deltas"]),
                      "output": str(output)}))
    return 0 if result["comparison_status"] == "SNAPSHOT_COMPARISON_COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
