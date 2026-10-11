from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

import pytest


@pytest.fixture(scope="module")
def fault_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    compiler = os.environ.get("CC") or shutil.which("clang") or shutil.which("cc")
    assert compiler is not None, "C compiler required for watchdog host tests"
    repo = Path(__file__).resolve().parents[2]
    binary = tmp_path_factory.mktemp("diag-watchdog") / "claritylink-target-diag-test"
    subprocess.run(
        [compiler, "-std=c11", "-O1", "-Wall", "-Wextra", "-Werror",
         "-DCLARITYLINK_TEST_FAULTS", str(repo / "native/diagnostic/claritylink_target_diag.c"),
         "-o", str(binary)],
        check=True,
    )
    return binary


def invoke(binary: Path, mode: str, timeout: float = 5.0) -> tuple[int, str, float]:
    process = subprocess.Popen(
        [str(binary), mode], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True,
    )
    started = time.monotonic()
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        pytest.fail(f"{mode} exceeded the test harness bound; stdout={stdout!r} stderr={stderr!r}")
    return process.returncode, stdout + stderr, time.monotonic() - started


def test_supervised_version_and_self_test_complete(fault_binary: Path) -> None:
    version_code, version_output, version_elapsed = invoke(fault_binary, "--version")
    assert version_code == 0
    assert "CLARITYLINK_DIAG_VERSION=1.0.0" in version_output
    assert version_elapsed < 1.0

    test_code, test_output, test_elapsed = invoke(fault_binary, "--self-test")
    assert test_code == 0
    assert "RESOURCE_COUNTS final=0" in test_output
    assert "SELF_TEST_PASS" in test_output
    assert test_elapsed < 1.0


@pytest.mark.parametrize("mode", ["--test-child-loop", "--test-child-sleep"])
def test_child_watchdog_terminates_and_reaps_exact_child(fault_binary: Path, mode: str) -> None:
    exit_code, output, elapsed = invoke(fault_binary, mode, timeout=4.0)
    assert exit_code == 124
    assert elapsed < 3.0
    assert "SELF_TEST_PASS" not in output
    # communicate() reaches EOF only after the supervised child closes its
    # inherited pipe descriptors; an orphaned child would keep it open.


def test_parent_watchdog_kills_and_reaps_exact_child(fault_binary: Path) -> None:
    exit_code, _output, elapsed = invoke(fault_binary, "--test-parent-timeout", timeout=4.0)
    assert exit_code == 125
    assert elapsed < 3.0


def test_child_crash_is_reaped_and_mapped(fault_binary: Path) -> None:
    exit_code, output, elapsed = invoke(fault_binary, "--test-child-crash")
    assert exit_code == 126
    assert "SELF_TEST_PASS" not in output
    assert elapsed < 1.0


def test_repeated_watchdog_lifecycles_do_not_leave_pipe_holders(fault_binary: Path) -> None:
    for _ in range(5):
        exit_code, _output, elapsed = invoke(fault_binary, "--test-child-loop", timeout=4.0)
        assert exit_code == 124
        assert elapsed < 3.0
    for _ in range(100):
        exit_code, output, _elapsed = invoke(fault_binary, "--version")
        assert exit_code == 0
        assert "CLARITYLINK_DIAG_VERSION=1.0.0" in output
