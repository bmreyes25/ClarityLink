"""Offline receiver integration and regression checks."""
from __future__ import annotations

from pathlib import Path
import socket
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "claritylink-jmcs"))

from claritylink_jmcs.capabilities import SecondaryDisplayCapability, lab_info
from claritylink_jmcs.compat.honda import EvidenceRequired, HondaStaticType110Adapter
from claritylink_jmcs.compat.honda.lifecycle import teardown_type_supported_by_static_honda
from claritylink_jmcs.compat.honda.session import HondaType110SessionModel
from claritylink_jmcs.compat.honda.type110 import known_type110_response_matches
from claritylink_jmcs.display import DisplayError, FrameDumpDisplay, NullDisplay
from claritylink_jmcs.listener import HostListener, ListenerError
from claritylink_jmcs.media import MediaError, encode_lab_message, read_message
from claritylink_jmcs.receiver import FaultInjector, Receiver, ReceiverError, ReceiverState
from claritylink_jmcs.setup import SetupRequest, SetupError, append_secondary, primary_unchanged


def request(*kinds: int) -> dict:
    return {"streams": [{"type": kind, "streamConnectionID": 1000 + kind} for kind in kinds]}


def start(receiver: Receiver) -> int:
    generation = receiver.start_session()
    receiver.info_exchanged(generation)
    return generation


def generated_h264() -> bytes:
    return subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
         "color=c=red:s=32x32:r=1", "-frames:v", "1", "-c:v", "libx264", "-f", "h264", "pipe:1"],
        capture_output=True, timeout=5, check=True,
    ).stdout


def test_honda_known_type110_fields_and_unknown_type111() -> None:
    adapter = HondaStaticType110Adapter()
    assert adapter.parse_known_request(request(110), 1).streams[0].stream_connection_id == 1110
    assert adapter.known_response_entry(50001) == {"type": 110, "dataPort": 50001}
    with pytest.raises(EvidenceRequired, match="honda_non_type110"):
        adapter.parse_known_request(request(111), 1)
    with pytest.raises(EvidenceRequired, match="honda_type111_response"):
        adapter.type111_response({})
    assert HondaType110SessionModel(1, 42).stream_connection_id == 42
    assert known_type110_response_matches({"type": 110, "dataPort": 50001}, 50001)
    assert teardown_type_supported_by_static_honda(110)
    with pytest.raises(EvidenceRequired, match="honda_type111_teardown"):
        teardown_type_supported_by_static_honda(111)


@pytest.mark.parametrize("kinds", [(110, 111), (111, 110)])
def test_setup_both_orders_and_teardown(kinds: tuple[int, int]) -> None:
    receiver = Receiver(clear_lab=True)
    gen = start(receiver)
    first = receiver.setup(request(kinds[0]), gen)
    second = receiver.setup(request(kinds[1]), gen)
    assert len(first.fields["streams"]) == 1
    assert len(second.fields["streams"]) == 2
    assert receiver.state is ReceiverState.BOTH_ACTIVE
    primary = receiver.primary
    receiver.teardown_secondary(gen)
    assert receiver.primary is primary and receiver.state is ReceiverState.PRIMARY_ACTIVE
    receiver.teardown(gen)
    receiver.teardown(gen)
    assert receiver.snapshot().sessions == 0
    assert receiver.snapshot().secondary_listeners == 0


def test_type111_disabled_without_security_evidence_preserves_primary() -> None:
    receiver = Receiver()  # Fail-closed default.
    gen = start(receiver)
    response = receiver.setup(request(110, 111), gen)
    assert [s["type"] for s in response.fields["streams"]] == [110]
    assert receiver.state is ReceiverState.PRIMARY_ACTIVE
    assert receiver.snapshot().secondary_listeners == 0
    receiver.teardown(gen)


@pytest.mark.parametrize("point", ["listener_bind", "security", "decoder", "response", "commit"])
def test_secondary_setup_fault_preserves_primary(point: str) -> None:
    receiver = Receiver(clear_lab=True)
    gen = start(receiver)
    first = receiver.setup(request(110), gen)
    receiver.faults.points.add(point)
    primary = receiver.primary
    fallback = receiver.setup(request(111), gen)
    assert fallback.fields["streams"] == first.fields["streams"]
    assert receiver.primary is primary
    assert receiver.state is ReceiverState.PRIMARY_ACTIVE
    assert receiver.snapshot().secondary_listeners == 0
    receiver.teardown(gen)


