"""Register/control-flow obligations for a synthetic Thumb adapter."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-negotiation"))
from trampoline_contract import RegisterState, execute_synthetic_trampoline  # noqa: E402


CONTINUATION = 0x28AFBF  # Thumb function pointer for code at 0x28afbe


def entry_state():
    return RegisterState(
        r=(0x100, 0x200, 0x300, 0x5040, 0x400, 0x500, 0x600, 0x700,
           0x800, 0x900, 0xA00, 0xB00, 0xC00),
        sp=0x100000,
        lr=CONTINUATION,
        flags=0x60000010,
    )


def test_serializer_receives_exact_original_arguments_and_aligned_stack_once():
    entry = entry_state()
    invocations = []

    def serializer(call):
        invocations.append(call)
        return 0xC8, 0

    result = execute_synthetic_trampoline(entry, serializer=serializer)
    assert len(invocations) == result.serializer_calls == 1
    call = invocations[0]
    assert call.args == entry.serializer_args
    assert call.sp == entry.sp and call.sp % 8 == 0
    assert all(sp == entry.sp and sp % 8 == 0 for _, sp in result.call_boundary_sps)
    assert call.lr != entry.lr  # stock returns to adapter so post-work can run
    assert result.returned_lr == entry.lr == CONTINUATION
    assert result.returned_sp == entry.sp
    assert result.returned_r4_r11 == entry.r[4:12]
    assert result.serializer_result == 0xC8 and result.status_out == 0
    assert not result.flags_preserved  # flags are not live at the continuation
    assert result.entry_flags == entry.flags and result.continuation_flags_unspecified
    assert result.r12_entry == entry.r[12]


def test_prepare_failure_still_calls_stock_once_and_preserves_result():
    calls = []

    def fail_prepare():
        raise RuntimeError("synthetic project failure")

    result = execute_synthetic_trampoline(
        entry_state(),
        serializer=lambda call: (calls.append(call) or (0x1F4, -7)),
        prepare=fail_prepare,
    )
    assert len(calls) == result.serializer_calls == 1
    assert not result.prepare_succeeded
    assert result.serializer_result == 0x1F4 and result.status_out == -7
    assert result.post_hook_succeeded is None


def test_post_failure_cannot_rewrite_honda_return_or_status():
    def fail_post(_token, _result, _status):
        raise RuntimeError("synthetic bookkeeping failure")

    result = execute_synthetic_trampoline(
        entry_state(), serializer=lambda _call: (0xC8, 0), post=fail_post,
    )
    assert result.serializer_calls == 1
    assert result.post_hook_succeeded is False
    assert result.serializer_result == 0xC8 and result.status_out == 0
    assert result.returned_lr == CONTINUATION


def test_generation_guard_commit_or_rollback_is_post_serializer_only():
    generation = {"current": 4}
    committed, rolled_back, calls = [], [], []
    token = ("opaque-session", 4)

    def post(state, status, status_out):
        if state[1] == generation["current"] and status == 0xC8 and status_out == 0:
            committed.append(state)
        else:
            rolled_back.append(state)

    result = execute_synthetic_trampoline(
        entry_state(),
        serializer=lambda call: (calls.append(call) or (0xC8, 0)),
        prepare=lambda: token,
        post=post,
    )
    assert len(calls) == result.serializer_calls == 1 and committed == [token]

    generation["current"] = 5
    calls.clear()
    stale = execute_synthetic_trampoline(
        entry_state(),
        serializer=lambda call: (calls.append(call) or (0xC8, 0)),
        prepare=lambda: token,
        post=post,
    )
    assert len(calls) == stale.serializer_calls == 1
    assert rolled_back == [token] and stale.serializer_result == 0xC8


def test_rejects_unaligned_stack_and_wrong_continuation():
    good = entry_state()
    for state in (
        RegisterState(good.r, good.sp + 4, good.lr, good.flags),
        RegisterState(good.r, good.sp, 0x1235, good.flags),
    ):
        try:
            execute_synthetic_trampoline(state, serializer=lambda _call: (0xC8, 0))
        except ValueError:
            pass
        else:
            raise AssertionError("invalid trampoline entry state must fail closed")

    try:
        execute_synthetic_trampoline(good, serializer=lambda _call: (0xC8, 0),
                                     expected_continuation=0x28AFBD)
    except ValueError:
        pass
    else:
        raise AssertionError("unexpected caller continuation must be rejected")
