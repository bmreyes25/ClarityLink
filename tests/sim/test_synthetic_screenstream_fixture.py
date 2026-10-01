from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
for relative in ("src/claritylink-sim", "src/claritylink-transport", "src/claritylink-renderer"):
    sys.path.insert(0, str(ROOT / relative))

from h264_extractor import H264ExtractError
from host_h264_decoder import FfmpegCliDecoder, probe_ffmpeg_capabilities
from receiver_core import HondaScreenReceiverCore, UnknownMessageEvent
from screen_parser import HEADER_SIZE, ScreenFrameParser
from synthetic_screenstream_fixture import (
    build_avcc_config, create_synthetic_screenstream_fixture, run_fixture_through_transport,
)
from export_visual_demo import write_visual_frame
from video_config import VideoConfigError, VideoConfigParser


class SyntheticScreenStreamEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        caps = probe_ffmpeg_capabilities()
        if not (caps.ffmpeg_available and caps.libx264_available and
                caps.h264_decoder_available and caps.rgba_output_available):
            raise unittest.SkipTest("FFmpeg/libx264/H.264 decode/RGBA unavailable")
        cls.fixture = create_synthetic_screenstream_fixture()

    def test_generated_nals_avcc_and_screenstream_envelopes(self):
        fixture = self.fixture
        types = [nal[0] & 0x1F for nal in fixture.nals]
        self.assertIn(7, types)
        self.assertIn(8, types)
        self.assertTrue(any(1 <= nal_type <= 5 for nal_type in types))
        self.assertIn(5, types, "single-frame stream should contain an IDR")
        self.assertEqual(fixture.evidence, "SYNTHETIC_TEST_VALUE")
        self.assertEqual(fixture.crypto_mode, "PLAINTEXT_SYNTHETIC")
        config = VideoConfigParser.parse(fixture.avcc_config)
        self.assertEqual(config.configuration_version, 1)
        self.assertEqual(config.nal_length_size, 4)
        self.assertEqual(config.sequence_parameter_sets, fixture.sps)
        self.assertEqual(config.picture_parameter_sets, fixture.pps)
        self.assertEqual(int.from_bytes(fixture.opcode1_packet[:4], "little"), len(fixture.avcc_config))
        self.assertEqual(fixture.opcode1_packet[4], 1)
        self.assertEqual(fixture.opcode0_packet[4], 0)
        self.assertEqual(len(fixture.opcode1_packet), HEADER_SIZE + len(fixture.avcc_config))
        self.assertEqual(len(fixture.opcode0_packet), HEADER_SIZE + len(fixture.avcc_frame))

    def test_screenstream_config_frame_annexb_decode_and_renderer(self):
        stock_type110 = {"response": {"type": 110, "dataPort": 42110}, "active": True,
                         "crypto_counter": 42}
        audio = {"center_active": True, "voice_route_active": True, "owner": "synthetic-stock"}
        stock_before, audio_before = deepcopy(stock_type110), deepcopy(audio)
        result = run_fixture_through_transport(self.fixture)
        self.assertEqual(result["status"], "PASS", result.get("reason"))
        self.assertEqual(result["config"].nal_length_size, 4)
        self.assertTrue(result["media"].config_prepended)
        self.assertEqual(result["media"].data_format, "annex-b-normal-record-path")
        self.assertTrue({5, 7, 8}.issubset(result["nal_types"]))
        frame = result["frame"]
        self.assertEqual((frame.width, frame.height), (320, 180))
        self.assertEqual(len(frame.rgba), 320 * 180 * 4)
        self.assertEqual(frame.presentation_time_ns, 1_000_000_000)
        self.assertTrue(result["rendered"])
        self.assertEqual(result["renderer_target"], 1)
        self.assertEqual(result["renderer_frame"], frame)
        self.assertEqual(result["evidence"], "SYNTHETIC_TEST_VALUE")
        self.assertEqual(stock_type110, stock_before)
        self.assertEqual(audio, audio_before)

    def test_missing_parameter_sets_and_malformed_config_rejected(self):
        fixture = self.fixture
        with self.assertRaisesRegex(ValueError, "SPS"):
            build_avcc_config((), fixture.pps)
        with self.assertRaisesRegex(ValueError, "PPS"):
            build_avcc_config(fixture.sps, ())
        malformed = bytes([1, 66, 0, 30, 0xFF, 0xE1]) + b"\x00\x10\x67"
        with self.assertRaises(VideoConfigError):
            VideoConfigParser.parse(malformed)

    def test_unsupported_length_size_and_malformed_avcc_frame_rejected(self):
        fixture = self.fixture
        with self.assertRaisesRegex(ValueError, "NAL length size"):
            build_avcc_config(fixture.sps, fixture.pps, nal_length_size=3)
        unsupported = bytearray(fixture.avcc_config)
        unsupported[4] = (unsupported[4] & 0xFC) | 0x02  # value 3 means 3-byte lengths
        bad_length_mode = HondaScreenReceiverCore(crypto=None)
        bad_length_mode.feed(_packet(1, bytes(unsupported)))
        with self.assertRaises(H264ExtractError):
            bad_length_mode.feed(_packet(0, b"\x00\x00\x01\x01x"))
        receiver = HondaScreenReceiverCore(crypto=None)
        receiver.feed(_packet(1, fixture.avcc_config))
        with self.assertRaises(H264ExtractError):
            receiver.feed(_packet(0, b"\x00\x00\x00\x09\x65"))

    def test_header_length_mismatch_waits_and_unknown_opcode_is_preserved(self):
        parser = ScreenFrameParser(max_body_size=128)
        header = bytearray(HEADER_SIZE)
        header[0:4] = (4).to_bytes(4, "little")
        header[4] = 0
        self.assertEqual(parser.feed(bytes(header) + b"abc"), [])
        self.assertEqual(parser.buffered_bytes, 3)
        self.assertEqual(parser.feed(b"d")[0].body_wire, b"abcd")
        unknown = HondaScreenReceiverCore(crypto=None).feed(_packet(0x7F, b"opaque"))
        self.assertTrue(any(isinstance(event, UnknownMessageEvent) for event in unknown))

    def test_invalid_h264_and_renderer_rejection_leave_stock_audio_state_alone(self):
        stock = {"response": {"type": 110, "dataPort": 42110}, "active": True,
                 "crypto_counter": 42}
        audio = {"center_active": True, "voice_route_active": True}
        before_stock, before_audio = deepcopy(stock), deepcopy(audio)
        invalid = (b"\x00\x00\x00\x01\x67\x42\x00\x1e"
                   b"\x00\x00\x00\x01\x68\xce"
                   b"\x00\x00\x00\x01\x65\x88")
        decode = FfmpegCliDecoder().decode_access_unit(
            invalid, width=320, height=180, timestamp_ns=0,
        )
        self.assertNotEqual(decode.status.value, "DECODED")
        self.assertIsNone(decode.frame)
        from model import ClarityLinkRenderer, DecodedFrame, MockDisplay1Backend, PIXEL_FORMAT
        renderer = ClarityLinkRenderer(MockDisplay1Backend())
        renderer.start()
        with self.assertRaises(ValueError):
            renderer.submit(DecodedFrame(0, 180, PIXEL_FORMAT, 0, 0, rgba=b""))
        renderer.close()
        self.assertEqual(stock, before_stock)
        self.assertEqual(audio, before_audio)

    def test_exact_screenstream_renderer_frame_becomes_visual_png_provenance(self):
        result = run_fixture_through_transport(self.fixture)
        self.assertEqual(result["status"], "PASS", result.get("reason"))
        frame = result["renderer_frame"]
        self.assertEqual(frame, result["frame"])
        self.assertEqual(len(frame.rgba), frame.width * frame.height * 4)
        with tempfile.TemporaryDirectory() as scratch:
            metadata = write_visual_frame(frame, Path(scratch))
            self.assertEqual(metadata["source"], "screenstream_synthetic_decode")
            self.assertEqual(metadata["width"], 320)
            self.assertEqual(metadata["height"], 180)
            self.assertEqual(metadata["pixelFormat"], "RGBA8888")
            self.assertEqual(metadata["rgbaBytes"], 230400)
            self.assertEqual(metadata["sha256"], hashlib.sha256(frame.rgba).hexdigest())
            self.assertEqual(metadata["evidence"], "SYNTHETIC_TEST_VALUE")
            self.assertTrue((Path(scratch) / "type111-frame.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))


def _packet(opcode: int, body: bytes) -> bytes:
    header = bytearray(HEADER_SIZE)
    header[:4] = len(body).to_bytes(4, "little")
    header[4] = opcode
    header[8:16] = (1234).to_bytes(8, "little")
    return bytes(header) + body


if __name__ == "__main__":
    unittest.main()
