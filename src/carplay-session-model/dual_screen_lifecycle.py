"""Offline generation and lease ownership for the synthetic second screen.

Lifecycle operations are bound to one explicit project generation. Type110 is
held as an unchanged sibling reference and is never a registry-owned resource.
"""

from __future__ import annotations

from time import monotonic
from typing import Callable

from legacy_dual_screen_twin import (
    DuplicateStreamConnectionID,
    LegacyDualScreenTwin,
    LegacyScreenInputError,
    LegacyScreenSession,
    ScreenRole,
)
from project_lifecycle import (
    ChildPhase,
    LeaseTicket,
    PreparedChildTransaction,
    ProjectSessionKey,
    ProjectSessionRegistry,
)
from receiver_core import ReceiverEvent

# Semantic alias for call sites that handle only Type111 lifecycle tickets.
Type111LeaseTicket = LeaseTicket


class _OwnedType111Screen:
    """Registry resource handle that closes only its captured screen object."""

    def __init__(self, twin: LegacyDualScreenTwin, screen: LegacyScreenSession) -> None:
        self._twin = twin
        self._screen = screen

    def close(self) -> None:
        self._twin.destroy_screen(
            ScreenRole.TYPE111_SYNTHETIC, expected_screen=self._screen
        )


class Type111Generation:
    """Handle to one immutable identity and its project-owned screen state."""

    role = ScreenRole.TYPE111_SYNTHETIC

    def __init__(
        self,
        owner: "DualScreenLifecycleTwin",
        key: ProjectSessionKey,
        screen: LegacyScreenSession,
        transaction: PreparedChildTransaction,
    ) -> None:
        self._owner = owner
        self.key = key
        self._screen = screen
        self._transaction = transaction

    @property
    def generation(self) -> int:
        return self.key.generation

    @property
    def phase(self) -> ChildPhase:
        child = self._owner._registry.child(self.key)
        return child.phase if child is not None else ChildPhase.STOPPED

    def activate(self) -> bool:
        if not self._owner._is_current(self) or self.phase is not ChildPhase.PREPARED:
            return False
        try:
            self._transaction.mark_response_ready()
            return self._transaction.commit_after_response_commit()
        except RuntimeError:
            return False

    def feed(self, data: bytes | bytearray | memoryview) -> list[ReceiverEvent]:
        if not self._owner._is_current(self) or self.phase is not ChildPhase.ACTIVE:
            raise RuntimeError("Type111 generation is not active")
        try:
            return self._screen.feed(data)
        except LegacyScreenInputError:
            self.fail()
            raise

    def renew(self) -> bool:
        if not self._owner._is_current(self):
            return False
        return self._owner._registry.renew_lease(self.key)

    def lease_ticket(self) -> Type111LeaseTicket | None:
        if not self._owner._is_current(self):
            return None
        return self._owner._registry.lease_ticket(self.key)

    def teardown(self) -> bool:
        return self._owner._stop_exact(self, "explicit Type111 teardown")

    def fail(self) -> bool:
        return self._owner._stop_exact(self, "synthetic Type111 generation failure")

    def __repr__(self) -> str:
        return f"Type111Generation(generation={self.generation}, phase={self.phase.name})"


class DualScreenLifecycleTwin:
    """Compose the 43Q-A screen twin with the existing project generation registry."""

    def __init__(
        self,
        screen_twin: LegacyDualScreenTwin,
        *,
        lease_seconds: float = 300.0,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if ScreenRole.TYPE110 not in screen_twin.roles:
            raise ValueError("an active Type110 screen is required")
        if ScreenRole.TYPE111_SYNTHETIC in screen_twin.roles:
            raise ValueError("Type111 state must be created through this lifecycle owner")
        self._screen_twin = screen_twin
        self._type110 = screen_twin.screen(ScreenRole.TYPE110)
        self._registry_identity = (object(), ScreenRole.TYPE111_SYNTHETIC.value)
        self._registry = ProjectSessionRegistry(lease_seconds=lease_seconds, clock=clock)
        self._current: Type111Generation | None = None
        self._parent_destroyed = False
        self.type110_generation = 1

    @property
    def type110(self) -> LegacyScreenSession:
        return self._type110

    @property
    def current_type111(self) -> Type111Generation | None:
        current = self._current
        if current is None or current.phase is ChildPhase.STOPPED:
            return None
        return current

    @property
    def parent_destroyed(self) -> bool:
        return self._parent_destroyed

    def create_type111(self, stream_connection_id: int) -> Type111Generation:
        if self._parent_destroyed:
            raise RuntimeError("parent session is destroyed")
        if (
            isinstance(stream_connection_id, bool)
            or not isinstance(stream_connection_id, int)
            or not 1 <= stream_connection_id < (1 << 64)
        ):
            raise ValueError("stream_connection_id must be a nonzero uint64")
        current = self.current_type111
        if stream_connection_id == self._type110.stream_connection_id:
            raise DuplicateStreamConnectionID(
                (ScreenRole.TYPE110, ScreenRole.TYPE111_SYNTHETIC)
            )
        if current is not None and stream_connection_id == current._screen.stream_connection_id:
            raise ValueError("a replacement Type111 generation requires a fresh stream ID")
        key = self._registry.next_key(self._registry_identity)
        self._current = None
        screen = self._screen_twin.add_screen(
            ScreenRole.TYPE111_SYNTHETIC, stream_connection_id
        )
        resource = _OwnedType111Screen(self._screen_twin, screen)
        try:
            transaction = self._registry.prepare_child(key, lambda: (resource,))
        except Exception:
            # prepare_child normally owns rollback; this exact close is
            # idempotent and covers failures before ownership was transferred.
            resource.close()
            raise
        generation = Type111Generation(self, key, screen, transaction)
        self._current = generation
        return generation

    def reap_expired(self, *, now: float | None = None) -> tuple[int, ...]:
        reaped = self._registry.reap_expired(now=now)
        if self._current is not None and self._current.key in reaped:
            self._current = None
        return tuple(key.generation for key in reaped)

    def reap_lease(self, ticket: Type111LeaseTicket, *, now: float | None = None) -> bool:
        if ticket.key.session_identity != self._registry_identity:
            return False
        reaped = self._registry.reap_lease(ticket, now=now)
        if reaped and self._current is not None and self._current.key == ticket.key:
            self._current = None
        return reaped

    def destroy_parent(self) -> bool:
        if self._parent_destroyed:
            return False
        self._parent_destroyed = True
        current = self._current
        if current is not None:
            self._stop_exact(current, "parent session destroyed")
        self._screen_twin.destroy_screen(ScreenRole.TYPE111_SYNTHETIC)
        self._screen_twin.destroy_screen(
            ScreenRole.TYPE110, expected_screen=self._type110
        )
        self._current = None
        return True

    def _is_current(self, generation: Type111Generation) -> bool:
        return not self._parent_destroyed and self._current is generation

    def _stop_exact(self, generation: Type111Generation, reason: str) -> bool:
        stopped = self._registry.stop_child(generation.key, reason)
        if stopped and self._current is generation:
            self._current = None
        return stopped
