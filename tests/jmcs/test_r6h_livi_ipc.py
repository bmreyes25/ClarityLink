from __future__ import annotations

import base64
import json
import os
import plistlib
import socket
import threading
import tempfile
import uuid
from pathlib import Path

import pytest

from claritylink_jmcs.auth_providers.livi_ipc import (
    AUTH_STATE_PROOF, LiviIpcError, LiviUnixSocketBridgeFactory, PROTOCOL_VERSION,
    _decode_control_plist, _encode_control_plist,
)
from claritylink_jmcs.auth_providers.livi import LiviAuthority
from claritylink_jmcs.authentication import LabAuthenticationProvider
from claritylink_jmcs.receiver import Receiver
from claritylink_jmcs.session import ReceiverSession
from claritylink_jmcs.session_transport import ControlResponse, TransportError
from test_r6b_session_boundary import profile


def _frame(sock: socket.socket):
    data = bytearray()
    while b"\n" not in data:
        data.extend(sock.recv(4096))
    line, _, rest = data.partition(b"\n")
    assert not rest
    return json.loads(line)


def _connect_local(path: str) -> socket.socket:
    peer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    for attempt in range(100):
        try:
            peer.connect(path)
            return peer
        except (FileNotFoundError, ConnectionRefusedError):
            if attempt == 99:
                peer.close()
                raise
            threading.Event().wait(0.005)
    raise AssertionError("socket connection retry exhausted")


def test_private_unix_bridge_roundtrip_and_redaction():
    parent = tempfile.mkdtemp(prefix="clh-")
    os.chmod(parent, 0o700)
    path = os.path.join(parent, "livi.sock")
    factory = LiviUnixSocketBridgeFactory(path, accept_timeout=3)
    outcome = []

    def accept():
        outcome.append(factory.open_authenticated(7))

    worker = threading.Thread(target=accept)
    worker.start()
    for _ in range(100):
        if os.path.exists(path):
            break
        threading.Event().wait(0.01)
    peer = _connect_local(path)
    session_id = str(uuid.uuid4())
    peer.sendall((json.dumps([PROTOCOL_VERSION, "authenticated", session_id, AUTH_STATE_PROOF]) + "\n").encode())
    ready = _frame(peer)
    assert ready == [PROTOCOL_VERSION, "session_ready", 7]
    worker.join(3)
    bridge = outcome[0]
    request_id = str(uuid.uuid4())
    body = plistlib.dumps({"request": True, "UDID": "must-not-cross",
                           "deviceID": "private-phone-id", "streams": []}, fmt=plistlib.FMT_BINARY)
    peer.sendall((json.dumps([PROTOCOL_VERSION, "request", 7, request_id, "GET", "rtsp://local/info", "application/x-apple-binary-plist", base64.b64encode(body).decode()]) + "\n").encode())
    req = bridge.read_request(2)
    assert req.path == "/info" and req.body == {"request": True, "streams": []}
    response_body = {"deviceID": "stable-receiver-id", "bluetoothIDs": ["stable-receiver-id"], "ok": True}
    bridge.write_response(ControlResponse(200, response_body, 7))
    response = _frame(peer)
    assert response[:6] == [PROTOCOL_VERSION, "response", 7, request_id, 200, "application/x-apple-binary-plist"]
    response_raw = base64.b64decode(response[6], validate=True)
    assert plistlib.loads(response_raw) == response_body
    bridge.close()
    factory.close()
    peer.close()
    assert not os.path.exists(path)
    os.rmdir(parent)


def test_livi_ipc_rejects_duplicate_keys_and_unexpected_plist_types():
    from claritylink_jmcs.auth_providers.livi_ipc import _read_frame
    left, right = socket.socketpair()
    try:
        right.sendall(b'{"a":1,"a":2}\n')
        with pytest.raises(TransportError, match="malformed_bridge_frame"):
            _read_frame(left, 1, bytearray())
    finally:
        left.close(); right.close()


