"""Compile and run the Type111 child-control boundary C (offline, synthetic).

Host runs prove boundary logic only. The ARMv7 test proves the code compiles
for the target ABI; it does not execute on, or demonstrate anything about, Honda.
"""
from pathlib import Path
import os
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
INCLUDE = ROOT / "src/claritylink-negotiation"
SOURCE = INCLUDE / "cl_type111_child.c"
HARNESS = ROOT / "tests/native/cl_type111_child_test.c"
WARNINGS = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-Wconversion", "-Wshadow"]


def _clang():
    clang = shutil.which("clang")
    if not clang:
        pytest.skip("clang not available for host-native Type111 child tests")
    return clang


def _run_host(tmp_path, sanitizer):
    binary = tmp_path / f"t111-child-{sanitizer or 'plain'}"
    command = [_clang(), *WARNINGS, "-O1", "-g", "-pthread",
               "-DCL_T111_TEST_HOOKS", "-I", str(INCLUDE)]
    if sanitizer:
        command += [f"-fsanitize={sanitizer}", "-fno-omit-frame-pointer"]
    command += [str(SOURCE), str(HARNESS), "-o", str(binary)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = "halt_on_error=1"
    done = subprocess.run([str(binary)], check=True, capture_output=True, text=True,
                          env=env, timeout=120)
    assert "type111 child boundary tests passed" in done.stdout


def test_type111_child_host_plain(tmp_path):
    _run_host(tmp_path, None)


def test_type111_child_host_asan_ubsan(tmp_path):
    _run_host(tmp_path, "address,undefined")


def test_type111_child_host_tsan(tmp_path):
    _run_host(tmp_path, "thread")


def _ndk_clang():
    ndk = os.environ.get("ANDROID_NDK_HOME")
    if not ndk:
        return None
    candidate = Path(ndk) / "toolchains/llvm/prebuilt/darwin-x86_64/bin/armv7a-linux-androideabi17-clang"
    return candidate if candidate.exists() else None


def test_type111_child_compiles_for_armv7(tmp_path):
    """Target-ABI compile only. Uses the API17 NDK wrapper when configured,
    otherwise a freestanding armv7a object (still ARM32, no Bionic sysroot)."""
    ndk_clang = _ndk_clang()
    obj = tmp_path / "cl_type111_child.o"
    if ndk_clang:
        command = [str(ndk_clang)]
    else:
        command = [_clang(), "--target=armv7a-none-eabi", "-ffreestanding"]
    command += [*WARNINGS, "-UCL_T111_TEST_HOOKS", "-Os", "-march=armv7-a", "-mfloat-abi=softfp", "-fPIC",
                "-I", str(INCLUDE), "-c", str(SOURCE), "-o", str(obj)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    blob = obj.read_bytes()
    assert b"t111_test" not in blob, "test hooks leaked into the production object"
    header = blob[:20]
    assert header[:4] == b"\x7fELF" and header[4] == 1, "expected ELF32"
    assert int.from_bytes(header[18:20], "little") == 40, "expected EM_ARM"
    # No unresolved reference to Honda/CoreFoundation symbols.
    nm = shutil.which("llvm-nm") or shutil.which("nm")
    if nm:
        symbols = subprocess.run([nm, str(obj)], capture_output=True, text=True).stdout
        assert "CF" not in "".join(
            line.split()[-1] for line in symbols.splitlines() if " U " in line
        )
