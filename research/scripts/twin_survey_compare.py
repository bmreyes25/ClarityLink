#!/usr/bin/env python3
"""Summarize two saved, read-only infotainment surveys without contacting the car."""

import argparse
import hashlib
import json
from pathlib import Path
import re


CAPTURE_ROOT = Path(__file__).resolve().parent.parent / "captures"
SIGNAL = re.compile(
    r"carplay|hondahack|externaldisplay|surface|layer|hdmi|audio|focus|route|navigation|navi|display|stream",
    re.IGNORECASE,
)
MAX_CHANGED_LINES = 80


def checked_folder(path):
    folder = path.resolve()
    if CAPTURE_ROOT.resolve() not in folder.parents:
        raise ValueError("Survey must be inside research/captures")
    if not (folder / "manifest.json").is_file():
        raise ValueError("Missing survey manifest")
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest.get("phase") != "twin-survey":
        raise ValueError("Expected a twin-survey manifest")
    return folder, manifest


def entries(folder, manifest):
    result = {}
    for command in manifest.get("commands", []):
        name = command.get("file")
        if not isinstance(name, str) or name in result or Path(name).name != name:
            raise ValueError("Invalid or duplicate manifest filename")
        file = folder / name
        if command.get("exitCode") == 0 and file.is_file():
            data = file.read_bytes()
            result[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        else:
            result[name] = {"unavailable": True, "exitCode": command.get("exitCode")}
    return result


def signal_lines(folder, name):
    file = folder / name
    if not file.is_file() or file.suffix != ".txt":
        return set()
    return {line.strip()[:300] for line in file.read_text(errors="replace").splitlines()
            if SIGNAL.search(line) and line.strip()}


def compare(off_path, on_path):
    off_folder, off_manifest = checked_folder(off_path)
    on_folder, on_manifest = checked_folder(on_path)
    off_entries = entries(off_folder, off_manifest)
    on_entries = entries(on_folder, on_manifest)
    changed = {}
    for name in sorted(off_entries.keys() | on_entries.keys()):
        left = off_entries.get(name)
        right = on_entries.get(name)
        if left == right:
            continue
        item = {"castingOff": left, "castingOn": right}
        if name.endswith(".txt"):
            off_lines = signal_lines(off_folder, name) if left and "sha256" in left else set()
            on_lines = signal_lines(on_folder, name) if right and "sha256" in right else set()
            removed = off_lines - on_lines
            added = on_lines - off_lines
            item["signalLinesOffOnly"] = sorted(removed)[:MAX_CHANGED_LINES]
            item["signalLinesOnOnly"] = sorted(added)[:MAX_CHANGED_LINES]
            item["signalLinesTruncated"] = len(removed) > MAX_CHANGED_LINES or len(added) > MAX_CHANGED_LINES
        changed[name] = item
    return {
        "kind": "infotainment-twin-survey-diff",
        "offStartedUtc": off_manifest.get("startedUtc"),
        "onStartedUtc": on_manifest.get("startedUtc"),
        "changedFiles": changed,
        "interpretation": "Hash/line differences are observations, not proof of signal ownership or CarPlay cluster support.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--off", required=True, type=Path, help="casting-off twin-survey folder")
    parser.add_argument("--on", required=True, type=Path, help="casting-on twin-survey folder")
    parser.add_argument("--output", required=True, type=Path, help="JSON file inside research/captures")
    args = parser.parse_args()
    output = args.output.resolve()
    if CAPTURE_ROOT.resolve() not in output.parents:
        parser.error("Output must be inside research/captures")
    result = compare(args.off, args.on)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"output": str(output), "changedFiles": len(result["changedFiles"])}, indent=2))


if __name__ == "__main__":
    main()
