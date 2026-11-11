"""CL-AUTH-01 M2: authority provenance, handoff ownership and control-transport lifecycle.

Every fixture here is synthetic. Nothing in this file is evidence of MFi, LIVI,
iPhone or Honda authentication.
"""
from __future__ import annotations

from pathlib import Path
import pickle
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-jmcs"))

from claritylink_jmcs import authentication as auth_module
from claritylink_jmcs.authentication import (
    AuthenticatedSessionHandoff, AuthenticationError, AuthorityType, LabAuthenticationProvider,
    ReplayAuthenticationProvider, SessionLedger, SessionOrigin, TrustClass, attest_handoff,
    real_authentication_proven)
from claritylink_jmcs.auth_providers.livi import LiviAuthority
from claritylink_jmcs.receiver import Receiver
from claritylink_jmcs.session import ReceiverSession, SessionError
from claritylink_jmcs.session_transport import (ControlRequest, ControlResponse,
                                                LabSessionTransport, TransportError)
from test_r6b_session_boundary import profile
from test_r6e_auth_transport import ContractAuthority, ContractChannel
from test_r6g_livi_provider import SyntheticFactory


def _live_handoff(channel=None, generation=1, **kwargs) -> AuthenticatedSessionHandoff:
    channel = channel or ContractChannel(generation)
    return AuthenticatedSessionHandoff(
        channel.session_identifier, generation, SessionOrigin.AUTHENTICATED_LAB,
        ContractAuthority.identity, channel,
        authority_type=AuthorityType.GENUINE_HARDWARE, authenticated=True, **kwargs)


def _session(tmp_path, channel, receiver=None, **kwargs):
    authority = ContractAuthority(channel)
    session = ReceiverSession(LabAuthenticationProvider(authority=authority),
                              receiver or Receiver(clear_lab=True), profile(tmp_path), **kwargs)
    return session, authority


# ---- C1 provenance -------------------------------------------------------

def test_synthetic_bridge_handoff_is_never_real_and_receiver_session_rejects_it(tmp_path):
    factory = SyntheticFactory(1)
    provider = LabAuthenticationProvider(authority=LiviAuthority(
        bridge_factory=factory, explicitly_authorized=True, allow_synthetic_test_bridge=True))
    session = ReceiverSession(provider, Receiver(clear_lab=True), profile(tmp_path))
    with pytest.raises(SessionError, match="synthetic_authority_not_enabled"):
        session.open()
    assert factory.bridge.closed and factory.closed
    assert session.receiver.snapshot().sessions == 0 and session.trust is None


def test_synthetic_bridge_accepted_only_when_explicitly_enabled_and_never_proven(tmp_path):
    factory = SyntheticFactory(1)
    provider = LabAuthenticationProvider(authority=LiviAuthority(
        bridge_factory=factory, explicitly_authorized=True, allow_synthetic_test_bridge=True))
    session = ReceiverSession(provider, Receiver(clear_lab=True), profile(tmp_path),
                              allow_synthetic_authority=True)
    session.open()
    handoff = session._handoff
    assert session.trust is TrustClass.SYNTHETIC_TEST
    assert handoff.capabilities["real_livi_bridge"] is False
    assert real_authentication_proven(handoff) is False
    session.close()


def test_real_kind_bridge_is_unverified_hardware_not_attested():
    class Bridge:
        bridge_kind = "REAL_LIVI_BRIDGE"
        authenticated = True
        session_identifier = "bridge-session"
        generation = 1
        def read_request(self, timeout): raise EOFError
        def write_response(self, response): pass
        def close(self): pass

    class Factory:
        bridge_kind = "REAL_LIVI_BRIDGE"
        def open_authenticated(self, generation): return Bridge()
        def close(self): pass

    handoff = LiviAuthority(bridge_factory=Factory(), explicitly_authorized=True).open(1)
    assert handoff.trust is TrustClass.UNVERIFIED_HARDWARE
    assert real_authentication_proven(handoff) is False
    handoff.close()


@pytest.mark.parametrize("trust", [TrustClass.ATTESTED, TrustClass.REPLAY_FIXTURE])
def test_constructor_cannot_assign_attested_or_replay_trust_to_live_handoff(trust):
    with pytest.raises(AuthenticationError, match="trust_not_assignable"):
        _live_handoff(trust=trust)


def test_replay_handoff_cannot_claim_live_trust():
    with pytest.raises(AuthenticationError, match="trust_not_assignable"):
        AuthenticatedSessionHandoff("r", 1, SessionOrigin.SANITIZED_REPLAY, "r", object(),
                                    trust=TrustClass.UNVERIFIED_HARDWARE)
    replay = AuthenticatedSessionHandoff("r", 1, SessionOrigin.SANITIZED_REPLAY, "r", object())
    assert replay.trust is TrustClass.REPLAY_FIXTURE and not real_authentication_proven(replay)


