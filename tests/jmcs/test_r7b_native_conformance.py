"""Cross-language behavior check over the shared R7B vector/media assets."""
from __future__ import annotations

import json
import base64
import socket
import subprocess
from pathlib import Path

import pytest

from test_r7a_integrated_dual_receiver import _info_profile, _session
from claritylink_jmcs.display import NullDisplay
from claritylink_jmcs.media import encode_lab_message
from claritylink_jmcs.receiver import Receiver

ROOT = Path(__file__).resolve().parents[2]


def test_shared_vectors_have_equivalent_python_and_native_dual_frame_behavior():
    vectors = json.loads((ROOT / "tests/fixtures/r7b/vectors.json").read_text())
    native = ROOT / "build/r7b/host/receiver_test"
    if not native.exists():
        pytest.skip("build the native executable with tools/build_r7b_host.sh first")
    fixtures = {item["type"]: base64.b64decode((ROOT / "tests/fixtures/r7b" / item["fixture"]).read_text())
                for item in vectors["setup"]}
    primary, secondary = fixtures[110], fixtures[111]

    display0, display1 = NullDisplay(), NullDisplay()
    receiver = Receiver(clear_lab=True, primary_display=display0, display=display1,
                        primary_dimensions=(32, 24), secondary_dimensions=(32, 24))
    generation = _session(receiver)
    stream_setup = [{"type": item["type"], "streamConnectionID": item["connection_id"]}
                    for item in vectors["setup"]]
    response = receiver.setup({"streams": stream_setup}, generation)
    assert [x["type"] for x in response.fields["streams"]] == [110, 111]
    clients = []
    try:
        for item, payload, timestamp in zip(vectors["setup"], (primary, secondary), (110, 111)):
            stream_type = item["type"]
            listener = receiver.primary if stream_type == 110 else receiver.secondary
            clients.append(socket.create_connection(("127.0.0.1", listener.port), timeout=2))
            if stream_type == 110:
                receiver.accept_primary(generation)
            else:
                receiver.accept_secondary(generation)
            clients[-1].sendall(encode_lab_message(0, payload, timestamp=timestamp))
        frame0 = receiver.receive_primary_frame(generation)
        frame1 = receiver.receive_secondary_frame(generation)
        assert frame0 != frame1
        assert display0.current is not None and display1.current is not None
        assert (display0.current.width, display0.current.height) == (32, 24)
        assert (display1.current.width, display1.current.height) == (32, 24)
        assert display0.current.timestamp == 110 and display1.current.timestamp == 111
        assert display0.current.generation == display1.current.generation == generation
        assert receiver.snapshot().sessions == 1
    finally:
        for client in clients:
            client.close()
        receiver.teardown(generation)
    assert display0.current is None and display1.current is None
    assert receiver.snapshot().sessions == 0

    output = subprocess.run([str(native), str(ROOT / "build/r7b/fixtures/type110-red.h264"),
                             str(ROOT / "build/r7b/fixtures/type111-blue.h264"),
                             str(next(x["connection_id"] for x in vectors["setup"] if x["type"] == 110)),
                             str(next(x["connection_id"] for x in vectors["setup"] if x["type"] == 111))],
                            check=True, capture_output=True, text=True, timeout=120).stdout
    assert "NATIVE_R7B_PASS" in output
    assert "decoded_per_sink=102" in output
    assert "resources=0" in output
    assert vectors["expected"] == {
        "accepted_setup": True, "active_streams": 2,
        "frames_per_sink": 1, "cleanup_resources": 0,
    }
