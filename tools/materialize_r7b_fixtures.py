#!/usr/bin/env python3
"""Verify and materialize the checked-in text-only R7B binary fixtures."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
args = parser.parse_args()
vectors_path = root / "tests/fixtures/r7b/vectors.json"
vectors = json.loads(vectors_path.read_text())
fixture_root = vectors_path.parent
args.output.mkdir(parents=True, exist_ok=True)
for stream in vectors["setup"]:
    name = stream["fixture"]
    if Path(name).name != name or not name.endswith(".b64"):
        raise SystemExit("invalid fixture path")
    encoded = (fixture_root / name).read_text().strip().encode("ascii")
    payload = base64.b64decode(encoded, validate=True)
    if not payload or len(payload) > 2 * 1024 * 1024:
        raise SystemExit(f"invalid fixture length: {name}")
    actual = hashlib.sha256(payload).hexdigest()
    if actual != stream["sha256"]:
        raise SystemExit(f"fixture checksum mismatch: {name}")
    target = args.output / name.removesuffix(".b64")
    target.write_bytes(payload)
    print(f"{name}: verified SHA-256 {actual}")
