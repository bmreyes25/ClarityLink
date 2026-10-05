"""Bounded, same-user Unix-domain bridge for the patched LIVI delegate.

Wire protocol: newline-delimited JSON arrays with fixed positions (v1). Binary
plists travel as base64; no arbitrary process, socket, or crypto state crosses
the boundary. See research/runtime/r6h-livi-bridge-protocol.md.
"""
from __future__ import annotations

import base64
import binascii
import json
import os
from pathlib import Path
import plistlib
import socket
import stat
import sys
import struct
import uuid

from ..session_transport import (
    ControlRequest,
    ControlResponse,
    MAX_REQUEST_BYTES,
    TransportError,
    validate_control_request,
)

PROTOCOL_VERSION = 1
MAX_FRAME_BYTES = 1_400_000
MAX_PLIST_BYTES = MAX_REQUEST_BYTES
MAX_PENDING_IDS = 4096
AUTH_STATE_PROOF = "mfi_auth_setup_response_then_pair_verify_then_next_control_request"
PLIST_CONTENT_TYPE = "application/x-apple-binary-plist"
_PRIVATE_FIELDS = {
    "name", "deviceid", "macaddress", "btmac", "wifiaddress", "udid",
    "serialnumber", "appleid", "account", "pairingid", "privatekey",
    "certificate", "certificatedata", "challenge", "authchallenge",
    "authdata", "pairingdata", "pairings", "key", "keys", "secret",
    "password", "token", "sessionkey", "encryptionkey",
}


class LiviIpcError(TransportError):
    """Stable, redacted bridge errors."""


