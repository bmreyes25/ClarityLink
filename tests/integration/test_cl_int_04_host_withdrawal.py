"""CL-INT-04: autonomous host-owned Display 1 withdrawal, across real process boundaries.

Evidence scope: SYNTHETIC lifecycle only. A host process owns the lease and its expiry
timer; producer processes are separate OS processes that are exited, SIGKILLed or left
silent. Nothing here is Honda, iPhone-origin video or physical Display 1 evidence.
"""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

import t111_synth as synth
from display1_host_ipc import Display1HostServer, HostIpcError, RemoteDisplay1Host
from display1_host_service import Display1HostService
from failsafe_coordinator import (Display1LeaseHost, Fault, FailSafeCoordinator, GrantResult,
                                  LeaseGrant, SubmitResult)
from type111_ingest import Type111IngestPipeline

ROOT = Path(__file__).resolve().parents[2]
HOST_PROCESS = ROOT / "src" / "claritylink-honda" / "display1_host_process.py"
PRODUCER = Path(__file__).with_name("cl_int_04_producer.py")
LEASE = 0.4
WAIT = 8.0  # generous ceiling; every wait returns as soon as its condition holds


def wait_for(predicate, timeout=WAIT):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


@pytest.fixture
def sock_path():
    directory = tempfile.mkdtemp(prefix="cl04", dir="/tmp")  # short: AF_UNIX path limit
    yield os.path.join(directory, "h.sock")
    shutil.rmtree(directory, ignore_errors=True)


def spawn_host(path, *extra, lease=LEASE):
    proc = subprocess.Popen(
        [sys.executable, "-I", str(HOST_PROCESS), "--socket", path, "--lease-seconds", str(lease),
         "--lab-controls", *extra], stdout=subprocess.PIPE, text=True)
    assert proc.stdout.readline().startswith("READY"), "host process did not start"
    return proc


def spawn_producer(path, mode):
    proc = subprocess.Popen([sys.executable, "-I", str(PRODUCER), path, mode],
                            stdout=subprocess.PIPE, text=True)
    line = proc.stdout.readline()
    assert line.startswith("STREAMING"), line
    return proc


def stop_host(proc):
    proc.send_signal(signal.SIGTERM)
    out = proc.communicate(timeout=10)[0]
    return proc.returncode, out


@pytest.fixture
def host_proc(sock_path):
    proc = spawn_host(sock_path)
    yield proc
    if proc.poll() is None:
        proc.kill()
        proc.communicate()


@pytest.fixture
def monitor(sock_path, host_proc):
    client = RemoteDisplay1Host(sock_path)
    yield client
    client.close()


def reasons(monitor):
    return monitor.status()["revocations"]


# ---- producer process boundary ----
def test_producer_sigkill_withdraws_display1_and_the_host_survives(host_proc, monitor, sock_path):
    producer = spawn_producer(sock_path, "hold")
    assert monitor.status()["visible"] is True
    producer.kill()
    producer.wait()
    assert wait_for(lambda: monitor.status()["visible"] is False)
    status = monitor.status()
    assert status["lease_held"] is False and status["residual"] == 0
    assert "producer connection lost" in status["revocations"]
    assert host_proc.poll() is None  # the host's lifecycle is independent of the producer's


def test_producer_normal_exit_withdraws_through_its_own_cleanup(host_proc, monitor, sock_path):
    producer = spawn_producer(sock_path, "clean")
    assert producer.wait(timeout=10) == 0
    assert wait_for(lambda: monitor.status()["visible"] is False)
    status = monitor.status()
    assert status["residual"] == 0 and status["lease_held"] is False
    assert host_proc.poll() is None


def test_silent_but_alive_producer_is_withdrawn_by_the_host_timer_alone(host_proc, monitor, sock_path):
    producer = spawn_producer(sock_path, "idle")
    try:
        assert monitor.status()["visible"] is True
        time.sleep(LEASE * 3)  # no reads: only the host's own timer can have acted
        status = monitor.status()
        assert producer.poll() is None  # the producer never died and never called anything
        assert status["visible"] is False and status["lease_held"] is False
        assert status["watchdog_enforcements"] >= 1  # the timer, not a lazy read, did the work
        assert any(r in ("lease expired", "no frame progress") for r in status["revocations"])
    finally:
        producer.kill()
        producer.wait()


