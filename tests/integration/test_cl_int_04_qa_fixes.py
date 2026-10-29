"""CL-INT-04 QA corrections (PR #104). Offline, synthetic only.

Defect 1: a producer connection that lost ownership to another producer must stay fenced.
Defect 2: a broken IPC channel must never be reported as a legitimate host refusal.
"""
import json
import socket
import threading
from contextlib import contextmanager

import pytest

import t111_synth as synth
from display1_host_ipc import Display1HostServer, HostIpcError, RemoteDisplay1Host
from display1_host_service import Display1HostService
from failsafe_coordinator import (Display1LeaseHost, FailSafeCoordinator, Fault, GrantResult,
                                  LeaseGrant, LinkState, SubmitResult)
from test_cl_int_04_host_withdrawal import FakeClock, sock_path, wait_for  # noqa: F401 (fixture)
from type111_ingest import Type111IngestPipeline

SCRIPT_TIMEOUT = 0.4  # client read timeout against the scripted host
HELLO_OK = b'{"ok":true,"epoch":7}\n'
CLOSE, SILENT = object(), object()


# ---- a scripted raw host: answers each request line with the next scripted action ----
class ScriptedHost:
    def __init__(self, path, *script):
        self._script = [HELLO_OK, *script]
        self._stop = threading.Event()
        self._listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._listener.bind(path)
        self._listener.listen(1)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self):
        try:
            conn, _addr = self._listener.accept()
        except OSError:
            return
        with conn:
            for action in self._script:
                if not self._read_request(conn) or action is CLOSE:
                    return
                if action is SILENT:
                    self._stop.wait(5)
                    return
                if isinstance(action, tuple):  # (bytes, CLOSE): send a fragment, then hang up
                    conn.sendall(action[0])
                    return
                conn.sendall(action)

    @staticmethod
    def _read_request(conn):
        data = b""
        while b"\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                return False
            data += chunk
        return True

    def stop(self):
        self._stop.set()
        self._listener.close()
        self._thread.join(5)


@contextmanager
def scripted_client(path, *script):
    host = ScriptedHost(path, *script)
    client = RemoteDisplay1Host(path, timeout=SCRIPT_TIMEOUT)
    try:
        yield client
    finally:
        client.close()
        host.stop()


def reply(**fields):
    return json.dumps(fields).encode() + b"\n"


# ---- defect 2: valid host refusal vs. IPC failure ----
REFUSALS = [r for r in GrantResult if r is not GrantResult.GRANTED]


@pytest.mark.parametrize("refusal", REFUSALS, ids=lambda r: r.value)
def test_valid_host_refusal_is_returned_as_that_refusal(sock_path, refusal):
    with scripted_client(sock_path, reply(ok=True, result=refusal.value, epoch=7, generation=0)) as client:
        assert client.grant(1) == (refusal, None)
        assert client.connected and client.transport_errors == 0  # a real answer is not a transport fault


# (id, scripted action, error text, connection survives)
IPC_FAILURES = [
    ("eof_after_request", CLOSE, "host_closed", False),
    ("missing_reply", SILENT, "host_transport_failed", False),
    ("truncated_reply", (b'{"ok":true,"resu', CLOSE), "host_closed", False),
    ("not_json", b"not json\n", "host_transport_failed:JSONDecodeError", False),
    ("not_an_object", b"[1,2]\n", "bad_reply", False),
    ("oversized_line", b"x" * 9000, "line_too_long", False),
    ("unknown_result", reply(ok=True, result="BOGUS"), "invalid_grant_reply", False),
    ("missing_result", reply(ok=True), "invalid_grant_reply", False),
    ("result_wrong_type", reply(ok=True, result=[]), "invalid_grant_reply", False),
    ("granted_without_epoch", reply(ok=True, result="GRANTED", generation=3), "invalid_grant_reply", False),
    ("granted_bad_epoch", reply(ok=True, result="GRANTED", epoch="x", generation=3),
     "invalid_grant_reply", False),
    ("granted_negative_generation", reply(ok=True, result="GRANTED", epoch=7, generation=-1),
     "invalid_grant_reply", False),
    ("ok_not_true", reply(ok="yes"), "host_error", True),
    ("host_reports_fault", reply(ok=False, error="host_error"), "host_error:host_error", True),
    ("host_reports_bad_request", reply(ok=False, error="bad_request"), "host_error:bad_request", True),
]


