"""CL-AUTH-01 M3: Type111 security binding, stream ownership and failure containment.

All keys are generated per test and every frame is sealed with a public AEAD
(ChaCha20-Poly1305). This proves ownership and failure handling only; it says
nothing about the real Type111 key derivation or any Honda/iPhone session.
"""
from __future__ import annotations

import os
from pathlib import Path
import pickle
import shutil
import socket
import subprocess
import sys
import threading

import pytest
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-jmcs"))

from claritylink_jmcs import authentication as auth_module
from claritylink_jmcs.authentication import (AuthenticatedSessionHandoff, AuthorityType,
                                             LabAuthenticationProvider, SessionOrigin, TrustClass,
                                             attest_handoff)
from claritylink_jmcs.media import FramingProfile
from claritylink_jmcs.receiver import Receiver, ReceiverError
from claritylink_jmcs.security import (HandoffSecurityFactory, SecurityError, SecurityProfile,
                                       Type111SecurityGrant)
from claritylink_jmcs.session import ReceiverSession
from claritylink_jmcs.session_transport import ControlRequest
from test_r6b_session_boundary import profile
from test_r6e_auth_transport import ContractAuthority, ContractChannel

SESSION_ID = "contract-1"
STREAM_110, STREAM_111 = 21, 22
SETUP_BOTH = ControlRequest("SETUP", "/session", {"streams": [
    {"type": 110, "streamConnectionID": STREAM_110},
    {"type": 111, "streamConnectionID": STREAM_111}]}, 1)
INFO = ControlRequest("GET", "/info", {}, 1)


def _grant(key, *, generation=1, stream=STREAM_111, session=SESSION_ID,
           profile_name=SecurityProfile.MODERN_CHACHA_SCREEN, synthetic=True):
    return Type111SecurityGrant(profile_name, provenance="generated test context",
                                session_identifier=session, generation=generation,
                                stream_connection_id=stream, key=key, synthetic=synthetic)


class GrantAuthority(ContractAuthority):
    def __init__(self, channel, grant):
        super().__init__(channel)
        self.grant = grant

    def open(self, generation):
        self.opened_generations.append(generation)
        return AuthenticatedSessionHandoff(
            self.channel.session_identifier, generation, SessionOrigin.AUTHENTICATED_LAB,
            self.identity, self.channel, self.grant, authority_type=self.authority_type,
            authenticated=True)


def _open(tmp_path, grant, requests=(INFO, SETUP_BOTH), *, allow_test_security=True, setup=True):
    channel = ContractChannel(1, list(requests))
    authority = GrantAuthority(channel, grant)
    receiver = Receiver(framing_profile=FramingProfile.CURRENT_IOS_TYPE111)
    session = ReceiverSession(LabAuthenticationProvider(authority=authority), receiver,
                              profile(tmp_path), allow_test_security=allow_test_security)
    session.open()
    session.handle_one()  # /info
    if setup:
        session.handle_one()  # SETUP
    return session, receiver, channel, authority


def _frame(key, body, *, counter=0, opcode=0, timestamp=1):
    header = bytearray(128)
    header[:4] = (len(body) + 16).to_bytes(4, "little")
    header[4] = opcode
    header[8:16] = timestamp.to_bytes(8, "little")
    nonce = b"\x00" * 4 + counter.to_bytes(8, "little")
    return bytes(header), ChaCha20Poly1305(key).encrypt(nonce, body, bytes(header))


def _connected(receiver, generation=1):
    client = socket.create_connection(("127.0.0.1", receiver.secondary.port), timeout=1)
    receiver.accept_secondary(generation)
    return client


def _bound(handoff_trust_key, **grant_kwargs):
    key = handoff_trust_key
    channel = ContractChannel(1)
    handoff = AuthenticatedSessionHandoff(
        channel.session_identifier, 1, SessionOrigin.AUTHENTICATED_LAB, "o", channel,
        _grant(key, **grant_kwargs), authority_type=AuthorityType.GENUINE_HARDWARE,
        authenticated=True)
    return handoff, HandoffSecurityFactory(handoff, allow_test_profiles=True)


# ---- grant construction ---------------------------------------------------

@pytest.mark.parametrize("kwargs", [
    {"profile_name": SecurityProfile.CLEAR_GENERATED_LAB},
    {"profile_name": "ROT13_SCREEN"},
    {"profile_name": "modern_chacha_screen"},
    {"generation": True}, {"generation": 0}, {"generation": 1 << 64},
    {"stream": 0}, {"stream": False}, {"session": ""}, {"key": b"short"},
    {"key": "x" * 32}, {"synthetic": 1}])
