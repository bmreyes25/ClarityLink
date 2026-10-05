"""Honda target contracts. Static evidence does not yet supply a live handoff.

These objects deliberately contain no certificate, signature, or key material.
They cannot open a Honda device or start a receiver session.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .authentication import AuthenticationError, SessionHandoff
from .session_transport import ControlRequest, ControlResponse, TransportError


class HondaSubstrateError(RuntimeError):
    def __init__(self, code: str = "EVIDENCE_REQUIRED") -> None:
        self.code = code
        super().__init__(code)


@dataclass(eq=False, repr=False)
class HondaOpaqueContext:
    """Generation-scoped ownership token for a future factory API binding.

    The handle is intentionally opaque and is never serialized or logged.
    No Honda handle constructor is available until its ABI is established.
    """

    generation: int
    handle: object = field(repr=False)
    closed: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.generation < 1 or self.handle is None:
            raise HondaSubstrateError("invalid_opaque_context")

    def require(self, generation: int) -> object:
        if self.closed or generation != self.generation:
            raise HondaSubstrateError("stale_or_closed_context")
        return self.handle

    def close(self) -> None:
        self.closed = True
        self.handle = None

    def __getstate__(self) -> None:
        raise HondaSubstrateError("opaque_context_not_serializable")

    def __reduce__(self) -> None:
        raise HondaSubstrateError("opaque_context_not_serializable")


class HondaAuthenticationProvider:
    """Future factory-auth consumer; no independently callable API is proven."""

    def initialize(self) -> None:
        raise AuthenticationError("EVIDENCE_REQUIRED_HONDA_AUTH_API")

    def authenticate(self) -> SessionHandoff:
        raise AuthenticationError("EVIDENCE_REQUIRED_HONDA_SESSION_HANDOFF")

    def session_ready(self) -> bool:
        return False

    def session_identifier(self) -> str:
        raise AuthenticationError("EVIDENCE_REQUIRED_HONDA_SESSION_HANDOFF")

    def transport_handle(self) -> object:
        raise AuthenticationError("EVIDENCE_REQUIRED_HONDA_SESSION_HANDOFF")

    def security_context(self) -> object | None:
        raise AuthenticationError("EVIDENCE_REQUIRED_HONDA_SESSION_HANDOFF")

    def close(self) -> None:
        pass


class HondaIap2Transport:
    """iAP2 is in jmcs; an external transport ABI remains unproven."""

    def open(self) -> None:
        raise HondaSubstrateError("EVIDENCE_REQUIRED_HONDA_IAP2_HANDOFF")

    def close(self) -> None:
        pass


class HondaCarPlaySessionTransport:
    """No factory authenticated control-channel handoff has been identified."""

    @property
    def authenticated(self) -> bool:
        return False

    @property
    def session_identifier(self) -> str:
        raise TransportError("EVIDENCE_REQUIRED_HONDA_SESSION_HANDOFF")

    @property
    def generation(self) -> int:
        raise TransportError("EVIDENCE_REQUIRED_HONDA_SESSION_HANDOFF")

    def read_request(self, timeout: float) -> ControlRequest:
        raise TransportError("EVIDENCE_REQUIRED_HONDA_CONTROL_CHANNEL")

    def write_response(self, response: ControlResponse) -> None:
        raise TransportError("EVIDENCE_REQUIRED_HONDA_CONTROL_CHANNEL")

    def close(self) -> None:
        pass