@pytest.mark.parametrize("action,message,survives", [f[1:] for f in IPC_FAILURES],
                         ids=[f[0] for f in IPC_FAILURES])
def test_ipc_failure_during_grant_raises_instead_of_manufacturing_a_refusal(sock_path, action, message, survives):
    with scripted_client(sock_path, action) as client:
        with pytest.raises(HostIpcError, match=message):
            client.grant(1)
        assert client.connected is survives
        assert client.transport_errors == (0 if survives else 1)


@pytest.mark.parametrize("action,message", [
    (CLOSE, "host_closed"), (SILENT, "host_transport_failed"),
    (reply(ok=True, result="BOGUS"), "invalid_submit_reply"), (reply(ok=True), "invalid_submit_reply"),
    (reply(ok=False, error="bad_content"), "host_error:bad_content"),
], ids=["eof", "missing_reply", "unknown_result", "missing_result", "host_error"])
def test_ipc_failure_during_submit_raises_instead_of_rejecting(sock_path, action, message):
    with scripted_client(sock_path, action) as client:
        with pytest.raises(HostIpcError, match=message):
            client.submit(LeaseGrant(7, 1), 0, "frame")


def test_valid_submit_refusal_is_still_returned(sock_path):
    with scripted_client(sock_path, reply(ok=True, result="REJECTED_INTERRUPTED")) as client:
        assert client.submit(LeaseGrant(7, 1), 0, "x") is SubmitResult.REJECTED_INTERRUPTED


@pytest.mark.parametrize("action", [CLOSE, reply(ok=True, alive="yes"), reply(ok=True)],
                         ids=["eof", "alive_not_bool", "alive_missing"])
def test_ipc_failure_during_heartbeat_raises_instead_of_reporting_dead(sock_path, action):
    with scripted_client(sock_path, action) as client:
        with pytest.raises(HostIpcError):
            client.heartbeat(LeaseGrant(7, 1))


def test_unconfirmed_revoke_status_and_lease_state_raise_with_the_transport_cause(sock_path):
    with scripted_client(sock_path, CLOSE) as client:
        with pytest.raises(HostIpcError, match="revoke_unconfirmed") as info:
            client.revoke("x")
        assert "host_closed" in str(info.value.__cause__)  # the original reason is preserved
        with pytest.raises(HostIpcError, match="host_status_unavailable"):
            client.status()
        with pytest.raises(HostIpcError):
            _ = client.lease_held


def test_lab_controls_raise_when_unconfirmed(sock_path):
    with scripted_client(sock_path, CLOSE) as client:
        with pytest.raises(HostIpcError):
            client.activate_interrupt()
        for control in (client.clear_interrupt, client.lose_display, client.restore_display,
                        lambda: client.select_page(True)):
            with pytest.raises(HostIpcError, match="host_unavailable"):
                control()


def live_host(sock_path, *, clock=None, lease_seconds=5.0):
    host = Display1LeaseHost(lease_seconds=lease_seconds, **({"clock": clock} if clock else {}))
    host.select_page(True)
    service = Display1HostService(host, max_wait=0.005)
    server = Display1HostServer(service, sock_path, lab_controls=True)
    server.start()
    return service, server


def test_connection_lost_during_grant_raises(sock_path):
    service, server = live_host(sock_path)
    client = RemoteDisplay1Host(sock_path)
    assert server.stop()  # the host goes away under an established connection
    with pytest.raises(HostIpcError):
        client.grant(1)
    assert not client.connected


