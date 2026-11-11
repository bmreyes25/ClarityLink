"""CL-HONDA-111-01: Type111 child stream -> simulated Navigation pane.

End-to-end synthetic integration of the parent-owned child authority, the
bounded frame path and the simulated pane host, beside an untouched Type110
frame gate. Uses generated frames only: no protected media, no Honda IPC, no
factory window attachment. A pass proves ClarityLink's own contract, nothing
about the real Honda receiver or cluster. ``safe_for_honda()`` stays False.

Scenario numbers follow section E3 of the campaign brief.
"""
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in ("claritylink-honda", "claritylink-transport", "claritylink-negotiation"):
    sys.path.insert(0, str(ROOT / "src" / p))

import frame_gate as fg  # noqa: E402
import factory_integration_contract as fic  # noqa: E402
import navigation_pane_host as nph  # noqa: E402
import type111_child_authority as tca  # noqa: E402
import type111_pane_bridge as tpb  # noqa: E402

VP = nph.Viewport(0, 0, 400, 200, nph.ViewportSource.SYNTHETIC_TEST)
SID = 0x1111


class Rig:
    def __init__(self, *, capacity=2, page=True, viewport=VP):
        self.parent = tca.ParentAuthority()
        self.host = nph.NavigationPaneHost()
        self.host.connect_display()
        self.host.select_navigation_page(page)
        if viewport is not None:
            self.host.set_viewport(viewport)
        self.bridge = tpb.Type111PaneBridge(self.parent, self.host, capacity=capacity)
        self.type110 = fg.FrameGate(capacity=4)
        self.type110.begin_generation(1)
        self._t110_seq = 0
        self.releases = 0
        self.sent = []
        self._seq = 0

    # --- Type110 witness: independent gate the bridge cannot name ---
    def t110_frame(self):
        self._t110_seq += 1
        return self.type110.offer(fg.Frame(1, self._t110_seq, self._t110_seq, b"t110-video"))

    def t110_snapshot(self):
        s = self.type110.stats
        return (self.type110.generation, self.type110.closed, s.accepted, s.closed_refusals)

    # --- Type111 frames ---
    def frame(self, *, seq=None, w=64, h=32, **kw):
        if seq is None:
            self._seq += 1
            seq = self._seq
        ident = self.bridge.child.identity
        fields = dict(stream_connection_id=ident.stream_connection_id,
                      parent_generation=ident.parent_generation,
                      stream_generation=ident.stream_generation,
                      config_generation=self.bridge.config_generation,
                      sequence=seq, presentation_time_ns=seq * 1000, width=w, height=h,
                      stride=w * 4, payload=bytes(w * 4 * h),
                      release_callback=self._on_release)
        fields.update(kw)
        return nph.DecodedFrame(**fields)

    def _on_release(self):
        self.releases += 1

    def start(self, sid=SID, config=(64, 32)):
        status = self.bridge.start(sid)
        if config and self.bridge.child is not None and self.bridge.child.live:
            self.bridge.video_config(*config)
        return status

    def send(self, **kw):
        f = self.frame(**kw)
        self.sent.append(f)
        return f, self.bridge.offer(f)

    def show(self, **kw):
        f, status = self.send(**kw)
        assert status is tpb.OfferStatus.ACCEPTED, status
        return self.bridge.pump()


# ---- 1. Type110 remains active throughout ----
def test_type110_stays_active_across_the_whole_type111_lifecycle():
    r = Rig()
    assert r.t110_frame() is fg.FrameStatus.ACCEPTED
    before = r.t110_snapshot()
    assert r.start() is nph.AcquireStatus.GRANTED
    assert r.show().presented
    r.host.activate_interrupt()
    r.host.clear_interrupt()
    assert r.bridge.resume() is nph.AcquireStatus.GRANTED
    r.bridge.stop()
    r.parent.lose()
    after = r.t110_snapshot()
    assert after[:2] == before[:2] and after[3] == before[3]
    assert r.t110_frame() is fg.FrameStatus.ACCEPTED


