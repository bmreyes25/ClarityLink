"""External prior art cannot be promoted into Honda facts by the model."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-negotiation"))
from external_alt_screen import (  # noqa: E402
    Evidence,
    HondaStatus,
    HondaType111Candidate,
    diplay_alt_screen_profile,
    honda_type111_security_status,
)


def test_all_external_fields_remain_tagged_and_honda_unknown():
    profile = diplay_alt_screen_profile()
    assert profile.fields
    assert all(field.honda_status is HondaStatus.UNKNOWN for field in profile.fields)
    assert all(field.provenance in (Evidence.EXTERNAL_PRIOR_ART, Evidence.EXTERNAL_PHYSICAL_VALIDATION,
                                    Evidence.SYNTHETIC_TEST_VALUE) for field in profile.fields)
    assert profile.get("stream_type").value == 111
    assert profile.get("stream_type").provenance is Evidence.EXTERNAL_PRIOR_ART


def test_initial_url_view_areas_and_features_are_not_honda_defaults():
    profile = diplay_alt_screen_profile()
    for name in ("initialURL", "viewAreas", "setup_enabled_features"):
        assert profile.get(name).provenance is Evidence.EXTERNAL_PRIOR_ART
        assert profile.get(name).honda_status is HondaStatus.UNKNOWN
    assert profile.get("initialURL").value == "maps:/car/instrumentcluster/map"
    assert profile.get("setup_enabled_features").value == ("viewAreas", "altScreen")


def test_type111_data_port_and_uuid_scoped_controls_keep_separate_provenance():
    profile = diplay_alt_screen_profile()
    assert profile.get("type111_setup_response").provenance is Evidence.EXTERNAL_PRIOR_ART
    assert profile.get("dataPort").provenance is Evidence.SYNTHETIC_TEST_VALUE
    assert profile.get("cluster_forceKeyFrame").value["params"]["uuid"] == "AltScreen UUID"
    assert profile.get("cluster_forceKeyFrame").honda_status is HondaStatus.UNKNOWN
    assert profile.get("showUI").provenance is Evidence.EXTERNAL_PRIOR_ART
    assert profile.get("stopUI").provenance is Evidence.EXTERNAL_PRIOR_ART


def test_modern_screen_security_is_never_a_honda_crypto_selection():
    profile = diplay_alt_screen_profile()
    assert "ChaCha20-Poly1305" in profile.get("screen_security").value
    assert profile.get("screen_security").provenance is Evidence.EXTERNAL_PRIOR_ART
    assert honda_type111_security_status() is HondaStatus.UNKNOWN


def test_external_field_cannot_claim_honda_confirmed():
    try:
        HondaType111Candidate("initialURL", "maps:/...", Evidence.EXTERNAL_PRIOR_ART,
                              honda_status="HONDA_CONFIRMED")
    except ValueError:
        pass
    else:
        raise AssertionError("external value must not promote itself into Honda evidence")
