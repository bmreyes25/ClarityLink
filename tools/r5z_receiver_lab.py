#!/usr/bin/env python3
"""Offline receiver laboratory driver; never authenticates or contacts Honda.

Input files are synthetic/sanitized JSON. lab-receiver listens on 127.0.0.1
only and accepts one locally supplied clear H.264 fixture connection.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "claritylink-jmcs"))

from claritylink_jmcs.capabilities import SecondaryDisplayCapability, lab_info
from claritylink_jmcs.display import FrameDumpDisplay, NullDisplay
from claritylink_jmcs.media import encode_lab_message
from claritylink_jmcs.receiver import Receiver


def _synthetic_h264() -> bytes:
    return subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
         "color=c=red:s=32x32:r=1", "-frames:v", "1", "-c:v", "libx264", "-f", "h264", "pipe:1"],
        capture_output=True, check=True, timeout=5,
    ).stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="R5Z offline localhost receiver lab")
    parser.add_argument("mode", choices=("replay", "synthetic-client", "captured-setup", "lab-receiver"))
    parser.add_argument("--setup-json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode in ("replay", "captured-setup", "lab-receiver") and args.setup_json is None:
        parser.error("--setup-json is required for this mode")
    if args.setup_json is not None:
        if args.setup_json.stat().st_size > 1_000_000:
            parser.error("setup fixture exceeds 1 MiB")
        setup = json.loads(args.setup_json.read_text(encoding="utf-8"))
    else:
        setup = {"streams": [{"type": 110, "streamConnectionID": 1100},
                             {"type": 111, "streamConnectionID": 1110}]}
    display = FrameDumpDisplay(args.output) if args.output else NullDisplay()
    receiver = Receiver(clear_lab=True, display=display)
    generation = receiver.start_session()
    receiver.info_exchanged(generation)
    response = receiver.setup(setup, generation)
    if args.mode == "synthetic-client" and receiver.secondary:
        with socket.create_connection(("127.0.0.1", receiver.secondary.port), timeout=1) as client:
            receiver.accept_secondary(generation)
            client.sendall(encode_lab_message(0, _synthetic_h264()))
            receiver.receive_secondary_frame(generation)
    elif args.mode == "lab-receiver" and receiver.secondary:
        receiver.accept_secondary(generation, timeout=5)
        receiver.receive_secondary_frame(generation)
    result = {"mode": args.mode, "info": lab_info(SecondaryDisplayCapability()),
              "response_stream_types": [x["type"] for x in response.fields["streams"]],
              "wire_bytes": len(response.wire), "frames": receiver.frames,
              "events": receiver.events.copy()}
    receiver.teardown(generation)
    result["after_teardown"] = receiver.snapshot().__dict__
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
