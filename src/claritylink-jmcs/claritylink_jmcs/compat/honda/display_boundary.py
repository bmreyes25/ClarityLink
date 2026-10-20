"""Fail-closed status for the not-established Honda Display 1 frame boundary.

This module does not implement a Honda adapter or accept caller-asserted
evidence. It records the contract items that must be documented before any
Honda-owned output can be enabled. The existing lab output host remains
independent of this gate.
"""
from __future__ import annotations

from enum import Enum

from .setup import EvidenceRequired


class DisplayEvidenceGap(str, Enum):
    FRAME_ADMISSION_API = "honda_display_frame_admission_api"
    CALLER_AUTHORIZATION = "honda_display_caller_authorization"
    INPUT_FRAME_CONTRACT = "honda_display_input_frame_contract"
    DISPLAY_OWNERSHIP = "honda_display_output_ownership"
    FRAME_GEOMETRY = "honda_display_frame_geometry_and_safe_area"
    WARNING_PRECEDENCE = "honda_display_warning_precedence_and_withdrawal"
    VIEW_REPLACEMENT = "honda_display_view_replacement_lifecycle"
    PARENT_TEARDOWN = "honda_display_parent_teardown_and_authority_loss"
    FACTORY_RESTORATION = "honda_display_factory_restoration"


class HondaDisplayBoundaryGate:
    """A permanently disabled evidence gate, not a display adapter."""

    ENABLED = False
    MISSING_EVIDENCE = tuple(DisplayEvidenceGap)

    @classmethod
    def require_supported_output(cls) -> None:
        gaps = ",".join(gap.value for gap in cls.MISSING_EVIDENCE)
        raise EvidenceRequired(f"honda_display_contract_incomplete:{gaps}")