def test_new_producer_after_death_gets_a_fresh_lease_and_old_generation_is_fenced(host_proc, monitor, sock_path):
    first = spawn_producer(sock_path, "hold")
    old = RemoteDisplay1Host(sock_path)  # a late sender still holding the old epoch
    first.kill()
    first.wait()
    assert wait_for(lambda: monitor.status()["lease_held"] is False)
    second = spawn_producer(sock_path, "hold")
    try:
        assert monitor.status()["visible"] is True
        stale = LeaseGrant(monitor.epoch, 1)  # the dead producer's generation
        # a late sender that owns no lease on its connection can never present, whatever it claims
        assert old.submit(stale, 99, "late") is SubmitResult.REJECTED_NO_LEASE
        assert monitor.status()["visible"] is True  # the late frame changed nothing
        assert monitor.status()["revocations"].count("producer connection lost") == 1
    finally:
        second.kill()
        second.wait()
        old.close()


def test_host_withdrawal_failure_is_reported_truthfully_then_recovers(sock_path):
    proc = spawn_host(sock_path, "--inject-withdraw-failures", "6")
    try:
        producer = spawn_producer(sock_path, "hold")
        watcher = RemoteDisplay1Host(sock_path)
        producer.kill()
        producer.wait()
        saw_pending = []

        def settled():
            st = watcher.status()
            if st["withdrawal_pending"]:
                saw_pending.append(st)
            return st["residual"] == 0 and not st["withdrawal_pending"]

        assert wait_for(settled)
        assert "OSError" in watcher.status()["withdrawal_failures"]
        assert watcher.status()["visible"] is False  # only after the retry succeeded
        assert saw_pending, "the failing phase must have been observable"
        assert watcher.status()["withdrawal_failure_count"] >= 6
        for st in saw_pending:  # while it was failing the host never claimed to be clean
            assert st["visible"] is True and st["residual"] > 0
        watcher.close()
    finally:
        code, out = stop_host(proc)
    assert code == 0 and "STOPPED clean=True" in out


# ---- in-process host-owned timer ----
class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def test_lease_expires_without_any_producer_callback_or_read():
    clock = FakeClock()
    host = Display1LeaseHost(lease_seconds=1.0, clock=clock)
    host.select_page(True)
    service = Display1HostService(host, max_wait=0.005)
    service.start()
    try:
        _result, lease = host.grant(1)
        assert host.submit(lease, 0, "frame") is SubmitResult.ACCEPTED
        clock.now += 5.0  # time passes; nobody reads, ticks, heartbeats or cleans up
        assert wait_for(lambda: host._lease is None)  # private read: avoids the lazy path
        assert host._cluster.main_content is None and host.revocations == ["lease expired"]
    finally:
        assert service.stop()


def test_withdrawal_failure_blocks_grants_and_timer_retries_until_clean():
    host = Display1LeaseHost(lease_seconds=1.0, clock=FakeClock())
    host.select_page(True)
    real, failures = host._cluster.withdraw_main, [3]

    def flaky():
        if failures[0]:
            failures[0] -= 1
            raise OSError("cluster refused")
        real()

    host._cluster.withdraw_main = flaky
    service = Display1HostService(host, max_wait=0.005)
    _result, lease = host.grant(1)
    host.submit(lease, 0, "frame")
    with pytest.raises(OSError):
        host.revoke("test")  # the failure is raised to a caller that reports cleanup
    assert host.withdrawal_pending and host.visible_content == "frame"  # truth: still shown
    assert host.grant(2)[0] is GrantResult.REJECTED_WITHDRAWAL_PENDING
    service.start()
    try:
        assert wait_for(lambda: not host.withdrawal_pending)
        assert host.visible_content is None and host.residual_state == ()
        assert host.withdrawal_failures.count("OSError") == 3
        assert host.grant(2)[0] is GrantResult.GRANTED
    finally:
        service.stop()


def test_watchdog_survives_an_unexpected_error_and_reports_it():
    host = Display1LeaseHost(lease_seconds=1.0, clock=FakeClock())
    calls = [0]
    real = host.enforce_expiry

    def broken():
        calls[0] += 1
        if calls[0] <= 2:
            raise RuntimeError("timer fault")
        return real()

    host.enforce_expiry = broken
    service = Display1HostService(host, max_wait=0.005)
    service.start()
    try:
        assert wait_for(lambda: calls[0] > 4)
        status = service.status()
        assert status.watchdog_alive and status.watchdog_errors == 2
        assert service.error_types[:2] == ["RuntimeError", "RuntimeError"]
    finally:
        service.stop()


