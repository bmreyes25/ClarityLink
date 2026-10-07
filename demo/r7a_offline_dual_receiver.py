#!/usr/bin/env python3
"""Run the executable R7A synthetic dual-stream host demonstration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "claritylink-jmcs"))

from claritylink_jmcs.capabilities import SecondaryDisplayCapability
from claritylink_jmcs.display import NullDisplay
from claritylink_jmcs.identity import LabIdentity
from claritylink_jmcs.info import InfoProfile
from claritylink_jmcs.media import encode_lab_message
from claritylink_jmcs.receiver import Receiver


def sample(color: str) -> bytes:
    return subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
         f"color=c={color}:s=64x48:r=1", "-frames:v", "1", "-c:v", "libx264", "-threads", "1",
         "-preset", "ultrafast", "-f", "h264", "pipe:1"],
        capture_output=True, check=True, timeout=10,
    ).stdout


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    main = NullDisplay()
    cluster = NullDisplay()
    receiver = Receiver(clear_lab=True, primary_display=main, display=cluster)
    generation = receiver.start_session()  # Synthetic authenticated-session boundary.
    profile = InfoProfile(
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
    info_wire = receiver.exchange_info(profile, generation)
    response = receiver.setup({"streams": [
        {"type": 110, "streamConnectionID": 1101},
        {"type": 111, "streamConnectionID": 1111},
    ]}, generation)
    clients: list[socket.socket] = []
    try:
        for listener in (receiver.primary, receiver.secondary):
            assert listener is not None
            clients.append(socket.create_connection(("127.0.0.1", listener.port), timeout=2))
        receiver.accept_primary(generation)
        receiver.accept_secondary(generation)
        clients[0].sendall(encode_lab_message(0, sample("red"), timestamp=10))
        clients[1].sendall(encode_lab_message(0, sample("blue"), timestamp=20))
        receiver.receive_primary_frame(generation)
        receiver.receive_secondary_frame(generation)
        assert main.current and cluster.current
        assert main.current.png != cluster.current.png
        (output_dir / "display0-type110.png").write_bytes(main.current.png)
        (output_dir / "display1-type111.png").write_bytes(cluster.current.png)
        result = {
            "evidence": "MODEL_ONLY",
            "generation": generation,
            "info_bytes": len(info_wire),
            "setup_stream_types": [entry["type"] for entry in response.fields["streams"]],
            "display0": {"stream": 110, "frames": 1, "width": main.current.width,
                         "height": main.current.height, "timestamp": main.current.timestamp},
            "display1": {"stream": 111, "frames": 1, "width": cluster.current.width,
                         "height": cluster.current.height, "timestamp": cluster.current.timestamp},
            "distinct_content": True,
            "artifacts": ["display0-type110.png", "display1-type111.png"],
        }
    finally:
        for client in clients:
            client.close()
        receiver.teardown(generation)
    result["resources_after_disconnect"] = receiver.snapshot().__dict__
    if receiver.snapshot().sessions != 0:
        raise RuntimeError("receiver resources remained after disconnect")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("r7a-artifacts"))
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), indent=2, sort_keys=True))
