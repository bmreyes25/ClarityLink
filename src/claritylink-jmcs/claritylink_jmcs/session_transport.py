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


@dataclass(frozen=True)
class ControlRequest:
    method: str
    path: str
    body: Mapping[str, Any]
    generation: int


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
        return self._requests.popleft()

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
        if handoff.origin is not SessionOrigin.AUTHENTICATED_LAB:
            raise TransportError("authenticated_origin_required")
        channel = handoff.transport
        if not all(callable(getattr(channel, name, None)) for name in ("read_request", "write_response", "close")):
            raise TransportError("invalid_authenticated_channel")
        self._handoff = handoff
        self._channel = channel
        self._closed = False

    @property
    def authenticated(self) -> bool:
        return not self._closed

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
        request = self._channel.read_request(timeout)
        if not isinstance(request, ControlRequest) or request.generation != self.generation:
            raise TransportError("invalid_or_stale_request")
        return request

    def write_response(self, response: ControlResponse) -> None:
        if self._closed or response.generation != self.generation:
            raise TransportError("stale_or_closed_transport")
        self._channel.write_response(response)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._channel.close()