def test_timer_and_submit_race_never_presents_after_revocation():
    host = Display1LeaseHost(lease_seconds=0.02)
    host.select_page(True)
    service = Display1HostService(host, max_wait=0.002)
    service.start()
    errors = []
    stop = threading.Event()

    def producer():
        generation = 0
        while not stop.is_set():
            generation += 1
            try:
                result, lease = host.grant(generation)
                if lease is None:
                    continue
                for sequence in range(50):
                    host.submit(lease, sequence, f"f{generation}.{sequence}")
                    time.sleep(0.001)
            except Exception as exc:  # noqa: BLE001 - any raise is a failure of the host contract
                errors.append(repr(exc))

    threads = [threading.Thread(target=producer) for _ in range(3)]
    for thread in threads:
        thread.start()
    time.sleep(0.8)
    stop.set()
    for thread in threads:
        thread.join(5)
    try:
        assert not errors and not any(t.is_alive() for t in threads)
        assert wait_for(lambda: host._lease is None and host.visible_content is None)
        assert host.residual_state == () and service.status().watchdog_errors == 0
        assert host.revocations  # expiry and supersession both really happened
    finally:
        assert service.stop()


def test_repeated_shutdown_and_restart_leak_nothing(sock_path):
    baseline = threading.active_count()
    epochs = []
    previous = None
    for _ in range(5):
        service = Display1HostService(Display1LeaseHost(lease_seconds=5.0))
        server = Display1HostServer(service, sock_path)
        server.start()
        client = RemoteDisplay1Host(sock_path)
        coordinator = FailSafeCoordinator(client)
        coordinator.phone_attached()
        coordinator.carplay_started()
        assert coordinator.type111_negotiated()
        assert coordinator.submit_frame("f") is SubmitResult.ACCEPTED
        epochs.append(client.epoch)
        if previous is not None:  # a lease from the previous boot can never match
            assert service.host.submit(previous, 0, "x") is SubmitResult.REJECTED_EPOCH
        previous = coordinator.lease
        assert server.stop() is True  # joins accept thread, connection threads and the timer
        assert not os.path.exists(sock_path)
        client.close()
        assert service.host.residual_state == () and not service.host.lease_held
    assert len(set(epochs)) == len(epochs)
    assert wait_for(lambda: threading.active_count() <= baseline)


def test_second_host_on_a_live_socket_is_refused(sock_path):
    first = Display1HostServer(Display1HostService(Display1LeaseHost()), sock_path)
    first.start()
    try:
        with pytest.raises(HostIpcError, match="host_already_running"):
            Display1HostServer(Display1HostService(Display1LeaseHost()), sock_path).start()
    finally:
        assert first.stop()


def test_stale_socket_file_from_a_dead_host_is_replaced(sock_path):
    proc = spawn_host(sock_path)
    proc.kill()
    proc.communicate()
    assert os.path.exists(sock_path)  # SIGKILL left it behind
    server = Display1HostServer(Display1HostService(Display1LeaseHost()), sock_path)
    server.start()
    assert server.stop()


def test_dead_producer_cannot_revoke_a_newer_generation(sock_path):
    service = Display1HostService(Display1LeaseHost(lease_seconds=5.0))
    service.host.select_page(True)
    server = Display1HostServer(service, sock_path)
    server.start()
    try:
        a, b = RemoteDisplay1Host(sock_path), RemoteDisplay1Host(sock_path)
        _r, lease_a = a.grant(1)
        _r, lease_b = b.grant(2)  # supersedes A
        assert a.submit(lease_a, 0, "old") is SubmitResult.REJECTED_SUPERSEDED
        assert b.submit(lease_b, 0, "new") is SubmitResult.ACCEPTED
        a.close()  # the old producer dies late
        assert wait_for(lambda: len(server._conns) == 1)  # the host really processed that death
        assert service.host.visible_content == "new" and service.host.lease_held
        assert b.submit(lease_a, 1, "forged") is SubmitResult.REJECTED_STALE_GENERATION
        b.close()
        assert wait_for(lambda: not service.host.lease_held)
    finally:
        assert server.stop()


