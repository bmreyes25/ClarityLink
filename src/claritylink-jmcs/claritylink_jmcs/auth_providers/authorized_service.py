"""Licensed service adapter slot; requires documented authorization and API."""
from ..authentication import AuthenticationError


def discover() -> None:
    raise AuthenticationError("licensed_service_api_unavailable")
