import importlib.util
import pathlib
import sys
import unittest


MODULE_PATH = (
    pathlib.Path(__file__).resolve().parents[2]
    / "src"
    / "claritylink-transport"
    / "screen_parser.py"
)
SPEC = importlib.util.spec_from_file_location("screen_parser", MODULE_PATH)
assert SPEC and SPEC.loader
screen_parser = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = screen_parser
SPEC.loader.exec_module(screen_parser)

CRYPTO_PATH = MODULE_PATH.with_name("crypto_model.py")
CRYPTO_SPEC = importlib.util.spec_from_file_location("crypto_model", CRYPTO_PATH)
assert CRYPTO_SPEC and CRYPTO_SPEC.loader
crypto_model = importlib.util.module_from_spec(CRYPTO_SPEC)
sys.modules[CRYPTO_SPEC.name] = crypto_model
CRYPTO_SPEC.loader.exec_module(crypto_model)


def packet(message_type: int, body: bytes, timestamp: int = 0x0102030405060708) -> bytes:
    header = bytearray(screen_parser.HEADER_SIZE)
    header[0:4] = len(body).to_bytes(4, "little")
    header[4] = message_type
    header[8:16] = timestamp.to_bytes(8, "little")
    return bytes(header) + body


class ScreenFrameParserTests(unittest.TestCase):
    def test_partial_header(self):
        parser = screen_parser.ScreenFrameParser()
        self.assertEqual(parser.feed(packet(0, b"frame")[:64]), [])
        messages = parser.feed(packet(0, b"frame")[64:])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].body_wire, b"frame")

    def test_split_body(self):
        parser = screen_parser.ScreenFrameParser()
        wire = packet(0, b"encrypted-body")
        self.assertEqual(parser.feed(wire[:screen_parser.HEADER_SIZE + 4]), [])
        result = parser.feed(wire[screen_parser.HEADER_SIZE + 4 :])
        self.assertEqual(result[0].body_wire, b"encrypted-body")

    def test_multiple_messages_in_one_read(self):
        parser = screen_parser.ScreenFrameParser()
        result = parser.feed(packet(0, b"one") + packet(1, b"config"))
        self.assertEqual([message.header.message_type for message in result], [0, 1])
        self.assertEqual([message.body_wire for message in result], [b"one", b"config"])

    def test_invalid_oversized_body_and_reset(self):
        parser = screen_parser.ScreenFrameParser(max_body_size=8)
        with self.assertRaises(screen_parser.ScreenParseError):
            parser.feed(packet(0, b"x" * 9))
        self.assertEqual(parser.buffered_bytes, 0)

    def test_unknown_message_type_is_preserved(self):
        parser = screen_parser.ScreenFrameParser()
        result = parser.feed(packet(0x7F, b"opaque"))
        self.assertEqual(result[0].header.message_type, 0x7F)
        self.assertEqual(result[0].body_wire, b"opaque")

    def test_zero_body_message(self):
        parser = screen_parser.ScreenFrameParser()
        result = parser.feed(packet(2, b""))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].body_wire, b"")

    def test_header_timestamp_is_retained_as_raw_integer(self):
        parser = screen_parser.ScreenFrameParser()
        result = parser.feed(packet(0, b"x", timestamp=0x1122334455667788))
        self.assertEqual(result[0].header.timestamp_raw, 0x1122334455667788)

    def test_reset_discards_partial_message(self):
        parser = screen_parser.ScreenFrameParser()
        wire = packet(0, b"body")
        parser.feed(wire[:screen_parser.HEADER_SIZE + 2])
        parser.reset()
        self.assertEqual(parser.buffered_bytes, 0)
        self.assertEqual(parser.feed(wire), [screen_parser.ScreenMessage(
            screen_parser.ScreenHeader.parse(wire[:screen_parser.HEADER_SIZE]), b"body"
        )])


class ScreenCryptoModelTests(unittest.TestCase):
    @staticmethod
    def synthetic_block_encryptor(key: bytes, block: bytes) -> bytes:
        # Deterministic test double for CTR state mechanics, not AES.
        return bytes((left ^ right) for left, right in zip(key, block))

    def test_state_continues_across_body_calls_and_partial_blocks(self):
        key = bytes(range(16))
        iv = bytes(range(16, 32))
        one = crypto_model.ScreenCryptoModel(key, iv, self.synthetic_block_encryptor)
        two = crypto_model.ScreenCryptoModel(key, iv, self.synthetic_block_encryptor)
        ciphertext = bytes(range(37))
        expected = one.update(ciphertext)
        actual = two.update(ciphertext[:5]) + two.update(ciphertext[5:19]) + two.update(ciphertext[19:])
        self.assertEqual(actual, expected)

    def test_reset_restarts_counter_and_partial_block_position(self):
        key = bytes(range(16))
        iv = bytes(range(16, 32))
        model = crypto_model.ScreenCryptoModel(key, iv, self.synthetic_block_encryptor)
        first = model.update(bytes(7))
        model.reset(iv)
        self.assertEqual(model.update(bytes(7)), first)

    def test_counter_increments_from_last_iv_byte_toward_first(self):
        observed_blocks = []

        def recording_block_encryptor(_key: bytes, block: bytes) -> bytes:
            observed_blocks.append(block)
            return bytes(16)

        iv = bytes(16)
        model = crypto_model.ScreenCryptoModel(bytes(16), iv, recording_block_encryptor)
        model.update(bytes(17))
        self.assertEqual(observed_blocks, [iv, bytes(15) + b"\x01"])

    def test_rejects_wrong_key_iv_and_encryptor_block_sizes(self):
        with self.assertRaises(ValueError):
            crypto_model.ScreenCryptoModel(b"short", bytes(16), self.synthetic_block_encryptor)
        model = crypto_model.ScreenCryptoModel(bytes(16), bytes(16), lambda _key, _block: b"bad")
        with self.assertRaises(ValueError):
            model.update(b"x")


if __name__ == "__main__":
    unittest.main()