# ---- defect 2: the failure travels through the fail-closed lifecycle with its cause ----
def dead_host_coordinator(sock_path, *, stream_first):
    service, server = live_host(sock_path)
    remote = RemoteDisplay1Host(sock_path)
    coordinator, closed = FailSafeCoordinator(remote), []
    coordinator.phone_attached()
    coordinator.carplay_started()
    closers = {"first": lambda: closed.append("first"), "second": lambda: closed.append("second")}
    if stream_first:
        assert coordinator.type111_negotiated(closers)
        assert coordinator.submit_frame("frame") is SubmitResult.ACCEPTED
    assert server.stop()
    return coordinator, closers, closed


def assert_failed_closed(coordinator, closed, error, reason):
    assert closed == ["second", "first"]  # every independent closer ran, newest first
    assert coordinator.lease is None and coordinator.state is LinkState.CARPLAY_ACTIVE
    assert coordinator.reports[-1].reason == reason
    chain, link = [], error.value  # status()/revoke wrap the transport error and keep it as __cause__
    while link is not None:
        chain.append(str(link))
        link = link.__cause__
    assert any(text.startswith(("host_closed", "host_transport_failed")) for text in chain)  # ORIGINAL cause
    assert "revoke_unconfirmed" not in chain[0]  # the grant/submit error was not replaced by the revoke's
    assert "withdrawal unconfirmed: HostIpcError" in error.value.__notes__  # never reported as withdrawn


def test_grant_ipc_failure_is_not_a_refusal_and_cleans_up(sock_path):
    coordinator, closers, closed = dead_host_coordinator(sock_path, stream_first=False)
    with pytest.raises(HostIpcError) as error:
        coordinator.type111_negotiated(closers)
    assert_failed_closed(coordinator, closed, error, "grant host error: HostIpcError")


def test_submit_ipc_failure_withdraws_and_raises(sock_path):
    coordinator, _closers, closed = dead_host_coordinator(sock_path, stream_first=True)
    with pytest.raises(HostIpcError) as error:
        coordinator.submit_frame("next")
    assert_failed_closed(coordinator, closed, error, "submit host error: HostIpcError")


def test_heartbeat_ipc_failure_withdraws_and_raises(sock_path):
    coordinator, _closers, closed = dead_host_coordinator(sock_path, stream_first=True)
    with pytest.raises(HostIpcError) as error:
        coordinator.heartbeat()
    assert_failed_closed(coordinator, closed, error, "heartbeat host error: HostIpcError")


def test_lease_state_ipc_failure_is_not_read_as_a_host_revocation(sock_path):
    coordinator, _closers, closed = dead_host_coordinator(sock_path, stream_first=True)
    with pytest.raises(HostIpcError) as error:
        coordinator.sync()
    assert_failed_closed(coordinator, closed, error, "lease state host error: HostIpcError")


def test_factory_warning_with_an_unreachable_host_still_cleans_up_then_raises(sock_path):
    coordinator, _closers, closed = dead_host_coordinator(sock_path, stream_first=True)
    with pytest.raises(HostIpcError) as error:
        coordinator.fault(Fault.FACTORY_WARNING)
    assert closed == ["second", "first"] and coordinator.lease is None
    assert coordinator.state is LinkState.CARPLAY_ACTIVE
    assert "withdrawal unconfirmed: HostIpcError" in error.value.__notes__


def test_pipeline_records_a_host_ipc_failure_on_heartbeat_and_keeps_type110(sock_path):
    service, server = live_host(sock_path)
    remote = RemoteDisplay1Host(sock_path)
    pipe = Type111IngestPipeline(lab_mode=True, host=remote, receiver_kwargs=dict(synth.DIMENSIONS))
    stream, client, primary = synth.SyntheticStream(2), None, None
    try:
        client, primary = synth.start_type111(pipe, with_primary=True)
        primary.sendall(stream.primary_message(0))
        pipe.receiver.receive_primary_frame(pipe.generation)
        held, decoder = pipe.primary_display.current, pipe.receiver.primary_decoder
        client.sendall(stream.config_message() + stream.frame_message(0, timestamp=5))
        assert pipe.pump_frame().accepted and pipe.pump_frame().accepted
        assert server.stop()
        assert pipe.heartbeat() is False  # no host decision: not "alive", not a raise
        assert pipe.cleanup_failures and "HostIpcError" in str(pipe.cleanup_failures)
        assert pipe.coordinator.lease is None and pipe.receiver.secondary is None
        assert pipe.primary_display.current is held and not decoder.closed  # Type110 untouched
    finally:
        for sock in (client, primary):
            if sock is not None:
                sock.close()
        pipe.receiver.teardown(pipe.generation)
        remote.close()


