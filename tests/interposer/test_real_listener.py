from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import gc
import os
import socket
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-interposer"))

from real_listener import (GenerationListenerRegistry, InterfaceKind, InterfacePolicy,
                           ListenerError, PreparedListener)


def loopback():
    return InterfacePolicy(InterfaceKind.LOOPBACK_TEST)


@pytest.mark.parametrize("phase", ["socket", "options", "bind", "getsockname", "listen", "worker", "accept"])
def test_listener_setup_failure_closes_any_created_real_socket(phase):
    opened = []

    def factory(*args):
        value = socket.socket(*args)
        opened.append(value)
        return value

    with pytest.raises(ListenerError):
        PreparedListener.create(("B", phase), loopback(), failure_at=phase,
                                socket_factory=factory)
    assert all(value.fileno() == -1 for value in opened)


def test_listen_and_worker_are_ready_before_immediate_client_connects():
    listener = PreparedListener.create("B42", loopback())
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    accepted = None
    try:
        assert listener.state == "READY"
        assert listener.assigned_port > 0
        assert not listener.sock.get_inheritable()
        # This connection starts immediately after create returns, the
        # equivalent of the simulated serializer completing.
        client.connect(("127.0.0.1", listener.assigned_port))
        accepted = listener.wait_accepted()
        assert accepted is not None
        assert listener.state == "CONNECTED"
        assert not accepted.get_inheritable()
        assert listener.worker.is_alive() is False
    finally:
        client.close()
        listener.close()
    assert listener.state == "CLOSED"
    assert not listener.worker.is_alive()
    assert listener.sock.fileno() == -1
    assert accepted is not None and accepted.fileno() == -1
    listener.close()  # idempotent; no double-close


def test_interface_policies_are_explicit_and_honda_policy_is_not_selected():
    specific = InterfacePolicy(InterfaceKind.SPECIFIC_ADDRESS, "127.0.0.1")
    wildcard = InterfacePolicy(InterfaceKind.WILDCARD_TEST_ONLY)
    for key, policy in (("loop", loopback()), ("specific", specific), ("wildcard", wildcard)):
        listener = PreparedListener.create(key, policy)
        listener.close()
    with pytest.raises(ListenerError, match="interface_policy_invalid"):
        InterfacePolicy(InterfaceKind.SPECIFIC_ADDRESS).bind_address()


def test_generation_exact_cleanup_cannot_close_replacement_sockets_or_worker():
    registry = GenerationListenerRegistry()
    b42 = PreparedListener.create("B42", loopback())
    b43 = PreparedListener.create("B43", loopback())
    clients = [socket.socket(socket.AF_INET, socket.SOCK_STREAM) for _ in range(2)]
    try:
        registry.attach("B42", b42)
        clients[0].connect(("127.0.0.1", b42.assigned_port))
        accepted42 = b42.wait_accepted()
        assert accepted42 is not None
        registry.attach("B43", b43)
        clients[1].connect(("127.0.0.1", b43.assigned_port))
        accepted43 = b43.wait_accepted()
        assert accepted43 is not None
        assert registry.close_generation("B42")
        assert not registry.close_generation("B42")
        assert b42.sock.fileno() == -1
        assert accepted42.fileno() == -1
        assert not b42.worker.is_alive()
        assert b43.sock.fileno() >= 0
        assert accepted43.fileno() >= 0
        assert not b43.worker.is_alive()
        assert registry.get("B43") is b43
        assert registry.owned_generations == ("B43",)
    finally:
        for client in clients:
            client.close()
        registry.close_all()


def test_accept_failure_timeout_and_never_connect_rollback_join_worker():
    idle = PreparedListener.create("Bidle", loopback())
    assert idle.wait_accepted(timeout=0.02) is None
    idle.close()
    assert not idle.worker.is_alive()
    assert idle.sock.fileno() == -1


def test_client_drop_timeout_parent_teardown_and_disable_close_owned_handles():
    for cause in ("client_drop", "timeout", "parent_teardown", "project_disable"):
        registry = GenerationListenerRegistry()
        listener = PreparedListener.create(cause, loopback())
        registry.attach(cause, listener)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", listener.assigned_port))
        accepted = listener.wait_accepted()
        assert accepted is not None
        client.close()
        assert registry.close_generation(cause)
        assert listener.sock.fileno() == -1
        assert accepted.fileno() == -1
        assert not listener.worker.is_alive()


def test_two_independent_generations_accept_concurrently_and_cleanup_independently():
    registry = GenerationListenerRegistry()
    listeners = [PreparedListener.create(("session", n), loopback()) for n in (1, 2)]
    clients = [socket.socket(socket.AF_INET, socket.SOCK_STREAM) for _ in listeners]
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            for listener in listeners:
                registry.attach(listener.generation, listener)
            futures = [pool.submit(client.connect, ("127.0.0.1", listener.assigned_port))
                       for client, listener in zip(clients, listeners)]
            for future in futures:
                future.result(timeout=2)
        accepted = [listener.wait_accepted() for listener in listeners]
        assert all(value is not None for value in accepted)
        assert registry.owned_generations == (("session", 1), ("session", 2))
        assert registry.close_generation(("session", 1))
        assert listeners[0].sock.fileno() == -1
        assert listeners[1].sock.fileno() >= 0
        assert not listeners[0].worker.is_alive()
        assert not listeners[1].worker.is_alive()
    finally:
        for client in clients:
            client.close()
        registry.close_all()


def test_repeated_real_socket_rollback_has_no_fd_or_worker_leak():
    fd_dir = Path("/dev/fd")
    before = set(fd_dir.iterdir()) if fd_dir.exists() else set()
    listeners = []
    for index in range(20):
        listener = PreparedListener.create(("leak", index), loopback())
        listeners.append(listener)
        assert listener.sock.fileno() >= 0
        listener.close()
    gc.collect()
    after = set(fd_dir.iterdir()) if fd_dir.exists() else set()
    assert all(item.sock.fileno() == -1 and not item.worker.is_alive() for item in listeners)
    # Allow a transient interpreter-owned descriptor, but no growth per cycle.
    assert len(after) <= len(before) + 1