def test_livi_ipc_timeout_oversize_stale_generation_and_disconnect():
    from claritylink_jmcs.auth_providers.livi_ipc import _read_frame

    timeout_dir = tempfile.mkdtemp(prefix="clh-")
    os.chmod(timeout_dir, 0o700)
    timeout_path = os.path.join(timeout_dir, "timeout.sock")
    timeout_factory = LiviUnixSocketBridgeFactory(timeout_path, accept_timeout=0.1)
    with pytest.raises(TimeoutError):
        timeout_factory.open_authenticated(1)
    assert not os.path.exists(timeout_path)
    os.rmdir(timeout_dir)

    version_dir = tempfile.mkdtemp(prefix="clh-")
    os.chmod(version_dir, 0o700)
    version_path = os.path.join(version_dir, "version.sock")
    version_factory = LiviUnixSocketBridgeFactory(version_path, accept_timeout=2)
    version_errors = []
    version_worker = threading.Thread(target=lambda: _open_factory(version_factory, 1, [], version_errors))
    version_worker.start()
    peer = _connect_local(version_path)
    peer.sendall((json.dumps([2, "authenticated", str(uuid.uuid4()), AUTH_STATE_PROOF]) + "\n").encode())
    version_worker.join(3)
    assert version_errors == ["LiviIpcError"]
    peer.close()
    assert not os.path.exists(version_path)
    os.rmdir(version_dir)

    class OversizedSocket:
        def recv(self, size):
            return b"x" * size
        def settimeout(self, _timeout):
            pass
    with pytest.raises(LiviIpcError, match="bridge_frame_too_large"):
        _read_frame(OversizedSocket(), 2, bytearray())

    parent = tempfile.mkdtemp(prefix="clh-")
    os.chmod(parent, 0o700)
    path = os.path.join(parent, "bridge.sock")
    factory = LiviUnixSocketBridgeFactory(path, accept_timeout=3)
    opened, errors = [], []
    worker = threading.Thread(target=lambda: _open_factory(factory, 4, opened, errors))
    worker.start()
    for _ in range(100):
        if os.path.exists(path):
            break
        threading.Event().wait(0.005)
    peer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    peer.connect(path)
    peer.sendall((json.dumps([1, "authenticated", str(uuid.uuid4()), AUTH_STATE_PROOF]) + "\n").encode())
    _frame(peer)
    worker.join(3)
    peer.sendall((json.dumps([1, "request", 3, str(uuid.uuid4()), "GET", "/info", None,
                              base64.b64encode(plistlib.dumps({})).decode()]) + "\n").encode())
    with pytest.raises(LiviIpcError, match="invalid_bridge_request"):
        opened[0].read_request(2)
    opened[0].close(); opened[0].close(); factory.close(); peer.close()
    assert not os.path.exists(path)
    os.rmdir(parent)


def test_livi_ipc_rejects_duplicate_request_ids():
    parent = tempfile.mkdtemp(prefix="clh-")
    os.chmod(parent, 0o700)
    path = os.path.join(parent, "bridge.sock")
    factory = LiviUnixSocketBridgeFactory(path, accept_timeout=3)
    opened, errors = [], []
    worker = threading.Thread(target=lambda: _open_factory(factory, 11, opened, errors))
    worker.start()
    peer = _connect_local(path)
    peer.sendall((json.dumps([1, "authenticated", str(uuid.uuid4()), AUTH_STATE_PROOF]) + "\n").encode())
    assert _frame(peer) == [1, "session_ready", 11]
    worker.join(3)
    bridge = opened[0]
    req_id = str(uuid.uuid4())
    encoded = base64.b64encode(plistlib.dumps({})).decode()
    request = [1, "request", 11, req_id, "GET", "/info", None, encoded]
    peer.sendall((json.dumps(request) + "\n").encode())
    assert bridge.read_request(2).generation == 11
    bridge.write_response(ControlResponse(200, {}, 11))
    _frame(peer)
    peer.sendall((json.dumps(request) + "\n").encode())
    with pytest.raises(LiviIpcError, match="invalid_bridge_request"):
        bridge.read_request(2)
    peer.close()
    bridge.close(); factory.close()
    assert not bridge.authenticated and not os.path.exists(path)
    os.rmdir(parent)


