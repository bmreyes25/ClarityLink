"""Optional host-only H.264 decode adapter for synthetic digital-twin media.

No decoder is bundled. Real decoding requires an installed FFmpeg executable;
the default replay remains usable when it is absent.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import shutil
import subprocess
from typing import Callable

from model import DecodedFrame, PIXEL_FORMAT


MAX_ACCESS_UNIT_BYTES = 4 * 1024 * 1024
MAX_WIDTH = 1920
MAX_HEIGHT = 1080


class DecodeStatus(str, Enum):
    DECODED = "DECODED"
    UNAVAILABLE = "HOST_DECODER_UNAVAILABLE"
    INVALID_INPUT = "INVALID_ANNEXB"
    MISSING_PARAMETER_SETS = "MISSING_SPS_PPS"
    FAILED = "DECODE_FAILED"
    TIMEOUT = "DECODE_TIMEOUT"


@dataclass(frozen=True)
class HostDecodeResult:
    status: DecodeStatus
    frame: DecodedFrame | None = None
    reason: str = ""
    backend: str = "FFMPEG_CLI"
    evidence: str = "SYNTHETIC_TEST_VALUE"


@dataclass(frozen=True)
class FfmpegCapabilities:
    ffmpeg_available: bool
    libx264_available: bool
    h264_decoder_available: bool
    rgba_output_available: bool
    version: str | None = None


def probe_ffmpeg_capabilities(executable: str | None = None) -> FfmpegCapabilities:
    """Read FFmpeg's local capability tables without installing or writing files."""
    ffmpeg = executable or shutil.which("ffmpeg")
    if not ffmpeg:
        return FfmpegCapabilities(False, False, False, False)
    try:
        version_result = subprocess.run([ffmpeg, "-version"], capture_output=True,
                                        check=False, timeout=3)
        if version_result.returncode != 0:
            return FfmpegCapabilities(False, False, False, False)
        encoder_result = subprocess.run([ffmpeg, "-encoders"], capture_output=True,
                                         check=False, timeout=3)
        decoder_result = subprocess.run([ffmpeg, "-decoders"], capture_output=True,
                                         check=False, timeout=3)
        pixel_result = subprocess.run([ffmpeg, "-pix_fmts"], capture_output=True,
                                      check=False, timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        return FfmpegCapabilities(False, False, False, False)
    encoder_text = encoder_result.stdout.decode("utf-8", "replace")
    decoder_text = decoder_result.stdout.decode("utf-8", "replace")
    pixel_text = pixel_result.stdout.decode("utf-8", "replace")
    version_lines = version_result.stdout.decode("utf-8", "replace").splitlines()
    return FfmpegCapabilities(
        ffmpeg_available=True,
        libx264_available="libx264" in encoder_text,
        h264_decoder_available=any(
            " h264 " in f" {line.lower()} " for line in decoder_text.splitlines()
        ),
        rgba_output_available=any(
            line.split()[1:2] == ["rgba"] for line in pixel_text.splitlines()
            if len(line.split()) > 1
        ),
        version=version_lines[0] if version_lines else "version unavailable",
    )


def _nal_types(annexb: bytes) -> set[int]:
    """Collect NAL types from three- or four-byte Annex-B start codes."""
    types: set[int] = set()
    i = 0
    while i < len(annexb):
        if annexb.startswith(b"\x00\x00\x00\x01", i):
            start = i + 4
        elif annexb.startswith(b"\x00\x00\x01", i):
            start = i + 3
        else:
            i += 1
            continue
        if start < len(annexb):
            types.add(annexb[start] & 0x1F)
        i = start + 1
    return types


class FfmpegCliDecoder:
    """Decode one synthetic Annex-B access unit to a bounded RGBA frame."""

    def __init__(
        self,
        executable: str | None = None,
        timeout_seconds: float = 3.0,
        run: Callable[..., subprocess.CompletedProcess[bytes]] = subprocess.run,
    ) -> None:
        self.executable = executable or shutil.which("ffmpeg")
        self.timeout_seconds = timeout_seconds
        self._run = run

    @property
    def available(self) -> bool:
        return bool(self.executable)

    def decode_access_unit(
        self, annexb: bytes, *, width: int, height: int, timestamp_ns: int, frame_index: int = 0
    ) -> HostDecodeResult:
        if not self.executable:
            return HostDecodeResult(DecodeStatus.UNAVAILABLE, reason="ffmpeg executable not found")
        if not annexb or len(annexb) > MAX_ACCESS_UNIT_BYTES or not (
            annexb.startswith(b"\x00\x00\x01") or annexb.startswith(b"\x00\x00\x00\x01")
        ):
            return HostDecodeResult(DecodeStatus.INVALID_INPUT, reason="bounded Annex-B input required")
        if not (0 < width <= MAX_WIDTH and 0 < height <= MAX_HEIGHT) or timestamp_ns < 0 or frame_index < 0:
            return HostDecodeResult(DecodeStatus.INVALID_INPUT, reason="invalid synthetic frame metadata")
        types = _nal_types(annexb)
        if not {7, 8}.issubset(types):
            return HostDecodeResult(DecodeStatus.MISSING_PARAMETER_SETS, reason="SPS and PPS are required")
        expected_bytes = width * height * 4
        command = [
            self.executable, "-nostdin", "-hide_banner", "-loglevel", "error",
            "-threads", "1", "-max_pixels", str(MAX_WIDTH * MAX_HEIGHT),
            "-f", "h264", "-i", "pipe:0", "-frames:v", "1",
            "-vf", f"scale={width}:{height}",
            "-f", "rawvideo", "-pix_fmt", "rgba", "pipe:1",
        ]
        try:
            completed = self._run(
                command, input=annexb, capture_output=True, check=False,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return HostDecodeResult(DecodeStatus.TIMEOUT, reason="ffmpeg decode timed out")
        except OSError as exc:
            return HostDecodeResult(DecodeStatus.UNAVAILABLE, reason=f"ffmpeg could not start: {exc}")
        if completed.returncode != 0 or len(completed.stdout) != expected_bytes:
            return HostDecodeResult(DecodeStatus.FAILED, reason="ffmpeg produced no valid single RGBA frame")
        frame = DecodedFrame(
            width=width, height=height, pixel_format=PIXEL_FORMAT, row_stride=width * 4,
            presentation_time_ns=timestamp_ns, rgba=completed.stdout,
        )
        try:
            frame.validate(require_cpu=True)
        except ValueError as exc:
            return HostDecodeResult(DecodeStatus.FAILED, reason=str(exc))
        return HostDecodeResult(DecodeStatus.DECODED, frame=frame)


def generate_synthetic_h264(executable: str | None = None) -> bytes:
    """Generate one unmistakable color-bar test frame; output is never persisted."""
    ffmpeg = executable or shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg unavailable; synthetic H.264 generation skipped")
    capabilities = probe_ffmpeg_capabilities(ffmpeg)
    if not capabilities.libx264_available:
        raise RuntimeError("ffmpeg libx264 encoder unavailable; synthetic H.264 generation skipped")
    command = [
        ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
        "-i", "testsrc2=size=320x180:rate=1", "-frames:v", "1", "-an",
        "-c:v", "libx264", "-profile:v", "baseline", "-preset", "ultrafast",
        "-tune", "zerolatency", "-pix_fmt", "yuv420p", "-f", "h264", "pipe:1",
    ]
    try:
        result = subprocess.run(command, capture_output=True, check=False, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"synthetic H.264 generation unavailable: {exc}") from exc
    if result.returncode != 0 or not result.stdout:
        raise RuntimeError("ffmpeg lacks a working synthetic H.264 encoder")
    if len(result.stdout) > MAX_ACCESS_UNIT_BYTES:
        raise RuntimeError("generated synthetic H.264 input exceeded its size limit")
    return result.stdout
