#!/usr/bin/env python3
"""Decode two independent H.264 inputs concurrently with a local FFmpeg build.

This is a macOS CPU/software replay test only. It does not exercise Tegra,
Android MediaCodec, a render Surface, or a CarPlay receiver session.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FFMPEG = ROOT / "research/tools/python/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v7.1"
DEFAULT_FIXTURE = ROOT / "research/probes/decoder-capacity/fixtures/avc-800x480-15fps.mp4"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_twice(ffmpeg: Path, fixture: Path) -> dict:
    command = [
        str(ffmpeg), "-nostdin", "-hide_banner", "-loglevel", "error",
        "-stats_period", "0.1", "-progress", "pipe:1", "-i", str(fixture),
        "-map", "0:v:0", "-an", "-f", "null", "-",
    ]
    processes = []
    start_ns = time.monotonic_ns()
    try:
        # Launch both FFmpeg processes before collecting either result.
        for index in range(2):
            processes.append(subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
            ))
        results = []
        for index, process in enumerate(processes, start=1):
            stdout, stderr = process.communicate(timeout=30)
            frame_values = [int(v) for v in re.findall(r"(?m)^frame=(\d+)$", stdout)]
            results.append({
                "decoder": index,
                "returnCode": process.returncode,
                "reportedFrames": frame_values[-1] if frame_values else None,
                "progressEnded": "progress=end" in stdout,
                "stderr": stderr.strip(),
            })
        elapsed_ms = round((time.monotonic_ns() - start_ns) / 1_000_000, 3)
        return {
            "mode": "two independent concurrent FFmpeg processes",
            "platform": os.uname().sysname + " " + os.uname().machine,
            "hardware": "host software decode; no platform hardware claim",
            "fixture": str(fixture.relative_to(ROOT)),
            "fixtureSha256": sha256(fixture),
            "elapsedMs": elapsed_ms,
            "streams": results,
            "passed": all(r["returnCode"] == 0 and r["reportedFrames"] == 30 and r["progressEnded"] for r in results),
        }
    except Exception:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.communicate()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", type=Path, default=Path(os.environ.get("CLARITY_FFMPEG", DEFAULT_FFMPEG)))
    parser.add_argument("--fixture", type=Path, default=Path(os.environ.get("CLARITY_H264_FIXTURE", DEFAULT_FIXTURE)))
    parser.add_argument("--json", type=Path, help="also save the result JSON at this path")
    args = parser.parse_args()
    if not args.ffmpeg.is_file() or not os.access(args.ffmpeg, os.X_OK):
        parser.error(f"FFmpeg executable not found or not executable: {args.ffmpeg}")
    if not args.fixture.is_file():
        parser.error(f"H.264 fixture not found: {args.fixture}")
    result = decode_twice(args.ffmpeg, args.fixture)
    encoded = json.dumps(result, indent=2) + "\n"
    print(encoded, end="")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(encoded)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
