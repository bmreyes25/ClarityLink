"""Security provider boundary. No authentication bypass or unknown key path."""
from __future__ import annotations

from typing import Protocol

MAX_SECURITY_FRAME = 8 * 1024 * 1024
MAX_SECURITY_GENERATION = (1 << 64) - 1


def _valid_positive_u64(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_SECURITY_GENERATION


class SecurityError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ScreenSecurityProvider(Protocol):
    def open(self, generation: int, stream_connection_id: int) -> None: ...
    def unprotect(self, generation: int, body: bytes, header: bytes = b"") -> bytes: ...
    def close(self) -> None: ...


class ClearLabSecurity:
    """Only for locally generated clear H.264 fixtures; never real CarPlay."""

    def __init__(self) -> None:
        self.generation: int | None = None

    def open(self, generation: int, stream_connection_id: int) -> None:
        if not _valid_positive_u64(generation) or not _valid_positive_u64(stream_connection_id):
            raise SecurityError("invalid_security_open")
        self.generation = generation

    def unprotect(self, generation: int, body: bytes, header: bytes = b"") -> bytes:
        if not _valid_positive_u64(generation) or self.generation != generation:
            raise SecurityError("stale_security_context")
        if not isinstance(body, bytes) or not isinstance(header, bytes):
            raise SecurityError("invalid_clear_fixture_frame")
        return body

    def close(self) -> None:
        self.generation = None


class EvidenceRequiredSecurity:
    """Fail closed for encrypted Type111 pending actual protocol evidence."""

    def open(self, generation: int, stream_connection_id: int) -> None:
        raise SecurityError("type111_security_evidence_required")

    def unprotect(self, generation: int, body: bytes, header: bytes = b"") -> bytes:
        raise SecurityError("type111_security_evidence_required")

    def close(self) -> None:
        return None


class EvidenceRequiredPrimarySecurity:
    """Fail closed on Type110 media when only a synthetic listener is known."""

    def open(self, generation: int, stream_connection_id: int) -> None:
        return None

    def unprotect(self, generation: int, body: bytes, header: bytes = b"") -> bytes:
        raise SecurityError("type110_security_evidence_required")

    def close(self) -> None:
        return None


class SecurityProfile(str):
    CLEAR_GENERATED_LAB = "CLEAR_GENERATED_LAB"
    LEGACY_AES_SCREEN = "LEGACY_AES_SCREEN"
    MODERN_CHACHA_SCREEN = "MODERN_CHACHA_SCREEN"


class SessionSecurityContext:
    """Explicit provenance and generation boundary; no secret storage in logs."""

    def __init__(self, profile: str, provenance: str, generation: int, stream_connection_id: int) -> None:
        if profile not in (SecurityProfile.LEGACY_AES_SCREEN, SecurityProfile.MODERN_CHACHA_SCREEN):
            raise SecurityError("unsupported_security_profile")
        if not provenance or not _valid_positive_u64(generation) or not _valid_positive_u64(stream_connection_id):
            raise SecurityError("invalid_security_context")
        self.profile = profile
        self.provenance = provenance
        self.generation = generation
        self.stream_connection_id = stream_connection_id
        self.closed = False

    def unprotect(self, generation: int, body: bytes, header: bytes = b"") -> bytes:
        if self.closed or generation != self.generation:
            raise SecurityError("stale_security_context")
        raise SecurityError("type111_security_evidence_required")

    def close(self) -> None:
        self.closed = True


class ModernChaChaScreenSecurity:
    """Current PlayPort host profile; requires an established lawful session key.

    The provider never obtains MFi credentials. One instance owns one stream
    generation and one nonce counter, which advances only on valid AEAD tags.
    """

    def __init__(self, key: bytes, *, provenance: str) -> None:
        if not isinstance(key, bytes) or len(key) != 32 or not isinstance(provenance, str) or not provenance.strip():
            raise SecurityError("invalid_session_key_context")
        self._key = bytearray(key)
        self.provenance = provenance
        self.generation: int | None = None
        self.stream_connection_id: int | None = None
        self.counter = 0
        self._closed = False

    def open(self, generation: int, stream_connection_id: int) -> None:
        if (self._closed or self.generation is not None
                or not _valid_positive_u64(generation)
                or not _valid_positive_u64(stream_connection_id)):
            raise SecurityError("invalid_security_open")
        self.generation = generation
        self.stream_connection_id = stream_connection_id
        self.counter = 0

    def unprotect(self, generation: int, body: bytes, header: bytes = b"") -> bytes:
        if (not _valid_positive_u64(generation) or self.generation != generation
                or self.stream_connection_id is None):
            raise SecurityError("stale_security_context")
        if (not isinstance(header, bytes) or not isinstance(body, bytes)
                or len(header) != 128 or not 16 <= len(body) <= MAX_SECURITY_FRAME
                or self.counter >= 2**64):
            raise SecurityError("invalid_protected_frame")
        try:
            from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
            nonce = b"\x00" * 4 + self.counter.to_bytes(8, "little")
            clear = ChaCha20Poly1305(bytes(self._key)).decrypt(nonce, body, header)
        except ImportError as exc:
            raise SecurityError("chacha_backend_unavailable") from exc
        except Exception as exc:
            raise SecurityError("screen_authentication_failed") from exc
        self.counter += 1
        return clear

    def close(self) -> None:
        for i in range(len(self._key)):
            self._key[i] = 0
        self.generation = None
        self.stream_connection_id = None
        self.counter = 0
        self._closed = True


_GRANTABLE_PROFILES = (SecurityProfile.LEGACY_AES_SCREEN, SecurityProfile.MODERN_CHACHA_SCREEN)


class Type111SecurityGrant:
    """Parent-owned, single-use security material for exactly one Type111 stream.

    A provider attaches this to its handoff. It binds the profile to one parent
    session, generation and stream connection ID. The grant never selects a
    decoder from a peer-supplied string: only profiles listed in
    `_PROFILE_PROVIDERS` can be built, and the key is zeroed once released.
    """
    __slots__ = ("profile", "provenance", "session_identifier", "generation",
                 "stream_connection_id", "synthetic", "_key", "_released", "_closed")

    def __init__(self, profile: str, *, provenance: str, session_identifier: str,
                 generation: int, stream_connection_id: int, key: bytes,
                 synthetic: bool) -> None:
        if (type(profile) is not str or profile not in _GRANTABLE_PROFILES or
                not isinstance(provenance, str) or not provenance.strip() or
                not isinstance(session_identifier, str) or not session_identifier or
                not _valid_positive_u64(generation) or
                not _valid_positive_u64(stream_connection_id) or
                not isinstance(key, bytes) or not 16 <= len(key) <= 64 or
                type(synthetic) is not bool):
            raise SecurityError("invalid_security_grant")
        self.profile = profile
        self.provenance = provenance
        self.session_identifier = session_identifier
        self.generation = generation
        self.stream_connection_id = stream_connection_id
        self.synthetic = synthetic
        self._key = bytearray(key)
        self._released = False
        self._closed = False

    @property
    def usable(self) -> bool:
        return not self._released and not self._closed

    def release_key(self) -> bytes:
        if not self.usable:
            raise SecurityError("security_grant_consumed")
        self._released = True
        key = bytes(self._key)
        self._zero()
        return key

    def _zero(self) -> None:
        for i in range(len(self._key)):
            self._key[i] = 0

    def close(self) -> None:
        self._zero()
        self._closed = True

    def __repr__(self) -> str:
        return f"Type111SecurityGrant(profile={self.profile}, generation={self.generation}, usable={self.usable})"

    def __reduce__(self) -> None:
        raise SecurityError("security_grant_not_serializable")


_PROFILE_PROVIDERS = {SecurityProfile.MODERN_CHACHA_SCREEN: ModernChaChaScreenSecurity}


class _GrantBoundSecurity:
    """ScreenSecurityProvider that builds its inner provider only after full binding."""

    def __init__(self, grant: Type111SecurityGrant, handoff: object,
                 allow_test_profiles: bool) -> None:
        self._grant = grant
        self._handoff = handoff
        self._allow_test_profiles = allow_test_profiles
        self._inner: ModernChaChaScreenSecurity | None = None
        self._opened = False

    def open(self, generation: int, stream_connection_id: int) -> None:
        grant, handoff = self._grant, self._handoff
        if self._opened or not grant.usable or getattr(handoff, "closed", True):
            raise SecurityError("security_grant_unavailable")
        if (not _valid_positive_u64(generation) or not _valid_positive_u64(stream_connection_id)
                or generation != grant.generation or generation != getattr(handoff, "generation", None)
                or grant.session_identifier != getattr(handoff, "session_identifier", None)
                or stream_connection_id != grant.stream_connection_id):
            raise SecurityError("security_grant_binding_mismatch")
        provider = _PROFILE_PROVIDERS.get(grant.profile)
        if provider is None:
            raise SecurityError("security_profile_unimplemented")
        from .authentication import TrustClass
        if grant.synthetic:
            if not self._allow_test_profiles:
                raise SecurityError("synthetic_security_not_enabled")
        elif getattr(handoff, "trust", None) is not TrustClass.ATTESTED:
            raise SecurityError("security_authority_unattested")
        self._opened = True
        inner = provider(grant.release_key(), provenance=grant.provenance)
        inner.open(generation, stream_connection_id)
        self._inner = inner

    def unprotect(self, generation: int, body: bytes, header: bytes = b"") -> bytes:
        if self._inner is None or getattr(self._handoff, "closed", True):
            raise SecurityError("stale_security_context")
        return self._inner.unprotect(generation, body, header)

    def close(self) -> None:
        inner, self._inner = self._inner, None
        try:
            if inner is not None:
                inner.close()
        finally:
            self._grant.close()


class HandoffSecurityFactory:
    """Receiver `security_factory` that yields the parent grant's provider once."""

    def __init__(self, handoff: object, *, allow_test_profiles: bool = False) -> None:
        grant = getattr(handoff, "security_context", None)
        if not isinstance(grant, Type111SecurityGrant):
            raise SecurityError("security_grant_required")
        self._grant = grant
        self._handoff = handoff
        self._allow_test_profiles = allow_test_profiles
        self._issued = False

    def __call__(self) -> ScreenSecurityProvider:
        if self._issued:
            raise SecurityError("security_grant_consumed")
        self._issued = True
        return _GrantBoundSecurity(self._grant, self._handoff, self._allow_test_profiles)