def test_caller_supplied_labels_and_capabilities_cannot_promote_trust():
    handoff = _live_handoff(capabilities={"attested": True, "real_livi_bridge": True,
                                          "genuine": True, "trust": True})
    assert handoff.trust is TrustClass.UNVERIFIED_HARDWARE
    assert not real_authentication_proven(handoff)
    service = AuthenticatedSessionHandoff(
        "svc", 1, SessionOrigin.AUTHENTICATED_LAB, "svc", object(),
        authority_type=AuthorityType.LICENSED_MFI_SERVICE, authenticated=True)
    assert service.trust is TrustClass.UNVERIFIED_SERVICE


def test_attestation_denied_for_caller_supplied_verifier():
    class EagerVerifier:
        def verify(self, handoff): return True

    handoff = _live_handoff()
    with pytest.raises(AuthenticationError, match="attestation_verifier_untrusted"):
        attest_handoff(handoff, EagerVerifier())
    assert handoff.trust is TrustClass.UNVERIFIED_HARDWARE
    assert auth_module._TRUSTED_ATTESTATION_VERIFIERS == ()


def test_attestation_requires_reviewed_verifier_affirmative_result_and_live_state(monkeypatch):
    class Reviewed:
        outcome: object = True
        def verify(self, handoff): return self.outcome

    monkeypatch.setattr(auth_module, "_TRUSTED_ATTESTATION_VERIFIERS", (Reviewed,))
    for outcome in (False, 1, "yes", None):
        verifier = Reviewed()
        verifier.outcome = outcome
        handoff = _live_handoff()
        with pytest.raises(AuthenticationError, match="attestation_failed"):
            attest_handoff(handoff, verifier)
        assert handoff.trust is TrustClass.UNVERIFIED_HARDWARE

    synthetic = _live_handoff(trust=TrustClass.SYNTHETIC_TEST)
    with pytest.raises(AuthenticationError, match="attestation_not_applicable"):
        attest_handoff(synthetic, Reviewed())
    closed = _live_handoff()
    closed.close()
    with pytest.raises(AuthenticationError, match="attestation_not_applicable"):
        attest_handoff(closed, Reviewed())

    handoff = _live_handoff()
    attest_handoff(handoff, Reviewed())
    assert real_authentication_proven(handoff)
    handoff.close()
    assert not real_authentication_proven(handoff)


def test_replayed_handoff_object_and_double_provider_use_are_rejected():
    channel = ContractChannel(1)
    handoff = _live_handoff(channel)

    class Reusing(ContractAuthority):
        def open(self, generation): return handoff

    first = LabAuthenticationProvider(authority=Reusing(channel))
    first.initialize()
    claimed = first.authenticate(1)
    claimed.claim(1)
    second = LabAuthenticationProvider(authority=Reusing(channel))
    second.initialize()
    with pytest.raises(AuthenticationError, match="unverified_live_handoff"):
        second.authenticate(1)
    with pytest.raises(AuthenticationError, match="session_already_active"):
        first.authenticate(1)
    with pytest.raises(AuthenticationError, match="handoff_unavailable"):
        claimed.claim(1)

    replay = AuthenticatedSessionHandoff("fx", 1, SessionOrigin.SANITIZED_REPLAY, "fx", object())
    replay_provider = ReplayAuthenticationProvider(replay)
    replay_provider.initialize()
    replay_provider.authenticate(1).claim(1)
    replay_provider._handoff = None
    with pytest.raises(AuthenticationError, match="replay_unavailable"):
        replay_provider.authenticate(1)


def test_untrusted_valid_looking_session_identifier_reuse_is_rejected_across_providers(tmp_path):
    ledger = SessionLedger()
    first, _ = _session(tmp_path, ContractChannel(1), session_ledger=ledger)
    first.open()
    first.close()
    second, authority = _session(tmp_path, ContractChannel(1), session_ledger=ledger)
    with pytest.raises(AuthenticationError, match="session_identifier_reused"):
        second.open()
    assert authority.closed and authority.channel.closed
    assert second.receiver.snapshot().sessions == 0


def test_session_ledger_is_bounded_and_validates_input():
    ledger = SessionLedger(capacity=2)
    for identifier in ("a", "b", "c"):
        ledger.admit(identifier)
    ledger.admit("a")  # evicted from the bounded window
    with pytest.raises(AuthenticationError, match="session_identifier_reused"):
        ledger.admit("c")
    for bad in ("", None, 5):
        with pytest.raises(AuthenticationError, match="invalid_session_identifier"):
            ledger.admit(bad)
    for bad in (0, True, 1 << 20):
        with pytest.raises(AuthenticationError, match="invalid_ledger_capacity"):
            SessionLedger(bad)


