"""Bounded, per-stream dispatch after H.264 decode in the host laboratory model."""
from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass
import queue
import threading
from typing import Any

from .decoder import DecodedFrame


PRIMARY_OUTPUT = 1
SECONDARY_OUTPUT = 2
MAX_STREAMS_PER_SESSION = 2
MAX_PENDING_FRAMES = 2  # Includes the frame currently inside the sink.
MAX_RETAINED_PNG_BYTES = 8 * 1024 * 1024  # Existing decoder output ceiling.


@dataclass(frozen=True)
class StreamIdentity:
    session_generation: int
    stream_type: int
    connection_id: int
    stream_generation: int
    output_id: int

    def valid(self) -> bool:
        expected_output = PRIMARY_OUTPUT if self.stream_type == 110 else (
            SECONDARY_OUTPUT if self.stream_type == 111 else None)
        return (all(isinstance(value, int) and not isinstance(value, bool) for value in
                    (self.session_generation, self.stream_type, self.connection_id,
                     self.stream_generation, self.output_id)) and
                self.session_generation > 0 and self.connection_id > 0 and
                self.stream_generation > 0 and expected_output is not None and
                self.output_id == expected_output)


@dataclass(frozen=True)
class DispatchSnapshot:
    identity: StreamIdentity
    outstanding_frames: int
    retained_bytes: int
    accepted: int
    rejected: int
    stale_dropped: int
    rendered: tuple[int, ...]
    closed: bool


@dataclass
class _FrameJob:
    identity: StreamIdentity
    frame: DecodedFrame
    completion: Future[bool]


class PerStreamFrameDispatcher:
    """One worker and hard count/byte bounds for already-decoded frames.

    The rejection policy is reject-new. It is safe for decoded frames because
    codec dependency handling has already happened upstream; compressed H.264
    access units must not use this queue's policy.
    """

    def __init__(self, identity: StreamIdentity, sink: Any, *,
                 max_frames: int = MAX_PENDING_FRAMES,
                 max_bytes: int = MAX_RETAINED_PNG_BYTES) -> None:
        if not identity.valid() or sink is None or max_frames < 1 or max_bytes < 1:
            raise ValueError("invalid_stream_dispatch_configuration")
        self.identity = identity
        self.sink = sink
        self.max_frames = max_frames
        self.max_bytes = max_bytes
        self._queue: queue.Queue[_FrameJob | None] = queue.Queue(maxsize=max_frames)
        self._lock = threading.RLock()
        self._draw_lock = threading.RLock()
        self._outstanding = 0
        self._retained_bytes = 0
        self._accepted = 0
        self._rejected = 0
        self._stale_dropped = 0
        self._rendered: list[int] = []
        self._closed = False
        self._transitioning = False
        self._sink_cleared = False
        self._worker = threading.Thread(target=self._run,
                                        name=f"ClarityLinkStream{identity.stream_type}", daemon=True)
        self._worker.start()

    def submit(self, identity: StreamIdentity, frame: DecodedFrame) -> Future[bool]:
        completion: Future[bool] = Future()
        size = (len(frame.png) if isinstance(frame, DecodedFrame) and isinstance(frame.png, bytes)
                else self.max_bytes + 1)
        with self._lock:
            if (self._closed or self._transitioning or identity != self.identity or not identity.valid() or
                    frame.generation != identity.stream_generation or size <= 0 or size > self.max_bytes or
                    self._outstanding >= self.max_frames or self._retained_bytes + size > self.max_bytes):
                self._rejected += 1
                completion.set_result(False)
                return completion
            job = _FrameJob(identity, frame, completion)
            try:
                self._queue.put_nowait(job)
            except queue.Full:
                self._rejected += 1
                completion.set_result(False)
                return completion
            self._outstanding += 1
            self._retained_bytes += size
            self._accepted += 1
        return completion

    def replace_generation(self, new_generation: int, *,
                           invalidated: threading.Event | None = None) -> StreamIdentity:
        with self._lock:
            if self._closed or self._transitioning or new_generation <= self.identity.stream_generation:
                raise ValueError("invalid_stream_generation_transition")
            self._transitioning = True
            self.identity = StreamIdentity(self.identity.session_generation, self.identity.stream_type,
                                           self.identity.connection_id, new_generation,
                                           self.identity.output_id)
            while True:
                try:
                    job = self._queue.get_nowait()
                except queue.Empty:
                    break
                if job is None:
                    continue
                self._outstanding -= 1
                self._retained_bytes -= len(job.frame.png)
                self._stale_dropped += 1
                job.completion.set_result(False)
                self._queue.task_done()
            identity = self.identity
        if invalidated is not None:
            invalidated.set()
        # Wait for any draw already past its final generation check, then clear
        # it before allowing submissions in the new generation.
        with self._draw_lock:
            self.sink.clear()
        with self._lock:
            self._transitioning = False
        return identity

    def snapshot(self) -> DispatchSnapshot:
        with self._lock:
            return DispatchSnapshot(self.identity, self._outstanding, self._retained_bytes,
                                    self._accepted, self._rejected, self._stale_dropped,
                                    tuple(self._rendered), self._closed)

    def close(self, timeout: float = 5.0) -> bool:
        with self._lock:
            if self._closed:
                pass
            else:
                self._closed = True
                while True:
                    try:
                        job = self._queue.get_nowait()
                    except queue.Empty:
                        break
                    if job is not None:
                        self._outstanding -= 1
                        self._retained_bytes -= len(job.frame.png)
                        self._stale_dropped += 1
                        job.completion.set_result(False)
                    self._queue.task_done()
                self._queue.put_nowait(None)
        self._worker.join(timeout)
        if self._worker.is_alive():
            return False
        with self._draw_lock:
            with self._lock:
                if self._sink_cleared:
                    return True
            try:
                self.sink.clear()
            except Exception:
                return False
            with self._lock:
                self._sink_cleared = True
        return True

    def _run(self) -> None:
        while True:
            job = self._queue.get()
            if job is None:
                self._queue.task_done()
                return
            try:
                with self._draw_lock:
                    with self._lock:
                        valid = not self._closed and job.identity == self.identity
                        if not valid:
                            self._stale_dropped += 1
                    if valid:
                        self.sink.show(job.frame)
                        with self._lock:
                            self._rendered.append(job.frame.timestamp)
                        job.completion.set_result(True)
                    else:
                        job.completion.set_result(False)
            except BaseException as failure:
                job.completion.set_exception(failure)
            finally:
                with self._lock:
                    self._outstanding -= 1
                    self._retained_bytes -= len(job.frame.png)
                self._queue.task_done()


