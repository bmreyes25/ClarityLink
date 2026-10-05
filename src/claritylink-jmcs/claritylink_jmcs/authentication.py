"""Authentication boundary for an already legitimate accessory session.

No provider here signs a challenge, reads a certificate, or bypasses MFi.
A live handoff must come from an independently authenticated host service.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol


class AuthenticationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SessionOrigin(str, Enum):
    AUTHENTICATED_LAB = "AUTHENTICATED_LAB"
    SANITIZED_REPLAY = "SANITIZED_REPLAY"


@dataclass(frozen=True)
class SessionHandoff:
    """Opaque control transport plus evidence of its authentication owner."""

    session_identifier: str
    generation: int
    origin: SessionOrigin
    auth_owner: str
    transport: object
    security_context: object | None = None

    def __post_init__(self) -> None:
        if not self.session_identifier or self.generation < 1 or not self.auth_owner:
            raise AuthenticationError("invalid_session_handoff")
        if self.transport is None:
            raise AuthenticationError("transport_required")


class AuthenticationProvider(Protocol):
    def initialize(self) -> None: ...
    def authenticate(self) -> SessionHandoff: ...
    def session_ready(self) -> bool: ...
    def session_identifier(self) -> str: ...
    def transport_handle(self) -> object: ...
    def security_context(self) -> object | None: ...
    def close(self) -> None: ...


class LabAuthenticationProvider:
    """Accepts a handoff only from a configured legitimate host authority.

    The factory is an integration point, not an authentication implementation.
    No default factory exists. In particular, recovered identities are excluded.
    """

    def __init__(self, factory: Callable[[], SessionHandoff] | None = None) -> None:
        self._factory = factory
        self._handoff: SessionHandoff | None = None
        self._initialized = False
        self._closed = False

    def initialize(self) -> None:
        if self._closed:
            raise AuthenticationError("provider_closed")
        self._initialized = True

    def authenticate(self) -> SessionHandoff:
        if not self._initialized or self._closed:
            raise AuthenticationError("provider_not_initialized")
        if self._handoff is not None:
            raise AuthenticationError("session_already_active")
        if self._factory is None:
            raise AuthenticationError("lawful_auth_substrate_required")
        handoff = self._factory()
        if not isinstance(handoff, SessionHandoff) or handoff.origin is not SessionOrigin.AUTHENTICATED_LAB:
            raise AuthenticationError("unverified_live_handoff")
        self._handoff = handoff
        return handoff

    def session_ready(self) -> bool:
        return self._handoff is not None and not self._closed

    def _require(self) -> SessionHandoff:
        if not self.session_ready():
            raise AuthenticationError("session_not_ready")
        assert self._handoff is not None
        return self._handoff

    def session_identifier(self) -> str:
        return self._require().session_identifier

    def transport_handle(self) -> object:
        return self._require().transport

    def security_context(self) -> object | None:
        return self._require().security_context

    def close(self) -> None:
        self._closed = True
        self._handoff = None


class ReplayAuthenticationProvider(LabAuthenticationProvider):
    """Sanitized fixture path; never counts as real iPhone authentication."""

    def __init__(self, handoff: SessionHandoff) -> None:
        if handoff.origin is not SessionOrigin.SANITIZED_REPLAY:
            raise AuthenticationError("replay_origin_required")
        super().__init__(lambda: handoff)

    def authenticate(self) -> SessionHandoff:
        if not self._initialized or self._closed:
            raise AuthenticationError("provider_not_initialized")
        if self._handoff is not None:
            raise AuthenticationError("session_already_active")
        assert self._factory is not None
        self._handoff = self._factory()
        return self._handoff


class HondaAuthenticationProviderStub:
    def initialize(self) -> None:
        raise AuthenticationError("EVIDENCE_REQUIRED_HONDA_AUTH")

    def authenticate(self) -> SessionHandoff:
        raise AuthenticationError("EVIDENCE_REQUIRED_HONDA_AUTH")

    def session_ready(self) -> bool:
        return False

    def session_identifier(self) -> str:
        raise AuthenticationError("EVIDENCE_REQUIRED_HONDA_AUTH")

    def transport_handle(self) -> object:
        raise AuthenticationError("EVIDENCE_REQUIRED_HONDA_AUTH")

    def security_context(self) -> object | None:
        raise AuthenticationError("EVIDENCE_REQUIRED_HONDA_AUTH")

    def close(self) -> None:
        return None
