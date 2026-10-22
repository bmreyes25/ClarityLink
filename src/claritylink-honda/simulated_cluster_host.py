"""Deterministic simulated cluster display host (CL-FACTORY-02 / P1).

Original, offline, synthetic model of the *architectural behavior* of a cluster
display host with two logically independent presentation layers -- a main-content
layer and a top-most interrupt layer -- plus display-loss / validity-gated
rebuild. It is informed by the CL-FACTORY-01 static finding that the factory host
composes separate windows (bottom / main / interrupt, interrupt top-most) and
rebuilds with a validity check after the display link returns (reports 07/08),
but it reproduces NONE of the factory's proprietary identifiers, constants,
window parameters, or implementation. There is no Android WindowManager here, no
Honda IPC, no real Display 1 -- only a Python state machine.

Safety posture (do not relax):
  * A critical interrupt ALWAYS wins and never depends on custom main content
    rendering successfully. Activating an interrupt cannot fail.
  * Interrupt removal NEVER re-exposes stale main content; main content must be
    presented again after an interrupt clears.
  * Display loss withdraws content and destroys presentation ownership. A rebuild
    only happens when the display is validated, and it NEVER reuses stale stream
    authority: a strictly greater generation is required to present again.
  * Unknown / non-available state denies custom presentation (fail-closed).
This models our own behavior; it does NOT prove the real Honda safety system
behaves identically.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HostState(str, Enum):
    NOT_INITIALIZED = "NOT_INITIALIZED"
    DISPLAY_AVAILABLE = "DISPLAY_AVAILABLE"      # display present, no custom main content
    MAIN_CONTENT_ACTIVE = "MAIN_CONTENT_ACTIVE"  # custom main content owns the main layer
    INTERRUPT_ACTIVE = "INTERRUPT_ACTIVE"        # interrupt layer preempts main
    DISPLAY_LOST = "DISPLAY_LOST"
    RESTORING = "RESTORING"
    CLOSED = "CLOSED"


class PresentResult(str, Enum):
    PRESENTED = "PRESENTED"
    REPLACED = "REPLACED"                 # newer generation replaced prior main owner
    REJECTED_NO_DISPLAY = "REJECTED_NO_DISPLAY"
    REJECTED_INTERRUPTED = "REJECTED_INTERRUPTED"
    REJECTED_STALE_GENERATION = "REJECTED_STALE_GENERATION"
    REJECTED_CLOSED = "REJECTED_CLOSED"


@dataclass(frozen=True)
class MainOwner:
    session_id: int
    generation: int


@dataclass
class HostStats:
    displays_connected: int = 0
    main_presented: int = 0
    main_replaced: int = 0
    main_rejected: int = 0
    main_withdrawn: int = 0
    interrupts_activated: int = 0
    interrupts_cleared: int = 0
    display_losses: int = 0
    restores_completed: int = 0
    restores_refused: int = 0


class SimulatedClusterHost:
    """A single-display cluster host with independent main/interrupt layers."""

    def __init__(self) -> None:
        self._state = HostState.NOT_INITIALIZED
        self._main_owner: MainOwner | None = None
        self._main_content: Any = None
        # Lifetime-monotonic: a main generation is never reusable, so stale
        # authority cannot be resurrected after an interrupt or a display rebuild.
        self._gen_high_water = 0
        # The interrupt layer is independent of main: this flag is tracked
        # separately and does not destroy the (conceptual) main layer object.
        self._interrupt_active = False
        self.stats = HostStats()

    # ---- read-only ----
    @property
    def state(self) -> HostState:
        return self._state

    @property
    def main_owner(self) -> MainOwner | None:
        return self._main_owner

    @property
    def main_content(self) -> Any:
        return self._main_content

    @property
    def interrupt_active(self) -> bool:
        return self._interrupt_active

    @property
    def display_available(self) -> bool:
        return self._state in (
            HostState.DISPLAY_AVAILABLE, HostState.MAIN_CONTENT_ACTIVE, HostState.INTERRUPT_ACTIVE)

    def main_presentable(self) -> bool:
        """Whether custom main content is currently eligible to be shown.
        Fail-closed: only in MAIN_CONTENT_ACTIVE with a live owner and no
        interrupt in effect."""
        return (self._state is HostState.MAIN_CONTENT_ACTIVE
                and self._main_owner is not None
                and not self._interrupt_active)

    # ---- display lifecycle ----
    def connect_display(self) -> None:
        if self._state is HostState.CLOSED:
            raise RuntimeError("host is closed")
        if self._state in (HostState.NOT_INITIALIZED, HostState.DISPLAY_LOST, HostState.RESTORING):
            self._state = HostState.DISPLAY_AVAILABLE
            self._main_owner = None
            self._main_content = None
            self._interrupt_active = False
            self.stats.displays_connected += 1

    def lose_display(self) -> None:
        """Display link dropped: immediate content withdrawal + ownership destroyed."""
        if self._state is HostState.CLOSED:
            return
        self.stats.display_losses += 1
        self._main_owner = None
        self._main_content = None
        self._interrupt_active = False
        self._state = HostState.DISPLAY_LOST

    def begin_restore(self) -> None:
        if self._state is HostState.DISPLAY_LOST:
            self._state = HostState.RESTORING

    def complete_restore(self, *, display_valid: bool) -> bool:
        """Validity-gated rebuild. Only a valid display rebuilds the host; an
        invalid one stays lost (fail-closed). Never restores stale content: a new
        presentation generation is required afterward."""
        if self._state is not HostState.RESTORING:
            return False
        if not display_valid:
            self.stats.restores_refused += 1
            self._state = HostState.DISPLAY_LOST
            return False
        self.stats.restores_completed += 1
        self._state = HostState.DISPLAY_AVAILABLE
        self._main_owner = None
        self._main_content = None
        self._interrupt_active = False
        return True

    def close(self) -> None:
        self._state = HostState.CLOSED
        self._main_owner = None
        self._main_content = None
        self._interrupt_active = False

    # ---- main-content layer ----
    def present_main(self, *, session_id: int, generation: int, content: Any) -> PresentResult:
        """Present or replace custom main content. Requires an available display,
        no active interrupt, and a strictly-monotonic generation (lifetime)."""
        if self._state is HostState.CLOSED:
            return PresentResult.REJECTED_CLOSED
        if not self.display_available:
            self.stats.main_rejected += 1
            return PresentResult.REJECTED_NO_DISPLAY
        if self._interrupt_active or self._state is HostState.INTERRUPT_ACTIVE:
            self.stats.main_rejected += 1
            return PresentResult.REJECTED_INTERRUPTED
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
            raise ValueError("generation must be a positive int")
        if isinstance(session_id, bool) or not isinstance(session_id, int) or session_id < 1:
            raise ValueError("session_id must be a positive int")
        if generation < self._gen_high_water:
            self.stats.main_rejected += 1
            return PresentResult.REJECTED_STALE_GENERATION
        if generation == self._gen_high_water:
            # A generation already used this lifetime may only be *refreshed* by
            # the same live owner. Once the owner is cleared (teardown, interrupt,
            # display rebuild) that generation is spent and can never be reused --
            # this is the anti-stale-authority guard. Cross-session reuse at the
            # same generation is also refused.
            same_live_owner = (self._main_owner is not None
                               and self._main_owner.generation == generation
                               and self._main_owner.session_id == session_id)
            if not same_live_owner:
                self.stats.main_rejected += 1
                return PresentResult.REJECTED_STALE_GENERATION
        replaced = self._main_owner is not None and generation > self._main_owner.generation
        self._main_owner = MainOwner(session_id=session_id, generation=generation)
        self._main_content = content
        self._gen_high_water = max(self._gen_high_water, generation)
        self._state = HostState.MAIN_CONTENT_ACTIVE
        if replaced:
            self.stats.main_replaced += 1
            return PresentResult.REPLACED
        self.stats.main_presented += 1
        return PresentResult.PRESENTED

    def withdraw_main(self) -> None:
        """Remove custom main content (safe direction; always allowed)."""
        if self._main_owner is not None or self._main_content is not None:
            self.stats.main_withdrawn += 1
        self._main_owner = None
        self._main_content = None
        if self._state is HostState.MAIN_CONTENT_ACTIVE:
            self._state = HostState.DISPLAY_AVAILABLE

    def clear_host(self) -> None:
        """Clear all custom content but keep the display connected."""
        self.withdraw_main()
        self._interrupt_active = False
        if self.display_available:
            self._state = HostState.DISPLAY_AVAILABLE

    # ---- interrupt layer (independent, always wins) ----
    def activate_interrupt(self) -> None:
        """A critical interrupt preempts custom main content immediately. This can
        never fail and never depends on main content rendering. Main content is
        withdrawn so clearing the interrupt cannot re-expose stale content."""
        if self._state is HostState.CLOSED:
            return
        if not self._interrupt_active:
            self.stats.interrupts_activated += 1
        self._interrupt_active = True
        # withdraw main content (do not keep it behind the interrupt)
        self._main_owner = None
        self._main_content = None
        if self.display_available or self._state is HostState.MAIN_CONTENT_ACTIVE:
            self._state = HostState.INTERRUPT_ACTIVE

    def clear_interrupt(self) -> None:
        """Interrupt ended. Returns to an available display with NO main content;
        content must be presented again (never auto-restored)."""
        if self._state is HostState.CLOSED:
            return
        if self._interrupt_active:
            self.stats.interrupts_cleared += 1
        self._interrupt_active = False
        if self._state is HostState.INTERRUPT_ACTIVE:
            self._state = HostState.DISPLAY_AVAILABLE
