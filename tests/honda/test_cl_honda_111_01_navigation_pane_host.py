"""CL-HONDA-111-01: simulated Navigation-pane host (synthetic layers only).

Proves ClarityLink's own page / viewport / lease behavior. Nothing here reflects
the real Honda display host, whose Navigation-page ownership and physical
aperture are unknown. ``safe_for_honda()`` stays False.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in ("claritylink-honda", "claritylink-transport", "claritylink-negotiation"):
    sys.path.insert(0, str(ROOT / "src" / p))

import navigation_pane_host as nph  # noqa: E402

VP = nph.Viewport(10, 20, 400, 200, nph.ViewportSource.SYNTHETIC_TEST)


def host(*, page=True, viewport=VP, display=True):
    h = nph.NavigationPaneHost()
    if display:
        h.connect_display()
    h.select_navigation_page(page)
    if viewport is not None:
        assert h.set_viewport(viewport)
    return h


def owner(gen=1, sid=0x11, parent=1):
    return nph.PaneOwner(sid, parent, gen)


def frame(seq=1, w=800, h=480, sid=0x11, parent=1, **kw):
    fields = dict(stream_connection_id=sid, parent_generation=parent, stream_generation=1,
                  config_generation=1, sequence=seq, presentation_time_ns=seq * 1000,
                  width=w, height=h, stride=w * 4, payload=bytes(w * 4 * h))
    fields.update(kw)
    return nph.DecodedFrame(**fields)


# --- viewport honesty ---
def test_layout_local_candidate_and_unknown_viewports_are_refused():
    h = host(viewport=None)
    local = nph.Viewport(0, 24, 584, 191, nph.ViewportSource.LAYOUT_LOCAL_CANDIDATE)
    assert h.set_viewport(local) is False
    assert h.set_viewport(nph.Viewport(0, 0, 100, 100)) is False   # UNKNOWN source
    assert h.viewport is None and h.stats.viewports_rejected == 2
    assert h.acquire(owner()).status is nph.AcquireStatus.DENIED_NO_VIEWPORT


@pytest.mark.parametrize("args", [(-1, 0, 1, 1), (0, -1, 1, 1), (0, 0, 0, 1), (0, 0, 1, 0), (0, 0, True, 1),
                                  (0, 0, 1.5, 1)])
def test_invalid_viewport_cannot_be_constructed(args):
    with pytest.raises(ValueError):
        nph.Viewport(*args, nph.ViewportSource.SYNTHETIC_TEST)


def test_no_default_physical_geometry_exists():
    h = nph.NavigationPaneHost()
    assert h.viewport is None


def test_viewport_change_revokes_the_lease():
    h = host()
    lease = h.acquire(owner()).lease
    seen = []
    lease.add_revoke_callback(seen.append)
    assert h.set_viewport(nph.Viewport(0, 0, 50, 50, nph.ViewportSource.SYNTHETIC_TEST))
    assert not lease.valid and seen == ["viewport_changed"]
    # identical viewport is not a change
    lease2 = h.acquire(owner(gen=2)).lease
    assert h.set_viewport(nph.Viewport(0, 0, 50, 50, nph.ViewportSource.SYNTHETIC_TEST))
    assert lease2.valid


# --- acquire preconditions ---
def test_lease_needs_display_page_viewport_and_no_interrupt():
    assert host(display=False).acquire(owner()).status is nph.AcquireStatus.DENIED_NO_DISPLAY
    assert host(page=False).acquire(owner()).status is nph.AcquireStatus.DENIED_PAGE_NOT_SELECTED
    h = host()
    h.activate_interrupt()
    assert h.acquire(owner()).status is nph.AcquireStatus.DENIED_INTERRUPTED
    h2 = host()
    r = h2.acquire(owner())
    assert r.status is nph.AcquireStatus.GRANTED and r.lease.valid


@pytest.mark.parametrize("bad", [dict(stream_connection_id=0), dict(parent_generation=0),
                                 dict(pane_generation=0), dict(pane_generation=True)])
def test_malformed_owner_is_rejected(bad):
    fields = dict(stream_connection_id=1, parent_generation=1, pane_generation=1)
    fields.update(bad)
    with pytest.raises(ValueError):
        host().acquire(nph.PaneOwner(**fields))


def test_non_owner_object_is_rejected():
    with pytest.raises(ValueError):
        host().acquire(object())


def test_generation_must_strictly_increase_for_the_life_of_the_host():
    h = host()
    l1 = h.acquire(owner(gen=5)).lease
    h.withdraw(l1)
    assert h.acquire(owner(gen=5)).status is nph.AcquireStatus.DENIED_STALE_GENERATION
    assert h.acquire(owner(gen=4)).status is nph.AcquireStatus.DENIED_STALE_GENERATION
    assert h.acquire(owner(gen=6)).granted


def test_newer_lease_replaces_and_revokes_the_older_one():
    h = host()
    l1 = h.acquire(owner(gen=1)).lease
    seen = []
    l1.add_revoke_callback(seen.append)
    r2 = h.acquire(owner(gen=2))
    assert r2.status is nph.AcquireStatus.REPLACED
    assert not l1.valid and seen == ["replaced"] and r2.lease.valid


# --- revocation causes ---
def test_page_deselect_revokes_and_reselect_grants_nothing():
    h = host()
    lease = h.acquire(owner()).lease
    assert h.present(lease, frame()).presented
    h.select_navigation_page(False)
    assert not lease.valid and lease.revoked_reason == "page_deselected"
    assert h.custom_content_visible is False and h.factory_content_visible is True
    h.select_navigation_page(True)
    assert h.lease is None and h.presented is None and h.custom_content_visible is False
    assert h.present(lease, frame(seq=2)).status is nph.PresentStatus.DENIED_LEASE_INVALID


def test_interrupt_revokes_and_clearing_it_does_not_restore_content():
    h = host()
    lease = h.acquire(owner()).lease
    h.present(lease, frame())
    h.activate_interrupt()
    assert not lease.valid and h.custom_content_visible is False
    h.clear_interrupt()
    assert h.custom_content_visible is False and h.lease is None
    assert h.present(lease, frame(seq=2)).status is nph.PresentStatus.DENIED_LEASE_INVALID
    assert h.acquire(owner(gen=1)).status is nph.AcquireStatus.DENIED_STALE_GENERATION
    assert h.acquire(owner(gen=2)).granted


def test_display_loss_revokes_and_recovery_needs_a_fresh_generation():
    h = host()
    lease = h.acquire(owner(gen=3)).lease
    h.lose_display()
    assert not lease.valid and not h.display_available
    assert h.acquire(owner(gen=4)).status is nph.AcquireStatus.DENIED_NO_DISPLAY
    h.begin_restore()
    assert h.complete_restore(display_valid=False) is False
    assert h.acquire(owner(gen=4)).status is nph.AcquireStatus.DENIED_NO_DISPLAY
    h.begin_restore()
    assert h.complete_restore(display_valid=True) is True
    assert h.acquire(owner(gen=3)).status is nph.AcquireStatus.DENIED_STALE_GENERATION
    assert h.acquire(owner(gen=4)).granted


def test_host_rebuild_by_reconnect_also_revokes_callbacks_run():
    h = host()
    lease = h.acquire(owner()).lease
    seen = []
    lease.add_revoke_callback(seen.append)
    h.connect_display()
    assert not lease.valid and seen == ["display_connected_rebuild"]


def test_close_revokes_and_denies_everything_after():
    h = host()
    lease = h.acquire(owner()).lease
    h.close()
    assert not lease.valid
    assert h.acquire(owner(gen=9)).status is nph.AcquireStatus.DENIED_CLOSED
    assert h.factory_content_visible is False   # display is not available once closed


def test_withdraw_is_always_allowed_and_idempotent_for_stale_leases():
    h = host()
    lease = h.acquire(owner()).lease
    h.withdraw(lease)
    h.withdraw(lease)
    h.withdraw(None)
    assert h.lease is None and h.factory_content_visible


def test_revoke_callbacks_run_once_and_are_contained():
    h = host()
    lease = h.acquire(owner()).lease
    seen = []

    def boom(_r):
        raise RuntimeError("consumer bug")
    lease.add_revoke_callback(boom)
    lease.add_revoke_callback(seen.append)
    h.activate_interrupt()
    h.activate_interrupt()
    assert seen == ["interrupt"]


def test_late_revoke_callback_on_revoked_lease_runs_immediately():
    h = host()
    lease = h.acquire(owner()).lease
    h.select_navigation_page(False)
    seen = []
    lease.add_revoke_callback(seen.append)
    assert seen == ["page_deselected"]


def test_revoke_callback_count_is_bounded():
    lease = host().acquire(owner()).lease
    for _ in range(nph.MAX_REVOKE_CALLBACKS):
        lease.add_revoke_callback(lambda _r: None)
    with pytest.raises(ValueError):
        lease.add_revoke_callback(lambda _r: None)


# --- presentation ---
def test_present_computes_a_centered_scale_to_fit_destination_inside_the_viewport():
    h = host()
    lease = h.acquire(owner()).lease
    r = h.present(lease, frame(w=800, h=480))
    assert r.presented
    x, y, w, hh = r.destination
    assert (w, hh) == (333, 200)   # width-limited? 400/800 vs 200/480 -> height-limited
    assert 10 <= x and x + w <= 410 and 20 <= y and y + hh <= 220


def test_rotation_swaps_effective_size_and_crop_is_applied_first():
    f = frame(w=800, h=480, crop=(0, 0, 400, 100), rotation=90)
    assert f.effective_size() == (100, 400)
    assert f.validate() is None


@pytest.mark.parametrize("kw,reason", [
    (dict(width=0), "invalid_dimensions"),
    (dict(width=nph.MAX_WIDTH + 1), "invalid_dimensions"),
    (dict(stride=100), "invalid_stride"),
    (dict(payload=b"short"), "short_payload"),
    (dict(rotation=45), "invalid_rotation"),
    (dict(crop=(5, 5, 5, 10)), "invalid_crop"),
    (dict(crop=(790, 0, 810, 10)), "invalid_crop"),
    (dict(crop=(0, 0, 1)), "invalid_crop"),
    (dict(sequence=-1), "malformed_field"),
    (dict(stream_generation=0), "malformed_identity"),
])
def test_malformed_frames_are_rejected_with_a_reason(kw, reason):
    h = host()
    lease = h.acquire(owner()).lease
    if "width" in kw and kw["width"] == 0:
        f = frame(w=100)
        f.width = 0
    else:
        f = frame(w=100, h=60, **kw) if "width" not in kw else frame(**kw)
    r = h.present(lease, f)
    assert r.status is nph.PresentStatus.DENIED_MALFORMED and r.reason == reason


def test_oversize_frame_is_rejected_before_any_copy():
    f = frame(w=100, h=100)
    f.width, f.height = nph.MAX_WIDTH, nph.MAX_HEIGHT
    f.stride = nph.MAX_WIDTH * 4
    assert f.validate() == "frame_too_large"


def test_surface_backed_frames_are_unsupported():
    h = host()
    lease = h.acquire(owner()).lease
    f = frame(w=10, h=10)
    f.storage = nph.FrameStorage.SURFACE
    assert h.present(lease, f).status is nph.PresentStatus.DENIED_UNSUPPORTED_STORAGE


def test_identity_mismatch_stale_and_duplicate_sequence_are_denied():
    h = host()
    lease = h.acquire(owner(sid=0x11, parent=1)).lease
    assert h.present(lease, frame(seq=5)).presented
    assert h.present(lease, frame(seq=5)).status is nph.PresentStatus.DENIED_STALE_SEQUENCE
    assert h.present(lease, frame(seq=4)).status is nph.PresentStatus.DENIED_STALE_SEQUENCE
    assert h.present(lease, frame(seq=6, sid=0x99)).status is nph.PresentStatus.DENIED_IDENTITY_MISMATCH
    assert h.present(lease, frame(seq=6, parent=2)).status is nph.PresentStatus.DENIED_IDENTITY_MISMATCH
    assert h.present(lease, frame(seq=6)).presented


def test_non_frame_and_foreign_lease_are_denied():
    h, other = host(), host()
    lease = h.acquire(owner()).lease
    assert h.present(lease, object()).status is nph.PresentStatus.DENIED_MALFORMED
    assert other.present(lease, frame()).status is nph.PresentStatus.DENIED_LEASE_INVALID
    assert h.present("lease", frame()).status is nph.PresentStatus.DENIED_LEASE_INVALID


def test_fit_rect_is_pure_and_stays_inside_the_viewport():
    for sw, sh in [(1, 1), (800, 480), (480, 800), (3, 1000), (1000, 3), (400, 200)]:
        x, y, w, h = nph.fit_rect(sw, sh, VP)
        assert w >= 1 and h >= 1
        assert VP.x <= x and x + w <= VP.x + VP.width
        assert VP.y <= y and y + h <= VP.y + VP.height
    with pytest.raises(ValueError):
        nph.fit_rect(0, 5, VP)


def test_frame_release_is_exactly_once_and_contained():
    calls = []
    f = frame(w=4, h=4, release_callback=lambda: calls.append(1))
    f.release()
    f.release()
    assert calls == [1]

    def boom():
        raise RuntimeError("producer bug")
    g = frame(w=4, h=4, release_callback=boom)
    g.release()   # must not raise
    g.release()


def test_host_never_claims_to_be_safe_for_honda_or_real():
    h = host()
    assert h.safe_for_honda() is False and h.synthetic is True
    assert "redacted" in repr(h.acquire(owner()).lease)


def test_factory_content_visible_means_display_up_and_nothing_of_ours_shown():
    h = host()
    assert h.factory_content_visible is True
    lease = h.acquire(owner()).lease
    h.present(lease, frame())
    assert h.factory_content_visible is False and h.custom_content_visible is True
    h.withdraw(lease)
    assert h.factory_content_visible is True


def test_next_generation_tracks_the_lifetime_floor_but_does_not_revive_dead_leases():
    h = host()
    assert h.next_generation() == 1
    l1 = h.acquire(owner(gen=h.next_generation())).lease
    assert h.next_generation() == 2
    h.activate_interrupt()
    h.clear_interrupt()
    assert h.next_generation() == 2
    assert not l1.valid
    assert h.present(l1, frame()).status is nph.PresentStatus.DENIED_LEASE_INVALID


@pytest.mark.parametrize("cause", ["page", "interrupt", "display", "viewport", "withdraw", "close"])
def test_every_revocation_cause_empties_the_main_layer_not_just_the_lease(cause):
    h = host()
    lease = h.acquire(owner()).lease
    h.present(lease, frame())
    assert h.main_layer_occupied
    {"page": lambda: h.select_navigation_page(False),
     "interrupt": h.activate_interrupt,
     "display": h.lose_display,
     "viewport": lambda: h.set_viewport(nph.Viewport(1, 1, 9, 9, nph.ViewportSource.SYNTHETIC_TEST)),
     "withdraw": lambda: h.withdraw(lease),
     "close": h.close}[cause]()
    assert not lease.valid and not h.main_layer_occupied and h.lease is None


# --- page and interrupt driven by the host's reported selection ---
CC, CS = nph.ContentClass, nph.ContentStatus


def test_only_active_navigation_selects_the_page():
    h = host(page=False)
    for cls, st in [(CC.NAVIGATION, CS.INACTIVE), (CC.NAVIGATION, CS.UNKNOWN), (CC.OTHER, CS.ACTIVE),
                    (CC.NONE, CS.ACTIVE), (CC.WARNING, CS.INACTIVE)]:
        assert h.observe_contents(cls, st, tick=1) is True
        assert h.page_selected is False
    h.observe_contents(CC.NAVIGATION, CS.ACTIVE, tick=2)
    assert h.page_selected is True and h.acquire(owner()).granted


def test_unknown_status_deselects_instead_of_keeping_the_old_state():
    h = host(page=False)
    h.observe_contents(CC.NAVIGATION, CS.ACTIVE, tick=1)
    lease = h.acquire(owner()).lease
    h.observe_contents(CC.NAVIGATION, CS.UNKNOWN, tick=2)
    assert not lease.valid and not h.page_selected


def test_warning_content_raises_the_interrupt_layer_and_leaving_it_restores_nothing():
    h = host(page=False)
    h.observe_contents(CC.NAVIGATION, CS.ACTIVE, tick=1)
    lease = h.acquire(owner()).lease
    h.present(lease, frame())
    h.observe_contents(CC.WARNING, CS.ACTIVE, tick=2)
    assert h.interrupt_active and not lease.valid and not h.page_selected
    h.observe_contents(CC.WARNING, CS.INACTIVE, tick=3)
    assert not h.interrupt_active and not h.page_selected and h.custom_content_visible is False
    assert h.acquire(owner(gen=2)).status is nph.AcquireStatus.DENIED_PAGE_NOT_SELECTED
    h.observe_contents(CC.NAVIGATION, CS.ACTIVE, tick=4)
    assert h.acquire(owner(gen=2)).granted


def test_a_directly_raised_interrupt_is_not_cleared_by_a_content_observation():
    h = host(page=False)
    h.activate_interrupt()
    h.observe_contents(CC.NAVIGATION, CS.ACTIVE, tick=1)
    assert h.interrupt_active   # we did not raise it, we do not lower it


def test_older_observations_are_ignored():
    h = host(page=False)
    assert h.observe_contents(CC.NAVIGATION, CS.ACTIVE, tick=10)
    assert h.observe_contents(CC.OTHER, CS.ACTIVE, tick=9) is False
    assert h.page_selected is True


def test_silent_host_expires_the_page_and_a_never_reporting_host_never_selects_one():
    h = host(page=False)
    assert h.expire_observation(0, max_age=5) is True and not h.page_selected
    h.observe_contents(CC.NAVIGATION, CS.ACTIVE, tick=10)
    lease = h.acquire(owner()).lease
    assert h.expire_observation(15, max_age=5) is False and lease.valid
    assert h.expire_observation(16, max_age=5) is True
    assert not lease.valid and not h.page_selected


@pytest.mark.parametrize("args", [("NAVIGATION", CS.ACTIVE, 1), (CC.NAVIGATION, "ACTIVE", 1),
                                  (CC.NAVIGATION, CS.ACTIVE, -1), (CC.NAVIGATION, CS.ACTIVE, True)])
def test_malformed_observations_raise(args):
    h = host(page=False)
    with pytest.raises(ValueError):
        h.observe_contents(args[0], args[1], tick=args[2])
    with pytest.raises(ValueError):
        h.expire_observation(-1, max_age=1)
