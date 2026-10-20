"""Public-safe tests: Honda Display 1 admission remains unavailable."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-jmcs"))

from claritylink_jmcs.compat.honda.display_boundary import (  # noqa: E402
    DisplayEvidenceGap,
    HondaDisplayBoundaryGate,
)
from claritylink_jmcs.compat.honda.setup import EvidenceRequired  # noqa: E402


def test_honda_display_gate_is_disabled_and_enumerates_contract_gaps():
    assert HondaDisplayBoundaryGate.ENABLED is False
    assert HondaDisplayBoundaryGate.MISSING_EVIDENCE == tuple(DisplayEvidenceGap)
    assert {gap.value for gap in HondaDisplayBoundaryGate.MISSING_EVIDENCE} == {
        "honda_display_frame_admission_api",
        "honda_display_caller_authorization",
        "honda_display_input_frame_contract",
        "honda_display_output_ownership",
        "honda_display_frame_geometry_and_safe_area",
        "honda_display_warning_precedence_and_withdrawal",
        "honda_display_view_replacement_lifecycle",
        "honda_display_parent_teardown_and_authority_loss",
        "honda_display_factory_restoration",
    }


def test_honda_display_admission_fails_closed_with_exact_missing_contracts():
    with pytest.raises(EvidenceRequired) as error:
        HondaDisplayBoundaryGate.require_supported_output()

    assert error.value.fact == "honda_display_contract_incomplete:" + ",".join(
        gap.value for gap in DisplayEvidenceGap
    )


def test_caller_assertions_cannot_be_used_as_an_admission_override():
    # There is no evidence/token argument in this gate. Claimed session, owner,
    # dimensions, warning state, or restoration flags cannot open Honda output.
    with pytest.raises(TypeError):
        HondaDisplayBoundaryGate.require_supported_output(  # type: ignore[call-arg]
            authenticated=True,
            session="synthetic",
            width=800,
            height=480,
            warnings_safe=True,
            restored=True,
        )