def test_transport_failure_fails_closed():
    host_less = RemoteDisplay1Host.__new__(RemoteDisplay1Host)
    host_less._lock, host_less._sock, host_less._buffer = threading.Lock(), None, b""
    host_less.transport_errors = 0
    # no transport means no host decision: every operation raises, none invents a refusal
    # (test_cl_int_04_qa_fixes.py covers valid refusal vs. each kind of IPC failure)
    lease = LeaseGrant(1, 1)
    for unknown in (lambda: host_less.grant(1), lambda: host_less.submit(lease, 0, "x"),
                    lambda: host_less.heartbeat(lease), lambda: host_less.lease_held,
                    lambda: host_less.revoke("x"), lambda: host_less.residual_state,
                    lambda: host_less.visible_content, host_less.status):
        with pytest.raises(HostIpcError):
            unknown()


# ---- Type110 independence with the real ingest pipeline against the out-of-process host ----
def test_type110_stays_operational_through_host_withdrawal_and_reactivation(sock_path):
    stream = synth.SyntheticStream(4)
    proc = spawn_host(sock_path, lease=0.5)
    remote = RemoteDisplay1Host(sock_path)
    pipe = Type111IngestPipeline(lab_mode=True, host=remote, receiver_kwargs=dict(synth.DIMENSIONS))
    client = primary = None
    try:
        client, primary = synth.start_type111(pipe, with_primary=True)
        primary.sendall(stream.primary_message(0))
        pipe.receiver.receive_primary_frame(pipe.generation)
        held, decoder = pipe.primary_display.current, pipe.receiver.primary_decoder
        client.sendall(stream.config_message() + stream.frame_message(0, timestamp=5))
        assert pipe.pump_frame().accepted and pipe.pump_frame().accepted
        assert remote.status()["visible"] is True
        time.sleep(1.2)  # producer is silent: no tick(), no heartbeat; only the host can act
        assert remote.status()["visible"] is False  # host withdrew on its own
        assert pipe.tick() is True  # the producer adopts what the host already did
        assert pipe.primary_display.current is held and not decoder.closed  # Type110 untouched
        primary.sendall(stream.primary_message(1))
        assert pipe.receiver.receive_primary_frame(pipe.generation).startswith(b"\x89PNG")
        assert pipe.residual() == ()
    finally:
        for sock in (client, primary):
            if sock is not None:
                sock.close()
        pipe.receiver.teardown(pipe.generation)
        remote.close()
        code, out = stop_host(proc)
        assert code == 0 and "STOPPED clean=True" in out


# ---- review follow-ups: truthful remote reporting, bounds, reactivation, socket safety ----
def flaky_service(failures, lease_seconds=5.0):
    host = Display1LeaseHost(lease_seconds=lease_seconds)
    host.select_page(True)
    real, left = host._cluster.withdraw_main, [failures]

    def withdraw():
        if left[0] > 0:
            left[0] -= 1
            raise OSError("cluster refused")
        real()

    host._cluster.withdraw_main = withdraw
    return Display1HostService(host, max_wait=0.005)


def test_remote_revoke_raises_when_the_cluster_refuses_instead_of_claiming_withdrawn(sock_path):
    service = flaky_service(failures=3)
    server = Display1HostServer(service, sock_path)
    server.start()
    try:
        client = RemoteDisplay1Host(sock_path)
        _result, lease = client.grant(1)
        assert client.submit(lease, 0, "frame") is SubmitResult.ACCEPTED
        with pytest.raises(HostIpcError, match="host_withdrawal_pending"):
            client.revoke("test")
        st = client.status()
        assert st["withdrawal_pending"] is True and st["visible"] is True  # truth: still shown
        assert wait_for(lambda: not service.host.withdrawal_pending)  # the host timer retried
        assert client.revoke("again") is False  # nothing left, and now confirmed
        client.close()
    finally:
        assert server.stop()