def _is_uuid(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 36:
        return False
    try:
        return str(uuid.UUID(value)) == value.lower()
    except (ValueError, AttributeError):
        return False


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _encode_frame(value: list[object]) -> bytes:
    try:
        frame = json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("ascii") + b"\n"
    except (TypeError, ValueError, OverflowError):
        raise LiviIpcError("bridge_frame_encode_failed") from None
    if len(frame) > MAX_FRAME_BYTES:
        raise LiviIpcError("bridge_frame_too_large")
    return frame


def _send_frame(sock: socket.socket, value: list[object]) -> None:
    try:
        sock.sendall(_encode_frame(value))
    except (OSError, LiviIpcError):
        raise LiviIpcError("bridge_write_failed") from None


def _read_frame(sock: socket.socket, timeout: float, pending: bytearray) -> list[object]:
    if not 0 < timeout <= 30:
        raise LiviIpcError("invalid_timeout")
    sock.settimeout(timeout)
    while True:
        end = pending.find(b"\n")
        if end >= 0:
            raw = bytes(pending[:end])
            del pending[: end + 1]
            break
        if len(pending) >= MAX_FRAME_BYTES:
            raise LiviIpcError("bridge_frame_too_large")
        try:
            chunk = sock.recv(min(65536, MAX_FRAME_BYTES - len(pending)))
        except socket.timeout:
            raise TimeoutError("livi_bridge_timeout") from None
        except OSError:
            raise ConnectionError("livi_bridge_disconnected") from None
        if not chunk:
            raise EOFError("livi_bridge_eof")
        pending.extend(chunk)
    try:
        value = json.loads(raw.decode("ascii"), object_pairs_hook=_reject_duplicate_json_keys)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
        raise LiviIpcError("malformed_bridge_frame") from None
    if not isinstance(value, list):
        raise LiviIpcError("bridge_frame_shape")
    return value


def _verify_peer_uid(sock: socket.socket, expected_uid: int) -> None:
    try:
        if hasattr(sock, "getpeereid"):
            peer_uid, _peer_gid = sock.getpeereid()
        elif sys.platform == "darwin":
            # Darwin sys/un.h: SOL_LOCAL=0, LOCAL_PEERCRED=1; xucred
            # starts with uint32 version and uint32 effective uid.
            raw = sock.getsockopt(0, 1, 76)
            if len(raw) < 8:
                raise OSError("peer_credentials_truncated")
            version, peer_uid = struct.unpack_from("=II", raw)
            if version != 0:
                raise OSError("peer_credentials_version")
        elif hasattr(socket, "SO_PEERCRED"):
            raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
            peer_pid, peer_uid, _peer_gid = struct.unpack("3i", raw)
            if peer_pid <= 0:
                raise OSError("peer_pid_unavailable")
        else:
            raise OSError("peer_credentials_unavailable")
    except OSError:
        raise LiviIpcError("bridge_peer_identity_unavailable") from None
    if peer_uid != expected_uid:
        raise LiviIpcError("bridge_peer_uid_mismatch")


def _prepare_socket_path(path: Path, uid: int) -> None:
    if not path.is_absolute() or len(os.fsencode(path)) > 103:
        raise LiviIpcError("invalid_bridge_socket_path")
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        parent_stat = path.parent.lstat()
    except OSError:
        raise LiviIpcError("bridge_socket_directory_unavailable") from None
    if (not stat.S_ISDIR(parent_stat.st_mode) or stat.S_ISLNK(parent_stat.st_mode) or
            parent_stat.st_uid != uid or parent_stat.st_mode & 0o022):
        raise LiviIpcError("bridge_socket_directory_unsafe")
    try:
        existing = path.lstat()
    except FileNotFoundError:
        return
    except OSError:
        raise LiviIpcError("bridge_socket_path_unavailable") from None
    if (not stat.S_ISSOCK(existing.st_mode) or existing.st_uid != uid):
        raise LiviIpcError("bridge_socket_path_conflict")
    try:
        path.unlink()
    except OSError:
        raise LiviIpcError("stale_bridge_socket_cleanup_failed") from None


def _sanitize_plist(value: object, depth: int = 0, nodes: list[int] | None = None,
                    *, strip_private: bool = True) -> object:
    if nodes is None:
        nodes = [0]
    nodes[0] += 1
    if depth > 12 or nodes[0] > 4096:
        raise LiviIpcError("bridge_plist_structure_limit")
    if isinstance(value, dict):
        if len(value) > 256:
            raise LiviIpcError("bridge_plist_map_limit")
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 256:
                raise LiviIpcError("bridge_plist_key_limit")
            if strip_private and key.casefold().replace("_", "") in _PRIVATE_FIELDS:
                continue
            result[key] = _sanitize_plist(item, depth + 1, nodes, strip_private=strip_private)
        return result
    if isinstance(value, list):
        if len(value) > 256:
            raise LiviIpcError("bridge_plist_array_limit")
        return [_sanitize_plist(item, depth + 1, nodes, strip_private=strip_private) for item in value]
    if isinstance(value, (str, bytes)):
        if len(value) > (4096 if isinstance(value, str) else MAX_PLIST_BYTES):
            raise LiviIpcError("bridge_plist_value_limit")
        return value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise LiviIpcError("bridge_plist_value_type")


def _decode_control_plist(encoded: object) -> dict[str, object]:
    if not isinstance(encoded, str) or len(encoded) > ((MAX_PLIST_BYTES + 2) // 3) * 4:
        raise LiviIpcError("bridge_plist_encoding_limit")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise LiviIpcError("malformed_bridge_plist_base64") from None
    if len(raw) > MAX_PLIST_BYTES:
        raise LiviIpcError("bridge_plist_too_large")
    try:
        parsed = plistlib.loads(raw)
    except (plistlib.InvalidFileException, ValueError, TypeError, OverflowError, RecursionError):
        raise LiviIpcError("malformed_control_plist") from None
    safe = _sanitize_plist(parsed)
    if not isinstance(safe, dict):
        raise LiviIpcError("control_plist_root_not_dictionary")
    return safe


def _encode_control_plist(body: object) -> str:
    # This body is generated by ClarityLink. Keep required accessory identity
    # fields such as deviceID; only inbound phone fields are privacy-filtered.
    safe = _sanitize_plist(body, strip_private=False)
    if not isinstance(safe, dict):
        raise LiviIpcError("response_plist_root_not_dictionary")
    try:
        raw = plistlib.dumps(safe, fmt=plistlib.FMT_BINARY, sort_keys=True)
    except (ValueError, TypeError, OverflowError):
        raise LiviIpcError("response_plist_encode_failed") from None
    if len(raw) > MAX_PLIST_BYTES:
        raise LiviIpcError("response_plist_too_large")
    return base64.b64encode(raw).decode("ascii")


class LiviUnixSocketBridge:
    """One authenticated LIVI socket session and one outstanding request."""

    bridge_kind = "REAL_LIVI_BRIDGE"

    __slots__ = (
        "_socket", "_pending", "_generation", "_session_id", "_closed",
        "_seen_ids", "_active_request_id",
    )

    def __init__(self, sock: socket.socket, pending: bytearray,
                 generation: int, session_id: str) -> None:
        self._socket = sock
        self._pending = pending
        self._generation = generation
        self._session_id = session_id
        self._closed = False
        self._seen_ids: set[str] = set()
        self._active_request_id: str | None = None

    @property
    def authenticated(self) -> bool:
        return not self._closed

    @property
    def session_identifier(self) -> str:
        return self._session_id

    @property
    def generation(self) -> int:
        return self._generation

    def read_request(self, timeout: float) -> ControlRequest:
        if not self.authenticated:
            raise LiviIpcError("transport_closed")
        if self._active_request_id is not None:
            raise LiviIpcError("bridge_request_already_pending")
        try:
            frame = _read_frame(self._socket, timeout, self._pending)
            if (len(frame) != 8 or frame[0] != PROTOCOL_VERSION or frame[1] != "request" or
                    type(frame[2]) is not int or frame[2] != self._generation or
                    not _is_uuid(frame[3]) or frame[3] in self._seen_ids or
                    not isinstance(frame[4], str) or len(frame[4]) > 16 or
                    not isinstance(frame[5], str) or len(frame[5]) > 128 or
                    (frame[6] is not None and
                     (not isinstance(frame[6], str) or len(frame[6]) > 128))):
                raise LiviIpcError("invalid_bridge_request")
            request_id = frame[3]
            body = _decode_control_plist(frame[7])
            method = frame[4].upper()
            path = "/info" if method == "GET" and frame[5].lower().endswith("/info") else (
                "/session" if method == "SETUP" else frame[5]
            )
            content_type = frame[6]
            if content_type is not None and content_type != PLIST_CONTENT_TYPE:
                raise LiviIpcError("unsupported_control_content_type")
            request = ControlRequest(method, path, body, self._generation, content_type)
            validate_control_request(request, self._generation)
            if method not in ("GET", "SETUP") or (method == "GET" and path != "/info"):
                raise LiviIpcError("unsupported_delegated_request")
            self._seen_ids.add(request_id)
            if len(self._seen_ids) > MAX_PENDING_IDS:
                raise LiviIpcError("bridge_request_count_limit")
            self._active_request_id = request_id
            return request
        except TimeoutError:
            self.close()
            raise
        except (EOFError, ConnectionError):
            self.close()
            raise
        except Exception:
            self.close()
            raise

    def write_response(self, response: ControlResponse) -> None:
        request_id = self._active_request_id
        if not self.authenticated or request_id is None:
            raise LiviIpcError("bridge_response_without_request")
        if (not isinstance(response, ControlResponse) or type(response.status) is not int or
                not 100 <= response.status <= 599 or response.generation != self._generation):
            raise LiviIpcError("invalid_bridge_response")
        encoded = _encode_control_plist(response.body)
        try:
            _send_frame(self._socket, [
                PROTOCOL_VERSION, "response", self._generation, request_id,
                response.status, PLIST_CONTENT_TYPE, encoded,
            ])
        finally:
            self._active_request_id = None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._active_request_id = None
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self._socket.close()
        except OSError:
            pass

    def __repr__(self) -> str:
        return f"LiviUnixSocketBridge(generation={self._generation}, authenticated={self.authenticated}, closed={self._closed})"

    def __reduce__(self) -> None:
        raise LiviIpcError("bridge_not_serializable")


class LiviUnixSocketBridgeFactory:
    """Accept exactly one same-UID LIVI session on a private local socket."""

    bridge_kind = "REAL_LIVI_BRIDGE"

    def __init__(self, socket_path: str | os.PathLike[str], *, expected_uid: int | None = None,
                 accept_timeout: float = 30.0) -> None:
        self._path = Path(socket_path)
        self._uid = os.getuid() if expected_uid is None else expected_uid
        self._accept_timeout = accept_timeout
        self._listener: socket.socket | None = None
        self._bridge: LiviUnixSocketBridge | None = None
        self._socket_identity: tuple[int, int] | None = None
        self._closed = False
        if (type(self._uid) is not int or self._uid < 0 or
                not 0 < accept_timeout <= 300):
            raise LiviIpcError("invalid_bridge_factory_config")

    def _listen(self) -> socket.socket:
        if self._closed:
            raise LiviIpcError("bridge_factory_closed")
        _prepare_socket_path(self._path, self._uid)
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            listener.bind(str(self._path))
            os.chmod(self._path, 0o600)
            st = self._path.lstat()
            self._socket_identity = (st.st_dev, st.st_ino)
            listener.listen(1)
            listener.settimeout(self._accept_timeout)
            self._listener = listener
            return listener
        except Exception:
            listener.close()
            self._unlink_own_socket()
            raise LiviIpcError("bridge_listener_start_failed") from None

    def open_authenticated(self, generation: int) -> LiviUnixSocketBridge:
        if self._bridge is not None or type(generation) is not int or generation < 1:
            raise LiviIpcError("bridge_session_unavailable")
        listener = self._listen()
        client: socket.socket | None = None
        try:
            try:
                client, _address = listener.accept()
            except socket.timeout:
                raise TimeoutError("livi_bridge_accept_timeout") from None
            _verify_peer_uid(client, self._uid)
            pending = bytearray()
            hello = _read_frame(client, min(self._accept_timeout, 30), pending)
            if (len(hello) != 4 or hello[0] != PROTOCOL_VERSION or hello[1] != "authenticated" or
                    not _is_uuid(hello[2]) or hello[3] != AUTH_STATE_PROOF):
                raise LiviIpcError("livi_authenticated_state_unproven")
            _send_frame(client, [PROTOCOL_VERSION, "session_ready", generation])
            client.settimeout(30)
            self._bridge = LiviUnixSocketBridge(client, pending, generation, hello[2])
            client = None
            return self._bridge
        except Exception:
            if client is not None:
                try:
                    client.close()
                except OSError:
                    pass
            self.close()
            raise
        finally:
            listener.close()
            self._listener = None
            self._unlink_own_socket()

    def _unlink_own_socket(self) -> None:
        if self._socket_identity is None:
            return
        try:
            st = self._path.lstat()
            if (stat.S_ISSOCK(st.st_mode) and st.st_uid == self._uid and
                    (st.st_dev, st.st_ino) == self._socket_identity):
                self._path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass
        self._socket_identity = None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._bridge is not None:
            self._bridge.close()
            self._bridge = None
        if self._listener is not None:
            try:
                self._listener.close()
            except OSError:
                pass
            self._listener = None
        self._unlink_own_socket()

    def __repr__(self) -> str:
        return "LiviUnixSocketBridgeFactory(path=redacted, state=redacted)"
