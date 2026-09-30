"""Offline, bounded models for fail-closed in-process target location.

This module never reads procfs or process memory and never patches code.
"""
from dataclasses import dataclass
from enum import Enum

U32_LIMIT = 1 << 32
MAX_MAP_BYTES = 1 << 20
MAX_MAP_ENTRIES = 4096


class LocationError(ValueError):
    pass


class Verdict(str, Enum):
    VALID_TARGET = "VALID_TARGET"
    WRONG_BINARY = "WRONG_BINARY"
    WRONG_PROLOGUE = "WRONG_PROLOGUE"
    WRONG_MAPPING = "WRONG_MAPPING"
    UNSUPPORTED_MODE = "UNSUPPORTED_MODE"


@dataclass(frozen=True)
class Mapping:
    start: int
    end: int
    permissions: str
    offset: int
    pathname: str


@dataclass(frozen=True)
class TargetDescriptor:
    module_path: str
    module_sha256: str
    target_offset: int
    expected_bytes: bytes
    mode: str  # "arm" or "thumb"
    minimum_patch_bytes: int


@dataclass(frozen=True)
class Validation:
    verdict: Verdict
    runtime_address: int | None = None
    reason: str = ""


def parse_maps_bounded(raw: bytes, *, max_bytes: int = MAX_MAP_BYTES,
                       max_entries: int = MAX_MAP_ENTRIES) -> tuple[Mapping, ...]:
    if len(raw) > max_bytes:
        raise LocationError("maps input exceeds byte limit")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise LocationError("maps input is not ASCII") from exc
    result = []
    for line in text.splitlines():
        fields = line.split(None, 5)
        if len(fields) < 5:
            raise LocationError("malformed maps line")
        try:
            lo_s, hi_s = fields[0].split("-", 1)
            lo, hi, off = int(lo_s, 16), int(hi_s, 16), int(fields[2], 16)
        except (ValueError, IndexError) as exc:
            raise LocationError("malformed maps address") from exc
        perms = fields[1]
        if lo >= hi or hi > U32_LIMIT or len(perms) != 4 or perms[0] not in "r-" or perms[1] not in "w-" or perms[2] not in "x-":
            raise LocationError("invalid mapping range or permissions")
        if off >= U32_LIMIT:
            raise LocationError("mapping offset overflow")
        result.append(Mapping(lo, hi, perms, off, fields[5] if len(fields) == 6 else ""))
        if len(result) > max_entries:
            raise LocationError("maps entry limit exceeded")
    return tuple(result)


def locate_load_bias(maps: tuple[Mapping, ...], *, module_path: str,
                     executable_segment_offset: int, executable_segment_vaddr: int,
                     page_size: int = 4096) -> int:
    if page_size <= 0 or page_size & (page_size - 1):
        raise LocationError("unsupported page size")
    off_page = executable_segment_offset & -page_size
    va_page = executable_segment_vaddr & -page_size
    matches = [m for m in maps if m.pathname == module_path and "x" in m.permissions and m.offset == off_page]
    if not matches:
        raise LocationError("executable module mapping missing")
    biases = {m.start - va_page for m in matches if m.start >= va_page}
    if len(biases) != 1:
        raise LocationError("ambiguous or invalid load bias")
    return next(iter(biases))


def validate_target(*, actual_sha256: str, descriptor: TargetDescriptor,
                    load_bias: int, memory_window: bytes, mapping_permissions: str) -> Validation:
    if actual_sha256.lower() != descriptor.module_sha256.lower():
        return Validation(Verdict.WRONG_BINARY, reason="module hash mismatch")
    if descriptor.mode not in ("arm", "thumb"):
        return Validation(Verdict.UNSUPPORTED_MODE, reason="unknown instruction mode")
    addr = load_bias + descriptor.target_offset
    if addr < 0 or addr >= U32_LIMIT or addr + max(len(descriptor.expected_bytes), descriptor.minimum_patch_bytes) > U32_LIMIT:
        return Validation(Verdict.WRONG_MAPPING, reason="address overflow")
    if "x" not in mapping_permissions or "w" in mapping_permissions:
        return Validation(Verdict.WRONG_MAPPING, reason="target is not executable non-writable memory")
    required = max(len(descriptor.expected_bytes), descriptor.minimum_patch_bytes)
    if len(memory_window) < required:
        return Validation(Verdict.WRONG_MAPPING, reason="target window too short")
    if not descriptor.expected_bytes or memory_window[:len(descriptor.expected_bytes)] != descriptor.expected_bytes:
        return Validation(Verdict.WRONG_PROLOGUE, reason="instruction fingerprint mismatch")
    return Validation(Verdict.VALID_TARGET, addr, "exact offline identity and bytes matched")
