import pathlib
import sys
import unittest


SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "claritylink-transport"
sys.path.insert(0, str(SRC))

from h264_extractor import H264ExtractError, H264Extractor  # noqa: E402
from receiver_core import (  # noqa: E402
    ConfigMetadataEvent,
    HondaScreenReceiverCore,
    UnconfiguredVideoEvent,
    VideoConfigEvent,
    VideoMediaBufferEvent,
)
from screen_parser import HEADER_SIZE  # noqa: E402
from video_config import VideoConfigError, VideoConfigParser  # noqa: E402


def avcc(width_code=3, *, sps=(b"\x67\x64",), pps=(b"\x68\xee",), trailing=b""):
    body = bytearray((1, 100, 0, 31, 0xFC | width_code, 0xE0 | len(sps)))
    for nal in sps:
        body.extend(len(nal).to_bytes(2, "big"))
        body.extend(nal)
    body.append(len(pps))
    for nal in pps:
        body.extend(len(nal).to_bytes(2, "big"))
        body.extend(nal)
    body.extend(trailing)
    return bytes(body)


def screen_message(kind, body, timestamp=0x0102030405060708):
    header = bytearray(HEADER_SIZE)
    header[:4] = len(body).to_bytes(4, "little")
    header[4] = kind
    header[8:16] = timestamp.to_bytes(8, "little")
    return bytes(header) + body


class VideoConfigParserTests(unittest.TestCase):
    def test_valid_avcc_derives_width_and_annex_b_parameter_sets(self):
        config = VideoConfigParser.parse(avcc())
        self.assertEqual(config.nal_length_size, 4)
        self.assertEqual(config.sequence_parameter_sets, (b"\x67\x64",))
        self.assertEqual(config.picture_parameter_sets, (b"\x68\xee",))
        self.assertEqual(
            config.annex_b_parameter_sets,
            b"\x00\x00\x00\x01\x67\x64\x00\x00\x00\x01\x68\xee",
        )

    def test_length_width_values_1_2_3_4_are_extracted_from_low_two_bits(self):
        self.assertEqual(
            [VideoConfigParser.parse(avcc(width_code=i)).nal_length_size for i in range(4)],
            [1, 2, 3, 4],
        )

    def test_multiple_sps_pps_and_trailing_bytes_are_preserved(self):
        config = VideoConfigParser.parse(
            avcc(sps=(b"s1", b"s2"), pps=(b"p1", b"p2"), trailing=b"opaque")
        )
        self.assertEqual(config.sequence_parameter_sets, (b"s1", b"s2"))
        self.assertEqual(config.picture_parameter_sets, (b"p1", b"p2"))
        self.assertEqual(config.trailing_data, b"opaque")

    def test_honda_helper_allows_absent_pps_section_at_exact_end(self):
        raw = bytes((1, 66, 0, 30, 0xFF, 0xE1)) + b"\x00\x01s"
        config = VideoConfigParser.parse(raw)
        self.assertFalse(config.pps_count_present)
        self.assertEqual(config.picture_parameter_sets, ())

    def test_rejects_short_fixed_header_and_truncated_sps_fields(self):
        for raw in (b"", bytes(5), bytes((1, 2, 3, 4, 0xFF, 0xE1, 0))):
            with self.subTest(raw=raw), self.assertRaises(VideoConfigError):
                VideoConfigParser.parse(raw)

    def test_rejects_truncated_sps_pps_lengths_and_payloads(self):
        malformed = (
            bytes((1, 2, 3, 4, 0xFF, 0xE1)) + b"\x00",
            bytes((1, 2, 3, 4, 0xFF, 0xE1)) + b"\x00\x03a",
            bytes((1, 2, 3, 4, 0xFF, 0xE0)) + b"\x01\x00",
            bytes((1, 2, 3, 4, 0xFF, 0xE0)) + b"\x01\x00\x02a",
        )
        for raw in malformed:
            with self.subTest(raw=raw), self.assertRaises(VideoConfigError):
                VideoConfigParser.parse(raw)


class H264ExtractorTests(unittest.TestCase):
    def test_single_and_multiple_nals_for_supported_widths(self):
        for width in (1, 2, 4):
            body = b"".join(
                len(nal).to_bytes(width, "big") + nal for nal in (b"\x65abc", b"\x41d")
            )
            expected = b"\x00\x00\x00\x01\x65abc\x00\x00\x00\x01\x41d"
            self.assertEqual(H264Extractor.to_annex_b(body, width), expected)

    def test_zero_length_nal_matches_honda_start_code_output(self):
        self.assertEqual(H264Extractor.to_annex_b(b"\x00", 1), b"\x00\x00\x00\x01")

    def test_rejects_unsupported_width_and_truncated_or_oversized_records(self):
        bad = ((b"\x00", 2), (b"\x04ab", 1), (b"\x00\x05ab", 2))
        for body, width in bad:
            with self.subTest(body=body, width=width), self.assertRaises(H264ExtractError):
                H264Extractor.to_annex_b(body, width)
        with self.assertRaises(H264ExtractError):
            H264Extractor.to_annex_b(b"\x00", 3)


