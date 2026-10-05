"""Public FFmpeg host decoder for bounded clear H.264 lab access units."""
from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess


class DecodeError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class DecodedFrame:
    png: bytes
    timestamp: int
    generation: int


class FFmpegDecoder:
    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or shutil.which("ffmpeg")
        if not self.executable:
            raise DecodeError("ffmpeg_unavailable")
        self.closed = False

    def decode(self, access_unit: bytes, timestamp: int, generation: int) -> DecodedFrame:
        if self.closed:
            raise DecodeError("decoder_closed")
        if not access_unit or len(access_unit) > 2 * 1024 * 1024:
            raise DecodeError("invalid_access_unit")
        try:
            result = subprocess.run(
                [self.executable, "-hide_banner", "-loglevel", "error", "-f", "h264", "-i", "pipe:0",
                 "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
                input=access_unit, capture_output=True, timeout=5, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DecodeError("decode_failed") from exc
        if result.returncode or not result.stdout.startswith(b"\x89PNG\r\n\x1a\n") or len(result.stdout) > 8 * 1024 * 1024:
            raise DecodeError("decode_failed")
        return DecodedFrame(result.stdout, timestamp, generation)

    def close(self) -> None:
        self.closed = True


def avcc_to_annexb(access_unit: bytes, *, nal_length_size: int = 4) -> bytes:
    """Convert one bounded AVCC access unit without guessing its codec config."""
    if nal_length_size not in (1, 2, 4) or not access_unit or len(access_unit) > 2 * 1024 * 1024:
        raise DecodeError("invalid_avcc_unit")
    offset = 0
    output = bytearray()
    while offset < len(access_unit):
        if len(access_unit) - offset < nal_length_size:
            raise DecodeError("truncated_avcc_length")
        size = int.from_bytes(access_unit[offset:offset + nal_length_size], "big")
        offset += nal_length_size
        if size < 1 or size > len(access_unit) - offset:
            raise DecodeError("invalid_avcc_nal_length")
        output += b"\x00\x00\x00\x01" + access_unit[offset:offset + size]
        offset += size
    return bytes(output)


def parse_avcc_config(payload: bytes) -> bytes:
    """Extract bounded H.264 SPS/PPS from a VideoConfig avcC record."""
    if not payload or len(payload) > 65536:
        raise DecodeError("invalid_avcc_config")
    marker = payload.find(b"avcC")
    data = payload[marker + 4:] if marker >= 0 else payload
    if len(data) < 7 or data[0] != 1:
        raise DecodeError("invalid_avcc_config")
    offset = 6
    sps_count = data[5] & 31
    if sps_count < 1 or sps_count > 8:
        raise DecodeError("invalid_sps_count")
    output = bytearray()
    for group in range(2):
        if group == 1 and offset >= len(data):
            raise DecodeError("truncated_avcc_config")
        count = sps_count if group == 0 else data[offset]
        if group == 1:
            offset += 1
            if count < 1 or count > 8:
                raise DecodeError("invalid_pps_count")
        for _ in range(count):
            if len(data) - offset < 2:
                raise DecodeError("truncated_avcc_config")
            size = int.from_bytes(data[offset:offset + 2], "big")
            offset += 2
            if size < 1 or size > len(data) - offset:
                raise DecodeError("invalid_avcc_parameter_length")
            nal = data[offset:offset + size]
            if (nal[0] & 31) != (7 if group == 0 else 8):
                raise DecodeError("unexpected_avcc_parameter_type")
            output += b"\x00\x00\x00\x01" + nal
            offset += size
    return bytes(output)
