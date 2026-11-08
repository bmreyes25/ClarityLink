"""Offline Honda-facing Type111 SETUP/listener contract.

This models project preparation around the known stock serializer seam. It
does not execute Honda code or establish Honda Type111 acceptance/security.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping

from legacy_dual_screen_twin import DuplicateStreamConnectionID, ScreenRole
from dual_screen_lifecycle import DualScreenLifecycleTwin, Type111Generation
from project_lifecycle import ProjectSessionKey

MAX_UINT64 = (1 << 64) - 1
SERIALIZER_SUCCESS_R0 = 0xC8


class SetupContractError(ValueError):
    """Sanitized fail-closed contract error; never includes peer identifiers."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ListenerState(str, Enum):
    RESERVED = "RESERVED"
    LISTENING = "LISTENING"
    CLOSED = "CLOSED"


class SecurityMode(str, Enum):
    """Describes evidence status; only the synthetic value permits lab output."""

    HONDA_UNKNOWN = "HONDA_UNKNOWN"
    TYPE111_DISABLED_AUTHORITY_UNKNOWN = "TYPE111_DISABLED_AUTHORITY_UNKNOWN"
    SYNTHETIC_TEST_ONLY = "SYNTHETIC_TEST_ONLY"


@dataclass
class ListenerReservation:
    listener_id: int
    port: int
    owner_key: ProjectSessionKey
    role: ScreenRole = ScreenRole.TYPE111_SYNTHETIC
    state: ListenerState = ListenerState.LISTENING
    close_count: int = 0

    @property
    def generation(self) -> int:
        return self.owner_key.generation

    def close(self) -> None:
        if self.state is not ListenerState.CLOSED:
            self.state = ListenerState.CLOSED
            self.close_count += 1


class DeterministicListenerAllocator:
    """Fake allocator: no OS socket, with deterministic failure injection."""

    def __init__(self, first_port: int = 41000, *, fail_at: str | None = None) -> None:
        self._next_port = first_port
        self._next_id = 1
        self.fail_at = fail_at
        self.reservations: list[ListenerReservation] = []

    def reserve(self, generation: Type111Generation) -> ListenerReservation:
        if self.fail_at in ("allocate", "bind", "listen"):
            raise SetupContractError("listener_reservation_failed")
        port = self._next_port
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise SetupContractError("invalid_listener_port")
        self._next_port += 1
        reservation = ListenerReservation(self._next_id, port, generation.key)
        self._next_id += 1
        self.reservations.append(reservation)
        if self.fail_at == "closed_before_commit":
            reservation.close()
        return reservation


@dataclass(frozen=True)
class SetupStreamRequest:
    stream_type: int
    stream_connection_id: int | None
    request_index: int
    fields: Mapping[str, Any]


@dataclass(frozen=True)
class SerializerResult:
    r0: int
    status_out: int
    continuation: str = "ORIGINAL_CONTINUATION"

    @property
    def succeeded(self) -> bool:
        return self.r0 == SERIALIZER_SUCCESS_R0 and self.status_out == 0


@dataclass(frozen=True)
class SetupTransactionResult:
    response: dict[str, Any] | None
    serializer_result: SerializerResult | None
    serializer_invocations: int
    requested_type111: bool
    generation: int | None
    listener_id: int | None
    data_port: int | None
    response_appended: bool
    committed: bool
    error_code: str | None
    security_mode: SecurityMode = SecurityMode.HONDA_UNKNOWN
    fallback_error_code: str | None = None
    generation_lease: Type111Generation | None = None
    cleanup_error_code: str | None = None
    candidate_serializer_result: SerializerResult | None = None


