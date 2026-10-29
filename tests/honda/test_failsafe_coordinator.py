"""CL-INT-03 laboratory acceptance for the disconnect fail-safe.

Offline and synthetic: these tests exercise ``failsafe_coordinator`` against the
``SimulatedClusterHost`` model. They do NOT demonstrate Honda behavior, warning
precedence on a real cluster, or physical safety. Cases marked "no callback"
never call the coordinator after the failure; only the host's own lease decides.
"""
import os
import signal
import socket
import subprocess
import sys
import time

import pytest

import failsafe_coordinator as fsc
from failsafe_coordinator import Fault, LinkState, SubmitResult

LEASE = 1.0


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class Closers:
    """Records closer invocations; ``fail`` names raise to test isolation."""

    def __init__(self, fail=()):
        self.calls = []
        self._fail = set(fail)

    def make(self, *names):
        def build(name):
            def close():
                self.calls.append(name)
                if name in self._fail:
                    raise RuntimeError(name)
            return close
        return {name: build(name) for name in names}


def _setup(clock=None, page=True):
    clock = clock or Clock()
    host = fsc.Display1LeaseHost(lease_seconds=LEASE, clock=clock, epoch=7)
    host.select_page(page)
    coord = fsc.FailSafeCoordinator(host)
    return clock, host, coord


def _stream(coord, closers=None, frames=3):
    coord.phone_attached()
    coord.carplay_started()
    assert coord.type111_negotiated((closers or Closers()).make("stream", "decoder"))
    for i in range(frames):
        assert coord.submit_frame(f"frame{i}") is SubmitResult.ACCEPTED


def _assert_factory_only(host):
    assert host.visible_content is None
    assert host.residual_state == ()
    assert host.lease_held is False


# ---- startup defaults ----
def test_no_phone_at_boot_is_factory_only_and_refuses_everything():
    _, host, coord = _setup()
    assert coord.state is LinkState.FACTORY_ONLY
    assert coord.submit_frame("x") is SubmitResult.REJECTED_NO_LEASE
    assert coord.type111_negotiated() is False
    _assert_factory_only(host)


def test_negotiation_refused_before_carplay_active_releases_acquired_resources():
    _, host, coord = _setup()
    closers = Closers()
    coord.phone_attached()
    assert coord.type111_negotiated(closers.make("stream")) is False
    assert closers.calls == ["stream"]
    assert coord.state is LinkState.PHONE_PRESENT
    _assert_factory_only(host)


# ---- connected behavior ----
def test_content_visible_only_while_page_selected_and_leased():
    _, host, coord = _setup(page=False)
    _stream(coord)
    assert host.visible_content is None  # streaming, page not selected
    host.select_page(True)
    assert host.visible_content == "frame2"
    host.select_page(False)
    assert host.visible_content is None
    assert host.lease_held  # hiding is not revocation; frames still owned


def test_normal_session_end_withdraws_everything():
    _, host, coord = _setup()
    closers = Closers()
    _stream(coord, closers)
    report = coord.fault(Fault.CARPLAY_ENDED)
    assert coord.state is LinkState.PHONE_PRESENT
    assert closers.calls == ["decoder", "stream"]  # reverse acquisition order
    assert report.failed == ()
    _assert_factory_only(host)


# ---- failure matrix: with a coordinator callback ----
@pytest.mark.parametrize("fault,expected_state", [
    (Fault.USB_UNPLUG, LinkState.FACTORY_ONLY),
    (Fault.RECEIVER_DEATH, LinkState.FACTORY_ONLY),
    (Fault.CARPLAY_ENDED, LinkState.PHONE_PRESENT),
    (Fault.TYPE111_TRANSPORT_FAILURE, LinkState.CARPLAY_ACTIVE),
    (Fault.DECODER_DEATH, LinkState.CARPLAY_ACTIVE),
    (Fault.DISPLAY_HOST_RESTART, LinkState.CARPLAY_ACTIVE),
    (Fault.INIT_FAILURE, LinkState.CARPLAY_ACTIVE),
    (Fault.FACTORY_WARNING, LinkState.CARPLAY_ACTIVE),
])
def test_every_fault_leaves_no_custom_content_or_residue(fault, expected_state):
    _, host, coord = _setup()
    _stream(coord)
    coord.fault(fault)
    assert coord.state is expected_state
    _assert_factory_only(host)
    assert coord.submit_frame("late") is SubmitResult.REJECTED_NO_LEASE


