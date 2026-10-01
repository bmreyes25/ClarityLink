"""Synthetic-only H.264 media packed through the modeled ScreenStream receiver."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from host_h264_decoder import DecodeStatus, FfmpegCliDecoder, generate_synthetic_h264
from model import ClarityLinkRenderer, MockDisplay1Backend
from receiver_core import HondaScreenReceiverCore, VideoConfigEvent, VideoMediaBufferEvent
from screen_parser import HEADER_SIZE
from video_config import VideoConfigParser


@dataclass(frozen=True)
class SyntheticScreenStreamFixture:
    encoded_annexb: bytes
    nals: tuple[bytes, ...]
    sps: tuple[bytes, ...]
    pps: tuple[bytes, ...]
    vcl: tuple[bytes, ...]
    avcc_config: bytes
    avcc_frame: bytes
    opcode1_packet: bytes
    opcode0_packet: bytes
    width: int = 320
    height: int = 180
    evidence: str = "SYNTHETIC_TEST_VALUE"
    crypto_mode: str = "PLAINTEXT_SYNTHETIC"


def extract_annexb_nals(stream: bytes) -> tuple[bytes, ...]:
    """Split a bounded Annex-B bytestream on three/four-byte start codes."""
    if not stream or len(stream) > 4 * 1024 * 1024:
        raise ValueError("empty or oversized synthetic Annex-B stream")
    markers: list[tuple[int, int]] = []
    index = 0
    while index < len(stream):
        if stream.startswith(b"\x00\x00\x00\x01", index):
            markers.append((index, index + 4))
            index += 4
        elif stream.startswith(b"\x00\x00\x01", index):
            markers.append((index, index + 3))
            index += 3
        else:
            index += 1
    if not markers or any(start >= end for start, end in markers):
        raise ValueError("Annex-B start code not found")
    if stream[:markers[0][0]].strip(b"\x00"):
        raise ValueError("unexpected bytes before first Annex-B NAL")
    nals = []
    for ordinal, (_marker_start, payload_start) in enumerate(markers):
        payload_end = markers[ordinal + 1][0] if ordinal + 1 < len(markers) else len(stream)
        nal = stream[payload_start:payload_end].rstrip(b"\x00")
        if not nal:
            raise ValueError("empty NAL in synthetic Annex-B stream")
        nals.append(nal)
    return tuple(nals)


def build_avcc_config(sps: tuple[bytes, ...], pps: tuple[bytes, ...], nal_length_size: int = 4) -> bytes:
    """Build a small avcC record from parsed synthetic parameter sets."""
    if not sps:
        raise ValueError("at least one SPS is required")
    if not pps:
        raise ValueError("at least one PPS is required")
    if nal_length_size not in (1, 2, 4):
        raise ValueError("NAL length size must be 1, 2, or 4")
    first_sps = sps[0]
    if len(first_sps) < 4 or (first_sps[0] & 0x1F) != 7:
        raise ValueError("SPS lacks profile/compatibility/level bytes")
    if len(sps) > 31 or len(pps) > 255:
        raise ValueError("parameter-set count exceeds avcC field width")
    output = bytearray((
        1,
        first_sps[1],  # profile_idc
        first_sps[2],  # profile_compatibility
        first_sps[3],  # level_idc
        0xFC | (nal_length_size - 1),
        0xE0 | len(sps),
    ))
    for nal in sps:
        if len(nal) > 0xFFFF or (nal[0] & 0x1F) != 7:
            raise ValueError("invalid or oversized SPS")
        output.extend(len(nal).to_bytes(2, "big"))
        output.extend(nal)
    output.append(len(pps))
    for nal in pps:
        if len(nal) > 0xFFFF or (nal[0] & 0x1F) != 8:
            raise ValueError("invalid or oversized PPS")
        output.extend(len(nal).to_bytes(2, "big"))
        output.extend(nal)
    parsed = VideoConfigParser.parse(output)
    if parsed.nal_length_size != nal_length_size:
        raise ValueError("avcC parser returned unexpected NAL length size")
    return bytes(output)


def _screenstream_packet(opcode: int, body: bytes, timestamp: int) -> bytes:
    header = bytearray(HEADER_SIZE)
    header[0:4] = len(body).to_bytes(4, "little")
    header[4] = opcode
    header[8:16] = timestamp.to_bytes(8, "little")
    return bytes(header) + body


def create_synthetic_screenstream_fixture(encoded_annexb: bytes | None = None) -> SyntheticScreenStreamFixture:
    encoded = encoded_annexb if encoded_annexb is not None else generate_synthetic_h264()
    nals = extract_annexb_nals(encoded)
    sps = tuple(nal for nal in nals if nal[0] & 0x1F == 7)
    pps = tuple(nal for nal in nals if nal[0] & 0x1F == 8)
    vcl = tuple(nal for nal in nals if 1 <= (nal[0] & 0x1F) <= 5)
    if not sps or not pps or not vcl:
        raise ValueError("generated media must contain SPS, PPS, and VCL NALs")
    if not any((nal[0] & 0x1F) == 5 for nal in vcl):
        raise ValueError("single-frame synthetic source must contain an IDR access unit")
    nal_length_size = 4
    config = build_avcc_config(sps, pps, nal_length_size)
    frame = b"".join(len(nal).to_bytes(nal_length_size, "big") + nal for nal in vcl)
    return SyntheticScreenStreamFixture(
        encoded_annexb=encoded,
        nals=nals,
        sps=sps,
        pps=pps,
        vcl=vcl,
        avcc_config=config,
        avcc_frame=frame,
        opcode1_packet=_screenstream_packet(1, config, 1_000),
        opcode0_packet=_screenstream_packet(0, frame, 2_000),
    )


def run_fixture_through_transport(
    fixture: SyntheticScreenStreamFixture,
    *, decoder: FfmpegCliDecoder | None = None,
) -> dict[str, Any]:
    """Parse config/video messages, extract Annex-B, decode and mock-render."""
    receiver = HondaScreenReceiverCore(crypto=None)
    config_events = receiver.feed(fixture.opcode1_packet)
    config_event = next((event for event in config_events if isinstance(event, VideoConfigEvent)), None)
    if config_event is None:
        raise AssertionError("opcode 1 did not produce VideoConfigEvent")
    media_events = receiver.feed(fixture.opcode0_packet)
    media_event = next((event for event in media_events if isinstance(event, VideoMediaBufferEvent)), None)
    if media_event is None:
        raise AssertionError("opcode 0 did not produce VideoMediaBufferEvent")
    media_nals = extract_annexb_nals(media_event.data)
    nal_types = sorted({nal[0] & 0x1F for nal in media_nals})
    active_decoder = decoder or FfmpegCliDecoder()
    decode = active_decoder.decode_access_unit(
        media_event.data,
        width=fixture.width,
        height=fixture.height,
        timestamp_ns=1_000_000_000,
        frame_index=0,
    )
    if decode.status is not DecodeStatus.DECODED or decode.frame is None:
        return {
            "status": "ATTEMPTED_FAILED",
            "reason": decode.reason or decode.status.value,
            "config": config_event.config,
            "media": media_event,
            "nal_types": nal_types,
            "decoder_status": decode.status.value,
            "evidence": "SYNTHETIC_TEST_VALUE",
        }
    backend = MockDisplay1Backend()
    renderer = ClarityLinkRenderer(backend)
    renderer.start()
    renderer.submit(decode.frame)
    rendered = len(backend.frames) == 1 and backend.frames[0] == decode.frame
    target = backend.target.display_id if backend.target else None
    renderer.close()
    return {
        "status": "PASS" if rendered else "ATTEMPTED_FAILED",
        "reason": "" if rendered else "renderer did not retain decoded frame",
        "config": config_event.config,
        "media": media_event,
        "nal_types": nal_types,
        "frame": decode.frame,
        "rendered": rendered,
        "renderer_target": target,
        "evidence": "SYNTHETIC_TEST_VALUE",
        "crypto_mode": fixture.crypto_mode,
        "packet_lengths": {
            "opcode1": len(fixture.opcode1_packet),
            "opcode0": len(fixture.opcode0_packet),
        },
        "media_dimensions": [fixture.width, fixture.height],
        "rgba_payload_size": len(decode.frame.rgba or b""),
        "sps_count": len(fixture.sps),
        "pps_count": len(fixture.pps),
        "vcl_count": len(fixture.vcl),
        "avcc_config_length": len(fixture.avcc_config),
        "avcc_frame_length": len(fixture.avcc_frame),
        "encoded_annexb_length": len(fixture.encoded_annexb),
    }
