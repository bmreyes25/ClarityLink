"""Bounded host parser for the recovered Honda Type110 envelope family.

Use on Type111 only as an explicit lab framing hypothesis. Its 128-byte
header does not identify the cipher or prove Type111 Honda compatibility.
"""
from __future__ import annotations

from dataclasses import dataclass
import socket

HEADER_SIZE = 128
MAX_BODY = 2 * 1024 * 1024


class MediaError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ScreenMessage:
    opcode: int
    timestamp: int
    body: bytes
    generation: int


def _read_exact(conn: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        try:
            part = conn.recv(min(65536, size - len(chunks)))
        except (OSError, TimeoutError) as exc:
            raise MediaError("media_read_failed") from exc
        if not part:
            raise MediaError("media_eof")
        chunks.extend(part)
    return bytes(chunks)


def read_message(conn: socket.socket, generation: int) -> ScreenMessage:
    header = _read_exact(conn, HEADER_SIZE)
    size = int.from_bytes(header[:4], "little")
    opcode = header[4]
    timestamp = int.from_bytes(header[8:16], "little")
    if size < 1 or size > MAX_BODY:
        raise MediaError("invalid_body_length")
    if opcode not in (0, 1):
        raise MediaError("unsupported_screen_opcode")
    return ScreenMessage(opcode, timestamp, _read_exact(conn, size), generation)


def encode_lab_message(opcode: int, body: bytes, timestamp: int = 1) -> bytes:
    """Fixture encoder; not a claim about Type111's actual transport."""
    if opcode not in (0, 1) or not 1 <= len(body) <= MAX_BODY or not 0 <= timestamp < 2**64:
        raise MediaError("invalid_lab_message")
    header = bytearray(HEADER_SIZE)
    header[:4] = len(body).to_bytes(4, "little")
    header[4] = opcode
    header[8:16] = timestamp.to_bytes(8, "little")
    return bytes(header) + body