class StreamDispatchRegistry:
    """Session-scoped stream identity registry with independent output queues."""

    def __init__(self, session_generation: int) -> None:
        if session_generation <= 0:
            raise ValueError("invalid_session_generation")
        self.session_generation = session_generation
        self._lock = threading.RLock()
        self._dispatchers: dict[int, PerStreamFrameDispatcher] = {}
        self._connection_ids: set[int] = set()

    def register(self, identity: StreamIdentity, sink: Any) -> PerStreamFrameDispatcher:
        with self._lock:
            if (not identity.valid() or identity.session_generation != self.session_generation or
                    identity.stream_type in self._dispatchers or
                    identity.connection_id in self._connection_ids or
                    len(self._dispatchers) >= MAX_STREAMS_PER_SESSION):
                raise ValueError("stream_identity_conflict")
            dispatcher = PerStreamFrameDispatcher(identity, sink)
            self._dispatchers[identity.stream_type] = dispatcher
            self._connection_ids.add(identity.connection_id)
            return dispatcher

    def dispatcher(self, identity: StreamIdentity) -> PerStreamFrameDispatcher:
        with self._lock:
            dispatcher = self._dispatchers.get(identity.stream_type)
            if dispatcher is None or dispatcher.snapshot().identity != identity:
                raise ValueError("unknown_or_stale_stream_identity")
            return dispatcher

    def dispatch(self, identity: StreamIdentity, frame: DecodedFrame) -> Future[bool]:
        return self.dispatcher(identity).submit(identity, frame)

    def replace_generation(self, stream_type: int, new_generation: int, *,
                           invalidated: threading.Event | None = None) -> StreamIdentity:
        with self._lock:
            dispatcher = self._dispatchers.get(stream_type)
            if dispatcher is None:
                raise ValueError("unknown_stream_type")
            return dispatcher.replace_generation(new_generation, invalidated=invalidated)

    def close_stream(self, stream_type: int, timeout: float = 5.0) -> bool:
        with self._lock:
            dispatcher = self._dispatchers.get(stream_type)
            if dispatcher is None:
                return True
        closed = dispatcher.close(timeout)
        if closed:
            with self._lock:
                if self._dispatchers.get(stream_type) is dispatcher:
                    self._dispatchers.pop(stream_type)
                    self._connection_ids.discard(dispatcher.identity.connection_id)
        return closed

    def close(self, timeout: float = 5.0) -> bool:
        with self._lock:
            dispatchers = tuple(self._dispatchers.values())
        results = [dispatcher.close(timeout) for dispatcher in dispatchers]
        if all(results):
            with self._lock:
                self._dispatchers.clear()
                self._connection_ids.clear()
        return all(results)

    def snapshots(self) -> dict[int, DispatchSnapshot]:
        with self._lock:
            return {stream_type: dispatcher.snapshot()
                    for stream_type, dispatcher in self._dispatchers.items()}
