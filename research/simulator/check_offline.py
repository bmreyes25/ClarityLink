#!/usr/bin/env python3
"""Repeatable offline checks. Private assets are required for capture tests."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SIMULATOR = ROOT / "research/simulator"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", action="store_true", help="Also run local Chromium with env configured")
    args = parser.parse_args()
    commands = [[sys.executable, "-m", "unittest", "discover", "-s", "research/simulator", "-p", "test_*.py"]]
    commands += [["node", str(p.relative_to(ROOT))] for p in sorted(SIMULATOR.glob("test-*.js"))]
    if args.browser:
        commands.append(["node", "research/simulator/browser-replay-check.js"])
    for command in commands:
        print("RUN " + " ".join(command), flush=True)
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode:
            sys.exit(result.returncode)
    print(f"PASS {len(commands)} check commands; actual ARM execution not tested")