def test_one_failing_closer_does_not_block_other_cleanup():
    _, host, coord = _setup()
    closers = Closers(fail={"decoder"})
    _stream(coord, closers)
    report = coord.fault(Fault.USB_UNPLUG)
    assert closers.calls == ["decoder", "stream"]
    assert report.failed == ("decoder",) and report.ran == ("stream",)
    _assert_factory_only(host)  # visible content gone regardless


def test_repeated_faults_are_idempotent():
    _, host, coord = _setup()
    closers = Closers()
    _stream(coord, closers)
    coord.fault(Fault.USB_UNPLUG)
    coord.fault(Fault.USB_UNPLUG)
    assert closers.calls == ["decoder", "stream"]  # not closed twice
    _assert_factory_only(host)


def test_failure_during_initialization_grant_refused_cleans_up():
    _, host, coord = _setup()
    coord.phone_attached(); coord.carplay_started()
    host.activate_interrupt()  # factory interrupt already showing
    closers = Closers()
    assert coord.type111_negotiated(closers.make("stream")) is False
    assert closers.calls == ["stream"]
    assert coord.state is LinkState.CARPLAY_ACTIVE
    _assert_factory_only(host)


# ---- no callback: the host fence alone must restore factory-only output ----
def test_no_callback_silent_stream_stop_expires_lease():
    clock, host, coord = _setup()
    _stream(coord)
    assert host.visible_content == "frame2"
    clock.advance(LEASE - 0.01)
    assert host.visible_content == "frame2"  # still inside the lease
    clock.advance(0.02)
    _assert_factory_only(host)  # no tick, no disconnect callback, nothing called
    assert host.revocations[-1] == "lease expired"


def test_no_callback_coordinator_adopts_host_revocation_and_cleans_up_later():
    clock, host, coord = _setup()
    closers = Closers()
    _stream(coord, closers)
    clock.advance(LEASE + 0.1)
    assert coord.heartbeat() is False  # discovers the loss
    assert coord.state is LinkState.CARPLAY_ACTIVE
    assert closers.calls == ["decoder", "stream"]
    _assert_factory_only(host)


def test_heartbeats_cannot_extend_a_revoked_lease():
    clock, host, coord = _setup()
    _stream(coord)
    clock.advance(LEASE + 0.1)
    assert coord.heartbeat() is False
    assert coord.heartbeat() is False
    _assert_factory_only(host)


def test_heartbeats_alone_cannot_hold_a_frozen_frame():
    """A hung decoder with a live heartbeat thread must not freeze the last frame."""
    clock, host, coord = _setup()
    _stream(coord)
    clock.advance(LEASE * 0.6)
    assert coord.heartbeat() is True   # within the frame-age limit
    clock.advance(LEASE * 0.6)
    assert coord.heartbeat() is True
    assert host.visible_content == "frame2"
    clock.advance(LEASE * 0.6)         # 1.8 leases since the last frame
    assert coord.heartbeat() is True
    clock.advance(LEASE * 0.6)         # 2.4 leases: past the frame-age limit
    assert coord.heartbeat() is False
    assert host.revocations[-1] == "no frame progress"
    _assert_factory_only(host)


def test_frames_with_heartbeats_keep_the_lease_alive_indefinitely():
    clock, host, coord = _setup()
    _stream(coord)
    for i in range(20):
        clock.advance(LEASE * 0.6)
        assert coord.heartbeat() is True
        assert coord.submit_frame(f"n{i}") is SubmitResult.ACCEPTED
    assert host.visible_content == "n19"


# ---- stale frame rejection and ownership transfer ----
def test_stale_generation_frames_rejected_after_ownership_transfer():
    _, host, coord = _setup()
    _stream(coord)
    old = coord._lease
    assert coord.type111_negotiated(Closers().make("stream2"))
    assert host.submit(old, 99, "stale") is SubmitResult.REJECTED_STALE_GENERATION
    assert host.visible_content is None  # nothing from the old generation survives
    assert coord.submit_frame("new") is SubmitResult.ACCEPTED
    assert host.visible_content == "new"


def test_transfer_runs_old_generation_cleanup_before_new_owns_display():
    _, host, coord = _setup()
    closers = Closers()
    _stream(coord, closers)
    coord.type111_negotiated(Closers().make("stream2"))
    assert closers.calls == ["decoder", "stream"]


