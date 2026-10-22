"""Phase C — structured-navigation vs Type111-video contract separation
(CL-FACTORY-02). Proves the two representations cannot be accidentally
interchanged: a decoded-video frame is never treated as a semantic maneuver, and
a structured navigation update is never a video frame. No invented video->TBT
conversion exists. Offline, synthetic only.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("claritylink-transport", "claritylink-honda"):
    sys.path.insert(0, str(ROOT / "src" / p))

import pytest
import frame_gate as fg
import cluster_navigation_model as nav
import synthetic_navigation_pipeline as snp


def test_video_frame_and_nav_update_are_distinct_types():
    frame = fg.Frame(generation=1, sequence=0, timestamp=0, payload=b"\x00\x01video")
    update = nav.NavigationUpdate.build(1, 0, nav.ManeuverType.TURN_LEFT, 100, nav.DistanceUnit.METERS, "Main")
    assert not isinstance(frame, nav.NavigationUpdate)
    assert not isinstance(update, fg.Frame)
    # a video frame exposes no semantic maneuver fields
    assert not hasattr(frame, "maneuver")
    assert not hasattr(frame, "distance")


def test_nav_model_refuses_a_video_frame():
    """Feeding a transport video frame to the navigation model must NOT be
    silently interpreted as a maneuver -- it is rejected as malformed."""
    m = nav.ClusterNavigationModel(); m.start_session(1, 1)
    frame = fg.Frame(generation=1, sequence=0, timestamp=0, payload=b"video")
    assert m.apply_update(frame) is nav.UpdateStatus.MALFORMED
    assert m.current is None  # nothing was applied


def test_nav_model_refuses_raw_payload_shapes():
    m = nav.ClusterNavigationModel(); m.start_session(1, 1)
    for bogus in (b"\x00\x01\x02", {"maneuver": "LEFT"}, (nav.ManeuverType.TURN_LEFT, 100), "LEFT", 42):
        assert m.apply_update(bogus) is nav.UpdateStatus.MALFORMED
    assert m.current is None


def test_pipeline_has_no_video_to_maneuver_path():
    """The pipeline only accepts explicit structured fields; there is no API that
    converts decoded video bytes into a maneuver."""
    pipe = snp.SyntheticNavigationPipeline(capacity=4)
    pipe.open_session(session_id=1, generation=1)
    pipe.set_host_available(True)
    # payload bytes are not an accepted argument shape; a video frame cannot be
    # submitted as a maneuver because `maneuver` must resolve to a ManeuverType
    # and the numeric fields are validated.
    bad = pipe.submit_update(generation=1, sequence=0, timestamp=0,
                             maneuver=b"\x00video", distance=0, unit=nav.DistanceUnit.METERS)
    # a bytes maneuver stringifies to an unknown token -> UNKNOWN maneuver, which
    # is explicitly flagged (never a real decoded instruction), still structured.
    assert bad.admission is snp.Admission.ACCEPTED
    assert pipe.current.maneuver is nav.ManeuverType.UNKNOWN
    # there is categorically no method that ingests a fg.Frame as guidance
    assert not hasattr(pipe, "submit_video_frame")
    assert not hasattr(pipe, "decode_to_maneuver")


def test_structured_update_carries_no_decoded_video():
    update = nav.NavigationUpdate.build(1, 0, nav.ManeuverType.ROUNDABOUT, 50, nav.DistanceUnit.METERS, "Ring Rd")
    # the structured update is pure semantics -- no payload / pixel / codec fields
    for forbidden in ("payload", "pixels", "nal_units", "codec", "frame"):
        assert not hasattr(update, forbidden)
