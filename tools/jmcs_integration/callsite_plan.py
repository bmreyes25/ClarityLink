"""Read-only compatibility plan for the 43M Thumb callsite.

This module verifies a reference ELF and emits a synthetic JSON plan only.
It never writes to the ELF, emits patch bytes, reads process memory, or loads
the target binary.
"""
from __future__ import annotations

import json
import hashlib
import struct
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-honda"))
from elf_identity import ELFError, inspect_elf32  # noqa: E402
from thumb_call import ThumbEncodingError, can_direct_call, decode_thumb_bl  # noqa: E402

REFERENCE_SHA256 = "cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232"
TARGET_VA = 0x28AFBA
EXPECTED_BL = bytes.fromhex("fe f7 d1 ff")
STOCK_TARGET = 0x289F60
CONTINUATION = 0x28AFBE
CONTEXT_VA = 0x28AFB2
CONTEXT_BYTES = bytes.fromhex("31 46 20 46 15 9a 14 ab fe f7 d1 ff 06 46 40 e0")
CONTEXT_SHA256 = "edec335f1cd6f9d0d053a0d2b4a05f515c25e1a1524fccca2c4c0ebd610273df"
PROLOGUE_VA = 0x28A30C
PROLOGUE_BYTES = bytes.fromhex("df f8 8c 24 2d e9 f0 4f 04 46 df f8")
PROLOGUE_SHA256 = "be9f272a09201f326e42c27962609add81149bbe1adb9e843bb8b8ff685d7878"
EXPECTED_E_FLAGS = 0x05000000  # ARM EABI version 5


class PlanError(ValueError):
    """Reference artifact or target does not satisfy the static contract."""


