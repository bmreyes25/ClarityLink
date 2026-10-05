"""Lawful authority boundary. No credential or challenge implementation lives here."""
from __future__ import annotations

from enum import Enum
from typing import Mapping, Protocol


class AuthenticationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SessionOrigin(str, Enum):
    AUTHENTICATED_LAB = "AUTHENTICATED_LAB"
    SANITIZED_REPLAY = "SYNTHETIC"


class AuthorityType(str, Enum):
    GENUINE_MFI_COPROCESSOR = "USER_OWNED_GENUINE_MFI_COPROCESSOR"
    LICENSED_MFI_SERVICE = "USER_AUTHORIZED_LICENSED_MFI_SERVICE"
    GENUINE_HARDWARE = "USER_OWNED_HARDWARE_WITH_GENUINE_MFI_AUTHORITY"
    APPLE_COMPLIANT = "ANOTHER_EXPLICITLY_AUTHORIZED_APPLE_COMPLIANT_ACCESSORY_AUTHORITY"


class AuthorizedAuthenticationAuthority(Protocol):
    """Reviewed adapter owns iAP2, MFi and the control channel.

    Satisfying this Python protocol alone is not proof of authorization.
    """
    @property
    def identity(self) -> str: ...
    @property
    def authority_type(self) -> AuthorityType: ...
    @property
    def explicitly_authorized(self) -> bool: ...
    def open(self, generation: int) -> AuthenticatedSessionHandoff: ...
    def close(self) -> None: ...


class AuthenticatedSessionHandoff:
    """Single-use, non-serializable ownership of one authenticated channel."""
    __slots__ = ("session_identifier", "generation", "origin", "auth_owner", "authority_type",
                 "transport", "security_context", "capabilities", "authenticated", "_closed", "_claimed")

    def __init__(self, session_identifier: str, generation: int, origin: SessionOrigin,
                 auth_owner: str, transport: object, security_context: object | None = None,
                 *, authority_type: AuthorityType | None = None, authenticated: bool = False,
                 capabilities: Mapping[str, bool] | None = None) -> None:
        if not session_identifier or not isinstance(generation, int) or generation < 1 or not auth_owner:
            raise AuthenticationError("invalid_session_handoff")
        if transport is None:
            raise AuthenticationError("transport_required")
        if origin is SessionOrigin.AUTHENTICATED_LAB and (not authenticated or authority_type is None):
            raise AuthenticationError("authenticated_authority_required")
        if origin is SessionOrigin.SANITIZED_REPLAY and authenticated:
            raise AuthenticationError("synthetic_cannot_authenticate")
        self.session_identifier = session_identifier
        self.generation = generation
        self.origin = origin
        self.auth_owner = auth_owner
        self.authority_type = authority_type
        self.transport = transport
        self.security_context = security_context
        self.capabilities = dict(capabilities or {})
        self.authenticated = authenticated
        self._closed = False
        self._claimed = False

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def claimed(self) -> bool:
        return self._claimed

    def claim(self, generation: int) -> None:
        if self._closed or self._claimed:
            raise AuthenticationError("handoff_unavailable")
        if self.generation != generation:
            raise AuthenticationError("stale_handoff_generation")
        self._claimed = True

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            close = getattr(self.transport, "close", None)
            if callable(close):
                close()
        except Exception:
            # Vendor exceptions may contain opaque session/secret details.
            raise AuthenticationError("handoff_transport_close_failed") from None
        finally:
            context = self.security_context
            self.security_context = None
            close_context = getattr(context, "close", None)
            if callable(close_context):
                close_context()

    def __repr__(self) -> str:
        return f"AuthenticatedSessionHandoff(generation={self.generation}, origin={self.origin.value}, closed={self._closed})"

    def __reduce__(self) -> None:
        raise AuthenticationError("handoff_not_serializable")

    def __getstate__(self) -> None:
        raise AuthenticationError("handoff_not_serializable")


SessionHandoff = AuthenticatedSessionHandoff  # R6B compatibility


class AuthenticationProvider(Protocol):
    def initialize(self) -> None: ...
    def authenticate(self, generation: int = 1) -> AuthenticatedSessionHandoff: ...
    def session_ready(self) -> bool: ...
    def session_identifier(self) -> str: ...
    def transport_handle(self) -> object: ...
    def security_context(self) -> object | None: ...
    def close(self) -> None: ...


class LabAuthenticationProvider:
    """Wrap a reviewed authority adapter; no default software MFi authority."""
    def __init__(self, *, authority: AuthorizedAuthenticationAuthority | None = None) -> None:
        self._authority = authority
        self._handoff: AuthenticatedSessionHandoff | None = None
        self._initialized = False
        self._closed = False

    def initialize(self) -> None:
        if self._closed:
            raise AuthenticationError("provider_closed")
        self._initialized = True

    def authenticate(self, generation: int = 1) -> AuthenticatedSessionHandoff:
        if not self._initialized or self._closed:
            raise AuthenticationError("provider_not_initialized")
        if self._handoff is not None:
            raise AuthenticationError("session_already_active")
        authority = self._authority
        if authority is None:
            raise AuthenticationError("lawful_auth_substrate_required")
        if not authority.explicitly_authorized or not authority.identity or not isinstance(authority.authority_type, AuthorityType):
            raise AuthenticationError("authority_not_authorized")
        try:
            handoff = authority.open(generation)
        except AuthenticationError:
            raise
        except Exception:
            # Do not expose provider exception text, which may include secrets.
            raise AuthenticationError("authority_open_failed") from None
        if (not isinstance(handoff, AuthenticatedSessionHandoff) or
                handoff.origin is not SessionOrigin.AUTHENTICATED_LAB or
                not handoff.authenticated or handoff.closed or handoff.claimed or
                handoff.generation != generation or handoff.auth_owner != authority.identity or
                handoff.authority_type is not authority.authority_type):
            if isinstance(handoff, AuthenticatedSessionHandoff) and not handoff.claimed:
                handoff.close()
            raise AuthenticationError("unverified_live_handoff")
        self._handoff = handoff
        return handoff

    def session_ready(self) -> bool:
        return self._handoff is not None and not self._handoff.closed and not self._closed

    def _require(self) -> AuthenticatedSessionHandoff:
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
        if self._closed:
            return
        self._closed = True
        failure = False
        if self._handoff is not None:
            try:
                self._handoff.close()
            except Exception:
                failure = True
            finally:
                self._handoff = None
        if self._authority is not None:
            try:
                self._authority.close()
            except Exception:
                # Provider close is best-effort and must not leak vendor details.
                failure = True
        if failure:
            raise AuthenticationError("provider_close_failed") from None


class ReplayAuthenticationProvider(LabAuthenticationProvider):
    """Fixture provider; its handoff is always SYNTHETIC."""
    def __init__(self, handoff: AuthenticatedSessionHandoff) -> None:
        if handoff.origin is not SessionOrigin.SANITIZED_REPLAY:
            raise AuthenticationError("replay_origin_required")
        super().__init__()
        self._replay = handoff

    def authenticate(self, generation: int = 1) -> AuthenticatedSessionHandoff:
        if not self._initialized or self._closed:
            raise AuthenticationError("provider_not_initialized")
        if self._handoff is not None or self._replay.generation != generation or self._replay.closed or self._replay.claimed:
            raise AuthenticationError("replay_unavailable")
        self._handoff = self._replay
        return self._replay


class HondaAuthenticationProviderStub:
    def initialize(self) -> None:
        raise AuthenticationError("EVIDENCE_REQUIRED_HONDA_AUTH")
    def authenticate(self) -> AuthenticatedSessionHandoff:
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
