"""CL-FACTORY-01 / G-04 integration — structured nav model with stream/lifecycle.

Synthetic only. Shows the cluster-navigation model yielding to a warning while the
(independent) Type110 center-display stream continues, plus host-loss withdrawal
and the fail-closed contract staying inert. No vehicle, no real stream.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-transport"))
sys.path.insert(0, str(ROOT / "src" / "claritylink-honda"))

import frame_gate as fg
import cluster_navigation_model as nav
import factory_integration_contract as fic


def _f(gen, seq, ts):
    return fg.Frame(generation=gen, sequence=seq, timestamp=ts, payload=b"t110")


def test_warning_withdraws_cluster_nav_but_type110_continues():
    t110 = fg.FrameGate(capacity=4); t110.begin_generation(1)
    m = nav.ClusterNavigationModel(); m.start_session(session_id=1, generation=1)
    contract = fic.default_fail_closed_contract()

    m.apply_update(nav.NavigationUpdate.build(1, 0, nav.ManeuverType.TURN_RIGHT, 300, nav.DistanceUnit.METERS, "1st Ave"))
    assert m.visible is True
    assert t110.offer(_f(1, 0, 0)) is fg.FrameStatus.ACCEPTED

    # factory warning: cluster custom content withdraws; contract yields; Type110 untouched
    assert contract.withdraw_for_warning().allowed is True
    m.interrupt()
    assert m.visible is False and m.state is nav.NavState.INTERRUPTED
    assert t110.offer(_f(1, 1, 1)) is fg.FrameStatus.ACCEPTED
    assert t110.poll() is not None and t110.poll() is not None

    # warning clears: cluster nav resumes; Type110 never interrupted
    m.clear_interrupt()
    assert m.visible is True and m.state is nav.NavState.ACTIVE


def test_host_loss_withdraws_nav_and_factory_stays_inert():
    m = nav.ClusterNavigationModel(); m.start_session(1, 1)
    contract = fic.default_fail_closed_contract()
    m.on_host_lost()
    assert m.visible is False and m.state is nav.NavState.HOST_LOST
    contract.on_host_death()
    # even a (hypothetical) factory-proven frame stays blocked by the guard
    d = contract.submit_frame_to_factory(evidence_tier=fic.EvidenceTier.FACTORY_PROVEN)
    assert d.allowed is False and d.reason_code == fic.R_SAFE_FOR_HONDA_FALSE
    m.begin_recovery(); m.restore_factory()
    assert m.state is nav.NavState.INACTIVE


def test_nav_model_never_presentable_to_factory_in_harness():
    m = nav.ClusterNavigationModel(); m.start_session(1, 1)
    assert m.presentable_to_factory() is False
