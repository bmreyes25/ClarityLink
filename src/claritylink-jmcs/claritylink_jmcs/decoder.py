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
