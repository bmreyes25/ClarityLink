#!/usr/bin/env python3
"""Run fail-closed mode tests against an already built target diagnostic."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def run(binary: Path, *args: str, expected: int = 0) -> str:
    result = subprocess.run([str(binary), *args], text=True, capture_output=True, check=False)
    if result.returncode != expected:
        raise RuntimeError(f"{args!r}: exit {result.returncode}, expected {expected}; stderr={result.stderr!r}")
    if result.stderr and expected == 0:
        raise RuntimeError(f"{args!r}: unexpected stderr {result.stderr!r}")
    return result.stdout


def check(binary: Path, cycles: int) -> None:
    before = set(binary.parent.iterdir())
    no_args = run(binary)
    assert "CLARITYLINK_DIAG_VERSION=1.0.0" in no_args
    assert "Usage:" in no_args
    assert "SELF_TEST_BEGIN" not in no_args
    assert "--help" in run(binary, "--help")
    version = run(binary, "--version")
    assert "API_TARGET=17" in version and "ABI=armeabi-v7a" in version
    status = run(binary, "--status")
    assert "PERSISTENCE=NONE" in status and "LISTENERS=0" in status
    assert "SELF_TEST_PASS" in run(binary, "--self-test")

    for args in (("--unknown",), ("--carplay",), ("--type110",), ("--type111",),
                 ("--display",), ("--usb",), ("--iap2",), ("--mfi",),
                 ("--listen",), ("--daemon",), ("--self-test", "--display")):
        output = run(binary, *args, expected=2)
        assert "SELF_TEST_BEGIN" not in output
    for cycle in range(cycles):
        output = run(binary, "--self-test")
        assert "RESOURCE_COUNTS final=0" in output, cycle
        assert "SELF_TEST_PASS" in output, cycle
    after = set(binary.parent.iterdir())
    assert before == after, "diagnostic created files beside itself"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("binary", type=Path)
    parser.add_argument("--cycles", type=int, default=100)
    args = parser.parse_args()
    if not args.binary.is_file() or args.cycles < 1 or args.cycles > 10000:
        parser.error("binary must exist and cycles must be in 1..10000")
    check(args.binary.resolve(), args.cycles)
    print(f"R7E1_DIAGNOSTIC_MODES_PASS cycles={args.cycles}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
