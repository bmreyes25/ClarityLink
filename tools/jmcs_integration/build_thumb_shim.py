"""Compile and locally relocate the standalone Thumb shim for Unicorn tests.

This emits an in-memory flat test image only. It does not modify or consume
the preserved jmcs ELF, and writes no installation/patch artifact.
"""
from __future__ import annotations

import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/claritylink-negotiation/thumb_setup_shim.S"
HELPER_SOURCE = ROOT / "src/claritylink-negotiation/native_setup_txn.c"
sys_path = ROOT / "src/claritylink-honda"
sys.path.insert(0, str(sys_path))


class ShimBuildError(ValueError):
    pass


def _sections(data: bytes):
    if data[:4] != b"\x7fELF" or data[4:6] != b"\x01\x01":
        raise ShimBuildError("expected ELF32 little-endian object")
    header = struct.unpack_from("<16sHHIIIIIHHHHHH", data)
    shoff, shentsize, shnum = header[6], header[11], header[12]
    return [struct.unpack_from("<IIIIIIIIII", data, shoff + i * shentsize) for i in range(shnum)]


def build_thumb_shim(base_address: int = 0x10000) -> tuple[bytes, dict[str, int], dict[str, object]]:
    clang = shutil.which("clang")
    if not clang:
        raise ShimBuildError("clang is required to build the offline shim")
    with tempfile.TemporaryDirectory(prefix="claritylink-thumb-shim-") as temp:
        helper_asm = Path(temp) / "native_setup_txn.s"
        combined = Path(temp) / "shim_and_helpers.S"
        obj = Path(temp) / "shim.o"
        common = [clang, "--target=armv7-none-eabi", "-mcpu=cortex-a9", "-mthumb",
                  "-ffreestanding", "-fno-builtin", "-fno-stack-protector",
                  "-fno-unwind-tables", "-fno-asynchronous-unwind-tables",
                  "-fno-jump-tables", "-O1", "-DCL_TEST_SERVICE_TABLE_ADDRESS=0x20800"]
        compile_helper = subprocess.run(
            [*common, "-S", str(HELPER_SOURCE), "-o", str(helper_asm)],
            capture_output=True, text=True,
        )
        if compile_helper.returncode:
            raise ShimBuildError(compile_helper.stderr.strip() or "native helper compilation failed")
        combined.write_text(SOURCE.read_text() + "\n" + helper_asm.read_text())
        result = subprocess.run([clang, "--target=armv7-none-eabi", "-mcpu=cortex-a9",
                                 "-mthumb", "-c", str(combined), "-o", str(obj)],
                                capture_output=True, text=True)
        if result.returncode:
            raise ShimBuildError(result.stderr.strip() or "shim assembly failed")
        data = obj.read_bytes()
    if struct.unpack_from("<H", data, 18)[0] != 40:
        raise ShimBuildError("shim object is not EM_ARM")
    flags = struct.unpack_from("<I", data, 36)[0]
    sh = _sections(data)
    writable_state = [
        (sec[0], sec[5]) for sec in sh
        if sec[2] & 0x2 and sec[2] & 0x1 and sec[5] > 0
    ]
    if writable_state:
        raise ShimBuildError(f"unexpected writable allocated state sections: {writable_state!r}")
    text_index = next((i for i, sec in enumerate(sh) if sec[1] == 1 and sec[2] & 0x4), None)
    if text_index is None:
        raise ShimBuildError("executable text section missing")
    text_sec = sh[text_index]
    if text_sec[2] & 0x1:
        raise ShimBuildError("shim text must not be writable/executable")
    if text_sec[5] > 4096:
        raise ShimBuildError("shim/helper text size exceeds 4096-byte review bound")
    image = bytearray(data[text_sec[4]:text_sec[4] + text_sec[5]])
    symbols: dict[str, int] = {}
    undefined_symbols: list[str] = []
    for sec in sh:
        if sec[1] != 2:
            continue
        strings_sec = sh[sec[6]]
        strings = data[strings_sec[4]:strings_sec[4] + strings_sec[5]]
        for pos in range(sec[4], sec[4] + sec[5], sec[9] or 16):
            name_off, value, _size, _info, _other, ndx = struct.unpack_from("<IIIBBH", data, pos)
            if not name_off:
                continue
            end = strings.find(b"\0", name_off)
            name = strings[name_off:end].decode("ascii")
            if ndx == 0:
                undefined_symbols.append(name)
                continue
            if ndx != text_index:
                continue
            symbols[name] = base_address + (value & ~1) | (value & 1)
    relocation_count = 0
    relocation_symbols: list[str] = []
    from thumb_call import encode_thumb_bl

    for sec in sh:
        if sec[1] != 9 or sec[7] != text_index:
            continue
        symtab = sh[sec[6]]
        strsec = sh[symtab[6]]
        strings = data[strsec[4]:strsec[4] + strsec[5]]
        for pos in range(sec[4], sec[4] + sec[5], sec[9] or 8):
            offset, info = struct.unpack_from("<II", data, pos)
            reloc_type, sym_index = info & 0xFF, info >> 8
            if reloc_type != 10:  # R_ARM_THM_CALL
                raise ShimBuildError(f"unsupported ARM relocation {reloc_type}")
            sym_pos = symtab[4] + sym_index * (symtab[9] or 16)
            name_off, value, _size, _syminfo, _other, ndx = struct.unpack_from("<IIIBBH", data, sym_pos)
            if ndx != text_index:
                raise ShimBuildError("shim relocation references a non-text symbol")
            end = strings.find(b"\0", name_off)
            name = strings[name_off:end].decode("ascii")
            relocation_symbols.append(name)
            target = base_address + (value & ~1)
            call_address = base_address + offset
            image[offset:offset + 4] = encode_thumb_bl(call_address, target)
            relocation_count += 1
    required = {"shim_entry", "project_prepare", "stock_serializer", "project_finish",
                "cl_setup_prepare", "cl_setup_finish"}
    if not required.issubset(symbols):
        raise ShimBuildError("expected shim entry/helper symbols missing")
    if symbols["shim_entry"] & 1 == 0:
        raise ShimBuildError("shim_entry is missing Thumb function state")
    if flags != 0x05000000:
        raise ShimBuildError("shim object is not ARM EABI5")
    required_calls = {"project_prepare", "stock_serializer", "project_finish",
                      "cl_setup_prepare", "cl_setup_finish"}
    if not required_calls.issubset(relocation_symbols):
        raise ShimBuildError(f"required compiled call edges missing: {sorted(required_calls - set(relocation_symbols))}")
    if undefined_symbols:
        raise ShimBuildError(f"unexpected undefined imports: {undefined_symbols!r}")
    meta = {"machine": 40, "eabi_flags": flags, "relocations": relocation_count,
            "text_size": len(image), "base_address": base_address,
            "undefined_imports": tuple(undefined_symbols), "writable_text": False,
            "helper_source": str(HELPER_SOURCE),
            "relocation_symbols": tuple(relocation_symbols),
            "writable_state_sections": tuple(writable_state)}
    return bytes(image), symbols, meta
