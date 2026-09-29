"""Honda Type-110 screen key derivation model; synthetic inputs only."""
from __future__ import annotations

import hashlib

MAX_UINT64 = (1 << 64) - 1


def _validate(master_material: bytes, stream_connection_id: int) -> None:
    if not isinstance(master_material, bytes) or len(master_material) != 16:
        raise ValueError("master_material must be exactly 16 bytes")
    if (
        isinstance(stream_connection_id, bool)
        or not isinstance(stream_connection_id, int)
        or not 1 <= stream_connection_id <= MAX_UINT64
    ):
        raise ValueError("stream_connection_id must be a nonzero uint64")


def derive_honda_type110_screen_key_iv(
    master_material: bytes, stream_connection_id: int
) -> tuple[bytes, bytes]:
    """Derive 16-byte outputs as SHA512(ASCII label + unsigned decimal ID || master).

    Honda's helper formats `AirPlayStreamKey%llu` and `AirPlayStreamIV%llu`,
    independently hashes each formatted salt followed by the 16-byte session
    master material, and copies the first 16 digest bytes to key/IV outputs.
    Whether Type 111 uses this Honda Type-110 helper is still unknown.
    """
    _validate(master_material, stream_connection_id)
    decimal_id = str(stream_connection_id).encode("ascii")
    key_salt = b"AirPlayStreamKey" + decimal_id
    iv_salt = b"AirPlayStreamIV" + decimal_id
    key = hashlib.sha512(key_salt + master_material).digest()[:16]
    iv = hashlib.sha512(iv_salt + master_material).digest()[:16]
    return key, iv
