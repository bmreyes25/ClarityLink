"""Single-owner host runtime joining control sessions and independent media streams.

This coordinator is laboratory software. It does not own Honda's factory
receiver, authentication, primary stream, or displays.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
import threading
from typing import Mapping

from .receiver import ReceiverError, ResourceSnapshot
from .session import ReceiverSession
from .session_transport import ControlResponse, ReplaySessionTransport


class RuntimeErrorState(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class RuntimeState(str, Enum):
    NEW = "NEW"
    STARTING = "STARTING"
    ACTIVE = "ACTIVE"
    STOPPING = "STOPPING"
    CLOSED = "CLOSED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class RuntimeEvent:
    name: str
    generation: int
    stream_type: int | None = None
    reason: str | None = None


@dataclass(frozen=True)
class RuntimeSnapshot:
    state: RuntimeState
    generation: int
    workers: tuple[tuple[int, bool], ...]
    receiver: ResourceSnapshot
    cleanup_complete: bool | None


class DualDisplayRuntime:
    """Own one ReceiverSession and one worker per negotiated stream.

    The session manager remains the only control-protocol owner. Type110 and
    Type111 media each get a separate worker; Receiver owns their listeners,
    per-stream security, decoders and display outputs. Closing this runtime
    withdraws only these project-owned resources and never restarts a target.
    """

    def __init__(self, session: ReceiverSession, *, worker_join_timeout: float = 5.0) -> None:
        if not isinstance(session, ReceiverSession):
            raise ValueError("receiver session required")
        if not 0.1 <= worker_join_timeout <= 30.0:
            raise ValueError("worker join timeout outside 0.1..30 seconds")
        self.session = session
        self.receiver = session.receiver
        self.worker_join_timeout = worker_join_timeout
        self._condition = threading.Condition(threading.RLock())
        self._close_lock = threading.Lock()
        self._stop = threading.Event()
        self._state = RuntimeState.NEW
        self._generation = 0
        self._workers: dict[int, threading.Thread] = {}
        self._events: list[RuntimeEvent] = []
        self._cleanup_complete: bool | None = None

    @property
    def state(self) -> RuntimeState:
        with self._condition:
            return self._state

    @property
    def events(self) -> tuple[RuntimeEvent, ...]:
        with self._condition:
            return tuple(self._events)

    def start(self, replay_transport: ReplaySessionTransport | None = None) -> int:
        with self._condition:
            if self._state is not RuntimeState.NEW:
                raise RuntimeErrorState("runtime_already_started")
            self._state = RuntimeState.STARTING
        try:
            self.session.open(replay_transport)
            if self.session.generation is None:
                raise RuntimeErrorState("session_generation_missing")
            with self._condition:
                self._generation = self.session.generation
                self._state = RuntimeState.ACTIVE
                self._record_locked("runtime_started")
                return self._generation
        except Exception:
            try:
                self.session.close()
            finally:
                with self._condition:
                    self._state = RuntimeState.FAILED
                    self._record_locked("runtime_start_failed", reason="session_open_failed")
            raise

    def handle_control_once(self, timeout: float = 5.0) -> ControlResponse:
        with self._condition:
            if self._state is not RuntimeState.ACTIVE:
                raise RuntimeErrorState("runtime_not_active")
        try:
            response = self.session.handle_one(timeout)
            streams = response.body.get("streams") if isinstance(response.body, Mapping) else None
            if isinstance(streams, (list, tuple)):
                negotiated = {item.get("type") for item in streams if isinstance(item, Mapping)}
                for stream_type in (110, 111):
                    if stream_type in negotiated:
                        self._start_stream_worker(stream_type)
            return response
        except Exception:
            self.close()
            raise

    def wait_for_event(self, name: str, timeout: float = 5.0,
                       stream_type: int | None = None) -> RuntimeEvent | None:
        if not name or len(name) > 64 or timeout < 0 or timeout > 30:
            raise ValueError("invalid event wait")
        with self._condition:
            found = self._find_event(name, stream_type)
            if found is not None:
                return found
            self._condition.wait_for(
                lambda: self._find_event(name, stream_type) is not None or
                self._state in (RuntimeState.CLOSED, RuntimeState.FAILED), timeout)
            return self._find_event(name, stream_type)

    def snapshot(self) -> RuntimeSnapshot:
        with self._condition:
            workers = tuple(sorted((kind, worker.is_alive())
                                   for kind, worker in self._workers.items()))
            return RuntimeSnapshot(self._state, self._generation, workers,
                                   self.receiver.snapshot(), self._cleanup_complete)

    def close(self) -> bool:
        with self._close_lock:
            return self._close_once()

    def _close_once(self) -> bool:
        with self._condition:
            if self._state is RuntimeState.STARTING:
                raise RuntimeErrorState("runtime_start_in_progress")
            if self._state is RuntimeState.CLOSED:
                return self._cleanup_complete is True
            if self._state is RuntimeState.NEW:
                self._state = RuntimeState.STOPPING
            elif self._state is RuntimeState.ACTIVE:
                self._state = RuntimeState.STOPPING
            elif self._state is RuntimeState.FAILED:
                self._state = RuntimeState.STOPPING
            self._stop.set()
            self._record_locked("runtime_stopping")
        session_error = False
        try:
            self.session.close()
        except Exception:
            session_error = True
        for worker in tuple(self._workers.values()):
            worker.join(self.worker_join_timeout)
        workers_stopped = all(not worker.is_alive() for worker in self._workers.values())
        resources = self.receiver.snapshot()
        clean = (not session_error and workers_stopped and resources.sessions == 0 and
                 resources.primary_listeners == 0 and resources.secondary_listeners == 0 and
                 resources.security_contexts == 0 and resources.decoders == 0 and
                 resources.displayed_frames == 0 and resources.display_uncleared == 0)
        with self._condition:
            self._cleanup_complete = clean
            self._state = RuntimeState.CLOSED if clean else RuntimeState.FAILED
            self._record_locked("runtime_closed" if clean else "runtime_cleanup_incomplete",
                                reason=None if clean else "owned_resources_remain")
            return clean

    def _start_stream_worker(self, stream_type: int) -> None:
        with self._condition:
            if self._state is not RuntimeState.ACTIVE or self._stop.is_set():
                return
            existing = self._workers.get(stream_type)
            if existing is not None:
                if existing.is_alive():
                    return
                raise RuntimeErrorState("stream_worker_already_finished")
            worker = threading.Thread(target=self._run_stream, args=(stream_type,),
                                      name=f"ClarityLinkType{stream_type}", daemon=True)
            self._workers[stream_type] = worker
            worker.start()
            self._record_locked("stream_worker_started", stream_type=stream_type)

    def _run_stream(self, stream_type: int) -> None:
        generation = self._generation
        try:
            if stream_type == 110:
                self.receiver.accept_primary(generation, timeout=5.0)
            else:
                self.receiver.accept_secondary(generation, timeout=5.0)
            self._record("stream_connected", stream_type=stream_type)
            while not self._stop.is_set():
                if stream_type == 110:
                    frame = self.receiver.receive_primary_frame(generation)
                else:
                    frame = self.receiver.receive_secondary_frame(generation)
                self._record("stream_frame" if frame else "stream_config",
                             stream_type=stream_type)
        except ReceiverError as exc:
            reason = self._safe_reason(getattr(exc, "code", "receiver_error"))
            if not self._stop.is_set():
                if stream_type == 111:
                    self.receiver.teardown_secondary(generation)
                else:
                    self.receiver.teardown_primary(generation)
            self._record("stream_stopped", stream_type=stream_type, reason=reason)
        except Exception as exc:
            reason = self._safe_reason(type(exc).__name__)
            if stream_type == 111:
                self.receiver.teardown_secondary(generation)
            else:
                self.receiver.teardown_primary(generation)
            self._record("stream_failed", stream_type=stream_type, reason=reason)

    def _record(self, name: str, *, stream_type: int | None = None,
                reason: str | None = None) -> None:
        with self._condition:
            self._record_locked(name, stream_type=stream_type, reason=reason)

    def _record_locked(self, name: str, *, stream_type: int | None = None,
                       reason: str | None = None) -> None:
        if len(self._events) >= 128:
            del self._events[:32]
        self._events.append(RuntimeEvent(name, self._generation, stream_type, reason))
        self._condition.notify_all()

    def _find_event(self, name: str, stream_type: int | None) -> RuntimeEvent | None:
        for event in reversed(self._events):
            if event.name == name and (stream_type is None or event.stream_type == stream_type):
                return event
        return None

    @staticmethod
    def _safe_reason(reason: object) -> str:
        text = str(reason)
        return text if len(text) <= 64 and re.fullmatch(r"[A-Za-z0-9_]+", text) else "runtime_error"
