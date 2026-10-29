"""Synthetic tests for the bounded generation-gated FrameGate (CL-FACTORY-01 M5-C).

Offline only. No sockets, no secrets, no real stream.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "claritylink-transport"))

import pytest
import frame_gate as fg


def _f(gen, seq, ts, payload=None):
    return fg.Frame(generation=gen, sequence=seq, timestamp=ts, payload=payload)


def test_unopened_generation_rejects_until_begin():
    g = fg.FrameGate()
    assert g.offer(_f(1, 0, 0)) is fg.FrameStatus.UNOPENED_GENERATION
    g.begin_generation(1)
    assert g.offer(_f(1, 0, 0)) is fg.FrameStatus.ACCEPTED


def test_strictly_increasing_generation_required():
    g = fg.FrameGate()
    g.begin_generation(2)
    with pytest.raises(ValueError):
        g.begin_generation(2)
    with pytest.raises(ValueError):
        g.begin_generation(1)
    g.begin_generation(3)
    assert g.generation == 3


def test_old_generation_is_stale_and_new_generation_is_unopened():
    g = fg.FrameGate()
    g.begin_generation(5)
    assert g.offer(_f(4, 0, 0)) is fg.FrameStatus.STALE_GENERATION
    assert g.offer(_f(6, 0, 0)) is fg.FrameStatus.UNOPENED_GENERATION  # fail-closed: must open explicitly


def test_begin_generation_clears_prior_frames():
    g = fg.FrameGate()
    g.begin_generation(1)
    g.offer(_f(1, 0, 0))
    g.offer(_f(1, 1, 1))
    assert len(g) == 2
    g.begin_generation(2)
    assert len(g) == 0 and g.poll() is None


def test_out_of_order_and_duplicate_rejected():
    g = fg.FrameGate()
    g.begin_generation(1)
    assert g.offer(_f(1, 10, 100)) is fg.FrameStatus.ACCEPTED
    assert g.offer(_f(1, 10, 101)) is fg.FrameStatus.DUPLICATE
    assert g.offer(_f(1, 9, 102)) is fg.FrameStatus.OUT_OF_ORDER
    assert g.offer(_f(1, 11, 100)) is fg.FrameStatus.ACCEPTED  # ts equal is allowed (non-decreasing)
    assert g.offer(_f(1, 12, 99)) is fg.FrameStatus.STALE_TIMESTAMP


def test_drop_oldest_keeps_freshest():
    g = fg.FrameGate(capacity=2, policy=fg.BackpressurePolicy.DROP_OLDEST)
    g.begin_generation(1)
    for i in range(4):
        assert g.offer(_f(1, i, i)) is fg.FrameStatus.ACCEPTED
    assert g.stats.dropped_oldest == 2
    # the two freshest survive, in order
    assert g.poll().sequence == 2
    assert g.poll().sequence == 3
    assert g.poll() is None


def test_reject_new_when_full_is_fail_closed():
    g = fg.FrameGate(capacity=2, policy=fg.BackpressurePolicy.REJECT_NEW)
    g.begin_generation(1)
    assert g.offer(_f(1, 0, 0)) is fg.FrameStatus.ACCEPTED
    assert g.offer(_f(1, 1, 1)) is fg.FrameStatus.ACCEPTED
    assert g.offer(_f(1, 2, 2)) is fg.FrameStatus.REJECTED_FULL
    assert len(g) == 2


@pytest.mark.parametrize("death", ["on_source_death", "on_consumer_death", "close"])
def test_death_withdraws_and_refuses(death):
    g = fg.FrameGate()
    g.begin_generation(1)
    g.offer(_f(1, 0, 0))
    getattr(g, death)()
    assert g.closed is True
    assert len(g) == 0
    assert g.poll() is None
    assert g.offer(_f(1, 1, 1)) is fg.FrameStatus.CLOSED
    assert g.stats.closed_refusals == 1


def test_independent_streams_do_not_interfere():
    a = fg.FrameGate(); b = fg.FrameGate()
    a.begin_generation(1); b.begin_generation(7)
    assert a.offer(_f(1, 0, 0)) is fg.FrameStatus.ACCEPTED
    assert b.offer(_f(1, 0, 0)) is fg.FrameStatus.STALE_GENERATION
    a.close()
    assert b.closed is False
    assert b.offer(_f(7, 0, 0)) is fg.FrameStatus.ACCEPTED


def test_frame_validation_rejects_bad_fields():
    for bad in [(-1, 0, 0), (0, -1, 0), (0, 0, -1), (True, 0, 0)]:
        with pytest.raises(ValueError):
            fg.Frame(generation=bad[0], sequence=bad[1], timestamp=bad[2])


def test_capacity_must_be_positive():
    with pytest.raises(ValueError):
        fg.FrameGate(capacity=0)