# ---- 2, 3, 4. Type111 begins, config accepted, decoded frames reach the pane ----
def test_type111_begins_config_is_accepted_and_frames_reach_the_pane():
    r = Rig()
    assert r.start(config=None) is nph.AcquireStatus.GRANTED
    assert r.bridge.state is tpb.BridgeState.STREAMING
    f, status = r.send()
    assert status is tpb.OfferStatus.REJECTED_NO_CONFIG and f._released
    assert r.bridge.video_config(64, 32) == 1
    result = r.show()
    assert result.presented and r.host.custom_content_visible
    seq, dest, pane_gen = r.host.presented
    assert seq == 2 and pane_gen == r.bridge.pane_generation   # sequence 1 was the pre-config rejection
    assert 0 <= dest[0] and dest[0] + dest[2] <= 400 and dest[1] + dest[3] <= 200


def test_video_config_replacement_opens_a_new_generation_and_drops_old_frames():
    r = Rig()
    r.start()
    f_old, status = r.send()
    assert status is tpb.OfferStatus.ACCEPTED
    assert r.bridge.video_config(128, 64) == 2
    assert f_old._released and r.bridge.queue_depth == 0   # queued under the old config
    stale = r.frame(config_generation=1, w=128, h=64)
    assert r.bridge.offer(stale) is tpb.OfferStatus.REJECTED_STALE_CONFIG and stale._released
    assert r.show(w=128, h=64).presented
    # an identical config is not a new generation
    assert r.bridge.video_config(128, 64) == 2


@pytest.mark.parametrize("bad", [(0, 10), (10, 0), (-1, 5), (nph.MAX_WIDTH + 1, 5), (5, nph.MAX_HEIGHT + 1), (True, 5), (5.0, 5)])
def test_invalid_video_config_is_rejected(bad):
    r = Rig()
    r.start(config=None)
    with pytest.raises(ValueError):
        r.bridge.video_config(*bad)


def test_video_config_needs_a_live_child():
    r = Rig()
    with pytest.raises(tca.AuthorityError):
        r.bridge.video_config(10, 10)


# ---- 5, 6. Navigation page deselect withdraws; reselect needs valid current ownership ----
def test_page_deselect_withdraws_and_reselect_requires_explicit_fresh_ownership():
    r = Rig()
    r.start()
    assert r.show().presented
    f_q, _ = r.send()   # buffered, not yet pumped
    r.host.select_navigation_page(False)
    assert r.bridge.state is tpb.BridgeState.WITHDRAWN
    assert r.bridge.withdraw_reason == "page_deselected"
    assert f_q._released and r.bridge.queue_depth == 0
    f2, status = r.send()
    assert status is tpb.OfferStatus.REJECTED_NOT_STREAMING and f2._released
    first_gen = r.bridge.pane_generation
    # page returns: still nothing until the bridge re-acquires with a fresh generation
    r.host.select_navigation_page(True)
    assert r.host.custom_content_visible is False and r.host.lease is None
    assert r.bridge.resume() is nph.AcquireStatus.GRANTED
    assert r.bridge.pane_generation > first_gen
    assert r.show().presented


def test_resume_while_page_is_still_away_stays_pending_without_a_lease():
    r = Rig()
    r.start()
    r.host.select_navigation_page(False)
    assert r.bridge.resume() is nph.AcquireStatus.DENIED_PAGE_NOT_SELECTED
    assert r.bridge.state is tpb.BridgeState.WITHDRAWN
    assert r.host.custom_content_visible is False


def test_starting_while_the_page_is_not_selected_waits_without_presenting():
    r = Rig(page=False)
    assert r.start() is nph.AcquireStatus.DENIED_PAGE_NOT_SELECTED
    assert r.bridge.state is tpb.BridgeState.PENDING_PANE
    f, status = r.send()
    assert status is tpb.OfferStatus.REJECTED_NOT_STREAMING and f._released
    r.host.select_navigation_page(True)
    assert r.bridge.resume() is nph.AcquireStatus.GRANTED
    assert r.show().presented


