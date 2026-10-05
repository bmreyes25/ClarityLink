"""Offline, evidence-bounded dual-screen host receiver core.

This is an executable host laboratory receiver, not a replacement Honda ELF.
Type111 encrypted media and actual Honda integration fail closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import socket
from typing import Any, Callable, Mapping

from .decoder import DecodeError, FFmpegDecoder, avcc_to_annexb
from .display import Display1Output, NullDisplay
from .listener import HostListener, ListenerError
from .media import FramingProfile, MediaError, read_profile_message
from .security import ClearLabSecurity, EvidenceRequiredSecurity, ScreenSecurityProvider, SecurityError
from .setup import SetupError, SetupRequest, SetupResponse, append_secondary, primary_unchanged, serialize_lab_plist


class ReceiverError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class FaultInjector:
    """Named, one-shot laboratory faults; never driven by peer input."""

    def __init__(self, *points: str) -> None:
        self.points = set(points)

    def check(self, point: str) -> None:
        if point in self.points:
            self.points.remove(point)
            raise ReceiverError(f"fault_{point}")


class ReceiverState(str, Enum):
    IDLE = "IDLE"
    AUTHENTICATED_SESSION = "AUTHENTICATED_SESSION"  # Harness only; no MFi auth implementation.
    INFO_EXCHANGED = "INFO_EXCHANGED"
    PRIMARY_ACTIVE = "PRIMARY_ACTIVE"
    SECONDARY_ACTIVE = "SECONDARY_ACTIVE"
    BOTH_ACTIVE = "BOTH_ACTIVE"
    FAILED = "FAILED"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class ResourceSnapshot:
    sessions: int
    primary_listeners: int
    secondary_listeners: int
    security_contexts: int
    decoders: int
    displayed_frames: int
    display_uncleared: int


class Receiver:
    def __init__(self, *, clear_lab: bool = False, display: Display1Output | None = None,
                 faults: FaultInjector | None = None,
                 framing_profile: str = FramingProfile.LEGACY_HONDA_TYPE110,
                 security_factory: Callable[[], ScreenSecurityProvider] | None = None) -> None:
        self.clear_lab = clear_lab
        self.framing_profile = framing_profile
        self.security_factory = security_factory
        self.codec_prefix = b""
        self.display = display if display is not None else NullDisplay()
        self.generation = 0
        self.state = ReceiverState.IDLE
        self.primary: HostListener | None = None
        self.secondary: HostListener | None = None
        self.primary_id: int | None = None
        self.secondary_id: int | None = None
        self.security: ScreenSecurityProvider | None = None
        self.decoder: FFmpegDecoder | None = None
        self.events: list[str] = []
        self.last_response: SetupResponse | None = None
        self.frames = 0
        self.display_uncleared = False
        self.faults = faults if faults is not None else FaultInjector()

    def start_session(self) -> int:
        self.faults.check("session_creation")
        if self.state not in (ReceiverState.IDLE, ReceiverState.CLOSED):
            raise ReceiverError("session_already_active")
        self.generation += 1
        self.last_response = None
        self.frames = 0
        self.codec_prefix = b""
        self.display_uncleared = False
        if hasattr(self.display, "begin_generation"):
            self.display.begin_generation(self.generation)
        self.state = ReceiverState.AUTHENTICATED_SESSION
        self.events.append("SESSION_CREATED")
        return self.generation

    def info_exchanged(self, generation: int) -> None:
        self._require_generation(generation)
        if self.state is not ReceiverState.AUTHENTICATED_SESSION:
            raise ReceiverError("info_out_of_order")
        self.state = ReceiverState.INFO_EXCHANGED
        self.events.append("INFO_EXCHANGED")

    def _require_generation(self, generation: int) -> None:
        if generation != self.generation or self.state in (ReceiverState.IDLE, ReceiverState.CLOSED, ReceiverState.FAILED):
            raise ReceiverError("stale_or_closed_session")

    def _sync_state(self) -> None:
        if self.primary and self.secondary:
            self.state = ReceiverState.BOTH_ACTIVE
        elif self.primary:
            self.state = ReceiverState.PRIMARY_ACTIVE
        elif self.secondary:
            self.state = ReceiverState.SECONDARY_ACTIVE
        else:
            self.state = ReceiverState.INFO_EXCHANGED

    def setup(self, request_fields: Mapping[str, Any], generation: int) -> SetupResponse:
        self._require_generation(generation)
        if self.state is ReceiverState.AUTHENTICATED_SESSION:
            raise ReceiverError("info_required")
        self.events.append("SETUP_BEGIN")
        try:
            self.faults.check("setup_validation")
            request = SetupRequest.parse(request_fields, generation)
        except (SetupError, ReceiverError) as exc:
            self.events.append("SETUP_REJECTED")
            raise ReceiverError(exc.code) from exc
        for item in request.streams:
            if item.type not in (110, 111):
                raise ReceiverError("unsupported_stream_type")
            if item.stream_connection_id in (self.primary_id, self.secondary_id):
                raise ReceiverError("duplicate_stream_connection_id")

        prior_primary = self.primary
        prior_primary_id = self.primary_id
        new_primary: HostListener | None = None
        new_secondary: HostListener | None = None
        security: ScreenSecurityProvider | None = None
        decoder: FFmpegDecoder | None = None
        # Rebuild from live resources: a prior response may name a torn-down stream.
        original: dict[str, Any] = {"streams": []}
        if prior_primary:
            original["streams"].append({"type": 110, "dataPort": prior_primary.port})
        if self.secondary:
            original["streams"].append({"type": 111, "dataPort": self.secondary.port})
        primary_requested = next((x for x in request.streams if x.type == 110), None)
        secondary_requested = next((x for x in request.streams if x.type == 111), None)
        try:
            if primary_requested:
                if prior_primary:
                    raise ReceiverError("primary_already_active")
                self.faults.check("primary_listener")
                new_primary = HostListener.create(generation)
                original["streams"].append({"type": 110, "dataPort": new_primary.port})
            # Original primary is frozen logically before secondary allocation.
            primary_snapshot = serialize_lab_plist(original)
            if secondary_requested:
                if self.secondary:
                    raise ReceiverError("secondary_already_active")
                self.faults.check("listener_bind")
                new_secondary = HostListener.create(generation)
                security = (self.security_factory() if self.security_factory else
                            ClearLabSecurity() if self.clear_lab else EvidenceRequiredSecurity())
                assert secondary_requested.stream_connection_id is not None
                self.faults.check("security")
                security.open(generation, secondary_requested.stream_connection_id)
                self.faults.check("decoder")
                decoder = FFmpegDecoder()
                self.faults.check("response")
                candidate = append_secondary(original, request, new_secondary.port)
                if not primary_unchanged(original, candidate.fields):
                    raise ReceiverError("primary_preservation_failed")
            else:
                candidate = SetupResponse(original, primary_snapshot)
            if serialize_lab_plist(original) != primary_snapshot:
                raise ReceiverError("primary_snapshot_changed")
            self.faults.check("commit")
        except (ReceiverError, SetupError, ListenerError, SecurityError, DecodeError) as exc:
            if decoder:
                decoder.close()
            if security:
                security.close()
            if new_secondary:
                new_secondary.close()
            # A combined request may still establish Type110 when child setup fails.
            if new_primary:
                self.primary = new_primary
                assert primary_requested is not None
                self.primary_id = primary_requested.stream_connection_id
                self.events.append("PRIMARY_READY")
            self._sync_state()
            self.events.append("SECONDARY_ROLLBACK")
            if new_primary or prior_primary:
                fallback = SetupResponse(original, serialize_lab_plist(original))
                self.last_response = fallback
                return fallback
            code = exc.code if hasattr(exc, "code") else "setup_failed"
            raise ReceiverError(code) from exc

        if new_primary:
            self.primary = new_primary
            assert primary_requested is not None
            self.primary_id = primary_requested.stream_connection_id
            self.events.append("PRIMARY_READY")
        if new_secondary:
            self.secondary = new_secondary
            self.secondary_id = secondary_requested.stream_connection_id if secondary_requested else None
            self.security = security
            self.decoder = decoder
            self.events.append("SECONDARY_READY")
        self._sync_state()
        self.last_response = candidate
        self.events.append("SETUP_COMMIT")
        assert prior_primary is self.primary or prior_primary is None
        assert prior_primary_id == self.primary_id or prior_primary_id is None
        return candidate

    def accept_secondary(self, generation: int, timeout: float = 1.0) -> socket.socket:
        self._require_generation(generation)
        if not self.secondary:
            raise ReceiverError("secondary_not_active")
        try:
            connection = self.secondary.accept(generation, timeout)
        except ListenerError as exc:
            raise ReceiverError(exc.code) from exc
        self.events.append("SECONDARY_CONNECTED")
        return connection

    def receive_secondary_frame(self, generation: int) -> bytes:
        self._require_generation(generation)
        if not self.secondary or not self.secondary.accepted or not self.security or not self.decoder:
            raise ReceiverError("secondary_not_connected")
        try:
            self.faults.check("media")
            message = read_profile_message(self.secondary.accepted, generation, self.framing_profile)
            if message.opcode == 1:
                if self.framing_profile != FramingProfile.CURRENT_IOS_TYPE111:
                    raise ReceiverError("video_config_not_implemented")
                from .decoder import parse_avcc_config
                self.codec_prefix = parse_avcc_config(message.body)
                self.events.append("VIDEO_CONFIG_RECEIVED")
                return b""
            clear = self.security.unprotect(generation, message.body, message.header)
            if self.framing_profile == FramingProfile.CURRENT_IOS_TYPE111:
                clear = self.codec_prefix + (clear if clear.startswith(b"\x00\x00\x00\x01") else
                                             avcc_to_annexb(clear))
            self.faults.check("decode")
            decoded = self.decoder.decode(clear, message.timestamp, generation)
            self.faults.check("display")
            self.display.show(decoded)
            self.frames += 1
            self.events.append("FRAME_DISPLAYED")
            return decoded.png
        except (MediaError, SecurityError, DecodeError, ReceiverError, OSError) as exc:
            self.events.append("SECONDARY_MEDIA_FAILED")
            self.teardown_secondary(generation)
            code = exc.code if hasattr(exc, "code") else "display_failed"
            raise ReceiverError(code) from exc

    def teardown_secondary(self, generation: int) -> None:
        if generation != self.generation:
            return
        try:
            self.faults.check("teardown")
        except ReceiverError:
            self.events.append("TEARDOWN_FAULT_CONTAINED")
        try:
            self.display.clear()
        except Exception:
            self.display_uncleared = True
            self.events.append("DISPLAY_CLEAR_FAILED")
        else:
            self.display_uncleared = False
        if self.decoder:
            try:
                self.decoder.close()
            except Exception:
                self.events.append("DECODER_CLOSE_FAILED")
            else:
                self.decoder = None
        if self.security:
            try:
                self.security.close()
            except Exception:
                self.events.append("SECURITY_CLOSE_FAILED")
            else:
                self.security = None
        if self.secondary:
            try:
                self.secondary.close()
            except Exception:
                self.events.append("LISTENER_CLOSE_FAILED")
            else:
                self.secondary = None
        if self.secondary is None and self.security is None and self.decoder is None:
            self.secondary_id = None
            self.codec_prefix = b""
        if self.state not in (ReceiverState.IDLE, ReceiverState.CLOSED, ReceiverState.FAILED):
            self._sync_state()
        self.events.append("SECONDARY_CLOSED")

    def teardown(self, generation: int) -> None:
        if generation != self.generation or self.state in (ReceiverState.IDLE, ReceiverState.CLOSED):
            return
        self.teardown_secondary(generation)
        if self.primary:
            try:
                self.primary.close()
            except Exception:
                self.events.append("PRIMARY_CLOSE_FAILED")
            else:
                self.primary = None
        if self.primary is None:
            self.primary_id = None
        if any((self.primary, self.secondary, self.security, self.decoder, self.display_uncleared)):
            self.state = ReceiverState.FAILED
            self.events.append("GENERATION_CLEANUP_INCOMPLETE")
        else:
            self.state = ReceiverState.CLOSED
            self.events.append("GENERATION_CLOSED")

    def snapshot(self) -> ResourceSnapshot:
        return ResourceSnapshot(
            0 if self.state in (ReceiverState.IDLE, ReceiverState.CLOSED) else 1,
            int(self.primary is not None), int(self.secondary is not None),
            int(self.security is not None), int(self.decoder is not None),
            int(getattr(self.display, "current", None) is not None),
            int(self.display_uncleared),
        )
