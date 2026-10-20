import pytest

from claritylink_jmcs.compat.honda import (
    EvidenceRequired,
    HondaHackEvidenceGap,
    HondaHackFrameAdmissionGate,
)


def test_hondahack_frame_admission_is_disabled():
    assert HondaHackFrameAdmissionGate.ENABLED is False
    assert HondaHackFrameAdmissionGate.MISSING_EVIDENCE == tuple(HondaHackEvidenceGap)


def test_synthetic_frame_does_not_get_honda_authority():
    # A tiny synthetic frame exercises neither device access nor caller authority.
    synthetic_frame = b"\x00\x00\x00\x01\x65"
    with pytest.raises(EvidenceRequired, match="hondahack_oem_frame_admission_contract"):
        HondaHackFrameAdmissionGate.require_supported_frame_admission()
    # The diagnostic gate has no payload or authority override.
    with pytest.raises(TypeError):
        HondaHackFrameAdmissionGate.require_supported_frame_admission(frame=synthetic_frame)


@pytest.mark.parametrize("gap", HondaHackEvidenceGap)
def test_every_unresolved_contract_item_is_reported(gap):
    with pytest.raises(EvidenceRequired) as exc:
        HondaHackFrameAdmissionGate.require_supported_frame_admission()
    assert gap.value in str(exc.value)
