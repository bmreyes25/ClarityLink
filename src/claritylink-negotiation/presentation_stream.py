"""Offline adapter connecting synthetic Type111 presentation state to the host stream registry.

The adapter consumes only an already registered lab Type111 stream. It does not
serialize CarPlay control messages or assert Honda receiver compatibility.
"""
from __future__ import annotations

import threading
from typing import Any

from claritylink_jmcs.capabilities import DualDisplayCapabilityPlan
from claritylink_jmcs.receiver import Receiver, ReceiverError
from claritylink_jmcs.stream_dispatch import StreamIdentity

from presentation_state import PresentationState


class PresentationOutput:
    """One-frame hidden-view retention around a real host Display1Output sink."""

    MAX_RETAINED_FRAME_BYTES = 8 * 1024 * 1024

    def __init__(self, state: PresentationState, output: Any) -> None:
        if state is None or output is None:
            raise ValueError("presentation_state_and_output_required")
        self.state = state
        self.output = output
        self._lock = threading.RLock()
        self._latest: Any | None = None
        self._generation = state.generation

    def begin_generation(self, generation: int) -> None:
        if generation != self.state.generation:
            raise ValueError("presentation_generation_mismatch")
        with self._lock:
            self._generation = generation
            self._latest = None
        begin = getattr(self.output, "begin_generation", None)
        if begin is not None:
            begin(generation)

    def show(self, frame: Any) -> None:
        png = getattr(frame, "png", None)
        if not isinstance(png, bytes) or not 0 < len(png) <= self.MAX_RETAINED_FRAME_BYTES:
            raise ValueError("presentation_frame_exceeds_retention_budget")
        with self._lock:
            if getattr(frame, "generation", None) <= 0:
                raise ValueError("invalid_presentation_frame_generation")
            self._latest = frame
            if self.state.visible:
                self.output.show(frame)

    def clear(self) -> None:
        with self._lock:
            self._latest = None
            self.output.clear()

    def set_visible(self, visible: bool) -> None:
        with self._lock:
            if visible:
                if self.state.visible and self._latest is not None:
                    self.output.show(self._latest)
            else:
                self.output.clear()

    def set_geometry(self, view_area: object | None, safe_area: object | None) -> None:
        # Geometry remains presentation state; stream identity and dispatch are untouched.
        with self._lock:
            self.view_area = view_area
            self.safe_area = safe_area


class PresentationStreamCoordinator:
    """Connect existing UI state to an already setup Receiver Type111 dispatcher."""

    def __init__(self, receiver: Receiver, state: PresentationState,
                 capability: DualDisplayCapabilityPlan, output: PresentationOutput) -> None:
        if receiver is None or state is None or capability is None or output is None:
            raise ValueError("receiver_presentation_capability_and_output_required")
        if (capability.generation != state.generation or capability.secondary is None or
                not capability.preserves_primary_ownership or output.state is not state or
                receiver.display is not output):
            raise ValueError("incoherent_synthetic_secondary_session")
        self.receiver = receiver
        self.state = state
        self.capability = capability
        self.output = output
        self.identity: StreamIdentity | None = None
        self._parent_active = True
        self.events: list[str] = ["SYNTHETIC_CAPABILITY_REGISTERED"]

    def register_existing_type111(self) -> StreamIdentity:
        if not self.state.active:
            raise ReceiverError("presentation_transport_inactive")
        identity = self.receiver.stream_identity(111)
        descriptor = self.capability.secondary
        if (identity.session_generation != self.state.generation or
                identity.connection_id != descriptor.stream_connection_id or
                identity.output_id != 2):
            raise ReceiverError("type111_capability_stream_identity_mismatch")
        self.identity = identity
        self.events.append("TYPE111_EXISTING_STREAM_BOUND")
        return identity

    def _require_identity(self) -> StreamIdentity:
        if self.identity is None:
            raise ReceiverError("type111_stream_not_registered")
        current = self.receiver.stream_identity(111)
        if current != self.identity:
            raise ReceiverError("type111_stream_identity_changed")
        return current

    def set_navigation(self, provider: str | None, *, active: bool,
                       instruction_active: bool = False) -> None:
        identity = self._require_identity()
        self.state.set_navigation(provider, active=active,
                                  instruction_active=instruction_active)
        self.output.set_visible(self.state.visible)
        self._assert_identity(identity)
        self.events.append("NAVIGATION_ELIGIBILITY_CHANGED")

    def control(self, command: str, *, value: object | None = None) -> None:
        identity = self._require_identity()
        self.state.control(command, value=value)
        if command in {"showUI", "stopUI"}:
            self.output.set_visible(self.state.visible)
        elif command in {"ViewArea", "SafeArea"}:
            self.output.set_geometry(self.state.view_area, self.state.safe_area)
        self._assert_identity(identity)
        self.events.append(f"PRESENTATION_{command.upper()}_APPLIED")

    def update_video_config(self, width: int, height: int) -> int:
        identity = self._require_identity()
        before = self.state.video_config
        decoder_generation = self.state.update_video_config(width, height)
        if self.state.video_config != before:
            receiver_generation = self.receiver.restart_secondary_decoder(
                self.state.generation, width, height)
            if receiver_generation != decoder_generation:
                raise ReceiverError("decoder_generation_model_mismatch")
            self.events.append("TYPE111_DECODER_RESTARTED")
        self._assert_identity(identity)
        return decoder_generation

    def dispatch_decoded(self, frame: Any) -> bool:
        identity = self._require_identity()
        if getattr(frame, "generation", None) != identity.stream_generation:
            raise ReceiverError("decoded_frame_generation_mismatch")
        return self.receiver.dispatch_decoded_frame(identity, frame)

    def teardown_type111(self) -> None:
        identity = self._require_identity()
        self.receiver.teardown_secondary(self.state.generation)
        self.state.transport_restart_required("teardown")
        self.identity = None
        self.events.append(f"TYPE111_STREAM_TORN_DOWN:{identity.connection_id}")

    def teardown_parent(self) -> None:
        if self._parent_active:
            self.receiver.teardown(self.state.generation)
            if self.state.active:
                self.state.transport_restart_required("teardown")
            self.identity = None
            self._parent_active = False
            self.events.append("PARENT_SESSION_TORN_DOWN")

    def _assert_identity(self, expected: StreamIdentity) -> None:
        if self.receiver.stream_identity(111) != expected:
            raise ReceiverError("presentation_event_changed_transport_identity")