def test_invalid_or_peer_chosen_profile_cannot_build_a_grant(kwargs):
    base = dict(profile_name=SecurityProfile.MODERN_CHACHA_SCREEN, generation=1, stream=2,
                session="s", key=os.urandom(32), synthetic=True)
    base.update(kwargs)
    with pytest.raises(SecurityError, match="invalid_security_grant"):
        _grant(**{("key" if k == "key" else k): v for k, v in base.items()})


def test_grant_repr_pickle_and_key_zeroing_never_expose_the_key():
    key = os.urandom(32)
    grant = _grant(key)
    assert key.hex() not in repr(grant) and "key" not in repr(grant).lower()
    with pytest.raises(SecurityError, match="security_grant_not_serializable"):
        pickle.dumps(grant)
    released = grant.release_key()
    assert released == key and not grant.usable
    assert bytes(grant._key) == b"\x00" * 32
    with pytest.raises(SecurityError, match="security_grant_consumed"):
        grant.release_key()


def test_factory_requires_a_real_grant_and_is_single_use():
    channel = ContractChannel(1)
    bare = AuthenticatedSessionHandoff("s", 1, SessionOrigin.AUTHENTICATED_LAB, "o", channel,
                                       object(), authority_type=AuthorityType.GENUINE_HARDWARE,
                                       authenticated=True)
    with pytest.raises(SecurityError, match="security_grant_required"):
        HandoffSecurityFactory(bare)
    handoff, factory = _bound(os.urandom(32))
    factory()
    with pytest.raises(SecurityError, match="security_grant_consumed"):
        factory()


# ---- binding checks at open ----------------------------------------------

@pytest.mark.parametrize("grant_kwargs,open_args,code", [
    ({"generation": 2}, (1, STREAM_111), "security_grant_binding_mismatch"),
    ({"stream": 99}, (1, STREAM_111), "security_grant_binding_mismatch"),
    ({"session": "other-session"}, (1, STREAM_111), "security_grant_binding_mismatch"),
    ({}, (2, STREAM_111), "security_grant_binding_mismatch"),
    ({}, (1, 99), "security_grant_binding_mismatch"),
    ({}, (True, STREAM_111), "security_grant_binding_mismatch"),
    ({"profile_name": SecurityProfile.LEGACY_AES_SCREEN}, (1, STREAM_111),
     "security_profile_unimplemented"),
])
def test_grant_must_match_parent_generation_session_and_stream(grant_kwargs, open_args, code):
    handoff, factory = _bound(os.urandom(32), **grant_kwargs)
    provider = factory()
    with pytest.raises(SecurityError, match=code):
        provider.open(*open_args)
    with pytest.raises(SecurityError, match="stale_security_context"):
        provider.unprotect(1, b"x" * 16, bytes(128))


def test_synthetic_grant_denied_unless_test_profiles_enabled():
    channel = ContractChannel(1)
    handoff = AuthenticatedSessionHandoff(
        channel.session_identifier, 1, SessionOrigin.AUTHENTICATED_LAB, "o", channel,
        _grant(os.urandom(32)), authority_type=AuthorityType.GENUINE_HARDWARE, authenticated=True)
    with pytest.raises(SecurityError, match="synthetic_security_not_enabled"):
        HandoffSecurityFactory(handoff)().open(1, STREAM_111)


def test_non_synthetic_grant_needs_attested_parent(monkeypatch):
    handoff, factory = _bound(os.urandom(32), synthetic=False)
    with pytest.raises(SecurityError, match="security_authority_unattested"):
        factory().open(1, STREAM_111)
    # Even a caller-supplied "attested" capability cannot satisfy the check.
    assert handoff.trust is TrustClass.UNVERIFIED_HARDWARE

    class Reviewed:
        def verify(self, h): return True

    monkeypatch.setattr(auth_module, "_TRUSTED_ATTESTATION_VERIFIERS", (Reviewed,))
    handoff, factory = _bound(os.urandom(32), synthetic=False)
    attest_handoff(handoff, Reviewed())
    provider = factory()
    provider.open(1, STREAM_111)
    provider.close()


def test_closed_parent_denies_open_and_unprotect_and_zeroes_key():
    key = os.urandom(32)
    handoff, factory = _bound(key)
    grant = handoff.security_context
    provider = factory()
    provider.open(1, STREAM_111)
    header, body = _frame(key, b"abc")
    assert provider.unprotect(1, body, header) == b"abc"
    handoff.close()
    with pytest.raises(SecurityError, match="stale_security_context"):
        provider.unprotect(1, *reversed(_frame(key, b"abc", counter=1)))
    assert bytes(grant._key) == b"\x00" * 32
    handoff2, factory2 = _bound(os.urandom(32))
    handoff2.close()
    with pytest.raises(SecurityError, match="security_grant_unavailable"):
        factory2().open(1, STREAM_111)


