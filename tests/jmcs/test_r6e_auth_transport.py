from __future__ import annotations

import json
from pathlib import Path
import pickle
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-jmcs"))
sys.path.insert(0, str(ROOT / "tools"))

from claritylink_jmcs.authentication import (AuthenticatedSessionHandoff, AuthenticationError,
    AuthorityType, LabAuthenticationProvider, SessionOrigin)
from claritylink_jmcs.auth_providers import select_provider
from claritylink_jmcs.receiver import Receiver
from claritylink_jmcs.session import ReceiverSession
from claritylink_jmcs.session_transport import (ControlRequest, LabSessionTransport,
    TransportError, validate_control_request)
from claritylink_jmcs.trace import SanitizedTrace
from test_r6b_session_boundary import profile
from r6e_real_ios_lab import preflight
from argparse import Namespace


class ContractChannel:
    """Test double; never real iPhone evidence."""
    def __init__(self, generation: int, requests=()):
        self.authenticated = True
        self.session_identifier = f"contract-{generation}"
        self.generation = generation
        self.requests = list(requests)
        self.responses = []
        self.closed = False

    def read_request(self, timeout):
        if not self.requests:
            raise EOFError
        return self.requests.pop(0)

    def write_response(self, response):
        self.responses.append(response)

    def close(self):
        self.closed = True
        self.authenticated = False


class ContractAuthority:
    identity = "test-only-contract"
    authority_type = AuthorityType.GENUINE_HARDWARE
    explicitly_authorized = True

    def __init__(self, channel):
        self.channel = channel
        self.closed = False
        self.context_closed = False

    def open(self, generation):
        assert generation == self.channel.generation
        context = type("Context", (), {"close": lambda _: setattr(self, "context_closed", True)})()
        return AuthenticatedSessionHandoff(self.channel.session_identifier, generation,
            SessionOrigin.AUTHENTICATED_LAB, self.identity, self.channel, context,
            authority_type=self.authority_type, authenticated=True)

    def close(self):
        self.closed = True


def test_handoff_rejects_untrusted_replay_and_serialization():
    with pytest.raises(AuthenticationError, match="authenticated_authority_required"):
        AuthenticatedSessionHandoff("x", 1, SessionOrigin.AUTHENTICATED_LAB, "x", object())
    with pytest.raises(AuthenticationError, match="synthetic_cannot_authenticate"):
        AuthenticatedSessionHandoff("x", 1, SessionOrigin.SANITIZED_REPLAY, "x", object(),
                                    authenticated=True)
    channel = ContractChannel(1)
    handoff = ContractAuthority(channel).open(1)
    with pytest.raises(AuthenticationError, match="not_serializable"):
        pickle.dumps(handoff)
    with pytest.raises(AuthenticationError, match="stale_handoff_generation"):
        handoff.claim(2)
    handoff.claim(1)
    with pytest.raises(AuthenticationError, match="handoff_unavailable"):
        handoff.claim(1)
    handoff.close()
    handoff.close()
    assert channel.closed and handoff.security_context is None
    with pytest.raises(TransportError):
        LabSessionTransport(handoff)


def test_provider_rejects_unauthorized_and_missing_adapter():
    with pytest.raises(AuthenticationError, match="adapter_unavailable"):
        select_provider("hardware")
    authority = ContractAuthority(ContractChannel(1))
    authority.explicitly_authorized = False
    provider = LabAuthenticationProvider(authority=authority)
    provider.initialize()
    with pytest.raises(AuthenticationError, match="authority_not_authorized"):
        provider.authenticate()


@pytest.mark.parametrize("body", [
    {"x": "a" * 4097},
    {"x": [0] * 257},
    {"x": b"a" * 1_000_001},
    {"x": object()},
])
def test_bounded_control_input(body):
    with pytest.raises(TransportError):
        validate_control_request(ControlRequest("GET", "/info", body, 1), 1)


def test_malformed_request_tears_down_every_resource(tmp_path):
    channel = ContractChannel(1, [ControlRequest("GET", "/info", {"x": "a" * 4097}, 1)])
    authority = ContractAuthority(channel)
    session = ReceiverSession(LabAuthenticationProvider(authority=authority), Receiver(), profile(tmp_path))
    session.open()
    with pytest.raises(TransportError, match="control_string_limit"):
        session.handle_one()
    assert session.receiver.snapshot().sessions == 0
    assert channel.closed and authority.closed and authority.context_closed
    session.close()


def test_100_generation_owned_contract_cycles(tmp_path):
    receiver = Receiver()
    for generation in range(1, 101):
        channel = ContractChannel(generation, [ControlRequest("GET", "/info", {}, generation)])
        authority = ContractAuthority(channel)
        session = ReceiverSession(LabAuthenticationProvider(authority=authority), receiver, profile(tmp_path))
        session.open()
        assert session.handle_one().status == 200
        session.close()
        assert channel.closed and authority.closed and authority.context_closed
        assert receiver.snapshot().sessions == 0
    assert receiver.generation == 100


def test_duplicate_owner_and_authority_first_close(tmp_path):
    channel = ContractChannel(1, [ControlRequest("GET", "/info", {}, 1)])
    authority = ContractAuthority(channel)
    handoff = authority.open(1)
    class ReusedAuthority(ContractAuthority):
        def open(self, generation):
            return handoff
    first = ReceiverSession(LabAuthenticationProvider(authority=ReusedAuthority(channel)),
                            Receiver(), profile(tmp_path))
    first.open()
    second = ReceiverSession(LabAuthenticationProvider(authority=ReusedAuthority(channel)),
                             Receiver(), profile(tmp_path))
    with pytest.raises(AuthenticationError, match="unverified_live_handoff"):
        second.open()
    assert not channel.closed
    assert first.handle_one().status == 200
    channel.close()  # external authority/peer owns channel closure
    with pytest.raises(TransportError, match="transport_closed"):
        first.handle_one()
    assert first.receiver.snapshot().sessions == 0
    first.close()


def test_preflight_fails_closed_without_authority(tmp_path):
    result = preflight(Namespace(bind="127.0.0.1", profile=None, provider=None,
                                 identity_path=tmp_path / "identity.json"))
    assert result["ready"] is False
    assert result["reason"] == "R6E_AUTHORITY_NOT_AVAILABLE"
    assert result["checks"]["authority_reachable"] is False
    result = preflight(Namespace(bind="0.0.0.0", profile=None, provider="hardware",
                                 identity_path=tmp_path / "identity.json"))
    assert result["checks"]["private_bind"] is False
    assert "identity.json" not in json.dumps(result)
    process = subprocess.run([sys.executable, str(ROOT / "tools" / "r6e_real_ios_lab.py"),
                              "preflight"], text=True, capture_output=True, check=False)
    assert process.returncode == 1
    assert json.loads(process.stdout)["ready"] is False


def test_trace_reports_types_without_private_values():
    trace = SanitizedTrace()
    request = ControlRequest("SETUP", "/session",
        {"streams": [{"type": 111, "streamConnectionID": 12345,
                      "phone_private_identifier": "never-log-this"}]}, 1)
    validate_control_request(request, 1)
    trace.emit_request(request)
    output = json.dumps(trace.events)
    assert "streams:array:1" in output
    assert "streamConnectionID:int" in output
    assert "never-log-this" not in output
    assert "phone_private_identifier" not in output
    assert "12345" not in output
