"""Synthetic CL-R5 presentation lifecycle integrated with the host stream registry."""
from __future__ import annotations

import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-jmcs"))
sys.path.insert(0, str(ROOT / "src/claritylink-negotiation"))

from claritylink_jmcs.capabilities import CapabilityMode, build_dual_display_plan
from claritylink_jmcs.display import NullDisplay
from claritylink_jmcs.info import InfoProfile
from claritylink_jmcs.media import encode_lab_message
from claritylink_jmcs.receiver import Receiver, ReceiverError
from claritylink_jmcs.capabilities import SecondaryDisplayCapability
from claritylink_jmcs.identity import LabIdentity
from claritylink_jmcs.stream_dispatch import DecodedFrame
from presentation_state import INSTRUCTION_CONTEXT, MAP_CONTEXT, PresentationState
from presentation_stream import PresentationOutput, PresentationStreamCoordinator


def _profile() -> InfoProfile:
    return InfoProfile(
        identity=LabIdentity("02:00:00:00:00:01", "b7e6c5a0-1111-4000-8000-000000000001",
                             "b7e6c5a0-2222-4000-8000-000000000002"),
        name="ClarityLink Synthetic Receiver", model="LAB", manufacturer="ClarityLink",
        source_version="R5_CONTROL_PLANE_MODEL_ONLY", feature_bits=0,
        audio_formats=({"type": 1, "audioType": 1, "audioOutputFormats": 1},),
        audio_latencies=({"type": 1, "inputLatencyMicros": 0, "outputLatencyMicros": 0},),
        hid_devices=({"uuid": "lab-hid", "name": "Lab Input", "displayUUID":
                      "b7e6c5a0-1111-4000-8000-000000000001", "hidDescriptor": b"\x00",
                      "hidProductID": 1, "hidVendorID": 1, "hidCountryCode": 0},),
        displays=SecondaryDisplayCapability.synthetic_lab(width=800, height=480),
    )


def _h264(color: str, width: int = 64, height: int = 48) -> bytes:
    result = subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
         f"color=c={color}:s={width}x{height}:r=1", "-frames:v", "1", "-c:v", "libx264",
         "-threads", "1", "-preset", "ultrafast", "-f", "h264", "pipe:1"],
        check=True, capture_output=True, timeout=10,
    )
    return result.stdout


def _model_session():
    state = PresentationState(generation=1)
    secondary_view, primary_view = NullDisplay(), NullDisplay()
    output = PresentationOutput(state, secondary_view)
    receiver = Receiver(clear_lab=True, display=output, primary_display=primary_view)
    generation = receiver.start_session()
    assert generation == state.generation
    receiver.exchange_info(_profile(), generation)
    capability = build_dual_display_plan(
        generation, 1107, 1117, mode=CapabilityMode.SYNTHETIC_LAB)
    return state, secondary_view, primary_view, output, receiver, capability, generation


