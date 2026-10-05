from __future__ import annotations

import pickle

import pytest

from claritylink_jmcs.authentication import AuthenticationError, LabAuthenticationProvider
from claritylink_jmcs.auth_providers.livi import LiviAuthority
from claritylink_jmcs.session_transport import ControlRequest, ControlResponse, TransportError


class SyntheticBridge:
    """Synthetic contract fixture; never evidence of LIVI or iPhone auth."""

    def __init__(self, generation: int):
        self.authenticated = True
        self.session_identifier = f"test-session-{generation}"
        self.generation = generation
        self.closed = False
        self.requests = [ControlRequest("GET", "/info", {}, generation)]
        self.responses = []

    def read_request(self, timeout: float):
        if self.closed:
            raise EOFError("private fixture detail")
        if not 0 < timeout <= 30:
            raise TimeoutError("private fixture detail")
        return self.requests.pop(0)

    def write_response(self, response):
        self.responses.append(response)

    def close(self):
        self.closed = True


class SyntheticFactory:
    def __init__(self, generation: int):
        self.bridge = SyntheticBridge(generation)
        self.closed = False

    def open_authenticated(self, generation: int):
        if generation != self.bridge.generation:
            raise RuntimeError("private session details")
        return self.bridge

    def close(self):
        self.closed = True


def test_livi_provider_fails_closed_without_explicit_authorization():
    provider = LabAuthenticationProvider(
        authority=LiviAuthority(bridge_factory=SyntheticFactory(1))
    )
    provider.initialize()
    with pytest.raises(AuthenticationError, match="authority_not_authorized"):
        provider.authenticate(1)


def test_livi_provider_handoff_routes_once_and_redacts_private_state():
    factory = SyntheticFactory(1)
    authority = LiviAuthority(bridge_factory=factory, explicitly_authorized=True)
    provider = LabAuthenticationProvider(authority=authority)
    provider.initialize()
    handoff = provider.authenticate(1)
    handoff.claim(1)
    transport = handoff.transport
    request = transport.read_request(3)
    assert request == ControlRequest("GET", "/info", {}, 1)
    response = ControlResponse(200, {"ok": True}, 1)
    transport.write_response(response)
    assert factory.bridge.responses == [response]
    assert "test-session" not in repr(handoff)
    assert "test-session" not in repr(transport)
    with pytest.raises(AuthenticationError, match="not_serializable"):
        pickle.dumps(handoff)
    provider.close()
    provider.close()
    assert factory.bridge.closed and factory.closed and handoff.closed


def test_livi_provider_rejects_stale_generation_timeout_and_disconnect():
    factory = SyntheticFactory(2)
    provider = LabAuthenticationProvider(
        authority=LiviAuthority(bridge_factory=factory, explicitly_authorized=True)
    )
    provider.initialize()
    with pytest.raises(AuthenticationError, match="livi_bridge_open_failed"):
        provider.authenticate(3)
    provider.close()

    factory = SyntheticFactory(4)
    provider = LabAuthenticationProvider(
        authority=LiviAuthority(bridge_factory=factory, explicitly_authorized=True)
    )
    provider.initialize()
    handoff = provider.authenticate(4)
    transport = handoff.transport
    with pytest.raises(TransportError, match="invalid_timeout"):
        transport.read_request(31)
    factory.bridge.close()
    with pytest.raises(TransportError, match="peer_disconnected_or_timeout"):
        transport.read_request(1)
    provider.close()


def test_livi_provider_contains_bridge_errors_and_stale_responses():
    factory = SyntheticFactory(5)
    provider = LabAuthenticationProvider(
        authority=LiviAuthority(bridge_factory=factory, explicitly_authorized=True)
    )
    provider.initialize()
    handoff = provider.authenticate(5)
    transport = handoff.transport
    with pytest.raises(TransportError, match="stale_or_closed_transport"):
        transport.write_response(ControlResponse(200, {}, 4))
    assert "private fixture detail" not in repr(provider)
    provider.close()


def test_livi_provider_rejects_unauthenticated_and_malformed_or_oversized_requests():
    factory = SyntheticFactory(6)
    factory.bridge.authenticated = False
    authority = LiviAuthority(bridge_factory=factory, explicitly_authorized=True)
    with pytest.raises(AuthenticationError, match="livi_authenticated_bridge_required"):
        authority.open(6)
    assert factory.bridge.closed

    factory = SyntheticFactory(7)
    provider = LabAuthenticationProvider(
        authority=LiviAuthority(bridge_factory=factory, explicitly_authorized=True)
    )
    provider.initialize()
    handoff = provider.authenticate(7)
    factory.bridge.requests = [ControlRequest("GET", "/info", {"large": "x" * 5000}, 7)]
    with pytest.raises(TransportError, match="control_string_limit"):
        handoff.transport.read_request(2)
    provider.close()


def test_livi_provider_100_synthetic_lifecycle_cycles():
    for generation in range(1, 101):
        factory = SyntheticFactory(generation)
        provider = LabAuthenticationProvider(
            authority=LiviAuthority(bridge_factory=factory, explicitly_authorized=True)
        )
        provider.initialize()
        handoff = provider.authenticate(generation)
        handoff.claim(generation)
        provider.close()
        provider.close()
        assert handoff.closed and factory.bridge.closed and factory.closed
