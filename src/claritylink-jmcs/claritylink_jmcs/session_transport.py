"""Authenticated CarPlay control-session transport contract and replay adapter."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from .authentication import SessionHandoff, SessionOrigin


class TransportError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


MAX_REQUEST_BYTES = 1_000_000


def validate_control_request(request: ControlRequest, generation: int) -> None:
    """Bound structured input even when an authority adapter has already parsed it."""
    if not isinstance(request, ControlRequest) or request.generation != generation:
        raise TransportError("invalid_or_stale_request")
    if (not isinstance(request.method, str) or len(request.method) > 16 or
            not isinstance(request.path, str) or len(request.path) > 128 or
            not isinstance(request.body, Mapping) or
            (request.content_type is not None and
             (not isinstance(request.content_type, str) or len(request.content_type) > 128))):
        raise TransportError("malformed_control_request")
    count = 0
    size = 0
    def walk(value: Any, depth: int) -> None:
        nonlocal count, size
        count += 1
        if depth > 12 or count > 4096:
            raise TransportError("control_structure_limit")
        if isinstance(value, Mapping):
            if len(value) > 256:
                raise TransportError("control_structure_limit")
            for key, item in value.items():
                if not isinstance(key, str) or len(key) > 256:
                    raise TransportError("control_key_limit")
                size += len(key.encode("utf-8"))
                walk(item, depth + 1)
        elif isinstance(value, (list, tuple)):
            if len(value) > 256:
                raise TransportError("control_array_limit")
            for item in value:
                walk(item, depth + 1)
        elif isinstance(value, str):
            if len(value) > 4096:
                raise TransportError("control_string_limit")
            size += len(value.encode("utf-8"))
        elif isinstance(value, bytes):
            size += len(value)
        elif isinstance(value, bool) or value is None or isinstance(value, (int, float)):
            pass
        else:
            raise TransportError("control_value_type")
        if size > MAX_REQUEST_BYTES:
            raise TransportError("control_request_too_large")
    walk(request.body, 0)


@dataclass(frozen=True)
class ControlRequest:
    method: str
    path: str
    body: Mapping[str, Any]
    generation: int
    content_type: str | None = None


@dataclass(frozen=True)
class ControlResponse:
    status: int
    body: Mapping[str, Any]
    generation: int


class CarPlaySessionTransport(Protocol):
    @property
    def authenticated(self) -> bool: ...
    @property
    def session_identifier(self) -> str: ...
    @property
    def generation(self) -> int: ...
    def read_request(self, timeout: float) -> ControlRequest: ...
    def write_response(self, response: ControlResponse) -> None: ...
    def close(self) -> None: ...


class ReplaySessionTransport:
    """Bounded structured replay, never a live authenticated connection."""

    def __init__(self, handoff: SessionHandoff, requests: list[ControlRequest]) -> None:
        if handoff.origin is not SessionOrigin.SANITIZED_REPLAY:
            raise TransportError("replay_origin_required")
        if len(requests) > 64 or any(x.generation != handoff.generation for x in requests):
            raise TransportError("invalid_replay_requests")
        self._handoff = handoff
        self._requests = deque(requests)
        self.responses: list[ControlResponse] = []
        self._closed = False

    @property
    def authenticated(self) -> bool:
        return False

    @property
    def session_identifier(self) -> str:
        return self._handoff.session_identifier

    @property
    def generation(self) -> int:
        return self._handoff.generation

    def read_request(self, timeout: float) -> ControlRequest:
        if self._closed:
            raise TransportError("transport_closed")
        if not 0 < timeout <= 30:
            raise TransportError("invalid_timeout")
        if not self._requests:
            raise TransportError("replay_eof")
        request = self._requests.popleft()
        validate_control_request(request, self.generation)
        return request

    def write_response(self, response: ControlResponse) -> None:
        if self._closed or response.generation != self.generation:
            raise TransportError("stale_or_closed_transport")
        if len(self.responses) >= 64:
            raise TransportError("response_limit")
        self.responses.append(response)

    def close(self) -> None:
        self._closed = True
        self._requests.clear()


class LabSessionTransport:
    """Delegates to an authenticated external control channel after handoff."""

    def __init__(self, handoff: SessionHandoff) -> None:
        if handoff.origin is not SessionOrigin.AUTHENTICATED_LAB or not handoff.authenticated or handoff.closed:
            raise TransportError("authenticated_origin_required")
        channel = handoff.transport
        if not all(callable(getattr(channel, name, None)) for name in ("read_request", "write_response", "close")):
            raise TransportError("invalid_authenticated_channel")
        if (getattr(channel, "authenticated", False) is not True or
                getattr(channel, "session_identifier", None) != handoff.session_identifier or
                getattr(channel, "generation", None) != handoff.generation):
            raise TransportError("channel_identity_mismatch")
        self._handoff = handoff
        self._channel = channel
        self._closed = False

    @property
    def authenticated(self) -> bool:
        return not self._closed and not self._handoff.closed and getattr(self._channel, "authenticated", False) is True

    @property
    def session_identifier(self) -> str:
        return self._handoff.session_identifier

    @property
    def generation(self) -> int:
        return self._handoff.generation

    def read_request(self, timeout: float) -> ControlRequest:
        if not self.authenticated:
            raise TransportError("transport_closed")
        if not 0 < timeout <= 30:
            raise TransportError("invalid_timeout")
        try:
            request = self._channel.read_request(timeout)
        except (TimeoutError, EOFError, ConnectionError) as exc:
            raise TransportError("peer_disconnected_or_timeout") from exc
        validate_control_request(request, self.generation)
        return request

    def write_response(self, response: ControlResponse) -> None:
        if not self.authenticated or response.generation != self.generation:
            raise TransportError("stale_or_closed_transport")
        self._channel.write_response(response)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._handoff.close()