def test_setup_validation_fault_leaves_zero_resources() -> None:
    receiver = Receiver(clear_lab=True, faults=FaultInjector("setup_validation"))
    gen = start(receiver)
    with pytest.raises(ReceiverError, match="fault_setup_validation"):
        receiver.setup(request(111), gen)
    assert receiver.snapshot().secondary_listeners == 0
    receiver.teardown(gen)


def test_response_pre_serialization_and_primary_oracle() -> None:
    original = {"streams": [{"type": 110, "dataPort": 11111, "other": "keep"}], "other": 7}
    request_fields = request(111)
    parsed = SetupRequest.parse(request_fields, 1)
    response = append_secondary(original, parsed, 22222)
    assert response.wire.startswith(b"bplist00")
    assert primary_unchanged(original, response.fields)
    assert len(original["streams"]) == 1
    assert response.fields["streams"][1]["streamConnectionID"] == 1111


@pytest.mark.parametrize("bad", [0, -1, True, 2**64, "12"])
def test_invalid_connection_id_fails_before_allocation(bad: object) -> None:
    receiver = Receiver(clear_lab=True)
    gen = start(receiver)
    with pytest.raises(ReceiverError, match="invalid_stream_connection_id"):
        receiver.setup({"streams": [{"type": 111, "streamConnectionID": bad}]}, gen)
    assert receiver.snapshot().secondary_listeners == 0
    receiver.teardown(gen)


def test_duplicate_id_and_stale_generation() -> None:
    receiver = Receiver(clear_lab=True)
    gen = start(receiver)
    with pytest.raises(ReceiverError, match="duplicate_stream_connection_id"):
        receiver.setup({"streams": [{"type": 110, "streamConnectionID": 9},
                                    {"type": 111, "streamConnectionID": 9}]}, gen)
    receiver.teardown(gen)
    new_gen = start(receiver)
    with pytest.raises(ReceiverError, match="stale_or_closed_session"):
        receiver.setup(request(111), gen)
    assert new_gen != gen
    receiver.teardown(new_gen)


def test_listener_loopback_policy_and_generation() -> None:
    with pytest.raises(ListenerError, match="non_loopback"):
        HostListener.create(1, host="0.0.0.0")
    listener = HostListener.create(1)
    with pytest.raises(ListenerError, match="stale_listener"):
        listener.accept(2)
    listener.close()
    listener.close()


def test_media_bounds() -> None:
    with pytest.raises(MediaError, match="invalid_lab_message"):
        encode_lab_message(0, b"")
    with pytest.raises(MediaError, match="invalid_lab_message"):
        encode_lab_message(2, b"x")


@pytest.mark.parametrize("body_size,opcode", [(0, 0), (2 * 1024 * 1024 + 1, 0), (1, 255)])
def test_untrusted_media_header_fails_before_body_read(body_size: int, opcode: int) -> None:
    sender, receiver = socket.socketpair()
    receiver.settimeout(0.1)
    try:
        header = bytearray(128)
        header[:4] = body_size.to_bytes(4, "little")
        header[4] = opcode
        sender.sendall(header)
        with pytest.raises(MediaError, match="invalid_body_length|unsupported_screen_opcode"):
            read_message(receiver, 1)
    finally:
        sender.close()
        receiver.close()


def test_frame_dump_refuses_to_overwrite_preexisting_file(tmp_path: Path) -> None:
    existing = tmp_path / "existing.png"
    existing.write_bytes(b"user data")
    with pytest.raises(DisplayError, match="host_output_already_exists"):
        FrameDumpDisplay(existing)
    assert existing.read_bytes() == b"user data"


def test_host_h264_end_to_end(tmp_path: Path) -> None:
    output = tmp_path / "secondary.png"
    display = FrameDumpDisplay(output)
    receiver = Receiver(clear_lab=True, display=display)
    gen = start(receiver)
    primary = receiver.setup(request(110), gen)
    original_primary = primary.fields["streams"][0].copy()
    secondary = receiver.setup(request(111), gen)
    assert secondary.fields["streams"][0] == original_primary
    port = secondary.fields["streams"][1]["dataPort"]
    encoded = generated_h264()
    with socket.create_connection(("127.0.0.1", port), timeout=1) as client:
        receiver.accept_secondary(gen)
        client.sendall(encode_lab_message(0, encoded))
        png = receiver.receive_secondary_frame(gen)
    assert png.startswith(b"\x89PNG") and output.exists()
    assert receiver.state is ReceiverState.BOTH_ACTIVE
    receiver.teardown_secondary(gen)
    assert receiver.state is ReceiverState.PRIMARY_ACTIVE
    assert not output.exists()
    receiver.teardown(gen)
    assert receiver.snapshot().secondary_listeners == 0
    assert receiver.snapshot().decoders == 0


