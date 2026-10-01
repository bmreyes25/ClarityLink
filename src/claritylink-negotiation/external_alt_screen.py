"""Clean-room model of pinned external AltScreen observations.

Every modeled field stays tagged EXTERNAL_PRIOR_ART (or synthetic test data)
and maps to HONDA_UNKNOWN. This module does not build a Honda response.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


DIPLAY_REPOSITORY = "https://github.com/shihabal3amri/DiPlay"
DIPLAY_COMMIT = "f2d06951b4e8114dbb62f551c12a32a845a3042f"
PLAYPORT_REPOSITORY = "https://github.com/youcci/playport"
PLAYPORT_COMMIT = "9a0882dd0ffe48e467b59d58b12d81391df55ade"


class Evidence(str, Enum):
    EXTERNAL_PRIOR_ART = "EXTERNAL_PRIOR_ART"
    EXTERNAL_PHYSICAL_VALIDATION = "EXTERNAL_PHYSICAL_VALIDATION"
    SYNTHETIC_TEST_VALUE = "SYNTHETIC_TEST_VALUE"


class HondaStatus(str, Enum):
    UNKNOWN = "HONDA_UNKNOWN"


@dataclass(frozen=True)
class HondaType111Candidate:
    field: str
    value: Any
    provenance: Evidence
    honda_status: HondaStatus = HondaStatus.UNKNOWN
    source_repository: str = DIPLAY_REPOSITORY
    source_commit: str = DIPLAY_COMMIT

    def __post_init__(self) -> None:
        if self.honda_status is not HondaStatus.UNKNOWN:
            raise ValueError("external model values cannot assert Honda confirmation")
        if self.provenance is Evidence.SYNTHETIC_TEST_VALUE:
            if not self.source_repository.startswith("synthetic:"):
                raise ValueError("synthetic test values require a synthetic source label")
        elif not self.source_commit:
            raise ValueError("external prior art must remain pinned to a source commit")


@dataclass(frozen=True)
class ExternalAltScreenProfile:
    fields: tuple[HondaType111Candidate, ...]

    def get(self, name: str) -> HondaType111Candidate:
        for item in self.fields:
            if item.field == name:
                return item
        raise KeyError(name)


def diplay_alt_screen_profile(*, width: int = 1280, height: int = 480) -> ExternalAltScreenProfile:
    """Return a non-Honda model; dimensions/port are explicitly synthetic."""
    prior = Evidence.EXTERNAL_PRIOR_ART
    physical = Evidence.EXTERNAL_PHYSICAL_VALIDATION
    synthetic = Evidence.SYNTHETIC_TEST_VALUE
    external = lambda name, value, evidence=prior: HondaType111Candidate(
        name, value, evidence, source_repository=DIPLAY_REPOSITORY, source_commit=DIPLAY_COMMIT,
    )
    generated = lambda name, value: HondaType111Candidate(
        name, value, synthetic, source_repository="synthetic:claritylink-tests", source_commit="none",
    )
    return ExternalAltScreenProfile((
        external("phone_alt_screen_urls", (
            "maps:/car/instrumentcluster/map",
            "maps:/car/instrumentcluster/instructioncard",
            "maps:/car/instrumentcluster",
        ), physical),
        external("receiver_advertises_second_display", True),
        external("stream_type", 111),
        external("receiver_alt_uuid", "independent receiver-assigned UUID"),
        external("primaryInputDevice", 0),
        external("display_features", 0),
        generated("widthPixels", width),
        generated("heightPixels", height),
        external("viewAreas", "per-display view area and safeArea; geometry is profile-specific"),
        external("initialViewArea", 0),
        external("initialURL", "maps:/car/instrumentcluster/map"),
        external("setup_enabled_features", ("viewAreas", "altScreen")),
        external("type111_setup_response", {"type": 111, "dataPort": "project listener port"}),
        generated("dataPort", 61001),
        external("cluster_forceKeyFrame", {"type": "forceKeyFrame", "params": {"uuid": "AltScreen UUID"}}),
        external("showUI", {"type": "showUI", "params": {"uuid": "AltScreen UUID", "url": "initialURL"}}),
        external("stopUI", {"type": "stopUI", "params": {"uuid": "AltScreen UUID"}}),
        external("screen_security", "session shared secret + streamConnectionID; DataStream HKDF key; ChaCha20-Poly1305 frame body"),
    ))


def honda_type111_security_status() -> HondaStatus:
    """The external profile is never a source of Honda Type111 crypto facts."""
    return HondaStatus.UNKNOWN
