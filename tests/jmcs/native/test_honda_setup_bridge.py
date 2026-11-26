"""Synthetic whole-request bridge contract and API17 ARMv7 compile checks."""
from __future__ import annotations

import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
BRIDGE = ROOT / "src/claritylink-jmcs/native/honda_setup_bridge.c"
DISPATCH = ROOT / "src/claritylink-jmcs/native/setup_dispatch.c"
HARNESS = ROOT / "tests/jmcs/native/honda_setup_bridge_harness.c"
CFLITE_ADAPTER = ROOT / "src/claritylink-jmcs/native/honda_cflite_adapter.c"
CFLITE_HARNESS = ROOT / "tests/jmcs/native/honda_cflite_adapter_synthetic_harness.c"


def checked(command: list[str], timeout: int = 30) -> str:
    result = subprocess.run(command, check=True, capture_output=True, text=True,
                            timeout=timeout)
    return result.stdout


def test_synthetic_whole_request_bridge_contract(tmp_path: Path) -> None:
    clang = shutil.which("clang")
    if not clang:
        pytest.fail("clang required for native Honda bridge contract")
    exe = tmp_path / "honda_setup_bridge"
    checked([clang, "-Wall", "-Wextra", "-Werror", "-UNDEBUG", "-std=c11",
             str(DISPATCH), str(BRIDGE), str(HARNESS), "-o", str(exe)])
    output = checked([str(exe)], timeout=10)
    assert "HONDA_SETUP_BRIDGE_PASS" in output


def test_synthetic_typed_honda_cflite_adapter(tmp_path: Path) -> None:
    clang = shutil.which("clang")
    if not clang:
        pytest.fail("clang required for synthetic CFLite adapter contract")
    exe = tmp_path / "honda_cflite_adapter_synthetic"
    checked([clang, "-Wall", "-Wextra", "-Werror", "-UNDEBUG", "-std=c11",
             str(CFLITE_ADAPTER), str(CFLITE_HARNESS), "-o", str(exe)])
    output = checked([str(exe)], timeout=10)
    assert "SYNTHETIC_CFLITE_ADAPTER_PASS" in output


def ndk_bin(ndk: Path) -> Path | None:
    machine = platform.machine().lower()
    tags = (["darwin-arm64", "darwin-x86_64"] if machine in ("arm64", "aarch64")
            else ["darwin-x86_64", "darwin-arm64"])
    for tag in tags:
        candidate = ndk / "toolchains/llvm/prebuilt" / tag / "bin"
        if candidate.is_dir():
            return candidate
    return None


def test_api17_armv7_thumb_bridge_object_has_expected_abi(tmp_path: Path) -> None:
    ndk_raw = os.environ.get("ANDROID_NDK_HOME")
    if not ndk_raw:
        pytest.skip("ANDROID_NDK_HOME is not configured")
    tools = ndk_bin(Path(ndk_raw))
    if not tools:
        pytest.skip("NDK prebuilt directory does not match this host")
    clang = tools / "clang"
    readelf = tools / "llvm-readelf"
    objdump = tools / "llvm-objdump"
    if not all(path.is_file() for path in (clang, readelf, objdump)):
        pytest.skip("NDK clang/readelf/objdump unavailable")

    objects = []
    for name, source in (("bridge", BRIDGE), ("dispatch", DISPATCH),
                         ("cflite_adapter", CFLITE_ADAPTER)):
        obj = tmp_path / f"{name}.o"
        checked([str(clang), "--target=armv7a-linux-androideabi17",
                 "-mcpu=cortex-a9", "-mthumb", "-mfloat-abi=soft",
                 "-fno-pic", "-fno-pie", "-ffreestanding", "-fno-builtin",
                 "-fno-stack-protector", "-fno-unwind-tables",
                 "-fno-asynchronous-unwind-tables", "-Wall", "-Wextra",
                 "-Werror", "-std=c11", "-DCL_HONDA_ARM32_ABI", "-c",
                 str(source), "-o", str(obj)])
        header = checked([str(readelf), "-h", str(obj)])
        assert "Class:                             ELF32" in header
        assert "Machine:                           ARM" in header
        symbols = checked([str(readelf), "-s", str(obj)])
        undefined = re.findall(r"\b(?:GLOBAL|WEAK)\s+DEFAULT\s+UND\s+(\S+)", symbols)
        expected = ({"cl_native_setup_finalize_type111",
                     "cl_native_setup_prepare_type111"}
                    if name == "bridge" else set())
        assert set(undefined) == expected, (
            f"unexpected ARM undefined symbols in {name}: {undefined}")
        objects.append(obj)

    disassembly = checked([str(objdump), "-d", str(objects[0])])
    assert "<cl_honda_setup_bridge_call>" in disassembly
    assert "<cl_honda_setup_bridge_complete>" in disassembly