# ---- 7, 8. Warning withdraws; warning removal does not revive stale content ----
def test_warning_withdraws_and_clearing_it_never_revives_old_content():
    r = Rig()
    r.start()
    assert r.show().presented
    last_seq = r.host.presented[0]
    r.host.activate_interrupt()
    assert r.bridge.state is tpb.BridgeState.WITHDRAWN and r.bridge.withdraw_reason == "interrupt"
    assert r.host.custom_content_visible is False
    r.host.clear_interrupt()
    assert r.host.custom_content_visible is False and r.host.presented is None
    assert r.bridge.state is tpb.BridgeState.WITHDRAWN   # no automatic comeback
    assert r.bridge.pump() is None
    assert r.bridge.resume() is nph.AcquireStatus.GRANTED
    # a replay of an already-presented sequence is refused; a newer one shows
    stale = r.frame(seq=last_seq)
    assert r.bridge.offer(stale) is tpb.OfferStatus.REJECTED_ORDER and stale._released
    assert r.show(seq=last_seq + 5).presented


def test_start_is_refused_by_the_host_during_an_active_warning():
    r = Rig()
    r.host.activate_interrupt()
    assert r.start() is nph.AcquireStatus.DENIED_INTERRUPTED
    assert r.host.custom_content_visible is False


# ---- 9, 10. Host loss clears resources; recovery needs a fresh generation ----
def test_host_loss_releases_every_retained_frame_and_recovery_needs_fresh_generation():
    r = Rig(capacity=4)
    r.start()
    r.show()
    for _ in range(3):
        assert r.send()[1] is tpb.OfferStatus.ACCEPTED
    old_gen = r.bridge.pane_generation
    r.host.lose_display()
    assert r.bridge.state is tpb.BridgeState.WITHDRAWN and r.bridge.queue_depth == 0
    assert r.releases == r.bridge.stats.offered   # nothing retained
    assert r.bridge.resume() is nph.AcquireStatus.DENIED_NO_DISPLAY
    r.host.begin_restore()
    assert r.host.complete_restore(display_valid=True)
    assert r.bridge.resume() is nph.AcquireStatus.GRANTED
    assert r.bridge.pane_generation > old_gen
    assert r.show().presented


def test_invalid_display_never_rebuilds_the_pane():
    r = Rig()
    r.start()
    r.host.lose_display()
    r.host.begin_restore()
    assert r.host.complete_restore(display_valid=False) is False
    assert r.bridge.resume() is nph.AcquireStatus.DENIED_NO_DISPLAY
    assert r.host.custom_content_visible is False


# ---- 11. Type111 disconnect leaves Type110 working ----
def test_type111_disconnect_leaves_type110_working_and_restores_factory_content():
    r = Rig()
    r.t110_frame()
    r.start()
    r.show()
    r.bridge.stop()
    assert r.bridge.state is tpb.BridgeState.CLOSED and r.bridge.end_reason in ("stopped", "CLOSED", "closed")
    assert r.host.factory_content_visible and r.host.lease is None
    assert r.t110_frame() is fg.FrameStatus.ACCEPTED and not r.type110.closed
    f, status = r.send()
    assert status is tpb.OfferStatus.REJECTED_CHILD_ENDED and f._released
    assert r.parent.live_child is None


# ---- 12. Parent session loss revokes all children ----
def test_parent_loss_revokes_child_pane_and_blocks_restart():
    r = Rig(capacity=4)
    r.start()
    r.show()
    r.send()
    child = r.bridge.child
    r.parent.lose()
    assert not child.live and r.bridge.state is tpb.BridgeState.CLOSED
    assert r.bridge.end_reason == "parent_lost"
    assert r.host.custom_content_visible is False and r.host.lease is None and r.host.factory_content_visible
    assert r.bridge.queue_depth == 0 and r.releases == r.bridge.stats.offered
    with pytest.raises(tca.AuthorityError) as e:
        r.bridge.start(SID)
    assert e.value.code == "parent_lost"
    assert r.bridge.resume() is None
    f = nph.DecodedFrame(SID, 1, 1, 1, 9, 9, 8, 8, 32, payload=bytes(256))
    assert r.bridge.offer(f) is tpb.OfferStatus.REJECTED_CHILD_ENDED


