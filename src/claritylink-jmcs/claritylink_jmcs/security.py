"""Security provider boundary. No authentication bypass or unknown key path."""
from __future__ import annotations

from typing import Protocol


class SecurityError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ScreenSecurityProvider(Protocol):
    def open(self, generation: int, stream_connection_id: int) -> None: ...
    def unprotect(self, generation: int, body: bytes) -> bytes: ...
    def close(self) -> None: ...


class ClearLabSecurity:
    """Only for locally generated clear H.264 fixtures; never real CarPlay."""

    def __init__(self) -> None:
        self.generation: int | None = None

    def open(self, generation: int, stream_connection_id: int) -> None:
        if stream_connection_id < 1:
            raise SecurityError("invalid_stream_connection_id")
        self.generation = generation

    def unprotect(self, generation: int, body: bytes) -> bytes:
        if self.generation != generation:
            raise SecurityError("stale_security_context")
        return body

    def close(self) -> None:
        self.generation = None


class EvidenceRequiredSecurity:
    """Fail closed for encrypted Type111 pending actual protocol evidence."""

    def open(self, generation: int, stream_connection_id: int) -> None:
        raise SecurityError("type111_security_evidence_required")

    def unprotect(self, generation: int, body: bytes) -> bytes:
        raise SecurityError("type111_security_evidence_required")

    def close(self) -> None:
        return None
