"""Drive one receiver generation from an authenticated or explicit replay transport."""
from __future__ import annotations

from .authentication import AuthenticationProvider, SessionOrigin
from .info import InfoProfile, build_info
from .receiver import Receiver, ReceiverError
from .session_transport import (CarPlaySessionTransport, ControlRequest, ControlResponse,
                                LabSessionTransport, ReplaySessionTransport, TransportError)
from .trace import SanitizedTrace, TraceEvent


class SessionError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ReceiverSession:
    def __init__(self, provider: AuthenticationProvider, receiver: Receiver,
                 info_profile: InfoProfile, *, trace: SanitizedTrace | None = None,
                 allow_replay: bool = False) -> None:
        self.provider = provider
        self.receiver = receiver
        self.info_profile = info_profile
        self.trace = trace if trace is not None else SanitizedTrace()
        self.allow_replay = allow_replay
        self.transport: CarPlaySessionTransport | None = None
        self.generation: int | None = None
        self._info_sent = False

    def open(self, replay_transport: ReplaySessionTransport | None = None) -> None:
        if self.transport is not None:
            raise SessionError("session_already_open")
        self.trace.emit(TraceEvent.AUTH_START, status="begin")
        transport: CarPlaySessionTransport | None = None
        handoff = None
        owns_handoff = False
        try:
            self.provider.initialize()
            expected_generation = self.receiver.generation + 1
            handoff = self.provider.authenticate(expected_generation)
            if handoff.generation != expected_generation or handoff.closed:
                raise SessionError("session_generation_mismatch")
            handoff.claim(expected_generation)
            owns_handoff = True
            if handoff.origin is SessionOrigin.SANITIZED_REPLAY:
                if not self.allow_replay or replay_transport is None:
                    raise SessionError("replay_not_enabled")
                if replay_transport.generation != handoff.generation or replay_transport.session_identifier != handoff.session_identifier:
                    raise SessionError("replay_handoff_mismatch")
                transport: CarPlaySessionTransport = replay_transport
            elif handoff.origin is SessionOrigin.AUTHENTICATED_LAB:
                if replay_transport is not None:
                    raise SessionError("live_replay_mixed")
                transport = LabSessionTransport(handoff)
                if not transport.authenticated:
                    raise SessionError("transport_not_authenticated")
            else:
                raise SessionError("unsupported_session_origin")
            generation = self.receiver.start_session()
            if generation != handoff.generation:
                self.receiver.teardown(generation)
                transport.close()
                raise SessionError("session_generation_mismatch")
            self.generation = generation
            self.transport = transport
            self.trace.emit(TraceEvent.AUTH_SUCCESS, generation=generation, status="ok")
            self.trace.emit(TraceEvent.SESSION_OPEN, generation=generation)
        except Exception:
            if self.generation is not None:
                self.receiver.teardown(self.generation)
                self.generation = None
            if transport is not None:
                transport.close()
            if handoff is not None and owns_handoff:
                handoff.close()
            self.trace.emit(TraceEvent.AUTH_FAILURE, status="failed")
            self.provider.close()
            raise

    def handle_one(self, timeout: float = 5.0) -> ControlResponse:
        try:
            return self._handle_one(timeout)
        except Exception:
            self.close()
            raise

    def _handle_one(self, timeout: float) -> ControlResponse:
        if self.transport is None or self.generation is None:
            raise SessionError("session_not_open")
        request: ControlRequest = self.transport.read_request(timeout)
        if request.generation != self.generation:
            raise SessionError("stale_control_request")
        self.trace.emit_request(request)
        if request.method == "GET" and request.path == "/info":
            self.trace.emit(TraceEvent.INFO_REQUEST, generation=self.generation)
            if self._info_sent:
                raise SessionError("duplicate_info_request")
            info = build_info(self.info_profile)
            self.receiver.info_exchanged(self.generation)
            self._info_sent = True
            response = ControlResponse(200, info, self.generation)
            self.transport.write_response(response)
            self.trace.emit(TraceEvent.INFO_RESPONSE, generation=self.generation, status="ok")
            return response
        if request.method == "SETUP" and request.path == "/session":
            if not self._info_sent:
                raise SessionError("info_required")
            self.trace.emit(TraceEvent.SETUP_REQUEST, generation=self.generation)
            streams = request.body.get("streams")
            if isinstance(streams, (list, tuple)):
                for entry in streams[:16]:
                    if isinstance(entry, dict) and entry.get("type") in (110, 111):
                        event = TraceEvent.SETUP_TYPE110 if entry["type"] == 110 else TraceEvent.SETUP_TYPE111
                        self.trace.emit(event, generation=self.generation, stream_type=entry["type"])
            result = self.receiver.setup(request.body, self.generation)
            response = ControlResponse(200, result.fields, self.generation)
            self.transport.write_response(response)
            self.trace.emit(TraceEvent.SETUP_RESPONSE, generation=self.generation, status="ok")
            return response
        raise SessionError("unsupported_control_request")

    def close(self) -> None:
        generation = self.generation
        transport = self.transport
        self.transport = None
        self.generation = None
        self._info_sent = False
        try:
            if generation is not None:
                self.receiver.teardown(generation)
                self.trace.emit(TraceEvent.SESSION_TEARDOWN, generation=generation)
        finally:
            try:
                if transport is not None:
                    transport.close()
                    self.trace.emit(TraceEvent.SESSION_CLOSE, generation=generation)
            finally:
                self.provider.close()
