"""Streaming state model for Honda's recovered AES-CTR body transform.

The AES block primitive is injected by the caller so this offline model has
no runtime crypto dependency and contains no vehicle/session key material.
"""

from __future__ import annotations

from collections.abc import Callable

BlockEncryptor = Callable[[bytes, bytes], bytes]


class ScreenCryptoModel:
    """AES-CTR state spanning ordered screen-message bodies.

    ``encrypt_block`` must implement AES-128 encryption of one 16-byte block.
    Header bytes are intentionally outside this API: Honda decrypts body bytes
    only, and the same instance must be used for successive message bodies.
    """

    def __init__(self, key: bytes, iv: bytes, encrypt_block: BlockEncryptor) -> None:
        if len(key) != 16 or len(iv) != 16:
            raise ValueError("Honda screen AES key and IV must each be 16 bytes")
        self._key = bytes(key)
        self._counter = bytearray(iv)
        self._encrypt_block = encrypt_block
        self._position = 0
        self._keystream = b""

    def update(self, ciphertext: bytes | bytearray | memoryview) -> bytes:
        """Decrypt one body, retaining partial keystream/counter state."""
        source = memoryview(ciphertext).cast("B")
        plaintext = bytearray(len(source))
        for index, value in enumerate(source):
            if self._position == 0:
                block = self._encrypt_block(self._key, bytes(self._counter))
                if len(block) != 16:
                    raise ValueError("AES block encryptor must return 16 bytes")
                self._keystream = bytes(block)
                self._increment_counter_big_endian()
            plaintext[index] = value ^ self._keystream[self._position]
            self._position = (self._position + 1) & 0x0F
        return bytes(plaintext)

    def _increment_counter_big_endian(self) -> None:
        for index in range(15, -1, -1):
            self._counter[index] = (self._counter[index] + 1) & 0xFF
            if self._counter[index] != 0:
                break

    def reset(self, iv: bytes) -> None:
        """Start a new screen-security generation with a supplied synthetic IV."""
        if len(iv) != 16:
            raise ValueError("Honda screen AES IV must be 16 bytes")
        self._counter = bytearray(iv)
        self._position = 0
        self._keystream = b""