def test_r5_controls_follow_existing_stream_and_keep_transport_independent():
    state, secondary, primary, output, receiver, capability, generation = _model_session()
    streams = [{"type": 110, "streamConnectionID": 1107},
               {"type": 111, "streamConnectionID": 1117}]
    receiver.setup({"streams": streams}, generation)
    coordinator = PresentationStreamCoordinator(receiver, state, capability, output)
    identity = coordinator.register_existing_type111()
    assert identity.stream_type == 111 and identity.output_id == 2
    assert coordinator.events[:2] == ["SYNTHETIC_CAPABILITY_REGISTERED", "TYPE111_EXISTING_STREAM_BOUND"]
    assert state.eligible_contexts == ()

    secondary_client = socket.create_connection(("127.0.0.1", receiver.secondary.port), timeout=2)
    receiver.accept_secondary(generation)
    try:
        coordinator.set_navigation("maps", active=True, instruction_active=True)
        assert state.eligible_contexts == (MAP_CONTEXT, INSTRUCTION_CONTEXT)
        coordinator.control("suggestUI", value=MAP_CONTEXT)
        assert state.ui_suggestion == MAP_CONTEXT and state.selected_context is None and not state.visible
        secondary_client.sendall(encode_lab_message(0, _h264("blue"), timestamp=10))
        decoded_png = receiver.receive_secondary_frame(generation)
        assert decoded_png.startswith(b"\x89PNG\r\n\x1a\n")
        assert secondary.current is None  # Media is decoded/queued while the presentation is hidden.
        assert receiver.stream_identity(111) == identity

        coordinator.control("showUI")
        assert state.selected_context == MAP_CONTEXT and state.visible
        assert secondary.current is not None and secondary.current.width == 800
        coordinator.control("ViewArea", value={"x": 0, "y": 0, "w": 800, "h": 480})
        coordinator.control("SafeArea", value={"x": 8, "y": 8, "w": 784, "h": 464})
        assert output.view_area == state.view_area and output.safe_area == state.safe_area
        assert receiver.stream_identity(111) == identity

        assert coordinator.update_video_config(80, 60) == 1
        assert receiver.secondary_dimensions == (80, 60)
        assert receiver.secondary_decoder_generation == 1
        assert receiver.stream_identity(111) == identity
        coordinator.set_navigation("waze", active=True, instruction_active=True)
        assert state.visible and state.selected_context == MAP_CONTEXT

        coordinator.control("stopUI")
        assert not state.visible and state.selected_context is None and secondary.current is None
        secondary_client.sendall(encode_lab_message(0, _h264("green"), timestamp=20))
        receiver.receive_secondary_frame(generation)
        assert secondary.current is None and receiver.stream_identity(111) == identity
        coordinator.control("suggestUI", value=MAP_CONTEXT)
        coordinator.control("showUI")
        assert secondary.current is not None
        assert (secondary.current.width, secondary.current.height) == (80, 60)
        assert receiver.stream_identity(111) == identity
    finally:
        secondary_client.close()

    coordinator.teardown_type111()
    assert receiver.secondary is None and receiver.primary is not None
    assert state.visible is False and state.active is False
    primary_identity = receiver.stream_identity(110)
    assert receiver.enqueue_decoded_frame(primary_identity,
            DecodedFrame(b"primary-model-frame", 30, primary_identity.stream_generation, 16, 16)
            ).result(timeout=3)
    assert primary.current is not None and secondary.current is None
    coordinator.teardown_parent()
    assert receiver.snapshot().sessions == 0
    assert primary.current is None and secondary.current is None


def test_r5_control_model_never_creates_a_phantom_type111_stream():
    state, _, _, output, receiver, capability, generation = _model_session()
    receiver.setup({"streams": [{"type": 110, "streamConnectionID": 1107}]}, generation)
    coordinator = PresentationStreamCoordinator(receiver, state, capability, output)
    with pytest.raises(ReceiverError, match="stream_not_registered"):
        coordinator.register_existing_type111()
    assert receiver.secondary is None and receiver.primary is not None
    receiver.setup({"streams": [{"type": 111, "streamConnectionID": 1117}]}, generation)
    identity = coordinator.register_existing_type111()
    assert identity.connection_id == 1117
    coordinator.teardown_parent()


@pytest.mark.parametrize("order", [(110, 111), (111, 110)])
def test_r5_stream_setup_order_does_not_change_identity_or_control_state(order):
    state, _, _, output, receiver, capability, generation = _model_session()
    ids = {110: 1107, 111: 1117}
    receiver.setup({"streams": [{"type": kind, "streamConnectionID": ids[kind]} for kind in order]},
                   generation)
    coordinator = PresentationStreamCoordinator(receiver, state, capability, output)
    identity = coordinator.register_existing_type111()
    coordinator.set_navigation("maps", active=True)
    coordinator.control("suggestUI", value=MAP_CONTEXT)
    coordinator.control("showUI")
    assert receiver.stream_identity(111) == identity
    assert receiver.stream_identity(110).connection_id == 1107
    assert state.visible and state.selected_context == MAP_CONTEXT
    coordinator.teardown_parent()