# ---- protected-frame failure modes ---------------------------------------

def test_replay_tag_failure_truncation_oversize_and_counter_exhaustion():
    key = os.urandom(32)
    handoff, factory = _bound(key)
    provider = factory()
    provider.open(1, STREAM_111)
    header, body = _frame(key, b"frame-0")
    assert provider.unprotect(1, body, header) == b"frame-0"
    with pytest.raises(SecurityError, match="screen_authentication_failed"):
        provider.unprotect(1, body, header)  # replay of a consumed counter
    tampered = bytearray(body)
    tampered[0] ^= 1
    h1, b1 = _frame(key, b"frame-1", counter=1)
    with pytest.raises(SecurityError, match="screen_authentication_failed"):
        provider.unprotect(1, bytes(tampered), header)
    wrong_header = bytearray(h1)
    wrong_header[20] ^= 1
    with pytest.raises(SecurityError, match="screen_authentication_failed"):
        provider.unprotect(1, b1, bytes(wrong_header))
    # Failed attempts must not advance the nonce: the legitimate next frame still opens.
    assert provider.unprotect(1, b1, h1) == b"frame-1"
    for bad_body, bad_header in ((b"x" * 15, h1), (b"x" * (8 * 1024 * 1024 + 1), h1),
                                 (b1, h1[:127]), (b1, "text"), ("text", h1)):
        with pytest.raises(SecurityError, match="invalid_protected_frame"):
            provider.unprotect(1, bad_body, bad_header)
    with pytest.raises(SecurityError, match="stale_security_context"):
        provider.unprotect(2, b1, h1)  # wrong generation
    inner = provider._inner
    inner.counter = (1 << 64) - 1
    last_h, last_b = _frame(key, b"last", counter=(1 << 64) - 1)
    assert provider.unprotect(1, last_b, last_h) == b"last"
    with pytest.raises(SecurityError, match="invalid_protected_frame"):
        provider.unprotect(1, last_b, last_h)  # exhausted: refuses rather than wrap
    provider.close()
    with pytest.raises(SecurityError, match="stale_security_context"):
        provider.unprotect(1, last_b, last_h)


# ---- receiver-level ownership and containment -----------------------------

def test_missing_security_context_denies_type111_and_preserves_type110(tmp_path):
    channel = ContractChannel(1, [INFO, SETUP_BOTH])
    receiver = Receiver(framing_profile=FramingProfile.CURRENT_IOS_TYPE111)
    session = ReceiverSession(LabAuthenticationProvider(authority=ContractAuthority(channel)),
                              receiver, profile(tmp_path), allow_test_security=True)
    session.open()
    session.handle_one()
    response = session.handle_one()
    assert [s["type"] for s in response.body["streams"]] == [110]
    snap = receiver.snapshot()
    assert (snap.primary_listeners, snap.secondary_listeners) == (1, 0)
    assert "SECONDARY_ROLLBACK" in receiver.events
    session.close()


@pytest.mark.parametrize("grant_kwargs,allow", [
    ({"stream": 99}, True), ({"generation": 2}, True), ({"session": "other"}, True),
    ({"profile_name": SecurityProfile.LEGACY_AES_SCREEN}, True), ({}, False),
    ({"synthetic": False}, True)])
def test_setup_with_bad_grant_rolls_back_only_type111(tmp_path, grant_kwargs, allow):
    session, receiver, channel, _ = _open(tmp_path, _grant(os.urandom(32), **grant_kwargs),
                                          allow_test_security=allow)
    assert [s["type"] for s in channel.responses[-1].body["streams"]] == [110]
    snap = receiver.snapshot()
    assert (snap.sessions, snap.primary_listeners, snap.secondary_listeners,
            snap.security_contexts) == (1, 1, 0, 1)  # one context = the Type110 placeholder
    session.close()
    assert receiver.snapshot().sessions == 0