def test_a_child_replaced_by_a_new_start_cannot_reuse_the_old_frames_identity():
    r = Rig()
    r.start(sid=0xAAAA)
    old_frame = r.frame()
    r.bridge.stop()
    assert r.start(sid=0xBBBB) is nph.AcquireStatus.GRANTED
    assert r.bridge.offer(old_frame) is tpb.OfferStatus.REJECTED_IDENTITY and old_frame._released
    assert r.show().presented


# ---- 13. Invalid geometry rejects presentation ----
def test_missing_or_inadmissible_viewport_blocks_the_pane():
    r = Rig(viewport=None)
    assert r.start() is nph.AcquireStatus.DENIED_NO_VIEWPORT
    local = nph.Viewport(0, 24, 584, 191, nph.ViewportSource.LAYOUT_LOCAL_CANDIDATE)
    assert r.host.set_viewport(local) is False
    assert r.bridge.resume() is nph.AcquireStatus.DENIED_NO_VIEWPORT
    assert r.host.custom_content_visible is False
    assert r.host.set_viewport(VP)
    assert r.bridge.resume() is nph.AcquireStatus.GRANTED
    assert r.show().presented


def test_changing_the_viewport_mid_stream_withdraws_instead_of_stretching():
    r = Rig()
    r.start()
    r.show()
    r.host.set_viewport(nph.Viewport(5, 5, 100, 50, nph.ViewportSource.SYNTHETIC_TEST))
    assert r.bridge.state is tpb.BridgeState.WITHDRAWN and r.bridge.withdraw_reason == "viewport_changed"
    assert r.host.custom_content_visible is False


# ---- 14. Malformed frames are rejected and always released ----
@pytest.mark.parametrize("override,expected", [
    (dict(stride=4), tpb.OfferStatus.REJECTED_MALFORMED),
    (dict(payload=b"x"), tpb.OfferStatus.REJECTED_MALFORMED),
    (dict(rotation=45), tpb.OfferStatus.REJECTED_MALFORMED),
    (dict(crop=(0, 0, 999, 999)), tpb.OfferStatus.REJECTED_MALFORMED),
    (dict(storage=nph.FrameStorage.SURFACE), tpb.OfferStatus.REJECTED_UNSUPPORTED_STORAGE),
    (dict(stream_connection_id=0xFEED), tpb.OfferStatus.REJECTED_IDENTITY),
    (dict(parent_generation=99), tpb.OfferStatus.REJECTED_IDENTITY),
    (dict(stream_generation=99), tpb.OfferStatus.REJECTED_IDENTITY),
    (dict(config_generation=9), tpb.OfferStatus.REJECTED_STALE_CONFIG),
])
def test_malformed_or_foreign_frames_are_rejected_and_released(override, expected):
    r = Rig()
    r.start()
    f, status = r.send(**override)
    assert status is expected and f._released
    assert r.bridge.queue_depth == 0 and r.host.presented is None
    assert r.bridge.state is tpb.BridgeState.STREAMING   # bad input does not kill a good stream


def test_non_frame_input_is_rejected_without_error():
    r = Rig()
    r.start()
    assert r.bridge.offer(b"not a frame") is tpb.OfferStatus.REJECTED_MALFORMED


def test_type110_identity_frames_are_never_mixed_into_the_pane():
    r = Rig()
    r.start()
    t110_like = r.frame(stream_connection_id=0x110, payload=bytes(64 * 32 * 4))
    assert r.bridge.offer(t110_like) is tpb.OfferStatus.REJECTED_IDENTITY
    assert r.host.presented is None


# ---- bounded queue, ordering and freshness ----
def test_queue_is_bounded_oldest_dropped_and_only_the_freshest_is_presented():
    r = Rig(capacity=2)
    r.start()
    frames = []
    for _ in range(10):
        f, status = r.send()
        assert status is tpb.OfferStatus.ACCEPTED
        frames.append(f)
        assert r.bridge.queue_depth <= 2
    assert r.bridge.stats.dropped_oldest == 8
    result = r.bridge.pump()
    assert result.presented and r.host.presented[0] == 10
    assert all(f._released for f in frames)
    assert r.bridge.stats.released == 10 and r.bridge.queue_depth == 0


