"""Executable end-to-end synthetic Type110 + Type111 session acceptance."""
from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "claritylink-jmcs"))

from claritylink_jmcs.capabilities import SecondaryDisplayCapability
from claritylink_jmcs.identity import LabIdentity
from claritylink_jmcs.info import InfoProfile
from claritylink_jmcs.receiver import FaultInjector, Receiver, ReceiverError
from claritylink_jmcs.display import NullDisplay


def _info_profile() -> InfoProfile:
    return InfoProfile(
        identity=LabIdentity("02:00:00:00:00:01", "b7e6c5a0-1111-4000-8000-000000000001",
                             "b7e6c5a0-2222-4000-8000-000000000002"),
        name="ClarityLink Synthetic Receiver", model="LAB", manufacturer="ClarityLink",
        source_version="R7A-MODEL_ONLY", feature_bits=0,
        audio_formats=({"type": 1, "audioType": 1, "audioOutputFormats": 1},),
        audio_latencies=({"type": 1, "inputLatencyMicros": 0, "outputLatencyMicros": 0},),
        hid_devices=({"uuid": "lab-hid", "name": "Lab Input", "displayUUID":
                      "b7e6c5a0-1111-4000-8000-000000000001", "hidDescriptor": b"\x00",
                      "hidProductID": 1, "hidVendorID": 1, "hidCountryCode": 0},),
        displays=SecondaryDisplayCapability(width=800, height=480),
    )


def _h264(color: str) -> bytes:
    result = subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
         f"color=c={color}:s=64x48:r=1", "-frames:v", "1", "-c:v", "libx264", "-threads", "1",
         "-preset", "ultrafast", "-f", "h264", "pipe:1"],
        check=True, capture_output=True, timeout=10,
    )
    return result.stdout


def _session(receiver: Receiver) -> int:
    generation = receiver.start_session()
    assert receiver.authenticated_session is not None
    assert receiver.authenticated_session.generation == generation
    assert receiver.authenticated_session.evidence == "MODEL_ONLY"
    info = receiver.exchange_info(_info_profile(), generation)
    assert info.startswith(b"bplist00")
    return generation


def test_r7a_one_session_delivers_decoded_frames_to_both_owned_outputs():
    from claritylink_jmcs.media import encode_lab_message

    primary_sink, secondary_sink = NullDisplay(), NullDisplay()
    receiver = Receiver(clear_lab=True, primary_display=primary_sink, display=secondary_sink,
                        primary_dimensions=(800, 480), secondary_dimensions=(800, 480))
    generation = _session(receiver)
    response = receiver.setup({"streams": [
        {"type": 110, "streamConnectionID": 1101},
        {"type": 111, "streamConnectionID": 1111},
    ]}, generation)
    assert [stream["type"] for stream in response.fields["streams"]] == [110, 111]

    primary_access = _h264("red")
    secondary_access = _h264("blue")
    primary_client = socket.create_connection(("127.0.0.1", receiver.primary.port), timeout=2)
    secondary_client = socket.create_connection(("127.0.0.1", receiver.secondary.port), timeout=2)
    try:
        receiver.accept_primary(generation)
        receiver.accept_secondary(generation)
        primary_client.sendall(encode_lab_message(0, primary_access, timestamp=10))
        secondary_client.sendall(encode_lab_message(0, secondary_access, timestamp=20))
        primary_png = receiver.receive_primary_frame(generation)
        secondary_png = receiver.receive_secondary_frame(generation)
        assert primary_png.startswith(b"\x89PNG\r\n\x1a\n")
        assert secondary_png.startswith(b"\x89PNG\r\n\x1a\n")
        assert primary_png != secondary_png
        assert (primary_sink.current.width, primary_sink.current.height) == (800, 480)
        assert (secondary_sink.current.width, secondary_sink.current.height) == (800, 480)
        assert primary_sink.current.timestamp == 10 and primary_sink.current.generation == generation
        assert secondary_sink.current.timestamp == 20 and secondary_sink.current.generation == generation
        assert receiver.frames == 2
    finally:
        primary_client.close()
        secondary_client.close()
    receiver.teardown(generation)
    assert receiver.snapshot().sessions == 0
    assert primary_sink.current is None and secondary_sink.current is None
    with pytest.raises(ReceiverError, match="stale_or_closed_session"):
        receiver.receive_primary_frame(generation)
    with pytest.raises(ReceiverError, match="stale_or_closed_session"):
        receiver.receive_secondary_frame(generation)


@pytest.mark.parametrize("order", [(111, 110), (110, 111), (110,), (111,)])
def test_stream_order_and_single_stream_configurations(order: tuple[int, ...]):
    receiver = Receiver(clear_lab=True)
    generation = _session(receiver)
    for stream_type in order:
        receiver.setup({"streams": [{"type": stream_type,
                                      "streamConnectionID": 5000 + stream_type}]}, generation)
    assert bool(receiver.primary) == (110 in order)
    assert bool(receiver.secondary) == (111 in order)
    receiver.teardown(generation)
    assert receiver.snapshot().sessions == 0


def test_type111_setup_failure_keeps_type110_active_and_type110_failure_is_clean():
    primary_survives = Receiver()  # Production security interface is fail closed.
    generation = _session(primary_survives)
    response = primary_survives.setup({"streams": [
        {"type": 110, "streamConnectionID": 1},
        {"type": 111, "streamConnectionID": 2},
    ]}, generation)
    assert [entry["type"] for entry in response.fields["streams"]] == [110]
    assert primary_survives.primary and not primary_survives.secondary
    primary_survives.teardown(generation)

    failed_primary = Receiver(clear_lab=True, faults=FaultInjector("primary_listener"))
    failed_generation = _session(failed_primary)
    with pytest.raises(ReceiverError, match="fault_primary_listener"):
        failed_primary.setup({"streams": [{"type": 110, "streamConnectionID": 3}]}, failed_generation)
    assert failed_primary.snapshot().primary_listeners == 0
    failed_primary.teardown(failed_generation)


