"""MODEL_ONLY tests; these are not evidence of Honda implementation."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-renderer"))

from test4c_preemption_model import Mechanism, Phase, PreemptionModel  # noqa: E402


def test_all_competing_mechanisms_match_the_observed_visible_sequence():
    for mechanism in Mechanism:
        model = PreemptionModel(mechanism)
        assert model.snapshot().phase is Phase.CASTING_VISIBLE
        warning = model.activate_warning()
        assert warning.phase is Phase.WARNING_ACTIVE
        assert warning.warning_visible
        assert not warning.cast_view_visible
        restored = model.dismiss_warning()
        assert restored.phase is Phase.CASTING_RESTORED
        assert not restored.warning_visible
        assert restored.cast_view_visible
        assert not restored.production_admission_enabled


def test_view_replacement_hypothesis_detaches_and_restores_view():
    model = PreemptionModel(Mechanism.HONDA_VIEW_REPLACEMENT)
    assert not model.activate_warning().cast_view_attached
    assert model.dismiss_warning().cast_view_attached


def test_interrupt_and_meter_hypotheses_keep_cast_view_attached_under_warning():
    for mechanism in (Mechanism.HONDA_INTERRUPT_OVERLAY,
                      Mechanism.GAUGE_MODULE_COMPOSITION):
        model = PreemptionModel(mechanism)
        warning = model.activate_warning()
        assert warning.cast_view_attached
        assert not warning.cast_view_visible


def test_display_removal_and_host_failure_are_terminal_for_cast_content():
    for terminal in ("remove_display", "fail_host"):
        model = PreemptionModel(Mechanism.HONDA_INTERRUPT_OVERLAY)
        getattr(model, terminal)()
        assert not model.snapshot().cast_view_attached
        assert not model.activate_warning().cast_view_visible
        assert not model.dismiss_warning().cast_view_visible


def test_repeated_warning_cycle_does_not_leave_stale_cast_state():
    model = PreemptionModel(Mechanism.GAUGE_MODULE_COMPOSITION)
    for _ in range(3):
        assert not model.activate_warning().cast_view_visible
        assert model.dismiss_warning().cast_view_visible
