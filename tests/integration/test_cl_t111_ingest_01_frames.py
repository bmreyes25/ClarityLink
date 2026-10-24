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


# --- strict PNG chunk structure (CL-FIX-92) ---------------------------------------------------------------

SIGNATURE = b"\x89PNG\r\n\x1a\n"
HEADER_2X2 = struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0)
RAW_2X2 = b"".join(b"\x00" + bytes(range(6)) for _ in range(2))


def assemble(*chunks, raw_tail=b""):
    return SIGNATURE + b"".join(chunks) + raw_tail


def ihdr():
    return chunk(b"IHDR", HEADER_2X2)


def idat_split(parts=1):
    data = zlib.compress(RAW_2X2)
    size = -(-len(data) // parts)
    return [chunk(b"IDAT", data[i:i + size]) for i in range(0, len(data), size)]


IEND = chunk(b"IEND", b"")


def test_valid_multi_idat_matches_single_idat():
    single = png_to_rgb24(assemble(ihdr(), *idat_split(1), IEND))
    assert png_to_rgb24(assemble(ihdr(), *idat_split(3), IEND)) == single


def test_non_empty_iend_is_refused():
    with pytest.raises(FrameError, match="invalid_png_iend"):
        png_to_rgb24(assemble(ihdr(), *idat_split(), chunk(b"IEND", b"x")))


def test_idat_separated_by_text_chunk_is_refused():
    first, second = idat_split(2)
    with pytest.raises(FrameError, match="noncontiguous_png_idat"):
        png_to_rgb24(assemble(ihdr(), first, chunk(b"tEXt", b"k\x00v"), second, IEND))


@pytest.mark.parametrize("chunks, code", [
    ((ihdr(), ihdr(), *idat_split(), IEND), "invalid_png_header"),
    ((ihdr(), *idat_split(), IEND, IEND), "invalid_png"),
    ((ihdr(), *idat_split()), "invalid_png"),                        # IEND missing
    ((ihdr(), IEND), "invalid_png_iend"),                            # IDAT missing
    ((*idat_split(), IEND), "invalid_png_header"),                   # IHDR missing
    ((ihdr(), *idat_split(), IEND, chunk(b"tEXt", b"k\x00v")), "invalid_png"),
    ((ihdr(), chunk(b"ABCD", b""), *idat_split(), IEND), "unsupported_png_critical_chunk"),
    ((ihdr(), chunk(b"gAMA", bytes(4)), chunk(b"gAMA", bytes(4)), *idat_split(), IEND), "duplicate_png_chunk"),
    ((ihdr(), chunk(b"PLTE", bytes(3)), chunk(b"gAMA", bytes(4)), *idat_split(), IEND), "invalid_png_chunk_order"),
    ((ihdr(), *idat_split(), chunk(b"pHYs", bytes(9)), IEND), "invalid_png_chunk_order"),
    ((ihdr(), chunk(b"PLTE", bytes(4)), *idat_split(), IEND), "invalid_png_palette"),
    ((ihdr(), *idat_split(), chunk(b"PLTE", bytes(3)), IEND), "invalid_png_palette"),
    ((ihdr(), chunk(b"hIST", bytes(2)), *idat_split(), IEND), "invalid_png_chunk_order"),
    ((ihdr(), chunk(b"tIME", bytes(7)), chunk(b"tIME", bytes(7)), *idat_split(), IEND), "duplicate_png_chunk"),
    ((ihdr(), chunk(b"cHRM", bytes(32)), chunk(b"PLTE", bytes(3)), chunk(b"sBIT", bytes(3)), *idat_split(), IEND),
     "invalid_png_chunk_order"),
    ((ihdr(), chunk(b"PLTE", bytes(3)), chunk(b"PLTE", bytes(3)), *idat_split(), IEND), "invalid_png_palette"),
    ((ihdr(), chunk(b"tRNS", bytes(3)), chunk(b"PLTE", bytes(3)), *idat_split(), IEND), "invalid_png_palette"),
    ((ihdr(), chunk(b"abcd", b""), *idat_split(), IEND), "invalid_png_chunk"),  # reserved bit set
])
def test_structurally_invalid_png_is_refused(chunks, code):
    with pytest.raises(FrameError, match=code):
        png_to_rgb24(assemble(*chunks))


def corrupt_crc(data):
    return data[:-1] + bytes([data[-1] ^ 1])


@pytest.mark.parametrize("position", ["ihdr", "text", "idat", "iend"])
def test_malformed_crc_on_any_chunk_is_refused(position):
    parts = {"ihdr": ihdr(), "text": chunk(b"tEXt", b"k\x00v"), "idat": idat_split(1)[0], "iend": IEND}
    parts[position] = corrupt_crc(parts[position])
    with pytest.raises(FrameError, match="invalid_png"):
        png_to_rgb24(assemble(parts["ihdr"], parts["text"], parts["idat"], parts["iend"]))


def test_trns_is_refused_with_a_full_alpha_channel():
    header = struct.pack(">IIBBBBB", 2, 2, 8, 6, 0, 0, 0)
    data = zlib.compress(b"".join(b"\x00" + bytes(8) for _ in range(2)))
    with pytest.raises(FrameError, match="invalid_png_chunk"):
        png_to_rgb24(assemble(chunk(b"IHDR", header), chunk(b"tRNS", bytes(2)), chunk(b"IDAT", data), IEND))


def test_repeated_unknown_ancillary_and_apng_style_chunks_are_not_wrongly_refused():
    first = idat_split(1)[0]
    plain = png_to_rgb24(assemble(ihdr(), first, IEND))
    after = assemble(ihdr(), chunk(b"acTL", bytes(8)), chunk(b"prVT", b"a"), chunk(b"prVT", b"b"), first,
                     chunk(b"fcTL", bytes(26)), chunk(b"fdAT", bytes(8)), chunk(b"fcTL", bytes(26)), IEND)
    assert png_to_rgb24(after) == plain


def test_ancillary_chunks_in_legal_positions_are_accepted_and_ignored():
    plain = png_to_rgb24(assemble(ihdr(), *idat_split(), IEND))
    decorated = assemble(
        ihdr(), chunk(b"cHRM", bytes(32)), chunk(b"gAMA", bytes(4)), chunk(b"sRGB", b"\x00"), chunk(b"sBIT", bytes(3)),
        chunk(b"iCCP", b"p\x00\x00x"), chunk(b"PLTE", bytes(6)),
        chunk(b"bKGD", bytes(2)), chunk(b"pHYs", bytes(9)), chunk(b"tEXt", b"k\x00v"), chunk(b"tEXt", b"a\x00b"),
        *idat_split(2), chunk(b"tIME", bytes(7)), chunk(b"eXIf", b"II"), chunk(b"zTXt", b"k\x00\x00x"), IEND)
    assert png_to_rgb24(decorated) == plain


def test_invalid_png_is_always_a_frame_error_never_a_partial_frame():
    good = assemble(ihdr(), *idat_split(), IEND)
    for cut in range(len(SIGNATURE), len(good)):
        with pytest.raises(FrameError):
            png_to_rgb24(good[:cut])