def test_media_failure_clears_secondary_and_preserves_primary() -> None:
    receiver = Receiver(clear_lab=True)
    gen = start(receiver)
    receiver.setup(request(110, 111), gen)
    port = receiver.secondary.port
    with socket.create_connection(("127.0.0.1", port), timeout=1) as client:
        receiver.accept_secondary(gen)
        client.sendall(encode_lab_message(0, b"not h264"))
        with pytest.raises(ReceiverError, match="decode_failed"):
            receiver.receive_secondary_frame(gen)
    assert receiver.state is ReceiverState.PRIMARY_ACTIVE
    assert receiver.snapshot().secondary_listeners == 0
    receiver.teardown(gen)


@pytest.mark.parametrize("point", ["media", "decode", "display"])
def test_media_fault_containment(point: str) -> None:
    receiver = Receiver(clear_lab=True, faults=FaultInjector(point))
    gen = start(receiver)
    receiver.setup(request(110, 111), gen)
    port = receiver.secondary.port
    with socket.create_connection(("127.0.0.1", port), timeout=1) as client:
        receiver.accept_secondary(gen)
        client.sendall(encode_lab_message(0, generated_h264() if point == "display" else b"some bytes"))
        with pytest.raises(ReceiverError, match=f"fault_{point}"):
            receiver.receive_secondary_frame(gen)
    assert receiver.state is ReceiverState.PRIMARY_ACTIVE
    assert receiver.snapshot().secondary_listeners == 0
    receiver.teardown(gen)


def test_teardown_fault_is_contained() -> None:
    receiver = Receiver(clear_lab=True, faults=FaultInjector("teardown"))
    gen = start(receiver)
    receiver.setup(request(110, 111), gen)
    receiver.teardown(gen)
    assert receiver.state is ReceiverState.CLOSED
    assert receiver.snapshot().secondary_listeners == 0
    assert "TEARDOWN_FAULT_CONTAINED" in receiver.events


def test_display_clear_failure_keeps_generation_retryable() -> None:
    class FailOnceDisplay(NullDisplay):
        failed = False

        def clear(self) -> None:
            if not self.failed:
                self.failed = True
                raise OSError("synthetic clear failure")
            super().clear()

    receiver = Receiver(clear_lab=True, display=FailOnceDisplay())
    gen = start(receiver)
    receiver.setup(request(110, 111), gen)
    receiver.teardown(gen)
    assert receiver.state is ReceiverState.FAILED
    assert receiver.snapshot().secondary_listeners == 0
    assert receiver.snapshot().display_uncleared == 1
    receiver.teardown(gen)
    assert receiver.state is ReceiverState.CLOSED
    assert receiver.snapshot().display_uncleared == 0


def test_100_cycle_reconnect_no_resource_leak() -> None:
    receiver = Receiver(clear_lab=True, display=NullDisplay())
    for _ in range(100):
        gen = start(receiver)
        response = receiver.setup(request(110, 111), gen)
        assert len(response.fields["streams"]) == 2
        receiver.teardown(gen - 1)
        assert receiver.state is ReceiverState.BOTH_ACTIVE
        receiver.teardown(gen)
        assert receiver.snapshot().sessions == 0
        assert receiver.snapshot().secondary_listeners == 0
        assert receiver.snapshot().security_contexts == 0
        assert receiver.snapshot().decoders == 0


def test_capability_profile_explicitly_synthetic() -> None:
    info = lab_info(SecondaryDisplayCapability())
    assert [x["streamType"] for x in info["displays"]] == [110, 111]
    assert "SYNTHETIC" in info["evidence"]


def test_no_identifiers_in_trace() -> None:
    receiver = Receiver(clear_lab=True)
    gen = start(receiver)
    receiver.setup(request(110, 111), gen)
    receiver.teardown(gen)
    assert "1111" not in " ".join(receiver.events)
    assert all("KEY" not in event for event in receiver.events)
