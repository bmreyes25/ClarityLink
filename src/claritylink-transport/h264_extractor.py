"""Safe length-prefixed H.264 record conversion observed in Honda jmcs."""

from __future__ import annotations


class H264ExtractError(ValueError):
    """Malformed length-prefixed H.264 input."""


ANNEX_B_START_CODE = b"\x00\x00\x00\x01"
SUPPORTED_NAL_LENGTH_SIZES = (1, 2, 4)


class H264Extractor:
    """Convert one Honda screen message body into one Annex-B media buffer.

    The caller supplies the width selected from the preceding video config.
    Honda's converter handles 1-byte, 2-byte BE, and 4-byte BE lengths; it has
    no 3-byte branch. Empty NAL records are retained as start codes, matching
    the recovered conversion loop's zero-length behavior.
    """

    @staticmethod
    def to_annex_b(
        body: bytes | bytearray | memoryview, nal_length_size: int
    ) -> bytes:
        if nal_length_size not in SUPPORTED_NAL_LENGTH_SIZES:
            raise H264ExtractError(
                f"Honda record converter does not support width {nal_length_size}"
            )
        data = memoryview(body).cast("B")
        cursor = 0
        output = bytearray()
        while cursor < len(data):
            remaining = len(data) - cursor
            if remaining < nal_length_size:
                raise H264ExtractError(
                    f"truncated {nal_length_size}-byte NAL length at offset {cursor}"
                )
            nal_size = int.from_bytes(
                data[cursor : cursor + nal_length_size], "big"
            )
            cursor += nal_length_size
            remaining = len(data) - cursor
            if nal_size > remaining:
                raise H264ExtractError(
                    f"NAL declares {nal_size} bytes with only {remaining} remaining"
                )
            end = cursor + nal_size
            output.extend(ANNEX_B_START_CODE)
            output.extend(data[cursor:end])
            cursor = end
        return bytes(output)