def test_persistent_withdrawal_failure_keeps_diagnostics_bounded_and_status_readable(sock_path):
    service = flaky_service(failures=10 ** 9)
    server = Display1HostServer(service, sock_path)
    server.start()
    try:
        client = RemoteDisplay1Host(sock_path)
        _result, lease = client.grant(1)
        client.submit(lease, 0, "frame")
        with pytest.raises(HostIpcError):
            client.revoke("test")
        assert wait_for(lambda: service.host.withdrawal_failure_count > 300, timeout=15)
        st = client.status()  # still readable: the reply stays small however long it fails
        assert st["withdrawal_pending"] is True and st["visible"] is True
        assert len(st["withdrawal_failures"]) <= 32 and st["withdrawal_failure_count"] > 300
        assert client.connected and len(client.residual_state) > 0  # never reported clean
        client.close()
    finally:
        service.host._cluster.withdraw_main = lambda: None  # let teardown finish
        server.stop()


def test_superseded_connection_cannot_reclaim_ownership_by_granting_again(sock_path):
    """Regression for the CL-INT-04 QA defect: A -> B -> A's grant used to return generation 3."""
    service = Display1HostService(Display1LeaseHost(lease_seconds=5.0))
    service.host.select_page(True)
    server = Display1HostServer(service, sock_path)
    server.start()
    try:
        a, b = RemoteDisplay1Host(sock_path), RemoteDisplay1Host(sock_path)
        _r, first = a.grant(1)
        _r, other = b.grant(1)  # the host allocates above a's generation
        assert other.generation > first.generation
        high_water = service.host.generation_high_water
        assert a.grant(2) == (GrantResult.REJECTED_SUPERSEDED, None)  # A's counter cannot win it back
        assert service.host.generation_high_water == high_water  # no generation was consumed
        assert b.submit(other, 0, "owner") is SubmitResult.ACCEPTED
        assert a.submit(first, 0, "late") is SubmitResult.REJECTED_SUPERSEDED
        assert service.host.visible_content == "owner" and service.host.lease_held
        a.close()
        b.close()
    finally:
        assert server.stop()


def test_out_of_range_wire_integers_are_rejected_and_cannot_inflate_the_generation_fence(sock_path):
    service = Display1HostService(Display1LeaseHost(lease_seconds=5.0))
    server = Display1HostServer(service, sock_path)
    server.start()
    try:
        client = RemoteDisplay1Host(sock_path)
        before = service.host.generation_high_water
        with pytest.raises(HostIpcError, match="host_error:bad_request"):  # not a host decision
            client.grant(10 ** 18)
        assert service.host.generation_high_water == before and client.connected
        assert client.grant(1)[0] is GrantResult.GRANTED
        client.close()
    finally:
        assert server.stop()


def test_a_regular_file_at_the_socket_path_is_never_deleted(sock_path):
    Path(sock_path).write_text("not a socket")
    server = Display1HostServer(Display1HostService(Display1LeaseHost()), sock_path)
    with pytest.raises(HostIpcError, match="socket_path_not_ours"):
        server.start()
    assert Path(sock_path).read_text() == "not a socket"


def test_socket_is_private_to_the_owner(sock_path):
    server = Display1HostServer(Display1HostService(Display1LeaseHost()), sock_path)
    server.start()
    try:
        assert os.stat(sock_path).st_mode & 0o077 == 0
    finally:
        assert server.stop()


def test_visible_content_is_never_reported_without_a_lease_under_timer_and_submit_races():
    host = Display1LeaseHost(lease_seconds=0.02)
    host.select_page(True)
    service = Display1HostService(host, max_wait=0.002)
    service.start()
    violations, stop = [], threading.Event()

    def sampler():
        while not stop.is_set():
            with host._lock:  # one atomic view of lease and content
                if host._cluster.main_content is not None and host._lease is None \
                        and not host.withdrawal_pending:
                    violations.append("content held with no lease")

    def producer():
        generation = 0
        while not stop.is_set():
            generation += 1
            _result, lease = host.grant(generation)
            for sequence in range(30) if lease else ():
                host.submit(lease, sequence, "f")
                time.sleep(0.001)

    threads = [threading.Thread(target=sampler)] + [threading.Thread(target=producer) for _ in range(2)]
    for thread in threads:
        thread.start()
    time.sleep(0.8)
    stop.set()
    for thread in threads:
        thread.join(5)
    try:
        assert not violations
        assert host.revocation_count > 1  # the race really exercised expiry and supersession
    finally:
        assert service.stop()
