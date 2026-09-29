"""Offline Honda Type-110 screen media pipeline; no socket or rendering API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from h264_extractor import H264ExtractError, H264Extractor
from screen_parser import ScreenFrameParser, ScreenMessage
from video_config import VideoConfig, VideoConfigError, VideoConfigParser


@dataclass(frozen=True)
class VideoConfigEvent:
    config: VideoConfig


@dataclass(frozen=True)
class ConfigMetadataEvent:
    raw_header_fields: bytes


@dataclass(frozen=True)
class VideoMediaBufferEvent:
    data: bytes
    data_format: str
    timestamp_raw: int
    config_prepended: bool


@dataclass(frozen=True)
class UnconfiguredVideoEvent:
    body: bytes
    timestamp_raw: int


@dataclass(frozen=True)
class ControlMessageEvent:
    message_type: int
    body: bytes


@dataclass(frozen=True)
class UnknownMessageEvent:
    message: ScreenMessage
    body: bytes


ReceiverEvent: TypeAlias = (
    VideoConfigEvent
    | ConfigMetadataEvent
    | VideoMediaBufferEvent
    | UnconfiguredVideoEvent
    | ControlMessageEvent
    | UnknownMessageEvent
)


class HondaScreenReceiverCore:
    """Join envelope parsing, optional continuous CTR, config, and H.264.

    Supply a Honda-compatible crypto model when security is enabled. The
    provider/key derivation stays outside this receiver. Every body, including
    config and control bodies, advances that one CTR instance in wire order.
    """

    def __init__(
        self,
        *,
        crypto=None,
        direct_body_mode: bool = False,
        max_body_size: int = 16 * 1024 * 1024,
    ) -> None:
        self._parser = ScreenFrameParser(max_body_size=max_body_size)
        self._crypto = crypto
        # Honda callback context +0x11 bypasses length conversion when set.
        # Its live value is not recovered; callers must select it explicitly.
        self._direct_body_mode = direct_body_mode
        self._config: VideoConfig | None = None
        self._config_pending = False

    @property
    def config(self) -> VideoConfig | None:
        return self._config

    def feed(self, data: bytes | bytearray | memoryview) -> list[ReceiverEvent]:
        events: list[ReceiverEvent] = []
        for message in self._parser.feed(data):
            body = (
                self._crypto.update(message.body_wire)
                if self._crypto is not None
                else message.body_wire
            )
            kind = message.header.message_type
            if kind == 1:
                if not body:
                    events.append(ConfigMetadataEvent(message.header.raw[16:24]))
                    continue
                try:
                    config = VideoConfigParser.parse(body)
                except VideoConfigError:
                    raise
                self._config = config
                self._config_pending = True
                events.append(VideoConfigEvent(self._config))
            elif kind == 0:
                timestamp = message.header.timestamp_raw
                if self._direct_body_mode:
                    events.append(
                        VideoMediaBufferEvent(
                            body, "opaque-body", timestamp, config_prepended=False
                        )
                    )
                elif self._config is None:
                    events.append(UnconfiguredVideoEvent(body, timestamp))
                else:
                    config_prepended = self._config_pending
                    prefix = (
                        self._config.annex_b_parameter_sets if config_prepended else b""
                    )
                    # Honda clears the one-shot flag while beginning this
                    # conversion, before all video records have succeeded.
                    self._config_pending = False
                    try:
                        video_annex_b = H264Extractor.to_annex_b(
                            body, self._config.nal_length_size
                        )
                    except H264ExtractError:
                        raise
                    events.append(
                        VideoMediaBufferEvent(
                            prefix + video_annex_b,
                            "annex-b-normal-record-path",
                            timestamp,
                            config_prepended,
                        )
                    )
            elif kind in (2, 4, 5):
                events.append(ControlMessageEvent(kind, body))
            else:
                events.append(UnknownMessageEvent(message, body))
        return events

    def reset(self, *, reset_crypto: bool = False, iv: bytes | None = None) -> None:
        if reset_crypto and self._crypto is not None and iv is None:
            raise ValueError("an IV is required when resetting crypto")
        self._parser.reset()
        self._config = None
        self._config_pending = False
        if reset_crypto and self._crypto is not None:
            assert iv is not None
            self._crypto.reset(iv)
