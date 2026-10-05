from __future__ import annotations

import json
from pathlib import Path
import sys
import types
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-jmcs"))
sys.path.insert(0, str(ROOT / "tools"))
from claritylink_jmcs.authentication import (AuthenticationError, HondaAuthenticationProviderStub,
    LabAuthenticationProvider, ReplayAuthenticationProvider, SessionHandoff, SessionOrigin, AuthorityType)
from claritylink_jmcs.identity import IdentityError, load_or_create_identity
from claritylink_jmcs.info import InfoError, InfoProfile, build_info, validate_info_shape
from claritylink_jmcs.receiver import Receiver
from claritylink_jmcs.session import ReceiverSession, SessionError
from claritylink_jmcs.session_transport import (ControlRequest, ControlResponse, LabSessionTransport,
    ReplaySessionTransport, TransportError)
from claritylink_jmcs.trace import SanitizedTrace, TraceError, TraceEvent
from r6b_info_diff import compare


def profile(tmp_path: Path) -> InfoProfile:
    identity = load_or_create_identity(tmp_path / "private" / "identity.json")
    return InfoProfile(identity, "ClarityLink Lab", "HostLab", "ClarityLink", "366.0", 42,
        ({"type": 100, "audioType": "default", "audioOutputFormats": 1024},),
        ({"type": 100, "inputLatencyMicros": 0, "outputLatencyMicros": 0},),
        ({"uuid": "synthetic-touch", "name": "Synthetic Touch", "displayUUID": identity.main_uuid,
          "hidDescriptor": b"\x05\x0D", "hidProductID": 1, "hidVendorID": 2, "hidCountryCode": 0},))


def replay_handoff(generation: int, identifier: str = "fixture-session") -> SessionHandoff:
    return SessionHandoff(identifier, generation, SessionOrigin.SANITIZED_REPLAY, "sanitized fixture", object())


def test_lab_auth_refuses_without_lawful_handoff_and_honda_stub():
    lab = LabAuthenticationProvider()
    lab.initialize()
    with pytest.raises(AuthenticationError, match="lawful_auth_substrate_required"):
        lab.authenticate()
    assert not lab.session_ready()
    lab.close()
    with pytest.raises(AuthenticationError, match="provider_closed"):
        lab.initialize()
    with pytest.raises(AuthenticationError, match="EVIDENCE_REQUIRED_HONDA_AUTH"):
        HondaAuthenticationProviderStub().initialize()


def test_identity_stable_private_and_outside_repo(tmp_path: Path):
    path = tmp_path / "identity.json"
    first = load_or_create_identity(path)
    assert first == load_or_create_identity(path)
    assert path.stat().st_mode & 0o077 == 0
    assert int(first.device_id[:2], 16) & 3 == 2
    with pytest.raises(IdentityError, match="identity_path_inside_repository"):
        load_or_create_identity(ROOT / "tmp-identity.json")


def test_complete_shape_info_requires_injected_audio_hid(tmp_path: Path):
    info = build_info(profile(tmp_path))
    assert validate_info_shape(info) == ()
    assert [x["type"] for x in info["displays"]] == [110, 111]
    from dataclasses import replace
    with pytest.raises(InfoError, match="audio_hid_capabilities_required"):
        build_info(replace(profile(tmp_path), hid_devices=()))
    with pytest.raises(InfoError, match="invalid_hid_capability"):
        build_info(replace(profile(tmp_path), hid_devices=({"uuid": "stub"},)))


def test_info_diff_never_emits_identity_values(tmp_path: Path):
    reference = build_info(profile(tmp_path))
    candidate = dict(reference)
    candidate["deviceID"] = "synthetic-private-identifier"
    candidate["features"] = 43
    candidate["some_private_token"] = "do-not-print-me"
    candidate.pop("audioFormats")
    result = compare(reference, candidate)
    rendered = json.dumps(result)
    assert "audioFormats" in result["missing_fields"]
    assert "features" in result["feature_mismatch"]
    assert "unknown_field" in result and result["unknown_field"]
    assert "synthetic-private-identifier" not in rendered and "do-not-print-me" not in rendered