def build_plan(data: bytes, *, shim_address: int | None = None) -> dict[str, Any]:
    digest = hashlib.sha256(data).hexdigest()
    if digest != REFERENCE_SHA256:
        raise PlanError(f"reference SHA-256 mismatch: {digest}")
    try:
        inspection = inspect_elf32(data)
    except ELFError as exc:
        raise PlanError(str(exc)) from exc
    ident = inspection.identity
    if ident.elf_class != 32 or ident.endian != "little" or ident.machine != 40 or ident.elf_type != 3:
        raise PlanError("reference ELF class, byte order, machine, or type mismatch")
    e_flags = struct.unpack_from("<I", data, 36)[0]
    if e_flags != EXPECTED_E_FLAGS:
        raise PlanError(f"reference ARM e_flags mismatch: 0x{e_flags:08x}")
    delta = TARGET_VA - inspection.text_vaddr
    if delta < 0:
        raise PlanError("target precedes .text")
    offset = inspection.text_offset + delta
    actual = data[offset:offset + len(EXPECTED_BL)]
    if actual != EXPECTED_BL:
        raise PlanError(f"target bytes mismatch at 0x{TARGET_VA:08x}: {actual.hex()}")
    try:
        decoded = decode_thumb_bl(TARGET_VA, actual)
    except ThumbEncodingError as exc:
        raise PlanError(f"target is not the expected Thumb BL: {exc}") from exc
    if decoded.target != STOCK_TARGET or decoded.return_address != CONTINUATION:
        raise PlanError("target BL destination or continuation mismatch")
    context_offset = inspection.text_offset + (CONTEXT_VA - inspection.text_vaddr)
    context = data[context_offset:context_offset + len(CONTEXT_BYTES)]
    if context != CONTEXT_BYTES:
        raise PlanError("Setup serializer callsite context fingerprint mismatch")
    if hashlib.sha256(context).hexdigest() != CONTEXT_SHA256:
        raise PlanError("Setup serializer callsite context hash mismatch")
    prologue_offset = inspection.text_offset + (PROLOGUE_VA - inspection.text_vaddr)
    prologue = data[prologue_offset:prologue_offset + len(PROLOGUE_BYTES)]
    if prologue != PROLOGUE_BYTES:
        raise PlanError("_connectionHandleMessage prologue fingerprint mismatch")
    if hashlib.sha256(prologue).hexdigest() != PROLOGUE_SHA256:
        raise PlanError("_connectionHandleMessage prologue hash mismatch")
    branch = "NOT_EVALUATED" if shim_address is None else (
        "DIRECT_THUMB_BL" if can_direct_call(TARGET_VA, shim_address) else "VENEER_REQUIRED"
    )
    branch_examples = {
        "near": {"address": "0x0028b000", "result": "DIRECT_THUMB_BL"},
        "lowest_representable_address": {"address": "0x00000000", "result": "DIRECT_THUMB_BL"},
        "upper_edge": {"address": "0x128afbc", "result": "DIRECT_THUMB_BL"},
        "above_upper_edge": {"address": "0x128afbe", "result": "VENEER_REQUIRED"},
    }
    return {
        "compatibility": "MATCH",
        "binary_sha256": ident.elf_sha256,
        "target": f"0x{TARGET_VA:08x}",
        "mode": "Thumb",
        "architecture": "ARM32 EM_ARM, EABI5",
        "call_pc": f"0x{TARGET_VA + 4:08x}",
        "expected_bytes": actual.hex(),
        "displaced_instruction": f"BL 0x{STOCK_TARGET:08x} (_requestSendPlistResponse)",
        "overwrite_bytes": 4,
        "surrounding_fingerprint": {
            "address": f"0x{CONTEXT_VA:08x}",
            "bytes": context.hex(),
            "sha256": CONTEXT_SHA256,
        },
        "caller_prologue_fingerprint": {
            "address": f"0x{PROLOGUE_VA:08x}",
            "bytes": prologue.hex(),
            "sha256": PROLOGUE_SHA256,
        },
        "original_lr": f"0x{CONTINUATION | 1:08x}",
        "caller_stack": {
            "frame_size": "0x2d8",
            "entry_alignment_assumption": 8,
            "callsite_sp_alignment": 8,
            "locals": {
                "setup_request": "sp+0x1c",
                "status_out": "sp+0x50",
                "response": "sp+0x54",
                "session": "[r10+0xf4]",
            },
            "arguments": {
                "r0": "HTTP connection (r4)",
                "r1": "HTTP request/message (r6)",
                "r2": "Setup response ([sp+0x54])",
                "r3": "&statusOut (sp+0x50)",
            },
        },
        "lr_contract": {
            "trampoline_entry": f"0x{CONTINUATION | 1:08x}",
            "serializer_entry": "adapter-local Thumb return address (differs from direct-call LR)",
            "trampoline_return": f"0x{CONTINUATION | 1:08x}",
            "flags_live_at_continuation": False,
        },
        "register_contract": {
            "serializer_args": "restore r0-r3 exactly before original serializer call",
            "preserve": "r4-r11 and SP across the adapter; return stock r0 unchanged",
            "r12": "caller-saved scratch; not live in the observed continuation sequence",
        },
        "abi_contract": "PASS_SYNTHETIC_MODEL_REQUIRED",
        "relocation_requirements": [
            "preserve and invoke original _requestSendPlistResponse exactly once",
            "re-encode or veneer the stock BL from shim if needed",
            "no other instruction is displaced; continuation is the next Thumb instruction",
        ],
        "continuation": f"0x{CONTINUATION:08x}",
        "branch_reach": branch,
        "thumb_bl_range": {
            "pc": "callsite + 4",
            "displacement_min": "-0x1000000",
            "displacement_max": "+0xfffffe",
            "alignment": "halfword (2 bytes)",
            "target_mode": "Thumb only; ARM state needs a separately validated interworking veneer",
            "synthetic_examples": branch_examples,
        },
        "abi": "AAPCS32 Thumb call-site; preserve r4-r11 and SP; original args r0-r3; caller locals remain live",
        "risk": "call-site replacement changes one Honda instruction; runtime mapping, W^X, concurrency, and installation are unproven",
        "runtime_mechanism": "UNKNOWN",
        "patch_bytes": "NOT_EMITTED",
        "runtime_attachment": "NOT_IMPLEMENTED",
        "implementation_status": "OFFLINE DESIGN ONLY",
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("--shim-address", type=lambda value: int(value, 0))
    args = parser.parse_args()
    try:
        plan = build_plan(args.binary.read_bytes(), shim_address=args.shim_address)
    except (OSError, PlanError) as exc:
        print(json.dumps({"compatibility": "REJECT", "reason": str(exc)}, indent=2))
        return 2
    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