def test_out_of_order_and_replayed_sequence_rejected():
    _, host, coord = _setup()
    coord.phone_attached(); coord.carplay_started(); coord.type111_negotiated()
    lease = coord._lease
    assert host.submit(lease, 5, "a") is SubmitResult.ACCEPTED
    assert host.submit(lease, 5, "replay") is SubmitResult.REJECTED_OUT_OF_ORDER
    assert host.submit(lease, 4, "older") is SubmitResult.REJECTED_OUT_OF_ORDER
    assert host.visible_content == "a"


def test_token_from_previous_host_epoch_rejected_after_restart():
    clock = Clock()
    _, _, old_coord = _setup(clock)
    _stream(old_coord)
    stale = old_coord._lease
    # Incomplete teardown, then the head unit restarts: a new host epoch.
    new_host = fsc.Display1LeaseHost(lease_seconds=LEASE, clock=clock, epoch=8)
    new_host.select_page(True)
    _assert_factory_only(new_host)
    assert new_host.submit(stale, 0, "ghost") is SubmitResult.REJECTED_NO_LEASE
    new_coord = fsc.FailSafeCoordinator(new_host)
    new_coord.phone_attached(); new_coord.carplay_started(); new_coord.type111_negotiated()
    assert new_host.submit(stale, 0, "ghost") is SubmitResult.REJECTED_EPOCH
    assert new_host.visible_content is None


def test_host_refuses_to_regrant_a_spent_or_lower_generation():
    """The host enforces monotonic generations itself, not only its caller."""
    host = fsc.Display1LeaseHost(lease_seconds=LEASE, clock=Clock(), epoch=7)
    result, lease = host.grant(5)
    assert result is fsc.GrantResult.GRANTED and lease.generation == 5
    host.revoke("test")
    for spent in (5, 4, 1):
        result, lease = host.grant(spent)
        assert result is fsc.GrantResult.REJECTED_STALE_GENERATION and lease is None
    assert host.grant(6)[0] is fsc.GrantResult.GRANTED


def test_late_fault_callbacks_cannot_raise_state_or_reopen_the_gate():
    """A duplicate decoder/transport callback after unplug must not promote state."""
    _, host, coord = _setup()
    _stream(coord)
    coord.fault(Fault.USB_UNPLUG)
    assert coord.state is LinkState.FACTORY_ONLY
    for late in (Fault.DECODER_DEATH, Fault.TYPE111_TRANSPORT_FAILURE, Fault.INIT_FAILURE,
                 Fault.DISPLAY_HOST_RESTART, Fault.FACTORY_WARNING, Fault.CARPLAY_ENDED):
        coord.fault(late)
        assert coord.state is LinkState.FACTORY_ONLY
    host.clear_interrupt()
    assert coord.type111_negotiated(Closers().make("s")) is False
    assert coord.submit_frame("x") is SubmitResult.REJECTED_NO_LEASE
    _assert_factory_only(host)


@pytest.mark.parametrize("bad", [float("nan"), 1.5, True, -1, "1", None])
def test_host_rejects_non_integer_generation_and_sequence(bad):
    host = fsc.Display1LeaseHost(lease_seconds=LEASE, clock=Clock(), epoch=7)
    with pytest.raises(ValueError):
        host.grant(bad)
    _, lease = host.grant(3)
    with pytest.raises(ValueError):
        host.submit(lease, bad, "x")
    # monotonicity still intact after the rejected inputs
    assert host.submit(lease, 0, "ok") is SubmitResult.ACCEPTED
    host.revoke("t")
    assert host.grant(3)[0] is fsc.GrantResult.REJECTED_STALE_GENERATION


def test_content_is_withdrawn_before_any_project_closer_runs():
    """Revoke-first ordering: closers observe an already factory-only host."""
    for fault in (Fault.USB_UNPLUG, Fault.DECODER_DEATH, Fault.FACTORY_WARNING):
        _, host, coord = _setup()
        coord.phone_attached(); coord.carplay_started()
        seen = []

        def observing(name, raises=False):
            def close():
                seen.append((name, host.visible_content, host.lease_held, host.residual_state))
                if raises:
                    raise RuntimeError(name)
            return close

        coord.type111_negotiated({"first": observing("first"), "second": observing("second", True)})
        coord.submit_frame("visible")
        assert host.visible_content == "visible"
        coord.fault(fault)
        assert [name for name, *_ in seen] == ["second", "first"]
        assert all(v is None and held is False and res == () for _, v, held, res in seen)


