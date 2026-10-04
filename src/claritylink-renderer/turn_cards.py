"""R4B host-only turn-card state model. No transport or display backend."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping


WIDTH = 800
HEIGHT = 480
FRESH_SECONDS = 5
LOST_SECONDS = 30
MAX_STREET_CHARS = 30
MAX_SECONDARY_CHARS = 42
EVIDENCE_LABEL = "MODEL_ONLY / SYNTHETIC - NOT FOR DRIVING"


class ManeuverKind(str, Enum):
    STRAIGHT = "straight"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    SLIGHT_LEFT = "slight_left"
    SLIGHT_RIGHT = "slight_right"
    SHARP_LEFT = "sharp_left"
    SHARP_RIGHT = "sharp_right"
    MERGE = "merge"
    EXIT = "exit"
    U_TURN = "u_turn"
    ROUNDABOUT = "roundabout"
    ARRIVE = "arrive"
    UNKNOWN = "unknown"


class RouteState(str, Enum):
    NOT_STARTED = "not_started"
    ACTIVE = "active"
    REROUTING = "rerouting"
    ARRIVED = "arrived"
    STALE = "stale"
    LOST = "lost"
    ERROR = "error"


class WarningState(str, Enum):
    NONE = "none"
    NOT_STARTED = "not_started"
    REROUTING = "rerouting"
    ARRIVED = "arrived"
    STALE = "stale"
    LOST = "lost"
    ERROR = "error"
    UNKNOWN_MANEUVER = "unknown_maneuver"
    UNTRUSTED_SOURCE = "untrusted_source"
    CLEARED = "cleared"


class RendererState(str, Enum):
    GUIDANCE = "guidance"
    WARNING = "warning"
    IDLE = "idle"


class ColorMode(str, Enum):
    DAY = "day"
    NIGHT = "night"


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    def inside_canvas(self) -> bool:
        return 0 <= self.x and 0 <= self.y and self.width > 0 and self.height > 0 and self.x + self.width <= WIDTH and self.y + self.height <= HEIGHT


LAYOUT = {
    "primary_maneuver": Rect(40, 92, 180, 150),
    "distance": Rect(240, 100, 520, 100),
    "street": Rect(40, 245, 720, 60),
    "secondary_instruction": Rect(40, 315, 720, 40),
    "eta_progress": Rect(40, 370, 720, 42),
    "warning_banner": Rect(24, 20, 752, 60),
    "debug_evidence_label": Rect(24, 432, 752, 30),
}


def _nonnegative_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value < float("inf"):
        raise ValueError(f"{label} must be a finite nonnegative number")
    return float(value)


def _text(value: Any, label: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or (not value.strip() and not optional):
        raise ValueError(f"{label} must be text")
    if value is None:
        return None
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"{label} contains a control character")
    clean = " ".join(value.split())
    return clean or None


@dataclass(frozen=True)
class RouteStep:
    maneuver: ManeuverKind
    distance_remaining_m: float
    street_name: str | None = None
    lane_hint: str | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "RouteStep":
        if not isinstance(data, Mapping):
            raise ValueError("step must be an object")
        try:
            maneuver = ManeuverKind(data["maneuver"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("invalid maneuver kind") from exc
        return cls(
            maneuver=maneuver,
            distance_remaining_m=_nonnegative_number(data.get("distance_remaining_m"), "distance_remaining_m"),
            street_name=_text(data.get("street_name"), "street_name", optional=True),
            lane_hint=_text(data.get("lane_hint"), "lane_hint", optional=True),
        )


@dataclass(frozen=True)
class Route:
    route_id: str
    generation: int
    state: RouteState
    steps: tuple[RouteStep, ...]
    current_index: int
    updated_at_s: float
    eta_minutes: float | None = None
    source_trusted: bool = True  # Synthetic fixture input; no authentication implementation.

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Route":
        if not isinstance(data, Mapping):
            raise ValueError("route must be an object")
        route_id = _text(data.get("route_id"), "route_id")
        generation = data.get("generation")
        index = data.get("current_index")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
            raise ValueError("generation must be a nonnegative integer")
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            raise ValueError("current_index must be a nonnegative integer")
        try:
            state = RouteState(data["state"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("invalid route state") from exc
        raw_steps = data.get("steps")
        if not isinstance(raw_steps, list):
            raise ValueError("steps must be an array")
        steps = tuple(RouteStep.from_mapping(step) for step in raw_steps)
        if state == RouteState.ACTIVE and (not steps or index >= len(steps)):
            raise ValueError("active route needs a current step")
        if steps and index >= len(steps):
            raise ValueError("current_index exceeds steps")
        eta = data.get("eta_minutes")
        if eta is not None:
            eta = _nonnegative_number(eta, "eta_minutes")
        trusted = data.get("source_trusted", True)
        if not isinstance(trusted, bool):
            raise ValueError("source_trusted must be boolean")
        return cls(route_id or "", generation, state, steps, index,
                   _nonnegative_number(data.get("updated_at_s"), "updated_at_s"), eta, trusted)


def _shorten(value: str | None, limit: int, fallback: str) -> str:
    if not value:
        return fallback
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."


@dataclass(frozen=True)
class TurnCard:
    renderer_state: RendererState
    warning: WarningState
    warning_text: str
    maneuver: str | None
    next_maneuver: str | None
    distance_text: str | None
    street_text: str | None
    secondary_text: str | None
    eta_text: str | None
    progress_text: str | None
    mode: ColorMode
    route_generation: int | None
    evidence_label: str = EVIDENCE_LABEL

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["layout"] = {name: asdict(rect) for name, rect in LAYOUT.items()}
        result["canvas"] = {"width": WIDTH, "height": HEIGHT}
        return result


def _warning(warning: WarningState, message: str, mode: ColorMode, generation: int | None = None) -> TurnCard:
    return TurnCard(RendererState.IDLE if warning in (WarningState.CLEARED, WarningState.NOT_STARTED) else RendererState.WARNING,
                    warning, message, None, None, None, None, None, None, None, mode, generation)


def render_card(route: Route | None, now_s: float, mode: ColorMode = ColorMode.DAY, *, manual_clear: bool = False) -> TurnCard:
    """Pure projection. Warning states suppress maneuver data, even when old steps exist."""
    _nonnegative_number(now_s, "now_s")
    if not isinstance(mode, ColorMode):
        raise ValueError("mode must be day or night")
    if manual_clear:
        return _warning(WarningState.CLEARED, "GUIDANCE CLEARED", mode)
    if route is not None and (not isinstance(route, Route) or not isinstance(route.state, RouteState)):
        return _warning(WarningState.ERROR, "GUIDANCE UNAVAILABLE", mode)
    if route is None or route.state == RouteState.NOT_STARTED:
        return _warning(WarningState.NOT_STARTED, "NO ROUTE", mode)
    generation = route.generation
    if not route.source_trusted:
        return _warning(WarningState.UNTRUSTED_SOURCE, "ROUTE SOURCE UNVERIFIED", mode, generation)
    if now_s < route.updated_at_s:
        return _warning(WarningState.ERROR, "ROUTE TIME INVALID", mode, generation)
    if route.state == RouteState.ERROR:
        return _warning(WarningState.ERROR, "GUIDANCE UNAVAILABLE", mode, generation)
    if route.state == RouteState.LOST:
        return _warning(WarningState.LOST, "ROUTE LOST", mode, generation)
    if route.state == RouteState.STALE:
        return _warning(WarningState.STALE, "ROUTE UPDATE STALE", mode, generation)
    if route.state == RouteState.ARRIVED:
        return _warning(WarningState.ARRIVED, "DESTINATION REACHED", mode, generation)
    if route.state == RouteState.REROUTING:
        return _warning(WarningState.REROUTING, "REROUTING", mode, generation)
    age = now_s - route.updated_at_s
    if age > LOST_SECONDS:
        return _warning(WarningState.LOST, "ROUTE LOST", mode, generation)
    if age > FRESH_SECONDS:
        return _warning(WarningState.STALE, "ROUTE UPDATE STALE", mode, generation)
    if route.current_index >= len(route.steps) or not route.steps:
        return _warning(WarningState.ERROR, "GUIDANCE UNAVAILABLE", mode, generation)
    step = route.steps[route.current_index]
    if not isinstance(step.maneuver, ManeuverKind) or step.maneuver == ManeuverKind.UNKNOWN:
        return _warning(WarningState.UNKNOWN_MANEUVER, "MANEUVER UNKNOWN", mode, generation)
    if not 0 <= step.distance_remaining_m < float("inf"):
        return _warning(WarningState.ERROR, "GUIDANCE UNAVAILABLE", mode, generation)
    next_step = route.steps[route.current_index + 1] if route.current_index + 1 < len(route.steps) else None
    next_kind = next_step.maneuver.value if next_step and next_step.maneuver != ManeuverKind.UNKNOWN else None
    distance = f"{round(step.distance_remaining_m):,} m"
    street = _shorten(step.street_name, MAX_STREET_CHARS, "ROAD NAME UNAVAILABLE")
    secondary = _shorten(step.lane_hint, MAX_SECONDARY_CHARS, f"NEXT: {next_kind.upper().replace('_', ' ') if next_kind else 'NONE'}")
    eta = f"{round(route.eta_minutes)} min remaining" if route.eta_minutes is not None else None
    progress = f"Step {route.current_index + 1} of {len(route.steps)}"
    return TurnCard(RendererState.GUIDANCE, WarningState.NONE, "", step.maneuver.value,
                    next_kind, distance, street, secondary, eta, progress, mode, generation)
