"""Read-only reference-binary planning; no patch artifact is produced."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/jmcs_integration"))
from callsite_plan import build_plan, PlanError  # noqa: E402


def test_reference_plan_verifies_exact_callsite_and_stock_target():
    data = (ROOT / "extracted/system/system/bin/jmcs").read_bytes()
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
    assert "patched_binary" not in plan


def test_mismatched_binary_is_rejected_before_target_analysis():
    data = bytearray((ROOT / "extracted/system/system/bin/jmcs").read_bytes())
    data[-1] ^= 0x01
    try:
        build_plan(bytes(data))
    except PlanError as exc:
        assert "SHA-256" in str(exc)
    else:
        raise AssertionError("modified reference must fail closed")


def test_unreachable_shim_requires_veneer_and_unknown_without_address():
    data = (ROOT / "extracted/system/system/bin/jmcs").read_bytes()
    far = build_plan(data, shim_address=0x50000000)
    assert far["branch_reach"] == "VENEER_REQUIRED"
    unknown = build_plan(data)
    assert unknown["branch_reach"] == "NOT_EVALUATED"


def test_no_runtime_patch_or_hook_activation_output():
    data = (ROOT / "extracted/system/system/bin/jmcs").read_bytes()
    plan = build_plan(data)
    assert plan["runtime_mechanism"] == "UNKNOWN"
    assert plan["patch_bytes"] == "NOT_EMITTED"
    assert plan["runtime_attachment"] == "NOT_IMPLEMENTED"


def test_instruction_window_mismatch_fails_closed():
    data = bytearray((ROOT / "extracted/system/system/bin/jmcs").read_bytes())
    # Any mutation must be rejected by the complete-file hash gate before planning.
    data[0x28AFBA] ^= 0x01
    try:
        build_plan(bytes(data))
    except PlanError as exc:
        assert "SHA-256 mismatch" in str(exc)
    else:
        raise AssertionError("modified target instruction must be rejected")


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
