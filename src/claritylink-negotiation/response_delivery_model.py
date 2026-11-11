"""Synthetic-only project child ownership and HTTP delivery lifecycle model.

No Honda code is executed. Honda parent teardown effects are an explicit input
so tests can separate project cleanup from stock session behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DeliveryState(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    PREPARED = "PREPARED"
    SERIALIZED_LOCAL = "SERIALIZED_LOCAL"
    TRANSMISSION_STARTED = "TRANSMISSION_STARTED"
    DELIVERY_UNKNOWN = "DELIVERY_UNKNOWN"
    SEND_FAILED_NO_OUTPUT = "SEND_FAILED_NO_OUTPUT"
    SERIALIZATION_FAILED = "SERIALIZATION_FAILED"
    TRANSPORT_COMPLETE = "TRANSPORT_COMPLETE"
    FAILED_BEFORE_SERIALIZATION = "FAILED_BEFORE_SERIALIZATION"


@dataclass
class SyntheticResponseDelivery:
    type110_active: bool = True
    type110_crypto: bytes = b"synthetic-type110-crypto-snapshot"
    center_screen_state: str = "synthetic-center-screen-active"
    audio_active: bool = True
    entry_local: bool = False
    entry_array_owned: bool = False
    response_graph_live: bool = True
    listener_open: bool = False
    accepted_socket_open: bool = False
    decoder_live: bool = False
    close_count: int = 0
    socket_close_count: int = 0
    decoder_release_count: int = 0
    graph_release_count: int = 0
    parent_teardown_count: int = 0
    project_stock_mutations: int = 0
    events: list[str] = field(default_factory=list)
    delivery_state: DeliveryState = DeliveryState.NOT_STARTED
    serialized_bytes: bytes | None = None
    known_output_bytes: int | None = None
    transmission_offset: int = 0
    peer_acceptance: str = "UNKNOWN"
    generation: int = 1

    def allocate(self) -> bool:
        self.events.append("project-allocation")
        self.entry_local = True
        self.decoder_live = True
        return True

    def listener_created(self) -> None:
        if not self.entry_local:
            raise RuntimeError("allocate project child first")
        self.listener_open = True
        self.events.append("listener-created")

    def accept_socket(self) -> None:
        self.accepted_socket_open = True
        self.events.append("accepted-socket")

    def append_succeeded(self) -> None:
        if not self.entry_local:
            raise RuntimeError("project entry does not exist")
        self.entry_array_owned = True
        self.delivery_state = DeliveryState.PREPARED
        self.events.append("synthetic-response-insertion")

    def serialization_failed(self) -> None:
        if self.delivery_state is not DeliveryState.PREPARED:
            raise RuntimeError("serialization failure requires a prepared response")
        self.delivery_state = DeliveryState.SERIALIZATION_FAILED
        self.events.append("serialization-failed")
        self._discard_staged_response_graph()
        self._cleanup_child()

    def serialization_succeeded(self, payload: bytes) -> None:
        if self.delivery_state is not DeliveryState.PREPARED:
            raise RuntimeError("response must be prepared before serialization")
        if not isinstance(payload, bytes):
            raise TypeError("serialized payload must be bytes")
        self.serialized_bytes = payload
        self.delivery_state = DeliveryState.SERIALIZED_LOCAL
        self._release_serialized_graph()

    def transmission_started(self) -> None:
        if self.delivery_state is not DeliveryState.SERIALIZED_LOCAL or self.serialized_bytes is None:
            raise RuntimeError("cannot transmit before local serialization")
        self.delivery_state = DeliveryState.TRANSMISSION_STARTED
        self.known_output_bytes = 0
        self.transmission_offset = 0
        self.events.append("transmission-started")

    def transmission_failed(self, *, bytes_written: int | None) -> None:
        if self.delivery_state not in (DeliveryState.TRANSMISSION_STARTED,
                                       DeliveryState.DELIVERY_UNKNOWN):
            raise RuntimeError("transmission has not started")
        if bytes_written is not None:
            self._record_output_progress(bytes_written)
        self.known_output_bytes = self.transmission_offset
        no_output_is_known = bytes_written is not None and self.transmission_offset == 0
        self.delivery_state = (DeliveryState.SEND_FAILED_NO_OUTPUT
                               if no_output_is_known
                               else DeliveryState.DELIVERY_UNKNOWN)
        self.events.append("transmission-failed-no-output" if no_output_is_known
                           else "transmission-failed-delivery-unknown")

    def transport_completed(self) -> None:
        if self.delivery_state not in (DeliveryState.TRANSMISSION_STARTED,
                                       DeliveryState.DELIVERY_UNKNOWN):
            raise RuntimeError("transmission has not started")
        self.transmission_offset = len(self.serialized_bytes or b"")
        self.known_output_bytes = self.transmission_offset
        self.delivery_state = DeliveryState.TRANSPORT_COMPLETE
        self.events.append("local-transport-complete-peer-acceptance-unknown")

    def release_entry_local(self) -> None:
        if self.entry_local:
            self.entry_local = False
            self.events.append("local-entry-release")

    def _release_serialized_graph(self) -> None:
        if self.response_graph_live:
            self.response_graph_live = False
            self.graph_release_count += 1
            self.entry_array_owned = False
            self.events.append("synthetic-serialization-and-graph-release")

    def project_failure(self, phase: str, *, generation: int | None = None) -> None:
        """Rollback only project-owned resources; leave the parent untouched."""
        self.events.append(phase)
        if generation is not None and generation != self.generation:
            self.events.append("stale-generation-cleanup-ignored")
            return
        if self.delivery_state in (DeliveryState.NOT_STARTED, DeliveryState.PREPARED):
            self.delivery_state = DeliveryState.FAILED_BEFORE_SERIALIZATION
        self._discard_staged_response_graph()
        self._cleanup_child()

    def retryable_write(self, phase: str, *, bytes_written: int | None = None) -> None:
        """EAGAIN/partial-write modeled as pending delivery, not teardown."""
        if self.delivery_state is DeliveryState.SERIALIZED_LOCAL:
            if bytes_written is not None:
                self._validate_output_progress(bytes_written)
            self.transmission_started()
        if self.delivery_state not in (DeliveryState.TRANSMISSION_STARTED,
                                       DeliveryState.DELIVERY_UNKNOWN):
            self.events.append(phase)
            return
        if bytes_written is not None:
            self._validate_output_progress(bytes_written)
        self.events.append(phase)
        # Retryable backpressure is not terminal even when this attempt makes
        # zero progress. Keep the serialized payload and cumulative offset.
        if bytes_written is not None:
            self._record_output_progress(bytes_written)
        if self.transmission_offset:
            self.delivery_state = DeliveryState.DELIVERY_UNKNOWN
        else:
            self.delivery_state = DeliveryState.TRANSMISSION_STARTED

    def _record_output_progress(self, byte_count: int) -> None:
        self._validate_output_progress(byte_count)
        self.transmission_offset += byte_count
        self.known_output_bytes = self.transmission_offset

    def _validate_output_progress(self, byte_count: int) -> None:
        if byte_count < 0:
            raise ValueError("known output byte count cannot be negative")
        payload_length = len(self.serialized_bytes or b"")
        if self.transmission_offset + byte_count > payload_length:
            raise ValueError("known output exceeds serialized payload length")

    def _discard_staged_response_graph(self) -> None:
        if self.response_graph_live and self.entry_array_owned:
            # Synthetic rollback of an independently discardable candidate graph.
            self.response_graph_live = False
            self.graph_release_count += 1
            self.entry_array_owned = False

    def parent_connection_finalized(self) -> None:
        self.events.append("parent-connection-finalized")
        self.honda_parent_teardown()

    def honda_parent_teardown(self) -> None:
        """Explicit Honda-parent event; stock changes belong to Honda's side."""
        self.parent_teardown_count += 1
        self.events.append("honda-parent-session-teardown")
        self.type110_active = False
        self.audio_active = False
        self.center_screen_state = "honda-parent-torn-down"
        self._cleanup_child()

    def _cleanup_child(self) -> None:
        if self.listener_open:
            self.listener_open = False
            self.close_count += 1
        if self.accepted_socket_open:
            self.accepted_socket_open = False
            self.socket_close_count += 1
        if self.decoder_live:
            self.decoder_live = False
            self.decoder_release_count += 1
        self.entry_local = False
        self.entry_array_owned = False
