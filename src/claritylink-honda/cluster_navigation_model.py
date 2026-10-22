"""Structured cluster-navigation state model (CL-FACTORY-01 / G-04).

Original, offline, synthetic-only model of a structured turn-by-turn navigation
presentation for an instrument-cluster area. It uses **generic, public-safe data
contracts** (no proprietary identifiers) and does NOT implement any Honda IPC
client, Binder call, host injection, or real cluster output.

It is informed by the factory research finding that the cluster consumes
*structured* turn-by-turn data (maneuver/distance/road-name), not a video stream
(reports 06/08). It coordinates with the transport `frame_gate` freshness rules
(strictly increasing sequence per generation) and the honda
`factory_integration_contract` (presentation stays inert / fail-closed).

Safety posture (do not relax):
  * A factory warning/interrupt always wins: ``interrupt()`` withdraws custom
    content immediately. The model does NOT claim to *enforce* real factory
    warning priority -- only that it yields.
  * Unknown/lost host state fails closed to not-visible.
  * ``presentable_to_factory()`` is always False here; real presentation is gated
    by the fail-closed contract, which this campaign keeps inert.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ManeuverType(str, Enum):
    STRAIGHT = "STRAIGHT"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    SLIGHT_LEFT = "SLIGHT_LEFT"
    SLIGHT_RIGHT = "SLIGHT_RIGHT"
    SHARP_LEFT = "SHARP_LEFT"
    SHARP_RIGHT = "SHARP_RIGHT"
    UTURN = "UTURN"
    ROUNDABOUT = "ROUNDABOUT"
    MERGE = "MERGE"
    EXIT = "EXIT"
    ARRIVE = "ARRIVE"
    UNKNOWN = "UNKNOWN"


class DistanceUnit(str, Enum):
    METERS = "METERS"
    KILOMETERS = "KILOMETERS"
    FEET = "FEET"
    MILES = "MILES"


class NavState(str, Enum):
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    INTERRUPTED = "INTERRUPTED"   # a factory warning/interrupt is showing; custom content withdrawn
    WITHDRAWN = "WITHDRAWN"       # custom content withdrawn (source death / explicit)
    HOST_LOST = "HOST_LOST"       # display host disconnected
    RECOVERING = "RECOVERING"


class UpdateStatus(str, Enum):
    APPLIED = "APPLIED"
    STALE_GENERATION = "STALE_GENERATION"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    DUPLICATE = "DUPLICATE"
    NOT_ACTIVE = "NOT_ACTIVE"
    MALFORMED = "MALFORMED"


class MalformedUpdate(ValueError):
    pass


@dataclass(frozen=True)
class NavigationUpdate:
    """One structured guidance update. ``maneuver`` accepts an unknown string and
    maps it to ManeuverType.UNKNOWN; numeric/text fields are validated."""
    generation: int
    sequence: int
    maneuver: ManeuverType
    distance: int
    unit: DistanceUnit
    road_name: str = ""

    @staticmethod
    def build(generation, sequence, maneuver, distance, unit, road_name=""):
        for name, v in (("generation", generation), ("sequence", sequence), ("distance", distance)):
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise MalformedUpdate(f"{name} must be a non-negative int")
        try:
            mt = maneuver if isinstance(maneuver, ManeuverType) else ManeuverType(str(maneuver))
        except ValueError:
            mt = ManeuverType.UNKNOWN
        try:
            du = unit if isinstance(unit, DistanceUnit) else DistanceUnit(str(unit))
        except ValueError:
            raise MalformedUpdate("unknown distance unit")
        if not isinstance(road_name, str) or len(road_name) > 256:
            raise MalformedUpdate("road_name must be a str <= 256 chars")
        return NavigationUpdate(generation, sequence, mt, distance, du, road_name)


class ClusterNavigationModel:
    def __init__(self) -> None:
        self._state = NavState.INACTIVE
        self._session_id: int | None = None
        self._generation: int | None = None
        self._last_seq: int | None = None
        self._current: NavigationUpdate | None = None
        self._visible = False

    # ---- read-only ----
    @property
    def state(self) -> NavState:
        return self._state

    @property
    def current(self) -> NavigationUpdate | None:
        return self._current

    @property
    def visible(self) -> bool:
        # fail closed: only visible while genuinely ACTIVE
        return self._visible and self._state is NavState.ACTIVE

    def presentable_to_factory(self) -> bool:
        return False  # real presentation stays inert (see factory_integration_contract)

    # ---- session lifecycle ----
    def start_session(self, session_id: int, generation: int) -> None:
        if isinstance(session_id, bool) or not isinstance(session_id, int) or session_id <= 0:
            raise MalformedUpdate("session_id must be a positive int")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
            raise MalformedUpdate("generation must be a positive int")
        if self._generation is not None and generation <= self._generation:
            raise MalformedUpdate("generation must strictly increase")
        self._session_id = session_id
        self._generation = generation
        self._last_seq = None
        self._current = None
        self._state = NavState.ACTIVE
        self._visible = True

    def apply_update(self, update: NavigationUpdate) -> UpdateStatus:
        if not isinstance(update, NavigationUpdate):
            return UpdateStatus.MALFORMED
        if self._state is not NavState.ACTIVE or self._generation is None:
            return UpdateStatus.NOT_ACTIVE
        if update.generation < self._generation:
            return UpdateStatus.STALE_GENERATION
        if update.generation > self._generation:
            return UpdateStatus.NOT_ACTIVE  # fail-closed: a newer generation needs start_session
        if self._last_seq is not None:
            if update.sequence == self._last_seq:
                return UpdateStatus.DUPLICATE
            if update.sequence < self._last_seq:
                return UpdateStatus.OUT_OF_ORDER
        self._last_seq = update.sequence
        self._current = update
        return UpdateStatus.APPLIED

    def set_visible(self, visible: bool) -> None:
        if self._state is NavState.ACTIVE:
            self._visible = bool(visible)

    # ---- interrupts / warnings (fail-safe: always yield) ----
    def interrupt(self) -> None:
        """A factory warning/interrupt is showing: withdraw custom content."""
        self._visible = False
        if self._state in (NavState.ACTIVE, NavState.INACTIVE):
            self._state = NavState.INTERRUPTED

    def clear_interrupt(self) -> None:
        """Interrupt ended. Resume only if a valid session still exists."""
        if self._state is NavState.INTERRUPTED:
            if self._session_id is not None and self._generation is not None:
                self._state = NavState.ACTIVE
                self._visible = True
            else:
                self._state = NavState.INACTIVE

    # ---- death / host / recovery / restore ----
    def on_source_death(self) -> None:
        self._visible = False
        self._state = NavState.WITHDRAWN
        self._current = None

    def on_host_lost(self) -> None:
        self._visible = False
        self._state = NavState.HOST_LOST
        self._current = None

    def begin_recovery(self) -> None:
        if self._state is NavState.HOST_LOST:
            self._state = NavState.RECOVERING

    def restore_factory(self) -> None:
        """Return to the stock/default: inactive, not visible, no custom content."""
        self._state = NavState.INACTIVE
        self._session_id = None
        self._generation = None
        self._last_seq = None
        self._current = None
        self._visible = False

    def reset(self) -> None:
        self.restore_factory()