def test_non_lab_type110_media_security_fails_closed():
    from claritylink_jmcs.media import encode_lab_message

    receiver = Receiver()  # Listener contract is host-modeled; crypto remains unknown.
    generation = _session(receiver)
    receiver.setup({"streams": [{"type": 110, "streamConnectionID": 31}]}, generation)
    client = socket.create_connection(("127.0.0.1", receiver.primary.port), timeout=2)
    try:
        receiver.accept_primary(generation)
        client.sendall(encode_lab_message(0, b"synthetic bytes"))
        with pytest.raises(ReceiverError, match="type110_security_evidence_required"):
            receiver.receive_primary_frame(generation)
    finally:
        client.close()
    assert receiver.primary is None
    receiver.teardown(generation)


def test_duplicate_stream_ids_and_wrong_generation_rejected_before_media():
    receiver = Receiver(clear_lab=True)
    generation = _session(receiver)
    with pytest.raises(ReceiverError, match="duplicate_stream_connection_id"):
        receiver.setup({"streams": [{"type": 110, "streamConnectionID": 7},
                                     {"type": 111, "streamConnectionID": 7}]}, generation)
    receiver.teardown(generation)
    next_generation = _session(receiver)
    with pytest.raises(ReceiverError, match="stale_or_closed_session"):
        receiver.setup({"streams": [{"type": 111, "streamConnectionID": 8}]}, generation)
    receiver.teardown(next_generation)


def test_type111_media_failure_isolated_from_primary_and_repeated_cleanup_is_safe():
    from claritylink_jmcs.media import encode_lab_message

    receiver = Receiver(clear_lab=True)
    generation = _session(receiver)
    receiver.setup({"streams": [{"type": 110, "streamConnectionID": 9},
                                 {"type": 111, "streamConnectionID": 10}]}, generation)
    client = socket.create_connection(("127.0.0.1", receiver.secondary.port), timeout=2)
    try:
        receiver.accept_secondary(generation)
        client.sendall(encode_lab_message(0, b"malformed h264"))
        with pytest.raises(ReceiverError, match="decode_failed"):
            receiver.receive_secondary_frame(generation)
    finally:
        client.close()
    assert receiver.primary is not None and receiver.primary.closed is False
    assert receiver.secondary is None
    receiver.teardown_secondary(generation)
    receiver.teardown(generation)
    receiver.teardown(generation)
    assert receiver.snapshot().sessions == 0


@pytest.mark.parametrize("mode", ["truncated", "listener_disconnect", "unsupported_opcode"])
def test_type111_transport_failure_closes_only_secondary(mode: str):
    from claritylink_jmcs.media import encode_lab_message

    receiver = Receiver(clear_lab=True)
    generation = _session(receiver)
    receiver.setup({"streams": [{"type": 110, "streamConnectionID": 90},
                                 {"type": 111, "streamConnectionID": 91}]}, generation)
    client = socket.create_connection(("127.0.0.1", receiver.secondary.port), timeout=2)
    receiver.accept_secondary(generation)
    if mode == "listener_disconnect":
        client.close()
    elif mode == "truncated":
        header = bytearray(128)
        header[:4] = (4).to_bytes(4, "little")
        client.sendall(bytes(header) + b"x")
    else:
        header = bytearray(128)
        header[:4] = (1).to_bytes(4, "little")
        header[4] = 99
        client.sendall(bytes(header))
    try:
        with pytest.raises(ReceiverError):
            receiver.receive_secondary_frame(generation)
    finally:
        client.close()
    assert receiver.primary is not None and not receiver.primary.closed
    assert receiver.secondary is None
    receiver.teardown(generation)


def test_partial_primary_initialization_rolls_back_listener_and_decoder():
    receiver = Receiver(clear_lab=True, faults=FaultInjector("primary_decoder"))
    generation = _session(receiver)
    with pytest.raises(ReceiverError, match="fault_primary_decoder"):
        receiver.setup({"streams": [{"type": 110, "streamConnectionID": 92}]}, generation)
    snapshot = receiver.snapshot()
    assert (snapshot.primary_listeners, snapshot.decoders, snapshot.security_contexts) == (0, 0, 0)
    receiver.teardown(generation)


def test_partial_session_display_initialization_closes_synthetic_authority():
    class FailBeginDisplay(NullDisplay):
        def begin_generation(self, generation: int) -> None:
            raise RuntimeError("synthetic display unavailable")

    receiver = Receiver(primary_display=FailBeginDisplay())
    with pytest.raises(ReceiverError, match="session_display_initialization_failed"):
        receiver.start_session()
    assert receiver.generation == 0
    assert receiver.authenticated_session is None
    assert receiver.snapshot().sessions == 0


def test_one_hundred_complete_connection_disconnect_reconnect_cycles():
    receiver = Receiver(clear_lab=True)
    generations: set[int] = set()
    for index in range(100):
        generation = _session(receiver)
        assert generation not in generations
        generations.add(generation)
        receiver.setup({"streams": [{"type": 111, "streamConnectionID": 10000 + index * 2},
                                     {"type": 110, "streamConnectionID": 10001 + index * 2}]}, generation)
        receiver.teardown(generation)
        receiver.teardown(generation)
        snapshot = receiver.snapshot()
        assert (snapshot.sessions, snapshot.primary_listeners, snapshot.secondary_listeners,
                snapshot.security_contexts, snapshot.decoders, snapshot.displayed_frames,
                snapshot.display_uncleared) == (0, 0, 0, 0, 0, 0, 0)
