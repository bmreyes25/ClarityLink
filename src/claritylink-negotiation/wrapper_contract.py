"""Stock-delegating serializer transaction model (offline only).

No Honda objects are dereferenced here. Identity is an opaque project key,
and callback semantics are injected so unknown Honda behavior is not encoded.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, MutableMapping


@dataclass(frozen=True)
class WrapperResult:
    identity: Any
    generation: int
    response: MutableMapping[str, Any]
    serializer_result: Any
    project_extended: bool
    project_committed: bool


def serialize_stock_response(
    *,
    request: Mapping[str, Any],
    response: MutableMapping[str, Any],
    is_setup: bool,
    setup_status: Any,
    identity: Any,
    generation: int,
    serializer: Callable[[MutableMapping[str, Any]], Any],
    project_enabled: bool,
    prepare: Callable[[Any, int], Any],
    build_entry: Callable[[Mapping[str, Any], Mapping[str, Any], Any], Any],
    append_entry: Callable[[MutableMapping[str, Any], Any], None],
    commit: Callable[[Any], None],
    rollback: Callable[[Any], None],
    is_current_generation: Callable[[Any, int], bool] = lambda _identity, _generation: True,
    is_serializer_success: Callable[[Any], bool] = lambda value: value == (0xC8, 0),
) -> WrapperResult:
    """Run optional project preparation, then call the stock serializer once.

    `build_entry` must be read-only and complete all fallible construction
    before `append_entry`. `append_entry` models one final project mutation.
    `prepare`/`rollback` own only project resources; rollback identifies partial
    preparation by the supplied opaque identity and generation when state is
    not returned. The default success tuple is SYNTHETIC_TEST_VALUE reflecting
    the recovered Honda serializer predicate; callers may inject another.
    """
    state = None
    extended = False
    eligible = is_setup and setup_status == 0 and project_enabled
    if eligible:
        try:
            eligible = is_current_generation(identity, generation)
        except Exception:
            eligible = False
    if eligible:
        try:
            state = prepare(identity, generation)
            if state is None:
                raise RuntimeError("project prepare must return an owned transaction token")
            entry = build_entry(request, response, state)
            if entry is not None:
                if is_current_generation(identity, generation):
                    append_entry(response, entry)
                    extended = True
                else:
                    _rollback_safely(rollback, state)
                    state = None
            else:
                _rollback_safely(rollback, state)
                state = None
        except Exception:
            _rollback_safely(rollback, state)
            state = None

    try:
        serializer_result = serializer(response)
    except Exception:
        if state is not None:
            _rollback_safely(rollback, state)
        raise

    committed = False
    if state is not None:
        try:
            if (extended and is_current_generation(identity, generation)
                    and is_serializer_success(serializer_result)):
                commit(state)
                committed = True
            else:
                _rollback_safely(rollback, state)
        except Exception:
            # Project bookkeeping cannot replace Honda's exact serializer result.
            _rollback_safely(rollback, state)
    return WrapperResult(identity, generation, response, serializer_result, extended, committed)


def _rollback_safely(rollback: Callable[[Any], None], state: Any) -> None:
    try:
        rollback(state)
    except Exception:
        # Cleanup diagnostics belong to the project registry; never mask stock.
        pass
