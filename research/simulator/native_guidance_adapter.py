"""Offline model of Honda Hack's observed Waze -> external-display handler path.

This module does not import ADB or send broadcasts. Values mirror the decompiled
C0288xd / C0170b branch used with enable_custom_meter=false. It is a renderer
contract model, not evidence that iPhone CarPlay supplies these fields.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Guidance:
    maneuver: str
    street: str
    distance_meters: int | None


# turnSide, event, angle, matching the Android Waze hook's native-view branch.
MANEUVERS = {
    "start": (3, 1, -1),
    "left": (1, 4, -1),
    "right": (2, 4, -1),
    "straight": (3, 14, -1),
}


def render_events(guidance: Guidance) -> list[dict]:
    """Return factory external-display handler events, or refuse uncertain data."""
    if guidance.maneuver not in MANEUVERS:
        raise ValueError("Unsupported maneuver")
    if not isinstance(guidance.street, str) or not 1 <= len(guidance.street.strip()) <= 70:
        raise ValueError("Missing or overlong street")
    if (not isinstance(guidance.distance_meters, int) or
            isinstance(guidance.distance_meters, bool) or
            not 0 <= guidance.distance_meters <= 100000):
        raise ValueError("Verified distance in meters required; no stale distance may be reused")
    turn_side, event, angle = MANEUVERS[guidance.maneuver]
    return [
        {"handler": 5601, "status": 1},
        {"handler": 5602, "turnSide": turn_side, "event": event,
         "angle": angle, "street": guidance.street.strip()},
        {"handler": 5603, "distanceMeters": guidance.distance_meters},
    ]


def stop_events() -> list[dict]:
    return [{"handler": 5601, "status": 2}]


def expected_factory_view(guidance: Guidance) -> dict:
    """Static UI prediction from TurnByTurnController/ContentsTurnByTurnBase."""
    render_events(guidance)
    if guidance.distance_meters > 1000:
        view_id = "1000Over"
    else:
        view_id = 61441 if guidance.maneuver == "start" else 61442
    return {"viewId": view_id, "streetVisible": False}
