"""Read-only compatibility plan for the 43M Thumb callsite.

This module verifies a reference ELF and emits a synthetic JSON plan only.
It never writes to the ELF, emits patch bytes, reads process memory, or loads
the target binary.
"""
from __future__ import annotations

import json
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


class PlanError(ValueError):
    """Reference artifact or target does not satisfy the static contract."""


def build_plan(data: bytes, *, shim_address: int | None = None) -> dict[str, Any]:
    try:
        inspection = inspect_elf32(data)
    except ELFError as exc:
        raise PlanError(str(exc)) from exc
    ident = inspection.identity
    if ident.elf_sha256 != REFERENCE_SHA256:
        raise PlanError(f"reference SHA-256 mismatch: {ident.elf_sha256}")
    if ident.elf_class != 32 or ident.endian != "little" or ident.machine != 40 or ident.elf_type != 3:
        raise PlanError("reference ELF class, byte order, machine, or type mismatch")
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
    branch = "NOT_EVALUATED" if shim_address is None else (
        "DIRECT_THUMB_BL" if can_direct_call(TARGET_VA, shim_address) else "VENEER_REQUIRED"
    )
    return {
        "compatibility": "MATCH",
        "binary_sha256": ident.elf_sha256,
        "target": f"0x{TARGET_VA:08x}",
        "mode": "Thumb",
        "expected_bytes": actual.hex(),
        "displaced_instruction": f"BL 0x{STOCK_TARGET:08x} (_requestSendPlistResponse)",
        "overwrite_bytes": 4,
        "relocation_requirements": [
            "preserve and invoke original _requestSendPlistResponse exactly once",
            "re-encode or veneer the stock BL from shim if needed",
            "no other instruction is displaced; continuation is the next Thumb instruction",
        ],
        "continuation": f"0x{CONTINUATION:08x}",
        "branch_reach": branch,
        "abi": "AAPCS32 Thumb call-site; preserve r4-r11 and SP; original args r0-r3; caller locals remain live",
        "risk": "call-site replacement changes one Honda instruction; runtime mapping, W^X, concurrency, and installation are unproven",
        "runtime_mechanism": "UNKNOWN",
        "patch_bytes": "NOT_EMITTED",
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
