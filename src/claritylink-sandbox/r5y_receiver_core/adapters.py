"""Typed host-only extension contracts and symbolic mock providers.

NO HONDA IMPLEMENTATION. REQUIRES NEW HONDA_STATIC EVIDENCE.
NOT AUTHORIZED FOR VEHICLE USE.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .model import DecodedFrame, DisplayFrame, MediaFrame, ReceiverError, SessionGeneration


class ReceiverEntryAdapter(Protocol):
    def session_label(self) -> str: ...


class SetupRequestAdapter(Protocol):
    def synthetic_request_label(self) -> str: ...


class SetupResponseAdapter(Protocol):
    def synthetic_response_label(self) -> str: ...


class SessionIdentityAdapter(Protocol):
    def generation(self) -> SessionGeneration: ...


class LifecycleAdapter(Protocol):
    def closed(self, generation: SessionGeneration) -> bool: ...


class ListenerProvider(Protocol):
    def allocate(self, generation: SessionGeneration) -> ListenerHandle: ...


class SecurityProvider(Protocol):
    def create(self, generation: SessionGeneration) -> SecurityContext: ...


class DecoderProvider(Protocol):
    def create(self, generation: SessionGeneration) -> MockDecoder: ...


class DisplaySink(Protocol):
    generation: SessionGeneration
    current: DisplayFrame | None
    def show(self, frame: DisplayFrame) -> None: ...
    def clear(self, reason: str) -> None: ...
    def close(self) -> bool: ...


class DisplayProvider(Protocol):
    def create(self, generation: SessionGeneration) -> DisplaySink: ...


@dataclass
class ListenerHandle:
    generation: SessionGeneration
    port_label: str
    allocated: bool = True
    accepted: bool = False
    closed: bool = False

    def accept(self, generation: SessionGeneration) -> None:
        if generation != self.generation or self.closed:
            raise ReceiverError("listener_generation_or_state_mismatch")
        self.accepted = True

    def close(self, generation: SessionGeneration) -> bool:
        if generation != self.generation:
            raise ReceiverError("stale_listener_close")
        if self.closed:
            return False
        self.closed = True
        self.accepted = False
        return True


@dataclass
class SecurityContext:
    generation: SessionGeneration
    context_label: str
    initialized: bool = False
    ready: bool = False
    destroyed: bool = False

    def initialize(self) -> None:
        if self.destroyed:
            raise ReceiverError("security_destroyed")
        self.initialized = self.ready = True

    def unwrap_symbol(self, frame: MediaFrame) -> str:
        if not self.ready or self.destroyed or frame.generation != self.generation:
            raise ReceiverError("mock_security_unavailable")
        return "clear-" + frame.symbol

    def destroy(self) -> bool:
        if self.destroyed:
            return False
        self.destroyed = True
        self.ready = False
        return True


@dataclass
class MockDecoder:
    generation: SessionGeneration
    closed: bool = False

    def decode(self, sequence: int, clear_symbol: str) -> DecodedFrame:
        if self.closed or not clear_symbol.startswith("clear-frame-"):
            raise ReceiverError("mock_decode_unavailable")
        return DecodedFrame(self.generation, sequence, "decoded-" + clear_symbol)

    def close(self) -> bool:
        if self.closed:
            return False
        self.closed = True
        return True


@dataclass
class MockDisplay1Sink:
    generation: SessionGeneration
    current: DisplayFrame | None = None
    frame_count: int = 0
    clear_reason: str | None = None
    closed: bool = False

    def show(self, frame: DisplayFrame) -> None:
        if self.closed or frame.generation != self.generation:
            raise ReceiverError("mock_display_generation_or_state_mismatch")
        self.current = frame
        self.frame_count += 1
        self.clear_reason = None

    def clear(self, reason: str) -> None:
        self.current = None
        self.clear_reason = reason

    def close(self) -> bool:
        if self.closed:
            return False
        self.clear("teardown")
        self.closed = True
        return True


class MockListenerProvider:
    def allocate(self, generation: SessionGeneration) -> ListenerHandle:
        return ListenerHandle(generation, f"mock-port-{50000 + generation.value}")


class MockSecurityProvider:
    def create(self, generation: SessionGeneration) -> SecurityContext:
        return SecurityContext(generation, f"mock-security-{generation.value}")


class MockDecoderProvider:
    def create(self, generation: SessionGeneration) -> MockDecoder:
        return MockDecoder(generation)


class MockDisplayProvider:
    def create(self, generation: SessionGeneration) -> MockDisplay1Sink:
        return MockDisplay1Sink(generation)
