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
    security_mode: str = "HONDA_UNKNOWN"


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


class Type111SetupContract:
    """Prepare listener + response, then invoke the stock serializer exactly once."""

    def __init__(self, lifecycle: DualScreenLifecycleTwin, listeners: DeterministicListenerAllocator) -> None:
        self.lifecycle = lifecycle
        self.listeners = listeners

    def process(
        self,
        request: Mapping[str, Any],
        stock_response: Mapping[str, Any],
        serializer: Callable[[Mapping[str, Any]], SerializerResult],
        *,
        fail_response_mutation: bool = False,
    ) -> SetupTransactionResult:
        generation: Type111Generation | None = None
        listener: ListenerReservation | None = None
        candidate: dict[str, Any] | None = None
        appended = False
        invoked = 0
        try:
            parsed = parse_setup_request(request)
            if not isinstance(stock_response, Mapping):
                raise SetupContractError("stock_response_must_be_mapping")
            original_streams = _response_streams(stock_response)
            type111 = next((item for item in parsed if item.stream_type == 111), None)
            candidate = deepcopy(dict(stock_response))
            if type111 is not None:
                assert type111.stream_connection_id is not None
                generation = self.lifecycle.create_type111(type111.stream_connection_id)
                listener = self.listeners.reserve(generation)
                if not generation.own_resource(listener):
                    raise SetupContractError("listener_ownership_rejected")
                if listener.state is ListenerState.CLOSED:
                    raise SetupContractError("listener_closed_before_commit")
                if fail_response_mutation:
                    raise SetupContractError("response_mutation_failed")
                candidate["streams"] = original_streams + [{"type": 111, "dataPort": listener.port}]
                appended = True
            invoked += 1
            result = serializer(candidate)
            if not isinstance(result, SerializerResult):
                raise SetupContractError("serializer_result_invalid")
            if type111 is None:
                return SetupTransactionResult(candidate, result, invoked, False, None, None, None, False, result.succeeded, None if result.succeeded else "stock_serializer_failed")
            if result.succeeded and generation is not None and generation.activate():
                return SetupTransactionResult(candidate, result, invoked, True, generation.generation, listener.listener_id if listener else None, listener.port if listener else None, appended, True, None)
            generation.fail()
            return SetupTransactionResult(candidate, result, invoked, True, generation.generation, listener.listener_id if listener else None, listener.port if listener else None, appended, False, "stock_serializer_failed")
        except DuplicateStreamConnectionID:
            if generation is not None:
                generation.fail()
            return self._fallback(stock_response, serializer, invoked, _contains_type111(request), "duplicate_stream_connection_id")
        except SetupContractError as exc:
            if generation is not None:
                generation.fail()
            return self._fallback(stock_response, serializer, invoked, _contains_type111(request), exc.code)
        except Exception:
            if generation is not None:
                generation.fail()
            # No exception text or peer fields are returned in diagnostics.
            return self._fallback(stock_response, serializer, invoked, _contains_type111(request), "project_setup_failed")

    @staticmethod
    def _fallback(stock_response: Any, serializer: Callable[[Mapping[str, Any]], SerializerResult], invoked: int, requested: bool, code: str) -> SetupTransactionResult:
        result = None
        response = None
        if invoked == 0:
            try:
                serializer_input = deepcopy(dict(stock_response)) if isinstance(stock_response, Mapping) else stock_response
            except Exception:
                serializer_input = stock_response
            response = serializer_input if isinstance(serializer_input, dict) else None
            try:
                invoked += 1
                candidate = serializer(serializer_input)
                result = candidate if isinstance(candidate, SerializerResult) else None
            except Exception:
                result = None
        return SetupTransactionResult(response, result, invoked, requested, None, None, None, False, False, code)


def _contains_type111(request: Any) -> bool:
    if not isinstance(request, Mapping):
        return False
    streams = request.get("streams")
    return isinstance(streams, (list, tuple)) and any(
        isinstance(item, Mapping) and item.get("type") == 111 for item in streams
    )
