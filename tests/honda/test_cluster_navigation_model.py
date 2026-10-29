"""Synthetic tests for the structured cluster-navigation model (CL-FACTORY-01 G-04).

Offline only. No Honda IPC, no cluster output, no vehicle. safeForHonda() stays False.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "claritylink-honda"))

import pytest
import cluster_navigation_model as nav


def _upd(gen, seq, man=nav.ManeuverType.TURN_LEFT, dist=200, unit=nav.DistanceUnit.METERS, road="Main St"):
    return nav.NavigationUpdate.build(gen, seq, man, dist, unit, road)


def test_start_session_activates_and_is_visible():
    m = nav.ClusterNavigationModel()
    m.start_session(session_id=1, generation=1)
    assert m.state is nav.NavState.ACTIVE and m.visible is True
    assert m.presentable_to_factory() is False  # inert


def test_updates_apply_and_track_current():
    m = nav.ClusterNavigationModel(); m.start_session(1, 1)
    assert m.apply_update(_upd(1, 0)) is nav.UpdateStatus.APPLIED
    assert m.apply_update(_upd(1, 1, man=nav.ManeuverType.ROUNDABOUT, dist=50)) is nav.UpdateStatus.APPLIED
    assert m.current.maneuver is nav.ManeuverType.ROUNDABOUT and m.current.distance == 50


def test_freshness_rejects_stale_dup_and_out_of_order():
    m = nav.ClusterNavigationModel(); m.start_session(1, 5)
    assert m.apply_update(_upd(5, 10)) is nav.UpdateStatus.APPLIED
    assert m.apply_update(_upd(5, 10)) is nav.UpdateStatus.DUPLICATE
    assert m.apply_update(_upd(5, 9)) is nav.UpdateStatus.OUT_OF_ORDER
    assert m.apply_update(_upd(4, 11)) is nav.UpdateStatus.STALE_GENERATION
    assert m.apply_update(_upd(6, 11)) is nav.UpdateStatus.NOT_ACTIVE  # newer gen needs start_session


def test_generation_must_strictly_increase_on_restart():
    m = nav.ClusterNavigationModel(); m.start_session(1, 1)
    with pytest.raises(nav.MalformedUpdate):
        m.start_session(1, 1)
    m.start_session(2, 2)
    assert m.apply_update(_upd(1, 0)) is nav.UpdateStatus.STALE_GENERATION
    assert m.apply_update(_upd(2, 0)) is nav.UpdateStatus.APPLIED


def test_malformed_input_rejected():
    for bad in [(-1, 0), (1, -1)]:
        with pytest.raises(nav.MalformedUpdate):
            _upd(bad[0], bad[1])
    with pytest.raises(nav.MalformedUpdate):
        nav.NavigationUpdate.build(1, 0, nav.ManeuverType.ARRIVE, 10, "PARSECS")
    # unknown maneuver string maps to UNKNOWN (accepted, flagged), not a crash
    u = nav.NavigationUpdate.build(1, 0, "noodle", 10, nav.DistanceUnit.MILES)
    assert u.maneuver is nav.ManeuverType.UNKNOWN


def test_warning_interrupt_withdraws_and_resumes():
    m = nav.ClusterNavigationModel(); m.start_session(1, 1)
    m.apply_update(_upd(1, 0))
    m.interrupt()
    assert m.state is nav.NavState.INTERRUPTED and m.visible is False
    # updates during an interrupt do not restore visibility implicitly
    assert m.apply_update(_upd(1, 1)) is nav.UpdateStatus.NOT_ACTIVE
    m.clear_interrupt()
    assert m.state is nav.NavState.ACTIVE and m.visible is True


def test_rapid_page_visibility_toggles():
    m = nav.ClusterNavigationModel(); m.start_session(1, 1)
    for v in (False, True, False, True):
        m.set_visible(v)
    assert m.visible is True
    m.set_visible(False)
    assert m.visible is False and m.state is nav.NavState.ACTIVE


def test_source_death_withdraws():
    m = nav.ClusterNavigationModel(); m.start_session(1, 1); m.apply_update(_upd(1, 0))
    m.on_source_death()
    assert m.state is nav.NavState.WITHDRAWN and m.visible is False and m.current is None


def test_host_lost_recover_and_restore():
    m = nav.ClusterNavigationModel(); m.start_session(1, 1)
    m.on_host_lost()
    assert m.state is nav.NavState.HOST_LOST and m.visible is False
    m.begin_recovery()
    assert m.state is nav.NavState.RECOVERING
    m.restore_factory()
    assert m.state is nav.NavState.INACTIVE and m.visible is False and m.current is None


def test_not_active_rejects_updates_before_session():
    m = nav.ClusterNavigationModel()
    assert m.apply_update(_upd(1, 0)) is nav.UpdateStatus.NOT_ACTIVE
    assert m.visible is False


def test_fail_closed_visibility_when_not_active():
    m = nav.ClusterNavigationModel(); m.start_session(1, 1)
    m.set_visible(True)
    m.on_host_lost()
    assert m.visible is False  # never visible outside ACTIVE
