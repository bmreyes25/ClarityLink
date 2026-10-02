"""Independent Step 43S1 fingerprint/BL revalidation for local evidence."""
from pathlib import Path
import hashlib
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
BIN = ROOT / "extracted/system/system/bin/jmcs"
sys.path.insert(0, str(ROOT / "tools/jmcs_integration"))
from callsite_plan import build_plan, PlanError


def _sign_extend(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def _independent_thumb_bl_target(call: int, instruction: bytes) -> int:
    h1 = int.from_bytes(instruction[:2], "little")
    h2 = int.from_bytes(instruction[2:], "little")
    assert h1 & 0xF800 == 0xF000
    assert h2 & 0xD000 == 0xD000
    s = (h1 >> 10) & 1
    j1 = (h2 >> 13) & 1
    j2 = (h2 >> 11) & 1
    i1 = 1 ^ (j1 ^ s)
    i2 = 1 ^ (j2 ^ s)
    immediate = (s << 24) | (i1 << 23) | (i2 << 22) | ((h1 & 0x3FF) << 12) | ((h2 & 0x7FF) << 1)
    return call + 4 + _sign_extend(immediate, 25)


def test_reference_jmcs_and_thumb_bl_decode_independently():
    if not BIN.is_file():
        pytest.skip("local-only preserved Honda binary is absent")
    data = BIN.read_bytes()
    assert hashlib.sha256(data).hexdigest() == (
        "cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232")
    plan = build_plan(data)
    assert plan["architecture"] == "ARM32 EM_ARM, EABI5"
    assert plan["mode"] == "Thumb"
    assert plan["target"] == "0x0028afba"
    assert plan["expected_bytes"] == "fef7d1ff"
    assert _independent_thumb_bl_target(0x28AFBA, bytes.fromhex("fe f7 d1 ff")) == 0x289F60
    assert plan["continuation"] == "0x0028afbe"
    assert plan["original_lr"] == "0x0028afbf"
    assert plan["caller_stack"]["locals"] == {
        "setup_request": "sp+0x1c", "status_out": "sp+0x50",
        "response": "sp+0x54", "session": "[r10+0xf4]"}


@pytest.mark.parametrize("offset", [0x28AFBA, 0x28AFB2, 0x28A30C])
def test_callsite_and_frame_fingerprints_reject_modified_artifact(offset):
    if not BIN.is_file():
        pytest.skip("local-only preserved Honda binary is absent")
    altered = bytearray(BIN.read_bytes())
    altered[offset] ^= 1
    with pytest.raises(PlanError, match="SHA-256 mismatch"):
        build_plan(bytes(altered))
