"""Canonical, content-agnostic decoded video frame (CL-T111-INGEST-01).

The host decoder emits PNG bytes (``DecodedFrame.png``). A display that must
reason about pixels needs an explicit, validated representation instead, and
PNG, RGB24 and compressed H.264 are never interchangeable. The only conversion
here is ``png_to_rgb24``: bounded, stdlib-only, 8-bit non-interlaced RGB/RGBA.

Nothing in this module knows what the pixels depict. ``provenance`` records
where the bytes came from; this milestone only ever admits generated lab
content, so a frame can never be mistaken for iPhone-origin video.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import struct
import zlib

MAX_DIMENSION = 4096
MAX_FRAME_BYTES = 8 * 1024 * 1024  # same ceiling as the decoder's PNG output
# Conversion is pure Python (~0.2 ms per 1k pixels observed), so cap the work a single
# frame can demand; 1920x1080 is far above any Display 1 this project models.
MAX_FRAME_PIXELS = 1920 * 1080
PIXEL_FORMAT_RGB24 = "RGB24"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_CHANNELS = {2: 3, 6: 4}  # PNG colour type -> channels; 8-bit samples only
_PNG_CRITICAL = {b"IHDR", b"PLTE", b"IDAT", b"IEND"}
# Ancillary chunk placement per the PNG specification (positions are relative to PLTE and IDAT).
_BEFORE_PLTE = {b"cHRM", b"gAMA", b"iCCP", b"sBIT", b"sRGB", b"cICP", b"mDCV", b"cLLI"}
_AFTER_PLTE_BEFORE_IDAT = {b"bKGD", b"hIST", b"tRNS"}
_BEFORE_IDAT = {b"pHYs", b"sPLT", b"acTL"}
_AT_MOST_ONCE = (_BEFORE_PLTE | _AFTER_PLTE_BEFORE_IDAT | {b"pHYs", b"acTL", b"tIME", b"eXIf"})


class FrameError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class Provenance(str, Enum):
    """Origin classes. Only generated lab content exists in this milestone."""

    SYNTHETIC_LAB_CONTENT = "SYNTHETIC_LAB_CONTENT"


@dataclass(frozen=True)
class VideoFrame:
    """One decoded frame. Immutable; ``pixels`` is owned by the frame (bytes).

    ``stride`` is bytes per row (== width * 3 for RGB24; no row padding).
    Identity fields bind the frame to the stream and session it was decoded for.
    """

    pixels: bytes
    width: int
    height: int
    stride: int
    timestamp: int
    session_generation: int
    stream_type: int
    stream_connection_id: int
    stream_generation: int
    provenance: Provenance
    pixel_format: str = PIXEL_FORMAT_RGB24

    def __post_init__(self) -> None:
        ints = (self.width, self.height, self.stride, self.timestamp, self.session_generation,
                self.stream_type, self.stream_connection_id, self.stream_generation)
        if any(type(value) is not int for value in ints):
            raise FrameError("invalid_frame_field")
        if self.pixel_format != PIXEL_FORMAT_RGB24 or not isinstance(self.provenance, Provenance):
            raise FrameError("unsupported_frame_format")
        if (not (1 <= self.width <= MAX_DIMENSION and 1 <= self.height <= MAX_DIMENSION)
                or self.width * self.height > MAX_FRAME_PIXELS):
            raise FrameError("invalid_frame_dimensions")
        if self.stride != self.width * 3 or not isinstance(self.pixels, bytes):
            raise FrameError("invalid_frame_stride")
        if len(self.pixels) != self.stride * self.height or len(self.pixels) > MAX_FRAME_BYTES:
            raise FrameError("invalid_frame_size")
        if (self.timestamp < 0 or self.session_generation < 1 or self.stream_connection_id < 1
                or self.stream_generation < 1 or self.stream_type not in (110, 111)):
            raise FrameError("invalid_frame_identity")

    def pixel(self, x: int, y: int) -> tuple[int, int, int]:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise FrameError("pixel_out_of_range")
        offset = y * self.stride + x * 3
        return self.pixels[offset], self.pixels[offset + 1], self.pixels[offset + 2]


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    d_left, d_up, d_corner = abs(estimate - left), abs(estimate - up), abs(estimate - upper_left)
    if d_left <= d_up and d_left <= d_corner:
        return left
    return up if d_up <= d_corner else upper_left


def _unfilter(raw: bytes, width: int, height: int, channels: int) -> bytes:
    row_bytes = width * channels
    previous = bytearray(row_bytes)
    rows = bytearray()
    for y in range(height):
        base = y * (row_bytes + 1)
        mode = raw[base]
        line = bytearray(raw[base + 1:base + 1 + row_bytes])
        if mode == 0:
            pass
        elif mode == 1:
            for i in range(channels, row_bytes):
                line[i] = (line[i] + line[i - channels]) & 255
        elif mode == 2:
            for i in range(row_bytes):
                line[i] = (line[i] + previous[i]) & 255
        elif mode == 3:
            for i in range(row_bytes):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 255
        elif mode == 4:
            for i in range(row_bytes):
                left = line[i - channels] if i >= channels else 0
                corner = previous[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(left, previous[i], corner)) & 255
        else:
            raise FrameError("invalid_png_filter")
        rows += line
        previous = line
    return bytes(rows)


def _check_ancillary_placement(kind: bytes, seen: set[bytes], palette: bool, idat_started: bool) -> None:
    """Refuse a known ancillary chunk that is duplicated or outside its legal position."""
    if kind in seen and kind in _AT_MOST_ONCE:
        raise FrameError("duplicate_png_chunk")
    if kind in _BEFORE_PLTE and (palette or idat_started):
        raise FrameError("invalid_png_chunk_order")
    if kind in _AFTER_PLTE_BEFORE_IDAT and idat_started:
        raise FrameError("invalid_png_chunk_order")
    if kind == b"hIST" and not palette:
        raise FrameError("invalid_png_chunk_order")  # hIST describes the palette
    if kind in _BEFORE_IDAT and idat_started:
        raise FrameError("invalid_png_chunk_order")


def png_to_rgb24(png: bytes) -> tuple[int, int, bytes]:
    """Return ``(width, height, rgb24)``; alpha is dropped, never composited."""
    if not isinstance(png, bytes) or not png.startswith(_PNG_SIGNATURE) or len(png) > MAX_FRAME_BYTES:
        raise FrameError("invalid_png")
    offset = len(_PNG_SIGNATURE)
    header: tuple[int, ...] | None = None
    compressed = bytearray()
    seen: set[bytes] = set()
    palette = idat_started = idat_closed = ended = False
    while offset + 12 <= len(png) and not ended:
        length = struct.unpack(">I", png[offset:offset + 4])[0]
        kind = png[offset + 4:offset + 8]
        body = png[offset + 8:offset + 8 + length]
        crc = png[offset + 8 + length:offset + 12 + length]
        if len(body) != length or len(crc) != 4 or struct.unpack(">I", crc)[0] != zlib.crc32(kind + body):
            raise FrameError("invalid_png_chunk")
        if not all(65 <= byte <= 90 or 97 <= byte <= 122 for byte in kind) or kind[2] & 0x20:
            raise FrameError("invalid_png_chunk")  # not a letter-only type, or the reserved bit is set
        if header is None and kind != b"IHDR":
            raise FrameError("invalid_png_header")  # IHDR must come first
        if kind == b"IHDR":
            if header is not None or length != 13:
                raise FrameError("invalid_png_header")
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"PLTE":
            if (palette or idat_started or not length or length % 3 or length > 3 * 256
                    or seen & _AFTER_PLTE_BEFORE_IDAT):
                raise FrameError("invalid_png_palette")
            palette = True
        elif kind == b"IDAT":
            if idat_closed:
                raise FrameError("noncontiguous_png_idat")
            idat_started = True
            compressed += body
        elif kind == b"IEND":
            if length or not idat_started:
                raise FrameError("invalid_png_iend")
            ended = True
        else:
            if kind not in _PNG_CRITICAL and not kind[0] & 0x20:
                raise FrameError("unsupported_png_critical_chunk")  # never silently skipped
            if idat_started:
                idat_closed = True  # anything between IDAT chunks breaks the contiguous run
            _check_ancillary_placement(kind, seen, palette, idat_started)
        seen.add(kind)
        offset += 12 + length
    if header is None or not ended or not compressed or offset != len(png):
        raise FrameError("invalid_png")  # missing parts or bytes after IEND
    width, height, depth, colour, compression, filtering, interlace = header
    if depth != 8 or colour not in _CHANNELS or compression or filtering or interlace:
        raise FrameError("unsupported_png_format")
    if b"tRNS" in seen and colour == 6:
        raise FrameError("invalid_png_chunk")  # tRNS is forbidden alongside a full alpha channel
    if (not (1 <= width <= MAX_DIMENSION and 1 <= height <= MAX_DIMENSION)
            or width * height > MAX_FRAME_PIXELS):
        raise FrameError("invalid_frame_dimensions")
    channels = _CHANNELS[colour]
    expected = height * (1 + width * channels)
    if expected > MAX_FRAME_BYTES + MAX_DIMENSION:
        raise FrameError("invalid_frame_size")
    stream = zlib.decompressobj()
    try:  # bounded: never inflate past the size the header promises
        raw = stream.decompress(bytes(compressed), expected + 1)
    except zlib.error as exc:
        raise FrameError("invalid_png_data") from exc
    if len(raw) != expected or not stream.eof or stream.unused_data:
        raise FrameError("invalid_png_data")
    pixels = _unfilter(raw, width, height, channels)
    if channels == 4:
        pixels = b"".join(pixels[i:i + 3] for i in range(0, len(pixels), 4))
    return width, height, pixels