def test_valid_grant_establishes_type111_and_duplicate_setup_is_rejected(tmp_path):
    session, receiver, channel, _ = _open(tmp_path, _grant(os.urandom(32)))
    assert [s["type"] for s in channel.responses[-1].body["streams"]] == [110, 111]
    with pytest.raises(ReceiverError, match="duplicate_stream_connection_id"):
        receiver.setup({"streams": [{"type": 111, "streamConnectionID": STREAM_111}]}, 1)
    port, listener = receiver.secondary.port, receiver.secondary
    # A second Type111 with a fresh ID falls back to the live resources unchanged.
    fallback = receiver.setup({"streams": [{"type": 111, "streamConnectionID": 77}]}, 1)
    assert [(s["type"], s["dataPort"]) for s in fallback.fields["streams"]][-1] == (111, port)
    assert receiver.secondary is listener and receiver.secondary_id == STREAM_111
    assert receiver.events[-1] == "SECONDARY_ROLLBACK"
    session.close()


def test_type110_and_type111_cannot_share_a_stream_identity(tmp_path):
    channel = ContractChannel(1, [INFO, ControlRequest("SETUP", "/session", {"streams": [
        {"type": 110, "streamConnectionID": 5}, {"type": 111, "streamConnectionID": 5}]}, 1)])
    session = ReceiverSession(
        LabAuthenticationProvider(authority=GrantAuthority(channel, _grant(os.urandom(32), stream=5))),
        Receiver(framing_profile=FramingProfile.CURRENT_IOS_TYPE111), profile(tmp_path),
        allow_test_security=True)
    session.open()
    session.handle_one()
    with pytest.raises(Exception):
        session.handle_one()
    assert session.receiver.snapshot().sessions == 0
    session.close()


def test_forged_frame_tears_down_only_type111_and_grant_is_not_reusable(tmp_path):
    key = os.urandom(32)
    session, receiver, channel, authority = _open(tmp_path, _grant(key))
    client = _connected(receiver)
    try:
        header, body = _frame(key, b"\x00\x00\x00\x01" + b"junk", counter=0)
        tampered = bytearray(body)
        tampered[-1] ^= 1
        client.sendall(header + bytes(tampered))
        with pytest.raises(ReceiverError, match="screen_authentication_failed"):
            receiver.receive_secondary_frame(1)
    finally:
        client.close()
    snap = receiver.snapshot()
    assert (snap.sessions, snap.primary_listeners, snap.secondary_listeners) == (1, 1, 0)
    assert receiver.frames == 0 and receiver.security is None and receiver.decoder is None
    assert receiver.generation == 1 and session.generation == 1  # parent unaffected
    # Reconnect cannot reuse the consumed grant: Type111 is refused, Type110 preserved.
    retry = receiver.setup({"streams": [{"type": 111, "streamConnectionID": STREAM_111}]}, 1)
    assert [s["type"] for s in retry.fields["streams"]] == [110]
    assert receiver.secondary is None and receiver.security is None
    assert receiver.events[-1] == "SECONDARY_ROLLBACK"
    assert bytes(authority.grant._key) == b"\x00" * 32
    session.close()


@pytest.mark.parametrize("size", [0, 8 * 1024 * 1024 + 1])
def test_malformed_length_header_tears_down_only_type111(tmp_path, size):
    session, receiver, _, _ = _open(tmp_path, _grant(os.urandom(32)))
    client = _connected(receiver)
    try:
        header = bytearray(128)
        header[:4] = size.to_bytes(4, "little")
        client.sendall(bytes(header))
        with pytest.raises(ReceiverError, match="invalid_body_length"):
            receiver.receive_secondary_frame(1)
    finally:
        client.close()
    snap = receiver.snapshot()
    assert (snap.primary_listeners, snap.secondary_listeners) == (1, 0)
    session.close()


def test_truncated_media_disconnect_tears_down_only_type111(tmp_path):
    key = os.urandom(32)
    session, receiver, _, _ = _open(tmp_path, _grant(key))
    client = _connected(receiver)
    header, body = _frame(key, b"abcdef")
    client.sendall(header + body[:5])
    client.close()
    with pytest.raises(ReceiverError):
        receiver.receive_secondary_frame(1)
    snap = receiver.snapshot()
    assert (snap.primary_listeners, snap.secondary_listeners) == (1, 0)
    session.close()


def _avcc(sps=b"\x67\x42\x00\x1e", pps=b"\x68\xce"):
    return (b"xxxxavcC" + bytes([1, 66, 0, 30, 255, 0xE1]) + len(sps).to_bytes(2, "big") + sps +
            b"\x01" + len(pps).to_bytes(2, "big") + pps)


