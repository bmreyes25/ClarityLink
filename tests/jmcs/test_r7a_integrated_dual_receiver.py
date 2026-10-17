"""Executable end-to-end synthetic Type110 + Type111 session acceptance."""
from __future__ import annotations

import socket
import subprocess
import sys
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

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
        displays=SecondaryDisplayCapability.synthetic_lab(width=800, height=480),
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


def test_r7a_concurrent_stream_dispatch_and_secondary_only_reconnect():
    """Host model: distinct stream IDs/listeners/decoders run in parallel; B teardown leaves A live."""
    from claritylink_jmcs.media import encode_lab_message

    primary_sink, secondary_sink = NullDisplay(), NullDisplay()
    receiver = Receiver(clear_lab=True, primary_display=primary_sink, display=secondary_sink)
    generation = _session(receiver)
    receiver.setup({"streams": [
        {"type": 111, "streamConnectionID": 2111},
        {"type": 110, "streamConnectionID": 2110},
    ]}, generation)
    primary_decoder, secondary_decoder = receiver.primary_decoder, receiver.decoder
    assert receiver.primary_id == 2110 and receiver.secondary_id == 2111
    assert receiver.primary.port != receiver.secondary.port
    assert primary_decoder is not secondary_decoder

    primary_access, secondary_access = _h264("red"), _h264("blue")
    primary_client = socket.create_connection(("127.0.0.1", receiver.primary.port), timeout=2)
    secondary_client = socket.create_connection(("127.0.0.1", receiver.secondary.port), timeout=2)
    receiver.accept_primary(generation)
    receiver.accept_secondary(generation)
    primary_client.sendall(encode_lab_message(0, primary_access, timestamp=10))
    secondary_client.sendall(encode_lab_message(0, secondary_access, timestamp=20))

    start = threading.Barrier(3)
    with ThreadPoolExecutor(max_workers=2) as pool:
        primary_future = pool.submit(lambda: (start.wait(timeout=3), receiver.receive_primary_frame(generation))[1])
        secondary_future = pool.submit(lambda: (start.wait(timeout=3), receiver.receive_secondary_frame(generation))[1])
        start.wait(timeout=3)
        primary_png = primary_future.result(timeout=10)
        secondary_png = secondary_future.result(timeout=10)
    assert primary_png != secondary_png
    assert primary_sink.current.timestamp == 10 and secondary_sink.current.timestamp == 20
    assert primary_sink.current.generation == secondary_sink.current.generation == generation

    secondary_client.close()
    old_secondary_decoder = receiver.decoder
    receiver.teardown_secondary(generation)
    assert receiver.primary is not None and receiver.primary_decoder is primary_decoder
    assert receiver.decoder is None and old_secondary_decoder.closed

    # Parent stream A continues producing after only B was removed.
    try:
        primary_client.sendall(encode_lab_message(0, primary_access, timestamp=30))
        receiver.receive_primary_frame(generation)
        assert primary_sink.current.timestamp == 30
    finally:
        primary_client.close()

    receiver.setup({"streams": [{"type": 111, "streamConnectionID": 2112}]}, generation)
    assert receiver.primary is not None and receiver.primary_decoder is primary_decoder
    assert receiver.secondary_id == 2112 and receiver.decoder is not old_secondary_decoder
    secondary_client = socket.create_connection(("127.0.0.1", receiver.secondary.port), timeout=2)
    try:
        receiver.accept_secondary(generation)
        secondary_client.sendall(encode_lab_message(0, secondary_access, timestamp=40))
        receiver.receive_secondary_frame(generation)
        assert secondary_sink.current.timestamp == 40
        assert receiver.generation == generation and receiver.primary_id == 2110
    finally:
        secondary_client.close()
        receiver.teardown(generation)
    snapshot = receiver.snapshot()
    assert (snapshot.sessions, snapshot.primary_listeners, snapshot.secondary_listeners,
            snapshot.security_contexts, snapshot.decoders, snapshot.displayed_frames,
            snapshot.display_uncleared) == (0, 0, 0, 0, 0, 0, 0)


