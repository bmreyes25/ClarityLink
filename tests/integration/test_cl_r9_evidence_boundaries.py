"""Synthetic contract join kept separate from both disabled Honda edges."""
from dataclasses import replace
from pathlib import Path
import struct
import sys
import zlib

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-renderer"))
sys.path.insert(0, str(ROOT / "src/claritylink-jmcs"))

from honda_output import HondaDisplay1OutputAdapter, HondaDisplayEvidenceRequired
from claritylink_jmcs.compat.honda.setup import EvidenceRequired, HondaStaticType110Adapter
from claritylink_jmcs.decoder import DecodedFrame
from claritylink_jmcs.display import NullDisplay
from claritylink_jmcs.receiver import Receiver, ReceiverError


class SyntheticWarningGatedOutput(NullDisplay):
    """Explicit lab-only display fixture; it does not model Honda authority."""

    synthetic_only = True

    def __init__(self):
        super().__init__()
        self.generation = None
        self.warning_active = False
        self.withheld = []

    def begin_generation(self, generation):
        self.clear()
        self.generation = generation

    def show(self, frame):
        if frame.generation != self.generation:
            raise ValueError("stale_synthetic_output_generation")
        if self.warning_active:
            self.withheld.append(frame.timestamp)
            return
        super().show(frame)

    def warning_preempted(self):
        self.warning_active = True
        self.clear()

    def warning_cleared(self):
        self.warning_active = False
        # A fresh decoded frame is required; do not resurrect the old frame.


def _request(kind, connection_id):
    return {"streams": [{"type": kind, "streamConnectionID": connection_id}]}


def _frame(timestamp, generation):
    # Dispatch checks ownership/lifecycle here; pixel decode is covered by the
    # existing CL-R7 and API17 acceptance. This fixture is deliberately synthetic.
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n" +
           chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) +
           chunk(b"IDAT", zlib.compress(b"\x00\x20\x80\xe0\xff")) +
           chunk(b"IEND", b""))
    return DecodedFrame(png, timestamp, generation, 1, 1)


@pytest.mark.parametrize("order", [(110, 111), (111, 110)])
def test_synthetic_contract_join_preserves_type110_and_type111_lifecycle(order):
    primary_output = NullDisplay()
    secondary_output = SyntheticWarningGatedOutput()
    receiver = Receiver(clear_lab=True, primary_display=primary_output, display=secondary_output)
    generation = receiver.start_session()
    session = receiver.authenticated_session
    assert session is not None
    assert session.evidence == "MODEL_ONLY"
    assert session.generation == generation
    receiver.info_exchanged(generation)

    # This receiver is explicitly a MODEL_ONLY laboratory provider.
    for stream_type in order:
        receiver.setup(_request(stream_type, 1100 if stream_type == 110 else 1101), generation)
    primary_identity = receiver.stream_identity(110)
    secondary_identity = receiver.stream_identity(111)
    assert (primary_identity.session_generation, primary_identity.stream_type,
            primary_identity.connection_id, primary_identity.stream_generation,
            primary_identity.output_id) == (generation, 110, 1100, generation, 1)
    assert (secondary_identity.session_generation, secondary_identity.stream_type,
            secondary_identity.connection_id, secondary_identity.stream_generation,
            secondary_identity.output_id) == (generation, 111, 1101, generation, 2)

    assert receiver.dispatch_decoded_frame(primary_identity, _frame(10, generation))
    assert receiver.dispatch_decoded_frame(secondary_identity, _frame(20, generation))
    assert primary_output.current.timestamp == 10
    assert secondary_output.current.timestamp == 20

    secondary_output.warning_preempted()
    assert secondary_output.current is None
    assert receiver.dispatch_decoded_frame(secondary_identity, _frame(21, generation))
    assert secondary_output.current is None and secondary_output.withheld == [21]
    secondary_output.warning_cleared()
    assert secondary_output.current is None
    assert receiver.dispatch_decoded_frame(secondary_identity, _frame(22, generation))
    assert secondary_output.current.timestamp == 22

    stale = replace(secondary_identity, session_generation=generation + 1)
    with pytest.raises(ReceiverError, match="stale_or_conflicting_stream_identity"):
        receiver.enqueue_decoded_frame(stale, _frame(23, generation))

    receiver.teardown_secondary(generation)
    assert receiver.primary is not None
    assert receiver.dispatch_decoded_frame(primary_identity, _frame(11, generation))
    assert primary_output.current.timestamp == 11
    with pytest.raises(ReceiverError, match="stream_not_registered"):
        receiver.stream_identity(111)

    receiver.teardown(generation)
    snapshot = receiver.snapshot()
    assert (snapshot.sessions, snapshot.primary_listeners, snapshot.secondary_listeners,
            snapshot.security_contexts, snapshot.decoders, snapshot.displayed_frames,
            snapshot.display_uncleared) == (0, 0, 0, 0, 0, 0, 0)
    assert receiver.authenticated_session is None


def test_honda_edges_fail_closed_without_a_lab_fallback_or_sink():
    honda_receiver = HondaStaticType110Adapter()
    type110 = honda_receiver.parse_known_request(_request(110, 1100), generation=8)
    assert type110.streams[0].stream_connection_id == 1100
    with pytest.raises(EvidenceRequired, match="honda_type111_setup_dispatch"):
        honda_receiver.parse_known_request(_request(111, 1101), generation=8)

    class UnexpectedSink:
        def __init__(self):
            self.calls = []

        def attach(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    sink = UnexpectedSink()
    honda_output = HondaDisplay1OutputAdapter()
    assert honda_output.enabled is False
    with pytest.raises(HondaDisplayEvidenceRequired) as blocked:
        honda_output.attach(sink, {"owner_authorized": True, "generation": 8,
                                   "stream_id": 1101, "display_id": 1})
    assert blocked.value.code == "EVIDENCE_REQUIRED_HONDA_DISPLAY_ADMISSION_API"
    assert sink.calls == []

    # These adapters have no reference to Receiver or a synthetic authority;
    # Type111 refusal cannot dispatch into the lab provider by itself.
