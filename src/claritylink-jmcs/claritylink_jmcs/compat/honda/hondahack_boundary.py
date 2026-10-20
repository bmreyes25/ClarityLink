"""Fail-closed diagnostic boundary for an unverified Honda display integration.

This module does not attach to a display process or accept caller-supplied
evidence or authority.
"""
from __future__ import annotations

from enum import Enum

from .setup import EvidenceRequired


class HondaHackEvidenceGap(str, Enum):
    OEM_FRAME_ADMISSION = "hondahack_oem_frame_admission_contract"
    CALLER_AUTHORIZATION = "hondahack_caller_authorization"
    CLARITY_DEVICE_SCOPE = "hondahack_clarity_device_and_firmware_scope"
    WARNING_PRECEDENCE = "hondahack_warning_precedence"
    RESTORATION_LIFECYCLE = "hondahack_factory_restoration_lifecycle"


class HondaHackFrameAdmissionGate:
    """Diagnostic only: there is no supported HondaHack frame adapter."""

    ENABLED = False
    MISSING_EVIDENCE = tuple(HondaHackEvidenceGap)

    @classmethod
    def require_supported_frame_admission(cls) -> None:
        gaps = ",".join(gap.value for gap in cls.MISSING_EVIDENCE)
        raise EvidenceRequired(f"hondahack_frame_admission_unverified:{gaps}")