def test_trace_rejects_private_metadata_and_values():
    trace = SanitizedTrace(limit=2)
    trace.emit(TraceEvent.AUTH_START, status="begin")
    with pytest.raises(TraceError, match="unsafe_trace_event"):
        trace.emit(TraceEvent.AUTH_SUCCESS, certificate="private")
    with pytest.raises(TraceError, match="invalid_trace_status"):
        trace.emit(TraceEvent.AUTH_FAILURE, status="serial-123")
    trace.emit(TraceEvent.AUTH_FAILURE, status="failed")
    assert "serial" not in json.dumps(trace.events)
    with pytest.raises(TraceError, match="trace_limit"):
        trace.emit(TraceEvent.SESSION_OPEN)


def test_replay_session_info_type110_type111_and_teardown(tmp_path: Path):
    handoff = replay_handoff(1)
    requests = [ControlRequest("GET", "/info", {}, 1),
                ControlRequest("SETUP", "/session", {"streams": [
                    {"type": 111, "streamConnectionID": 1111},
                    {"type": 110, "streamConnectionID": 1100}]}, 1)]
    transport = ReplaySessionTransport(handoff, requests)
    session = ReceiverSession(ReplayAuthenticationProvider(handoff), Receiver(clear_lab=True),
                              profile(tmp_path), allow_replay=True)
    session.open(transport)
    info = session.handle_one()
    setup = session.handle_one()
    assert info.status == 200 and validate_info_shape(info.body) == ()
    assert [x["type"] for x in setup.body["streams"]] == [110, 111]
    assert not transport.authenticated
    session.close()
    assert session.receiver.snapshot().sessions == 0
    assert "SETUP_TYPE111" in [event["event"] for event in session.trace.events]
    assert "1111" not in json.dumps(session.trace.events)


def test_replay_never_promoted_to_live(tmp_path: Path):
    handoff = replay_handoff(1)
    session = ReceiverSession(ReplayAuthenticationProvider(handoff), Receiver(), profile(tmp_path))
    with pytest.raises(SessionError, match="replay_not_enabled"):
        session.open(ReplaySessionTransport(handoff, []))
    assert session.receiver.snapshot().sessions == 0


def test_live_handoff_contract_with_external_channel(tmp_path: Path):
    class Channel:
        def __init__(self):
            self.closed = False
            self.authenticated = True
            self.session_identifier = "opaque"
            self.generation = 1
            self.requests = [ControlRequest("GET", "/info", {}, 1)]
            self.responses = []
        def read_request(self, timeout): return self.requests.pop(0)
        def write_response(self, response): self.responses.append(response)
        def close(self): self.closed = True
    channel = Channel()
    class ContractAuthority:
        identity = "test-contract-only"
        authority_type = AuthorityType.GENUINE_HARDWARE
        explicitly_authorized = True
        def open(self, generation):
            return SessionHandoff("opaque", generation, SessionOrigin.AUTHENTICATED_LAB,
                                  self.identity, channel, authority_type=self.authority_type,
                                  authenticated=True)
        def close(self): pass
    session = ReceiverSession(LabAuthenticationProvider(authority=ContractAuthority()), Receiver(), profile(tmp_path))
    session.open()
    assert session.transport.authenticated
    assert session.handle_one().status == 200
    session.close()
    assert channel.closed
    # This proves only the adapter contract; the channel above is a test double.


def test_truncated_malformed_setup_and_stale_generation_contained(tmp_path: Path):
    handoff = replay_handoff(1)
    malformed = ControlRequest("SETUP", "/session", {"streams": [
        {"type": 110, "streamConnectionID": 1},
        {"type": 111, "streamConnectionID": 1}]}, 1)
    transport = ReplaySessionTransport(handoff, [ControlRequest("GET", "/info", {}, 1), malformed])
    session = ReceiverSession(ReplayAuthenticationProvider(handoff), Receiver(clear_lab=True),
                              profile(tmp_path), allow_replay=True)
    session.open(transport)
    session.handle_one()
    with pytest.raises(Exception, match="duplicate_stream_connection_id"):
        session.handle_one()
    session.close()
    assert session.receiver.snapshot().secondary_listeners == 0
    with pytest.raises(TransportError, match="transport_closed"):
        transport.read_request(1)


def test_100_replay_auth_session_cycles(tmp_path: Path):
    for _ in range(100):
        handoff = replay_handoff(1)
        transport = ReplaySessionTransport(handoff, [ControlRequest("GET", "/info", {}, 1)])
        session = ReceiverSession(ReplayAuthenticationProvider(handoff), Receiver(),
                                  profile(tmp_path), allow_replay=True)
        session.open(transport)
        session.handle_one()
        session.close()
        assert session.receiver.snapshot().sessions == 0
        assert session.receiver.snapshot().secondary_listeners == 0
