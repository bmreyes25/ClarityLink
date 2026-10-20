"""CL-R9E offline composition: lab media cannot acquire Honda authority.

All receiver/setup authority and frames in this test are synthetic CL-R7 lab
fixtures. It verifies isolation across the existing lab pipeline and the
disabled Honda boundaries; it is not Honda compatibility evidence.
"""
from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-jmcs"))

from claritylink_jmcs.compat.honda import (  # noqa: E402
    EvidenceRequired,
    HondaHackFrameAdmissionGate,
    HondaStaticType110Adapter,
)
from claritylink_jmcs.capabilities import SecondaryDisplayCapability  # noqa: E402
from claritylink_jmcs.display import NullDisplay  # noqa: E402
from claritylink_jmcs.identity import LabIdentity  # noqa: E402
from claritylink_jmcs.info import InfoProfile  # noqa: E402
from claritylink_jmcs.media import encode_lab_message  # noqa: E402
from claritylink_jmcs.receiver import Receiver  # noqa: E402


def synthetic_h264() -> bytes:
    result = subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
         "-i", "color=c=blue:s=64x48:r=1", "-frames:v", "1", "-c:v", "libx264",
         "-threads", "1", "-preset", "ultrafast", "-f", "h264", "pipe:1"],
        check=True, capture_output=True, timeout=10,
    )
    return result.stdout


def synthetic_info_profile() -> InfoProfile:
    return InfoProfile(
        identity=LabIdentity(
            "02:00:00:00:00:01",
            "b7e6c5a0-1111-4000-8000-000000000001",
            "b7e6c5a0-2222-4000-8000-000000000002",
        ),
        name="ClarityLink Synthetic Receiver",
        model="LAB",
        manufacturer="ClarityLink",
        source_version="CL-R9E_MODEL_ONLY",
        feature_bits=0,
        audio_formats=({"type": 1, "audioType": 1, "audioOutputFormats": 1},),
        audio_latencies=({"type": 1, "inputLatencyMicros": 0, "outputLatencyMicros": 0},),
        hid_devices=({"uuid": "lab-hid", "name": "Lab Input", "displayUUID":
                      "b7e6c5a0-1111-4000-8000-000000000001", "hidDescriptor": b"\x00",
                      "hidProductID": 1, "hidVendorID": 1, "hidCountryCode": 0},),
        displays=SecondaryDisplayCapability.synthetic_lab(width=800, height=480),
    )


@pytest.mark.parametrize("order", [(110, 111), (111, 110)])
def test_synthetic_dual_stream_stops_at_disabled_honda_boundaries(order):
    primary_sink = NullDisplay()
    secondary_sink = NullDisplay()
    receiver = Receiver(
        clear_lab=True,
        primary_display=primary_sink,
        display=secondary_sink,
        primary_dimensions=(800, 480),
        secondary_dimensions=(800, 480),
    )
    primary_client = secondary_client = None
    generation = receiver.start_session()
    try:
        authority = receiver.authenticated_session
        assert authority is not None
        assert authority.generation == generation
        assert authority.evidence == "MODEL_ONLY"
        assert receiver.exchange_info(synthetic_info_profile(), generation).startswith(b"bplist00")

        streams = [
            {"type": kind, "streamConnectionID": 11001 if kind == 110 else 11101}
            for kind in order
        ]
        response = receiver.setup({"streams": streams}, generation)
        assert {item["type"] for item in response.fields["streams"]} == {110, 111}

        adapter = HondaStaticType110Adapter()
        parsed_primary = adapter.parse_known_request(
            {"streams": [{"type": 110, "streamConnectionID": 11001}]}, generation
        )
        assert [stream.type for stream in parsed_primary.streams] == [110]
        assert adapter.known_response_entry(41001) == {"type": 110, "dataPort": 41001}
        with pytest.raises(EvidenceRequired, match="honda_type111_setup_dispatch"):
            adapter.parse_known_request({"streams": streams}, generation)

        primary_client = socket.create_connection(("127.0.0.1", receiver.primary.port), timeout=2)
        secondary_client = socket.create_connection(("127.0.0.1", receiver.secondary.port), timeout=2)
        receiver.accept_primary(generation)
        receiver.accept_secondary(generation)
        primary_client.sendall(encode_lab_message(0, synthetic_h264(), timestamp=110))
        secondary_client.sendall(encode_lab_message(0, synthetic_h264(), timestamp=111))
        primary_png = receiver.receive_primary_frame(generation)
        secondary_png = receiver.receive_secondary_frame(generation)

        assert primary_png.startswith(b"\x89PNG\r\n\x1a\n")
        assert secondary_png.startswith(b"\x89PNG\r\n\x1a\n")
        assert primary_sink.current.timestamp == 110
        assert primary_sink.current.generation == generation
        assert secondary_sink.current.timestamp == 111
        assert secondary_sink.current.generation == generation

        # A decoded synthetic frame and model-only authority still cannot
        # cross into a Honda output contract that has not been documented.
        assert HondaHackFrameAdmissionGate.ENABLED is False
        with pytest.raises(EvidenceRequired, match="hondahack_frame_admission_unverified"):
            HondaHackFrameAdmissionGate.require_supported_frame_admission()
        with pytest.raises(TypeError):
            HondaHackFrameAdmissionGate.require_supported_frame_admission(frame=secondary_png)
        assert primary_sink.current.timestamp == 110  # Type110 lab output stays independent.
    finally:
        if primary_client is not None:
            primary_client.close()
        if secondary_client is not None:
            secondary_client.close()
        receiver.teardown(generation)
    assert primary_sink.current is None and secondary_sink.current is None
    snapshot = receiver.snapshot()
    assert (snapshot.sessions, snapshot.primary_listeners, snapshot.secondary_listeners,
            snapshot.security_contexts, snapshot.decoders, snapshot.displayed_frames,
            snapshot.display_uncleared) == (0, 0, 0, 0, 0, 0, 0)
