"""Bounded, generation-gated secondary-stream frame delivery (CL-FACTORY-01 / M5-C).

Original, offline, synthetic-only transport primitive. It sits between a decoded-
frame producer (see ``receiver_core``) and a presentation consumer (see
``presentation_stream``) and enforces, per stream, independent of any other stream:

  * per-generation frame ownership -- frames tagged with an older generation are
    rejected; a new generation must be opened explicitly via ``begin_generation``
    (fail-closed: a newer generation is not auto-adopted).
  * freshness -- sequence numbers strictly increase and timestamps are
    non-decreasing within a generation; replays and out-of-order frames are
    rejected rather than delivered.
  * bounded capacity with an explicit backpressure policy.
  * withdrawal on source/consumer death or close -- the queue is cleared and all
    further offers are refused.

No I/O, no secrets, no real stream. Payloads are held opaquely by reference; the
gate never inspects or decodes them.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any


class BackpressurePolicy(str, Enum):
    DROP_OLDEST = "DROP_OLDEST"   # keep freshest: drop the head to admit a new frame
    REJECT_NEW = "REJECT_NEW"     # fail-closed: refuse the new frame when full


class FrameStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    STALE_GENERATION = "STALE_GENERATION"
    UNOPENED_GENERATION = "UNOPENED_GENERATION"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    DUPLICATE = "DUPLICATE"
    STALE_TIMESTAMP = "STALE_TIMESTAMP"
    REJECTED_FULL = "REJECTED_FULL"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class Frame:
    generation: int
    sequence: int
    timestamp: int
    payload: Any = None

    def __post_init__(self) -> None:
        for name in ("generation", "sequence", "timestamp"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise ValueError(f"{name} must be a non-negative int")


@dataclass
class FrameGateStats:
    accepted: int = 0
    dropped_oldest: int = 0
    rejected_full: int = 0
    stale_generation: int = 0
    unopened_generation: int = 0
    out_of_order: int = 0
    duplicate: int = 0
    stale_timestamp: int = 0
    closed_refusals: int = 0
    delivered: int = 0


class FrameGate:
    def __init__(self, capacity: int = 8, policy: BackpressurePolicy = BackpressurePolicy.DROP_OLDEST) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be a positive int")
        self._capacity = capacity
        self._policy = policy
        self._generation: int | None = None
        self._last_seq: int | None = None
        self._last_ts: int | None = None
        self._queue: deque[Frame] = deque()
        self._closed = False
        self.stats = FrameGateStats()

    # ---- lifecycle ----
    @property
    def generation(self) -> int | None:
        return self._generation

    @property
    def closed(self) -> bool:
        return self._closed

    def __len__(self) -> int:
        return len(self._queue)

    def begin_generation(self, generation: int) -> None:
        """Open a new, strictly greater generation. Clears any buffered frames
        from the prior generation (a new stream owns a fresh buffer)."""
        if self._closed:
            raise RuntimeError("gate is closed")
        if isinstance(generation, bool) or not isinstance(generation, int) or generation < 1:
            raise ValueError("generation must be a positive int")
        if self._generation is not None and generation <= self._generation:
            raise ValueError("generation must strictly increase")
        self._generation = generation
        self._last_seq = None
        self._last_ts = None
        self._queue.clear()

    def offer(self, frame: Frame) -> FrameStatus:
        if self._closed:
            self.stats.closed_refusals += 1
            return FrameStatus.CLOSED
        if self._generation is None or frame.generation > self._generation:
            self.stats.unopened_generation += 1
            return FrameStatus.UNOPENED_GENERATION
        if frame.generation < self._generation:
            self.stats.stale_generation += 1
            return FrameStatus.STALE_GENERATION
        # same generation: enforce strict sequence ordering + non-decreasing ts
        if self._last_seq is not None:
            if frame.sequence == self._last_seq:
                self.stats.duplicate += 1
                return FrameStatus.DUPLICATE
            if frame.sequence < self._last_seq:
                self.stats.out_of_order += 1
                return FrameStatus.OUT_OF_ORDER
        if self._last_ts is not None and frame.timestamp < self._last_ts:
            self.stats.stale_timestamp += 1
            return FrameStatus.STALE_TIMESTAMP
        # bounded admission
        if len(self._queue) >= self._capacity:
            if self._policy is BackpressurePolicy.REJECT_NEW:
                self.stats.rejected_full += 1
                return FrameStatus.REJECTED_FULL
            self._queue.popleft()
            self.stats.dropped_oldest += 1
        self._queue.append(frame)
        self._last_seq = frame.sequence
        self._last_ts = frame.timestamp
        self.stats.accepted += 1
        return FrameStatus.ACCEPTED

    def poll(self) -> Frame | None:
        if self._closed or not self._queue:
            return None
        frame = self._queue.popleft()
        self.stats.delivered += 1
        return frame

    # ---- withdrawal (fail-safe) ----
    def on_source_death(self) -> None:
        self.close()

    def on_consumer_death(self) -> None:
        self.close()

    def close(self) -> None:
        self._queue.clear()
        self._closed = True
