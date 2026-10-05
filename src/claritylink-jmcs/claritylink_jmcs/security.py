"""Security provider boundary. No authentication bypass or unknown key path."""
from __future__ import annotations

from typing import Protocol


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
        if stream_connection_id < 1:
            raise SecurityError("invalid_stream_connection_id")
        self.generation = generation

    def unprotect(self, generation: int, body: bytes, header: bytes = b"") -> bytes:
        if self.generation != generation:
            raise SecurityError("stale_security_context")
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


class SecurityProfile(str):
    CLEAR_GENERATED_LAB = "CLEAR_GENERATED_LAB"
    LEGACY_AES_SCREEN = "LEGACY_AES_SCREEN"
    MODERN_CHACHA_SCREEN = "MODERN_CHACHA_SCREEN"


class SessionSecurityContext:
    """Explicit provenance and generation boundary; no secret storage in logs."""

    def __init__(self, profile: str, provenance: str, generation: int, stream_connection_id: int) -> None:
        if profile not in (SecurityProfile.LEGACY_AES_SCREEN, SecurityProfile.MODERN_CHACHA_SCREEN):
            raise SecurityError("unsupported_security_profile")
        if not provenance or generation < 1 or stream_connection_id < 1:
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
        if len(key) != 32 or not provenance:
            raise SecurityError("invalid_session_key_context")
        self._key = bytearray(key)
        self.provenance = provenance
        self.generation: int | None = None
        self.stream_connection_id: int | None = None
        self.counter = 0

    def open(self, generation: int, stream_connection_id: int) -> None:
        if self.generation is not None or generation < 1 or stream_connection_id < 1:
            raise SecurityError("invalid_security_open")
        self.generation = generation
        self.stream_connection_id = stream_connection_id
        self.counter = 0

    def unprotect(self, generation: int, body: bytes, header: bytes = b"") -> bytes:
        if self.generation != generation or self.stream_connection_id is None:
            raise SecurityError("stale_security_context")
        if len(header) != 128 or len(body) < 16 or self.counter >= 2**64:
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