class ReceiverCoreTests(unittest.TestCase):
    def test_config_then_video_yields_timestamped_annex_b_buffer(self):
        core = HondaScreenReceiverCore()
        cfg_event = core.feed(screen_message(1, avcc()))[0]
        self.assertIsInstance(cfg_event, VideoConfigEvent)
        media = core.feed(screen_message(0, b"\x00\x00\x00\x02\x65x"))[0]
        self.assertIsInstance(media, VideoMediaBufferEvent)
        self.assertEqual(
            media.data,
            b"\x00\x00\x00\x01\x67\x64"
            b"\x00\x00\x00\x01\x68\xee"
            b"\x00\x00\x00\x01\x65x",
        )
        self.assertEqual(media.data_format, "annex-b-normal-record-path")
        self.assertTrue(media.config_prepended)
        self.assertEqual(media.timestamp_raw, 0x0102030405060708)

    def test_video_before_config_remains_opaque_and_config_update_replaces_state(self):
        core = HondaScreenReceiverCore()
        self.assertIsInstance(
            core.feed(screen_message(0, b"raw"))[0], UnconfiguredVideoEvent
        )
        core.feed(screen_message(1, avcc(width_code=0)))
        self.assertEqual(core.config.nal_length_size, 1)
        core.feed(screen_message(1, avcc(width_code=1)))
        self.assertEqual(core.config.nal_length_size, 2)

    def test_empty_config_body_updates_no_codec_state(self):
        core = HondaScreenReceiverCore()
        header = bytearray(HEADER_SIZE)
        header[4] = 1
        header[16:24] = b"floatraw"
        event = core.feed(bytes(header))[0]
        self.assertIsInstance(event, ConfigMetadataEvent)
        self.assertEqual(event.raw_header_fields, b"floatraw")
        self.assertIsNone(core.config)

    def test_malformed_config_does_not_replace_previous_good_config(self):
        core = HondaScreenReceiverCore()
        core.feed(screen_message(1, avcc(width_code=0)))
        previous = core.config
        with self.assertRaises(VideoConfigError):
            core.feed(screen_message(1, b"\x01\x64\x00\x1f"))
        self.assertIs(core.config, previous)

    def test_explicit_direct_body_mode_bypasses_config_and_record_conversion(self):
        core = HondaScreenReceiverCore(direct_body_mode=True)
        event = core.feed(screen_message(0, b"opaque bytes"))[0]
        self.assertIsInstance(event, VideoMediaBufferEvent)
        self.assertEqual(event.data, b"opaque bytes")
        self.assertEqual(event.data_format, "opaque-body")

    def test_partial_and_multiple_messages_flow_through_core(self):
        core = HondaScreenReceiverCore()
        stream = screen_message(1, avcc()) + screen_message(0, b"\x00\x00\x00\x01\x65")
        self.assertEqual(core.feed(stream[:127]), [])
        events = core.feed(stream[127:])
        self.assertEqual(len(events), 2)
        self.assertIsInstance(events[0], VideoConfigEvent)
        self.assertIsInstance(events[1], VideoMediaBufferEvent)
        self.assertTrue(events[1].config_prepended)

    def test_crypto_state_advances_over_config_before_video(self):
        from crypto_model import ScreenCryptoModel

        def block(key, counter):
            return bytes(a ^ b for a, b in zip(key, counter))

        key, iv = bytes(range(16)), bytes(range(16, 32))
        config = avcc()
        frame = b"\x00\x00\x00\x01\x65"
        encryptor = ScreenCryptoModel(key, iv, block)
        encrypted = screen_message(1, encryptor.update(config)) + screen_message(
            0, encryptor.update(frame)
        )
        decryptor = ScreenCryptoModel(key, iv, block)
        events = HondaScreenReceiverCore(crypto=decryptor).feed(encrypted)
        self.assertIsInstance(events[0], VideoConfigEvent)
        self.assertEqual(events[0].config.raw, config)
        self.assertEqual(
            events[1].data,
            b"\x00\x00\x00\x01\x67\x64"
            b"\x00\x00\x00\x01\x68\xee"
            b"\x00\x00\x00\x01\x65",
        )

    def test_reset_clears_partial_message_and_codec_state(self):
        core = HondaScreenReceiverCore()
        core.feed(screen_message(1, avcc()))
        core.feed(screen_message(0, b"\x00")[:HEADER_SIZE])
        core.reset()
        self.assertIsNone(core.config)
        self.assertEqual(core.feed(screen_message(0, b"x"))[0].body, b"x")


if __name__ == "__main__":
    unittest.main()