# ---- defect 1: a superseded connection stays fenced ----
@pytest.fixture
def host(sock_path):
    service, server = live_host(sock_path)
    clients = []

    def connect():
        clients.append(RemoteDisplay1Host(sock_path))
        return clients[-1]

    yield service, server, connect
    for client in clients:
        client.close()
    assert server.stop()


def test_a_b_then_stale_a_grant_is_rejected_and_changes_nothing(host):
    service, _server, connect = host
    a, b = connect(), connect()
    _r, lease_a = a.grant(1)
    _r, lease_b = b.grant(1)
    assert b.submit(lease_b, 0, "owner") is SubmitResult.ACCEPTED
    before = (service.host.generation_high_water, service.host.revocation_count)
    for _attempt in range(5):  # asking repeatedly never wins it back
        assert a.grant(99) == (GrantResult.REJECTED_SUPERSEDED, None)
    assert (service.host.generation_high_water, service.host.revocation_count) == before
    assert lease_b.generation == before[0] and service.host.visible_content == "owner"
    assert b.submit(lease_b, 1, "still owner") is SubmitResult.ACCEPTED


def test_stale_a_submit_and_heartbeat_are_rejected_without_touching_visible_content(host):
    service, _server, connect = host
    a, b = connect(), connect()
    _r, lease_a = a.grant(1)
    _r, lease_b = b.grant(1)
    assert b.submit(lease_b, 0, "owner") is SubmitResult.ACCEPTED
    assert a.submit(lease_a, 0, "intruder") is SubmitResult.REJECTED_SUPERSEDED
    assert a.submit(lease_b, 1, "forged current lease") is SubmitResult.REJECTED_SUPERSEDED
    assert a.heartbeat(lease_b) is False
    assert service.host.visible_content == "owner" and service.host.lease_held
    assert service.host.generation_high_water == lease_b.generation


def test_superseded_connection_cannot_revoke_the_new_owner(host):
    service, _server, connect = host
    a, b = connect(), connect()
    a.grant(1)
    _r, lease_b = b.grant(1)
    assert b.submit(lease_b, 0, "owner") is SubmitResult.ACCEPTED
    assert a.revoke("stale cleanup") is False  # nothing of A's to revoke
    assert service.host.visible_content == "owner"


def test_stale_disconnect_handler_does_not_revoke_the_new_owner(host):
    service, server, connect = host
    a, b = connect(), connect()
    a.grant(1)
    _r, lease_b = b.grant(1)
    assert b.submit(lease_b, 0, "owner") is SubmitResult.ACCEPTED
    revocations = service.host.revocation_count
    a.close()
    assert wait_for(lambda: len(server._conns) == 1)  # the host really processed A's death
    assert service.host.revocation_count == revocations
    assert service.host.visible_content == "owner" and service.host.lease_held
    assert b.submit(lease_b, 1, "alive") is SubmitResult.ACCEPTED


def test_fresh_producer_gets_a_host_assigned_monotonic_generation(host):
    service, server, connect = host
    a, b = connect(), connect()
    _r, lease_a = a.grant(1)
    _r, lease_b = b.grant(1)
    a.close()
    b.close()
    assert wait_for(lambda: len(server._conns) == 0)
    c = connect()
    result, lease_c = c.grant(1)  # a fresh process restarts its own counter at 1
    assert result is GrantResult.GRANTED
    assert lease_c.generation > lease_b.generation > lease_a.generation
    assert lease_c.epoch == service.host.epoch
    assert c.submit(lease_c, 0, "fresh") is SubmitResult.ACCEPTED
    assert c.grant(1)[0] is GrantResult.GRANTED  # the owner may renegotiate on its own connection


