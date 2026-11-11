"""Lawful authority boundary. No credential or challenge implementation lives here."""
from __future__ import annotations

from collections import deque
from enum import Enum
from typing import Callable, Mapping, Protocol


MAX_SESSION_GENERATION = (1 << 64) - 1


def _valid_session_generation(value: object) -> bool:
    return type(value) is int and 1 <= value <= MAX_SESSION_GENERATION


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


class TrustClass(str, Enum):
    """Provenance of a handoff, derived by the library and never caller-asserted.

    Only ATTESTED means a reviewed verifier confirmed genuine authority, and no
    such verifier exists in this repository. Every other class is a statement
    that real authentication has NOT been proven.
    """
    SYNTHETIC_TEST = "SYNTHETIC_TEST"
    REPLAY_FIXTURE = "REPLAY_FIXTURE"
    UNVERIFIED_HARDWARE = "UNVERIFIED_HARDWARE"
    UNVERIFIED_SERVICE = "UNVERIFIED_SERVICE"
    ATTESTED = "ATTESTED"


_CONSTRUCTIBLE_LIVE_TRUST = (TrustClass.SYNTHETIC_TEST, TrustClass.UNVERIFIED_HARDWARE,
                             TrustClass.UNVERIFIED_SERVICE)

# Exact verifier types reviewed in source to attest a handoff. Intentionally
# empty: promotion needs a documented verification contract that does not yet
# exist, and no runtime API may add to this tuple.
_TRUSTED_ATTESTATION_VERIFIERS: tuple[type, ...] = ()


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
                 "transport", "security_context", "capabilities", "authenticated", "_closed", "_claimed",
                 "_trust", "_attested", "_close_callbacks")

    def __init__(self, session_identifier: str, generation: int, origin: SessionOrigin,
                 auth_owner: str, transport: object, security_context: object | None = None,
                 *, authority_type: AuthorityType | None = None, authenticated: bool = False,
                 capabilities: Mapping[str, bool] | None = None,
                 trust: TrustClass | None = None) -> None:
        if (not isinstance(session_identifier, str) or not session_identifier or
                not _valid_session_generation(generation) or
                not isinstance(origin, SessionOrigin) or
                not isinstance(auth_owner, str) or not auth_owner):
            raise AuthenticationError("invalid_session_handoff")
        if transport is None:
            raise AuthenticationError("transport_required")
        if origin is SessionOrigin.AUTHENTICATED_LAB and (
                not authenticated or not isinstance(authority_type, AuthorityType)):
            raise AuthenticationError("authenticated_authority_required")
        if origin is SessionOrigin.SANITIZED_REPLAY and authenticated:
            raise AuthenticationError("synthetic_cannot_authenticate")
        if origin is SessionOrigin.SANITIZED_REPLAY:
            if trust not in (None, TrustClass.REPLAY_FIXTURE):
                raise AuthenticationError("trust_not_assignable")
            trust = TrustClass.REPLAY_FIXTURE
        else:
            if trust is None:
                trust = (TrustClass.UNVERIFIED_SERVICE
                         if authority_type is AuthorityType.LICENSED_MFI_SERVICE
                         else TrustClass.UNVERIFIED_HARDWARE)
            if trust not in _CONSTRUCTIBLE_LIVE_TRUST:
                raise AuthenticationError("trust_not_assignable")
        self._trust = trust
        self._attested = False
        self._close_callbacks: list[Callable[[], None]] = []
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

    @property
    def trust(self) -> TrustClass:
        return TrustClass.ATTESTED if self._attested else self._trust

    def add_close_callback(self, callback: Callable[[], None]) -> None:
        """Run `callback` once when this handoff closes (authority loss).

        A callback added after closure runs immediately. Callback exceptions
        are contained so one dependent cannot block another's revocation.
        """
        if not callable(callback):
            raise AuthenticationError("invalid_close_callback")
        if self._closed:
            self._run_callback(callback)
            return
        if len(self._close_callbacks) >= 16:
            raise AuthenticationError("close_callback_limit")
        self._close_callbacks.append(callback)

    @staticmethod
    def _run_callback(callback: Callable[[], None]) -> None:
        try:
            callback()
        except Exception:
            pass

    def claim(self, generation: int) -> None:
        if not _valid_session_generation(generation):
            raise AuthenticationError("invalid_session_generation")
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
            self._close_resources()
        finally:
            callbacks, self._close_callbacks = self._close_callbacks, []
            for callback in callbacks:
                self._run_callback(callback)

    def _close_resources(self) -> None:
        transport_failed = False
        context_failed = False
        try:
            close = getattr(self.transport, "close", None)
            if callable(close):
                close()
        except Exception:
            # Provider exceptions may contain opaque session/secret details.
            transport_failed = True
        context = self.security_context
        self.security_context = None
        try:
            close_context = getattr(context, "close", None)
            if callable(close_context):
                close_context()
        except Exception:
            # Security-provider exceptions may contain key/session details.
            context_failed = True
        if transport_failed:
            raise AuthenticationError("handoff_transport_close_failed") from None
        if context_failed:
            raise AuthenticationError("handoff_security_context_close_failed") from None

    def __repr__(self) -> str:
        return (f"AuthenticatedSessionHandoff(generation={self.generation}, origin={self.origin.value}, "
                f"trust={self.trust.value}, closed={self._closed})")

    def __reduce__(self) -> None:
        raise AuthenticationError("handoff_not_serializable")

    def __getstate__(self) -> None:
        raise AuthenticationError("handoff_not_serializable")


