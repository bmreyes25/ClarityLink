"""Clean-room models of pinned external AltScreen observations.

Every external value keeps explicit external provenance and maps to
HONDA_UNKNOWN. Candidate schemas do not build a Honda response.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


DIPLAY_REPOSITORY = "https://github.com/shihabal3amri/DiPlay"
DIPLAY_COMMIT = "f2d06951b4e8114dbb62f551c12a32a845a3042f"
PLAYPORT_REPOSITORY = "https://github.com/youcci/playport"
PLAYPORT_COMMIT = "9a0882dd0ffe48e467b59d58b12d81391df55ade"
XCERTPLAY_REPOSITORY = "https://github.com/shilapi/xcertplay"
XCERTPLAY_COMMIT = "17c92439413638dfd1d7f91d7e1c2e7358398762"


class Evidence(str, Enum):
    EXTERNAL_PRIOR_ART = "EXTERNAL_PRIOR_ART"
    EXTERNAL_PHYSICAL_VALIDATION = "EXTERNAL_PHYSICAL_VALIDATION"
    SYNTHETIC_TEST_VALUE = "SYNTHETIC_TEST_VALUE"


class HondaStatus(str, Enum):
    UNKNOWN = "HONDA_UNKNOWN"


class FieldProvenance(str, Enum):
    """Evidence strength for a clean-room candidate; never implies Honda support."""

    HONDA_CONFIRMED = "HONDA_CONFIRMED"
    MULTIPLE_EXTERNAL_PRIOR_ART = "MULTIPLE_EXTERNAL_PRIOR_ART"
    SINGLE_EXTERNAL_PRIOR_ART = "SINGLE_EXTERNAL_PRIOR_ART"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class CandidateField:
    name: str
    value: Any
    provenance: FieldProvenance
    honda_status: HondaStatus = HondaStatus.UNKNOWN

    def __post_init__(self) -> None:
        if self.honda_status is not HondaStatus.UNKNOWN:
            raise ValueError("external candidate fields cannot assert Honda behavior")
        if self.provenance is FieldProvenance.HONDA_CONFIRMED:
            raise ValueError("this external candidate schema cannot assert Honda confirmation")


@dataclass(frozen=True)
class Type111CandidateDisplay:
    stream_type: CandidateField
    display_uuid: CandidateField
    width_pixels: CandidateField
    height_pixels: CandidateField
    width_physical: CandidateField
    height_physical: CandidateField
    max_fps: CandidateField
    display_features: CandidateField
    input_device: CandidateField
    view_areas: CandidateField
    safe_area: CandidateField
    initial_view_area: CandidateField
    initial_url: CandidateField


@dataclass(frozen=True)
class Type111CandidateSetup:
    enabled_features: CandidateField
    stream_type: CandidateField
    stream_connection_id: CandidateField
    data_port: CandidateField


def _candidate_field(name: str, value: Any, provenance: FieldProvenance) -> CandidateField:
    return CandidateField(name, value, provenance)


def type111_candidate_display() -> Type111CandidateDisplay:
    """Candidate shape shared by inspected implementations; values stay external/unknown."""
    multi = FieldProvenance.MULTIPLE_EXTERNAL_PRIOR_ART
    return Type111CandidateDisplay(
        stream_type=_candidate_field("stream_type", 111, multi),
        display_uuid=_candidate_field("display_uuid", None, multi),
        width_pixels=_candidate_field("width_pixels", None, multi),
        height_pixels=_candidate_field("height_pixels", None, multi),
        width_physical=_candidate_field("width_physical", None, multi),
        height_physical=_candidate_field("height_physical", None, multi),
        max_fps=_candidate_field("max_fps", None, multi),
        display_features=_candidate_field("display_features", None, multi),
        input_device=_candidate_field("input_device", None, multi),
        view_areas=_candidate_field("view_areas", None, multi),
        safe_area=_candidate_field("safe_area", None, multi),
        initial_view_area=_candidate_field("initial_view_area", None, multi),
        initial_url=_candidate_field("initial_url", None, multi),
    )


def type111_candidate_setup() -> Type111CandidateSetup:
    multi = FieldProvenance.MULTIPLE_EXTERNAL_PRIOR_ART
    return Type111CandidateSetup(
        enabled_features=_candidate_field("enabled_features", ("viewAreas", "altScreen"), multi),
        stream_type=_candidate_field("stream_type", 111, multi),
        stream_connection_id=_candidate_field("stream_connection_id", None, multi),
        data_port=_candidate_field("data_port", None, multi),
    )


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
