#!/usr/bin/env python3
"""Semantic /info differential; emits field paths and type families, never values."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

KNOWN = {"sourceVersion", "features", "statusFlags", "model", "manufacturer", "deviceID",
    "bluetoothIDs", "name", "rightHandDrive", "keepAliveLowPower", "keepAliveSendStatsAsBody",
    "modes", "resources", "resourceID", "transferType", "transferPriority", "takeConstraint",
    "borrowConstraint", "unborrowConstraint", "appStates", "appStateID", "state", "speechMode",
    "audioFormats", "audioLatencies", "audioType", "audioOutputFormats", "audioInputFormats",
    "inputLatencyMicros", "outputLatencyMicros", "hidDevices", "displays", "uuid", "type",
    "maxFPS", "widthPixels", "heightPixels", "widthPhysical", "heightPhysical", "primaryInputDevice",
    "viewAreas", "initialViewArea", "originXPixels", "originYPixels", "safeArea",
    "drawUIOutsideSafeArea", "initialURL", "extendedFeatures", "hevcInfo"}
MAX_BYTES = 1_000_000


def family(value: Any) -> str:
    if isinstance(value, bool): return "boolean"
    if isinstance(value, int): return "integer"
    if isinstance(value, str): return "string"
    if isinstance(value, bytes): return "bytes"
    if isinstance(value, list): return "array"
    if isinstance(value, dict): return "dictionary"
    if value is None: return "null"
    return "unsupported"


def compare(known: Any, candidate: Any) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = {key: [] for key in (
        "missing_fields", "extra_fields", "type_mismatch", "value_family_mismatch",
        "display_mismatch", "feature_mismatch", "unknown_field")}

    def walk(left: Any, right: Any, path: str, depth: int) -> None:
        if depth > 12:
            findings["value_family_mismatch"].append(path + ".depth_limit")
            return
        if family(left) != family(right):
            findings["type_mismatch"].append(path or "<root>")
            return
        if isinstance(left, Mapping):
            for key in left.keys() | right.keys():
                if not isinstance(key, str) or key not in KNOWN:
                    findings["unknown_field"].append((path + ".<unknown-field>").strip("."))
                    continue
                child = (path + "." + key).strip(".")
                if key not in right:
                    findings["missing_fields"].append(child)
                elif key not in left:
                    findings["extra_fields"].append(child)
                else:
                    walk(left[key], right[key], child, depth + 1)
        elif isinstance(left, list):
            if len(left) != len(right):
                bucket = "display_mismatch" if path.endswith("displays") else "value_family_mismatch"
                findings[bucket].append(path + ".count")
            for index, (item_left, item_right) in enumerate(zip(left[:32], right[:32])):
                walk(item_left, item_right, path + f"[{index}]", depth + 1)
        elif path.endswith("features") and left != right:
            findings["feature_mismatch"].append(path)
        elif (any(path.endswith("." + field) for field in
                  ("type", "widthPixels", "heightPixels", "widthPhysical", "heightPhysical", "maxFPS"))
              and "displays[" in path and left != right):
            findings["display_mismatch"].append(path)
        elif path.endswith(("sourceVersion", "model", "manufacturer", "deviceID", "name", "uuid")):
            # Independently generated identities need only have the same type family.
            pass
        elif left != right and family(left) in ("integer", "boolean"):
            findings["value_family_mismatch"].append(path)
    walk(known, candidate, "", 0)
    return {key: sorted(set(value)) for key, value in findings.items()}


def load(path: Path) -> Any:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("info_file_too_large")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Sanitized semantic CarPlay /info comparison")
    parser.add_argument("known", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(load(args.known), load(args.candidate)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
