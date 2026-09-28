"""Evidence-labeled offline model for Honda's primary and proposed Display B.

This module models known configuration and unknown protocol fields. Its JSON
encoding is a deterministic research fixture, not CarPlay/iAP2 wire encoding.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from typing import Optional
from uuid import UUID


class DisplayRole(str, Enum):
    CENTER_MAIN = "center-main"
    CLUSTER_CANDIDATE = "cluster-candidate"


@dataclass(frozen=True)
class DisplayDescriptor:
    role: DisplayRole
    width: int
    height: int
    display_uuid: Optional[str] = None
    max_fps: Optional[int] = None
    touch_mode: Optional[str] = None
    physical_width_mm: Optional[int] = None
    physical_height_mm: Optional[int] = None
    evidence: str = "unknown"

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("display dimensions must be positive")
        if self.max_fps is not None and self.max_fps <= 0:
            raise ValueError("max_fps must be positive when specified")
        if self.display_uuid is not None:
            try:
                UUID(self.display_uuid)
            except (ValueError, AttributeError) as exc:
                raise ValueError("display_uuid must be a UUID string") from exc


@dataclass(frozen=True)
class VideoSessionDescriptor:
    """Candidate session metadata; identifiers are opaque and wire-unknown."""

    display_uuid: Optional[str]
    session_id: Optional[str] = None
    stream_id: Optional[str] = None
    codec: Optional[str] = None
    independent_from_primary: Optional[bool] = None
    evidence: str = "unknown"


@dataclass(frozen=True)
class CarPlaySessionModel:
    primary: DisplayDescriptor
    secondary: Optional[DisplayDescriptor] = None
    secondary_session: Optional[VideoSessionDescriptor] = None

    def __post_init__(self) -> None:
        if self.primary.role is not DisplayRole.CENTER_MAIN:
            raise ValueError("primary display must have center-main role")
        if self.secondary is None and self.secondary_session is not None:
            raise ValueError("secondary session requires a secondary display")
        if self.secondary is not None:
            if self.secondary.role is not DisplayRole.CLUSTER_CANDIDATE:
                raise ValueError("secondary display must have cluster-candidate role")
            primary_uuid = self.primary.display_uuid
            secondary_uuid = self.secondary.display_uuid
            if primary_uuid and secondary_uuid and primary_uuid == secondary_uuid:
                raise ValueError("primary and secondary UUIDs must be unique")
            session_uuid = self.secondary_session.display_uuid if self.secondary_session else None
            if secondary_uuid and session_uuid and secondary_uuid != session_uuid:
                raise ValueError("secondary session must reference its display UUID")

    def to_dict(self) -> dict:
        return {
            "model_kind": "evidence-labeled-offline-model",
            "wire_protocol_encoding": "unknown-not-emitted",
            "primary": _display_dict(self.primary),
            "secondary": _display_dict(self.secondary) if self.secondary else _unknown("not configured"),
            "secondary_session": _session_dict(self.secondary_session) if self.secondary_session else _unknown("not configured"),
            "independence_mechanism": _unknown("no Honda setup/assignment evidence"),
        }

    def deterministic_json(self) -> bytes:
        """Stable model fixture bytes. These bytes are not protocol packets."""
        return (json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _unknown(reason: str) -> dict:
    return {"status": "unknown", "reason": reason}


def _display_dict(display: DisplayDescriptor) -> dict:
    return {
        "role": display.role.value,
        "width": display.width,
        "height": display.height,
        "display_uuid": display.display_uuid if display.display_uuid is not None else _unknown("UUID value/generation not recovered"),
        "max_fps": display.max_fps if display.max_fps is not None else _unknown("negotiated value not observed"),
        "touch_mode": display.touch_mode if display.touch_mode is not None else _unknown("secondary touch requirement not established"),
        "physical_size_mm": (
            {"width": display.physical_width_mm, "height": display.physical_height_mm}
            if display.physical_width_mm is not None and display.physical_height_mm is not None
            else _unknown("protocol mapping/value not established")
        ),
        "evidence": display.evidence,
    }


def _session_dict(session: VideoSessionDescriptor) -> dict:
    return {
        "display_uuid": session.display_uuid if session.display_uuid is not None else _unknown("identity binding not recovered"),
        "session_id": session.session_id if session.session_id is not None else _unknown("session ID schema/value not recovered"),
        "stream_id": session.stream_id if session.stream_id is not None else _unknown("stream ID schema/value not recovered"),
        "codec": session.codec if session.codec is not None else _unknown("negotiated codec/profile not observed"),
        "independent_from_primary": session.independent_from_primary if session.independent_from_primary is not None else _unknown("no independent Display B setup observed"),
        "evidence": session.evidence,
    }


def honda_primary_model() -> CarPlaySessionModel:
    """Known configured primary values; no invented UUID or wire fields."""
    return CarPlaySessionModel(
        primary=DisplayDescriptor(
            role=DisplayRole.CENTER_MAIN,
            width=800,
            height=480,
            max_fps=30,
            touch_mode="hifi",
            physical_width_mm=153,
            physical_height_mm=92,
            evidence="j_config.xml and single gMainScreen setup; not a wire capture",
        )
    )


def candidate_cluster_model() -> CarPlaySessionModel:
    """Candidate Display B uses the known Android output canvas only."""
    return CarPlaySessionModel(
        primary=honda_primary_model().primary,
        secondary=DisplayDescriptor(
            role=DisplayRole.CLUSTER_CANDIDATE,
            width=800,
            height=480,
            evidence="candidate Android Display 1 canvas; not a CarPlay protocol value",
        ),
        secondary_session=VideoSessionDescriptor(
            display_uuid=None,
            independent_from_primary=None,
            evidence="candidate only; Honda second-session setup is not present in observed path",
        ),
    )
