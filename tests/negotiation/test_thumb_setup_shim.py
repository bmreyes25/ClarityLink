"""Execute the compiled Thumb shim with Unicorn; all callbacks are synthetic."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/jmcs_integration"), str(ROOT / "src/claritylink-honda")]

unicorn = pytest.importorskip("unicorn", reason="install requirements-test.txt for ARM instruction emulation")
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_INSN_INVALID, UC_MODE_THUMB
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
    UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
    UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11, UC_ARM_REG_R12,
    UC_ARM_REG_SP,
)

from build_thumb_shim import build_thumb_shim

CALLEE_SAVED = (UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
                UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11)
ARG_REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
BASE = 0x10000
STACK = 0x80000
FRAME = STACK + 0x7000
DATA = 0x20000
CONTINUATION = 0x70000


def execute(*, prepare=1, serializer_r0=0xC8, status=0, status_ptr=True,
            r10_valid=True, finish_ok=True, serializer_clobber=True,
            request_present=True, response_present=True, nested=False):
    code, symbols, meta = build_thumb_shim(BASE)
    mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    mu.mem_map(BASE, 0x1000)
    mu.mem_map(STACK, 0x10000)
    mu.mem_map(DATA, 0x1000)
    mu.mem_map(CONTINUATION, 0x1000)
    mu.mem_write(BASE, code)
    initial_sp = FRAME
    request = DATA + 0x100 if request_present else 0
    response = DATA + 0x200 if response_present else 0
    status_address = initial_sp + 0x50 if status_ptr else 0
    mu.mem_write(initial_sp + 0x1C, request.to_bytes(4, "little"))
    mu.mem_write(initial_sp + 0x50, (0xA5A5A5A5).to_bytes(4, "little"))
    mu.mem_write(initial_sp + 0x54, response.to_bytes(4, "little"))
    mu.mem_write(DATA + 0xF4, (DATA + 0x400).to_bytes(4, "little"))
    if status_ptr:
        mu.reg_write(UC_ARM_REG_R3, status_address)
    original_args = (0x11111111, 0x22222222, response, status_address)
    for reg, value in zip(ARG_REGS, original_args):
        mu.reg_write(reg, value)
    mu.reg_write(UC_ARM_REG_SP, initial_sp)
    mu.reg_write(UC_ARM_REG_LR, CONTINUATION | 1)
    caller_saved = {reg: 0x44000000 + idx for idx, reg in enumerate(CALLEE_SAVED)}
    caller_saved[UC_ARM_REG_R10] = DATA if r10_valid else 0
    for reg, value in caller_saved.items():
        mu.reg_write(reg, value)
    mu.reg_write(UC_ARM_REG_R10, DATA if r10_valid else 0)

    calls = {"prepare": 0, "serializer": 0, "finish": 0, "context": None,
             "finish_commit": None, "continuation": 0, "call_boundary_sps": [],
             "status_after_serializer": None}

    def helper(uc, address, _size, _user):
        pc = address & ~1
        if pc == (symbols["project_prepare"] & ~1):
            calls["call_boundary_sps"].append(uc.reg_read(UC_ARM_REG_SP))
            calls["prepare"] += 1
            ctx = uc.reg_read(UC_ARM_REG_R0)
            calls["context"] = [int.from_bytes(uc.mem_read(ctx + o, 4), "little")
                                 for o in (0, 4, 8, 12, 16, 20, 24, 28, 32)]
            if nested:
                # Re-enter the compiled shim synchronously from the helper
                # boundary with an independent synthetic caller stack/session.
                calls["nested_result"] = execute(prepare=0, serializer_r0=0x1F4)
            uc.reg_write(UC_ARM_REG_R0, prepare)
        elif pc == (symbols["stock_serializer"] & ~1):
            calls["call_boundary_sps"].append(uc.reg_read(UC_ARM_REG_SP))
            calls["serializer"] += 1
            got = tuple(uc.reg_read(reg) for reg in ARG_REGS)
            assert got == original_args
            if status_ptr:
                uc.mem_write(status_address, int(status).to_bytes(4, "little", signed=False))
                calls["status_after_serializer"] = int.from_bytes(
                    uc.mem_read(status_address, 4), "little")
            uc.reg_write(UC_ARM_REG_R0, serializer_r0)
            if serializer_clobber:
                for reg, value in zip(ARG_REGS[1:], (0xBAD1, 0xBAD2, 0xBAD3)):
                    uc.reg_write(reg, value)
                uc.reg_write(UC_ARM_REG_R12, 0xBAD12)
        elif pc == (symbols["project_finish"] & ~1):
            calls["call_boundary_sps"].append(uc.reg_read(UC_ARM_REG_SP))
            calls["finish"] += 1
            calls["finish_commit"] = uc.reg_read(UC_ARM_REG_R0)
            if not finish_ok:
                uc.reg_write(UC_ARM_REG_R0, 0xDEAD)
            uc.reg_write(UC_ARM_REG_R1, 0xBAD1)
            uc.reg_write(UC_ARM_REG_R12, 0xBAD12)
        elif pc == CONTINUATION:
            calls["continuation"] += 1
            uc.emu_stop()

    trace = []
    def record(uc, address, _size, _user):
        trace.append((address, bytes(uc.mem_read(address, 4)).hex()))
    mu.hook_add(UC_HOOK_CODE, helper)
    mu.hook_add(UC_HOOK_CODE, record)
    def invalid(uc, _user):
        address = uc.reg_read(UC_ARM_REG_PC)
        trace.append((address, "INVALID:" + bytes(uc.mem_read(address & ~1, 4)).hex()))
        return False
    mu.hook_add(UC_HOOK_INSN_INVALID, invalid)
    try:
        mu.emu_start(symbols["shim_entry"] | 1, 0x100000, count=1000)
    except unicorn.UcError as exc:
        raise AssertionError(f"emulator error {exc}; last instructions: {trace[-24:]}") from exc
    return {
        "calls": calls,
        "r0": mu.reg_read(UC_ARM_REG_R0),
        "sp": mu.reg_read(UC_ARM_REG_SP),
        "lr": mu.reg_read(UC_ARM_REG_LR),
        "saved": tuple(mu.reg_read(reg) for reg in CALLEE_SAVED),
        "expected_saved": tuple(caller_saved[reg] for reg in CALLEE_SAVED),
        "initial_sp": initial_sp,
        "meta": meta,
        "symbols": symbols,
    }


def test_compiled_thumb_shim_delegates_once_and_restores_abi_state():
    result = execute()
    assert result["meta"]["machine"] == 40
    assert result["meta"]["eabi_flags"] == 0x05000000
    assert result["meta"]["relocations"] == 3
    assert result["meta"]["text_size"] < 512
    assert result["meta"]["undefined_imports"] == ()
    assert result["meta"]["writable_text"] is False
    assert result["symbols"]["shim_entry"] & 1
    assert result["calls"]["serializer"] == 1
    assert result["calls"]["finish_commit"] == 1
    assert result["calls"]["continuation"] == 1
    assert result["r0"] == 0xC8
    assert result["sp"] == result["initial_sp"]
    assert result["saved"] == result["expected_saved"]
    assert all(sp % 8 == 0 for sp in result["calls"]["call_boundary_sps"])
    assert result["calls"]["status_after_serializer"] == 0
    ctx = result["calls"]["context"]
    assert ctx[:5] == [result["initial_sp"], DATA + 0x100, DATA + 0x200,
                       result["initial_sp"] + 0x50, DATA + 0x400]


@pytest.mark.parametrize("prepare,r0,status,commit", [
    (0, 0xC8, 0, 0),       # no Type111 / prepare failure / malformed input
    (1, 0x1F4, 0, 0),      # serializer status failure
    (1, 0xC8, 5, 0),        # statusOut failure
    (1, 0xC8, 0, 1),        # eligible commit; helper failure cannot change stock r0
])
def test_shim_calls_serializer_once_and_commit_requires_both_stock_success_values(
        prepare, r0, status, commit):
    result = execute(prepare=prepare, serializer_r0=r0, status=status, finish_ok=False)
    assert result["calls"]["serializer"] == 1
    assert result["calls"]["finish_commit"] == commit
    assert result["calls"]["continuation"] == 1
    assert result["r0"] == r0
    assert result["sp"] == result["initial_sp"]
    assert result["saved"] == result["expected_saved"]


def test_null_status_out_and_null_r10_are_bounded():
    result = execute(status_ptr=False, r10_valid=False)
    assert result["calls"]["serializer"] == 1
    assert result["calls"]["finish_commit"] == 0
    assert result["calls"]["context"][3:5] == [0, 0]


@pytest.mark.parametrize("request_present,response_present", [(False, True), (True, False)])
def test_null_request_or_response_is_only_forwarded_and_never_committed(
        request_present, response_present):
    result = execute(prepare=0, request_present=request_present,
                     response_present=response_present)
    assert result["calls"]["serializer"] == 1
    assert result["calls"]["finish_commit"] == 0
    assert result["calls"]["continuation"] == 1
    assert result["calls"]["context"][1 if not request_present else 2] == 0
    assert result["r0"] == 0xC8 and result["sp"] == result["initial_sp"]


def test_two_concurrent_emulator_sessions_have_isolated_shim_state():
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(execute, prepare=1)
        second = pool.submit(execute, prepare=0, serializer_r0=0x1F4)
        a, b = first.result(timeout=5), second.result(timeout=5)
    assert a["calls"]["serializer"] == b["calls"]["serializer"] == 1
    assert a["r0"] == 0xC8 and b["r0"] == 0x1F4
    assert a["calls"]["finish_commit"] == 1
    assert b["calls"]["finish_commit"] == 0


def test_nested_synthetic_shim_invocation_has_independent_context_and_returns():
    outer = execute(prepare=1, nested=True)
    inner = outer["calls"]["nested_result"]
    assert outer["calls"]["serializer"] == inner["calls"]["serializer"] == 1
    assert outer["calls"]["finish_commit"] == 1
    assert inner["calls"]["finish_commit"] == 0
    assert outer["r0"] == 0xC8 and inner["r0"] == 0x1F4
    assert outer["sp"] == inner["sp"] == FRAME
