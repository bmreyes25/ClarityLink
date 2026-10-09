#!/usr/bin/env python3
"""Offline integrity/mode gate for the canonical future Test A artifact."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import sys

EXPECTED_SHA256 = "f2e12aafe221ff51e153ccc7c1b71402cf3cf0c3a4f1648fb5963e2e66cffca0"
EXPECTED_MODE = 0o755
DEFAULT_PATH = Path(__file__).resolve().parents[1] / "build/r7e1/native-armv7/claritylink-target-diag"


def inspect(path: Path) -> tuple[str, str, int]:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), hashlib.md5(data).hexdigest(), path.stat().st_mode & 0o777


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    try:
        sha256, md5, mode = inspect(args.path)
    except OSError as exc:
        print(f"ARTIFACT_CHECK_FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"path={args.path}")
    print(f"sha256={sha256}")
    print(f"md5={md5} (transport consistency only)")
    print(f"mode={mode:04o}")
    if sha256 != EXPECTED_SHA256 or mode != EXPECTED_MODE:
        print("ARTIFACT_CHECK_FAILED: canonical SHA-256 or intended mode mismatch", file=sys.stderr)
        return 1
    print("ARTIFACT_CHECK_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
