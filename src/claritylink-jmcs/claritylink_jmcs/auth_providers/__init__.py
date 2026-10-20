"""Provider selection is intentionally fail closed until a lawful adapter exists."""
from __future__ import annotations

from ..authentication import AuthenticationError, AuthenticationProvider

SUPPORTED = ("hardware", "authorized_service")


def select_provider(kind: str | None) -> AuthenticationProvider:
    if kind not in SUPPORTED:
        raise AuthenticationError("authorized_provider_not_configured")
    # No documented user-owned adapter/service API is installed in this lab.
    raise AuthenticationError("authorized_provider_adapter_unavailable")