def test_owner_may_release_and_regrant_on_its_own_connection(host):
    _service, _server, connect = host
    a = connect()
    _r, first = a.grant(1)
    assert a.revoke("renegotiate") is True
    result, second = a.grant(1)
    assert result is GrantResult.GRANTED and second.generation > first.generation


def test_lease_expiry_then_a_fresh_connection_is_legitimate_and_old_one_stays_fenced(sock_path):
    clock = FakeClock()
    service, server = live_host(sock_path, clock=clock, lease_seconds=1.0)
    a, c = RemoteDisplay1Host(sock_path), RemoteDisplay1Host(sock_path)
    try:
        _r, lease_a = a.grant(1)
        assert a.submit(lease_a, 0, "frame") is SubmitResult.ACCEPTED
        clock.now += 5.0
        assert wait_for(lambda: service.host._lease is None)  # the host's own timer expired it
        result, lease_c = c.grant(1)
        assert result is GrantResult.GRANTED and lease_c.generation > lease_a.generation
        assert a.grant(1) == (GrantResult.REJECTED_SUPERSEDED, None)  # expiry did not unfence A
        assert a.submit(lease_a, 1, "late") is SubmitResult.REJECTED_SUPERSEDED
        assert c.submit(lease_c, 0, "fresh") is SubmitResult.ACCEPTED
        assert service.host.visible_content == "fresh"
    finally:
        a.close()
        c.close()
        assert server.stop()


