"""Build and run the native SETUP dispatcher on host and API17 ARMv7."""
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
SOURCE = ROOT / "src/claritylink-jmcs/native/setup_dispatch.c"
HARNESS = ROOT / "tests/jmcs/native/setup_dispatch_harness.c"
REQUIRED = os.environ.get("CL_NATIVE_REQUIRE_TARGET") == "1"

try:
    from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_THUMB
    from unicorn.arm_const import (
        UC_ARM_REG_CPSR, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
        UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
        UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11,
        UC_ARM_REG_SP,
    )
except ImportError as exc:
    if REQUIRED:
        raise RuntimeError("CL_NATIVE_REQUIRE_TARGET=1 but Unicorn is unavailable") from exc
    pytest.skip("install requirements-test.txt for ARM execution", allow_module_level=True)

BASE = 0x10000
STACK = 0x80000
SENTINEL = 0x70000


def checked(command: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.CalledProcessError as exc:
        pytest.fail(f"command failed ({exc.returncode}): {command!r}\n"
                    f"stdout:\n{exc.stdout}\nstderr:\n{exc.stderr}")


def skip_or_fail(reason: str) -> None:
    if REQUIRED:
        pytest.fail(f"required native dispatcher check unavailable: {reason}")
    pytest.skip(reason)


def ndk_tools(ndk: str) -> Path | None:
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        tags = (["darwin-arm64", "darwin-x86_64"]
                if machine in ("arm64", "aarch64") else
                ["darwin-x86_64", "darwin-arm64"])
    elif sys.platform.startswith("linux"):
        tags = (["linux-aarch64", "linux-x86_64"]
                if machine in ("arm64", "aarch64") else
                ["linux-x86_64", "linux-aarch64"])
    else:
        tags = ["windows-x86_64"]
    for tag in tags:
        path = Path(ndk) / "toolchains/llvm/prebuilt" / tag / "bin"
        if path.is_dir():
            return path
    return None


def test_host_native_setup_dispatcher(tmp_path):
    clang = shutil.which("clang")
    if not clang:
        skip_or_fail("clang unavailable for host dispatcher harness")
    executable = tmp_path / "native_setup_dispatch"
    checked([clang, "-Wall", "-Wextra", "-Werror", "-UNDEBUG", "-std=c11",
             str(SOURCE), str(HARNESS), "-o", str(executable)])
    output = checked([str(executable)], timeout=10).stdout
    assert "NATIVE_SETUP_DISPATCH_PASS" in output


def test_api17_armv7_thumb_dispatcher_execution(tmp_path):
    ndk = os.environ.get("ANDROID_NDK_HOME")
    if not ndk:
        skip_or_fail("set ANDROID_NDK_HOME to the configured Android NDK r23c")
    tools = ndk_tools(ndk)
    if not tools:
        skip_or_fail("no NDK host prebuilt directory matches this platform")
    suffix = ".exe" if sys.platform == "win32" else ""
    clang = tools / f"clang{suffix}"
    objcopy = tools / f"llvm-objcopy{suffix}"
    readelf = tools / f"llvm-readelf{suffix}"
    objdump = tools / f"llvm-objdump{suffix}"
    if not all(path.is_file() for path in (clang, objcopy, readelf, objdump)):
        skip_or_fail("configured NDK compiler/inspection tools unavailable")

    executable = tmp_path / "native_setup_dispatch_arm.elf"
    flat = tmp_path / "native_setup_dispatch_arm.bin"
    checked([str(clang), "--target=armv7a-linux-androideabi17",
             "-mcpu=cortex-a9", "-mthumb", "-mfloat-abi=soft",
             "-fno-pic", "-fno-pie", "-Wall", "-Wextra", "-Werror",
             "-std=c11", "-ffreestanding", "-fno-builtin",
             "-fno-stack-protector", "-fno-unwind-tables",
             "-fno-asynchronous-unwind-tables", "-fno-jump-tables", "-O1",
             "-nostdlib", "-Wl,--no-undefined", "-Wl,--build-id=none",
             "-Wl,-no-pie", "-Wl,-Ttext=0x10000",
             "-Wl,-e,cl_native_setup_dispatch_test_entry", "-DCL_NATIVE_ARM",
             str(SOURCE), str(HARNESS), "-o", str(executable)])

    symbols = checked([str(readelf), "-s", str(executable)]).stdout
    match = re.search(
        r"^\s*\d+:\s+([0-9a-fA-F]+)\s+\d+\s+FUNC\s+GLOBAL\s+DEFAULT\s+\d+\s+cl_native_setup_dispatch_test_entry$",
        symbols, re.MULTILINE)
    assert match, "ARM test entry symbol is missing"
    entry = int(match.group(1), 16)
    assert entry & 1, "test entry must be Thumb code"
    header = checked([str(readelf), "-h", str(executable)]).stdout
    assert "Class:                             ELF32" in header
    assert "Machine:                           ARM" in header
    assert "Flags:                             0x5000200" in header
    assert "GLOBAL DEFAULT UND" not in symbols
    relocations = checked([str(readelf), "-r", str(executable)]).stdout
    assert "Relocation section" not in relocations
    disassembly = checked([str(objdump), "-d", str(executable)]).stdout
    assert "<cl_native_setup_dispatch_batch>" in disassembly
    headers = checked([str(readelf), "-l", str(executable), "-W"]).stdout
    load_ranges = []
    for line in headers.splitlines():
        fields = line.split()
        if fields and fields[0] == "LOAD":
            load_ranges.append((int(fields[2], 16),
                                int(fields[2], 16) + int(fields[5], 16)))
    assert load_ranges and min(start for start, _end in load_ranges) == BASE
    end = max(limit for _start, limit in load_ranges)
    assert end < SENTINEL
    mapped_end = (end + 0xFFF) & ~0xFFF
    checked([str(objcopy), "-O", "binary", str(executable), str(flat)])
    code = flat.read_bytes()
    assert code

    machine = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    machine.mem_map(BASE, mapped_end - BASE)
    machine.mem_map(STACK, 0x10000)
    machine.mem_map(SENTINEL, 0x1000)
    machine.mem_write(BASE, code)
    trace = []
    machine.hook_add(UC_HOOK_CODE,
                     lambda _uc, address, _size, _data: trace.append(address))
    machine.reg_write(UC_ARM_REG_CPSR,
                      machine.reg_read(UC_ARM_REG_CPSR) | 0x20)
    initial_sp = STACK + 0xF000
    machine.reg_write(UC_ARM_REG_SP, initial_sp)
    machine.reg_write(UC_ARM_REG_LR, SENTINEL | 1)
    preserved = {
        UC_ARM_REG_R4: 0x44444444, UC_ARM_REG_R5: 0x55555555,
        UC_ARM_REG_R6: 0x66666666, UC_ARM_REG_R7: 0x77777777,
        UC_ARM_REG_R8: 0x88888888, UC_ARM_REG_R9: 0x99999999,
        UC_ARM_REG_R10: 0xAAAAAAAA, UC_ARM_REG_R11: 0xBBBBBBBB,
    }
    for register, value in preserved.items():
        machine.reg_write(register, value)
    machine.reg_write(UC_ARM_REG_PC, entry | 1)
    try:
        machine.emu_start(entry | 1, SENTINEL, timeout=1_000_000,
                          count=100_000)
    except Exception as exc:
        pytest.fail(f"ARM dispatcher failed at PC trace {trace[-8:]!r}: {exc}")
    assert machine.reg_read(UC_ARM_REG_R0) == 0, trace[-12:]
    assert machine.reg_read(UC_ARM_REG_PC) & ~1 == SENTINEL
    assert machine.reg_read(UC_ARM_REG_SP) == initial_sp
    for register, value in preserved.items():
        assert machine.reg_read(register) == value