def parse_setup_request(request: Mapping[str, Any]) -> tuple[SetupStreamRequest, ...]:
    if not isinstance(request, Mapping):
        raise SetupContractError("request_must_be_mapping")
    streams = request.get("streams")
    if not isinstance(streams, (list, tuple)):
        raise SetupContractError("request_streams_must_be_array")
    parsed: list[SetupStreamRequest] = []
    seen_ids: dict[int, int] = {}
    count111 = 0
    for index, entry in enumerate(streams):
        if not isinstance(entry, Mapping):
            raise SetupContractError("stream_entry_must_be_mapping")
        kind = entry.get("type")
        if isinstance(kind, bool) or not isinstance(kind, int):
            raise SetupContractError("stream_type_must_be_integer")
        cid = entry.get("streamConnectionID")
        if kind in (110, 111):
            if isinstance(cid, bool) or not isinstance(cid, int) or not 1 <= cid <= MAX_UINT64:
                raise SetupContractError("screen_stream_connection_id_invalid")
            if cid in seen_ids:
                raise DuplicateStreamConnectionID((ScreenRole.TYPE110, ScreenRole.TYPE111_SYNTHETIC))
            seen_ids[cid] = kind
        if kind == 111:
            count111 += 1
        parsed.append(SetupStreamRequest(kind, cid if isinstance(cid, int) and not isinstance(cid, bool) else None, index, deepcopy(dict(entry))))
    if count111 > 1:
        raise SetupContractError("duplicate_type111_request")
    if count111 and any(item.stream_type not in (100, 101, 110, 111) for item in parsed):
        raise SetupContractError("unsupported_stream_type_for_type111_adapter")
    return tuple(parsed)


def _response_streams(response: Mapping[str, Any]) -> list[dict[str, Any]]:
    streams = response.get("streams")
    if not isinstance(streams, (list, tuple)) or any(not isinstance(item, Mapping) for item in streams):
        raise SetupContractError("stock_response_streams_invalid")
    return [deepcopy(dict(item)) for item in streams]


def _real_listener_types():
    try:
        from real_listener import InterfaceKind, InterfacePolicy, RealListenerAllocator
        return InterfaceKind, InterfacePolicy, RealListenerAllocator
    except ModuleNotFoundError as exc:
        if exc.name == "real_listener":
            return None
        raise


def _is_synthetic_listener(listeners: Any) -> bool:
    if type(listeners) is DeterministicListenerAllocator:
        return True
    listener_types = _real_listener_types()
    if listener_types is None:
        return False
    interface_kind, interface_policy, real_listener_allocator = listener_types
    return (
        type(listeners) is real_listener_allocator and
        type(getattr(listeners, "policy", None)) is interface_policy and
        listeners.policy.kind is interface_kind.LOOPBACK_TEST
    )