def test_duplicate_and_out_of_order_frames_are_rejected():
    r = Rig()
    r.start()
    assert r.show(seq=10).presented
    for seq in (10, 9, 1):
        f, status = r.send(seq=seq)
        assert status is tpb.OfferStatus.REJECTED_ORDER and f._released
    assert r.show(seq=11).presented


def test_pump_with_nothing_queued_is_a_no_op():
    r = Rig()
    r.start()
    assert r.bridge.pump() is None


# ---- 15. Full teardown restores simulated factory content ----
def test_full_teardown_restores_simulated_factory_content_and_leaves_nothing_behind():
    r = Rig(capacity=4)
    r.t110_frame()
    r.start()
    r.show()
    for _ in range(3):
        r.send()
    r.bridge.stop()
    assert r.host.factory_content_visible and not r.host.custom_content_visible
    assert r.host.lease is None and r.host.presented is None
    assert r.parent.live_child is None
    assert r.bridge.queue_depth == 0
    assert r.releases == r.bridge.stats.offered
    r.bridge.stop()   # idempotent
    assert r.t110_frame() is fg.FrameStatus.ACCEPTED


# ---- real-facing path stays closed ----
def test_factory_facing_sink_always_denies_and_the_bridge_never_presents():
    parent = tca.ParentAuthority()
    bridge = tpb.Type111PaneBridge(parent, tpb.FactorySinkAdapter())
    status = bridge.start(SID)
    assert status is nph.AcquireStatus.DENIED_NOT_ADMISSIBLE
    assert bridge.state is tpb.BridgeState.PENDING_PANE
    assert bridge.pump() is None
    assert bridge.resume() is nph.AcquireStatus.DENIED_NOT_ADMISSIBLE
    contract = fic.default_fail_closed_contract()
    assert contract.safe_for_honda() is False
    assert contract.submit_frame_to_factory(evidence_tier=fic.EvidenceTier.SYNTHETIC).allowed is False


def test_factory_sink_denies_a_direct_present_too():
    sink = tpb.FactorySinkAdapter()
    f = nph.DecodedFrame(1, 1, 1, 1, 1, 1, 4, 4, 16, payload=bytes(64))
    assert sink.present(None, f).presented is False
    sink.withdraw(None)   # safe direction never raises


# ---- bridge misuse ----
def test_start_twice_is_refused_and_bad_capacity_is_rejected():
    r = Rig()
    r.start()
    with pytest.raises(tca.AuthorityError):
        r.bridge.start(0x2222)
    for bad in (0, tpb.MAX_QUEUE + 1, True, "2"):
        with pytest.raises(ValueError):
            tpb.Type111PaneBridge(r.parent, r.host, capacity=bad)


def test_restart_after_a_clean_stop_gets_a_fresh_child_and_pane_generation():
    r = Rig()
    r.start()
    child1, pane1 = r.bridge.child, r.bridge.pane_generation
    r.show()
    r.bridge.stop()
    assert r.start(sid=0x3333) is nph.AcquireStatus.GRANTED
    assert r.bridge.child is not child1
    assert r.bridge.child.identity.stream_generation > child1.identity.stream_generation
    assert r.bridge.pane_generation > pane1
    assert r.show().presented


