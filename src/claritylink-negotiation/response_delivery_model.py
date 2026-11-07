"""Synthetic child ownership and parent HTTP response delivery lifecycle model.

No Honda code is executed. Honda parent teardown effects are an explicit input
so tests can separate project cleanup from stock session behavior.
Type111 child sockets and the caller-owned HTTP response transport are separate.
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
    parent_session_torn_down: bool = False
    events: list[str] = field(default_factory=list)
    delivery_state: DeliveryState = DeliveryState.NOT_STARTED
    serialized_bytes: bytes | None = None
    known_output_bytes: int | None = None
    # If progress becomes unknown, this retains only the last confirmed lower bound.
    transmission_offset: int = 0
    write_progress_known: bool = True
    transmission_terminal: bool = False
    parent_connection_open: bool = True
    # TCP accept is modeled separately; protocol/application acceptance stays unknown.
    peer_acceptance: str = "UNKNOWN"
    type111_in_serialized_response: bool = False
    generation: int = 1

    def allocate(self) -> bool:
        if not self.parent_connection_open:
            raise RuntimeError("child allocation requires an open parent connection")
        if self.delivery_state is not DeliveryState.NOT_STARTED:
            raise RuntimeError("child allocation requires NOT_STARTED delivery state")
        if self.entry_local or self.decoder_live:
            raise RuntimeError("previous child resources are still live")
        self.generation += 1
        self.events.append("project-allocation")
        self.entry_local = True
        self.decoder_live = True
        return True

    def listener_created(self, *, generation: int) -> None:
        self._require_current_generation(generation)
        if (not self.entry_local or self.listener_open
                or self.delivery_state is not DeliveryState.NOT_STARTED):
            raise RuntimeError("allocate project child first")
        self.listener_open = True
        self.events.append("listener-created")

    def accept_socket(self, *, generation: int) -> None:
        self._require_current_generation(generation)
        if (self.delivery_state is not DeliveryState.TRANSPORT_COMPLETE or not self.listener_open
                or not self.type111_in_serialized_response or self.accepted_socket_open):
            raise RuntimeError("accept requires a completed parent response and open listener")
        self.accepted_socket_open = True
        self.events.append("accepted-socket")

    def append_succeeded(self, *, generation: int) -> None:
        self._require_current_generation(generation)
        if (self.delivery_state is not DeliveryState.NOT_STARTED or not self.entry_local
                or not self.listener_open):
            raise RuntimeError("response insertion requires an unprepared entry and ready listener")
        self.entry_array_owned = True
        self.response_graph_live = True
        self.delivery_state = DeliveryState.PREPARED
        self.events.append("synthetic-response-insertion")

    def serialization_failed(self, *, generation: int) -> None:
        self._require_current_generation(generation)
        if self.delivery_state not in (DeliveryState.NOT_STARTED, DeliveryState.PREPARED):
            raise RuntimeError("serialization failure requires a pending parent response")
        self.delivery_state = DeliveryState.SERIALIZATION_FAILED
        self.events.append("serialization-failed")
        self._discard_staged_response_graph()
        self._cleanup_child()

    def serialization_succeeded(self, payload: bytes, *, generation: int) -> None:
        self._require_current_generation(generation)
        if (self.delivery_state not in (DeliveryState.NOT_STARTED, DeliveryState.PREPARED)
                or not self.parent_connection_open):
            raise RuntimeError("parent response is not available for serialization")
        if not isinstance(payload, bytes):
            raise TypeError("serialized payload must be bytes")
        self.type111_in_serialized_response = self.entry_array_owned
        self.serialized_bytes = payload
        self.delivery_state = DeliveryState.SERIALIZED_LOCAL
        self._release_serialized_graph()
        if not self.type111_in_serialized_response:
            self._cleanup_child()

    def transmission_started(self, *, generation: int) -> None:
        self._require_current_generation(generation)
        if not self.parent_connection_open:
            raise RuntimeError("cannot transmit after parent connection finalization")
        if self.type111_in_serialized_response and not self.listener_open:
            raise RuntimeError("cannot transmit response after Type111 listener cleanup")
        if (self.delivery_state is not DeliveryState.SERIALIZED_LOCAL
                or self.serialized_bytes is None):
            raise RuntimeError("cannot transmit before local serialization")
        self.delivery_state = DeliveryState.TRANSMISSION_STARTED
        self.known_output_bytes = 0
        self.transmission_offset = 0
        self.write_progress_known = True
        self.transmission_terminal = False
        self.events.append("transmission-started")

    def transmission_failed(self, *, known_output_bytes: int | None,
                            generation: int) -> None:
        """Record this attempt's byte delta; the model field stores cumulative progress."""
        self._require_current_generation(generation)
        if self.delivery_state not in (DeliveryState.TRANSMISSION_STARTED,
                                       DeliveryState.DELIVERY_UNKNOWN):
            raise RuntimeError("transmission has not started")
        if self.transmission_terminal:
            raise RuntimeError("transmission progress is no longer writable")
        was_already_unknown = self.delivery_state is DeliveryState.DELIVERY_UNKNOWN
        progress_was_known = self.write_progress_known
        if known_output_bytes is not None and progress_was_known:
            self._record_output_progress(known_output_bytes)
        elif known_output_bytes is not None:
            raise RuntimeError("cannot account for output after write progress became unknown")
        else:
            self.write_progress_known = False
        self.known_output_bytes = (self.transmission_offset
                                   if self.write_progress_known else None)
        no_output_is_known = (not was_already_unknown and progress_was_known
                              and known_output_bytes is not None
                              and self.transmission_offset == 0)
        self.delivery_state = (DeliveryState.SEND_FAILED_NO_OUTPUT
                               if no_output_is_known
                               else DeliveryState.DELIVERY_UNKNOWN)
        self.transmission_terminal = True
        self.events.append("transmission-failed-no-output" if no_output_is_known
                           else "transmission-failed-delivery-unknown")
        self._cleanup_child()

    def transport_completed(self, *, generation: int) -> None:
        self._require_current_generation(generation)
        if self.delivery_state not in (DeliveryState.TRANSMISSION_STARTED,
                                       DeliveryState.DELIVERY_UNKNOWN):
            raise RuntimeError("transmission has not started")
        if self.transmission_terminal:
            raise RuntimeError("terminal transmission failure cannot complete")
        self.transmission_offset = len(self.serialized_bytes or b"")
        self.known_output_bytes = self.transmission_offset
        self.write_progress_known = True
        self.delivery_state = DeliveryState.TRANSPORT_COMPLETE
        self.events.append("local-transport-complete-peer-acceptance-unknown")

    def release_entry_local(self, *, generation: int) -> None:
        self._require_current_generation(generation)
        if self.entry_local:
            self.entry_local = False
            self.events.append("local-entry-release")

    def _release_serialized_graph(self) -> None:
        if self.response_graph_live and self.entry_array_owned:
            self.response_graph_live = False
            self.graph_release_count += 1
            self.entry_array_owned = False
            self.events.append("synthetic-serialization-and-graph-release")

    def project_failure(self, phase: str, *, generation: int) -> None:
        """Rollback project resources and fence an unsent response containing a dead port."""
        if type(generation) is not int or generation < 0:
            raise ValueError("cleanup generation must be a nonnegative integer")
        if generation < self.generation:
            self.events.append("stale-generation-cleanup-ignored")
            return
        if generation > self.generation:
            raise RuntimeError("cleanup generation is from the future")
        self.events.append(phase)
        child_resources_exist = (self.entry_local or self.entry_array_owned
                                 or self.listener_open or self.accepted_socket_open
                                 or self.decoder_live)
        if self.delivery_state is DeliveryState.PREPARED:
            self.delivery_state = DeliveryState.NOT_STARTED
        if child_resources_exist:
            self.generation += 1
        self._fence_type111_send_if_endpoint_closes()
        self._discard_staged_response_graph()
        self._cleanup_child()

    def retryable_write(self, phase: str, *, known_output_bytes: int | None = None,
                        generation: int) -> None:
        """Model a parent HTTP write; byte counts are deltas for this attempt."""
        self._require_current_generation(generation)
        if self.delivery_state is DeliveryState.SERIALIZED_LOCAL:
            if known_output_bytes is not None:
                self._validate_output_progress(known_output_bytes)
            self.transmission_started(generation=generation)
        if self.delivery_state not in (DeliveryState.TRANSMISSION_STARTED,
                                       DeliveryState.DELIVERY_UNKNOWN) or self.transmission_terminal:
            raise RuntimeError("retryable write requires an active transmission")
        if not self.write_progress_known:
            raise RuntimeError("cannot retry when write progress is unknown")
        if known_output_bytes is not None:
            self._validate_output_progress(known_output_bytes)
        self.events.append(phase)
        # Retryable backpressure is not terminal even when this attempt makes
        # zero progress. Keep the serialized payload and cumulative offset.
        if known_output_bytes is None:
            self.write_progress_known = False
            self.known_output_bytes = None
            self.delivery_state = DeliveryState.DELIVERY_UNKNOWN
            self.events.append("retryable-write-progress-unknown")
            return
        self._record_output_progress(known_output_bytes)
        if self.transmission_offset:
            self.delivery_state = DeliveryState.DELIVERY_UNKNOWN
        else:
            self.delivery_state = DeliveryState.TRANSMISSION_STARTED

    def _record_output_progress(self, byte_count: int) -> None:
        self._validate_output_progress(byte_count)
        self.transmission_offset += byte_count
        self.known_output_bytes = self.transmission_offset

    def _validate_output_progress(self, byte_count: int) -> None:
        if type(byte_count) is not int:
            raise TypeError("known output byte count must be an integer")
        if byte_count < 0:
            raise ValueError("known output byte count cannot be negative")
        payload_length = len(self.serialized_bytes or b"")
        if self.transmission_offset + byte_count > payload_length:
            raise ValueError("known output exceeds serialized payload length")

    def _require_current_generation(self, generation: int) -> None:
        if type(generation) is not int or generation < 0:
            raise ValueError("operation generation must be a nonnegative integer")
        if generation != self.generation:
            raise RuntimeError("stale child generation")

    def _fence_type111_send_if_endpoint_closes(self) -> None:
        if not self.type111_in_serialized_response:
            return
        if self.delivery_state is DeliveryState.SERIALIZED_LOCAL:
            self.delivery_state = DeliveryState.SEND_FAILED_NO_OUTPUT
            self.transmission_offset = 0
            self.known_output_bytes = 0
            self.write_progress_known = True
            self.transmission_terminal = True
        elif self.delivery_state in (DeliveryState.TRANSMISSION_STARTED,
                                     DeliveryState.DELIVERY_UNKNOWN):
            self.delivery_state = DeliveryState.DELIVERY_UNKNOWN
            self.known_output_bytes = None
            self.write_progress_known = False
            self.transmission_terminal = True

    def _discard_staged_response_graph(self) -> None:
        if self.response_graph_live and self.entry_array_owned:
            # Synthetic rollback of an independently discardable candidate graph.
            self.response_graph_live = False
            self.graph_release_count += 1
            self.entry_array_owned = False

    def parent_connection_finalized(self) -> None:
        if not self.parent_connection_open:
            self.events.append("duplicate-parent-connection-finalize-ignored")
            return
        self.parent_connection_open = False
        self.events.append("parent-connection-finalized")
        if self.delivery_state in (DeliveryState.NOT_STARTED, DeliveryState.PREPARED):
            self.delivery_state = DeliveryState.FAILED_BEFORE_SERIALIZATION
            self._discard_staged_response_graph()
        elif self.delivery_state in (DeliveryState.TRANSMISSION_STARTED,
                                     DeliveryState.DELIVERY_UNKNOWN):
            # Finalization cannot prove whether an in-flight write reached the peer.
            self.delivery_state = DeliveryState.DELIVERY_UNKNOWN
            self.known_output_bytes = None
            self.write_progress_known = False
            self.transmission_terminal = True
        elif self.delivery_state is DeliveryState.SERIALIZED_LOCAL:
            # Nothing was sent yet; keep serialization history distinct from a send failure.
            if self.type111_in_serialized_response:
                self._fence_type111_send_if_endpoint_closes()
            else:
                self.transmission_terminal = True
        if self.delivery_state is not DeliveryState.TRANSPORT_COMPLETE:
            self._cleanup_child()

    def honda_parent_teardown(self) -> None:
        """Model Honda session teardown independently from caller HTTP transport."""
        if self.parent_session_torn_down:
            self.events.append("duplicate-parent-teardown-ignored")
            return
        self.parent_session_torn_down = True
        self.parent_teardown_count += 1
        self.events.append("honda-parent-session-teardown")
        if self.delivery_state in (DeliveryState.NOT_STARTED, DeliveryState.PREPARED):
            self.delivery_state = DeliveryState.FAILED_BEFORE_SERIALIZATION
            self._discard_staged_response_graph()
        self._fence_type111_send_if_endpoint_closes()
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
