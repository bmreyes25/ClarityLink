"""Incremental parser for the Honda Type-110 ScreenStream envelope.

The header and body-length split are recovered from jmcs. Message-specific
body semantics remain opaque here. ``body_wire`` is the received body, which
is AES-CTR ciphertext when the screen security flag is active.
"""

from __future__ import annotations

from dataclasses import dataclass

HEADER_SIZE = 128
DEFAULT_MAX_BODY_SIZE = 16 * 1024 * 1024


class ScreenParseError(ValueError):
    """Raised when a Honda screen envelope violates parser safety bounds."""


@dataclass(frozen=True)
class ScreenHeader:
    raw: bytes
    body_size: int
    message_type: int
    timestamp_raw: int

    @classmethod
    def parse(cls, raw: bytes) -> "ScreenHeader":
        if len(raw) != HEADER_SIZE:
            raise ScreenParseError(f"screen header must be {HEADER_SIZE} bytes")
        return cls(
            raw=bytes(raw),
            body_size=int.from_bytes(raw[0:4], "little"),
            message_type=raw[4],
            timestamp_raw=int.from_bytes(raw[8:16], "little"),
        )


@dataclass(frozen=True)
class ScreenMessage:
    header: ScreenHeader
    body_wire: bytes


class ScreenFrameParser:
    """Split a byte stream into fixed-header, length-delimited messages.

    ``max_body_size`` is a local allocation guard, not a Honda protocol limit.
    The parser deliberately does not decrypt or interpret opcodes/config data.
    """

    def __init__(self, max_body_size: int = DEFAULT_MAX_BODY_SIZE) -> None:
        if max_body_size < 0:
            raise ValueError("max_body_size must be nonnegative")
        self.max_body_size = max_body_size
        self._buffer = bytearray()
        self._pending_header: ScreenHeader | None = None

    def feed(self, data: bytes | bytearray | memoryview) -> list[ScreenMessage]:
        self._buffer.extend(data)
        messages: list[ScreenMessage] = []

        while True:
            if self._pending_header is None:
                if len(self._buffer) < HEADER_SIZE:
                    break
                raw_header = bytes(self._buffer[:HEADER_SIZE])
                del self._buffer[:HEADER_SIZE]
                header = ScreenHeader.parse(raw_header)
                if header.body_size > self.max_body_size:
                    self.reset()
                    raise ScreenParseError(
                        f"body size {header.body_size} exceeds local limit "
                        f"{self.max_body_size}"
                    )
                self._pending_header = header

            assert self._pending_header is not None
            body_size = self._pending_header.body_size
            if len(self._buffer) < body_size:
                break
            body = bytes(self._buffer[:body_size])
            del self._buffer[:body_size]
            messages.append(ScreenMessage(self._pending_header, body))
            self._pending_header = None

        return messages

    def reset(self) -> None:
        self._buffer.clear()
        self._pending_header = None

    @property
    def buffered_bytes(self) -> int:
        return len(self._buffer)
