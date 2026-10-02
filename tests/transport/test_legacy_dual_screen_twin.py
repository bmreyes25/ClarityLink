import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src/claritylink-transport"), str(ROOT / "src/claritylink-negotiation")]

from legacy_dual_screen_twin import (
    DuplicateStreamConnectionID,
    LegacyDualScreenTwin,
    LegacyScreenInputError,
    ScreenRole,
)
from screen_parser import HEADER_SIZE


MASTER = bytes(range(16))
ID_A = 0x102030405060708
ID_B = 0x102030405060709
ID_B_NEXT = 0x10203040506070A


def encrypt_block(key: bytes, counter: bytes) -> bytes:
    # Deterministic state-mechanics fixture; this is not a production AES primitive.
    return bytes(a ^ b for a, b in zip(key, counter))


def packet(body: bytes, kind: int = 0) -> bytes:
    header = bytearray(HEADER_SIZE)
    header[:4] = len(body).to_bytes(4, "little")
    header[4] = kind
    return bytes(header) + body


def twin() -> LegacyDualScreenTwin:
    return LegacyDualScreenTwin(MASTER, encrypt_block=encrypt_block, max_body_size=64)


def crypto_state(screen):
    crypto = screen._receiver._crypto
    return (bytes(crypto._counter), crypto._position, crypto._keystream)


def test_type110_only_baseline_uses_honda_confirmed_primitives():
    model = twin()
    a = model.add_screen(ScreenRole.TYPE110, ID_A)
    payload = packet(bytes(range(19)))
    assert len(a.feed(payload)) == 1
    assert a.active
    assert model.roles == (ScreenRole.TYPE110,)


def test_roles_have_unique_ids_and_independently_derived_state():
    model = twin()
    a = model.add_screen(ScreenRole.TYPE110, ID_A)
    b = model.add_screen(ScreenRole.TYPE111_SYNTHETIC, ID_B)
    assert a.stream_connection_id != b.stream_connection_id
    assert a._receiver._crypto is not b._receiver._crypto
    assert a._receiver._crypto._key != b._receiver._crypto._key
    assert a._iv != b._iv
    assert a._receiver._crypto._counter is not b._receiver._crypto._counter
    assert a._receiver._parser is not b._receiver._parser
    assert a._receiver is not b._receiver


def test_interleaved_streams_match_independent_control_runs():
    control_a, control_b = twin(), twin()
    a0 = control_a.add_screen(ScreenRole.TYPE110, ID_A)
    b0 = control_b.add_screen(ScreenRole.TYPE111_SYNTHETIC, ID_B)
    model = twin()
    a = model.add_screen(ScreenRole.TYPE110, ID_A)
    b = model.add_screen(ScreenRole.TYPE111_SYNTHETIC, ID_B)
    a_inputs = [packet(bytes([i]) * n) for i, n in ((1, 3), (2, 19), (3, 7))]
    b_inputs = [packet(bytes([i + 10]) * n) for i, n in ((1, 21), (2, 5), (3, 29))]
    out_a = [a0.feed(item) for item in a_inputs]
    out_b = [b0.feed(item) for item in b_inputs]
    assert a.feed(a_inputs[0]) == out_a[0]
    assert b.feed(b_inputs[0]) == out_b[0]
    assert b.feed(b_inputs[1]) == out_b[1]
    assert a.feed(a_inputs[1]) == out_a[1]
    assert b.feed(b_inputs[2]) == out_b[2]
    assert a.feed(a_inputs[2]) == out_a[2]
    assert crypto_state(a) == crypto_state(a0)
    assert crypto_state(b) == crypto_state(b0)


def test_advancing_either_role_leaves_the_sibling_ctr_unchanged():
    model = twin()
    a = model.add_screen(ScreenRole.TYPE110, ID_A)
    b = model.add_screen(ScreenRole.TYPE111_SYNTHETIC, ID_B)
    initial_a, initial_b = crypto_state(a), crypto_state(b)
    a.feed(packet(b"advance only A"))
    assert crypto_state(b) == initial_b
    after_a = crypto_state(a)
    b.feed(packet(b"advance only B"))
    assert crypto_state(a) == after_a
    assert crypto_state(a) != initial_a
    assert crypto_state(b) != initial_b


