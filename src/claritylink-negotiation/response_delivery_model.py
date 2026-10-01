"""Synthetic-only project child ownership and HTTP delivery lifecycle model.

No Honda code is executed. Honda parent teardown effects are an explicit input
so tests can separate project cleanup from stock session behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field


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
        self.events.append("synthetic-response-insertion")

    def release_entry_local(self) -> None:
        if self.entry_local:
            self.entry_local = False
            self.events.append("local-entry-release")

    def serialized(self) -> None:
        if self.response_graph_live:
            self.response_graph_live = False
            self.graph_release_count += 1
            self.entry_array_owned = False
            self.events.append("synthetic-serialization-and-graph-release")

    def project_failure(self, phase: str) -> None:
        """Rollback only project-owned resources; leave the parent untouched."""
        self.events.append(phase)
        if self.response_graph_live and self.entry_array_owned:
            # Synthetic rollback of an independently discardable candidate graph.
            self.response_graph_live = False
            self.graph_release_count += 1
            self.entry_array_owned = False
        self._cleanup_child()

    def retryable_write(self, phase: str) -> None:
        """EAGAIN/partial-write modeled as pending delivery, not teardown."""
        self.events.append(phase)

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