SessionHandoff = AuthenticatedSessionHandoff  # R6B compatibility


def attest_handoff(handoff: AuthenticatedSessionHandoff, verifier: object) -> None:
    """Promote a live handoff to ATTESTED only through a source-reviewed verifier.

    A caller-supplied verifier, flag, string or capability map cannot promote
    trust. With the empty allowlist this always denies, which is the
    fail-closed state until a verification contract exists.
    """
    if type(verifier) not in _TRUSTED_ATTESTATION_VERIFIERS:
        raise AuthenticationError("attestation_verifier_untrusted")
    if (not isinstance(handoff, AuthenticatedSessionHandoff) or handoff.closed or
            handoff.origin is not SessionOrigin.AUTHENTICATED_LAB or
            handoff.trust not in (TrustClass.UNVERIFIED_HARDWARE, TrustClass.UNVERIFIED_SERVICE)):
        raise AuthenticationError("attestation_not_applicable")
    verify = getattr(verifier, "verify", None)
    try:
        verified = callable(verify) and verify(handoff) is True
    except Exception:
        verified = False
    if not verified:
        raise AuthenticationError("attestation_failed")
    handoff._attested = True


def real_authentication_proven(handoff: AuthenticatedSessionHandoff) -> bool:
    """True only for an open, ATTESTED handoff; synthetic proof never counts."""
    return (isinstance(handoff, AuthenticatedSessionHandoff) and not handoff.closed and
            handoff.trust is TrustClass.ATTESTED)


class SessionLedger:
    """Bounded record of session identifiers already admitted.

    Rejects reuse of an identifier across provider restarts or reconnects. The
    window is bounded, so reuse of an evicted identifier is not detected.
    """

    def __init__(self, capacity: int = 1024) -> None:
        if type(capacity) is not int or not 1 <= capacity <= 65536:
            raise AuthenticationError("invalid_ledger_capacity")
        self._capacity = capacity
        self._order: deque[str] = deque()
        self._seen: set[str] = set()

    def admit(self, session_identifier: str) -> None:
        if not isinstance(session_identifier, str) or not session_identifier:
            raise AuthenticationError("invalid_session_identifier")
        if session_identifier in self._seen:
            raise AuthenticationError("session_identifier_reused")
        self._seen.add(session_identifier)
        self._order.append(session_identifier)
        if len(self._order) > self._capacity:
            self._seen.discard(self._order.popleft())


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
        if not _valid_session_generation(generation):
            raise AuthenticationError("invalid_session_generation")
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
        if not _valid_session_generation(generation):
            raise AuthenticationError("invalid_session_generation")
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
