"""Compile/run the same native transaction C on the host with stress/sanitizers."""
from pathlib import Path
import os
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/claritylink-negotiation/native_setup_txn.c"
HARNESS = ROOT / "tests/native/native_setup_txn_host.c"
INCLUDE = ROOT / "src/claritylink-negotiation"


def _compile_and_run(tmp_path, sanitizer):
    clang = shutil.which("clang")
    if not clang:
        pytest.skip("clang not available for host-native transaction tests")
    binary = tmp_path / f"native-txn-{sanitizer}"
    command = [clang, "-std=c11", "-Wall", "-Wextra", "-Werror", "-O1", "-g",
               "-pthread", "-I", str(INCLUDE)]
    if sanitizer:
        command += [f"-fsanitize={sanitizer}", "-fno-omit-frame-pointer"]
    command += [str(SOURCE), str(HARNESS), "-o", str(binary)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    env = os.environ.copy()
    if "address" in (sanitizer or ""):
        env["ASAN_OPTIONS"] = "halt_on_error=1"
    completed = subprocess.run([str(binary)], check=True, capture_output=True,
                               text=True, env=env, timeout=30)
    assert "native setup transaction" in completed.stdout


def test_host_native_transaction_core_concurrency_and_malformed_sweep(tmp_path):
    _compile_and_run(tmp_path, None)


def test_host_native_transaction_asan_ubsan(tmp_path):
    _compile_and_run(tmp_path, "address,undefined")


def test_host_native_transaction_tsan(tmp_path):
    _compile_and_run(tmp_path, "thread")
