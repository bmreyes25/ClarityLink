#!/usr/bin/env python3
"""Offline-only, two-callsite stock pass-through patcher for preserved jmcs.

It creates a new isolated copy and redirects only the verified Honda /info
call and post-Setup serializer call through AAPCS32 Thumb pass-through stubs.
It does not advertise or negotiate Type111 and does not install or load code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/jmcs_integration"))
sys.path.insert(0, str(ROOT / "src/claritylink-honda"))
import callsite_plan  # noqa: E402
from elf_identity import ELFError, inspect_elf32  # noqa: E402
from thumb_call import ThumbEncodingError, decode_thumb_bl, encode_thumb_bl  # noqa: E402
from callsite import HONDA_CALLSITES  # noqa: E402


class RewriteError(ValueError):
    """The preserved image or requested isolated output failed a safety gate."""


@dataclass(frozen=True)
class Patch:
    name: str
    site_va: int
    site_offset: int
    original: bytes
    replacement: bytes
    stub_va: int
    stub_offset: int
    stub_bytes: bytes
    stock_target: int


@dataclass(frozen=True)
class PatchPlan:
    source_sha256: str
    text_sha256: str
    cave_va: int
    cave_offset: int
    cave_size: int
    patches: tuple[Patch, ...]
    changed_offsets: tuple[int, ...]
    elf_identity: tuple[int, str, int, int, int]


@dataclass(frozen=True)
class RewriteReceipt:
    source_sha256: str
    output_sha256: str
    output_path: str
    changed_byte_count: int
    info_stub_va: int
    setup_stub_va: int
    pass_through_only: bool = True
    type111_supported: bool = False


# A four-byte Thumb B.W tail branch keeps incoming LR, arguments, SP and all
# registers untouched. The stock callee returns directly to the original
# callsite continuation, exactly as it did before redirection.
STUB_SIZE = 4
PF_X = 1
SHT_NOBITS = 8


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _section_file_ranges(data: bytes) -> list[tuple[int, int]]:
    if len(data) < 52:
        raise RewriteError("truncated ELF header")
    if data[4:7] != bytes((1, 1, 1)):
        raise RewriteError("reference must be ELF32 little-endian current-version")
    shoff = struct.unpack_from("<I", data, 32)[0]
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 46)
    ehsize, phentsize, phnum = struct.unpack_from("<HHH", data, 40)
    if shentsize < 40 or shnum < 3 or shstrndx >= shnum:
        raise RewriteError("ELF section table is missing or unsupported")
    if shoff + shentsize * shnum > len(data):
        raise RewriteError("ELF section table lies outside the file")
    phoff = struct.unpack_from("<I", data, 28)[0]
    ranges = [(0, ehsize), (phoff, phoff + phentsize * phnum),
              (shoff, shoff + shentsize * shnum)]
    for index in range(shnum):
        fields = struct.unpack_from("<IIIIIIIIII", data, shoff + index * shentsize)
        section_type, section_offset, section_size = fields[1], fields[4], fields[5]
        if section_type == SHT_NOBITS or not section_size:
            continue
        end = section_offset + section_size
        if end > len(data):
            raise RewriteError("file-backed ELF section lies outside the file")
        ranges.append((section_offset, end))
    return ranges


def _find_unique_code_cave(data: bytes) -> tuple[int, int, int]:
    """Return file offset, VA and size for the sole zero run outside sections."""
    try:
        elf = inspect_elf32(data)
    except ELFError as exc:
        raise RewriteError(str(exc)) from exc
    sections = _section_file_ranges(data)
    runs: dict[tuple[int, int], tuple[int, int, int]] = {}
    for segment in elf.load_segments:
        if not segment.flags & PF_X or not segment.filesz:
            continue
        start = segment.offset
        end = start + segment.filesz
        cursor = start
        while cursor < end:
            while cursor < end and (data[cursor] != 0 or any(a <= cursor < b for a, b in sections)):
                cursor += 1
            run_start = cursor
            while cursor < end and data[cursor] == 0 and not any(a <= cursor < b for a, b in sections):
                cursor += 1
            if cursor - run_start >= 2 * STUB_SIZE:
                # A run may begin at an odd address. Align the first Thumb
                # instruction and retain only file-backed executable bytes.
                aligned = run_start + ((segment.vaddr + run_start - segment.offset) & 1)
                available = cursor - aligned
                if available >= 2 * STUB_SIZE:
                    va = segment.vaddr + aligned - segment.offset
                    runs[(aligned, va)] = (aligned, va, available)
    if len(runs) != 1:
        raise RewriteError(f"expected one unambiguous executable cave >= {2 * STUB_SIZE} bytes; found {len(runs)}")
    return next(iter(runs.values()))


def _va_to_file(elf, address: int, count: int) -> int:
    candidates = [
        segment.offset + address - segment.vaddr
        for segment in elf.load_segments
        if segment.flags & PF_X
        and segment.vaddr <= address
        and address + count <= segment.vaddr + segment.filesz
    ]
    if len(candidates) != 1:
        raise RewriteError(f"address 0x{address:08x} has {len(candidates)} executable file mappings")
    return candidates[0]


def _make_stub(stub_va: int, stock_target: int) -> bytes:
    try:
        return encode_thumb_b_w(stub_va, stock_target)
    except ThumbEncodingError as exc:
        raise RewriteError(f"stock function is not directly reachable from the pass-through entry: {exc}") from exc


def encode_thumb_b_w(branch_address: int, target: int) -> bytes:
    """Encode a Thumb-2 B.W T4 same-state branch with signed 25-bit offset."""
    try:
        # Reuse BL's validation and displacement range; only the second
        # halfword opcode differs (B.W uses 0b1001, BL uses 0b1101).
        call = encode_thumb_bl(branch_address, target)
    except ThumbEncodingError:
        raise
    second = int.from_bytes(call[2:], "little")
    return call[:2] + (second & 0x2FFF | 0x9000).to_bytes(2, "little")


def decode_thumb_b_w(branch_address: int, raw: bytes) -> int:
    """Decode a Thumb-2 B.W T4 same-state branch target."""
    if len(raw) != 4:
        raise ThumbEncodingError("Thumb B.W must contain exactly four bytes")
    second = int.from_bytes(raw[2:], "little")
    if second & 0xD000 != 0x9000:
        raise ThumbEncodingError("instruction is not Thumb-2 B.W immediate")
    # Normalize B.W's opcode to BL's encoding; immediate bits are identical.
    return decode_thumb_bl(branch_address, raw[:2] + (second | 0x4000).to_bytes(2, "little")).target


def build_patch_plan(data: bytes) -> PatchPlan:
    """Validate the public reference fingerprints and derive exact patch bytes."""
    digest = _sha256(data)
    try:
        summary = callsite_plan.build_plan(data)
        elf = inspect_elf32(data)
    except (callsite_plan.PlanError, ELFError) as exc:
        raise RewriteError(str(exc)) from exc
    if digest != callsite_plan.REFERENCE_SHA256:
        raise RewriteError("reference jmcs SHA-256 does not match the public pinned identity")
    if summary.get("compatibility") != "MATCH":
        raise RewriteError("post-Setup serializer fingerprint did not validate")
    info_site = HONDA_CALLSITES[0]
    try:
        info_call = decode_thumb_bl(info_site.static_address, info_site.expected_bytes)
    except ThumbEncodingError as exc:
        raise RewriteError("/info stock call fingerprint is invalid") from exc
    if info_call.target != info_site.stock_target:
        raise RewriteError("/info stock call target differs from its pinned fingerprint")
    info_offset = _va_to_file(elf, info_site.static_address, 4)
    if data[info_offset:info_offset + 4] != info_site.expected_bytes:
        raise RewriteError("/info stock call bytes differ from the pinned fingerprint")

    setup_site = callsite_plan.TARGET_VA
    setup_original = callsite_plan.EXPECTED_BL
    setup_call = decode_thumb_bl(setup_site, setup_original)
    if setup_call.target != callsite_plan.STOCK_TARGET:
        raise RewriteError("post-Setup serializer target differs from its pinned fingerprint")
    setup_offset = _va_to_file(elf, setup_site, 4)
    if data[setup_offset:setup_offset + 4] != setup_original:
        raise RewriteError("post-Setup serializer call bytes differ from the pinned fingerprint")

    cave_offset, cave_va, cave_size = _find_unique_code_cave(data)
    info_stub_va = cave_va
    setup_stub_va = cave_va + STUB_SIZE
    info_stub = _make_stub(info_stub_va, info_site.stock_target)
    setup_stub = _make_stub(setup_stub_va, callsite_plan.STOCK_TARGET)
    try:
        info_redirect = encode_thumb_bl(info_site.static_address, info_stub_va)
        setup_redirect = encode_thumb_bl(setup_site, setup_stub_va)
    except ThumbEncodingError as exc:
        raise RewriteError(f"callsite cannot reach the unique cave using Thumb BL: {exc}") from exc

    changes = (
        Patch("/info AirPlayCopyServerInfo stock-call passthrough", info_site.static_address,
              info_offset, info_site.expected_bytes, info_redirect, info_stub_va,
              cave_offset, info_stub, info_site.stock_target),
        Patch("post-Setup serializer stock-call passthrough", setup_site,
              setup_offset, setup_original, setup_redirect, setup_stub_va,
              cave_offset + STUB_SIZE, setup_stub, callsite_plan.STOCK_TARGET),
    )
    offsets = []
    for patch in changes:
        offsets.extend(range(patch.site_offset, patch.site_offset + 4))
        offsets.extend(range(patch.stub_offset, patch.stub_offset + STUB_SIZE))
    ident = elf.identity
    return PatchPlan(
        digest, ident.text_sha256, cave_va, cave_offset, cave_size, changes,
        tuple(sorted(offsets)),
        (ident.elf_class, ident.endian, ident.machine, ident.elf_type,
         struct.unpack_from("<I", data, 36)[0]),
    )


def _apply_plan(data: bytes, plan: PatchPlan) -> bytes:
    output = bytearray(data)
    for patch in plan.patches:
        output[patch.site_offset:patch.site_offset + 4] = patch.replacement
        output[patch.stub_offset:patch.stub_offset + STUB_SIZE] = patch.stub_bytes
    return bytes(output)


def _validate_patched_copy(original: bytes, patched: bytes, plan: PatchPlan) -> None:
    allowed = set(plan.changed_offsets)
    changed = {index for index, (left, right) in enumerate(zip(original, patched)) if left != right}
    if len(original) != len(patched) or not changed <= allowed:
        raise RewriteError("written copy changed bytes outside the exact patch allowlist")
    try:
        before = inspect_elf32(original).identity
        after = inspect_elf32(patched).identity
    except ELFError as exc:
        raise RewriteError("written copy failed ELF identity validation") from exc
    before_identity = (before.elf_class, before.endian, before.machine, before.elf_type,
                       struct.unpack_from("<I", original, 36)[0])
    after_identity = (after.elf_class, after.endian, after.machine, after.elf_type,
                      struct.unpack_from("<I", patched, 36)[0])
    if before_identity != plan.elf_identity or after_identity != plan.elf_identity:
        raise RewriteError("written copy changed pinned ELF identity fields")
    for patch in plan.patches:
        raw = patched[patch.site_offset:patch.site_offset + 4]
        try:
            redirect = decode_thumb_bl(patch.site_va, raw)
        except ThumbEncodingError as exc:
            raise RewriteError("written copy contains an invalid Thumb BL") from exc
        if redirect.target != patch.stub_va or decode_thumb_b_w(patch.stub_va, patch.stub_bytes) != patch.stock_target:
            raise RewriteError("written copy branch does not reach its approved stub and stock target")
        if patched[patch.stub_offset:patch.stub_offset + STUB_SIZE] != patch.stub_bytes:
            raise RewriteError("written copy pass-through stub differs from the planned bytes")


def rewrite_isolated_copy(source: Path, output: Path) -> RewriteReceipt:
    """Patch only a new copy outside the public repository worktree."""
    source, output = Path(source), Path(output)
    output_parent = output.parent.resolve(strict=True)
    repo_root = ROOT.resolve(strict=True)
    if output_parent == repo_root or repo_root in output_parent.parents:
        raise RewriteError("isolated output directory must be outside the public Git worktree")
    output_real = output_parent / output.name
    if output_real.exists() or output_real.is_symlink():
        raise RewriteError("output already exists; refusing to overwrite it")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    source_fd = os.open(source, flags)
    try:
        source_stat = os.fstat(source_fd)
        if not stat.S_ISREG(source_stat.st_mode):
            raise RewriteError("source must be a regular file")
        with os.fdopen(source_fd, "rb", closefd=False) as stream:
            original = stream.read()
    finally:
        os.close(source_fd)

    plan = build_patch_plan(original)
    expected = _apply_plan(original, plan)
    _validate_patched_copy(original, expected, plan)
    create_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    output_fd = os.open(output_real, create_flags, 0o600)
    output_stat = os.fstat(output_fd)

    def cleanup_our_file() -> None:
        try:
            current = output_real.lstat()
            if (current.st_dev, current.st_ino) == (output_stat.st_dev, output_stat.st_ino):
                output_real.unlink()
        except OSError:
            pass

    try:
        with os.fdopen(output_fd, "wb") as stream:
            stream.write(expected)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), stat.S_IMODE(source_stat.st_mode) & 0o755)
        output_now = output_real.read_bytes()
        _validate_patched_copy(original, output_now, plan)
        if output_now != expected:
            raise RewriteError("written copy differs from deterministic planned bytes")
    except BaseException:
        cleanup_our_file()
        raise
    return RewriteReceipt(
        plan.source_sha256, _sha256(output_now), str(output_real),
        sum(left != right for left, right in zip(original, output_now)),
        plan.patches[0].stub_va, plan.patches[1].stub_va,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path,
                        help="preserved SHA-verified jmcs ELF (opened read-only)")
    parser.add_argument("--output", required=True, type=Path,
                        help="new output filename in an isolated directory outside this repository")
    args = parser.parse_args(argv)
    try:
        result = rewrite_isolated_copy(args.source, args.output)
    except (OSError, RewriteError) as exc:
        print(json.dumps({"result": "BLOCKED", "reason": str(exc),
                          "source_modified": False, "type111_supported": False}), file=sys.stderr)
        return 2
    print(json.dumps({
        "result": "ISOLATED_PASS_THROUGH_COPY_CREATED",
        "source_sha256": result.source_sha256,
        "output_sha256": result.output_sha256,
        "changed_byte_count": result.changed_byte_count,
        "output_path": result.output_path,
        "info_stub_va": f"0x{result.info_stub_va:08x}",
        "setup_stub_va": f"0x{result.setup_stub_va:08x}",
        "pass_through_only": True,
        "type111_supported": False,
        "source_modified": False,
        "relocation": "same-image Thumb BL redirects and B.W tail branches; no external loader or persistence",
        "vehicle_deployment": "VEHICLE_DEPLOYMENT_NOT_AUTHORIZED",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
