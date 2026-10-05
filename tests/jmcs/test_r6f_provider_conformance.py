from __future__ import annotations

import json
import pickle
import pytest

from claritylink_jmcs.authentication import (
    AuthenticatedSessionHandoff, AuthenticationError, LabAuthenticationProvider,
    SessionOrigin,
)
from claritylink_jmcs.session_transport import LabSessionTransport, TransportError
from test_r6e_auth_transport import ContractAuthority, ContractChannel


def test_provider_lifecycle_and_private_state_conformance():
    channel = ContractChannel(1)
    authority = ContractAuthority(channel)
    provider = LabAuthenticationProvider(authority=authority)
    with pytest.raises(AuthenticationError, match="provider_not_initialized"):
        provider.authenticate()
    provider.initialize()
    handoff = provider.authenticate(1)
    assert provider.session_ready() is True
    assert handoff.authenticated is True
    with pytest.raises(AuthenticationError, match="session_already_active"):
        provider.authenticate(1)
    assert "contract-1" not in repr(handoff)
    assert "test-only-contract" not in repr(handoff)
    with pytest.raises(AuthenticationError, match="not_serializable"):
        pickle.dumps(handoff)
    transport = LabSessionTransport(handoff)
    with pytest.raises(TransportError, match="invalid_timeout"):
        transport.read_request(31)
    provider.close()
    provider.close()
    assert channel.closed and authority.closed and authority.context_closed
    assert handoff.closed


def test_stale_generation_disconnect_and_log_redaction():
    channel = ContractChannel(3)
    class StaleAuthority(ContractAuthority):
        def open(self, generation):
            return super().open(3)
    authority = StaleAuthority(channel)
    provider = LabAuthenticationProvider(authority=authority)
    provider.initialize()
    with pytest.raises(AuthenticationError, match="unverified_live_handoff"):
        provider.authenticate(4)
    assert channel.closed
    provider.close()

    channel = ContractChannel(4)
    handoff = ContractAuthority(channel).open(4)
    transport = LabSessionTransport(handoff)
    channel.close()
    with pytest.raises(TransportError, match="stale_or_closed_transport"):
        transport.write_response(type("Response", (), {"generation": 4})())
    payload = {"session_identifier": "contract-4", "secret": "never-log-this"}
    sanitized = json.dumps({"keys": sorted(payload), "types": [type(x).__name__ for x in payload.values()]})
    assert "never-log-this" not in sanitized
    assert "contract-4" not in sanitized


def test_provider_contains_vendor_open_exception_text():
    class BrokenAuthority(ContractAuthority):
        def open(self, generation):
            raise RuntimeError("PRIVATE_AUTH_BLOB_must_not_escape")

    authority = BrokenAuthority(ContractChannel(1))
    provider = LabAuthenticationProvider(authority=authority)
    provider.initialize()
    with pytest.raises(AuthenticationError, match="authority_open_failed") as error:
        provider.authenticate(1)
    assert "PRIVATE_AUTH_BLOB" not in str(error.value)


def test_timeout_is_contained_and_provider_can_close():
    class TimeoutChannel(ContractChannel):
        def read_request(self, timeout):
            raise TimeoutError("private vendor detail")

    channel = TimeoutChannel(1)
    authority = ContractAuthority(channel)
    provider = LabAuthenticationProvider(authority=authority)
    provider.initialize()
    handoff = provider.authenticate(1)
    transport = LabSessionTransport(handoff)
    with pytest.raises(TransportError, match="peer_disconnected_or_timeout") as error:
        transport.read_request(2)
    assert "private vendor detail" not in str(error.value)
    provider.close()
    assert channel.closed and authority.closed and handoff.closed


def test_handoff_rejects_stale_claim_and_is_single_owner():
    handoff = AuthenticatedSessionHandoff(
        "private-id", 2, SessionOrigin.AUTHENTICATED_LAB, "owner",
        ContractChannel(2), authority_type=ContractAuthority.authority_type,
        authenticated=True,
    )
    with pytest.raises(AuthenticationError, match="stale_handoff_generation"):
        handoff.claim(1)
    handoff.claim(2)
    with pytest.raises(AuthenticationError, match="handoff_unavailable"):
        handoff.claim(2)
    handoff.close()
