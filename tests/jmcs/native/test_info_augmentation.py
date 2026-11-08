"""Build and run the C augmentation against host CF and API17 ARM ABI."""
from __future__ import annotations

import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "src/claritylink-jmcs/native/info_augmentation.c"
HARNESS = ROOT / "tests/jmcs/native/test_info_augmentation.c"
REQUIRED = os.environ.get("CL_NATIVE_REQUIRE_TARGET") == "1"


def checked(command: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.CalledProcessError as exc:
        pytest.fail(
            f"command failed ({exc.returncode}): {command!r}\n"
            f"stdout:\n{exc.stdout}\nstderr:\n{exc.stderr}"
        )


def skip_or_fail(reason: str) -> None:
    if REQUIRED:
        pytest.fail(f"required native check unavailable: {reason}")
    pytest.skip(reason)


def test_native_augmentation_host_corefoundation(tmp_path):
    if sys.platform != "darwin":
        skip_or_fail("host CoreFoundation harness is macOS-only; not Honda CFLite")
    clang = shutil.which("clang")
    if not clang:
        skip_or_fail("clang unavailable for native C harness")
    binary = tmp_path / "test_info_augmentation"
    checked(
        [clang, "-Wall", "-Wextra", "-Werror", "-UNDEBUG", "-std=c11",
         str(HARNESS), str(SOURCE), "-framework", "CoreFoundation", "-o",
         str(binary)]
    )
    result = checked([str(binary)], timeout=10)
    assert "NATIVE_INFO_AUGMENT_HOST_CF_PASS" in result.stdout
    assert "target_runtime=NOT_RUN" in result.stdout


def ndk_host_tools(ndk: str) -> Path | None:
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        tags = ["darwin-arm64", "darwin-x86_64"] if machine in ("arm64", "aarch64") else ["darwin-x86_64", "darwin-arm64"]
    elif sys.platform.startswith("linux"):
        tags = ["linux-aarch64", "linux-x86_64"] if machine in ("arm64", "aarch64") else ["linux-x86_64", "linux-aarch64"]
    else:
        tags = ["windows-x86_64"]
    for tag in tags:
        candidate = Path(ndk) / "toolchains/llvm/prebuilt" / tag / "bin"
        if candidate.is_dir():
            return candidate
    return None


def test_native_augmentation_api17_armv7_thumb_object(tmp_path):
    ndk = os.environ.get("ANDROID_NDK_HOME")
    if not ndk:
        skip_or_fail("set ANDROID_NDK_HOME to compile the API17 target object")
    toolchain = ndk_host_tools(ndk)
    if toolchain is None:
        skip_or_fail("no NDK host prebuilt directory matches this platform")
    exe_suffix = ".exe" if sys.platform == "win32" else ""
    clang = toolchain / f"clang{exe_suffix}"
    readelf = toolchain / f"llvm-readelf{exe_suffix}"
    objdump = toolchain / f"llvm-objdump{exe_suffix}"
    if not all(path.is_file() for path in (clang, readelf, objdump)):
        skip_or_fail("configured NDK tools are unavailable")
    obj = tmp_path / "info_augmentation.armv7.o"
    checked(
        [str(clang), "--target=armv7a-linux-androideabi17", "-mthumb",
         "-mfloat-abi=soft", "-O1", "-fPIC", "-fvisibility=hidden",
         "-Wall", "-Wextra", "-Werror", "-std=c11", "-c", str(SOURCE),
         "-o", str(obj)]
    )
    header = checked([str(readelf), "-h", str(obj)]).stdout
    assert "Class:                             ELF32" in header
    assert "Data:                              2's complement, little endian" in header
    assert "Machine:                           ARM" in header
    assert "Flags:                             0x5000000" in header
    disassembly = checked([str(objdump), "-d", str(obj)]).stdout
    assert "<cl_info_create_type111_candidate>" in disassembly
    assert "push" in disassembly
