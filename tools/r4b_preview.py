#!/usr/bin/env python3
"""Print deterministic JSON snapshots from checked-in synthetic R4B fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/claritylink-renderer"))
from turn_cards import ColorMode, Route, render_card  # noqa: E402


def main() -> int:
    fixtures = json.loads((ROOT / "tests/fixtures/r4b_turn_cards.json").read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=sorted(fixtures), help="one synthetic scenario; default: all")
    args = parser.parse_args()
    names = [args.fixture] if args.fixture else sorted(fixtures)
    output = {}
    for name in names:
        raw = fixtures[name]
        output[name] = render_card(Route.from_mapping(raw["route"]), raw["now_s"], ColorMode(raw["mode"])).to_dict()
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
