"""Acceptance tests for the integrated synthetic navigation pipeline
(CL-FACTORY-02 / P0). Offline, synthetic only. No vehicle, no real stream, no
factory output. safe_for_honda() stays False throughout.

Covers the 15 required Phase-A scenarios plus the four-way outcome distinction.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("claritylink-transport", "claritylink-honda"):
    sys.path.insert(0, str(ROOT / "src" / p))

import pytest
import frame_gate as fg
import cluster_navigation_model as nav
import factory_integration_contract as fic
import synthetic_navigation_pipeline as snp


def _open(pipe=None, *, sid=1, gen=1, host=True):
    pipe = pipe or snp.SyntheticNavigationPipeline(capacity=4)
    pipe.open_session(session_id=sid, generation=gen)
    pipe.set_host_available(host)
    return pipe


def _submit(pipe, *, gen=1, seq, ts, man=nav.ManeuverType.TURN_LEFT,
            dist=200, unit=nav.DistanceUnit.METERS, road="Main St"):
    return pipe.submit_update(generation=gen, sequence=seq, timestamp=ts,
                              maneuver=man, distance=dist, unit=unit, road_name=road)


# 1) valid navigation session starts
def test_valid_session_starts_active():
    pipe = _open()
    assert pipe.state is snp.PipelineState.ACTIVE
    assert pipe.generation == 1 and pipe.session_id == 1
    assert pipe.safe_for_honda() is False
    assert pipe.presentable_to_factory() is False


# 2) valid maneuver update accepted (all four outcomes)
def test_valid_update_accepted_four_way():
    pipe = _open()
    out = _submit(pipe, seq=0, ts=0)
    assert out.admission is snp.Admission.ACCEPTED
    assert out.accepted_into_transport is True
    assert out.accepted_into_nav is True
    assert out.presentation_eligible is True            # synthetic host present + visible
    assert out.presentation_reason == snp.P_ELIGIBLE_SYNTHETIC
    assert out.factory_decision.allowed is False         # factory output never available
    assert out.factory_decision.reason_code == fic.R_SAFE_FOR_HONDA_FALSE
    assert pipe.current.maneuver is nav.ManeuverType.TURN_LEFT


# 3) older generations rejected
def test_older_generation_rejected_at_transport():
    pipe = _open(gen=5)
    assert _submit(pipe, gen=5, seq=0, ts=0).admission is snp.Admission.ACCEPTED
    out = _submit(pipe, gen=4, seq=1, ts=1)
    assert out.admission is snp.Admission.REJECTED_TRANSPORT
    assert out.transport_status is fg.FrameStatus.STALE_GENERATION
    assert out.nav_status is None  # nav never consulted


# 4) duplicate updates rejected
def test_duplicate_update_rejected():
    pipe = _open()
    assert _submit(pipe, seq=3, ts=3).admission is snp.Admission.ACCEPTED
    out = _submit(pipe, seq=3, ts=4)
    assert out.admission is snp.Admission.REJECTED_TRANSPORT
    assert out.transport_status is fg.FrameStatus.DUPLICATE


# 5) out-of-order updates rejected
def test_out_of_order_rejected():
    pipe = _open()
    assert _submit(pipe, seq=5, ts=5).admission is snp.Admission.ACCEPTED
    out = _submit(pipe, seq=4, ts=6)
    assert out.admission is snp.Admission.REJECTED_TRANSPORT
    assert out.transport_status is fg.FrameStatus.OUT_OF_ORDER


# 6) invalid distance/unit inputs rejected
def test_invalid_inputs_rejected_malformed():
    pipe = _open()
    bad_unit = pipe.submit_update(generation=1, sequence=0, timestamp=0,
                                  maneuver=nav.ManeuverType.ARRIVE, distance=10,
                                  unit="PARSECS", road_name="x")
    assert bad_unit.admission is snp.Admission.REJECTED_MALFORMED
    assert bad_unit.transport_status is None  # transport untouched on malformed
    neg = pipe.submit_update(generation=1, sequence=0, timestamp=0,
                             maneuver=nav.ManeuverType.ARRIVE, distance=-1,
                             unit=nav.DistanceUnit.MILES)
    assert neg.admission is snp.Admission.REJECTED_MALFORMED
    # a still-valid update afterwards is accepted (state not corrupted)
    assert _submit(pipe, seq=0, ts=0).admission is snp.Admission.ACCEPTED


# 7) unknown maneuver types handled safely (accepted, flagged UNKNOWN)
def test_unknown_maneuver_handled_safely():
    pipe = _open()
    out = _submit(pipe, seq=0, ts=0, man="noodle")
    assert out.admission is snp.Admission.ACCEPTED
    assert pipe.current.maneuver is nav.ManeuverType.UNKNOWN


# 8) navigation page becomes inactive (not visible -> not eligible)
def test_navigation_page_inactive_not_eligible():
    pipe = _open()
    _submit(pipe, seq=0, ts=0)
    pipe._nav.set_visible(False)  # page hidden by the (synthetic) UI
    eligible, reason = pipe.presentation_eligibility()
    assert eligible is False and reason == snp.P_NOT_VISIBLE


# 9) warning withdraws custom content
def test_warning_withdraws_custom_content():
    pipe = _open()
    _submit(pipe, seq=0, ts=0)
    assert pipe.presentation_eligibility()[0] is True
    pipe.on_warning()
    assert pipe.state is snp.PipelineState.INTERRUPTED
    eligible, _ = pipe.presentation_eligibility()
    assert eligible is False  # content withdrawn while interrupted
    # updates during an interrupt are refused at the pipeline level (not ACTIVE)
    out = _submit(pipe, seq=1, ts=1)
    assert out.admission is snp.Admission.REJECTED_NOT_OPEN
    pipe.clear_warning()
    assert pipe.state is snp.PipelineState.ACTIVE
    assert pipe.presentation_eligibility()[0] is True  # resumes after warning clears


# 10) source dies during an update
def test_source_death_withdraws_everything():
    pipe = _open()
    _submit(pipe, seq=0, ts=0)
    pipe.on_source_death()
    assert pipe.state is snp.PipelineState.SOURCE_LOST
    assert pipe.nav_state is nav.NavState.WITHDRAWN
    assert pipe.current is None
    assert pipe.presentation_eligibility()[0] is False


# 11) host disappears during presentation
def test_host_loss_withdraws_and_closes_transport():
    pipe = _open()
    _submit(pipe, seq=0, ts=0)
    pipe.on_host_lost()
    assert pipe.state is snp.PipelineState.HOST_LOST
    assert pipe.nav_state is nav.NavState.HOST_LOST
    assert pipe.host_available is False
    assert pipe.presentation_eligibility()[0] is False


# 12) reconnect establishes a fresh generation
def test_reconnect_requires_fresh_generation():
    pipe = _open(gen=1)
    _submit(pipe, seq=0, ts=0)
    pipe.on_host_lost()
    pipe.begin_recovery()
    assert pipe.state is snp.PipelineState.RECOVERING
    pipe.restore_factory()
    assert pipe.state is snp.PipelineState.IDLE and pipe.generation is None
    # a strictly greater generation is required to reopen, even after a full
    # restore: the prior generation number can never be reused (anti-stale-auth)
    with pytest.raises(ValueError):
        pipe.open_session(session_id=2, generation=1)
    pipe.open_session(session_id=2, generation=2)
    pipe.set_host_available(True)
    assert _submit(pipe, gen=2, seq=0, ts=0).admission is snp.Admission.ACCEPTED


# 13) stale updates cannot reappear after recovery
def test_stale_update_cannot_reappear_after_recovery():
    pipe = _open(gen=2)
    _submit(pipe, gen=2, seq=10, ts=10)
    pipe.on_host_lost(); pipe.begin_recovery(); pipe.restore_factory()
    pipe.open_session(session_id=3, generation=3)
    pipe.set_host_available(True)
    # a replay from the old generation is rejected by transport ownership
    stale = _submit(pipe, gen=2, seq=11, ts=11)
    assert stale.admission is snp.Admission.REJECTED_TRANSPORT
    assert stale.transport_status is fg.FrameStatus.STALE_GENERATION
    # and the old sequence number is usable again under the fresh generation
    assert _submit(pipe, gen=3, seq=0, ts=0).admission is snp.Admission.ACCEPTED


# 14) factory-facing presentation remains disabled
def test_factory_presentation_always_disabled():
    pipe = _open()
    for seq in range(3):
        out = _submit(pipe, seq=seq, ts=seq)
        assert out.factory_decision.allowed is False
    assert pipe.safe_for_honda() is False
    assert pipe.presentable_to_factory() is False
    assert pipe.stats.factory_denied == 3


# 15) Type110 is unaffected by navigation withdrawal
def test_type110_independent_of_nav_withdrawal():
    # the pipeline owns only the secondary (cluster) nav path; a separate gate
    # models Type110 and must be untouched by any nav-side event.
    t110 = fg.FrameGate(capacity=4); t110.begin_generation(1)
    assert t110.offer(fg.Frame(generation=1, sequence=0, timestamp=0, payload=b"t110")) is fg.FrameStatus.ACCEPTED
    pipe = _open()
    _submit(pipe, seq=0, ts=0)
    pipe.on_warning()
    pipe.on_source_death()
    pipe.on_host_lost()
    # Type110 gate never observed any of it
    assert t110.closed is False
    assert t110.offer(fg.Frame(generation=1, sequence=1, timestamp=1, payload=b"t110")) is fg.FrameStatus.ACCEPTED
    assert len(t110) == 2


# extra: presentation eligibility reports factory-output-unavailable when no host
def test_no_synthetic_host_reports_output_unavailable():
    pipe = snp.SyntheticNavigationPipeline(capacity=4)
    pipe.open_session(session_id=1, generation=1)  # host not set -> unavailable
    out = _submit(pipe, seq=0, ts=0)
    assert out.admission is snp.Admission.ACCEPTED        # transport + nav still work
    assert out.presentation_eligible is False
    assert out.presentation_reason == snp.P_FACTORY_OUTPUT_UNAVAILABLE


# extra: submit before any session is not-open
def test_submit_before_session_rejected_not_open():
    pipe = snp.SyntheticNavigationPipeline(capacity=4)
    out = _submit(pipe, seq=0, ts=0)
    assert out.admission is snp.Admission.REJECTED_NOT_OPEN
    assert out.transport_status is None and out.nav_status is None


# extra: shutdown closes the pipeline permanently
def test_shutdown_is_terminal():
    pipe = _open()
    pipe.shutdown()
    assert pipe.state is snp.PipelineState.CLOSED
    with pytest.raises(RuntimeError):
        pipe.open_session(session_id=9, generation=9)
