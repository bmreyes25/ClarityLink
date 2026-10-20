"""Mock stock-first Type111 delegation for offline session integration tests.

This adapter has no Honda transport or process access. The primary owner is a
test double, and all Type111 listener/serialization behavior remains in the
existing evidence-bounded setup contract.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable, Mapping

from type111_setup_contract import (SerializerResult, SetupTransactionResult,
                                    Type111SetupContract)


def _valid_generation(generation: Any) -> bool:
    return (not isinstance(generation, bool) and isinstance(generation, int) and generation >= 1)


class DelegationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class MockStockPrimarySession:
    """A fake Type110 owner whose responses are supplied by an offline fixture."""

    def __init__(self, response: Mapping[str, Any]) -> None:
        self._response = deepcopy(dict(response))
        self.generation: int | None = None
        self.active = False
        self.setup_calls = 0
        self.events: list[str] = []

    def open(self, generation: int) -> None:
        if not _valid_generation(generation):
            raise DelegationError("invalid_session_generation")
        if self.active:
            raise DelegationError("primary_session_already_active")
        self.generation = generation
        self.active = True
        self.events.append("MOCK_PRIMARY_OPEN")

    def handle_setup(self, generation: int, request: Mapping[str, Any]) -> dict[str, Any]:
        if not _valid_generation(generation) or not self.active or generation != self.generation:
            raise DelegationError("stale_or_inactive_primary_session")
        if not isinstance(request, Mapping):
            raise DelegationError("invalid_setup_request")
        self.setup_calls += 1
        self.events.append("MOCK_PRIMARY_SETUP")
        return deepcopy(self._response)

    def revoke(self, generation: int) -> bool:
        if not _valid_generation(generation) or not self.active or generation != self.generation:
            return False
        self.active = False
        self.generation = None
        self.events.append("MOCK_PRIMARY_REVOKE")
        return True


@dataclass(frozen=True)
class DelegatedSetupResult:
    generation: int
    response: Mapping[str, Any]
    secondary_committed: bool
    primary_preserved: bool
    error_code: str | None
    transaction: SetupTransactionResult


class StockFirstType111Delegator:
    """Run the mock primary setup first, then the independently owned child."""

    def __init__(self, primary: MockStockPrimarySession,
                 secondary: Type111SetupContract) -> None:
        self.primary = primary
        self.secondary = secondary
        self._active_generation: int | None = None
        self._lock = RLock()
        self._setup_in_progress = False

    def open(self, generation: int) -> None:
        with self._lock:
            self.primary.open(generation)
            self._active_generation = generation

    def handle_setup(
        self,
        generation: int,
        request: Mapping[str, Any],
        serializer: Callable[[Mapping[str, Any]], SerializerResult],
    ) -> DelegatedSetupResult:
        with self._lock:
            if self._setup_in_progress:
                raise DelegationError("setup_already_in_progress")
            self._setup_in_progress = True
            try:
                return self._handle_setup_locked(generation, request, serializer)
            finally:
                self._setup_in_progress = False

    def _handle_setup_locked(
        self,
        generation: int,
        request: Mapping[str, Any],
        serializer: Callable[[Mapping[str, Any]], SerializerResult],
    ) -> DelegatedSetupResult:
        if (not _valid_generation(generation) or generation != self._active_generation or
                not self.primary.active):
            raise DelegationError("stale_or_inactive_delegation_generation")

        stock_response = self.primary.handle_setup(generation, request)
        stock_snapshot = deepcopy(stock_response)
        transaction = self.secondary.process(request, stock_response, serializer)

        if generation != self._active_generation or not self.primary.active:
            child = self.secondary.lifecycle.current_type111
            if child is not None:
                child.fail()
            return DelegatedSetupResult(
                generation, stock_snapshot, False, True, "session_revoked_during_setup", transaction)

        candidate = transaction.response
        requested_type111 = _contains_type111(request)
        if (candidate is None or
                not _primary_entries_unchanged(stock_snapshot, candidate) or
                not _stock_response_is_preserved(stock_snapshot, candidate, requested_type111)):
            child = self.secondary.lifecycle.current_type111
            if child is not None:
                child.fail()
            return DelegatedSetupResult(
                generation, stock_snapshot, False, False, "primary_response_changed", transaction)

        secondary_committed = bool(requested_type111 and transaction.committed)
        response = candidate if not requested_type111 or secondary_committed else stock_snapshot
        return DelegatedSetupResult(
            generation, deepcopy(response), secondary_committed, True,
            transaction.error_code, transaction)

    def teardown_secondary(self, generation: int) -> bool:
        with self._lock:
            if (not _valid_generation(generation) or generation != self._active_generation or
                    not self.primary.active):
                return False
            child = self.secondary.lifecycle.current_type111
            return child.teardown() if child is not None else False

    def teardown_stream(self, generation: int, stream_type: int) -> bool:
        """Apply stream-local teardown in this synthetic stock-first model.

        Type110 cleanup belongs to the mock primary owner. Only a Type111
        teardown may retire the project child; parent revocation retires both.
        This method is not a Honda teardown parser or protocol contract.
        """
        if isinstance(stream_type, bool) or not isinstance(stream_type, int):
            raise DelegationError("invalid_stream_type")
        if stream_type == 111:
            return self.teardown_secondary(generation)
        if stream_type == 110:
            return False
        raise DelegationError("unsupported_stream_teardown_type")

    def revoke_session(self, generation: int) -> bool:
        with self._lock:
            if not _valid_generation(generation) or generation != self._active_generation:
                return False
            # Parent authority owns the complete synthetic session tree. A
            # revoked parent cannot leave either child Type111 or its modeled
            # Type110 screen active. This is mock lifecycle behavior only; it
            # does not install or describe a Honda finalizer callback.
            self.secondary.lifecycle.destroy_parent()
            revoked = self.primary.revoke(generation)
            self._active_generation = None
            return revoked


def _primary_entries_unchanged(before: Mapping[str, Any], after: Mapping[str, Any]) -> bool:
    from claritylink_jmcs.setup import primary_unchanged

    try:
        return primary_unchanged(before, after)
    except Exception:
        return False


def _stock_response_is_preserved(before: Mapping[str, Any], after: Mapping[str, Any],
                                 secondary_requested: bool) -> bool:
    try:
        original_streams = before.get("streams")
        candidate_streams = after.get("streams")
        if (not isinstance(original_streams, (list, tuple)) or
                not isinstance(candidate_streams, (list, tuple)) or
                any(not isinstance(item, Mapping) for item in original_streams) or
                any(not isinstance(item, Mapping) for item in candidate_streams)):
            return False
        if (dict(before, streams=[]) != dict(after, streams=[]) or
                list(candidate_streams[:len(original_streams)]) != list(original_streams)):
            return False
        suffix = list(candidate_streams[len(original_streams):])
        if not suffix:
            return True
        return (secondary_requested and len(suffix) == 1 and
                suffix[0].get("type") == 111)
    except Exception:
        return False


def _contains_type111(request: Any) -> bool:
    if not isinstance(request, Mapping):
        return False
    streams = request.get("streams")
    return isinstance(streams, (list, tuple)) and any(
        isinstance(item, Mapping) and item.get("type") == 111 for item in streams
    )