# ---- factory interrupt / warning ----
def test_warning_withdraws_and_clearing_does_not_reexpose_content():
    _, host, coord = _setup()
    _stream(coord)
    coord.fault(Fault.FACTORY_WARNING)
    host.clear_interrupt()
    assert host.visible_content is None  # never auto-restored
    assert coord.type111_negotiated(Closers().make("s")) is True  # explicit re-grant
    assert coord.submit_frame("fresh") is SubmitResult.ACCEPTED


def test_frames_rejected_while_interrupt_active():
    _, host, coord = _setup()
    coord.phone_attached(); coord.carplay_started(); coord.type111_negotiated()
    lease = coord._lease
    host.activate_interrupt()
    assert host.submit(lease, 0, "x") is SubmitResult.REJECTED_NO_LEASE
    _assert_factory_only(host)


def test_display_host_restart_drops_lease_and_requires_new_generation():
    _, host, coord = _setup()
    _stream(coord)
    old = coord._lease
    coord.fault(Fault.DISPLAY_HOST_RESTART)
    assert host.submit(old, 50, "ghost") is SubmitResult.REJECTED_NO_LEASE
    assert coord.type111_negotiated(Closers().make("s"))
    assert coord._lease.generation > old.generation


# ---- repeated connect/disconnect ----
def test_repeated_connect_disconnect_cycles_leave_no_residue():
    _, host, coord = _setup()
    seen = []
    for cycle in range(50):
        _stream(coord, frames=2)
        seen.append(coord._lease.generation)
        fault = Fault.USB_UNPLUG if cycle % 2 else Fault.CARPLAY_ENDED
        coord.fault(fault)
        _assert_factory_only(host)
        if fault is Fault.USB_UNPLUG:
            assert coord.state is LinkState.FACTORY_ONLY
    assert seen == sorted(set(seen))  # strictly increasing, never reused
    assert len(host.revocations) == 50


def test_rapid_reconnect_old_stream_cannot_write_into_new_session():
    _, host, coord = _setup()
    _stream(coord)
    old = coord._lease
    coord.fault(Fault.USB_UNPLUG)
    coord.phone_attached(); coord.carplay_started()
    assert coord.type111_negotiated(Closers().make("s2"))
    assert host.submit(old, 0, "zombie") is SubmitResult.REJECTED_STALE_GENERATION
    assert host.visible_content is None


# ---- real process death (no callback of any kind) ----
_PRODUCER = (
    "import socket, sys, time\n"
    "s = socket.socket(fileno=int(sys.argv[1]))\n"
    "while True:\n"
    "    s.send(b'F'); time.sleep(0.02)\n"
)


def test_real_producer_process_sigkill_ends_in_factory_only_by_lease_alone():
    """SIGKILL a real producer process, then never read its socket or call the
    coordinator. Shows lazy lease expiry on the real clock clears content with no
    disconnect event. It does not show the host *reacting* to the death; the
    producer is a stand-in, not Honda's receiver."""
    parent_sock, child_sock = socket.socketpair()
    child = subprocess.Popen(
        [sys.executable, "-I", "-c", _PRODUCER, str(child_sock.fileno())],
        pass_fds=(child_sock.fileno(),),
    )
    child_sock.close()
    lease = 1.0
    try:
        parent_sock.settimeout(10.0)
        assert parent_sock.recv(1)  # child is up and producing before any lease exists
        host = fsc.Display1LeaseHost(lease_seconds=lease)
        host.select_page(True)
        coord = fsc.FailSafeCoordinator(host)
        coord.phone_attached(); coord.carplay_started()
        closers = Closers()
        assert coord.type111_negotiated(closers.make("stream"))
        frames = 0
        while frames < 5:
            data = parent_sock.recv(1)
            assert data, "producer exited early"
            assert coord.submit_frame(f"f{frames}") is SubmitResult.ACCEPTED
            frames += 1
        assert host.visible_content == "f4"
        killed_at = time.monotonic()
        os.kill(child.pid, signal.SIGKILL)
        child.wait(timeout=10)
        deadline = killed_at + lease + 5.0  # generous bound; exactness is checked by fake-clock tests
        while host.visible_content is not None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert host.visible_content is None
        assert closers.calls == []  # project closers have NOT run: host fenced alone
        coord.sync()  # a surviving coordinator later adopts the revocation
        assert closers.calls == ["stream"]
        _assert_factory_only(host)
    finally:
        parent_sock.close()
        if child.poll() is None:
            child.kill()
            child.wait()