# ---- C2 handoff ownership and revocation ---------------------------------

def test_parent_closure_revokes_receiver_generation_and_dependent_streams(tmp_path):
    channel = ContractChannel(1, [ControlRequest("GET", "/info", {}, 1)])
    session, authority = _session(tmp_path, channel)
    session.open()
    session.handle_one()
    receiver = session.receiver
    receiver.setup({"streams": [{"type": 110, "streamConnectionID": 10},
                                {"type": 111, "streamConnectionID": 11}]}, 1)
    snap = receiver.snapshot()
    assert snap.primary_listeners == 1 and snap.secondary_listeners == 1
    session._handoff.close()  # authority loss with no further control read
    snap = receiver.snapshot()
    assert (snap.sessions, snap.primary_listeners, snap.secondary_listeners) == (0, 0, 0)
    assert session.generation is None and session.transport is None and session.trust is None
    assert channel.closed and authority.closed and authority.context_closed
    session.close()  # idempotent after revocation


def test_close_callbacks_are_contained_bounded_and_run_once():
    handoff = _live_handoff()
    calls = []
    handoff.add_close_callback(lambda: (_ for _ in ()).throw(RuntimeError("secret detail")))
    handoff.add_close_callback(lambda: calls.append("second"))
    handoff.close()
    handoff.close()
    assert calls == ["second"]
    handoff.add_close_callback(lambda: calls.append("late"))
    assert calls == ["second", "late"]
    with pytest.raises(AuthenticationError, match="invalid_close_callback"):
        handoff.add_close_callback("not callable")
    other = _live_handoff()
    for _ in range(16):
        other.add_close_callback(lambda: None)
    with pytest.raises(AuthenticationError, match="close_callback_limit"):
        other.add_close_callback(lambda: None)


def test_close_callbacks_run_even_when_resource_close_fails():
    class Failing:
        def close(self): raise RuntimeError("private transport detail")

    handoff = AuthenticatedSessionHandoff(
        "x", 1, SessionOrigin.AUTHENTICATED_LAB, "o", Failing(),
        authority_type=AuthorityType.GENUINE_HARDWARE, authenticated=True)
    ran = []
    handoff.add_close_callback(lambda: ran.append(True))
    with pytest.raises(AuthenticationError, match="handoff_transport_close_failed"):
        handoff.close()
    assert ran == [True]


def test_handoff_is_not_serializable_and_repr_omits_identifiers():
    channel = ContractChannel(1)
    channel.session_identifier = "private-identifier-value"
    handoff = _live_handoff(channel)
    with pytest.raises(AuthenticationError, match="handoff_not_serializable"):
        pickle.dumps(handoff)
    text = repr(handoff)
    assert "private-identifier-value" not in text and "trust=UNVERIFIED_HARDWARE" in text


# ---- C3 transport lifecycle ----------------------------------------------

def _transport(requests=()):
    channel = ContractChannel(1, requests)
    return LabSessionTransport(_live_handoff(channel)), channel


def test_transport_pairs_exactly_one_response_per_request():
    transport, channel = _transport([ControlRequest("GET", "/info", {}, 1),
                                     ControlRequest("GET", "/info", {}, 1)])
    ok = ControlResponse(200, {}, 1)
    with pytest.raises(TransportError, match="response_without_request"):
        transport.write_response(ok)
    transport.read_request(1)
    with pytest.raises(TransportError, match="request_already_pending"):
        transport.read_request(1)
    transport.write_response(ok)
    with pytest.raises(TransportError, match="response_without_request"):
        transport.write_response(ok)  # duplicate response
    assert len(channel.responses) == 1
    transport.read_request(1)  # next request is admitted after the response


@pytest.mark.parametrize("response", [
    ControlResponse(99, {}, 1), ControlResponse(600, {}, 1), ControlResponse(True, {}, 1),
    ControlResponse(200, {}, 2), "not a response"])
def test_transport_rejects_malformed_or_wrong_generation_response(response):
    transport, channel = _transport([ControlRequest("GET", "/info", {}, 1)])
    transport.read_request(1)
    with pytest.raises(TransportError):
        transport.write_response(response)
    assert channel.responses == []


def test_failed_response_write_consumes_the_request():
    transport, channel = _transport([ControlRequest("GET", "/info", {}, 1)])
    channel.write_response = lambda response: (_ for _ in ()).throw(ConnectionError("x"))
    transport.read_request(1)
    with pytest.raises(ConnectionError):
        transport.write_response(ControlResponse(200, {}, 1))
    with pytest.raises(TransportError, match="response_without_request"):
        transport.write_response(ControlResponse(200, {}, 1))