def test_r7a_blocked_type111_output_does_not_starve_type110_output():
    """A slow secondary renderer must not hold the receiver-wide state lock."""
    import threading

    from claritylink_jmcs.media import encode_lab_message

    entered_secondary = threading.Event()
    release_secondary = threading.Event()

    class SlowSecondaryDisplay(NullDisplay):
        def show(self, frame):
            entered_secondary.set()
            if not release_secondary.wait(timeout=5):
                raise AssertionError("test did not release blocked secondary display")
            super().show(frame)

    primary_sink, secondary_sink = NullDisplay(), SlowSecondaryDisplay()
    receiver = Receiver(clear_lab=True, primary_display=primary_sink, display=secondary_sink)
    generation = _session(receiver)
    receiver.setup({"streams": [
        {"type": 110, "streamConnectionID": 3110},
        {"type": 111, "streamConnectionID": 3111},
    ]}, generation)
    primary_client = socket.create_connection(("127.0.0.1", receiver.primary.port), timeout=2)
    secondary_client = socket.create_connection(("127.0.0.1", receiver.secondary.port), timeout=2)
    receiver.accept_primary(generation)
    receiver.accept_secondary(generation)
    primary_access, secondary_access = _h264("red"), _h264("blue")
    primary_client.sendall(encode_lab_message(0, primary_access, timestamp=101))
    secondary_client.sendall(encode_lab_message(0, secondary_access, timestamp=202))

    with ThreadPoolExecutor(max_workers=2) as pool:
        secondary_future = pool.submit(receiver.receive_secondary_frame, generation)
        assert entered_secondary.wait(timeout=5), "secondary renderer was never entered"
        try:
            primary_future = pool.submit(receiver.receive_primary_frame, generation)
            primary_png = primary_future.result(timeout=3)
            assert primary_png.startswith(b"\x89PNG\r\n\x1a\n")
            assert primary_sink.current.timestamp == 101
            assert not secondary_future.done()
        finally:
            release_secondary.set()
        assert secondary_future.result(timeout=5).startswith(b"\x89PNG\r\n\x1a\n")

    primary_client.close()
    secondary_client.close()
    receiver.teardown(generation)
    snapshot = receiver.snapshot()
    assert (snapshot.sessions, snapshot.primary_listeners, snapshot.secondary_listeners,
            snapshot.security_contexts, snapshot.decoders, snapshot.displayed_frames,
            snapshot.display_uncleared) == (0, 0, 0, 0, 0, 0, 0)


def test_receiver_stream_registry_bounds_type111_and_routes_type110_independently():
    from claritylink_jmcs.decoder import DecodedFrame

    entered = threading.Event()
    release = threading.Event()

    class BlockedSecondaryDisplay(NullDisplay):
        def show(self, frame):
            entered.set()
            if not release.wait(5):
                raise AssertionError("Type111 dispatch barrier was not released")
            super().show(frame)

    primary, secondary = NullDisplay(), BlockedSecondaryDisplay()
    receiver = Receiver(clear_lab=True, primary_display=primary, display=secondary)
    generation = _session(receiver)
    receiver.setup({"streams": [
        {"type": 110, "streamConnectionID": 4110},
        {"type": 111, "streamConnectionID": 4111},
    ]}, generation)
    type110 = receiver.stream_identity(110)
    type111 = receiver.stream_identity(111)
    assert type110.stream_type == 110 and type110.output_id == 1
    assert type111.stream_type == 111 and type111.output_id == 2

    frame111a = DecodedFrame(b"111-A", 201, type111.stream_generation, 2, 2)
    frame111b = DecodedFrame(b"111-B", 202, type111.stream_generation, 2, 2)
    frame111c = DecodedFrame(b"111-C", 203, type111.stream_generation, 2, 2)
    blocked = receiver.enqueue_decoded_frame(type111, frame111a)
    assert entered.wait(3), "Type111 renderer did not block"
    queued = receiver.enqueue_decoded_frame(type111, frame111b)
    assert receiver.dispatch_registry_snapshot()[111].outstanding_frames == 2
    assert receiver.enqueue_decoded_frame(type111, frame111c).result(timeout=1) is False

    primary_frame = DecodedFrame(b"110-A", 101, type110.stream_generation, 2, 2)
    assert receiver.enqueue_decoded_frame(type110, primary_frame).result(timeout=3)
    assert primary.current == primary_frame
    assert secondary.current is None
    snapshot = receiver.dispatch_registry_snapshot()
    assert snapshot[111].retained_bytes == len(frame111a.png) + len(frame111b.png)
    assert snapshot[111].rejected == 1
    assert snapshot[110].rendered == (101,)
    release.set()
    assert blocked.result(timeout=3)
    assert queued.result(timeout=3)

    assert secondary.current == frame111b
    assert receiver.dispatch_registry_snapshot()[111].rendered == (201, 202)
    receiver.teardown(generation)
    assert receiver.snapshot().sessions == 0
    assert receiver.snapshot().displayed_frames == 0


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


def test_receiver_rejects_boolean_generation_alias():
    receiver = Receiver(clear_lab=True)
    generation = _session(receiver)
    assert generation == 1
    with pytest.raises(ReceiverError, match="stale_or_closed_session"):
        receiver.setup({"streams": [{"type": 111, "streamConnectionID": 8}]}, True)
    receiver.setup({"streams": [{"type": 110, "streamConnectionID": 9},
                                 {"type": 111, "streamConnectionID": 10}]}, generation)
    for teardown in (receiver.teardown_primary, receiver.teardown_secondary, receiver.teardown):
        teardown(True)
        assert receiver.generation == generation
        assert receiver.primary is not None and receiver.secondary is not None
    receiver.teardown(generation)


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
