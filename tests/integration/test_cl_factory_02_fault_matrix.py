"""Phase E — fault-injection matrix and resource invariants (CL-FACTORY-02).

Deterministic (no sleeps): every transition is driven explicitly. Exercises the
required fault categories across the pipeline, the simulated host and the
transport gate, and asserts resource invariants after each. Offline, synthetic.
safe_for_honda() is False throughout.
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
import simulated_cluster_host as sch


def _pipe(gen=1, cap=4, host=True):
    p = snp.SyntheticNavigationPipeline(capacity=cap)
    p.open_session(session_id=1, generation=gen)
    p.set_host_available(host)
    return p


def _u(p, gen, seq, ts, man=nav.ManeuverType.STRAIGHT, dist=100, unit=nav.DistanceUnit.METERS):
    return p.submit_update(generation=gen, sequence=seq, timestamp=ts,
                           maneuver=man, distance=dist, unit=unit, road_name="Rd")


# ---- fault categories ----
def test_unexpected_source_death():
    p = _pipe(); _u(p, 1, 0, 0)
    p.on_source_death()
    assert p.nav_state is nav.NavState.WITHDRAWN and p.current is None


def test_unexpected_consumer_death_closes_transport():
    g = fg.FrameGate(capacity=4); g.begin_generation(1)
    g.offer(fg.Frame(generation=1, sequence=0, timestamp=0))
    g.on_consumer_death()
    assert g.closed is True and len(g) == 0


def test_host_restart_cycle():
    p = _pipe(); _u(p, 1, 0, 0)
    p.on_host_lost(); p.begin_recovery(); p.restore_factory()
    assert p.state is snp.PipelineState.IDLE and p.current is None


def test_transport_closure_refuses_further_offers():
    g = fg.FrameGate(capacity=2); g.begin_generation(1); g.close()
    assert g.offer(fg.Frame(generation=1, sequence=0, timestamp=0)) is fg.FrameStatus.CLOSED


def test_queue_exhaustion_reject_new_policy():
    g = fg.FrameGate(capacity=2, policy=fg.BackpressurePolicy.REJECT_NEW); g.begin_generation(1)
    assert g.offer(fg.Frame(generation=1, sequence=0, timestamp=0)) is fg.FrameStatus.ACCEPTED
    assert g.offer(fg.Frame(generation=1, sequence=1, timestamp=1)) is fg.FrameStatus.ACCEPTED
    assert g.offer(fg.Frame(generation=1, sequence=2, timestamp=2)) is fg.FrameStatus.REJECTED_FULL
    assert len(g) == 2  # bounded


def test_queue_exhaustion_drop_oldest_policy():
    g = fg.FrameGate(capacity=2, policy=fg.BackpressurePolicy.DROP_OLDEST); g.begin_generation(1)
    for s in range(5):
        g.offer(fg.Frame(generation=1, sequence=s, timestamp=s))
    assert len(g) == 2 and g.stats.dropped_oldest == 3  # bounded, keeps freshest


def test_duplicate_generation_rejected_at_open():
    p = _pipe(gen=3)
    with pytest.raises(ValueError):
        p.open_session(session_id=1, generation=3)  # same generation
    with pytest.raises(ValueError):
        p.open_session(session_id=1, generation=2)  # lower generation


def test_future_generation_not_opened_rejected():
    p = _pipe(gen=1)
    out = _u(p, 2, 0, 0)  # gate opened at gen 1; gen 2 was never opened
    assert out.admission is snp.Admission.REJECTED_TRANSPORT
    assert out.transport_status is fg.FrameStatus.UNOPENED_GENERATION


def test_stale_timestamp_rejected():
    p = _pipe(gen=1)
    assert _u(p, 1, 0, 10).accepted is True
    out = _u(p, 1, 1, 5)  # seq advances but timestamp goes backwards
    assert out.admission is snp.Admission.REJECTED_TRANSPORT
    assert out.transport_status is fg.FrameStatus.STALE_TIMESTAMP


def test_sequence_rollback_rejected():
    p = _pipe(gen=1)
    assert _u(p, 1, 5, 5).accepted is True
    out = _u(p, 1, 3, 6)
    assert out.transport_status is fg.FrameStatus.OUT_OF_ORDER


def test_invalid_maneuver_mapped_unknown_not_crash():
    p = _pipe(gen=1)
    out = _u(p, 1, 0, 0, man="zigzag")
    assert out.accepted is True and p.current.maneuver is nav.ManeuverType.UNKNOWN


def test_oversized_road_name_rejected():
    p = _pipe(gen=1)
    out = p.submit_update(generation=1, sequence=0, timestamp=0,
                          maneuver=nav.ManeuverType.EXIT, distance=1,
                          unit=nav.DistanceUnit.FEET, road_name="x" * 1000)
    assert out.admission is snp.Admission.REJECTED_MALFORMED


def test_navigation_exit_during_pending_work():
    p = _pipe(gen=1); _u(p, 1, 0, 0)
    p.shutdown()  # exit while "work" is notionally pending
    assert p.state is snp.PipelineState.CLOSED and p.queue_depth == 0


def test_warning_arriving_during_recovery():
    p = _pipe(gen=1); _u(p, 1, 0, 0)
    p.on_host_lost(); p.begin_recovery()
    p.on_warning()  # warning during recovery must not crash or expose content
    assert p.presentation_eligibility()[0] is False
    assert p.current is None


def test_repeated_warning_events_safe():
    p = _pipe(gen=1); _u(p, 1, 0, 0)
    for _ in range(10):
        p.on_warning()
    assert p.state is snp.PipelineState.INTERRUPTED
    p.clear_warning()
    assert p.state is snp.PipelineState.ACTIVE


def test_recovery_interrupted_by_another_failure():
    p = _pipe(gen=1); _u(p, 1, 0, 0)
    p.on_host_lost(); p.begin_recovery()
    p.on_source_death()  # a second failure mid-recovery
    assert p.state is snp.PipelineState.SOURCE_LOST and p.current is None


def test_cleanup_called_twice_idempotent():
    p = _pipe(gen=1); _u(p, 1, 0, 0)
    p.shutdown(); p.shutdown()
    assert p.state is snp.PipelineState.CLOSED


def test_shutdown_during_in_flight_delivery():
    g = fg.FrameGate(capacity=4); g.begin_generation(1)
    for s in range(3):
        g.offer(fg.Frame(generation=1, sequence=s, timestamp=s))  # buffered, not polled
    assert len(g) == 3
    g.close()
    assert len(g) == 0 and g.poll() is None  # in-flight cleared on shutdown


def test_reconnection_after_complete_teardown():
    p = _pipe(gen=1); _u(p, 1, 0, 0)
    p.on_host_lost(); p.begin_recovery(); p.restore_factory()
    p.open_session(session_id=2, generation=2); p.set_host_available(True)
    assert _u(p, 2, 0, 0).accepted is True


# ---- resource invariants ----
def test_no_unbounded_update_history_or_queue():
    p = _pipe(gen=1, cap=4)
    for s in range(1000):
        _u(p, 1, s, s)
    assert p.queue_depth <= 1  # pipeline drains each accepted frame immediately
    assert p.current is not None  # only the latest is retained, not a history list


def test_ownership_released_on_teardown():
    p = _pipe(gen=1); _u(p, 1, 0, 0)
    p.shutdown()
    assert p.generation is None and p.session_id is None and p.current is None


def test_no_reused_stale_generation_across_lifetime():
    p = snp.SyntheticNavigationPipeline(capacity=4)
    p.open_session(session_id=1, generation=10); p.restore_factory()
    for g in (1, 5, 10):
        with pytest.raises(ValueError):
            p.open_session(session_id=1, generation=g)
    p.open_session(session_id=1, generation=11)  # strictly greater is required


def test_no_exposed_factory_presentation_interface():
    p = _pipe(gen=1)
    assert p.safe_for_honda() is False
    assert p.presentable_to_factory() is False
    for s in range(5):
        out = _u(p, 1, s, s)
        assert out.factory_decision.allowed is False
        assert out.factory_decision.reason_code == fic.R_SAFE_FOR_HONDA_FALSE
    # no method on the pipeline enables factory output
    assert not hasattr(p, "enable_factory")
    assert not hasattr(p, "present_to_factory")


def test_host_ownership_released_on_display_loss():
    h = sch.SimulatedClusterHost(); h.connect_display()
    h.present_main(session_id=1, generation=1, content="x")
    h.lose_display()
    assert h.main_owner is None and h.main_content is None
