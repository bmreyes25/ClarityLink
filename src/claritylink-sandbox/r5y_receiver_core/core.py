"""R5Y deterministic orchestration; symbolic data and project-owned mocks only."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .adapters import (
    DecoderProvider, DisplayProvider, DisplaySink, ListenerHandle, ListenerProvider,
    MockDecoder, MockDecoderProvider, MockDisplayProvider, MockListenerProvider,
    MockSecurityProvider, SecurityContext, SecurityProvider,
)
from .model import (
    CleanupResult, DisplayFrame, MediaFrame, ModelEvent, PrimaryStreamState,
    ReceiverError, ReceiverSession, ReceiverState, ResourceSnapshot, SecondaryStreamState,
    SessionGeneration, SetupRequest, SetupResponse, StreamDescriptor, capture_primary,
    primary_preserved,
)


class FailurePoint(str, Enum):
    SESSION_CREATION = "session_creation"
    SETUP_VALIDATION = "setup_validation"
    SECONDARY_RESPONSE_CREATION = "secondary_response_creation"
    LISTENER_ALLOCATION = "listener_allocation"
    SECURITY_INITIALIZATION = "security_initialization"
    DECODER_INITIALIZATION = "decoder_initialization"
    DISPLAY_INITIALIZATION = "display_initialization"
    SETUP_COMMIT = "setup_commit"
    FIRST_FRAME = "first_frame"
    MID_STREAM_FRAME = "mid_stream_frame"
    DECODER_PROCESSING = "decoder_processing"
    DISPLAY_UPDATE = "display_update"
    TEARDOWN = "teardown"
    DUPLICATE_TEARDOWN = "duplicate_teardown"


class FaultInjector:
    """Named one-shot faults, with no clock, randomness, external input or I/O."""

    def __init__(self, *points: FailurePoint) -> None:
        self.pending = set(points)
        if len(self.pending) != len(points):
            raise ReceiverError("duplicate_fault_point")

    def trip(self, point: FailurePoint) -> None:
        if point in self.pending:
            self.pending.remove(point)
            raise ReceiverError("injected_" + point.value)


@dataclass
class SetupTransaction:
    generation: SessionGeneration
    original: SetupResponse
    candidate: SetupResponse | None = None
    committed: bool = False
    aborted: bool = False

    def set_candidate(self, candidate: SetupResponse) -> None:
        if self.committed or self.aborted or candidate.streams[0] is not self.original.streams[0]:
            raise ReceiverError("invalid_transaction_candidate")
        self.candidate = candidate

    def commit(self) -> SetupResponse:
        if self.committed or self.aborted:
            raise ReceiverError("transaction_not_pending")
        self.committed = True
        return self.candidate if self.candidate is not None else self.original

    def abort(self) -> SetupResponse:
        if self.committed:
            raise ReceiverError("committed_transaction_cannot_abort")
        self.aborted = True
        self.candidate = None
        return self.original


@dataclass
class _OwnedSecondary:
    generation: SessionGeneration
    listener: ListenerHandle | None = None
    security: SecurityContext | None = None
    decoder: MockDecoder | None = None
    display: DisplaySink | None = None
    stream: SecondaryStreamState | None = None
    media_active: bool = False
    unresolved: bool = False


class CleanupManager:
    """Owns only symbolic secondary resources, keyed by exact generation."""

    def __init__(self) -> None:
        self._owned: dict[SessionGeneration, _OwnedSecondary] = {}

    def reserve(self, generation: SessionGeneration) -> _OwnedSecondary:
        if generation in self._owned:
            raise ReceiverError("secondary_generation_already_owned")
        child = _OwnedSecondary(generation)
        self._owned[generation] = child
        return child

    def owned(self, generation: SessionGeneration) -> _OwnedSecondary | None:
        return self._owned.get(generation)

    def cleanup(self, generation: SessionGeneration, *, inject_teardown_error: bool = False) -> CleanupResult:
        child = self._owned.get(generation)
        if child is None:
            return CleanupResult(False, generation)
        errors: list[str] = []
        child.media_active = False
        if child.display is not None:
            try:
                child.display.clear("teardown")
                child.display.close()
            except Exception as exc:
                errors.append("display_close_" + type(exc).__name__)
        if inject_teardown_error:
            errors.append("injected_teardown")
        if child.decoder is not None:
            try:
                child.decoder.close()
            except Exception as exc:
                errors.append("decoder_close_" + type(exc).__name__)
        if child.security is not None:
            try:
                child.security.destroy()
            except Exception as exc:
                errors.append("security_close_" + type(exc).__name__)
        if child.listener is not None:
            try:
                child.listener.close(generation)
            except Exception as exc:
                errors.append("listener_close_" + type(exc).__name__)
        if child.stream is not None:
            child.stream.active = False
        actual_errors = tuple(error for error in errors if error != "injected_teardown")
        if not actual_errors:
            self._owned.pop(generation, None)
        else:
            child.unresolved = True
        return CleanupResult(True, generation, tuple(errors))

    def counts(self) -> tuple[int, int, int, int, int, int]:
        values = tuple(self._owned.values())
        return (
            sum(item.stream is not None and item.stream.active for item in values),
            sum(item.listener is not None and not item.listener.closed for item in values),
            sum(item.security is not None and not item.security.destroyed for item in values),
            sum(item.decoder is not None and not item.decoder.closed for item in values),
            sum(item.display is not None and not item.display.closed for item in values),
            sum(item.unresolved for item in values),
        )


class ReceiverCore:
    """Stable host-facing facade; providers are replaceable symbolic interfaces."""

    def __init__(
        self, *, listener_provider: ListenerProvider | None = None,
        security_provider: SecurityProvider | None = None,
        decoder_provider: DecoderProvider | None = None,
        display_provider: DisplayProvider | None = None,
    ) -> None:
        self.listener_provider = listener_provider or MockListenerProvider()
        self.security_provider = security_provider or MockSecurityProvider()
        self.decoder_provider = decoder_provider or MockDecoderProvider()
        self.display_provider = display_provider or MockDisplayProvider()
        self.cleanup_manager = CleanupManager()
        self.sessions: dict[SessionGeneration, ReceiverSession] = {}
        self.current: SessionGeneration | None = None
        self.events: list[ModelEvent] = []

    def _event(self, kind: str, generation: SessionGeneration, detail: str = "") -> None:
        self.events.append(ModelEvent(len(self.events) + 1, kind, generation.value, detail))

    def _session(self, generation: SessionGeneration) -> ReceiverSession:
        try:
            return self.sessions[generation]
        except KeyError:
            raise ReceiverError("unknown_generation") from None

    def create_session(
        self, session_id: str, generation: SessionGeneration,
        *, faults: FaultInjector | None = None,
    ) -> ReceiverSession:
        faults = faults or FaultInjector()
        faults.trip(FailurePoint.SESSION_CREATION)
        if not session_id.startswith("session-") or any(generation.value <= key.value for key in self.sessions):
            raise ReceiverError("invalid_or_reused_session_generation")
        if self.current is not None and self._session(self.current).state is not ReceiverState.CLOSED:
            self.teardown(self.current)
        primary_descriptor = StreamDescriptor(110, f"synthetic-primary-{generation.value}")
        primary = PrimaryStreamState(session_id, primary_descriptor)
        session = ReceiverSession(session_id, generation, primary, SetupResponse((primary_descriptor,)))
        session.transition(ReceiverState.SESSION_CREATED)
        self.sessions[generation] = session
        self.current = generation
        self._event("SESSION_CREATED", generation)
        return session

    def setup(self, request: SetupRequest, *, faults: FaultInjector | None = None) -> ReceiverSession:
        faults = faults or FaultInjector()
        session = self._session(request.generation)
        if session.state is not ReceiverState.SESSION_CREATED or self.current != request.generation:
            raise ReceiverError("setup_requires_current_new_session")
        session.transition(ReceiverState.SETUP_RECEIVED)
        self._event("SETUP_BEGIN", request.generation)
        original = session.response
        transaction = SetupTransaction(request.generation, original)
        session.pending_transaction = True
        session.primary_snapshot = capture_primary(session.primary, original)
        self._event("PRIMARY_SNAPSHOT", request.generation)
        try:
            faults.trip(FailurePoint.SETUP_VALIDATION)
            if request.session_id != session.session_id or request.primary is not session.primary.descriptor:
                raise ReceiverError("setup_session_or_primary_mismatch")
            session.transition(ReceiverState.PRIMARY_READY)
            if not request.request_secondary:
                session.response = transaction.commit()
                self._event("SETUP_COMMIT", request.generation, "primary_only")
                return session
            session.transition(ReceiverState.SECONDARY_NEGOTIATING)
            self._event("SECONDARY_ENABLE", request.generation)
            child = self.cleanup_manager.reserve(request.generation)
            faults.trip(FailurePoint.LISTENER_ALLOCATION)
            child.listener = self.listener_provider.allocate(request.generation)
            if child.listener.generation != request.generation:
                raise ReceiverError("listener_owner_mismatch")
            self._event("LISTENER_ALLOCATED", request.generation)
            child.security = self.security_provider.create(request.generation)
            if child.security.generation != request.generation:
                raise ReceiverError("security_owner_mismatch")
            faults.trip(FailurePoint.SECURITY_INITIALIZATION)
            child.security.initialize()
            self._event("SECURITY_READY", request.generation)
            child.decoder = self.decoder_provider.create(request.generation)
            if child.decoder.generation != request.generation:
                raise ReceiverError("decoder_owner_mismatch")
            faults.trip(FailurePoint.DECODER_INITIALIZATION)
            self._event("DECODER_READY", request.generation)
            child.display = self.display_provider.create(request.generation)
            if child.display.generation != request.generation:
                raise ReceiverError("display_owner_mismatch")
            faults.trip(FailurePoint.DISPLAY_INITIALIZATION)
            self._event("DISPLAY_READY", request.generation)
            faults.trip(FailurePoint.SECONDARY_RESPONSE_CREATION)
            descriptor = StreamDescriptor(111, f"synthetic-secondary-{request.generation.value}", child.listener.port_label)
            child.stream = SecondaryStreamState(request.generation, descriptor)
            transaction.set_candidate(SetupResponse(original.streams + (descriptor,)))
            faults.trip(FailurePoint.SETUP_COMMIT)
            if not primary_preserved(session.primary, transaction.candidate, session.primary_snapshot):
                raise ReceiverError("primary_preservation_failed")
            session.response = transaction.commit()
            session.secondary = child.stream
            session.transition(ReceiverState.SECONDARY_READY)
            self._event("SETUP_COMMIT", request.generation, "secondary")
            return session
        except Exception as exc:
            code = exc.code if isinstance(exc, ReceiverError) else "adapter_" + type(exc).__name__
            session.last_secondary_error = code
            self.cleanup_manager.cleanup(request.generation)
            session.secondary = None
            session.response = transaction.abort()
            if session.state is ReceiverState.SETUP_RECEIVED:
                session.transition(ReceiverState.PRIMARY_READY)
            elif session.state is ReceiverState.SECONDARY_NEGOTIATING:
                session.transition(ReceiverState.PRIMARY_READY)
            self._event("SETUP_ROLLBACK", request.generation, code)
            return session
        finally:
            session.pending_transaction = False

    def start_streaming(self, generation: SessionGeneration) -> None:
        session = self._session(generation)
        if self.current != generation:
            raise ReceiverError("stale_stream_start")
        session.transition(ReceiverState.STREAMING)
        child = self.cleanup_manager.owned(generation)
        if child is not None:
            child.listener.accept(generation)
            child.media_active = True
        self._event("STREAMING", generation)

    def send_frame(self, frame: MediaFrame, *, faults: FaultInjector | None = None) -> bool:
        faults = faults or FaultInjector()
        generation = frame.generation
        if self.current != generation:
            self._event("FRAME_REJECTED_GENERATION", generation)
            return False
        session = self._session(generation)
        child = self.cleanup_manager.owned(generation)
        if session.state is not ReceiverState.STREAMING or child is None or child.stream is None or not child.media_active:
            self._event("FRAME_REJECTED_STATE", generation)
            return False
        if frame.sequence != child.stream.last_sequence + 1:
            child.display.clear("stale")
            self._event("FRAME_REJECTED_STALE", generation)
            return False
        try:
            faults.trip(FailurePoint.FIRST_FRAME if frame.sequence == 1 else FailurePoint.MID_STREAM_FRAME)
            clear_symbol = child.security.unwrap_symbol(frame)
            faults.trip(FailurePoint.DECODER_PROCESSING)
            decoded = child.decoder.decode(frame.sequence, clear_symbol)
            faults.trip(FailurePoint.DISPLAY_UPDATE)
            child.display.show(DisplayFrame(generation, frame.sequence, decoded.symbol))
            child.stream.last_sequence = frame.sequence
            self._event("FRAME_ACCEPTED", generation, str(frame.sequence))
            return True
        except Exception as exc:
            code = exc.code if isinstance(exc, ReceiverError) else "adapter_" + type(exc).__name__
            child.display.clear("error")
            self.cleanup_manager.cleanup(generation)
            session.secondary = None
            session.last_secondary_error = code
            session.transition(ReceiverState.PRIMARY_READY)
            self._event("SECONDARY_FAILED", generation, code)
            return False

    def clear_display(self, generation: SessionGeneration, reason: str) -> None:
        if reason not in ("lost", "reroute", "stale", "session_death"):
            raise ReceiverError("invalid_clear_reason")
        child = self.cleanup_manager.owned(generation)
        if self.current == generation and child is not None and child.display is not None:
            child.display.clear(reason)
            self._event("DISPLAY_CLEARED", generation, reason)

    def teardown(self, generation: SessionGeneration, *, faults: FaultInjector | None = None) -> CleanupResult:
        faults = faults or FaultInjector()
        session = self._session(generation)
        if session.state is ReceiverState.CLOSED:
            if self.cleanup_manager.owned(generation) is not None:
                return self.cleanup_manager.cleanup(generation)
            try:
                faults.trip(FailurePoint.DUPLICATE_TEARDOWN)
            except ReceiverError:
                self._event("DUPLICATE_TEARDOWN", generation)
            return CleanupResult(False, generation)
        session.transition(ReceiverState.TEARDOWN_PENDING)
        self._event("TEARDOWN_BEGIN", generation)
        inject_error = False
        try:
            faults.trip(FailurePoint.TEARDOWN)
        except ReceiverError:
            inject_error = True
        result = self.cleanup_manager.cleanup(generation, inject_teardown_error=inject_error)
        session.secondary = None
        session.pending_transaction = False
        session.transition(ReceiverState.CLOSED)
        self._event("DISPLAY_CLEARED", generation, "teardown")
        self._event("LISTENER_CLOSED", generation)
        self._event("GENERATION_CLOSED", generation)
        return result

    def resource_snapshot(self) -> ResourceSnapshot:
        streams, listeners, security, decoders, displays, unresolved = self.cleanup_manager.counts()
        return ResourceSnapshot(
            sum(session.state is not ReceiverState.CLOSED for session in self.sessions.values()),
            streams, listeners, security, decoders, displays,
            sum(session.pending_transaction for session in self.sessions.values()),
            unresolved,
        )

    def primary_intact(self, generation: SessionGeneration) -> bool:
        session = self._session(generation)
        snapshot = session.primary_snapshot
        return bool(snapshot and primary_preserved(session.primary, session.response, snapshot))
