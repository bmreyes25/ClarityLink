"""Runtime ownership joins the existing replay/session/receiver components."""
from __future__ import annotations

import base64
from pathlib import Path
import socket
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-jmcs"))

from claritylink_jmcs.authentication import (
    AuthenticationError, LabAuthenticationProvider, ReplayAuthenticationProvider,
    SessionHandoff, SessionOrigin,
)
from claritylink_jmcs.capabilities import SecondaryDisplayCapability
from claritylink_jmcs.display import NullDisplay
from claritylink_jmcs.identity import LabIdentity
from claritylink_jmcs.info import InfoProfile
from claritylink_jmcs.media import encode_lab_message
from claritylink_jmcs.receiver import Receiver
from claritylink_jmcs.runtime import DualDisplayRuntime, RuntimeState
from claritylink_jmcs.session import ReceiverSession
from claritylink_jmcs.session_transport import ControlRequest, ReplaySessionTransport


def _fixture(name: str) -> bytes:
    path = ROOT / "tests/fixtures/cl-imp-08" / name
    return base64.b64decode(path.read_text().strip(), validate=True)


def _profile() -> InfoProfile:
    return InfoProfile(
        identity=LabIdentity("02:00:00:00:00:01", "b7e6c5a0-1111-4000-8000-000000000001",
                             "b7e6c5a0-2222-4000-8000-000000000002"),
        name="ClarityLink Synthetic Runtime", model="LAB", manufacturer="ClarityLink",
        source_version="CL-IMP-10-MODEL_ONLY", feature_bits=0,
        audio_formats=({"type": 1, "audioType": 1, "audioOutputFormats": 1},),
        audio_latencies=({"type": 1, "inputLatencyMicros": 0, "outputLatencyMicros": 0},),
        hid_devices=({"uuid": "lab-hid", "name": "Lab Input",
                      "displayUUID": "b7e6c5a0-1111-4000-8000-000000000001",
                      "hidDescriptor": b"\x00", "hidProductID": 1,
                      "hidVendorID": 1, "hidCountryCode": 0},),
        displays=SecondaryDisplayCapability.synthetic_lab(width=800, height=480),
    )


def _runtime(*, with_secondary: bool = True):
    handoff = SessionHandoff("synthetic-runtime", 1, SessionOrigin.SANITIZED_REPLAY,
                             "synthetic-fixture", object())
    streams = [{"type": 110, "streamConnectionID": 1101}]
    if with_secondary:
        streams.append({"type": 111, "streamConnectionID": 1111})
    transport = ReplaySessionTransport(handoff, [
        ControlRequest("GET", "/info", {}, 1),
        ControlRequest("SETUP", "/session", {"streams": streams}, 1),
    ])
    primary, secondary = NullDisplay(), NullDisplay()
    receiver = Receiver(clear_lab=True, primary_display=primary, display=secondary)
    session = ReceiverSession(ReplayAuthenticationProvider(handoff), receiver, _profile(),
                              allow_replay=True)
    runtime = DualDisplayRuntime(session)
    assert runtime.start(transport) == 1
    assert runtime.handle_control_once().status == 200
    assert runtime.handle_control_once().status == 200
    return runtime, receiver, primary, secondary


def _connect(runtime: DualDisplayRuntime, stream_type: int) -> socket.socket:
    receiver = runtime.receiver
    listener = receiver.primary if stream_type == 110 else receiver.secondary
    assert listener is not None
    return socket.create_connection(("127.0.0.1", listener.port), timeout=2)


def test_unified_runtime_runs_independent_stream_workers_and_cleans_everything():
    runtime, receiver, primary, secondary = _runtime()
    primary_peer, secondary_peer = _connect(runtime, 110), _connect(runtime, 111)
    try:
        primary_peer.sendall(encode_lab_message(0, _fixture("type110-red-32x32.h264.b64"), 10))
        secondary_peer.sendall(encode_lab_message(0, _fixture("type111-blue-32x32.h264.b64"), 20))
        assert runtime.wait_for_event("stream_frame", 5, 110) is not None
        assert runtime.wait_for_event("stream_frame", 5, 111) is not None
        assert receiver.frames == 2
        assert primary.current is not None and secondary.current is not None
        assert primary.current.png != secondary.current.png
    finally:
        primary_peer.close()
        secondary_peer.close()
    assert runtime.close()
    snapshot = runtime.snapshot()
    assert snapshot.state is RuntimeState.CLOSED and snapshot.cleanup_complete is True
    assert (snapshot.receiver.sessions, snapshot.receiver.primary_listeners,
            snapshot.receiver.secondary_listeners, snapshot.receiver.security_contexts,
            snapshot.receiver.decoders, snapshot.receiver.displayed_frames,
            snapshot.receiver.display_uncleared) == (0, 0, 0, 0, 0, 0, 0)
    assert primary.current is None and secondary.current is None


def test_secondary_transport_failure_withdraws_only_child_and_primary_keeps_running():
    runtime, receiver, primary, _secondary = _runtime()
    primary_peer, secondary_peer = _connect(runtime, 110), _connect(runtime, 111)
    try:
        secondary_peer.sendall(encode_lab_message(0, b"invalid synthetic H264", 1))
        assert runtime.wait_for_event("stream_stopped", 5, 111) is not None
        assert receiver.secondary is None
        assert receiver.primary is not None and not receiver.primary.closed, runtime.events
        primary_peer.sendall(encode_lab_message(0, _fixture("type110-red-32x32.h264.b64"), 10))
        assert runtime.wait_for_event("stream_frame", 5, 110) is not None
        assert primary.current is not None
        assert receiver.primary is not None and not receiver.primary.closed
    finally:
        primary_peer.close()
        secondary_peer.close()
    assert runtime.close()


def test_runtime_is_single_use():
    runtime, _receiver, _primary, _secondary = _runtime(with_secondary=False)
    assert runtime.close()
    with pytest.raises(Exception, match="runtime_already_started"):
        runtime.start()


def test_runtime_fails_closed_without_an_authorized_authentication_substrate():
    receiver = Receiver()
    session = ReceiverSession(LabAuthenticationProvider(), receiver, _profile())
    runtime = DualDisplayRuntime(session)
    with pytest.raises(AuthenticationError, match="lawful_auth_substrate_required"):
        runtime.start()
    snapshot = runtime.snapshot()
    assert snapshot.state is RuntimeState.FAILED
    assert snapshot.receiver.sessions == 0
    assert snapshot.receiver.primary_listeners == snapshot.receiver.secondary_listeners == 0
    assert snapshot.receiver.security_contexts == snapshot.receiver.decoders == 0
    assert snapshot.receiver.displayed_frames == snapshot.receiver.display_uncleared == 0
    assert any(event.name == "runtime_start_failed" for event in runtime.events)
