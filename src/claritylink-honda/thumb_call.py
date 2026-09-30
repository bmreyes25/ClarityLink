"""Pure Thumb-2 BL encoding helpers; no process memory access."""

from __future__ import annotations

from dataclasses import dataclass

U32_MAX = 0xFFFF_FFFF
BL_MIN_DISPLACEMENT = -(1 << 24)
BL_MAX_DISPLACEMENT = (1 << 24) - 2


class ThumbEncodingError(ValueError):
    """The supplied code address or instruction is not a supported Thumb BL."""


def _code_address(value: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= U32_MAX:
        raise ThumbEncodingError(f"{label} must be an unsigned 32-bit code address")
    if value & 1:
        raise ThumbEncodingError(f"{label} must be even; pass function pointers through normalize_thumb_pointer")
    return value


def normalize_thumb_pointer(pointer: int) -> int:
    """Return an even code address from an explicitly Thumb-tagged function pointer."""
    if isinstance(pointer, bool) or not isinstance(pointer, int) or not 0 <= pointer <= U32_MAX:
        raise ThumbEncodingError("function pointer must be unsigned 32-bit")
    if not pointer & 1:
        raise ThumbEncodingError("Thumb function pointer must have bit 0 set")
    return pointer & ~1


def thumb_function_pointer(code_address: int) -> int:
    return _code_address(code_address, "code address") | 1


def _sign_extend(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


@dataclass(frozen=True)
class DecodedThumbCall:
    call_address: int
    target: int
    displacement: int
    return_address: int


def decode_thumb_bl(call_address: int, raw: bytes) -> DecodedThumbCall:
    call_address = _code_address(call_address, "call address")
    if call_address > U32_MAX - 4:
        raise ThumbEncodingError("call PC overflows 32-bit address space")
    if not isinstance(raw, bytes) or len(raw) != 4:
        raise ThumbEncodingError("Thumb BL must contain exactly four bytes")
    first = int.from_bytes(raw[:2], "little")
    second = int.from_bytes(raw[2:], "little")
    if first & 0xF800 != 0xF000 or second & 0xD000 != 0xD000:
        raise ThumbEncodingError("instruction is not Thumb-2 BL immediate")
    s = (first >> 10) & 1
    imm10 = first & 0x3FF
    j1 = (second >> 13) & 1
    j2 = (second >> 11) & 1
    imm11 = second & 0x7FF
    i1 = 1 ^ (j1 ^ s)
    i2 = 1 ^ (j2 ^ s)
    encoded = (s << 24) | (i1 << 23) | (i2 << 22) | (imm10 << 12) | (imm11 << 1)
    displacement = _sign_extend(encoded, 25)
    target = call_address + 4 + displacement
    if not 0 <= target <= U32_MAX or target & 1:
        raise ThumbEncodingError("decoded branch target is outside aligned 32-bit code space")
    return DecodedThumbCall(call_address, target, displacement, call_address + 4)


def encode_thumb_bl(call_address: int, target: int) -> bytes:
    call_address = _code_address(call_address, "call address")
    target = _code_address(target, "branch target")
    if call_address > U32_MAX - 4:
        raise ThumbEncodingError("call PC overflows 32-bit address space")
    displacement = target - (call_address + 4)
    if displacement & 1:
        raise ThumbEncodingError("Thumb BL displacement must be halfword aligned")
    if not BL_MIN_DISPLACEMENT <= displacement <= BL_MAX_DISPLACEMENT:
        raise ThumbEncodingError("Thumb BL target is outside the signed 25-bit displacement range")
    value = displacement & 0x01FF_FFFF
    s = (value >> 24) & 1
    i1 = (value >> 23) & 1
    i2 = (value >> 22) & 1
    imm10 = (value >> 12) & 0x3FF
    imm11 = (value >> 1) & 0x7FF
    j1 = 1 ^ (i1 ^ s)
    j2 = 1 ^ (i2 ^ s)
    first = 0xF000 | (s << 10) | imm10
    second = 0xD000 | (j1 << 13) | (j2 << 11) | imm11
    return first.to_bytes(2, "little") + second.to_bytes(2, "little")


def can_direct_call(call_address: int, target: int) -> bool:
    try:
        encode_thumb_bl(call_address, target)
        return True
    except ThumbEncodingError:
        return False


def encode_thumb_veneer(veneer_address: int, shim_function_pointer: int) -> bytes:
    """Emit `ldr.w r12,[pc,#4]; bx r12; alignment; .word shim|1` (12 bytes)."""
    veneer_address = _code_address(veneer_address, "veneer address")
    if veneer_address & 3:
        raise ThumbEncodingError("veneer must be four-byte aligned for its literal")
    target = normalize_thumb_pointer(shim_function_pointer)
    # clang/LLVM ARMv7 assembler encoding: F8DF C004; 4760; 0000; literal.
    return bytes.fromhex("df f8 04 c0 60 47 00 00") + thumb_function_pointer(target).to_bytes(4, "little")
