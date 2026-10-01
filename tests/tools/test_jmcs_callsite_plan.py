"""Read-only reference-binary planning; no patch artifact is produced."""
from pathlib import Path
import sys
import unittest
import pytest

ROOT = Path(__file__).resolve().parents[2]
REFERENCE_ELF = ROOT / "extracted/system/system/bin/jmcs"
sys.path.insert(0, str(ROOT / "tools/jmcs_integration"))
from callsite_plan import build_plan, PlanError  # noqa: E402


class PrivateHondaArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not REFERENCE_ELF.is_file():
            raise unittest.SkipTest("Honda jmcs is a local-only evidence artifact and is not committed to CI")

    def test_reference_plan_verifies_exact_callsite_and_stock_target(self):
        data = REFERENCE_ELF.read_bytes()
        plan = build_plan(data, shim_address=0x28B000)
        assert plan["compatibility"] == "MATCH"
        assert plan["target"] == "0x0028afba"
        assert plan["mode"] == "Thumb"
        assert plan["architecture"] == "ARM32 EM_ARM, EABI5"
        assert plan["expected_bytes"] == "fef7d1ff"
        assert plan["displaced_instruction"] == "BL 0x00289f60 (_requestSendPlistResponse)"
        assert plan["overwrite_bytes"] == 4
        assert plan["continuation"] == "0x0028afbe"
        assert plan["call_pc"] == "0x0028afbe"
        assert plan["original_lr"] == "0x0028afbf"
        assert plan["surrounding_fingerprint"]["sha256"]
        assert plan["caller_prologue_fingerprint"]["sha256"]
        assert plan["caller_stack"]["frame_size"] == "0x2d8"
        assert plan["caller_stack"]["callsite_sp_alignment"] == 8
        assert plan["abi_contract"] == "PASS_SYNTHETIC_MODEL_REQUIRED"
        assert plan["thumb_bl_range"]["displacement_min"] == "-0x1000000"
        assert plan["thumb_bl_range"]["displacement_max"] == "+0xfffffe"
        assert plan["thumb_bl_range"]["synthetic_examples"]["lowest_representable_address"]["result"] == "DIRECT_THUMB_BL"
        assert plan["branch_reach"] == "DIRECT_THUMB_BL"
        assert plan["implementation_status"] == "OFFLINE DESIGN ONLY"
        assert plan["runtime_attachment"] == "NOT_IMPLEMENTED"
        assert plan["runtime_mechanism"] == "UNKNOWN"
        assert plan["patch_bytes"] == "NOT_EMITTED"
        assert "patched_binary" not in plan

    def test_reference_corruption_is_rejected_by_hash_gate(self):
        data = bytearray(REFERENCE_ELF.read_bytes())
        data[0x28AFBA] ^= 0x01
        with self.assertRaisesRegex(PlanError, "SHA-256 mismatch"):
            build_plan(bytes(data))

    def test_unreachable_shim_requires_veneer_and_unknown_without_address(self):
        data = REFERENCE_ELF.read_bytes()
        assert build_plan(data, shim_address=0x50000000)["branch_reach"] == "VENEER_REQUIRED"
        assert build_plan(data)["branch_reach"] == "NOT_EVALUATED"

    def test_instruction_and_caller_fingerprints_remain_hash_gated(self):
        data = bytearray(REFERENCE_ELF.read_bytes())
        data[0x28AFB2] ^= 1
        with self.assertRaisesRegex(PlanError, "SHA-256 mismatch"):
            build_plan(bytes(data))


def test_synthetic_data_is_rejected_before_elf_parsing():
    with pytest.raises(PlanError, match="SHA-256 mismatch"):
        build_plan(b"synthetic test bytes")


def test_synthetic_branch_examples_match_encoder_reach():
    from thumb_call import can_direct_call

    callsite = 0x28AFBA
    for item in (
        (0x28B000, True),
        (0x00000000, True),
        (0x128AFBC, True),
        (0x128AFBE, False),
    ):
        assert can_direct_call(callsite, item[0]) is item[1]
