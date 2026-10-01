"""Synthetic stock-delegating callsite trampoline contract (offline only).

This models register and control-flow obligations. It does not emit code,
patch an ELF, or claim that a runtime attachment is available.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class RegisterState:
    """Synthetic ARM32 state at trampoline entry; r is the tuple r0..r12."""

    r: tuple[int, ...]
    sp: int
    lr: int
    flags: int = 0

    def __post_init__(self) -> None:
        if len(self.r) != 13:
            raise ValueError("r must contain r0 through r12")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in self.r):
            raise ValueError("register values must be integers")
        if isinstance(self.sp, bool) or not isinstance(self.sp, int):
            raise ValueError("sp must be an integer")
        if isinstance(self.lr, bool) or not isinstance(self.lr, int) or not self.lr & 1:
            raise ValueError("lr must be a Thumb-tagged return address")

    @property
    def serializer_args(self) -> tuple[int, int, int, int]:
        return self.r[0], self.r[1], self.r[2], self.r[3]


@dataclass(frozen=True)
class SerializerInvocation:
    args: tuple[int, int, int, int]
    lr: int
    sp: int


@dataclass(frozen=True)
class TrampolineResult:
    serializer_result: int
    status_out: int
    serializer_calls: int
    serializer_invocation: SerializerInvocation
    returned_lr: int
    returned_sp: int
    returned_r4_r11: tuple[int, ...]
    entry_r4_r11: tuple[int, ...]
    prepare_succeeded: bool
    post_hook_succeeded: Optional[bool]
    flags_preserved: bool
    entry_flags: int
    continuation_flags_unspecified: bool
    r12_entry: int
    call_boundary_sps: tuple[tuple[str, int], ...]
    control_flow: tuple[str, ...]


def execute_synthetic_trampoline(
    entry: RegisterState,
    *,
    serializer: Callable[[SerializerInvocation], tuple[int, int]],
    prepare: Callable[[], object] = lambda: object(),
    post: Callable[[object, int, int], None] = lambda _token, _result, _status: None,
    expected_continuation: int = 0x28AFBF,
    serializer_return_site: int = 0x70000021,
) -> TrampolineResult:
    """Model one BL-to-shim / stock-BL / post-hook / BX-to-caller transaction.

    The original direct BL would enter the serializer with LR equal to the
    caller continuation. A post-serializer hook requires a different LR so
    the serializer can return to the trampoline. The trampoline saves the
    caller continuation on entry and restores it only when returning to the
    original caller. This is a synthetic control-flow contract, not machine
    code generation or proof that the serializer is LR-insensitive at runtime.

    Preparation errors fail open and still call stock once. Post-hook errors
    cannot change Honda's serializer result or statusOut. The post callback
    receives statusOut by value, so it cannot rewrite the modeled output slot.
    """
    if entry.sp & 7:
        raise ValueError("AAPCS callsite SP must be 8-byte aligned")
    if entry.lr != expected_continuation:
        raise ValueError("entry LR does not match the saved Honda continuation")
    if serializer_return_site & 1 == 0:
        raise ValueError("synthetic serializer return site must be Thumb tagged")

    trace = ["entry: saved caller LR, SP, r0-r3, r4-r11"]
    boundary_sps = [("prepare", entry.sp)]
    try:
        token = prepare()
        prepared = True
        trace.append("bounded project prepare")
    except Exception:
        token = None
        prepared = False
        trace.append("prepare failure: fail open")

    # Restore the original serializer arguments and call with aligned caller SP.
    invocation = SerializerInvocation(entry.serializer_args, serializer_return_site, entry.sp)
    boundary_sps.append(("serializer", entry.sp))
    stock_result, status_out = serializer(invocation)
    trace.extend(("Honda serializer exactly once", "capture r0 and statusOut"))

    post_ok: Optional[bool] = None
    if prepared:
        boundary_sps.append(("post", entry.sp))
        try:
            post(token, stock_result, status_out)
            post_ok = True
            trace.append("post hook completed")
        except Exception:
            post_ok = False
            trace.append("post hook failure: preserve stock result")

    trace.append("restore saved caller LR and branch to original continuation")
    return TrampolineResult(
        serializer_result=stock_result,
        status_out=status_out,
        serializer_calls=1,
        serializer_invocation=invocation,
        returned_lr=entry.lr,
        returned_sp=entry.sp,
        returned_r4_r11=entry.r[4:12],
        entry_r4_r11=entry.r[4:12],
        prepare_succeeded=prepared,
        post_hook_succeeded=post_ok,
        flags_preserved=False,
        entry_flags=entry.flags,
        continuation_flags_unspecified=True,
        r12_entry=entry.r[12],
        call_boundary_sps=tuple(boundary_sps),
        control_flow=tuple(trace),
    )
