"""Process boundary for the Display 1 host (CL-INT-04). Original, offline, synthetic-only.

Newline-delimited JSON over a Unix domain socket between a producer process and a
host process. The host process owns the lease, the expiry timer
(``Display1HostService``) and the withdrawal. The producer only asks.

Producer death is detected by the host itself: a lease is bound to the connection
that was granted it, and when that connection ends (clean close, SIGKILL, crash)
the host revokes that lease -- the analogue of ``IBinder.linkToDeath``. A dead
connection can only revoke ITS lease; a newer generation is untouched. A producer
that stays alive but silent is covered by the expiry timer, not by this path.

``RemoteDisplay1Host`` mirrors the ``Display1LeaseHost`` surface used by
``FailSafeCoordinator`` and ``Type111IngestPipeline``, so neither needs a second
code path. Every transport error fails closed (rejects, never presents).

Limits: the socket is mode 0600 in the caller's directory; epoch/lease remain
staleness fences, not authenticators. Lab controls (interrupt, display loss) exist
only to exercise the synthetic host and are off unless the server enables them.
"""
from __future__ import annotations

import json
import os
import socket
import stat
import sys
import threading
from pathlib import Path
from typing import Any

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import failsafe_coordinator as fsc  # noqa: E402
from display1_host_service import Display1HostService  # noqa: E402

MAX_LINE_BYTES = 8192
MAX_CONNECTIONS = 8
MAX_CONTENT_CHARS = 256
MAX_REASON_CHARS = 64
STATUS_LOG_ENTRIES = 32
MAX_WIRE_INT = 2 ** 53
ACCEPT_POLL_SECONDS = 0.1
CONNECTION_IDLE_SECONDS = 30.0
CLIENT_TIMEOUT_SECONDS = 2.0
THREAD_JOIN_SECONDS = 2.0
MAX_SOCKET_PATH = 100  # sun_path is ~104 on macOS
_LAB_OPS = frozenset({"interrupt_on", "interrupt_off", "lose_display", "restore_display", "select_page"})


class HostIpcError(RuntimeError):
    pass


def _send(conn: socket.socket, message: dict[str, Any]) -> None:
    conn.sendall(json.dumps(message, separators=(",", ":")).encode() + b"\n")


class _Connection:
    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.lease: fsc.LeaseGrant | None = None
        self.buffer = b""

    def read_line(self) -> bytes | None:
        while b"\n" not in self.buffer:
            if len(self.buffer) > MAX_LINE_BYTES:
                raise HostIpcError("line_too_long")
            chunk = self.sock.recv(4096)
            if not chunk:
                return None
            self.buffer += chunk
        line, self.buffer = self.buffer.split(b"\n", 1)
        return line


