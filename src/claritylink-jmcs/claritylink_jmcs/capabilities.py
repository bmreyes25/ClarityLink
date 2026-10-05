"""Evidence-labeled /info laboratory profile, not a Honda advertisement."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SecondaryDisplayCapability:
    width: int = 800
    height: int = 480
    fps: int = 30
    enabled: bool = True

    def __post_init__(self) -> None:
        if not 1 <= self.width <= 4096 or not 1 <= self.height <= 4096 or not 1 <= self.fps <= 120:
            raise ValueError("invalid_lab_display_geometry")


def lab_info(capability: SecondaryDisplayCapability) -> dict[str, object]:
    """A controlled host-client fixture, not a complete iPhone /info payload."""
    displays: list[dict[str, object]] = [{"streamType": 110, "widthPixels": 800, "heightPixels": 480}]
    if capability.enabled:
        displays.append({"streamType": 111, "widthPixels": capability.width,
                         "heightPixels": capability.height, "maxFPS": capability.fps})
    return {"evidence": "CURRENT_IOS_LAB_TOPOLOGY_WITH_SYNTHETIC_GEOMETRY",
            "altScreen": capability.enabled, "displays": displays}
