"""Execute the compiled Thumb trampoline and native C transaction helpers."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path
import struct
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/jmcs_integration"), str(ROOT / "src/claritylink-honda")]

unicorn = pytest.importorskip("unicorn", reason="install requirements-test.txt for ARM instruction emulation")
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_THUMB
from unicorn.arm_const import (
    UC_ARM_REG_CPSR, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6,
    UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11,
    UC_ARM_REG_R12, UC_ARM_REG_SP,
)

from build_thumb_shim import build_thumb_shim

REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
        UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
        UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11,
        UC_ARM_REG_R12, UC_ARM_REG_SP, UC_ARM_REG_LR)
CALLEE_SAVED = (UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
                UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11)
ARG_REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
BASE = 0x10000
STACK = 0x80000
FRAME = STACK + 0x7000
NESTED_FRAME = STACK + 0x5000
DATA = 0x20000
SERVICE_TABLE = 0x20800
SERVICE_BASE = 0x60000
CONTINUATION = 0x70000
NESTED_CONTINUATION = CONTINUATION + 0x100
REQUEST_MAGIC = 0x43525131
RESPONSE_MAGIC = 0x43525331
CL_BYPASS, CL_PREPARED, CL_REJECTED, CL_BUSY, CL_INTERNAL = range(5)
SERVICE_NAMES = ("claim", "release", "generation_prepare", "listener_prepare",
                 "generation_commit", "generation_rollback", "listener_rollback")


def _u32(uc, address):
    return int.from_bytes(uc.mem_read(address, 4), "little")


def _put32(uc, address, value):
    uc.mem_write(address, int(value & 0xFFFFFFFF).to_bytes(4, "little"))


def _build_case(uc, frame, *, stream_types=(110, 111), ids=((0x11223344, 1), (0x55667788, 1)),
                response_types=(110,), response_ports=(41000,), status_ptr=True,
                request_present=True, response_present=True, session_present=True,
                data_base=DATA):
    request = data_base + 0x100 if request_present else 0
    response = data_base + 0x200 if response_present else 0
    status_address = frame + 0x50 if status_ptr else 0
    if request:
        entries = b"".join(struct.pack("<III", kind, low, high)
                           for kind, (low, high) in zip(stream_types, ids))
        data = struct.pack("<II", REQUEST_MAGIC, len(stream_types)) + entries
        uc.mem_write(request, data)
    if response:
        entries = b"".join(struct.pack("<II", kind, port)
                           for kind, port in zip(response_types, response_ports))
        data = struct.pack("<II", RESPONSE_MAGIC, len(response_types)) + entries
        uc.mem_write(response, data)
    _put32(uc, frame + 0x1C, request)
    _put32(uc, frame + 0x50, 0xA5A5A5A5)
    _put32(uc, frame + 0x54, response)
    session_base = data_base + 0xF00
    _put32(uc, session_base + 0xF4, data_base + 0x700 if session_present else 0)
    args = (0x11111111, 0x22222222, response, status_address)
    return {"frame": frame, "request": request, "response": response,
            "status": status_address, "session_base": session_base,
            "args": args, "session": data_base + 0x700 if session_present else 0}


def _invoke_start(uc, symbols, case, continuation):
    uc.reg_write(UC_ARM_REG_CPSR, uc.reg_read(UC_ARM_REG_CPSR) | 0x20)
    uc.reg_write(UC_ARM_REG_SP, case["frame"])
    uc.reg_write(UC_ARM_REG_LR, continuation | 1)
    for reg, value in zip(ARG_REGS, case["args"]):
        uc.reg_write(reg, value)
    for reg, value in zip(CALLEE_SAVED, (0x44000004, 0x44000005, 0x44000006,
                                        0x44000007, 0x44000008, 0x44000009,
                                        case["session_base"], 0x4400000B)):
        uc.reg_write(reg, value)
    uc.reg_write(UC_ARM_REG_R10, case["session_base"])
    uc.reg_write(UC_ARM_REG_PC, symbols["shim_entry"] | 1)


class EmulatorHarness:
    def __init__(self, *, prepare_mode="type111", serializer_r0=0xC8, serializer_status=0,
                 fail_service=None, nested_service=None, serializer_nested=False,
                 status_pointer_override=None, request_options=None):
        self.code, self.symbols, self.meta = build_thumb_shim(BASE)
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
        self.uc.mem_map(BASE, 0x4000)
        self.uc.mem_map(STACK, 0x10000)
        self.uc.mem_map(DATA, 0x4000)
        self.uc.mem_map(SERVICE_BASE, 0x4000)
        self.uc.mem_map(CONTINUATION, 0x1000)
        self.uc.mem_write(BASE, self.code)
        self.prepare_mode = prepare_mode
        self.serializer_r0 = serializer_r0
        self.serializer_status = serializer_status
        self.fail_service = fail_service
        self.nested_service = nested_service
        self.serializer_nested = serializer_nested
        self.status_pointer_override = status_pointer_override
        self.request_options = request_options or {}
        self.state = {"gate": False, "next_lease": 0, "next_generation": 0,
                      "serializer": 0, "prepare_entry": 0, "activate_entry": 0, "finish_entry": 0,
                      "events": [], "commits": [], "rollbacks": [],
                      "listener_rollbacks": [], "ready": set(), "port": 43000,
                      "serializer_args": [],
                      "serializer_response": [],
                      "nested_saved": None, "nested_active": False,
                      "nested_started": False, "nested_completed": False,
                      "nested_serializer_count": 0, "nested_return_r0": 1}
        self.outer_case = _build_case(self.uc, FRAME, **self.request_options)
        self.nested_case = _build_case(self.uc, NESTED_FRAME, data_base=DATA + 0x1000)
        if status_pointer_override is not None:
            args = self.outer_case["args"]
            self.outer_case["args"] = (*args[:3], status_pointer_override)
        service_ptrs = [SERVICE_BASE + i * 0x100 + 1 for i in range(len(SERVICE_NAMES))]
        self.uc.mem_write(SERVICE_TABLE, struct.pack("<8I", 0, *service_ptrs))
        self.callback_by_pc = {address & ~1: name for address, name in zip(service_ptrs, SERVICE_NAMES)}
        self.trace = []
        self.uc.hook_add(UC_HOOK_CODE, self._on_code)

    def _return_from_service(self, result):
        lr = self.uc.reg_read(UC_ARM_REG_LR)
        self.uc.reg_write(UC_ARM_REG_R0, result)
        self.uc.reg_write(UC_ARM_REG_CPSR, self.uc.reg_read(UC_ARM_REG_CPSR) | 0x20)
        self.uc.reg_write(UC_ARM_REG_PC, lr | 1)

    def _start_nested(self, return_r0=1):
        uc = self.uc
        state = self.state
        state["nested_started"] = True
        state["nested_return_r0"] = return_r0
        state["nested_saved"] = ({reg: uc.reg_read(reg) for reg in REGS},
                                  uc.reg_read(UC_ARM_REG_CPSR))
        state["nested_active"] = True
        _invoke_start(uc, self.symbols, self.nested_case, NESTED_CONTINUATION)

    def _resume_nested_parent(self):
        uc = self.uc
        state = self.state
        saved_regs, saved_cpsr = state["nested_saved"]
        resume_pc = saved_regs[UC_ARM_REG_LR] | 1
        for reg, value in saved_regs.items():
            if reg != UC_ARM_REG_PC:
                uc.reg_write(reg, value)
        uc.reg_write(UC_ARM_REG_CPSR, saved_cpsr)
        uc.reg_write(UC_ARM_REG_R0, state["nested_return_r0"])
        uc.reg_write(UC_ARM_REG_PC, resume_pc)
        state["nested_active"] = False
        state["nested_completed"] = True

    def _service_fails(self, name):
        if isinstance(self.fail_service, (set, tuple, list)):
            return name in self.fail_service
        return self.fail_service == name

    def _service(self, name):
        uc = self.uc
        state = self.state
        regs = [uc.reg_read(reg) for reg in ARG_REGS]
        _userdata, a1, a2, a3 = regs
        state["events"].append(name)
        if name == "claim":
            if state["gate"]:
                self._return_from_service(0)
                return
            if self._service_fails(name):
                self._return_from_service(0)
                return
            state["gate"] = True
            state["next_lease"] += 1
            _put32(uc, a1, state["next_lease"])
            self._return_from_service(1)
        elif name == "release":
            state["gate"] = False
            self._return_from_service(0 if self._service_fails(name) else 1)
        elif name == "generation_prepare":
            if self._service_fails(name):
                self._return_from_service(0)
                return
            state["next_generation"] += 1
            _put32(uc, a3, state["next_generation"])
            self._return_from_service(1)
        elif name == "listener_prepare":
            generation, port_out = a1, a2
            if self.nested_service == "listener_prepare" and not state["nested_started"]:
                state["ready"].add(generation)
                _put32(uc, port_out, 43001)
                self._start_nested()
                return
            state["ready"].add(generation)
            state["port"] = 43000 + generation
            _put32(uc, port_out, state["port"])
            self._return_from_service(0 if self._service_fails(name) else 1)
        elif name == "generation_commit":
            generation = a1
            assert generation in state["ready"]
            state["commits"].append(generation)
            self._return_from_service(0 if self._service_fails(name) else 1)
        elif name == "generation_rollback":
            state["rollbacks"].append(a1)
            state["ready"].discard(a1)
            self._return_from_service(0 if self._service_fails(name) else 1)
        elif name == "listener_rollback":
            state["listener_rollbacks"].append(a1)
            state["ready"].discard(a1)
            self._return_from_service(0 if self._service_fails(name) else 1)

    def _on_code(self, uc, address, _size, _userdata):
        pc = address & ~1
        if pc in self.callback_by_pc:
            self._service(self.callback_by_pc[pc])
            return
        symbols = self.symbols
        if pc == (symbols["project_prepare"] & ~1):
            self.state["prepare_entry"] += 1
        elif pc == (symbols["project_activate"] & ~1):
            self.state["activate_entry"] += 1
        elif pc == (symbols["project_finish"] & ~1):
            self.state["finish_entry"] += 1
        elif pc == (symbols["stock_serializer"] & ~1):
            args = tuple(uc.reg_read(reg) for reg in ARG_REGS)
            self.state["serializer"] += 1
            self.state["serializer_args"].append(args)
            response = args[2]
            if response:
                count = _u32(uc, response + 4)
                self.state["serializer_response"].append(
                    bytes(uc.mem_read(response, 8 + min(count, 8) * 8)))
            if self.state["nested_active"]:
                self.state["nested_serializer_count"] += 1
            status_ptr = args[3]
            if status_ptr:
                _put32(uc, status_ptr, self.serializer_status)
            uc.reg_write(UC_ARM_REG_R0, self.serializer_r0)
            # Serializer is a synchronous external boundary. Optional nested
            # entry uses the same Uc engine and independent synthetic frame.
            if self.serializer_nested and not self.state["nested_started"] and not self.state["nested_active"]:
                self._start_nested(return_r0=self.serializer_r0)
                return
            self._return_from_service(self.serializer_r0)
        elif pc == CONTINUATION:
            if self.state["nested_active"]:
                self._resume_nested_parent()
            else:
                self.state["outer_continuation"] = True
                uc.emu_stop()
        elif pc == NESTED_CONTINUATION:
            self._resume_nested_parent()

    def run(self):
        _invoke_start(self.uc, self.symbols, self.outer_case, CONTINUATION)
        self.uc.emu_start(self.symbols["shim_entry"] | 1, 0x100000, count=30000)
        return self

    def word(self, address):
        return _u32(self.uc, address)

    def outer_local_sp(self):
        return FRAME - 168

    def outer_txn_bytes(self):
        return bytes(self.uc.mem_read(self.outer_local_sp() + 64, 44))

    def outer_prepare_result(self):
        return self.word(self.outer_local_sp() + 36)

    def outer_finish_result(self):
        return self.word(self.outer_local_sp() + 52)


def test_compiled_arm_prepare_finish_execute_without_helper_hooks():
    h = EmulatorHarness().run()
    assert h.meta["machine"] == 40 and h.meta["eabi_flags"] == 0x05000000
    assert h.meta["undefined_imports"] == () and h.meta["writable_text"] is False
    assert h.meta["writable_state_sections"] == ()
    assert h.meta["text_size"] < 4096
    assert {"cl_setup_prepare", "cl_setup_finish"}.issubset(h.meta["relocation_symbols"])
    edges = {(caller, callee) for caller, callee, _ in h.meta["relocation_edges"]}
    assert {("shim_entry", "project_prepare"), ("project_prepare", "cl_setup_prepare"),
            ("shim_entry", "project_activate"),
            ("project_activate", "cl_setup_activate"), ("shim_entry", "stock_serializer"),
            ("shim_entry", "project_finish"), ("project_finish", "cl_setup_finish")} <= edges
    call_order = [callee for caller, callee, _ in sorted(h.meta["relocation_edges"], key=lambda edge: edge[2])
                  if caller == "shim_entry"]
    assert call_order == ["project_prepare", "project_activate", "stock_serializer", "project_finish"]
    assert h.state["prepare_entry"] == h.state["finish_entry"] == 1
    assert h.state["serializer"] == 1 and h.state["outer_continuation"]
    assert h.outer_prepare_result() == CL_PREPARED
    assert h.outer_finish_result() == CL_PREPARED
    assert h.state["events"] == ["claim", "generation_prepare", "listener_prepare",
                                  "generation_commit", "release"]
    assert h.state["serializer_response"][0][4:8] == (2).to_bytes(4, "little")
    assert h.state["commits"] == [1] and not h.state["rollbacks"]
    assert h.uc.reg_read(UC_ARM_REG_SP) == FRAME
    assert tuple(h.uc.reg_read(reg) for reg in CALLEE_SAVED) == (
        0x44000004, 0x44000005, 0x44000006, 0x44000007,
        0x44000008, 0x44000009, h.outer_case["session_base"], 0x4400000B)
    assert h.state["serializer_args"] == [h.outer_case["args"]]
    txn = h.outer_txn_bytes()
    forbidden = [h.outer_case[k].to_bytes(4, "little") for k in
                 ("request", "response", "status", "session")]
    assert not any(value != b"\0\0\0\0" and value in txn for value in forbidden)


@pytest.mark.parametrize(("case", "result"), [
    ({"prepare_mode": "type110"}, CL_BYPASS),
    ({"request_options": {"request_present": False}}, CL_BYPASS),
    ({"request_options": {"stream_types": (110, 111), "ids": ((7, 1), (7, 1))}}, CL_REJECTED),
    ({"request_options": {"stream_types": (111, 111), "ids": ((1, 0), (2, 0))}}, CL_REJECTED),
    ({"request_options": {"stream_types": (111,), "ids": ((0, 0),)}}, CL_REJECTED),
    ({"request_options": {"stream_types": (111,), "ids": ((3, 0),), "response_types": (111,)}}, CL_REJECTED),
    ({"request_options": {"stream_types": (111,), "ids": ((3, 0),), "session_present": False}}, CL_REJECTED),
    ({"request_options": {"stream_types": (111,), "ids": ((3, 0),), "response_present": False}}, CL_REJECTED),
    ({"request_options": {"stream_types": (111,), "ids": ((3, 0),), "status_ptr": False}}, CL_REJECTED),
    ({"fail_service": "claim"}, CL_BUSY),
    ({"fail_service": "generation_prepare"}, CL_INTERNAL),
    ({"fail_service": "listener_prepare"}, CL_INTERNAL),
])
def test_native_prepare_bypass_reject_and_service_failure(case, result):
    opts = dict(case)
    if opts.pop("prepare_mode", None) == "type110":
        opts["request_options"] = {"stream_types": (110,), "ids": ((8, 1),)}
    h = EmulatorHarness(**opts).run()
    assert h.outer_prepare_result() == result
    assert h.state["serializer"] == 1 and h.state["outer_continuation"]
    assert h.state["prepare_entry"] == h.state["finish_entry"] == 1
    assert h.state["activate_entry"] == int(result == CL_PREPARED)
    if result != CL_PREPARED:
        assert h.state["gate"] is False
        assert h.outer_finish_result() in (CL_BYPASS, CL_REJECTED)
        response = h.outer_case["response"]
        if response:
            assert h.word(response + 4) == len(opts.get("request_options", {}).get("response_types", (110,)))


@pytest.mark.parametrize(("serializer_r0", "status", "commit_allowed"), [
    (0x1F4, 0, False), (0xC8, 9, False), (0xC8, 0, True),
])
def test_native_finish_gates_commit_and_preserves_serializer_result(serializer_r0, status, commit_allowed):
    h = EmulatorHarness(serializer_r0=serializer_r0, serializer_status=status).run()
    assert h.state["serializer"] == 1 and h.state["finish_entry"] == 1
    assert h.uc.reg_read(UC_ARM_REG_R0) == serializer_r0
    assert h.state["outer_continuation"] and h.uc.reg_read(UC_ARM_REG_SP) == FRAME
    if commit_allowed:
        assert h.outer_finish_result() == CL_PREPARED
        assert h.state["commits"] == [1] and not h.state["rollbacks"]
        assert h.word(h.outer_case["response"] + 4) == 2
        assert h.word(h.outer_case["response"] + 8 + 8) == 111
    else:
        assert h.outer_finish_result() == CL_REJECTED
        assert h.state["commits"] == [1] and h.state["rollbacks"] == [1]
        assert h.state["listener_rollbacks"] == [1]
        assert h.word(h.outer_case["response"] + 4) == 1


def test_native_commit_service_failure_rolls_back_without_replaying_serializer():
    h = EmulatorHarness(fail_service="generation_commit", serializer_r0=0xC8).run()
    assert h.state["serializer"] == 1 and h.state["finish_entry"] == 1
    assert h.uc.reg_read(UC_ARM_REG_R0) == 0xC8
    assert h.state["commits"] == [1]  # attempted service call failed
    assert h.state["rollbacks"] == [1] and h.state["listener_rollbacks"] == [1]
    assert h.word(h.outer_case["response"] + 4) == 1
    assert h.state["outer_continuation"]
    assert int.from_bytes(h.state["serializer_response"][0][4:8], "little") == 1
    assert h.outer_finish_result() == CL_REJECTED


def test_gate_release_failure_preserves_serialized_listener_and_stock_result():
    h = EmulatorHarness(fail_service="release", serializer_r0=0xC8).run()
    assert h.state["serializer"] == 1 and h.uc.reg_read(UC_ARM_REG_R0) == 0xC8
    assert int.from_bytes(h.state["serializer_response"][0][4:8], "little") == 2
    assert h.word(h.outer_case["response"] + 4) == 2
    assert h.state["ready"] == {1}
    assert not h.state["rollbacks"] and not h.state["listener_rollbacks"]
    assert not h.state["gate"]
    assert h.outer_finish_result() == CL_INTERNAL


def test_native_rollback_service_failure_is_reported_without_changing_stock_r0():
    h = EmulatorHarness(fail_service="listener_rollback", serializer_r0=0x1F4).run()
    assert h.state["serializer"] == 1 and h.state["finish_entry"] == 1
    assert h.uc.reg_read(UC_ARM_REG_R0) == 0x1F4
    assert h.outer_finish_result() == CL_INTERNAL
    assert h.state["rollbacks"] == [1] and h.state["listener_rollbacks"] == [1]


def test_activation_rollback_failure_status_survives_project_finish():
    h = EmulatorHarness(fail_service={"generation_commit", "generation_rollback"}, serializer_r0=0xC8).run()
    assert h.state["serializer"] == 1 and h.uc.reg_read(UC_ARM_REG_R0) == 0xC8
    assert h.outer_finish_result() == CL_INTERNAL
    assert h.state["ready"] == set() and not h.state["gate"]


def test_mismatched_status_pointer_fails_closed_without_dereferencing_it():
    h = EmulatorHarness(status_pointer_override=DATA + 0x3F0).run()
    assert h.state["serializer"] == 1
    assert h.state["commits"] == [] and h.state["rollbacks"] == []
    assert h.state["listener_rollbacks"] == []
    assert h.uc.reg_read(UC_ARM_REG_R0) == 0xC8


def test_service_callback_reenters_same_emulator_and_outer_txn_survives():
    h = EmulatorHarness(nested_service="listener_prepare").run()
    assert h.state["nested_started"] and h.state["nested_completed"]
    assert h.state["nested_serializer_count"] == 1
    assert h.state["serializer"] == 2  # nested BUSY stock call + outer stock call
    assert h.state["commits"] == [1]
    assert h.outer_prepare_result() == CL_PREPARED
    assert h.state["outer_continuation"] and not h.state["gate"]
    assert h.state["prepare_entry"] == h.state["finish_entry"] == 2


def test_serializer_boundary_reenters_same_emulator_without_losing_outer_result():
    h = EmulatorHarness(serializer_nested=True, serializer_r0=0xC8).run()
    assert h.state["nested_started"] and h.state["nested_completed"]
    assert h.state["serializer"] == 2
    assert h.state["commits"] == [1]
    assert h.uc.reg_read(UC_ARM_REG_R0) == 0xC8
    assert h.uc.reg_read(UC_ARM_REG_SP) == FRAME and h.state["outer_continuation"]


def test_independent_emulator_instances_execute_concurrently():
    barrier = Barrier(2)
    def run():
        barrier.wait(timeout=5)
        return EmulatorHarness().run()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(run)
        b = pool.submit(run)
        left, right = a.result(timeout=10), b.result(timeout=10)
    assert left.state["commits"] == right.state["commits"] == [1]


@pytest.mark.parametrize(("case", "committed"), [
    ({}, True),
    ({"fail_service": "listener_prepare"}, False),
    ({"serializer_r0": 0x1F4}, False),
    ({"fail_service": "generation_commit"}, False),
])
def test_synthetic_shim_contract_keeps_stock_type110_byte_identical(case, committed):
    """Run the project shim against synthetic memory without Honda artifacts."""
    h = EmulatorHarness(**case)
    request = h.outer_case["request"]
    response = h.outer_case["response"]
    request_before = bytes(h.uc.mem_read(request, 8 + 12 * 2))
    type110_before = bytes(h.uc.mem_read(response + 8, 8))
    response_before = bytes(h.uc.mem_read(response, 8 + 8 * 8))

    h.run()

    assert bytes(h.uc.mem_read(request, len(request_before))) == request_before
    assert bytes(h.uc.mem_read(response + 8, 8)) == type110_before
    assert h.state["serializer"] == 1
    # The callback snapshot captures the serializer-time response before rollback.
    appended_at_serialize = case.get("fail_service") not in {"listener_prepare", "generation_commit"}
    serialized_response = h.state["serializer_response"][0]
    assert int.from_bytes(serialized_response[4:8], "little") == (
        2 if appended_at_serialize else 1
    )
    assert serialized_response[8:16] == type110_before
    assert h.uc.reg_read(UC_ARM_REG_R0) == case.get("serializer_r0", 0xC8)
    if committed:
        assert h.word(response + 4) == 2
        assert bytes(h.uc.mem_read(response + 16, 8)) == struct.pack("<II", 111, 43001)
        assert h.state["commits"] == [1]
        assert not h.state["rollbacks"] and not h.state["listener_rollbacks"]
    else:
        assert bytes(h.uc.mem_read(response, len(response_before))) == response_before
        assert not h.state["ready"]
        assert not h.state["gate"]
        assert h.state["rollbacks"] == [1]
        expected_listener_rollback = [] if case.get("fail_service") == "listener_prepare" else [1]
        assert h.state["listener_rollbacks"] == expected_listener_rollback
