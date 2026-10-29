"""Locally generated SYNTHETIC_LAB_CONTENT for the CL-T111-INGEST-01 tests.

A non-navigation pattern: each frame is two flat colour halves whose values are
a function of the frame index, so a decoded pixel identifies its frame. Encoded
with the host's ffmpeg/libx264 (every frame an IDR carrying SPS/PPS), then
packaged in the laboratory Type111 framing (`media.encode_lab_message`) as an
avcC VideoConfig followed by AVCC access units. No iPhone, Honda or third-party
media is involved.
"""
from __future__ import annotations

import re
import socket
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT / "src" / "claritylink-jmcs", ROOT / "src" / "claritylink-honda"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from claritylink_jmcs.media import encode_lab_message  # noqa: E402

PROVENANCE = "SYNTHETIC_LAB_CONTENT"
WIDTH, HEIGHT = 64, 48
COLOR_TOLERANCE = 24  # H.264 is lossy; halves are flat so error stays small
_START_CODE = re.compile(b"\x00\x00\x01")


def expected_colors(index: int) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    left = ((40 * index) % 256, 200, (90 + 60 * index) % 256)
    right = (20, (60 + 50 * index) % 256, 230)
    return left, right


def _rgb_frame(index: int) -> bytes:
    left, right = expected_colors(index)
    row = bytes(left) * (WIDTH // 2) + bytes(right) * (WIDTH // 2)
    return row * HEIGHT


def _split_nals(stream: bytes) -> list[bytes]:
    starts = [m.start() for m in _START_CODE.finditer(stream)]
    ends = starts[1:] + [len(stream)]
    return [stream[s + 3:e].rstrip(b"\x00") if i + 1 < len(starts) else stream[s + 3:e]
            for i, (s, e) in enumerate(zip(starts, ends))]


class SyntheticStream:
    """``count`` independent IDR frames plus their avcC config."""

    def __init__(self, count: int = 4) -> None:
        raw = b"".join(_rgb_frame(i) for i in range(count))
        encoded = subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
             "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}", "-r", "5", "-i", "pipe:0",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "baseline",
             "-preset", "ultrafast", "-tune", "zerolatency",
             "-x264-params", "keyint=1:repeat-headers=1:aud=0", "-f", "h264", "pipe:1"],
            input=raw, capture_output=True, timeout=20, check=True).stdout
        nals = _split_nals(encoded)
        self.sps = next(n for n in nals if n[0] & 31 == 7)
        self.pps = next(n for n in nals if n[0] & 31 == 8)
        slices = [n for n in nals if n[0] & 31 in (1, 5)]
        if len(slices) != count:
            raise RuntimeError("synthetic encode produced an unexpected slice count")
        self.annexb = [b"\x00\x00\x00\x01" + self.sps + b"\x00\x00\x00\x01" + self.pps +
                       b"\x00\x00\x00\x01" + s for s in slices]
        self.avcc = [len(s).to_bytes(4, "big") + s for s in slices]
        self.avcc_config = (bytes([1, self.sps[1], self.sps[2], self.sps[3], 0xFF, 0xE1]) +
                            len(self.sps).to_bytes(2, "big") + self.sps + b"\x01" +
                            len(self.pps).to_bytes(2, "big") + self.pps)

    def config_message(self) -> bytes:
        return encode_lab_message(1, b"avcC" + self.avcc_config, 0)

    def frame_message(self, index: int, timestamp: int | None = None) -> bytes:
        return encode_lab_message(0, self.avcc[index], index + 1 if timestamp is None else timestamp)

    def primary_message(self, index: int, timestamp: int | None = None) -> bytes:
        """Type110 carries a complete Annex-B access unit in this lab model."""
        return encode_lab_message(0, self.annexb[index], index + 1 if timestamp is None else timestamp)


def make_png(width: int, height: int, rgb: tuple[int, int, int] = (10, 20, 30), *,
             colour_type: int = 2, filter_mode: int = 0) -> bytes:
    """Minimal valid 8-bit PNG (solid colour) for adapter-level and malformed-output tests."""
    channels = 3 if colour_type == 2 else 4
    pixel = bytes(rgb) + (b"\xff" if channels == 4 else b"")
    raw_row = bytes([0]) + pixel * width
    if filter_mode == 1:  # Sub: first pixel raw, the rest are zero deltas
        rows = [bytes([1]) + pixel + bytes(channels * (width - 1))] * height
    elif filter_mode == 2:  # Up: raw first row, then zero deltas
        rows = [raw_row] + [bytes([2]) + bytes(channels * width)] * (height - 1)
    else:
        rows = [raw_row] * height

    def chunk(kind: bytes, body: bytes) -> bytes:
        return len(body).to_bytes(4, "big") + kind + body + zlib.crc32(kind + body).to_bytes(4, "big")

    header = width.to_bytes(4, "big") + height.to_bytes(4, "big") + bytes([8, colour_type, 0, 0, 0])
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
            chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b""))


def connect(port: int) -> socket.socket:
    return socket.create_connection(("127.0.0.1", port), timeout=2)


DIMENSIONS = {"primary_dimensions": (WIDTH, HEIGHT), "secondary_dimensions": (WIDTH, HEIGHT)}


class Clock:
    """Deterministic lease clock; the host never reads wall time in these tests."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def start_type111(pipe, *, with_primary: bool = False):
    """Open a lab session, set up Type111 (and optionally Type110), connect the lab client(s)."""
    pipe.open_session()
    primary_client = None
    if with_primary:
        assert pipe.setup_primary(11)
        primary_client = connect(pipe.receiver.primary.port)
        pipe.receiver.accept_primary(pipe.generation)
    outcome = pipe.setup_type111(12)
    assert outcome.accepted, outcome
    client = connect(pipe.receiver.secondary.port)
    pipe.accept_type111()
    return (client, primary_client) if with_primary else client


def assert_pixels_match(frame, index: int) -> None:
    left, right = expected_colors(index)
    for (x, y), want in (((WIDTH // 4, HEIGHT // 2), left), ((3 * WIDTH // 4, HEIGHT // 2), right)):
        got = frame.pixel(x, y)
        assert all(abs(a - b) <= COLOR_TOLERANCE for a, b in zip(got, want)), (index, (x, y), got, want)
