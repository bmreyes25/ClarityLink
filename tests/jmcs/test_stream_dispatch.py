from __future__ import annotations

import threading
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src/claritylink-jmcs"))

from claritylink_jmcs.decoder import DecodedFrame
from claritylink_jmcs.display import NullDisplay
from claritylink_jmcs.stream_dispatch import (
    PRIMARY_OUTPUT,
    SECONDARY_OUTPUT,
    StreamDispatchRegistry,
    StreamIdentity,
)


def _frame(timestamp: int, generation: int, size: int = 16) -> DecodedFrame:
    return DecodedFrame(b"x" * size, timestamp, generation, 2, 2)


def _identity(session: int, stream_type: int, connection_id: int,
              stream_generation: int | None = None) -> StreamIdentity:
    return StreamIdentity(session, stream_type, connection_id,
                          session if stream_generation is None else stream_generation,
                          PRIMARY_OUTPUT if stream_type == 110 else SECONDARY_OUTPUT)


def test_type111_saturation_does_not_block_type110_and_bounds_resources():
    secondary_entered = threading.Event()
    release_secondary = threading.Event()

    class BlockedDisplay(NullDisplay):
        def show(self, frame):
            secondary_entered.set()
            if not release_secondary.wait(5):
                raise AssertionError("Type111 barrier was not released")
            super().show(frame)

    primary, secondary = NullDisplay(), BlockedDisplay()
    registry = StreamDispatchRegistry(session_generation=7)
    type110 = _identity(7, 110, 1107)
    type111 = _identity(7, 111, 1117)
    registry.register(type110, primary)
    registry.register(type111, secondary)
    first = registry.dispatch(type111, _frame(201, 7, 128))
    assert secondary_entered.wait(3), "Type111 worker did not enter the sink"
    pending = registry.dispatch(type111, _frame(202, 7, 256))
    rejected = registry.dispatch(type111, _frame(203, 7, 512))
    assert not pending.done()
    assert rejected.done() and rejected.result() is False

    primary_future = registry.dispatch(type110, _frame(101, 7, 64))
    assert primary_future.result(timeout=3) is True
    assert primary.current.timestamp == 101
    assert secondary.current is None
    snapshot = registry.snapshots()
    assert snapshot[111].outstanding_frames == 2
    assert snapshot[111].retained_bytes == 384
    assert snapshot[111].accepted == 2 and snapshot[111].rejected == 1
    assert snapshot[110].rendered == (101,)
    assert snapshot[110].retained_bytes == 0

    release_secondary.set()
    assert first.result(timeout=3) is True
    assert pending.result(timeout=3) is True
    assert secondary.current.timestamp == 202  # newest accepted backlog; 203 was rejected
    assert registry.snapshots()[111].rendered == (201, 202)
    assert registry.close()
    assert primary.current is None and secondary.current is None
    assert all(s.outstanding_frames == 0 and s.retained_bytes == 0
               for s in registry.snapshots().values())


def test_registry_rejects_conflicting_outputs_ids_and_stale_session_frames():
    registry = StreamDispatchRegistry(session_generation=8)
    type110 = _identity(8, 110, 810)
    registry.register(type110, NullDisplay())
    with pytest.raises(ValueError, match="stream_identity_conflict"):
        registry.register(_identity(8, 111, 810), NullDisplay())
    with pytest.raises(ValueError, match="stream_identity_conflict"):
        registry.register(StreamIdentity(8, 111, 811, 8, PRIMARY_OUTPUT), NullDisplay())
    with pytest.raises(ValueError, match="stream_identity_conflict"):
        registry.register(_identity(9, 111, 811), NullDisplay())
    with pytest.raises(ValueError, match="unknown_or_stale_stream_identity"):
        registry.dispatch(_identity(8, 110, 810, stream_generation=9), _frame(1, 9))
    assert registry.close()


def test_generation_change_discards_queued_stale_frames_and_clears_sink():
    entered = threading.Event()
    release = threading.Event()

    class BlockedDisplay(NullDisplay):
        def show(self, frame):
            entered.set()
            if not release.wait(5):
                raise AssertionError("generation test barrier was not released")
            super().show(frame)

    display = BlockedDisplay()
    registry = StreamDispatchRegistry(session_generation=10)
    identity = _identity(10, 111, 1011)
    registry.register(identity, display)
    in_flight = registry.dispatch(identity, _frame(1, 10))
    assert entered.wait(3)
    stale = registry.dispatch(identity, _frame(2, 10))
    assert registry.snapshots()[111].outstanding_frames == 2

    changed: list[StreamIdentity] = []
    invalidated = threading.Event()
    transition = threading.Thread(target=lambda: changed.append(
        registry.replace_generation(111, 11, invalidated=invalidated)))
    transition.start()
    assert invalidated.wait(3), "generation was not invalidated before clearing the active draw"
    assert not stale.done() or stale.result() is False
    release.set()
    transition.join(3)
    assert not transition.is_alive()
    assert in_flight.result(timeout=1) is True
    assert stale.result(timeout=1) is False
    new_identity = changed[0]
    assert new_identity.stream_generation == 11
    assert display.current is None
    with pytest.raises(ValueError, match="unknown_or_stale_stream_identity"):
        registry.dispatch(identity, _frame(3, 10))
    assert registry.dispatch(new_identity, _frame(4, 11)).result(timeout=3) is True
    assert display.current.timestamp == 4
    assert registry.close()


def test_dispatcher_rejects_wrong_session_type_connection_and_dimension_payload():
    display = NullDisplay()
    registry = StreamDispatchRegistry(session_generation=12)
    identity = _identity(12, 111, 1211)
    registry.register(identity, display)
    with pytest.raises(ValueError, match="unknown_or_stale_stream_identity"):
        registry.dispatch(_identity(13, 111, 1211), _frame(1, 12))
    invalid_type = StreamIdentity(12, 112, 1212, 12, SECONDARY_OUTPUT)
    with pytest.raises(ValueError, match="unknown_or_stale_stream_identity"):
        registry.dispatch(invalid_type, _frame(2, 12))
    assert registry.dispatch(identity, _frame(3, 12, 9 * 1024 * 1024)).result() is False
    assert registry.snapshots()[111].rejected == 1
    assert registry.close()
