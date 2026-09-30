from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-sim"))
sys.path.insert(0, str(ROOT / "src/claritylink-renderer"))

from host_h264_decoder import (  # noqa: E402
    DecodeStatus, FfmpegCliDecoder, generate_synthetic_h264,
    probe_ffmpeg_capabilities,
)
from model import MockDisplay1Backend, ClarityLinkRenderer  # noqa: E402


def _synthetic_annexb() -> bytes:
    # Structurally valid NAL boundaries, but not a decodable SPS/PPS/IDR stream.
    # Used only to verify input validation and adapter wiring with a fake process.
    return b"\x00\x00\x00\x01\x67\x42\x00\x1e\x00\x00\x00\x01\x68\xce\x00\x00\x00\x01\x65\x88"


class HostH264DecoderTests(unittest.TestCase):
    def test_capability_detection_reports_host_tools(self):
        capabilities = probe_ffmpeg_capabilities()
        if not shutil.which("ffmpeg"):
            self.assertEqual(
                capabilities,
                type(capabilities)(False, False, False, False),
            )
        else:
            self.assertTrue(capabilities.ffmpeg_available)

    def test_unavailable_backend_is_explicit_and_does_not_claim_a_decode(self):
        with patch("host_h264_decoder.shutil.which", return_value=None):
            decoder = FfmpegCliDecoder()
        result = decoder.decode_access_unit(
            _synthetic_annexb(), width=4, height=2, timestamp_ns=77,
        )
        self.assertFalse(decoder.available)
        self.assertEqual(result.status, DecodeStatus.UNAVAILABLE)
        self.assertIsNone(result.frame)

    def test_mock_process_output_becomes_validated_renderer_frame(self):
        rgba = bytes([12, 34, 56, 255] * 8)
        seen: dict[str, object] = {}

        def fake_run(command, **kwargs):
            seen["command"] = command
            seen["input"] = kwargs["input"]
            return subprocess.CompletedProcess(command, 0, stdout=rgba, stderr=b"")

        decoder = FfmpegCliDecoder(executable="synthetic-ffmpeg", run=fake_run)
        result = decoder.decode_access_unit(
            _synthetic_annexb(), width=4, height=2, timestamp_ns=123, frame_index=7,
        )
        self.assertEqual(result.status, DecodeStatus.DECODED)
        self.assertEqual(seen["input"], _synthetic_annexb())
        self.assertIn("rgba", seen["command"])
        self.assertEqual(result.frame.presentation_time_ns, 123)
        self.assertEqual((result.frame.width, result.frame.height), (4, 2))
        backend = MockDisplay1Backend()
        renderer = ClarityLinkRenderer(backend)
        renderer.start()
        renderer.submit(result.frame)
        self.assertEqual(len(backend.frames), 1)
        self.assertEqual(backend.target.display_id, 1)
        renderer.close()

    def test_missing_parameter_sets_fail_before_backend_call(self):
        def must_not_run(*_args, **_kwargs):
            raise AssertionError("decoder process must not run")

        decoder = FfmpegCliDecoder(executable="ffmpeg", run=must_not_run)
        result = decoder.decode_access_unit(
            b"\x00\x00\x00\x01\x65\x88", width=4, height=2, timestamp_ns=0,
        )
        self.assertEqual(result.status, DecodeStatus.MISSING_PARAMETER_SETS)

    def test_timeout_and_zero_frame_are_not_reported_as_decode_success(self):
        def timeout(*_args, **_kwargs):
            raise subprocess.TimeoutExpired("ffmpeg", 0.01)

        timed = FfmpegCliDecoder(executable="ffmpeg", run=timeout).decode_access_unit(
            _synthetic_annexb(), width=4, height=2, timestamp_ns=0,
        )
        self.assertEqual(timed.status, DecodeStatus.TIMEOUT)
        empty = FfmpegCliDecoder(
            executable="ffmpeg",
            run=lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b""),
        ).decode_access_unit(_synthetic_annexb(), width=4, height=2, timestamp_ns=0)
        self.assertEqual(empty.status, DecodeStatus.FAILED)
        self.assertIsNone(empty.frame)

    def test_bad_or_oversized_input_fails_closed(self):
        decoder = FfmpegCliDecoder(executable="ffmpeg", run=lambda *_a, **_k: None)
        for media in (b"garbage", b"\x00\x00\x01" + b"x" * (4 * 1024 * 1024)):
            result = decoder.decode_access_unit(media, width=4, height=2, timestamp_ns=0)
            self.assertEqual(result.status, DecodeStatus.INVALID_INPUT)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg absent; real synthetic encode/decode not run")
    def test_real_synthetic_encode_then_host_decode(self):
        capabilities = probe_ffmpeg_capabilities()
        if not capabilities.libx264_available:
            self.skipTest("ffmpeg libx264 encoder unavailable; real synthetic encode/decode not run")
        if not capabilities.h264_decoder_available:
            self.skipTest("ffmpeg H.264 decoder unavailable; real synthetic decode not run")
        if not capabilities.rgba_output_available:
            self.skipTest("ffmpeg RGBA output unavailable; renderer handoff not run")
        try:
            elementary_stream = generate_synthetic_h264()
        except RuntimeError as exc:
            self.skipTest(str(exc))
        result = FfmpegCliDecoder().decode_access_unit(
            elementary_stream, width=320, height=180, timestamp_ns=1_000_000_000,
        )
        self.assertEqual(result.status, DecodeStatus.DECODED, result.reason)
        self.assertEqual(len(result.frame.rgba), 320 * 180 * 4)
        self.assertEqual(result.frame.presentation_time_ns, 1_000_000_000)
        center_display = {"type110_active": True, "display": 0}
        audio = {"active": True, "source": "synthetic-test-only"}
        type110_before, audio_before = center_display.copy(), audio.copy()
        backend = MockDisplay1Backend()
        renderer = ClarityLinkRenderer(backend)
        renderer.start()
        renderer.submit(result.frame)
        self.assertEqual(backend.target.display_id, 1)
        self.assertEqual(backend.frames, [result.frame])
        self.assertEqual(center_display, type110_before)
        self.assertEqual(audio, audio_before)
        renderer.close()


if __name__ == "__main__":
    unittest.main()
