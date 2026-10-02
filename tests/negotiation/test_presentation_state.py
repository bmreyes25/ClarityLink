from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-negotiation"))

from presentation_state import PresentationState


def test_control_and_view_area_updates_preserve_transport_generation():
    state = PresentationState(generation=7)
    state.control("suggestUI", value="maps:/car/instrumentcluster/map")
    state.control("showUI")
    state.control("forceKeyFrame")
    state.control("ViewArea", value={"x": 0, "y": 0, "w": 800, "h": 240})
    state.control("SafeArea", value={"x": 8, "y": 4, "w": 784, "h": 232})
    assert state.active and state.generation == 7
    assert state.visible and state.refresh_count == 1
    assert state.view_area["h"] == 240
    assert state.safe_area["h"] == 232


def test_navigation_provider_change_is_not_transport_restart():
    state = PresentationState(generation=2)
    assert not state.transport_restart_required("navigation_provider_change")
    assert state.active and state.generation == 2


def test_real_transport_events_retire_exact_generation():
    for event in ("new_setup", "stream_id_changed", "socket_death", "teardown"):
        state = PresentationState(generation=3)
        assert state.transport_restart_required(event)
        assert not state.active and state.generation == 3