def test_wrong_generation_control_request_tears_down_session(tmp_path):
    channel = ContractChannel(1, [ControlRequest("GET", "/info", {}, 2)])
    session, authority = _session(tmp_path, channel)
    session.open()
    with pytest.raises(TransportError, match="invalid_or_stale_request"):
        session.handle_one()
    assert session.receiver.snapshot().sessions == 0 and channel.closed and authority.closed


def test_transport_closure_during_info_tears_down_every_resource(tmp_path):
    channel = ContractChannel(1, [ControlRequest("GET", "/info", {}, 1)])
    session, authority = _session(tmp_path, channel)
    session.open()
    channel.close()  # peer/authority lost before /info is read
    with pytest.raises(TransportError, match="transport_closed"):
        session.handle_one()
    assert session.receiver.snapshot().sessions == 0 and authority.closed


def test_transport_failure_while_writing_info_response_tears_down(tmp_path):
    channel = ContractChannel(1, [ControlRequest("GET", "/info", {}, 1)])
    channel.write_response = lambda response: (_ for _ in ()).throw(ConnectionError("private"))
    session, authority = _session(tmp_path, channel)
    session.open()
    with pytest.raises(ConnectionError):
        session.handle_one()
    assert session.receiver.snapshot().sessions == 0 and channel.closed and authority.closed


def test_transport_closure_during_setup_releases_listeners(tmp_path):
    setup = ControlRequest("SETUP", "/session", {"streams": [
        {"type": 110, "streamConnectionID": 1}, {"type": 111, "streamConnectionID": 2}]}, 1)
    channel = ContractChannel(1, [ControlRequest("GET", "/info", {}, 1), setup])
    session, authority = _session(tmp_path, channel)
    session.open()
    session.handle_one()
    original = channel.write_response
    channel.write_response = lambda response: (_ for _ in ()).throw(ConnectionError("private"))
    with pytest.raises(ConnectionError):
        session.handle_one()
    channel.write_response = original
    snap = session.receiver.snapshot()
    assert (snap.sessions, snap.primary_listeners, snap.secondary_listeners) == (0, 0, 0)
    assert channel.closed and authority.closed and authority.context_closed


def test_missing_response_peer_timeout_and_duplicate_info_request_are_contained(tmp_path):
    channel = ContractChannel(1)
    session, authority = _session(tmp_path, channel)
    session.open()
    with pytest.raises(TransportError, match="peer_disconnected_or_timeout"):
        session.handle_one()  # peer never sends another request
    assert session.receiver.snapshot().sessions == 0 and authority.closed

    channel = ContractChannel(1, [ControlRequest("GET", "/info", {}, 1),
                                  ControlRequest("GET", "/info", {}, 1)])
    session, authority = _session(tmp_path, channel)
    session.open()
    session.handle_one()
    with pytest.raises(SessionError, match="duplicate_info_request"):
        session.handle_one()
    assert session.receiver.snapshot().sessions == 0 and authority.closed


def test_provider_restart_does_not_reuse_stale_authority(tmp_path):
    receiver = Receiver(clear_lab=True)
    first, first_authority = _session(tmp_path, ContractChannel(1), receiver)
    first.open()
    first.close()
    assert first.provider.session_ready() is False
    with pytest.raises(AuthenticationError, match="provider_not_initialized"):
        first.provider.authenticate(2)
    stale, stale_authority = _session(tmp_path, ContractChannel(1), receiver)
    with pytest.raises(AuthenticationError, match="authority_open_failed"):
        stale.open()  # an authority bound to generation 1 cannot open generation 2
    assert stale_authority.opened_generations == [2]
    restarted, authority = _session(tmp_path, ContractChannel(2), receiver)
    restarted.open()
    assert restarted.generation == 2 and authority.opened_generations == [2]
    assert first_authority.opened_generations == [1]
    restarted.close()


def test_repeated_open_close_cycles_and_multiple_close_calls_are_idempotent(tmp_path):
    receiver = Receiver(clear_lab=True)
    for generation in range(1, 31):
        channel = ContractChannel(generation, [ControlRequest("GET", "/info", {}, generation)])
        session, authority = _session(tmp_path, channel, receiver)
        session.open()
        assert session.handle_one().status == 200
        for _ in range(3):
            session.close()
        assert channel.closed and authority.closed and authority.context_closed
        assert receiver.snapshot().sessions == 0
    assert receiver.generation == 30


def test_diagnostics_exclude_session_identifiers_and_provider_text(tmp_path):
    channel = ContractChannel(1, [ControlRequest("GET", "/info", {}, 1)])
    channel.session_identifier = "super-private-session-token"
    session, _ = _session(tmp_path, channel)
    session.open()
    session.handle_one()
    rendered = " ".join(map(repr, (session.trace.events if hasattr(session.trace, "events") else ())))
    rendered += repr(session._handoff) + repr(session.transport) + repr(session.provider)
    assert "super-private-session-token" not in rendered
    session.close()