class Display1HostServer:
    """Serves one ``Display1HostService`` on a Unix socket until ``stop()``."""

    def __init__(self, service: Display1HostService, path: str, *, lab_controls: bool = False) -> None:
        if len(path) > MAX_SOCKET_PATH:
            raise HostIpcError("socket_path_too_long")
        self.service = service
        self.path = path
        self.lab_controls = lab_controls
        self._listener: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._conns: dict[int, tuple[_Connection, threading.Thread]] = {}
        self._next_id = 0
        self._stopping = threading.Event()
        self.rejected_connections = 0

    # ---- lifecycle ----
    def start(self) -> None:
        if self._listener is not None:
            raise HostIpcError("already_started")
        self._remove_stale_socket()
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        old_umask = os.umask(0o177)  # the socket is never connectable by others, not even briefly
        try:
            listener.bind(self.path)
            listener.listen(MAX_CONNECTIONS)
            listener.settimeout(ACCEPT_POLL_SECONDS)
        except OSError:
            listener.close()
            raise
        finally:
            os.umask(old_umask)
        self._listener = listener
        self.service.start()
        self._accept_thread = threading.Thread(target=self._accept_loop, name="Display1HostAccept", daemon=True)
        self._accept_thread.start()

    def _remove_stale_socket(self) -> None:
        try:
            info = os.lstat(self.path)
        except FileNotFoundError:
            return
        # Only ever remove a socket this user owns: never a regular file or someone else's path.
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
            raise HostIpcError("socket_path_not_ours")
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        probe.settimeout(0.5)
        try:
            probe.connect(self.path)
        except (ConnectionRefusedError, FileNotFoundError):
            os.unlink(self.path)  # nothing listens: a dead host left it behind
            return
        except OSError as exc:  # timeout, full backlog, EACCES: it may be alive, so do not touch it
            raise HostIpcError("socket_state_unknown") from exc
        finally:
            probe.close()
        raise HostIpcError("host_already_running")

    def stop(self) -> bool:
        """Close everything the server owns. True only if every thread ended and the host is clean."""
        self._stopping.set()
        listener, self._listener = self._listener, None
        if listener is not None:
            listener.close()
        threads: list[threading.Thread] = []
        accept = self._accept_thread
        if accept is not None and accept is not threading.current_thread():
            accept.join(THREAD_JOIN_SECONDS)  # first: no connection can appear after this
            threads.append(accept)
        with self._lock:
            conns = list(self._conns.values())
        for conn, _thread in conns:
            try:
                conn.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        threads.extend(t for _c, t in conns)
        for thread in threads[1 if accept in threads else 0:]:
            if thread is not threading.current_thread():
                thread.join(THREAD_JOIN_SECONDS)
        clean = self.service.stop() and not any(t.is_alive() for t in threads)
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass
        except OSError:
            clean = False
        return clean

    # ---- accept / serve ----
    def _accept_loop(self) -> None:
        while not self._stopping.is_set():
            listener = self._listener
            if listener is None:
                return
            try:
                sock, _addr = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            with self._lock:
                if len(self._conns) >= MAX_CONNECTIONS:
                    self.rejected_connections += 1
                    sock.close()
                    continue
                conn = _Connection(sock)
                conn_id = self._next_id = self._next_id + 1
                thread = threading.Thread(target=self._serve, args=(conn_id, conn),
                                          name=f"Display1HostConn{conn_id}", daemon=True)
                self._conns[conn_id] = (conn, thread)
            thread.start()

    def _serve(self, conn_id: int, conn: _Connection) -> None:
        conn.sock.settimeout(CONNECTION_IDLE_SECONDS)
        try:
            while not self._stopping.is_set():
                line = conn.read_line()
                if line is None:
                    return
                _send(conn.sock, self._handle(conn, line))
        except (OSError, HostIpcError):
            pass
        finally:
            self._on_connection_end(conn_id, conn)

    def _on_connection_end(self, conn_id: int, conn: _Connection) -> None:
        lease, conn.lease = conn.lease, None
        try:
            if lease is not None:  # host-owned detection of producer death
                self.service.revoke_if_current(lease, "producer connection lost")
        except Exception as exc:  # noqa: BLE001 - counted; the slot below must still be released
            self.service._record_error(exc)  # noqa: SLF001 - same-package collaborator
        finally:
            try:
                conn.sock.close()
            except OSError:
                pass
            with self._lock:
                self._conns.pop(conn_id, None)

    # ---- request handling (never raises: a bad request is an error reply) ----
    def _handle(self, conn: _Connection, line: bytes) -> dict[str, Any]:
        try:
            request = json.loads(line)
            op = request["op"]
            if not isinstance(op, str):
                raise ValueError("op")
            return self._dispatch(conn, op, request)
        except (ValueError, KeyError, TypeError):
            return {"ok": False, "error": "bad_request"}
        except Exception as exc:  # noqa: BLE001 - a host fault is reported, the connection stays fail-closed
            return {"ok": False, "error": "host_error", "type": type(exc).__name__}

    def _dispatch(self, conn: _Connection, op: str, req: dict[str, Any]) -> dict[str, Any]:
        host = self.service.host
        if op == "hello":
            return {"ok": True, "epoch": host.epoch}
        if op == "grant":
            # A producer process restarts its own counter, so the HOST allocates every generation
            # above all it has ever granted; the producer's number is only a lower bound.
            result, lease = host.grant_above(_bounded_int(req["generation"]))
            if lease is not None:
                conn.lease = lease
            return {"ok": True, "result": result.value, "epoch": host.epoch,
                    "generation": lease.generation if lease is not None else 0}
        if op == "submit":
            lease = fsc.LeaseGrant(_bounded_int(req["epoch"]), _bounded_int(req["generation"]))
            _bounded_int(req["sequence"])
            content = req["content"]
            if not isinstance(content, str) or len(content) > MAX_CONTENT_CHARS:
                return {"ok": False, "error": "bad_content"}
            if conn.lease is None:
                return {"ok": True, "result": fsc.SubmitResult.REJECTED_NO_LEASE.value}
            if lease != conn.lease:  # another connection's lease, or a stale one
                return {"ok": True, "result": fsc.SubmitResult.REJECTED_STALE_GENERATION.value}
            return {"ok": True, "result": host.submit(lease, req["sequence"], content).value}
        if op == "heartbeat":
            lease = fsc.LeaseGrant(_bounded_int(req["epoch"]), _bounded_int(req["generation"]))
            return {"ok": True, "alive": conn.lease == lease and host.heartbeat(lease)}
        if op == "revoke":
            lease, conn.lease = conn.lease, None
            revoked = lease is not None and self.service.revoke_if_current(
                lease, str(req.get("reason", "producer release"))[:MAX_REASON_CHARS])
            # Never claim "withdrawn" when the cluster refused: say so, and the client raises.
            return {"ok": True, "revoked": revoked, "withdrawal_pending": host.withdrawal_pending}
        if op == "status":
            st = self.service.status()
            return {"ok": True, "status": {
                **st.__dict__,
                # newest few only: the exact totals are in the *_count fields, and the reply must
                # stay far below MAX_LINE_BYTES however long the host has been failing
                "revocations": [r[:MAX_REASON_CHARS] for r in st.revocations[-STATUS_LOG_ENTRIES:]],
                "withdrawal_failures": list(st.withdrawal_failures[-STATUS_LOG_ENTRIES:])}}
        if op in _LAB_OPS and self.lab_controls:
            return self._lab(op, req)
        return {"ok": False, "error": "unknown_op"}

    def _lab(self, op: str, req: dict[str, Any]) -> dict[str, Any]:
        host = self.service.host
        if op == "interrupt_on":
            host.activate_interrupt()
        elif op == "interrupt_off":
            host.clear_interrupt()
        elif op == "lose_display":
            host.lose_display()
        elif op == "restore_display":
            return {"ok": True, "restored": host.restore_display()}
        else:
            host.select_page(bool(req["selected"]))
        return {"ok": True}


