#!/usr/bin/env python3
"""Run the frozen Test A collector against an in-memory, command-locked ADB.

This module never starts ADB. Its sole transport is an injected callable that
rejects any command outside the manifest's next expected operation.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import subprocess
import sys

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import r7e6_test_a_collector as collector

SERIAL = "R7E7G_SIMULATED_TARGET"
FAKE_ADB = "R7E7G_IN_MEMORY_ADB_ONLY"


class ContractFailure(AssertionError):
    """The collector issued a command outside the frozen next operation."""


class FakeADB:
    """Stateful remote file/process model; no subprocess and no device access."""

    def __init__(self, failure: str | None = None) -> None:
        self.failure = failure
        self.expected = collector.command_plan()
        self.calls: list[list[str]] = []
        self.file_present = False
        self.running: set[int] = set()
        self.procfs_controls_available = failure != "procfs_unavailable"
        self.transfers = 0
        self.executions = 0
        self.cleanups = 0
        self.unknown_commands = 0

    @staticmethod
    def _normalized(argv: list[str]) -> list[str]:
        result = argv[1:].copy()
        if result[:2] == ["-s", SERIAL]:
            result[1] = "<EXACT_SERIAL>"
        if result and "R7E6_PIDS_ABSENT:" in result[-1]:
            result[-1] = re.sub(r"\b(?:4101|4102|4201|4202)\b",
                                lambda match: ("<CHILD_PID>" if match.group() in {"4102", "4202"}
                                               else "<PARENT_PID>"), result[-1])
        return result

    def __call__(self, argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs.get("capture_output") is True and kwargs.get("text") is True
        assert kwargs.get("check") is False and kwargs.get("cwd") == collector.ROOT
        if not argv or argv[0] != FAKE_ADB:
            raise ContractFailure("collector attempted a non-simulated ADB transport")
        index = len(self.calls)
        if index >= len(self.expected) or self._normalized(argv) != self.expected[index]:
            self.unknown_commands += 1
            raise ContractFailure(f"command {index + 1} differs from frozen manifest")
        self.calls.append(argv.copy())
        out, err, rc = "", "", 0
        if index == 0:
            out = "Android Debug Bridge version 1.0.41\nVersion 37.0.1-15733141\n"
        elif index == 1:
            out = f"List of devices attached\n{SERIAL}\tdevice\n"
        elif index == 2:
            out = "drwxrwx--x shell    shell             2026-10-11 09:20 tmp\r\n"
        elif index in (3, 12):
            if self.file_present:
                out = f"-r-xr-xr-x shell shell {collector.SIZE} 2026-10-11 {Path(collector.REMOTE).name}\r\n"
            else:
                out = f"{collector.REMOTE}: No such file or directory\r\n"
        elif index == 4:
            self.file_present = True
            self.transfers += 1
            source = str(collector.ARTIFACT.relative_to(collector.ROOT))
            err = (f"{source}: 1 file pushed, 0 skipped. "
                   f"1.0 MB/s ({collector.SIZE} bytes in 0.01s)\n")
        elif index == 5:
            out = f"-r-xr-xr-x shell    shell       {collector.SIZE} 2026-10-11 {Path(collector.REMOTE).name}\r\n"
        elif index == 6:
            out = f"{collector.MD5}  {collector.REMOTE}\r\n"
        elif index in (7, 9):
            self.executions += 1
            parent, child = ((4101, 4102) if index == 7 else (4201, 4202))
            self.running.update((parent, child))
            lines = [f"SUPERVISOR_CHILD_STARTED parent_pid={parent} child_pid={child}",
                     "CLARITYLINK_DIAG_VERSION=1.0.0", "API_TARGET=17", "ABI=armeabi-v7a"]
            if index == 9:
                lines.extend(("RESOURCE_COUNTS final=0", "SELF_TEST_PASS"))
            if not (self.failure == "live_process" and index == 7):
                self.running.difference_update((parent, child))
            lines.extend((f"SUPERVISOR_CHILD_REAPED parent_pid={parent} child_pid={child}",
                          "__R7E6_STATUS:0"))
            out = "\r\n".join(lines) + "\r\n"
        elif index in (8, 10):
            parent, child = ((4101, 4102) if index == 8 else (4201, 4202))
            if not self.running and self.procfs_controls_available:
                out = f"R7E6_PIDS_ABSENT:{child}:{parent}\r\n"
        elif index == 11:
            if self.running:
                raise ContractFailure("collector attempted cleanup with a running process")
            self.cleanups += 1
            self.file_present = False
        if self.failure == "empty_process_sentinel" and index == 8:
            out = ""
        return subprocess.CompletedProcess(argv, rc, out, err)


def run_cycle() -> tuple[FakeADB, dict[str, object]]:
    args = collector.parser().parse_args([
        "--execute-authorized-test-a", "--authorized-collector-sha256",
        collector.sha(Path(collector.__file__).resolve()),
        "--authorized-manifest-sha256", collector.sha(collector.MANIFEST),
        "--serial", SERIAL, "--adb", FAKE_ADB, "--stationary", "--parked",
        "--display-booted", "--cluster-normal", "--no-warnings",
        "--exclusive-adb-window", "--power-state", "SIMULATED",
        "--audio-state", "SIMULATED",
    ])
    fake = FakeADB()
    output = io.StringIO()
    with redirect_stdout(output):
        collector.execute(args, runner=fake, confirm_stock_state=lambda: True)
    result = json.loads(output.getvalue())
    if (result["decision"] != "TEST_A_PASS_FOR_REVIEW"
            or len(fake.calls) != len(fake.expected) or fake.transfers != 1
            or fake.executions != 2 or fake.cleanups != 1 or fake.running
            or fake.file_present or fake.unknown_commands):
        raise ContractFailure("collector lifecycle or final modeled state differs from manifest")
    return fake, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=50)
    args = parser.parse_args()
    if args.cycles < 1:
        parser.error("--cycles must be positive")
    cycles = [run_cycle()[0] for _ in range(args.cycles)]
    print(json.dumps({
        "classification": "WET_REHEARSAL_PASS_SIMULATION_ONLY",
        "successful_cycles": len(cycles), "failed_cycles": 0,
        "commands_per_cycle": len(collector.command_plan()),
        "unexpected_commands": sum(c.unknown_commands for c in cycles),
        "simulated_transfers": sum(c.transfers for c in cycles),
        "simulated_executions": sum(c.executions for c in cycles),
        "simulated_cleanups": sum(c.cleanups for c in cycles),
        "file_leaks": sum(c.file_present for c in cycles),
        "process_leaks": sum(bool(c.running) for c in cycles),
        "honda_adb_operations": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
