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
    assert plan["expected_bytes"] == "fef7d1ff"
    assert plan["displaced_instruction"] == "BL 0x00289f60 (_requestSendPlistResponse)"
    assert plan["overwrite_bytes"] == 4
    assert plan["continuation"] == "0x0028afbe"
    assert plan["branch_reach"] == "DIRECT_THUMB_BL"
    assert plan["implementation_status"] == "OFFLINE DESIGN ONLY"
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
