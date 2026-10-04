"""R5Y symbolic receiver values. MODEL_ONLY / HOST_ONLY / NOT_DEPLOYABLE.

NOT_HONDA_BINARY / NOT_REAL_CARPLAY / NOT_MFI / NO_REAL_JMCS_PATCH.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum


LABELS = frozenset({
    "MODEL_ONLY", "HOST_ONLY", "NOT_DEPLOYABLE", "NOT_HONDA_BINARY",
    "NOT_REAL_CARPLAY", "NOT_MFI", "NO_REAL_JMCS_PATCH",
})
SERIALIZER_LABEL = "SYNTHETIC_MODEL_SERIALIZER"
WIRE_DISCLAIMER = "NOT_CARPLAY_WIRE_FORMAT"


class ReceiverError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ReceiverState(str, Enum):
    IDLE = "IDLE"
    SESSION_CREATED = "SESSION_CREATED"
    SETUP_RECEIVED = "SETUP_RECEIVED"
    PRIMARY_READY = "PRIMARY_READY"
    SECONDARY_NEGOTIATING = "SECONDARY_NEGOTIATING"
    SECONDARY_READY = "SECONDARY_READY"
    STREAMING = "STREAMING"
    TEARDOWN_PENDING = "TEARDOWN_PENDING"
    CLOSED = "CLOSED"
    FAILED = "FAILED"


LEGAL_TRANSITIONS: dict[ReceiverState, frozenset[ReceiverState]] = {
    ReceiverState.IDLE: frozenset({ReceiverState.SESSION_CREATED}),
    ReceiverState.SESSION_CREATED: frozenset({ReceiverState.SETUP_RECEIVED, ReceiverState.TEARDOWN_PENDING, ReceiverState.FAILED}),
    ReceiverState.SETUP_RECEIVED: frozenset({ReceiverState.PRIMARY_READY, ReceiverState.TEARDOWN_PENDING, ReceiverState.FAILED}),
    ReceiverState.PRIMARY_READY: frozenset({ReceiverState.SECONDARY_NEGOTIATING, ReceiverState.STREAMING, ReceiverState.TEARDOWN_PENDING, ReceiverState.FAILED}),
    ReceiverState.SECONDARY_NEGOTIATING: frozenset({ReceiverState.SECONDARY_READY, ReceiverState.PRIMARY_READY, ReceiverState.TEARDOWN_PENDING, ReceiverState.FAILED}),
    ReceiverState.SECONDARY_READY: frozenset({ReceiverState.STREAMING, ReceiverState.PRIMARY_READY, ReceiverState.TEARDOWN_PENDING, ReceiverState.FAILED}),
    ReceiverState.STREAMING: frozenset({ReceiverState.PRIMARY_READY, ReceiverState.TEARDOWN_PENDING, ReceiverState.FAILED}),
    ReceiverState.TEARDOWN_PENDING: frozenset({ReceiverState.CLOSED}),
    ReceiverState.CLOSED: frozenset(),
    ReceiverState.FAILED: frozenset({ReceiverState.TEARDOWN_PENDING}),
}


@dataclass(frozen=True, order=True)
class SessionGeneration:
    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int) or self.value < 1:
            raise ReceiverError("invalid_generation")


@dataclass(frozen=True)
class StreamDescriptor:
    kind: int
    connection_id: str
    port_label: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in (110, 111) or not self.connection_id.startswith("synthetic-"):
            raise ReceiverError("synthetic_descriptor_required")
        if self.port_label is not None and not self.port_label.startswith("mock-port-"):
            raise ReceiverError("mock_port_label_required")


@dataclass(frozen=True)
class SetupRequest:
    session_id: str
    generation: SessionGeneration
    primary: StreamDescriptor
    request_secondary: bool = False
    enable_secondary: bool = False

    def __post_init__(self) -> None:
        if not self.session_id.startswith("session-") or self.primary.kind != 110:
            raise ReceiverError("synthetic_request_required")
        if self.request_secondary and not self.enable_secondary:
            raise ReceiverError("secondary_requires_explicit_flag")


@dataclass(frozen=True)
class SetupResponse:
    streams: tuple[StreamDescriptor, ...]
    evidence: str = "MODEL_ONLY"

    def __post_init__(self) -> None:
        if not self.streams or self.streams[0].kind != 110 or self.evidence != "MODEL_ONLY":
            raise ReceiverError("invalid_model_response")


def serialize_setup(response: SetupResponse) -> bytes:
    """Canonical JSON fixture snapshot; never a protocol or Honda serializer."""
    value = {
        "format": SERIALIZER_LABEL,
        "wire": WIRE_DISCLAIMER,
        "evidence": response.evidence,
        "streams": [
            {"kind": item.kind, "connection_id": item.connection_id, "port_label": item.port_label}
            for item in response.streams
        ],
    }
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


@dataclass(frozen=True)
class PrimaryStreamState:
    session_id: str
    descriptor: StreamDescriptor
    opaque_value: str = "SYNTHETIC:primary"
    lifecycle: str = "READY"
    teardown_owner: str = "PARENT"

    def __post_init__(self) -> None:
        if self.descriptor.kind != 110 or not self.opaque_value.startswith("SYNTHETIC:"):
            raise ReceiverError("synthetic_primary_required")


@dataclass(frozen=True)
class PrimarySnapshot:
    identity: int
    descriptor: StreamDescriptor
    session_id: str
    lifecycle: str
    teardown_owner: str
    original_serialized: bytes


def capture_primary(primary: PrimaryStreamState, response: SetupResponse) -> PrimarySnapshot:
    return PrimarySnapshot(id(primary), primary.descriptor, primary.session_id,
                           primary.lifecycle, primary.teardown_owner, serialize_setup(response))


def primary_preserved(primary: PrimaryStreamState, response: SetupResponse, snapshot: PrimarySnapshot) -> bool:
    return (id(primary) == snapshot.identity and primary.descriptor is snapshot.descriptor
            and response.streams[0] is snapshot.descriptor
            and primary.session_id == snapshot.session_id
            and primary.lifecycle == snapshot.lifecycle
            and primary.teardown_owner == snapshot.teardown_owner
            and serialize_setup(SetupResponse((response.streams[0],))) == snapshot.original_serialized)


@dataclass(frozen=True)
class MediaFrame:
    generation: SessionGeneration
    sequence: int
    symbol: str

    def __post_init__(self) -> None:
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 1:
            raise ReceiverError("invalid_frame_sequence")
        if not self.symbol.startswith("frame-"):
            raise ReceiverError("synthetic_frame_required")


@dataclass(frozen=True)
class DecodedFrame:
    generation: SessionGeneration
    sequence: int
    symbol: str


@dataclass(frozen=True)
class DisplayFrame:
    generation: SessionGeneration
    sequence: int
    symbol: str


@dataclass(frozen=True)
class CleanupResult:
    performed: bool
    generation: SessionGeneration
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResourceSnapshot:
    sessions: int
    secondary_streams: int
    listeners: int
    security_contexts: int
    decoders: int
    display_sinks: int
    pending_transactions: int
    unresolved_bundles: int = 0

    @property
    def secondary_total(self) -> int:
        return sum((self.secondary_streams, self.listeners, self.security_contexts,
                    self.decoders, self.display_sinks, self.pending_transactions,
                    self.unresolved_bundles))


@dataclass(frozen=True)
class ModelEvent:
    index: int
    kind: str
    generation: int
    detail: str = ""


@dataclass
class ReceiverSession:
    session_id: str
    generation: SessionGeneration
    primary: PrimaryStreamState
    response: SetupResponse
    state: ReceiverState = ReceiverState.IDLE
    secondary: SecondaryStreamState | None = None
    primary_snapshot: PrimarySnapshot | None = None
    pending_transaction: bool = False
    last_secondary_error: str | None = None

    def transition(self, target: ReceiverState) -> None:
        if target not in LEGAL_TRANSITIONS[self.state]:
            raise ReceiverError("illegal_state_transition")
        self.state = target


@dataclass
class SecondaryStreamState:
    generation: SessionGeneration
    descriptor: StreamDescriptor
    last_sequence: int = 0
    active: bool = True