def test_video_config_replacement_then_malformed_config_contains_failure(tmp_path):
    key = os.urandom(32)
    session, receiver, _, _ = _open(tmp_path, _grant(key))
    client = _connected(receiver)
    try:
        def send_config(config):
            header = bytearray(128)
            header[:4] = len(config).to_bytes(4, "little")
            header[4] = 1
            client.sendall(bytes(header) + config)
        send_config(_avcc())
        receiver.receive_secondary_frame(1)
        first = receiver.codec_prefix
        send_config(_avcc(sps=b"\x67\x42\x00\x28"))
        receiver.receive_secondary_frame(1)
        assert receiver.codec_prefix != first and receiver.secondary is not None
        send_config(b"xxxxavcC\x01\x42")
        with pytest.raises(Exception):
            receiver.receive_secondary_frame(1)
    finally:
        client.close()
    snap = receiver.snapshot()
    assert (snap.sessions, snap.primary_listeners, snap.secondary_listeners) == (1, 1, 0)
    assert receiver.codec_prefix == b""
    session.close()


def test_type111_teardown_leaves_type110_and_parent_active_and_is_idempotent(tmp_path):
    session, receiver, _, _ = _open(tmp_path, _grant(os.urandom(32)))
    for _ in range(3):
        receiver.teardown_secondary(1)
    snap = receiver.snapshot()
    assert (snap.sessions, snap.primary_listeners, snap.secondary_listeners,
            snap.decoders) == (1, 1, 0, 1)
    assert session.trust is TrustClass.UNVERIFIED_HARDWARE
    session.close()


def test_concurrent_teardown_from_all_owners_leaves_no_resources(tmp_path):
    for _ in range(10):
        session, receiver, _, _ = _open(tmp_path, _grant(os.urandom(32)))
        errors = []

        def run(action):
            try:
                action()
            except Exception as exc:  # noqa: BLE001 - recording any escape
                errors.append(type(exc).__name__)

        threads = [threading.Thread(target=run, args=(a,)) for a in (
            lambda: receiver.teardown_secondary(1), lambda: receiver.teardown(1),
            session.close, lambda: session._handoff and session._handoff.close())]
        for t in threads:
            t.start()
        for t in threads:
            t.join(10)
        assert not errors
        assert receiver.snapshot() == type(receiver.snapshot())(0, 0, 0, 0, 0, 0, 0)


def test_repeated_start_stop_cycles_use_fresh_grants_without_leaks(tmp_path):
    receiver = Receiver(framing_profile=FramingProfile.CURRENT_IOS_TYPE111)
    for generation in range(1, 21):
        key = os.urandom(32)
        channel = ContractChannel(generation, [
            ControlRequest("GET", "/info", {}, generation),
            ControlRequest("SETUP", "/session", {"streams": [
                {"type": 111, "streamConnectionID": 1000 + generation}]}, generation)])
        grant = _grant(key, generation=generation, stream=1000 + generation,
                       session=channel.session_identifier)
        session = ReceiverSession(
            LabAuthenticationProvider(authority=GrantAuthority(channel, grant)), receiver,
            profile(tmp_path), allow_test_security=True)
        session.open()
        session.handle_one()
        assert [s["type"] for s in session.handle_one().body["streams"]] == [111]
        session.close()
        assert bytes(grant._key) == b"\x00" * 32
        assert receiver.snapshot().sessions == 0 and receiver.security is None


def test_diagnostics_never_contain_key_material(tmp_path):
    key = os.urandom(32)
    session, receiver, channel, _ = _open(tmp_path, _grant(key))
    client = _connected(receiver)
    header, body = _frame(key, b"abc")
    bad = bytearray(body)
    bad[0] ^= 1
    client.sendall(header + bytes(bad))
    with pytest.raises(ReceiverError) as error:
        receiver.receive_secondary_frame(1)
    client.close()
    rendered = " ".join(map(str, receiver.events)) + repr(error.value) + repr(session._handoff)
    rendered += repr(error.value.__cause__) + repr(session.transport)
    assert key.hex() not in rendered and repr(key) not in rendered
    session.close()


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg required for host decode")
def test_grant_bound_provider_decodes_a_sealed_generated_frame(tmp_path):
    key = os.urandom(32)
    session, receiver, _, _ = _open(tmp_path, _grant(key))
    access_unit = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=32x32:r=1",
         "-frames:v", "1", "-c:v", "libx264", "-f", "h264", "pipe:1"],
        capture_output=True, timeout=10, check=True).stdout
    client = _connected(receiver)
    try:
        header, body = _frame(key, access_unit)
        client.sendall(header + body)
        assert receiver.receive_secondary_frame(1).startswith(b"\x89PNG")
    finally:
        client.close()
    assert receiver.frames == 1
    session.close()
    assert receiver.snapshot().sessions == 0