# ---- repeated cycles keep resources bounded ----
def test_repeated_failure_cycles_leave_no_leases_children_or_frames():
    r = Rig(capacity=3)
    causes = [
        lambda: r.host.activate_interrupt(),
        lambda: r.host.select_navigation_page(False),
        lambda: r.host.lose_display(),
        lambda: r.bridge.stop(),
        lambda: r.parent.lose(),
    ]
    sid = 0x4000
    for i in range(60):
        if r.parent.state is tca.ParentState.LOST:
            r.parent = tca.ParentAuthority(generation=r.parent.generation + 1)
            r.bridge = tpb.Type111PaneBridge(r.parent, r.host, capacity=3)
        r.host.select_navigation_page(True)
        if not r.host.display_available:
            r.host.begin_restore()
            r.host.complete_restore(display_valid=True)
        r.host.clear_interrupt()
        sid += 1
        if r.bridge.state not in (tpb.BridgeState.IDLE, tpb.BridgeState.CLOSED):
            r.bridge.stop()
        assert r.start(sid=sid) is nph.AcquireStatus.GRANTED, i
        r._seq = 0
        for _ in range(5):
            r.send()
        r.bridge.pump()
        causes[i % len(causes)]()
        assert r.bridge.queue_depth == 0
    r.bridge.stop()
    assert r.host.lease is None and r.parent.live_child is None
    assert all(f._released for f in r.sent)
    assert r.releases == len(r.sent)   # one release per offered frame across every cycle
    r.host.close()
    assert r.host.lease is None


def test_every_offered_frame_is_released_exactly_once_across_mixed_outcomes():
    r = Rig(capacity=2)
    r.start()
    offered = []
    for i in range(30):
        kw = {}
        if i % 7 == 3:
            kw = dict(stride=1)          # malformed
        if i % 11 == 5:
            kw = dict(config_generation=9)   # stale config
        f, _ = r.send(**kw)
        offered.append(f)
        if i % 4 == 0:
            r.bridge.pump()
        if i == 15:
            r.host.activate_interrupt()
    r.bridge.stop()
    assert all(f._released for f in offered)
    assert r.releases == len(offered)   # callback ran once per frame, never twice


# ---- concurrency smoke ----
def test_concurrent_offers_while_the_pane_is_revoked_never_leak_or_raise():
    r = Rig(capacity=4)
    r.start()
    errors, frames = [], []
    flock = threading.Lock()
    stop = threading.Event()

    def producer():
        seq = 0
        try:
            while not stop.is_set():
                seq += 1
                f = nph.DecodedFrame(SID, 1, r.bridge.child.identity.stream_generation,
                                     r.bridge.config_generation, seq, seq, 16, 16, 64,
                                     payload=bytes(1024), release_callback=r._on_release)
                with flock:
                    frames.append(f)
                r.bridge.offer(f)
                r.bridge.pump()
        except Exception as exc:   # pragma: no cover - failure path
            errors.append(exc)

    threads = [threading.Thread(target=producer) for _ in range(3)]
    for t in threads:
        t.start()
    for _ in range(40):
        r.host.activate_interrupt()
        r.host.clear_interrupt()
        r.bridge.resume()
    stop.set()
    for t in threads:
        t.join(timeout=10)
    r.bridge.stop()
    assert not errors
    assert all(f._released for f in frames)
    assert r.releases == len(frames)


# ---- page driven by the host's reported selection, end to end ----
def test_reported_selection_drives_the_bridge_through_page_warning_and_return():
    r = Rig(page=False)
    CC, CS = nph.ContentClass, nph.ContentStatus
    assert r.start() is nph.AcquireStatus.DENIED_PAGE_NOT_SELECTED
    r.host.observe_contents(CC.NAVIGATION, CS.ACTIVE, tick=1)
    assert r.bridge.resume() is nph.AcquireStatus.GRANTED
    assert r.show().presented
    r.host.observe_contents(CC.WARNING, CS.ACTIVE, tick=2)
    assert r.bridge.state is tpb.BridgeState.WITHDRAWN and r.host.custom_content_visible is False
    r.host.observe_contents(CC.WARNING, CS.INACTIVE, tick=3)
    assert r.bridge.resume() is nph.AcquireStatus.DENIED_PAGE_NOT_SELECTED
    r.host.observe_contents(CC.NAVIGATION, CS.ACTIVE, tick=4)
    assert r.bridge.resume() is nph.AcquireStatus.GRANTED
    assert r.show().presented
    assert r.host.expire_observation(100, max_age=10) is True
    assert r.bridge.state is tpb.BridgeState.WITHDRAWN and r.bridge.withdraw_reason == "page_deselected"
