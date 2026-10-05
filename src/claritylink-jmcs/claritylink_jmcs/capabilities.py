"""Evidence-labeled host /info display profile.

This is an AirPlay-shaped subset. Transport, authentication, audio and HID
advertisement are separate blockers; this object is not a working iPhone server.
"""
from __future__ import annotations

from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class SecondaryDisplayCapability:
    width: int = 800
    height: int = 480
    fps: int = 30
    enabled: bool = True
    physical_width_mm: int = 160
    physical_height_mm: int = 96
    main_uuid: str = "b7e6c5a0-1111-4000-8000-000000000001"
    secondary_uuid: str = "b7e6c5a0-2222-4000-8000-000000000002"
    initial_url: str = "maps:/car/instrumentcluster/map"

    def __post_init__(self) -> None:
        if not (1 <= self.width <= 4096 and 1 <= self.height <= 4096 and
                1 <= self.fps <= 120 and 1 <= self.physical_width_mm <= 1000 and
                1 <= self.physical_height_mm <= 1000):
            raise ValueError("invalid_lab_display_geometry")
        if uuid.UUID(self.main_uuid) == uuid.UUID(self.secondary_uuid):
            raise ValueError("duplicate_display_uuid")
        if not self.initial_url.startswith("maps:/car/instrumentcluster/"):
            raise ValueError("invalid_lab_initial_url")


def _display(kind: int, identifier: str, width: int, height: int, fps: int,
             physical_width: int, physical_height: int, initial_url: str | None = None) -> dict[str, object]:
    area = {"widthPixels": width, "heightPixels": height, "originXPixels": 0,
            "originYPixels": 0, "safeArea": {"widthPixels": width, "heightPixels": height,
            "originXPixels": 0, "originYPixels": 0, "drawUIOutsideSafeArea": True}}
    entry: dict[str, object] = {"uuid": identifier, "type": kind, "widthPixels": width,
        "heightPixels": height, "widthPhysical": physical_width, "heightPhysical": physical_height,
        "maxFPS": fps, "features": 10 if kind == 110 else 0,
        "primaryInputDevice": 1 if kind == 110 else 0,
        "viewAreas": [area], "initialViewArea": 0}
    if initial_url is not None:
        entry["initialURL"] = initial_url
    return entry


def host_info(capability: SecondaryDisplayCapability) -> dict[str, object]:
    """Host protocol structure supported by 43P topology and public prior art."""
    displays = [_display(110, capability.main_uuid, 800, 480, 30, 160, 96)]
    if capability.enabled:
        displays.append(_display(111, capability.secondary_uuid, capability.width,
            capability.height, capability.fps, capability.physical_width_mm,
            capability.physical_height_mm, capability.initial_url))
    return {"displays": displays, "modes": {"resources": [
        {"resourceID": resource, "transferType": 1, "transferPriority": 100,
         "takeConstraint": 100, "borrowConstraint": 100, "unborrowConstraint": 100}
        for resource in (1, 2)]}, "statusFlags": 4}


def lab_info(capability: SecondaryDisplayCapability) -> dict[str, object]:
    """Keep the original R5Z synthetic fixture separate from host protocol data."""
    displays: list[dict[str, object]] = [{"streamType": 110, "widthPixels": 800, "heightPixels": 480}]
    if capability.enabled:
        displays.append({"streamType": 111, "widthPixels": capability.width,
                         "heightPixels": capability.height, "maxFPS": capability.fps})
    return {"evidence": "CURRENT_IOS_LAB_TOPOLOGY_WITH_SYNTHETIC_GEOMETRY",
            "altScreen": capability.enabled, "displays": displays}
