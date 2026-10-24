"""Canonical frame contract and the explicit PNG -> RGB24 conversion boundary."""
import struct
import subprocess
import zlib

import pytest

import t111_synth as synth
from claritylink_jmcs.decoder import FFmpegDecoder
from claritylink_jmcs.frames import (MAX_DIMENSION, FrameError, Provenance, VideoFrame, png_to_rgb24)


def chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def png_with(header, idat=None, width=2, height=2):
    data = zlib.compress(b"".join(b"\x00" + bytes(width * 3) for _ in range(height))) if idat is None else idat
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", data) + chunk(b"IEND", b"")


def frame(**overrides):
    fields = dict(pixels=bytes(2 * 3 * 2), width=2, height=2, stride=6, timestamp=0, session_generation=1,
                  stream_type=111, stream_connection_id=1, stream_generation=1,
                  provenance=Provenance.SYNTHETIC_LAB_CONTENT)
    fields.update(overrides)
    return VideoFrame(**fields)


@pytest.mark.parametrize("filter_mode", [0, 1, 2])
def test_png_filters_roundtrip_to_exact_rgb(filter_mode):
    width, height, pixels = png_to_rgb24(synth.make_png(5, 3, (9, 8, 7), filter_mode=filter_mode))
    assert (width, height) == (5, 3) and pixels == bytes((9, 8, 7)) * 15


def test_rgba_alpha_is_dropped_not_composited():
    _, _, pixels = png_to_rgb24(synth.make_png(2, 2, (1, 2, 3), colour_type=6))
    assert pixels == bytes((1, 2, 3)) * 4


def test_conversion_of_real_ffmpeg_png_matches_ffmpeg_raw_rgb_exactly():
    """Sub/Paeth filters from the real encoder: bit-exact against ffmpeg's own raw output."""
    stream = synth.SyntheticStream(2)
    png = FFmpegDecoder().decode(stream.annexb[1], 1, 1).png
    raw = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "h264", "-i", "pipe:0",
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
                         input=stream.annexb[1], capture_output=True, check=True, timeout=10).stdout
    width, height, pixels = png_to_rgb24(png)
    assert (width, height) == (synth.WIDTH, synth.HEIGHT) and pixels == raw


@pytest.mark.parametrize("mutate, code", [
    (lambda p: p[:-1], "invalid_png"),                                 # truncated IEND crc
    (lambda p: p[:16] + b"\xff" + p[17:], "invalid_png_chunk"),        # header CRC broken
    (lambda p: b"GIF89a" + p[6:], "invalid_png"),
])
def test_corrupt_png_is_refused(mutate, code):
    with pytest.raises(FrameError, match=code):
        png_to_rgb24(mutate(synth.make_png(4, 4)))


@pytest.mark.parametrize("header", [
    struct.pack(">IIBBBBB", 2, 2, 16, 2, 0, 0, 0),   # 16-bit samples
    struct.pack(">IIBBBBB", 2, 2, 8, 3, 0, 0, 0),    # palette
    struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 1),    # interlaced
])
def test_unsupported_png_formats_are_refused_not_guessed(header):
    with pytest.raises(FrameError, match="unsupported_png_format"):
        png_to_rgb24(png_with(header))


def test_oversized_declared_dimensions_are_refused_before_inflating():
    header = struct.pack(">IIBBBBB", MAX_DIMENSION + 1, 1, 8, 2, 0, 0, 0)
    with pytest.raises(FrameError, match="invalid_frame_dimensions"):
        png_to_rgb24(png_with(header))


def test_pixel_count_cap_bounds_conversion_work():
    header = struct.pack(">IIBBBBB", 2000, 1100, 8, 2, 0, 0, 0)  # within per-side limit, over pixel cap
    with pytest.raises(FrameError, match="invalid_frame_dimensions"):
        png_to_rgb24(png_with(header))
    with pytest.raises(FrameError, match="invalid_frame_dimensions"):
        frame(width=2000, height=1100, stride=6000, pixels=bytes(6000 * 1100))


def test_chunk_order_and_trailing_bytes_are_enforced():
    good = synth.make_png(2, 2)
    header_chunk = good[8:8 + 25]
    idat_first = good[:8] + good[8 + 25:-12] + header_chunk + good[-12:]
    with pytest.raises(FrameError, match="invalid_png_header"):
        png_to_rgb24(idat_first)
    with pytest.raises(FrameError, match="invalid_png"):
        png_to_rgb24(good + b"trailing")


def test_decompression_bomb_is_bounded_by_the_header_promise():
    header = struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)
    bomb = zlib.compress(bytes(64 * 1024 * 1024), 9)  # ~64 KiB compressed, 64 MiB inflated
    with pytest.raises(FrameError, match="invalid_png_data"):
        png_to_rgb24(png_with(header, idat=bomb))


def test_short_pixel_data_is_refused():
    header = struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0)
    with pytest.raises(FrameError, match="invalid_png_data"):
        png_to_rgb24(png_with(header, idat=zlib.compress(bytes(10))))


@pytest.mark.parametrize("override, code", [
    ({"pixels": bytes(5)}, "invalid_frame_size"),
    ({"stride": 8}, "invalid_frame_stride"),
    ({"width": 0, "stride": 0, "pixels": b""}, "invalid_frame_dimensions"),
    ({"width": True}, "invalid_frame_field"),
    ({"timestamp": -1}, "invalid_frame_identity"),
    ({"stream_type": 7}, "invalid_frame_identity"),
    ({"stream_generation": 0}, "invalid_frame_identity"),
    ({"provenance": "IPHONE_ORIGIN"}, "unsupported_frame_format"),
    ({"pixel_format": "RGBA8888"}, "unsupported_frame_format"),
    ({"pixels": bytearray(12)}, "invalid_frame_stride"),
])
def test_video_frame_rejects_invalid_contract(override, code):
    with pytest.raises(FrameError, match=code):
        frame(**override)


def test_only_synthetic_lab_provenance_exists_in_this_milestone():
    assert [p.value for p in Provenance] == ["SYNTHETIC_LAB_CONTENT"]
    assert frame().pixel(1, 1) == (0, 0, 0)
    with pytest.raises(FrameError, match="pixel_out_of_range"):
        frame().pixel(2, 0)
