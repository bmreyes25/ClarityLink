"""Evidence-labeled host /info display profile.

This is an AirPlay-shaped subset. Transport, authentication, audio and HID
advertisement are separate blockers; this object is not a working iPhone server.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import uuid
from typing import Any


class CapabilityMode(str, Enum):
    DISABLED = "disabled"
    SYNTHETIC_LAB = "synthetic_lab"
    PRODUCTION = "production"


class EvidenceClass(str, Enum):
    HONDA_CONFIRMED = "HONDA_CONFIRMED"
    CURRENT_IOS_LAB_CONFIRMED = "CURRENT_IOS_LAB_CONFIRMED"
    SYNTHETIC_TEST_VALUE = "SYNTHETIC_TEST_VALUE"
    EXTERNAL_PRIOR_ART = "EXTERNAL_PRIOR_ART"
    UNKNOWN = "UNKNOWN"


class HondaStatus(str, Enum):
    CONFIRMED = "HONDA_CONFIRMED"
    UNKNOWN = "HONDA_UNKNOWN"


class DisplayRole(str, Enum):
    PRIMARY = "primary"
    SECONDARY_NAVIGATION = "secondary_navigation"


class SessionOwner(str, Enum):
    FACTORY_HONDA_RECEIVER = "factory_honda_receiver"
    CLARITYLINK_SECONDARY_CANDIDATE = "claritylink_secondary_candidate"


@dataclass(frozen=True)
class OwnershipInvariant:
    """Static ownership rule; this does not attest to a modeled session."""
    owner: SessionOwner = SessionOwner.FACTORY_HONDA_RECEIVER
    stream_type: int = 110
    evidence: EvidenceClass = EvidenceClass.HONDA_CONFIRMED
    honda_status: HondaStatus = HondaStatus.CONFIRMED

    def __post_init__(self) -> None:
        if (self.owner is not SessionOwner.FACTORY_HONDA_RECEIVER or self.stream_type != 110 or
                self.evidence is not EvidenceClass.HONDA_CONFIRMED or
                self.honda_status is not HondaStatus.CONFIRMED):
            raise CapabilityError("primary_type110_ownership_invariant_is_fixed")


class CapabilityError(ValueError):
    """A capability profile is invalid or crosses a disabled production gate."""


@dataclass(frozen=True)
class SourcedCapabilityValue:
    name: str
    value: Any
    evidence: EvidenceClass
    honda_status: HondaStatus = HondaStatus.UNKNOWN

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name or len(self.name) > 64:
            raise CapabilityError("invalid_capability_field_name")
        if not isinstance(self.evidence, EvidenceClass) or not isinstance(self.honda_status, HondaStatus):
            raise CapabilityError("invalid_capability_provenance")
        if self.evidence is not EvidenceClass.HONDA_CONFIRMED and self.honda_status is HondaStatus.CONFIRMED:
            raise CapabilityError("non_honda_evidence_cannot_confirm_honda_field")


@dataclass(frozen=True)
class LocalDisplayGeometry:
    """Synthetic renderer bounds; these are not CarPlay wire fields."""
    width_px: int = 800
    height_px: int = 480
    safe_left_px: int = 0
    safe_top_px: int = 0
    safe_width_px: int = 800
    safe_height_px: int = 480
    evidence: EvidenceClass = EvidenceClass.SYNTHETIC_TEST_VALUE

    def __post_init__(self) -> None:
        if self.evidence is not EvidenceClass.SYNTHETIC_TEST_VALUE:
            raise CapabilityError("local_geometry_requires_synthetic_evidence")
        values = (self.width_px, self.height_px, self.safe_width_px, self.safe_height_px)
        if any(isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 4096
               for value in values):
            raise CapabilityError("invalid_local_geometry")
        if (isinstance(self.safe_left_px, bool) or not isinstance(self.safe_left_px, int) or
                isinstance(self.safe_top_px, bool) or not isinstance(self.safe_top_px, int) or
                self.safe_left_px < 0 or self.safe_top_px < 0 or
                self.safe_left_px + self.safe_width_px > self.width_px or
                self.safe_top_px + self.safe_height_px > self.height_px):
            raise CapabilityError("safe_area_outside_local_geometry")


@dataclass(frozen=True)
class StreamCapabilityDescriptor:
    stream_type: int
    stream_connection_id: int
    role: DisplayRole
    owner: SessionOwner
    evidence: EvidenceClass
    honda_status: HondaStatus
    generation: int
    geometry: LocalDisplayGeometry | None = None
    navigation_role: SourcedCapabilityValue | None = None

    def __post_init__(self) -> None:
        if (isinstance(self.stream_type, bool) or not isinstance(self.stream_type, int) or
                self.stream_type not in (110, 111)):
            raise CapabilityError("unsupported_stream_type")
        if (isinstance(self.stream_connection_id, bool) or not isinstance(self.stream_connection_id, int) or
                not 1 <= self.stream_connection_id <= (1 << 64) - 1):
            raise CapabilityError("invalid_stream_connection_id")
        if isinstance(self.generation, bool) or not isinstance(self.generation, int) or self.generation < 1:
            raise CapabilityError("invalid_session_generation")
        if not isinstance(self.evidence, EvidenceClass) or not isinstance(self.honda_status, HondaStatus):
            raise CapabilityError("invalid_capability_provenance")
        if self.stream_type == 110:
            if (self.role is not DisplayRole.PRIMARY or
                    self.owner is not SessionOwner.FACTORY_HONDA_RECEIVER or
                    self.evidence is not EvidenceClass.SYNTHETIC_TEST_VALUE or
                    self.honda_status is not HondaStatus.UNKNOWN):
                raise CapabilityError("primary_type110_ownership_is_fixed")
        elif (self.role is not DisplayRole.SECONDARY_NAVIGATION or
              self.owner is not SessionOwner.CLARITYLINK_SECONDARY_CANDIDATE or
              self.evidence is not EvidenceClass.CURRENT_IOS_LAB_CONFIRMED or
              self.honda_status is not HondaStatus.UNKNOWN or self.geometry is None or
              not isinstance(self.geometry, LocalDisplayGeometry) or
              self.navigation_role is None or
              not isinstance(self.navigation_role, SourcedCapabilityValue) or
              self.navigation_role.name != "navigation_map_role" or
              self.navigation_role.evidence is not EvidenceClass.CURRENT_IOS_LAB_CONFIRMED):
            raise CapabilityError("type111_must_remain_secondary_candidate")


@dataclass(frozen=True)
class DualDisplayCapabilityPlan:
    generation: int
    primary: StreamCapabilityDescriptor
    secondary: StreamCapabilityDescriptor | None
    mode: CapabilityMode
    primary_ownership: OwnershipInvariant = OwnershipInvariant()

    def __post_init__(self) -> None:
        if isinstance(self.generation, bool) or not isinstance(self.generation, int) or self.generation < 1:
            raise CapabilityError("invalid_session_generation")
        if not isinstance(self.mode, CapabilityMode):
            raise CapabilityError("invalid_capability_mode")
        if self.primary.stream_type != 110 or self.primary.generation != self.generation:
            raise CapabilityError("primary_type110_required")
        if not isinstance(self.primary_ownership, OwnershipInvariant):
            raise CapabilityError("primary_ownership_invariant_required")
        if self.secondary is not None:
            if self.mode is not CapabilityMode.SYNTHETIC_LAB:
                raise CapabilityError("type111_production_advertisement_disabled")
            if (self.secondary.stream_type != 111 or self.secondary.generation != self.generation or
                    self.secondary.stream_connection_id == self.primary.stream_connection_id):
                raise CapabilityError("invalid_secondary_stream_ownership")

    @property
    def preserves_primary_ownership(self) -> bool:
        return (self.primary_ownership.owner is SessionOwner.FACTORY_HONDA_RECEIVER and
                self.primary_ownership.stream_type == 110 and
                self.primary.owner is self.primary_ownership.owner and
                self.primary.stream_type == self.primary_ownership.stream_type)


def build_dual_display_plan(
    generation: int,
    primary_stream_connection_id: int,
    secondary_stream_connection_id: int | None = None,
    *,
    mode: CapabilityMode = CapabilityMode.PRODUCTION,
    geometry: LocalDisplayGeometry | None = None,
) -> DualDisplayCapabilityPlan:
    """Build an internal plan; it does not serialize or advertise Apple fields."""
    primary = StreamCapabilityDescriptor(
        110, primary_stream_connection_id, DisplayRole.PRIMARY,
        SessionOwner.FACTORY_HONDA_RECEIVER, EvidenceClass.SYNTHETIC_TEST_VALUE,
        HondaStatus.UNKNOWN, generation,
    )
    secondary = None
    if secondary_stream_connection_id is not None:
        if mode is not CapabilityMode.SYNTHETIC_LAB:
            raise CapabilityError("type111_production_advertisement_disabled")
        if (isinstance(secondary_stream_connection_id, bool) or
                not isinstance(secondary_stream_connection_id, int)):
            raise CapabilityError("invalid_stream_connection_id")
        secondary = StreamCapabilityDescriptor(
            111, secondary_stream_connection_id, DisplayRole.SECONDARY_NAVIGATION,
            SessionOwner.CLARITYLINK_SECONDARY_CANDIDATE,
            EvidenceClass.CURRENT_IOS_LAB_CONFIRMED, HondaStatus.UNKNOWN, generation,
            geometry=geometry or LocalDisplayGeometry(),
            navigation_role=SourcedCapabilityValue(
                "navigation_map_role", "maps:/car/instrumentcluster/map",
                EvidenceClass.CURRENT_IOS_LAB_CONFIRMED,
            ),
        )
    return DualDisplayCapabilityPlan(generation, primary, secondary, mode)


def resolve_local_renderer_geometry(
    source_width_px: int,
    source_height_px: int,
    target: LocalDisplayGeometry,
) -> tuple[int, int, int, int]:
    """Fit a decoded frame in local safe bounds; no remote geometry is inferred."""
    if (isinstance(source_width_px, bool) or isinstance(source_height_px, bool) or
            not isinstance(source_width_px, int) or not isinstance(source_height_px, int) or
            not 1 <= source_width_px <= 4096 or not 1 <= source_height_px <= 4096):
        raise CapabilityError("invalid_source_geometry")
    scale_num = min(target.safe_width_px * source_height_px,
                    target.safe_height_px * source_width_px)
    scale_den = source_width_px * source_height_px
    width = max(1, source_width_px * scale_num // scale_den)
    height = max(1, source_height_px * scale_num // scale_den)
    left = target.safe_left_px + (target.safe_width_px - width) // 2
    top = target.safe_top_px + (target.safe_height_px - height) // 2
    return left, top, width, height


@dataclass(frozen=True)
class SecondaryDisplayCapability:
    width: int = 800
    height: int = 480
    fps: int = 30
    enabled: bool = False
    mode: CapabilityMode = CapabilityMode.DISABLED
    physical_width_mm: int = 160
    physical_height_mm: int = 96
    main_uuid: str = "b7e6c5a0-1111-4000-8000-000000000001"
    secondary_uuid: str = "b7e6c5a0-2222-4000-8000-000000000002"
    initial_url: str = "maps:/car/instrumentcluster/map"

    def __post_init__(self) -> None:
        if not isinstance(self.mode, CapabilityMode) or not isinstance(self.enabled, bool):
            raise CapabilityError("invalid_capability_mode")
        if self.enabled and self.mode is not CapabilityMode.SYNTHETIC_LAB:
            raise CapabilityError("secondary_advertisement_requires_explicit_synthetic_lab_mode")
        numeric = (self.width, self.height, self.fps,
                   self.physical_width_mm, self.physical_height_mm)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in numeric) or not (
                1 <= self.width <= 4096 and 1 <= self.height <= 4096 and
                1 <= self.fps <= 120 and 1 <= self.physical_width_mm <= 1000 and
                1 <= self.physical_height_mm <= 1000):
            raise ValueError("invalid_lab_display_geometry")
        try:
            main_uuid = uuid.UUID(self.main_uuid)
            secondary_uuid = uuid.UUID(self.secondary_uuid)
        except (ValueError, TypeError, AttributeError) as exc:
            raise CapabilityError("invalid_display_uuid") from exc
        if main_uuid == secondary_uuid:
            raise CapabilityError("duplicate_display_uuid")
        if not self.initial_url.startswith("maps:/car/instrumentcluster/"):
            raise ValueError("invalid_lab_initial_url")

    @classmethod
    def synthetic_lab(cls, **overrides: Any) -> "SecondaryDisplayCapability":
        return cls(enabled=True, mode=CapabilityMode.SYNTHETIC_LAB, **overrides)


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
            "mode": capability.mode.value,
            "altScreen": capability.enabled, "displays": displays}