def test_concurrent_supersession_and_regrant_never_unfence_a_loser(host):
    service, _server, connect = host
    workers, rounds = 4, 40
    clients, barrier = [connect() for _ in range(workers)], threading.Barrier(workers)
    logs = [[] for _ in range(workers)]  # per connection: ("grant"|"submit", result) in order

    def producer(index):
        client, lease = clients[index], None
        barrier.wait()
        for round_no in range(rounds):
            result, granted = client.grant(round_no + 1)
            logs[index].append(("grant", result, granted))
            if granted is not None:
                lease = granted
            if lease is not None:
                logs[index].append(("submit", client.submit(lease, round_no, f"c{index}"), lease))

    threads = [threading.Thread(target=producer, args=(i,)) for i in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert not any(thread.is_alive() for thread in threads)
    generations = [granted.generation for log in logs for kind, _r, granted in log
                   if kind == "grant" and granted is not None]
    assert len(generations) == len(set(generations))  # the host never issued a generation twice
    for log in logs:
        superseded = False
        for kind, result, _lease in log:
            if superseded:  # once fenced, nothing from this connection succeeds again
                assert result in (GrantResult.REJECTED_SUPERSEDED, SubmitResult.REJECTED_SUPERSEDED)
            superseded = superseded or result in (GrantResult.REJECTED_SUPERSEDED,
                                                  SubmitResult.REJECTED_SUPERSEDED)
    assert service.host.generation_high_water == max(generations)


def test_superseded_coordinator_withdraws_on_heartbeat_instead_of_keeping_a_dead_lease(host):
    """Review finding: host-global lease_held is True (the new owner's), so sync() alone kept A's lease."""
    service, _server, connect = host
    a, b = connect(), connect()
    coordinator, closed = FailSafeCoordinator(a), []
    coordinator.phone_attached()
    coordinator.carplay_started()
    assert coordinator.type111_negotiated({"stream": lambda: closed.append("stream")})
    assert coordinator.submit_frame("frame") is SubmitResult.ACCEPTED
    _r, lease_b = b.grant(1)
    assert b.submit(lease_b, 0, "owner") is SubmitResult.ACCEPTED
    assert coordinator.heartbeat() is False
    assert coordinator.lease is None and closed == ["stream"]
    assert coordinator.state is LinkState.CARPLAY_ACTIVE
    assert service.host.visible_content == "owner"  # the new owner is untouched by A's withdrawal
    assert coordinator.type111_negotiated({}) is False  # and A cannot renegotiate on this connection
    assert coordinator.reports[-1].reason.startswith("grant refused: REJECTED_SUPERSEDED")


def test_submit_by_a_superseded_coordinator_withdraws_it(host):
    _service, _server, connect = host
    a, b = connect(), connect()
    coordinator, closed = FailSafeCoordinator(a), []
    coordinator.phone_attached()
    coordinator.carplay_started()
    assert coordinator.type111_negotiated({"stream": lambda: closed.append("stream")})
    b.grant(1)
    assert coordinator.submit_frame("late") is SubmitResult.REJECTED_SUPERSEDED
    assert coordinator.lease is None and closed == ["stream"]


def test_a_fenced_connection_is_not_told_about_the_new_owners_pending_withdrawal(sock_path):
    service, server = live_host(sock_path)
    a, b = RemoteDisplay1Host(sock_path), RemoteDisplay1Host(sock_path)
    try:
        a.grant(1)
        _r, lease_b = b.grant(1)
        b.submit(lease_b, 0, "owner")
        service.host._withdrawal_pending = True  # the new owner's withdrawal is (pretend) pending
        assert a.revoke("stale cleanup") is False  # A owns nothing: no HostIpcError for B's problem
        assert service.host.withdrawal_pending  # and the host's own state was not touched by it
    finally:
        service.host._withdrawal_pending = False
        a.close()
        b.close()
        assert server.stop()


@pytest.mark.parametrize("status", [
    {"lease_held": "false", "visible": False, "withdrawal_pending": False, "residual": 0, "revocations": []},
    {"visible": False, "withdrawal_pending": False, "residual": 0, "revocations": []},
    {"lease_held": True, "visible": False, "withdrawal_pending": False, "residual": 10 ** 9, "revocations": []},
    {"lease_held": True, "visible": False, "withdrawal_pending": False, "residual": 0, "revocations": "x"},
], ids=["string_bool", "missing_key", "huge_residual", "revocations_not_list"])
def test_status_with_mistyped_fields_is_a_protocol_error_not_a_value(sock_path, status):
    with scripted_client(sock_path, reply(ok=True, status=status)) as client:
        with pytest.raises(HostIpcError, match="invalid_status_reply"):
            client.status()
        assert not client.connected


def test_type110_is_unaffected_when_the_type111_producer_is_superseded(sock_path):
    service, server = live_host(sock_path)
    remote, rival = RemoteDisplay1Host(sock_path), RemoteDisplay1Host(sock_path)
    pipe = Type111IngestPipeline(lab_mode=True, host=remote, receiver_kwargs=dict(synth.DIMENSIONS))
    stream, client, primary = synth.SyntheticStream(3), None, None
    try:
        client, primary = synth.start_type111(pipe, with_primary=True)
        primary.sendall(stream.primary_message(0))
        pipe.receiver.receive_primary_frame(pipe.generation)
        held, decoder = pipe.primary_display.current, pipe.receiver.primary_decoder
        client.sendall(stream.config_message() + stream.frame_message(0, timestamp=5))
        assert pipe.pump_frame().accepted and pipe.pump_frame().accepted
        assert rival.grant(1)[0] is GrantResult.GRANTED  # another producer takes Display 1
        client.sendall(stream.frame_message(1, timestamp=6))
        assert not pipe.pump_frame().accepted  # the superseded pipeline can no longer present
        assert service.host.visible_content is None  # and nothing of the old producer remains
        assert remote.grant(1) == (GrantResult.REJECTED_SUPERSEDED, None)
        assert pipe.primary_display.current is held and not decoder.closed  # Type110 untouched
        primary.sendall(stream.primary_message(1))
        assert pipe.receiver.receive_primary_frame(pipe.generation).startswith(b"\x89PNG")
    finally:
        for sock in (client, primary):
            if sock is not None:
                sock.close()
        pipe.receiver.teardown(pipe.generation)
        remote.close()
        rival.close()
        assert server.stop()
