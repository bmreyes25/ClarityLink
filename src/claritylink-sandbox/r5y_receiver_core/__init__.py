"""R5Y stable host-only symbolic receiver-core API.

MODEL_ONLY / HOST_ONLY / NOT_DEPLOYABLE / NOT_HONDA_BINARY /
NOT_REAL_CARPLAY / NOT_MFI / NO_REAL_JMCS_PATCH.
"""

from .adapters import (
    DecoderProvider, DisplayProvider, DisplaySink, LifecycleAdapter,
    ListenerHandle, ListenerProvider, MockDecoder, MockDecoderProvider,
    MockDisplay1Sink, MockDisplayProvider, MockListenerProvider,
    MockSecurityProvider, ReceiverEntryAdapter, SecurityContext, SecurityProvider,
    SessionIdentityAdapter, SetupRequestAdapter, SetupResponseAdapter,
)
from .core import CleanupManager, FailurePoint, FaultInjector, ReceiverCore, SetupTransaction
from .model import (
    LABELS, SERIALIZER_LABEL, WIRE_DISCLAIMER, CleanupResult, DecodedFrame,
    DisplayFrame, LEGAL_TRANSITIONS, MediaFrame, ModelEvent, PrimarySnapshot,
    PrimaryStreamState, ReceiverError, ReceiverSession, ReceiverState,
    ResourceSnapshot, SecondaryStreamState, SessionGeneration, SetupRequest,
    SetupResponse, StreamDescriptor, capture_primary, primary_preserved,
    serialize_setup,
)
from .replay import replay_document

__all__ = [name for name in globals() if not name.startswith("_")]
