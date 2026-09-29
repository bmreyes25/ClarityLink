"""Bounded parser for the avcC fields consumed by Honda's jmcs helper.

Honda's H264ConvertAVCCtoAnnexBHeader reads the SPS/PPS arrays and derives
NAL length width from byte 4. It does not validate configurationVersion or
the profile bytes, so this model preserves those bytes without claiming
Honda validates their values.
"""

from __future__ import annotations

from dataclasses import dataclass


class VideoConfigError(ValueError):
    """Malformed AVCDecoderConfigurationRecord-style input."""


@dataclass(frozen=True)
class VideoConfig:
    raw: bytes
    configuration_version: int
    profile: int
    compatibility: int
    level: int
    nal_length_size: int
    sequence_parameter_sets: tuple[bytes, ...]
    picture_parameter_sets: tuple[bytes, ...]
    pps_count_present: bool
    trailing_data: bytes

    @property
    def annex_b_parameter_sets(self) -> bytes:
        start_code = b"\x00\x00\x00\x01"
        return b"".join(
            start_code + nal
            for nal in (*self.sequence_parameter_sets, *self.picture_parameter_sets)
        )


class VideoConfigParser:
    """Parse the portions of avcC directly read by Honda's helper.

    Honda accepts a buffer ending immediately after its SPS list without a
    PPS-count byte. This parser retains that observed edge behavior. Any bytes
    after the parsed PPS list are preserved as opaque trailing data.
    """

    @staticmethod
    def parse(data: bytes | bytearray | memoryview) -> VideoConfig:
        raw = bytes(data)
        if len(raw) < 6:
            raise VideoConfigError("configuration needs the six-byte avcC prefix")

        nal_length_size = (raw[4] & 0x03) + 1
        sps_count = raw[5] & 0x1F
        cursor = 6
        sps: list[bytes] = []

        for index in range(sps_count):
            nal, cursor = _read_nal(raw, cursor, f"SPS[{index}]")
            sps.append(nal)

        pps_present = cursor < len(raw)
        pps: list[bytes] = []
        if pps_present:
            pps_count = raw[cursor]
            cursor += 1
            for index in range(pps_count):
                nal, cursor = _read_nal(raw, cursor, f"PPS[{index}]")
                pps.append(nal)

        return VideoConfig(
            raw=raw,
            configuration_version=raw[0],
            profile=raw[1],
            compatibility=raw[2],
            level=raw[3],
            nal_length_size=nal_length_size,
            sequence_parameter_sets=tuple(sps),
            picture_parameter_sets=tuple(pps),
            pps_count_present=pps_present,
            trailing_data=raw[cursor:],
        )


def _read_nal(data: bytes, cursor: int, label: str) -> tuple[bytes, int]:
    remaining = len(data) - cursor
    if remaining < 2:
        raise VideoConfigError(f"truncated {label} length at offset {cursor}")
    size = int.from_bytes(data[cursor : cursor + 2], "big")
    start = cursor + 2
    remaining = len(data) - start
    if size > remaining:
        raise VideoConfigError(
            f"{label} declares {size} bytes with only {remaining} remaining"
        )
    end = start + size
    return data[start:end], end