def _bounded_int(value: Any) -> int:
    """A wire integer: exact int, non-negative, below 2**53 (a peer cannot inflate the high-water mark)."""
    if type(value) is not int or not 0 <= value < MAX_WIRE_INT:
        raise ValueError("out_of_range_int")
    return value


def _describe(content: Any) -> str:
    """Compact, bounded text for synthetic content; pixels never cross the socket."""
    if isinstance(content, str):
        return content[:MAX_CONTENT_CHARS]
    frame = getattr(content, "frame", None)
    if frame is not None and hasattr(content, "sequence"):
        return (f"frame seq={content.sequence} {getattr(frame, 'width', '?')}x"
                f"{getattr(frame, 'height', '?')} ts={getattr(frame, 'timestamp', '?')}")
    return type(content).__name__


class RemoteDisplay1Host:
    """``Display1LeaseHost`` look-alike that talks to a host in another process.

    Not thread-safe by itself beyond one request at a time; a lock serializes the
    control thread and the receiver's dispatcher worker. Any transport failure
    rejects (fail closed) and the connection stays dead: the host's own death
    detection then withdraws, so the client never needs to clean up to be safe.
    """

    def __init__(self, path: str, *, timeout: float = CLIENT_TIMEOUT_SECONDS) -> None:
        self._lock = threading.Lock()
        self._sock: socket.socket | None = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.settimeout(timeout)
        self._buffer = b""
        self.transport_errors = 0
        try:
            self._sock.connect(path)
        except OSError:
            self._sock.close()
            self._sock = None
            raise
        reply = self._call({"op": "hello"})
        if not reply or not reply.get("ok") or type(reply.get("epoch")) is not int:
            self.close()
            raise HostIpcError("hello_failed")
        self.epoch: int = reply["epoch"]

    # ---- transport ----
    def _call(self, request: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock:
            sock = self._sock
            if sock is None:
                return None
            try:
                _send(sock, request)
                while b"\n" not in self._buffer:
                    if len(self._buffer) > MAX_LINE_BYTES:
                        raise HostIpcError("line_too_long")
                    chunk = sock.recv(4096)
                    if not chunk:
                        raise HostIpcError("host_closed")
                    self._buffer += chunk
                line, self._buffer = self._buffer.split(b"\n", 1)
                reply = json.loads(line)
                if not isinstance(reply, dict):
                    raise HostIpcError("bad_reply")
                return reply
            except (OSError, ValueError, HostIpcError):
                self.transport_errors += 1
                self._close_locked()
                return None

    def _close_locked(self) -> None:
        sock, self._sock = self._sock, None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def close(self) -> None:
        with self._lock:
            self._close_locked()

    @property
    def connected(self) -> bool:
        return self._sock is not None

    # ---- Display1LeaseHost surface ----
    def grant(self, generation: int) -> tuple[fsc.GrantResult, fsc.LeaseGrant | None]:
        reply = self._call({"op": "grant", "generation": generation})
        if not reply or not reply.get("ok"):
            return fsc.GrantResult.REJECTED_NO_DISPLAY, None
        try:
            result = fsc.GrantResult(reply["result"])
            if result is not fsc.GrantResult.GRANTED:
                return result, None
            return result, fsc.LeaseGrant(_bounded_int(reply["epoch"]), _bounded_int(reply["generation"]))
        except (KeyError, ValueError, TypeError):
            self._protocol_error()
            return fsc.GrantResult.REJECTED_NO_DISPLAY, None  # adopt generation: host allocated it

    def submit(self, lease: fsc.LeaseGrant, sequence: int, content: Any) -> fsc.SubmitResult:
        text = _describe(content)
        reply = self._call({"op": "submit", "epoch": lease.epoch, "generation": lease.generation,
                            "sequence": sequence, "content": text})
        if not reply or not reply.get("ok"):
            return fsc.SubmitResult.REJECTED_NO_DISPLAY
        try:
            return fsc.SubmitResult(reply["result"])
        except (KeyError, ValueError, TypeError):
            self._protocol_error()
            return fsc.SubmitResult.REJECTED_NO_DISPLAY

    def _protocol_error(self) -> None:
        """A reply this client cannot parse: count it and drop the connection (fail closed)."""
        with self._lock:
            self.transport_errors += 1
            self._close_locked()

    def heartbeat(self, lease: fsc.LeaseGrant) -> bool:
        reply = self._call({"op": "heartbeat", "epoch": lease.epoch, "generation": lease.generation})
        return bool(reply and reply.get("ok") and reply.get("alive"))

    def revoke(self, reason: str) -> bool:
        """True if a lease was withdrawn. RAISES when the host did not confirm the withdrawal.

        Like the in-process host, a revoke that cannot be confirmed (cluster refused, or the
        transport is gone) is an error, never a quiet False: callers keep ``withdrawal_pending``
        set and report it. A dead transport also makes the host revoke on its own.
        """
        reply = self._call({"op": "revoke", "reason": reason})
        if not reply or not reply.get("ok"):
            raise HostIpcError("revoke_unconfirmed")
        if reply.get("withdrawal_pending"):
            raise HostIpcError("host_withdrawal_pending")
        return bool(reply.get("revoked"))

    def status(self) -> dict[str, Any]:
        """The host's own report. RAISES when unavailable: unknown state is never reported as clean."""
        reply = self._call({"op": "status"})
        if not reply or not reply.get("ok") or not isinstance(reply.get("status"), dict):
            raise HostIpcError("host_status_unavailable")
        return reply["status"]

    @property
    def lease_held(self) -> bool:
        try:
            return bool(self.status()["lease_held"])
        except HostIpcError:
            return False  # connection gone: the host revokes that connection's lease itself

    @property
    def visible_content(self) -> Any:
        return "host-content" if self.status()["visible"] else None

    @property
    def residual_state(self) -> tuple[Any, ...]:
        return tuple(range(self.status()["residual"]))

    @property
    def revocations(self) -> list[str]:
        try:
            return list(self.status()["revocations"])
        except HostIpcError:
            return []  # diagnostic only

    def activate_interrupt(self) -> None:
        self._call({"op": "interrupt_on"})

    def clear_interrupt(self) -> None:
        self._call({"op": "interrupt_off"})

    def lose_display(self) -> None:
        self._call({"op": "lose_display"})

    def restore_display(self) -> bool:
        reply = self._call({"op": "restore_display"})
        return bool(reply and reply.get("ok") and reply.get("restored"))

    def select_page(self, selected: bool) -> None:
        self._call({"op": "select_page", "selected": bool(selected)})
