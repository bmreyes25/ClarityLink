"""Evidence-aware capability gate for synthetic Type111 replay only."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReplayMode(str, Enum):
    STRICT_HONDA = "strict_honda"
    HYPOTHETICAL_TYPE111 = "hypothetical_type111"


@dataclass(frozen=True)
class CapabilityInputs:
    session_active: bool
    type110_established: bool
    capability_advertised: bool
    display_descriptor_available: bool
    stream_fields_available: bool
    synthetic_security_inputs_available: bool
    renderer_target_available: bool
    unknown_honda_fields_explicit: bool


@dataclass(frozen=True)
class CapabilityDecision:
    allowed: bool
    mode: ReplayMode
    blockers: tuple[str, ...]
    evidence: str


def evaluate_capability_gate(mode: ReplayMode, inputs: CapabilityInputs) -> CapabilityDecision:
    """Strict Honda mode never asserts unimplemented Honda Type111 support."""
    if mode is ReplayMode.STRICT_HONDA:
        return CapabilityDecision(
            False, mode, ("Honda Type111 support is not confirmed",),
            "HONDA_CONFIRMED: stock Honda skips unsupported Type111",
        )
    required = {
        "session_active": inputs.session_active,
        "type110_established": inputs.type110_established,
        "capability_advertised": inputs.capability_advertised,
        "display_descriptor_available": inputs.display_descriptor_available,
        "stream_fields_available": inputs.stream_fields_available,
        "synthetic_security_inputs_available": inputs.synthetic_security_inputs_available,
        "renderer_target_available": inputs.renderer_target_available,
        "unknown_honda_fields_explicit": inputs.unknown_honda_fields_explicit,
    }
    blockers = tuple(name for name, available in required.items() if not available)
    return CapabilityDecision(
        not blockers, mode, blockers,
        "MHI2_DERIVED_HYPOTHESIS + SYNTHETIC_TEST_VALUE; not Honda support evidence",
    )
