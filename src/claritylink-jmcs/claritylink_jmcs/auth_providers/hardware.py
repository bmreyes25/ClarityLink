"""Genuine hardware adapter slot; requires documented, user-owned hardware API."""
from ..authentication import AuthenticationError


def discover() -> None:
    raise AuthenticationError("genuine_hardware_api_unavailable")
