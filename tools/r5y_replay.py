#!/usr/bin/env python3
"""Replay allowlisted synthetic R5Y JSON fixtures on the host only."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = (ROOT / "tests" / "fixtures" / "r5y").resolve()
sys.path.insert(0, str(ROOT / "src" / "claritylink-sandbox"))

from r5y_receiver_core.replay import replay_document  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: r5y_replay.py tests/fixtures/r5y/<name>.json", file=sys.stderr)
        return 2
    path = (ROOT / argv[1]).resolve()
    if not path.is_relative_to(FIXTURES) or path.suffix != ".json" or not path.is_file():
        print("fixture must be a JSON file under tests/fixtures/r5y", file=sys.stderr)
        return 2
    if path.stat().st_size > 65536:
        print("fixture is too large", file=sys.stderr)
        return 2
    document = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(replay_document(document), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
