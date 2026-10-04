"""MODEL_ONLY / NOT_DEPLOYABLE / NOT_HONDA_BINARY / NOT_REAL_CARPLAY.

NOT_MFI / NO_REAL_JMCS_PATCH. In-memory architecture exercise only.
There are no network, file, media, authentication, or device operations here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePath


MODEL_LABELS = frozenset({
    "MODEL_ONLY", "NOT_DEPLOYABLE", "NOT_HONDA_BINARY",
    "NOT_REAL_CARPLAY", "NOT_MFI", "NO_REAL_JMCS_PATCH",
})


class PatchError(ValueError):
    """A synthetic input or model transition violates the sandbox contract."""


class PatchDecision(str, Enum):
    STOCK_ONLY = "STOCK_ONLY"
    SYNTHETIC_TYPE111 = "SYNTHETIC_TYPE111"


@dataclass(frozen=True)
class StreamDescriptor:
    stream_type: int
    connection_id: str
    data_port: int | None = None
    evidence: str = "MODEL_ONLY"

    def __post_init__(self) -> None:
        if self.evidence != "MODEL_ONLY" or not self.connection_id.startswith("SYNTHETIC-"):
            raise PatchError("synthetic stream descriptors only")
        if self.stream_type not in (110, 111):
            raise PatchError("model supports only screen types 110 and 111")


@dataclass(frozen=True)
class SetupRequest:
    session_id: str
    generation: int
    primary: StreamDescriptor
    source: str = "SYNTHETIC"

    def __post_init__(self) -> None:
        if self.source != "SYNTHETIC" or not self.session_id.startswith("SYNTHETIC-"):
            raise PatchError("Honda paths and real traffic are excluded")
        if self.generation < 1 or self.primary.stream_type != 110:
            raise PatchError("request requires a synthetic Type110 and positive generation")


@dataclass(frozen=True)
class SetupResponse:
    streams: tuple[StreamDescriptor, ...]
    evidence: str = "MODEL_ONLY"


@dataclass(frozen=True)
class Type110PrimaryScreen:
    descriptor: StreamDescriptor
    opaque_stock_model: bytes

    def __post_init__(self) -> None:
        if self.descriptor.stream_type != 110 or not self.opaque_stock_model.startswith(b"SYNTHETIC:"):
            raise PatchError("Type110 model must use invented data")


@dataclass
class Type111Listener:
    generation: int
    port: int
    transport: str = "MOCK_ONLY"
    open: bool = True

    def __post_init__(self) -> None:
        if self.transport != "MOCK_ONLY":
            raise PatchError("real sockets and listeners are excluded")

    def close(self) -> None:
        self.open = False


@dataclass
class MockSecurityContext:
    generation: int
    marker: str = "MOCK_SECURITY_NO_KEYS"
    active: bool = True

    def clear(self) -> None:
        self.active = False


@dataclass
class MockDecoder:
    generation: int
    active: bool = True

    def decode(self, frame: str) -> str:
        if not self.active or not frame.startswith("MOCK_FRAME:"):
            raise PatchError("only invented frames can be decoded")
        return "MOCK_DECODED:" + frame.removeprefix("MOCK_FRAME:")

    def close(self) -> None:
        self.active = False


@dataclass
class MockDisplaySink:
    generation: int
    displayed: str | None = None
    clear_reason: str | None = None

    def show(self, frame: str, generation: int) -> bool:
        if generation != self.generation:
            self.clear("stale")
            return False
        if not frame.startswith("MOCK_DECODED:"):
            raise PatchError("mock decoded frame required")
        self.displayed = frame
        self.clear_reason = None
        return True

    def clear(self, reason: str) -> None:
        self.displayed = None
        self.clear_reason = reason


@dataclass
class Type111SecondaryScreen:
    descriptor: StreamDescriptor
    listener: Type111Listener
    security: MockSecurityContext
    decoder: MockDecoder
    display: MockDisplaySink
    generation: int
    active: bool = True


@dataclass
class ReceiverSession:
    session_id: str
    generation: int
    primary: Type110PrimaryScreen
    response: SetupResponse
    decision: PatchDecision
    secondary: Type111SecondaryScreen | None = None
    closed: bool = False


class TeardownManager:
    def teardown(self, session: ReceiverSession, generation: int) -> bool:
        if generation != session.generation or session.closed:
            return False
        secondary = session.secondary
        if secondary is not None:
            secondary.display.clear("teardown")
            secondary.decoder.close()
            secondary.security.clear()
            secondary.listener.close()
            secondary.active = False
        session.closed = True
        return True


def validate_model_artifact_name(name: str) -> PurePath:
    """Validate a *name* only; never opens or creates any artifact."""
    path = PurePath(name)
    forbidden = {".bin", ".patch", ".ips", ".bspatch", ".so", ".apk", ".img"}
    if path.is_absolute() or len(path.parts) != 1 or path.suffix.lower() in forbidden:
        raise PatchError("deployable artifact names and paths are excluded")
    if any(token in path.name.lower() for token in ("jmcs", "honda", "deploy", "patch")):
        raise PatchError("artifact name resembles deployment material")
    return path


@dataclass
class TheoreticalPatchSandbox:
    """A deterministic transaction model; no real listener or byte serializer."""

    teardown_manager: TeardownManager = field(default_factory=TeardownManager)

    def receive_setup(
        self, request: SetupRequest, primary: Type110PrimaryScreen,
        *, enable_type111: bool = False, request_type111: bool = False,
        fail_at: str | None = None,
    ) -> ReceiverSession:
        if primary.descriptor != request.primary:
            raise PatchError("Type110 request and primary model differ")
        if request_type111 and not enable_type111:
            raise PatchError("Type111 requires explicit model enable flag")
        stock_response = SetupResponse((primary.descriptor,))
        session = ReceiverSession(
            request.session_id, request.generation, primary, stock_response,
            PatchDecision.STOCK_ONLY,
        )
        if not request_type111:
            return session
        try:
            if fail_at == "listener":
                raise PatchError("injected mock listener failure")
            # This integer is a label, not a bound or reachable TCP port.
            port = 40000 + request.generation
            if port > 49999:
                raise PatchError("synthetic generation exceeds port label range")
            listener = Type111Listener(request.generation, port)
            security = MockSecurityContext(request.generation)
            decoder = MockDecoder(request.generation)
            display = MockDisplaySink(request.generation)
            descriptor = StreamDescriptor(111, f"SYNTHETIC-111-{request.generation}", port)
            session.secondary = Type111SecondaryScreen(
                descriptor, listener, security, decoder, display, request.generation,
            )
            if fail_at == "augmentation":
                raise PatchError("injected mock augmentation failure")
            session.response = SetupResponse(stock_response.streams + (descriptor,))
            session.decision = PatchDecision.SYNTHETIC_TYPE111
        except PatchError:
            # Failure is local to the optional child. Stock data is retained.
            if session.secondary is not None:
                session.secondary.display.clear("failure")
                session.secondary.decoder.close()
                session.secondary.security.clear()
                session.secondary.listener.close()
                session.secondary.active = False
            session.secondary = None
            session.response = stock_response
            session.decision = PatchDecision.STOCK_ONLY
        return session

    def deliver_mock_frame(self, session: ReceiverSession, generation: int, frame: str) -> bool:
        secondary = session.secondary
        if session.closed or secondary is None or not secondary.active:
            return False
        if generation != session.generation:
            secondary.display.clear("stale")
            return False
        return secondary.display.show(secondary.decoder.decode(frame), generation)

    def lose_source(self, session: ReceiverSession) -> None:
        if session.secondary is not None:
            session.secondary.display.clear("lost")
