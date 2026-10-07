"""Authentication authority boundary with an explicitly synthetic lab implementation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class AuthenticationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class AuthenticatedSession:
    session_id: str
    generation: int
    evidence: str


class AuthenticationAuthority(Protocol):
    def authenticate(self, generation: int) -> AuthenticatedSession: ...
    def close(self, session: AuthenticatedSession) -> None: ...


class SyntheticLabAuthenticationAuthority:
    """Creates a model-only session token; performs no MFi or iPhone auth."""

    def authenticate(self, generation: int) -> AuthenticatedSession:
        if generation < 1:
            raise AuthenticationError("invalid_session_generation")
        return AuthenticatedSession(f"synthetic-session-{generation}", generation, "MODEL_ONLY")

    def close(self, session: AuthenticatedSession) -> None:
        return None


class UnavailableAuthenticationAuthority:
    """Production placeholder that refuses authentication until implemented."""

    def authenticate(self, generation: int) -> AuthenticatedSession:
        raise AuthenticationError("authentication_authority_unavailable")

    def close(self, session: AuthenticatedSession) -> None:
        return None