def test_livi_ipc_propagates_peer_disconnect():
    parent = tempfile.mkdtemp(prefix="clh-")
    os.chmod(parent, 0o700)
    path = os.path.join(parent, "bridge.sock")
    factory = LiviUnixSocketBridgeFactory(path, accept_timeout=3)
    opened, errors = [], []
    worker = threading.Thread(target=lambda: _open_factory(factory, 12, opened, errors))
    worker.start()
    peer = _connect_local(path)
    peer.sendall((json.dumps([1, "authenticated", str(uuid.uuid4()), AUTH_STATE_PROOF]) + "\n").encode())
    assert _frame(peer) == [1, "session_ready", 12]
    worker.join(3)
    bridge = opened[0]
    peer.close()
    with pytest.raises(EOFError):
        bridge.read_request(2)
    assert not bridge.authenticated
    factory.close()
    assert not os.path.exists(path)
    os.rmdir(parent)


def test_synthetic_livi_info_and_setup_reach_receiver_session_once(tmp_path: Path):
    parent = tempfile.mkdtemp(prefix="clh-")
    os.chmod(parent, 0o700)
    path = os.path.join(parent, "livi.sock")
    factory = LiviUnixSocketBridgeFactory(path, accept_timeout=4)
    provider = LabAuthenticationProvider(authority=LiviAuthority(
        bridge_factory=factory, explicitly_authorized=True,
    ))
    receiver = Receiver(clear_lab=True)
    session = ReceiverSession(provider, receiver, profile(tmp_path))
    open_errors = []
    opener = threading.Thread(target=lambda: _open_session(session, open_errors))
    opener.start()
    for _ in range(200):
        if os.path.exists(path):
            break
        threading.Event().wait(0.01)
    peer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    peer.connect(path)
    peer.sendall((json.dumps([1, "authenticated", str(uuid.uuid4()), AUTH_STATE_PROOF]) + "\n").encode())
    assert _frame(peer) == [1, "session_ready", 1]
    opener.join(4)
    assert not open_errors

    for request_id, method, url, body in (
        (str(uuid.uuid4()), "GET", "rtsp://local/info", {}),
        (str(uuid.uuid4()), "SETUP", "rtsp://local/session", {"streams": [{"type": 110, "streamConnectionID": 1234}]}),
    ):
        encoded_body = plistlib.dumps(body, fmt=plistlib.FMT_BINARY)
        peer.sendall((json.dumps([1, "request", 1, request_id, method, url, "application/x-apple-binary-plist", base64.b64encode(encoded_body).decode()]) + "\n").encode())
        response_thread = threading.Thread(target=session.handle_one)
        response_thread.start()
        response = _frame(peer)
        response_thread.join(4)
        assert response[0:5] == [1, "response", 1, request_id, 200]
        decoded = _decode_control_plist(response[6])
        if method == "GET":
            assert "displays" in decoded
            full_info = plistlib.loads(base64.b64decode(response[6], validate=True))
            assert full_info["deviceID"] == profile(tmp_path).identity.device_id
        else:
            assert decoded["streams"][0]["type"] == 110
    session.close()
    peer.close()
    assert receiver.snapshot().sessions == 0
    assert not os.path.exists(path)
    os.rmdir(parent)


def _open_session(session, errors):
    try:
        session.open()
    except Exception as exc:
        errors.append(type(exc).__name__)


def test_livi_unix_bridge_100_synthetic_connect_close_cycles():
    parent = tempfile.mkdtemp(prefix="clh-")
    os.chmod(parent, 0o700)
    path = os.path.join(parent, "l.sock")
    for generation in range(1, 101):
        factory = LiviUnixSocketBridgeFactory(path, accept_timeout=3)
        opened = []
        errors = []
        worker = threading.Thread(target=lambda: _open_factory(factory, generation, opened, errors))
        worker.start()
        for _ in range(100):
            if os.path.exists(path):
                break
            threading.Event().wait(0.005)
        peer = _connect_local(path)
        peer.sendall((json.dumps([1, "authenticated", str(uuid.uuid4()), AUTH_STATE_PROOF]) + "\n").encode())
        assert _frame(peer) == [1, "session_ready", generation]
        worker.join(3)
        assert not errors and opened
        opened[0].close()
        factory.close()
        peer.close()
        assert not os.path.exists(path)
    os.rmdir(parent)


def _open_factory(factory, generation, opened, errors):
    try:
        opened.append(factory.open_authenticated(generation))
    except Exception as exc:
        errors.append(type(exc).__name__)