def test_reset_and_destroy_b_do_not_change_a_and_recreated_b_is_new():
    model = twin()
    a = model.add_screen(ScreenRole.TYPE110, ID_A)
    b = model.add_screen(ScreenRole.TYPE111_SYNTHETIC, ID_B)
    a.feed(packet(b"advance A"))
    a_before = crypto_state(a)
    b.feed(packet(b"advance B"))
    b_crypto = b._receiver._crypto
    b.reset()
    assert crypto_state(a) == a_before
    assert crypto_state(b) != crypto_state(a)
    b.feed(packet(b"again"))
    model.destroy_screen(ScreenRole.TYPE111_SYNTHETIC)
    assert a.active
    assert crypto_state(a) == a_before
    assert b_crypto._destroyed
    assert b_crypto._key == bytes(16)
    replacement = model.add_screen(ScreenRole.TYPE111_SYNTHETIC, ID_B_NEXT)
    assert replacement is not b
    assert replacement.active
    assert a.active and crypto_state(a) == a_before


def test_malformed_b_fails_closed_without_changing_a_crypto_or_parser():
    model = twin()
    a = model.add_screen(ScreenRole.TYPE110, ID_A)
    b = model.add_screen(ScreenRole.TYPE111_SYNTHETIC, ID_B)
    # Partial bytes are buffered on A before B fails.
    a.feed(packet(b"valid A")[:HEADER_SIZE + 2])
    a_crypto = crypto_state(a)
    a_buffered = a._receiver._parser.buffered_bytes
    a_config = a._receiver.config
    malformed = bytearray(HEADER_SIZE)
    malformed[:4] = (65).to_bytes(4, "little")  # max_body_size is 64
    with pytest.raises(LegacyScreenInputError) as error:
        b.feed(bytes(malformed))
    assert str(error.value) == "synthetic screen input rejected"
    assert not b.active
    assert a.active
    assert crypto_state(a) == a_crypto
    assert a._receiver._parser.buffered_bytes == a_buffered
    assert a._receiver.config is a_config
    # Complete the valid A packet and compare against a clean control.
    control = twin().add_screen(ScreenRole.TYPE110, ID_A)
    assert a.feed(packet(b"valid A")[HEADER_SIZE + 2 :]) == control.feed(packet(b"valid A"))
    assert crypto_state(a) == crypto_state(control)


def test_duplicate_ids_are_structured_fail_closed_error():
    model = twin()
    model.add_screen(ScreenRole.TYPE110, ID_A)
    with pytest.raises(DuplicateStreamConnectionID) as error:
        model.add_screen(ScreenRole.TYPE111_SYNTHETIC, ID_A)
    assert error.value.code == "duplicate_stream_connection_id"
    assert error.value.roles == (ScreenRole.TYPE110, ScreenRole.TYPE111_SYNTHETIC)
    assert model.roles == (ScreenRole.TYPE110,)


@pytest.mark.parametrize("bad_id", [0, -1, 1 << 64, True, "7"])
def test_invalid_stream_ids_are_rejected(bad_id):
    with pytest.raises(ValueError, match="nonzero uint64"):
        twin().add_screen(ScreenRole.TYPE110, bad_id)


def test_two_sessions_cannot_alias_mutable_state():
    first, second = twin(), twin()
    a1 = first.add_screen(ScreenRole.TYPE110, ID_A)
    b1 = first.add_screen(ScreenRole.TYPE111_SYNTHETIC, ID_B)
    a2 = second.add_screen(ScreenRole.TYPE110, ID_A)
    b2 = second.add_screen(ScreenRole.TYPE111_SYNTHETIC, ID_B)
    b1.feed(packet(b"private synthetic bytes"))
    assert crypto_state(a1) == crypto_state(a2)
    assert crypto_state(b1) != crypto_state(b2)
    assert a1._receiver._crypto is not a2._receiver._crypto
    assert b1._receiver._parser is not b2._receiver._parser


def test_no_secrets_are_in_errors_or_repr():
    model = twin()
    a = model.add_screen(ScreenRole.TYPE110, ID_A)
    b = model.add_screen(ScreenRole.TYPE111_SYNTHETIC, ID_B)
    assert MASTER.hex() not in repr(model)
    assert a._receiver._crypto._key.hex() not in repr(a)
    malformed = bytearray(HEADER_SIZE)
    malformed[:4] = (65).to_bytes(4, "little")
    with pytest.raises(LegacyScreenInputError) as error:
        b.feed(bytes(malformed))
    rendered = repr(error.value) + str(error.value)
    assert MASTER.hex() not in rendered
    assert b._receiver is None
