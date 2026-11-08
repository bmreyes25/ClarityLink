"""Mock stock-first Type111 delegation for offline session integration tests.

This adapter has no Honda transport or process access. The primary owner is a
test double, and all Type111 listener/serialization behavior remains in the
existing evidence-bounded setup contract.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from threading import RLock
from typing import Any, Callable, Mapping

from type111_setup_contract import (
    SecurityMode,
    SerializerResult,
    SetupTransactionResult,
    Type111SetupContract,
    contains_type111_request,
)


def _valid_generation(generation: Any) -> bool:
    return (not isinstance(generation, bool) and isinstance(generation, int) and generation >= 1)


def _fail_transaction_generation(transaction: SetupTransactionResult) -> bool:
    generation = transaction.generation_lease
    if generation is None:
        return bool(
            transaction.cleanup_error_code is None and
            (not transaction.requested_type111 or not transaction.committed)
        )
    # Generation tokens stop only their own registry child, even after the
    # lifecycle has advanced to a newer current child.
    try:
        stopped = generation.fail()
    except Exception:
        return False
    if stopped:
        return True
    try:
        return getattr(generation.phase, "name", None) == "STOPPED"
    except Exception:
        return False


def _mark_secondary_rolled_back(
    transaction: SetupTransactionResult,
    stock_response: Mapping[str, Any],
    error_code: str | None,
) -> SetupTransactionResult:
    return replace(
        transaction,
        response=deepcopy(dict(stock_response)),
        listener_id=None,
        data_port=None,
        response_appended=False,
        committed=False,
        error_code=error_code or transaction.error_code,
    )


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
        if (not _valid_generation(generation) or not self.active or
                generation != self.generation):
            return False
        self._clear_generation(generation)
        return True

    def invalidate(self, generation: int) -> bool:
        """Clear state for a parent already marked inactive by its owner."""
        if not _valid_generation(generation) or generation != self.generation:
            return False
        self.active = False
        self.generation = None
        self.events.append("MOCK_PRIMARY_INVALIDATE")
        return True

    def _clear_generation(self, generation: int) -> None:
        self.active = False
        self.generation = None
        self.events.append("MOCK_PRIMARY_REVOKE")


@dataclass(frozen=True)
class DelegatedSetupResult:
    generation: int
    response: Mapping[str, Any]
    secondary_committed: bool
    primary_preserved: bool
    error_code: str | None
    transaction: SetupTransactionResult

    @property
    def security_mode(self) -> str:
        return self.transaction.security_mode.value

    @property
    def fallback_error_code(self) -> str | None:
        return self.transaction.fallback_error_code


class StockFirstType111Delegator:
    """Run one mock parent session and its independently owned child.

    This instance is single-parent. A reconnect needs a fresh primary,
    lifecycle and delegator because a destroyed lifecycle cannot be reopened.
    """

    def __init__(self, primary: MockStockPrimarySession,
                 secondary: Type111SetupContract, *,
                 allow_synthetic_type111_for_tests: bool = False) -> None:
        self.primary = primary
        self.secondary = secondary
        self._allow_synthetic_type111_for_tests = allow_synthetic_type111_for_tests
        self._active_generation: int | None = None
        self._lock = RLock()
        self._setup_in_progress = False

    def open(self, generation: int) -> None:
        with self._lock:
            if self.secondary.lifecycle.parent_destroyed:
                raise DelegationError("parent_lifecycle_destroyed")
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
                not self.primary.active or self.primary.generation != generation):
            raise DelegationError("stale_or_inactive_delegation_generation")

        stock_response = self.primary.handle_setup(generation, request)
        stock_snapshot = deepcopy(stock_response)
        transaction = self.secondary.process(
            request, stock_response, serializer,
            allow_synthetic_type111_for_tests=self._allow_synthetic_type111_for_tests,
        )

        cleanup_retry_failed = False
        if transaction.cleanup_error_code is not None:
            cleanup_retry_failed = not _fail_transaction_generation(transaction)
            if not cleanup_retry_failed:
                transaction = replace(transaction, cleanup_error_code=None)

        if (generation != self._active_generation or not self.primary.active or
                self.primary.generation != generation):
            if generation == self._active_generation and not self.primary.active:
                # Parent loss invalidates every project-owned child, even if this
                # request failed before obtaining a child generation.
                cleanup_ok = not cleanup_retry_failed
                if not cleanup_ok:
                    cleanup_ok = _fail_transaction_generation(transaction)
                try:
                    destroyed = self.secondary.lifecycle.destroy_parent()
                except Exception:
                    cleanup_ok = False
                else:
                    if not destroyed:
                        cleanup_ok = bool(
                            cleanup_ok and self.secondary.lifecycle.parent_destroyed and
                            self.secondary.lifecycle.current_type111 is None and
                            not self.secondary.lifecycle.type110.active
                        )
                self.primary.invalidate(generation)
                if cleanup_ok:
                    self._active_generation = None
            else:
                # A stale transaction must not tear down a newer parent session.
                cleanup_ok = _fail_transaction_generation(transaction)
            if cleanup_ok and (transaction.requested_type111 or transaction.generation_lease is not None):
                transaction = _mark_secondary_rolled_back(
                    transaction, stock_snapshot,
                    "session_revoked_during_setup" if generation == self._active_generation else None,
                )
            return DelegatedSetupResult(
                generation, stock_snapshot, False, True,
                ("session_revoked_during_setup" if cleanup_ok else "type111_cleanup_failed"), transaction)

        if cleanup_retry_failed:
            return DelegatedSetupResult(
                generation, stock_snapshot, False, True,
                "type111_cleanup_failed", transaction)

        if transaction.fallback_error_code is not None:
            cleanup_ok = _fail_transaction_generation(transaction)
            error_code = (
                transaction.fallback_error_code if cleanup_ok
                else "type111_cleanup_failed"
            )
            return DelegatedSetupResult(
                generation, stock_snapshot, False, False, error_code, transaction)

        candidate = transaction.response
        requested_type111 = contains_type111_request(request)
        if transaction.error_code in (
            "stock_response_must_be_mapping", "stock_response_streams_invalid"
        ):
            return DelegatedSetupResult(
                generation, stock_snapshot, False, False,
                transaction.error_code, transaction)
        if candidate is None:
            return DelegatedSetupResult(
                generation, stock_snapshot, False, False,
                transaction.error_code or "stock_response_unavailable", transaction)
        if (not _primary_entries_unchanged(stock_snapshot, candidate) or
                not _stock_response_is_preserved(stock_snapshot, candidate, requested_type111)):
            cleanup_ok = _fail_transaction_generation(transaction)
            if cleanup_ok and (transaction.requested_type111 or transaction.generation_lease is not None):
                transaction = _mark_secondary_rolled_back(
                    transaction, stock_snapshot,
                    "primary_response_changed",
                )
            return DelegatedSetupResult(
                generation, stock_snapshot, False, False,
                ("primary_response_changed" if cleanup_ok else "type111_cleanup_failed"), transaction)

        synthetic_only = transaction.security_mode is SecurityMode.SYNTHETIC_TEST_ONLY
        secondary_committed = bool(
            requested_type111 and transaction.committed and synthetic_only and
            self._allow_synthetic_type111_for_tests
        )
        error_code = transaction.error_code
        response = candidate if not requested_type111 or secondary_committed else stock_snapshot
        if transaction.committed and requested_type111 and not secondary_committed:
            error_code = error_code or "type111_not_enabled_by_delegator"
            if not _fail_transaction_generation(transaction):
                error_code = "type111_cleanup_failed"
            else:
                transaction = _mark_secondary_rolled_back(
                    transaction, stock_snapshot, error_code,
                )
        return DelegatedSetupResult(
            generation, deepcopy(response), secondary_committed, True,
            error_code, transaction)

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
            if self.primary.active and self.primary.generation != generation:
                return False
            # Parent authority owns the complete synthetic session tree. A
            # revoked parent cannot leave either child Type111 or its modeled
            # Type110 screen active. This is mock lifecycle behavior only; it
            # does not install or describe a Honda finalizer callback.
            cleanup_ok = True
            child = self.secondary.lifecycle.current_type111
            if child is not None:
                try:
                    stopped = child.fail()
                except Exception:
                    stopped = False
                if not stopped:
                    cleanup_ok = getattr(child.phase, "name", None) == "STOPPED"
            try:
                destroyed = self.secondary.lifecycle.destroy_parent()
            except Exception:
                destroyed = False
                cleanup_ok = False
            if not destroyed:
                cleanup_ok = bool(
                    cleanup_ok and self.secondary.lifecycle.parent_destroyed and
                    self.secondary.lifecycle.current_type111 is None and
                    not self.secondary.lifecycle.type110.active
                )
            if not cleanup_ok:
                self.primary.invalidate(generation)
                return False
            if self.primary.active:
                primary_revoked = self.primary.revoke(generation)
                if not primary_revoked:
                    return False
            else:
                self.primary.invalidate(generation)
                if self.primary.active or self.primary.generation is not None:
                    return False
            self._active_generation = None
            return True


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
