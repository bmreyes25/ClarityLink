"""CL-AUTH-01 M4: LIVI bridge drift guards and bodyless-request handling.

These tests compare ClarityLink's bridge against the recorded patch text only.
They do not run LIVI, touch hardware or involve any phone.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import re
import socket
import sys
import uuid

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-jmcs"))

from claritylink_jmcs.auth_providers import livi_ipc
from claritylink_jmcs.auth_providers.livi_ipc import (LiviIpcError, LiviUnixSocketBridge,
                                                      _decode_control_plist)

PATCH = ROOT / "third_party" / "patches" / "livi" / "0001-control-delegate-dispatch-and-bounds.patch"
CONTRACT = ROOT / "research" / "runtime" / "r6h-livi-patch-contract.md"


def _patch_text() -> str:
    return PATCH.read_text(encoding="utf-8")


def test_recorded_patch_hash_matches_the_documented_contract():
    digest = hashlib.sha256(PATCH.read_bytes()).hexdigest()
    assert digest in CONTRACT.read_text(encoding="utf-8")


def test_python_bridge_constants_match_the_recorded_patch_client():
    text = _patch_text()
    assert re.search(r"const VERSION = (\d+)", text).group(1) == str(livi_ipc.PROTOCOL_VERSION)
    assert re.search(r"const MAX_FRAME_BYTES = ([\d_]+)", text).group(1).replace("_", "") == \
        str(livi_ipc.MAX_FRAME_BYTES)
    assert re.search(r"const PROOF = '([^']+)'", text).group(1) == livi_ipc.AUTH_STATE_PROOF
    assert re.search(r"const PLIST_TYPE = '([^']+)'", text).group(1) == livi_ipc.PLIST_CONTENT_TYPE
    assert "body.length > 1_000_000" in text and livi_ipc.MAX_PLIST_BYTES == 1_000_000
    assert "frame.length !== 7" in text and "'session_ready'" in text


def test_patch_request_frame_layout_matches_the_python_reader():
    text = "\n".join(line[1:] if line.startswith("+") else line for line in _patch_text().splitlines())
    layout = re.search(r"await this\.send\(\[\s*VERSION,\s*'request',\s*this\.generation,\s*requestId,"
                       r"\s*request\.method,\s*request\.path,\s*request\.headers\['content-type'\] \?\? null,"
                       r"\s*request\.body\.toString\('base64'\)", text)
    assert layout is not None  # eight fields: version, kind, generation, id, method, path, type, body


def _bridge_pair():
    ours, peer = socket.socketpair()
    session = str(uuid.uuid4())
    return LiviUnixSocketBridge(ours, bytearray(), 1, session), peer


def _send(peer, method, url, content_type, body: bytes):
    frame = [1, "request", 1, str(uuid.uuid4()), method, url, content_type,
             base64.b64encode(body).decode()]
    peer.sendall((json.dumps(frame) + "\n").encode())


@pytest.mark.parametrize("method,url,expected_path", [
    ("GET", "rtsp://local/info", "/info"), ("SETUP", "rtsp://local/session", "/session")])
def test_bodyless_request_without_content_type_is_accepted_as_empty_mapping(method, url, expected_path):
    bridge, peer = _bridge_pair()
    try:
        _send(peer, method, url, None, b"")
        request = bridge.read_request(2)
        assert (request.method, request.path, dict(request.body)) == (method, expected_path, {})
    finally:
        bridge.close()
        peer.close()


def test_malformed_nonempty_plist_and_wrong_content_type_still_close_the_bridge():
    for body, content_type, code in ((b"not a plist", livi_ipc.PLIST_CONTENT_TYPE, "malformed_control_plist"),
                                     (b"", "text/plain", "unsupported_control_content_type")):
        bridge, peer = _bridge_pair()
        try:
            _send(peer, "GET", "rtsp://local/info", content_type, body)
            with pytest.raises(LiviIpcError, match=code):
                bridge.read_request(2)
            assert not bridge.authenticated
        finally:
            peer.close()


def test_decode_control_plist_empty_input_is_bounded_and_nothing_else_changes():
    assert _decode_control_plist("") == {}
    for bad in (None, 5, "!!!notbase64"):
        with pytest.raises(LiviIpcError):
            _decode_control_plist(bad)
