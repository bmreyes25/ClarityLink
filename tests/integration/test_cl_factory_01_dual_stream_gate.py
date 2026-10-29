"""CL-FACTORY-01 / M7 — synthetic dual-stream integration.

Composes the real project modules end to end with SYNTHETIC inputs only:
  * two independent FrameGate instances model Type110 (center) and Type111 (cluster),
  * Type111Lifecycle models the secondary-stream generation lifecycle,
  * FactoryIntegrationContract keeps all factory-facing action fail-closed.

No iPhone, no authentication, no vehicle. Nothing here is a genuine Type111
session; frames are fabricated. safeForHonda() stays False.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-transport"))
sys.path.insert(0, str(ROOT / "src" / "claritylink-negotiation"))
sys.path.insert(0, str(ROOT / "src" / "claritylink-honda"))

import pytest
import frame_gate as fg
import lifecycle as lc
import factory_integration_contract as fic


def _frame(gen, seq, ts):
    return fg.Frame(generation=gen, sequence=seq, timestamp=ts, payload=b"synthetic")


def _make_pair():
    t110 = fg.FrameGate(capacity=4)
    t111 = fg.FrameGate(capacity=4)
    life = lc.Type111Lifecycle()
    contract = fic.default_fail_closed_contract()  # all factory facts UNKNOWN
    return t110, t111, life, contract


@pytest.mark.parametrize("order", ["type110_first", "type111_first"])
def test_both_setup_orders_yield_independent_streams(order):
    t110, t111, life, _ = _make_pair()
    if order == "type110_first":
        t110.begin_generation(1)
        gen = life.prepare(stream_connection_id=0x1001, data_port=41000); t111.begin_generation(gen)
    else:
        gen = life.prepare(stream_connection_id=0x1001, data_port=41000); t111.begin_generation(gen)
        t110.begin_generation(1)
    life.mark_advertised(); life.mark_active()
    assert t110.offer(_frame(1, 0, 0)) is fg.FrameStatus.ACCEPTED
    assert t111.offer(_frame(gen, 0, 0)) is fg.FrameStatus.ACCEPTED
    # streams are independent instances: each buffers only its own frame, and
    # draining or closing one leaves the other intact.
    assert len(t110) == 1 and len(t111) == 1
    assert t110.poll().payload == b"synthetic"
    assert len(t110) == 0 and len(t111) == 1  # draining Type110 did not touch Type111
    t110.close()
    assert t110.closed is True and t111.closed is False
    assert t111.poll().payload == b"synthetic"


def test_type111_restart_bumps_generation_and_discards_stale_frames():
    _, t111, life, _ = _make_pair()
    g1 = life.prepare(0x1001, 41000); t111.begin_generation(g1)
    t111.offer(_frame(g1, 0, 0)); t111.offer(_frame(g1, 1, 1))
    assert len(t111) == 2
    # reconnect: new generation
    g2 = life.prepare(0x1002, 41001); t111.begin_generation(g2)
    assert g2 == g1 + 1
    assert len(t111) == 0  # stale frames discarded
    assert t111.offer(_frame(g1, 2, 2)) is fg.FrameStatus.STALE_GENERATION
    assert t111.offer(_frame(g2, 0, 0)) is fg.FrameStatus.ACCEPTED


def test_warning_withdrawal_stops_custom_content_but_type110_untouched():
    t110, t111, life, contract = _make_pair()
    t110.begin_generation(1)
    g = life.prepare(0x1001, 41000); t111.begin_generation(g)
    t111.offer(_frame(g, 0, 0))
    # a factory warning: always-win withdrawal of custom (Type111) content
    assert contract.withdraw_for_warning().allowed is True
    t111.on_source_death()  # model: withdraw the custom stream
    assert t111.closed is True and t111.poll() is None
    # Type110 center display continuity is unaffected
    assert t110.offer(_frame(1, 0, 0)) is fg.FrameStatus.ACCEPTED
    assert t110.poll() is not None


def test_host_death_closes_both_gates_and_factory_frames_stay_denied():
    t110, t111, life, contract = _make_pair()
    t110.begin_generation(1)
    g = life.prepare(0x1001, 41000); t111.begin_generation(g)
    # host death -> tear everything down
    contract.on_host_death()
    t110.close(); t111.close()
    life.teardown()
    assert t110.closed and t111.closed
    # even after a (hypothetical) factory-proven attempt, frames are blocked by the guard
    d = contract.submit_frame_to_factory(evidence_tier=fic.EvidenceTier.FACTORY_PROVEN)
    assert d.allowed is False and d.reason_code == fic.R_SAFE_FOR_HONDA_FALSE


def test_backpressure_keeps_freshest_under_load():
    _, t111, life, _ = _make_pair()
    g = life.prepare(0x1001, 41000); t111.begin_generation(g)
    for i in range(10):
        assert t111.offer(_frame(g, i, i)) is fg.FrameStatus.ACCEPTED
    # capacity 4 -> only the 4 freshest remain, in order
    seqs = []
    while (f := t111.poll()) is not None:
        seqs.append(f.sequence)
    assert seqs == [6, 7, 8, 9]
    assert t111.stats.dropped_oldest == 6


def test_contract_never_admits_on_synthetic_evidence_in_this_harness():
    _, _, _, contract = _make_pair()
    # the whole harness is synthetic; it must never flip the factory gate open
    assert contract.admit_receiver_session(evidence_tier=fic.EvidenceTier.SYNTHETIC).allowed is False
    assert contract.safe_for_honda() is False
