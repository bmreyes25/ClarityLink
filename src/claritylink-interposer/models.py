"""Configurable display, response, and redacted-secret models."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

class Provenance(str, Enum):
    HONDA_MAIN_DERIVED = "honda_main_derived"
    CLUSTER_KNOWN = "cluster_known"
    PRIOR_ART = "prior_art"
    CONFIGURABLE = "configurable"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class SourcedValue:
    value: Any = None
    provenance: Provenance = Provenance.UNKNOWN

@dataclass(frozen=True)
class ClarityLinkSecondaryDisplayDescriptor:
    uuid: SourcedValue = SourcedValue()
    edid: SourcedValue = SourcedValue()
    features: SourcedValue = SourcedValue()
    max_fps: SourcedValue = SourcedValue()
    pixel_width: SourcedValue = SourcedValue()
    pixel_height: SourcedValue = SourcedValue()
    physical_width: SourcedValue = SourcedValue()
    physical_height: SourcedValue = SourcedValue()
    opaque_fields: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        result = dict(self.opaque_fields)
        for key, item in (("uuid", self.uuid), ("edid", self.edid), ("features", self.features),
                          ("maxFPS", self.max_fps), ("pixelWidth", self.pixel_width),
                          ("pixelHeight", self.pixel_height), ("physicalWidth", self.physical_width),
                          ("physicalHeight", self.physical_height)):
            if item.value is not None:
                result[key] = item.value
        if not result:
            raise ValueError("secondary display descriptor has no configured fields")
        return result

@dataclass(frozen=True)
class ClarityLinkCapabilityProfile:
    enabled: bool = True
    descriptor: ClarityLinkSecondaryDisplayDescriptor = ClarityLinkSecondaryDisplayDescriptor()
    experimental_tokens: tuple[str, ...] = ()
    evidence_label: str = "configurable"

class ResponseStrategy(str, Enum):
    MINIMAL = "minimal"
    PRIOR_ART_CLONE = "prior_art_clone"

@dataclass(frozen=True)
class Type111ResponseProfile:
    strategy: ResponseStrategy = ResponseStrategy.MINIMAL
    include_stream_id: bool = False
    custom_fields: Mapping[str, Any] = field(default_factory=dict)

class SecretBytes:
    """Mutable secret holder with redacted representations and best-effort wiping."""
    __slots__ = ("_data",)
    def __init__(self, value: bytes):
        self._data = bytearray(value)
    def reveal_for_crypto(self) -> bytes:
        return bytes(self._data)
    def clear(self) -> None:
        for i in range(len(self._data)): self._data[i] = 0
        self._data.clear()
    def __len__(self) -> int: return len(self._data)
    def __repr__(self) -> str: return f"SecretBytes(<redacted>, length={len(self._data)})"
    __str__ = __repr__
