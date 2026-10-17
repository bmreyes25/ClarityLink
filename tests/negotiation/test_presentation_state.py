from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-negotiation"))

from presentation_state import INSTRUCTION_CONTEXT, MAP_CONTEXT, PresentationState


def test_control_and_view_area_updates_preserve_transport_generation():
    state = PresentationState(generation=7)
    state.set_navigation("maps", active=True)
    state.control("suggestUI", value=MAP_CONTEXT)
    assert not state.visible  # suggestion is a candidate, not a display switch
    assert state.selected_context is None
    state.control("showUI")
    assert state.selected_context == MAP_CONTEXT and state.visible
    state.control("forceKeyFrame")
    state.control("ViewArea", value={"x": 0, "y": 0, "w": 800, "h": 240})
    state.control("SafeArea", value={"x": 8, "y": 4, "w": 784, "h": 232})
    assert state.active and state.generation == 7
    assert state.visible and state.refresh_count == 1
    assert state.view_area["h"] == 240
    assert state.safe_area["h"] == 232
    assert state.presentation_generation == 3


def test_navigation_provider_change_is_not_transport_restart():
    state = PresentationState(generation=2)
    assert not state.transport_restart_required("navigation_provider_change")
    assert state.active and state.generation == 2


def test_real_transport_events_retire_exact_generation():
    for event in ("new_setup", "stream_id_changed", "socket_death", "teardown"):
        state = PresentationState(generation=3)
        assert state.transport_restart_required(event)
        assert not state.active and state.generation == 3


def test_no_navigation_has_no_candidates_and_provider_switch_keeps_transport():
    state = PresentationState(generation=2)
    assert state.eligible_contexts == ()
    state.set_navigation("maps", active=True)
    assert state.eligible_contexts == (MAP_CONTEXT,)
    state.control("suggestUI", value=MAP_CONTEXT)
    state.control("showUI")
    generation = state.generation
    state.set_navigation("waze", active=True)
    assert state.active and state.generation == generation
    assert state.visible and state.ui_suggestion == MAP_CONTEXT


def test_instruction_context_is_eligible_only_when_active_and_supported():
    state = PresentationState(generation=4)
    state.set_navigation("maps", active=True, instruction_active=False)
    assert INSTRUCTION_CONTEXT not in state.eligible_contexts
    state.set_navigation("maps", active=True, instruction_active=True)
    assert INSTRUCTION_CONTEXT in state.eligible_contexts
    state.control("suggestUI", value=INSTRUCTION_CONTEXT)
    state.control("showUI")
    assert state.visible
    state.set_navigation(None, active=False)
    assert not state.visible and state.ui_suggestion is None
    assert state.eligible_contexts == ()


def test_show_stop_and_unsupported_suggestion_fail_closed():
    state = PresentationState(generation=5)
    with pytest.raises(ValueError, match="no_eligible_ui_suggestion"):
        state.control("showUI")
    with pytest.raises(ValueError, match="ui_context_not_eligible"):
        state.control("suggestUI", value=MAP_CONTEXT)
    state.set_navigation("maps", active=True)
    state.control("suggestUI", value=MAP_CONTEXT)
    state.control("showUI")
    state.control("stopUI")
    assert not state.visible and state.ui_suggestion is None and state.selected_context is None


def test_view_area_and_safe_area_are_bounded_and_updates_are_atomic():
    state = PresentationState(generation=6)
    state.control("ViewArea", value={"x": 0, "y": 0, "w": 400, "h": 300})
    state.control("SafeArea", value={"x": 8, "y": 8, "w": 380, "h": 280})
    before = dict(state.view_area)
    with pytest.raises(ValueError, match="safe_area_outside_view_area"):
        state.control("ViewArea", value={"x": 0, "y": 0, "w": 100, "h": 100})
    assert state.view_area == before
    for invalid in ({"x": -1, "y": 0, "w": 10, "h": 10},
                    {"x": 0, "y": 0, "w": 900, "h": 10},
                    {"x": 0, "y": 0, "w": True, "h": 10}):
        with pytest.raises(ValueError, match="invalid_view_area"):
            state.control("ViewArea", value=invalid)


def test_video_config_advances_decoder_not_transport_generation():
    state = PresentationState(generation=8)
    assert state.update_video_config(800, 480) == 1
    assert state.update_video_config(800, 480) == 1
    assert state.update_video_config(1280, 720) == 2
    assert state.generation == 8 and state.active
    with pytest.raises(ValueError, match="invalid_video_config"):
        state.update_video_config(0, 720)


def test_provider_switch_is_presentation_only_and_socket_loss_retires_transport():
    state = PresentationState(generation=9)
    state.set_navigation("maps", active=True)
    state.control("suggestUI", value=MAP_CONTEXT)
    state.control("showUI")
    presentation_generation = state.presentation_generation
    assert not state.transport_restart_required("navigation_provider_change")
    assert state.generation == 9 and state.presentation_generation == presentation_generation
    assert state.transport_restart_required("socket_death")
    assert not state.active and not state.visible
    with pytest.raises(ValueError, match="transport_generation_not_active"):
        state.control("forceKeyFrame")