class Type111SetupContract:
    """Offline transaction model; Type111 is disabled unless test mode is explicit.

    `enable_synthetic_type111_for_tests` exercises lifecycle/rollback mechanics
    with lab resources only. It is not an authorization or Honda integration
    switch. The default path rejects Type111 before listener allocation.
    """

    def __init__(
        self, lifecycle: DualScreenLifecycleTwin,
        listeners: Any, *,
        enable_synthetic_type111_for_tests: bool = False,
    ) -> None:
        if enable_synthetic_type111_for_tests and not _is_synthetic_listener(listeners):
            raise ValueError("synthetic_type111_requires_loopback_or_deterministic_listener")
        self.lifecycle = lifecycle
        self._listeners = listeners
        self._synthetic_type111_for_tests = enable_synthetic_type111_for_tests

    @property
    def listeners(self) -> Any:
        return self._listeners

    def process(
        self,
        request: Mapping[str, Any],
        stock_response: Mapping[str, Any],
        serializer: Callable[[Mapping[str, Any]], SerializerResult],
        *,
        fail_response_mutation: bool = False,
        allow_synthetic_type111_for_tests: bool | None = None,
    ) -> SetupTransactionResult:
        """Run a host-only response-construction probe, never network I/O.

        The serializer callback must not publish bytes or perform transport
        side effects. A caller may expose the returned response only after this
        method returns; real integration needs an explicit response-commit
        boundary.
        """
        synthetic_enabled = (
            self._synthetic_type111_for_tests and
            allow_synthetic_type111_for_tests is not False
        )
        generation: Type111Generation | None = None
        listener: ListenerReservation | None = None
        candidate: dict[str, Any] | None = None
        appended = False
        invoked = 0
        serialized_result: SerializerResult | None = None
        try:
            parsed = parse_setup_request(request)
            if not isinstance(stock_response, Mapping):
                raise SetupContractError("stock_response_must_be_mapping")
            original_streams = _response_streams(stock_response)
            type111 = next((item for item in parsed if item.stream_type == 111), None)
            if type111 is not None and not synthetic_enabled:
                raise SetupContractError("type111_authority_unavailable")
            candidate = deepcopy(dict(stock_response))
            if type111 is not None:
                assert type111.stream_connection_id is not None
                if synthetic_enabled and not _is_synthetic_listener(self.listeners):
                    raise SetupContractError("synthetic_listener_policy_invalid")
                generation = self.lifecycle.create_type111(type111.stream_connection_id)
                listener = self.listeners.reserve(generation)
                if not generation.own_resource(listener):
                    raise SetupContractError("listener_ownership_rejected")
                if getattr(listener.state, "value", listener.state) == ListenerState.CLOSED.value:
                    raise SetupContractError("listener_closed_before_commit")
                if fail_response_mutation:
                    raise SetupContractError("response_mutation_failed")
                candidate["streams"] = original_streams + [{"type": 111, "dataPort": listener.port}]
                appended = True
            serializer_candidate = deepcopy(candidate)
            invoked += 1
            result = serializer(serializer_candidate)
            if not isinstance(result, SerializerResult):
                raise SetupContractError("serializer_result_invalid")
            serialized_result = result
            if not _mapping_matches(serializer_candidate, candidate):
                raise SetupContractError("serializer_candidate_mutated")
            if type111 is None:
                return SetupTransactionResult(serializer_candidate, result, invoked, False, None, None, None, False, result.succeeded, None if result.succeeded else "stock_serializer_failed")
            if result.succeeded and generation is not None and generation.activate():
                return SetupTransactionResult(
                    serializer_candidate, result, invoked, True, generation.generation,
                    listener.listener_id if listener else None,
                    listener.port if listener else None, appended, True, None,
                    self._security_mode(request, synthetic_enabled),
                    generation_lease=generation,
                )
            cleanup_error = _generation_cleanup_failed(generation)
            failure_code = (
                "type111_activation_failed"
                if result.succeeded else "type111_candidate_serializer_failed"
            )
            return self._fallback(
                stock_response, serializer, invoked, True, failure_code,
                security_mode=self._security_mode(request, synthetic_enabled),
                serializer_result=result, generation_lease=generation,
                cleanup_error_code=("type111_cleanup_failed" if cleanup_error else None),
                retry_stock_serializer=True,
            )
        except DuplicateStreamConnectionID:
            cleanup_error = _generation_cleanup_failed(generation)
            return self._fallback(
                stock_response, serializer, invoked, contains_type111_request(request),
                "duplicate_stream_connection_id",
                security_mode=self._security_mode(request, synthetic_enabled),
                generation_lease=generation,
                cleanup_error_code=("type111_cleanup_failed" if cleanup_error else None),
            )
        except SetupContractError as exc:
            cleanup_error = _generation_cleanup_failed(generation)
            return self._fallback(
                stock_response, serializer, invoked, contains_type111_request(request),
                exc.code, security_mode=self._security_mode(request, synthetic_enabled),
                serializer_result=serialized_result,
                generation_lease=generation,
                cleanup_error_code=("type111_cleanup_failed" if cleanup_error else None),
                retry_stock_serializer=(generation is not None),
            )
        except Exception:
            cleanup_error = _generation_cleanup_failed(generation)
            # No exception text or peer fields are returned in diagnostics.
            return self._fallback(
                stock_response, serializer, invoked, contains_type111_request(request),
                "project_setup_failed", security_mode=self._security_mode(request, synthetic_enabled),
                serializer_result=serialized_result,
                generation_lease=generation,
                cleanup_error_code=("type111_cleanup_failed" if cleanup_error else None),
                retry_stock_serializer=(generation is not None),
            )

    def _security_mode(self, request: Any, synthetic_enabled: bool) -> SecurityMode:
        if not contains_type111_request(request):
            return SecurityMode.HONDA_UNKNOWN
        return (SecurityMode.SYNTHETIC_TEST_ONLY if synthetic_enabled
                else SecurityMode.TYPE111_DISABLED_AUTHORITY_UNKNOWN)

    @staticmethod
    def _fallback(
        stock_response: Any, serializer: Callable[[Mapping[str, Any]], SerializerResult],
        invoked: int, requested: bool, code: str,
        *, security_mode: SecurityMode = SecurityMode.HONDA_UNKNOWN,
        serializer_result: SerializerResult | None = None,
        generation_lease: Type111Generation | None = None,
        cleanup_error_code: str | None = None,
        retry_stock_serializer: bool = False,
    ) -> SetupTransactionResult:
        result = serializer_result
        candidate_result = serializer_result if retry_stock_serializer else None
        response = None
        fallback_error_code = None
        if invoked == 0 or retry_stock_serializer:
            try:
                serializer_input = (deepcopy(dict(stock_response))
                                    if isinstance(stock_response, Mapping)
                                    else deepcopy(stock_response))
                response = deepcopy(serializer_input) if isinstance(serializer_input, dict) else None
            except Exception:
                # Preserve the factory serializer path even when an opaque stock
                # value cannot be copied. No project Type111 fields are added.
                serializer_input = stock_response
                response = None
                fallback_error_code = "stock_response_copy_failed"
            try:
                invoked += 1
                candidate = serializer(serializer_input)
                result = candidate if isinstance(candidate, SerializerResult) else None
                if candidate is not None and result is None:
                    fallback_error_code = "stock_serializer_result_invalid"
                if (isinstance(serializer_input, dict) and isinstance(response, Mapping) and
                        not _mapping_matches(serializer_input, response)):
                    fallback_error_code = "stock_serializer_mutated_response"
            except Exception:
                result = None
                fallback_error_code = "stock_serializer_failed"
        elif invoked > 0:
            # The stock serializer already ran. Preserve a fresh factory snapshot
            # for its caller without invoking the serializer a second time.
            try:
                response = (deepcopy(dict(stock_response))
                            if isinstance(stock_response, Mapping)
                            else deepcopy(stock_response))
            except Exception:
                response = None
                fallback_error_code = "stock_response_copy_failed"
        return SetupTransactionResult(
            response, result, invoked, requested, None, None, None, False, False,
            code, security_mode, fallback_error_code, generation_lease,
            cleanup_error_code, candidate_result,
        )


def _generation_cleanup_failed(generation: Type111Generation | None) -> bool:
    """Attempt exact cleanup; report an exception or an un-stopped live child."""
    if generation is None:
        return False
    try:
        stopped = generation.fail()
    except Exception:
        return True
    if stopped:
        return False
    try:
        return getattr(generation.phase, "name", None) != "STOPPED"
    except Exception:
        return True


def _mapping_matches(left: Any, right: Any) -> bool:
    try:
        return isinstance(left, Mapping) and isinstance(right, Mapping) and left == right
    except Exception:
        return False


def contains_type111_request(request: Any) -> bool:
    if not isinstance(request, Mapping):
        return False
    streams = request.get("streams")
    return isinstance(streams, (list, tuple)) and any(
        isinstance(item, Mapping) and not isinstance(item.get("type"), bool) and
        isinstance(item.get("type"), int) and
        item.get("type") == 111 for item in streams
    )
