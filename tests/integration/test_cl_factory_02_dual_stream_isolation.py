"""Phase D — Type110 / Type111 dual-stream ownership & isolation
(CL-FACTORY-02). Scenarios A-H from the campaign brief.

Type110 (center-display video) is modeled by an independent FrameGate. Type111
(secondary cluster navigation) is modeled by the integrated
SyntheticNavigationPipeline + Type111Lifecycle. These are synthetic models; none
of this proves independence on real factory hardware. safe_for_honda() is False.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("claritylink-transport", "claritylink-negotiation", "claritylink-honda"):
    sys.path.insert(0, str(ROOT / "src" / p))

import pytest
import frame_gate as fg
import lifecycle as lc
import cluster_navigation_model as nav
import synthetic_navigation_pipeline as snp


def _t110(gen=1, cap=4):
    g = fg.FrameGate(capacity=cap); g.begin_generation(gen)
    return g


def _vframe(gen, seq, ts):
    return fg.Frame(generation=gen, sequence=seq, timestamp=ts, payload=b"t110-video")


def _pipe(gen=1, sid=1, host=True, cap=4):
    p = snp.SyntheticNavigationPipeline(capacity=cap)
    p.open_session(session_id=sid, generation=gen)
    p.set_host_available(host)
    return p


def _nav_update(p, gen, seq, ts):
    return p.submit_update(generation=gen, sequence=seq, timestamp=ts,
                           maneuver=nav.ManeuverType.TURN_LEFT, distance=100,
                           unit=nav.DistanceUnit.METERS, road_name="Main")


# --- Scenario A: Type110 first ---
def test_scenario_a_type110_first():
    t110 = _t110(1)
    assert t110.offer(_vframe(1, 0, 0)) is fg.FrameStatus.ACCEPTED
    pipe = _pipe(gen=1)
    assert _nav_update(pipe, 1, 0, 0).accepted is True
    # independent identities: the pipeline has its own generation + state
    assert pipe.generation == 1 and t110.generation == 1
    assert t110.offer(_vframe(1, 1, 1)) is fg.FrameStatus.ACCEPTED
    assert len(t110) == 2  # cluster nav never touched the Type110 queue


# --- Scenario B: Type111 first ---
def test_scenario_b_type111_first():
    pipe = _pipe(gen=1)
    assert _nav_update(pipe, 1, 0, 0).accepted is True
    t110 = _t110(1)
    assert t110.offer(_vframe(1, 0, 0)) is fg.FrameStatus.ACCEPTED
    # order did not couple them: each advances on its own
    assert _nav_update(pipe, 1, 1, 1).accepted is True
    assert t110.offer(_vframe(1, 1, 1)) is fg.FrameStatus.ACCEPTED
    assert pipe.stats.accepted == 2 and t110.stats.accepted == 2


# --- Scenario C: Type111 dies ---
def test_scenario_c_type111_dies_type110_continues():
    t110 = _t110(1); t110.offer(_vframe(1, 0, 0))
    pipe = _pipe(gen=1); _nav_update(pipe, 1, 0, 0)
    pipe.on_source_death()
    assert pipe.nav_state is nav.NavState.WITHDRAWN
    # stale Type111 updates are rejected (pipeline no longer ACTIVE)
    assert _nav_update(pipe, 1, 1, 1).admission is snp.Admission.REJECTED_NOT_OPEN
    # Type110 continues untouched
    assert t110.offer(_vframe(1, 1, 1)) is fg.FrameStatus.ACCEPTED
    assert t110.closed is False


# --- Scenario D: Type110 dies ---
def test_scenario_d_type110_dies_type111_follows_own_contract():
    t110 = _t110(1); t110.offer(_vframe(1, 0, 0))
    pipe = _pipe(gen=1); _nav_update(pipe, 1, 0, 0)
    t110.on_source_death()
    assert t110.closed is True
    assert t110.offer(_vframe(1, 1, 1)) is fg.FrameStatus.CLOSED
    # Type111 pipeline is unaffected and keeps accepting per its own rules
    assert pipe.state is snp.PipelineState.ACTIVE
    assert _nav_update(pipe, 1, 1, 1).accepted is True


# --- Scenario E: Host restart ---
def test_scenario_e_host_restart_withdraws_secondary_keeps_type110():
    t110 = _t110(1); t110.offer(_vframe(1, 0, 0))
    pipe = _pipe(gen=1); _nav_update(pipe, 1, 0, 0)
    pipe.on_host_lost()
    assert pipe.presentation_eligibility()[0] is False
    # Type110 continuity
    assert t110.offer(_vframe(1, 1, 1)) is fg.FrameStatus.ACCEPTED
    # secondary resumes only with a fresh, strictly greater generation
    pipe.begin_recovery(); pipe.restore_factory()
    with pytest.raises(ValueError):
        pipe.open_session(session_id=2, generation=1)
    pipe.open_session(session_id=2, generation=2); pipe.set_host_available(True)
    assert _nav_update(pipe, 2, 0, 0).accepted is True


# --- Scenario F: Warning interruption ---
def test_scenario_f_warning_withdraws_secondary_type110_independent():
    t110 = _t110(1); t110.offer(_vframe(1, 0, 0))
    pipe = _pipe(gen=1); _nav_update(pipe, 1, 0, 0)
    pipe.on_warning()
    assert pipe.state is snp.PipelineState.INTERRUPTED
    assert pipe.presentation_eligibility()[0] is False
    # Type110 keeps flowing; we never touch factory warnings
    assert t110.offer(_vframe(1, 1, 1)) is fg.FrameStatus.ACCEPTED
    pipe.clear_warning()
    assert pipe.state is snp.PipelineState.ACTIVE


# --- Scenario G: Repeated failures, bounded resources ---
def test_scenario_g_repeated_cycles_bounded():
    t110 = _t110(1)
    gen = 0
    pipe = snp.SyntheticNavigationPipeline(capacity=4)
    for cycle in range(25):
        gen += 1
        pipe.open_session(session_id=cycle + 1, generation=gen)
        pipe.set_host_available(True)
        # push more updates than capacity; the gate drains per-update so depth<=1
        for seq in range(10):
            _nav_update(pipe, gen, seq, seq)
        assert pipe.queue_depth <= 1  # bounded; pipeline drains each accepted frame
        # alternate the failure that ends each cycle
        if cycle % 3 == 0:
            pipe.on_warning(); pipe.clear_warning(); pipe.on_host_lost()
        elif cycle % 3 == 1:
            pipe.on_source_death()
        else:
            pipe.on_host_lost()
        if pipe.state is snp.PipelineState.HOST_LOST:
            pipe.begin_recovery()
        pipe.restore_factory()
        assert pipe.state is snp.PipelineState.IDLE
        assert pipe.current is None  # no stale content survives a cycle
        # Type110 untouched throughout
        assert t110.offer(_vframe(1, cycle, cycle)) is fg.FrameStatus.ACCEPTED
    assert t110.closed is False


# --- Scenario H: Malformed input never reaches presentation ---
def test_scenario_h_malformed_input_never_presented():
    pipe = _pipe(gen=1)
    # malformed structured content
    bad_unit = pipe.submit_update(generation=1, sequence=0, timestamp=0,
                                  maneuver=nav.ManeuverType.ARRIVE, distance=5,
                                  unit="LIGHTYEARS")
    assert bad_unit.admission is snp.Admission.REJECTED_MALFORMED
    assert bad_unit.presentation_eligible is False
    # malformed transport metadata (negative seq) is rejected before nav
    with pytest.raises(ValueError):
        fg.Frame(generation=1, sequence=-1, timestamp=0, payload=b"x")
    # oversized road name
    big = pipe.submit_update(generation=1, sequence=0, timestamp=0,
                             maneuver=nav.ManeuverType.MERGE, distance=5,
                             unit=nav.DistanceUnit.METERS, road_name="R" * 9999)
    assert big.admission is snp.Admission.REJECTED_MALFORMED
    # the pipeline never presented anything malformed
    assert pipe.current is None
    # a valid update still works afterward (state intact)
    assert _nav_update(pipe, 1, 0, 0).accepted is True
