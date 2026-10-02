"""Host-only, generation-owned TCP listener reference implementation.

This is not a Honda Android listener and never chooses a Honda interface.
Listener setup is synchronous; a bounded-timeout joinable worker accepts off
the caller thread. Every live socket/worker is owned by one exact generation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import socket
import threading
import time
from typing import Callable, Hashable


class ListenerError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class InterfaceKind(str, Enum):
    LOOPBACK_TEST = "LOOPBACK_TEST"
    SPECIFIC_ADDRESS = "SPECIFIC_ADDRESS"
    WILDCARD_TEST_ONLY = "WILDCARD_TEST_ONLY"


@dataclass(frozen=True)
class InterfacePolicy:
    kind: InterfaceKind
    address: str | None = None

    def bind_address(self) -> str:
        if self.kind is InterfaceKind.LOOPBACK_TEST:
            return "127.0.0.1"
        if self.kind is InterfaceKind.WILDCARD_TEST_ONLY:
            return "0.0.0.0"
        if self.kind is InterfaceKind.SPECIFIC_ADDRESS and self.address:
            return self.address
        raise ListenerError("interface_policy_invalid")


@dataclass
class PreparedListener:
    generation: Hashable
    sock: socket.socket
    assigned_port: int
    worker: threading.Thread
    accepted: socket.socket | None = None
    state: str = "READY"
    cancelled: threading.Event = field(default_factory=threading.Event)
    accepted_event: threading.Event = field(default_factory=threading.Event)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    _listener_closed: bool = False
    _accepted_closed: bool = False
    close_count: int = 0

    @property
    def port(self) -> int:
        return self.assigned_port

    @classmethod
    def create(
        cls,
        generation: Hashable,
        policy: InterfacePolicy,
        *,
        failure_at: str | None = None,
        socket_factory: Callable[..., socket.socket] = socket.socket,
        accept_timeout: float = 0.05,
        on_failure: Callable[[str], None] | None = None,
    ) -> "PreparedListener":
        sock = None
        ready = threading.Event()
        accepted_box: dict[str, socket.socket] = {}
        accepted_lock = threading.Lock()
        cancelled = threading.Event()
        worker_errors: list[str] = []
        listener_holder: dict[str, "PreparedListener"] = {}

        def notify_failure(code: str) -> None:
            worker_errors.append(code)
            listener = listener_holder.get("listener")
            if listener is not None and on_failure is not None:
                try:
                    on_failure(code)
                except Exception:
                    # Failure callbacks must not escape the owned worker.
                    worker_errors.append("failure_callback_failed")
        try:
            if failure_at == "socket":
                raise ListenerError("socket_create_failed")
            sock = socket_factory(socket.AF_INET, socket.SOCK_STREAM)
            if failure_at == "options":
                raise ListenerError("socket_option_failed")
            sock.set_inheritable(False)
            sock.settimeout(accept_timeout)
            if failure_at == "bind":
                raise ListenerError("bind_failed")
            sock.bind((policy.bind_address(), 0))
            if failure_at == "getsockname":
                raise ListenerError("getsockname_failed")
            port = int(sock.getsockname()[1])
            if not 1 <= port <= 65535:
                raise ListenerError("assigned_port_invalid")
            if failure_at == "listen":
                raise ListenerError("listen_failed")
            sock.listen(1)

            listener = cls(generation, sock, port, threading.Thread(target=lambda: None))
            listener.cancelled = cancelled
            listener.accepted_event = ready
            listener._accepted_box = accepted_box
            listener._accepted_lock = accepted_lock
            listener._worker_errors = worker_errors
            # Publish ownership before the worker can report an asynchronous
            # failure, eliminating a startup window that could lose cleanup.
            listener_holder["listener"] = listener

            def accept_loop() -> None:
                ready.set()
                if failure_at == "accept":
                    notify_failure("accept_failed")
                    return
                while not cancelled.is_set():
                    try:
                        conn, _peer = sock.accept()
                    except socket.timeout:
                        continue
                    except OSError:
                        if not cancelled.is_set():
                            notify_failure("accept_failed")
                        return
                    try:
                        conn.set_inheritable(False)
                        conn.settimeout(None)
                    except OSError:
                        conn.close()
                        notify_failure("accepted_socket_setup_failed")
                        return
                    if cancelled.is_set():
                        conn.close()
                        return
                    with accepted_lock:
                        if cancelled.is_set():
                            conn.close()
                            return
                        accepted_box["socket"] = conn
                    ready.set()
                    return

            def accept_worker() -> None:
                try:
                    accept_loop()
                finally:
                    listener = listener_holder.get("listener")
                    if listener is not None and cancelled.is_set():
                        with listener._lock:
                            if listener._listener_closed:
                                listener.state = "CLOSED"

            if failure_at == "worker":
                raise ListenerError("worker_create_failed")
            worker = threading.Thread(target=accept_worker,
                                      name=f"type111-accept-{generation!s}", daemon=False)
            listener.worker = worker
            worker.start()
            if not ready.wait(timeout=1.0):
                raise ListenerError("worker_readiness_timeout")
            if worker_errors or not worker.is_alive():
                raise ListenerError("worker_not_ready")
            return listener
        except Exception as exc:
            cancelled.set()
            listener = locals().get("listener")
            if listener is not None:
                try:
                    listener.close()
                except ListenerError:
                    pass
            elif sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
            worker = locals().get("worker")
            if worker is not None and worker.is_alive():
                worker.join(timeout=1.0)
            if isinstance(exc, ListenerError):
                raise
            raise ListenerError("listener_prepare_failed") from exc

    def wait_accepted(self, timeout: float = 1.0) -> socket.socket | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._accepted_lock:
                accepted = self._accepted_box.pop("socket", None)
            if accepted is not None:
                with self._lock:
                    if not self.cancelled.is_set() and self.state == "READY":
                        self.accepted = accepted
                        self.state = "CONNECTED"
                        return accepted
                accepted.close()
                return None
            if not self.worker.is_alive():
                return None
            time.sleep(0.005)
        return None

    @property
    def worker_errors(self) -> tuple[str, ...]:
        return tuple(getattr(self, "_worker_errors", ()))

    def close(self, *, join_timeout: float = 1.0) -> None:
        with self._lock:
            if self.state == "CLOSED":
                return
            self.close_count += 1
            self.state = "CLOSING"
            self.cancelled.set()
            accepted = self.accepted
            self.accepted = None
            box = getattr(self, "_accepted_box", {})
            lock = getattr(self, "_accepted_lock", threading.Lock())
            with lock:
                if accepted is None:
                    accepted = box.pop("socket", None)
                else:
                    box.pop("socket", None)
            close_listener = not self._listener_closed
            self._listener_closed = True
            close_accepted = accepted is not None and not self._accepted_closed
            if close_accepted:
                self._accepted_closed = True
        if close_accepted:
            try:
                accepted.close()
            except OSError:
                pass
        if close_listener:
            try:
                self.sock.close()
            except OSError:
                pass
        if self.worker is threading.current_thread():
            # The owned worker's finally block marks CLOSED after this callback
            # returns; it must never join itself or escape ownership.
            return
        if self.worker.ident is not None:
            self.worker.join(timeout=join_timeout)
        with self._lock:
            if self.worker.is_alive():
                self.state = "CLOSE_FAILED"
                raise ListenerError("worker_join_timeout")
            self.state = "CLOSED"


class GenerationListenerRegistry:
    """Exact-key ownership; stale cleanup never looks up the current generation."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._listeners: dict[Hashable, PreparedListener] = {}

    def attach(self, generation: Hashable, listener: PreparedListener) -> None:
        if listener.generation != generation:
            listener.close()
            raise ListenerError("listener_generation_mismatch")
        with self._lock:
            if generation in self._listeners:
                listener.close()
                raise ListenerError("generation_listener_already_owned")
            self._listeners[generation] = listener

    def get(self, generation: Hashable) -> PreparedListener | None:
        with self._lock:
            return self._listeners.get(generation)

    def close_generation(self, generation: Hashable) -> bool:
        with self._lock:
            listener = self._listeners.pop(generation, None)
        if listener is None:
            return False
        listener.close()
        return True

    def close_all(self) -> None:
        with self._lock:
            owned, self._listeners = tuple(self._listeners.items()), {}
        failures = []
        for _generation, listener in owned:
            try:
                listener.close()
            except ListenerError:
                failures.append("listener_close_failed")
        if failures:
            raise ListenerError("generation_cleanup_failed")

    @property
    def owned_generations(self) -> tuple[Hashable, ...]:
        with self._lock:
            return tuple(self._listeners)


class RealListenerAllocator:
    """Adapter for the 43R SETUP contract, intended for host-only tests."""

    def __init__(self, policy: InterfacePolicy, *, failure_at: str | None = None) -> None:
        self.policy = policy
        self.failure_at = failure_at
        self._next_id = 1
        self._lock = threading.Lock()
        self.reservations: list[PreparedListener] = []

    def reserve(self, generation) -> PreparedListener:
        listener = PreparedListener.create(
            generation.key, self.policy, failure_at=self.failure_at,
            on_failure=lambda _code: generation.fail(),
        )
        with self._lock:
            listener.listener_id = self._next_id
            self._next_id += 1
        listener.owner_key = generation.key
        listener.generation_number = generation.generation
        try:
            from legacy_dual_screen_twin import ScreenRole
            listener.role = ScreenRole.TYPE111_SYNTHETIC
        except ImportError:
            listener.role = "TYPE111_SYNTHETIC"
        self.reservations.append(listener)
        return listener
