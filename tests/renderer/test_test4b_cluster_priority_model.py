"""Model-only warning ordering tests. No Honda display or coordinates."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-renderer"))

from cluster_priority_model import (  # noqa: E402
    api17_aosp_scenario,
    scenario_above_interrupt,
    scenario_between_main_and_interrupt,
    scenario_honda_owned_content,
    scenario_meter_warning,
    scenario_mixed_warning_owners,
)


def test_aosp_ordinary_presentation_is_below_honda_overlay_model_but_not_safe_proof():
    result = api17_aosp_scenario()
    assert not result.presentation_visible
    assert not result.obscured_warnings
    assert result.unknown_warnings == ("warning owner/stack not identified",)
    assert not result.modeled_safe
    assert result.provenance == "MODEL_ONLY"


def test_presentation_between_honda_main_and_interrupt_exposes_main_warning():
    result = scenario_between_main_and_interrupt()
    assert "warning inside main content" in result.obscured_warnings
    assert not result.modeled_safe


def test_presentation_above_interrupt_is_rejected():
    result = scenario_above_interrupt()
    assert result.obscured_warnings == ("interrupt-root warning",)
    assert not result.modeled_safe


def test_honda_owned_navigation_content_can_be_preempted_in_model_only():
    result = scenario_honda_owned_content()
    assert result.modeled_safe
    assert not result.presentation_visible
    assert result.provenance == "MODEL_ONLY"


def test_gauge_module_plane_protects_only_its_modeled_warning_class():
    result = scenario_meter_warning()
    assert not result.obscured_warnings
    assert result.modeled_safe


def test_mixed_warning_owners_fail_if_android_warning_is_below_app_layer():
    result = scenario_mixed_warning_owners()
    assert result.obscured_warnings == ("Android interrupt warning",)
    assert not result.modeled_safe
