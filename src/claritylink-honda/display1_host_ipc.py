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
code path. A transport or protocol failure raises ``HostIpcError``; it is never
returned as a host refusal, and callers fail closed on it.

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
_STATUS_BOOLS = ("lease_held", "visible", "withdrawal_pending")
MAX_RESIDUAL = 64  # a handful of project-owned items at most; bounds residual_state's allocation
_LAB_OPS = frozenset({"interrupt_on", "interrupt_off", "lose_display", "restore_display", "select_page"})


class HostIpcError(RuntimeError):
    pass


def _send(conn: socket.socket, message: dict[str, Any]) -> None:
    conn.sendall(json.dumps(message, separators=(",", ":")).encode() + b"\n")


class _Connection:
    """One producer connection. ``lease``/``superseded``/``ever_granted`` change only under the
    server's ownership lock, and ``superseded`` is never cleared: a connection that lost
    ownership to another producer can only be replaced by a fresh connection."""

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.lease: fsc.LeaseGrant | None = None
        self.ever_granted = False
        self.superseded = False
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
        self._ownership_lock = threading.Lock()  # grant + supersession marking are one step
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
        with self._ownership_lock:
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
            minimum = _bounded_int(req["generation"])
            with self._ownership_lock:
                if conn.superseded:  # permanent: asking again can never win ownership back
                    return {"ok": True, "result": fsc.GrantResult.REJECTED_SUPERSEDED.value,
                            "epoch": host.epoch, "generation": 0}
                result, lease = host.grant_above(minimum)
                if lease is not None:
                    conn.lease, conn.ever_granted = lease, True
                    self._supersede_other_owners(conn)
            return {"ok": True, "result": result.value, "epoch": host.epoch,
                    "generation": lease.generation if lease is not None else 0}
        if op == "submit":
            lease = fsc.LeaseGrant(_bounded_int(req["epoch"]), _bounded_int(req["generation"]))
            _bounded_int(req["sequence"])
            content = req["content"]
            if not isinstance(content, str) or len(content) > MAX_CONTENT_CHARS:
                return {"ok": False, "error": "bad_content"}
            owned, superseded = self._ownership_of(conn)
            if superseded:
                return {"ok": True, "result": fsc.SubmitResult.REJECTED_SUPERSEDED.value}
            if owned is None:
                return {"ok": True, "result": fsc.SubmitResult.REJECTED_NO_LEASE.value}
            if lease != owned:  # another connection's lease, or a stale one
                return {"ok": True, "result": fsc.SubmitResult.REJECTED_STALE_GENERATION.value}
            return {"ok": True, "result": host.submit(lease, req["sequence"], content).value}
        if op == "heartbeat":
            lease = fsc.LeaseGrant(_bounded_int(req["epoch"]), _bounded_int(req["generation"]))
            owned, superseded = self._ownership_of(conn)
            return {"ok": True, "alive": not superseded and owned == lease and host.heartbeat(lease)}
        if op == "revoke":
            with self._ownership_lock:
                lease, conn.lease = conn.lease, None
                superseded = conn.superseded
            revoked = lease is not None and self.service.revoke_if_current(
                lease, str(req.get("reason", "producer release"))[:MAX_REASON_CHARS])
            # Never claim "withdrawn" when the cluster refused: say so, and the client raises. A
            # fenced connection owns no content, so another owner's pending withdrawal is not its news.
            return {"ok": True, "revoked": revoked,
                    "withdrawal_pending": host.withdrawal_pending and not superseded}
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

    def _ownership_of(self, conn: _Connection) -> tuple[fsc.LeaseGrant | None, bool]:
        """One consistent (lease, superseded) view of a connection, taken under the ownership lock."""
        with self._ownership_lock:
            return conn.lease, conn.superseded

    def _supersede_other_owners(self, owner: _Connection) -> None:
        """Called under the ownership lock after ``owner`` was granted. Every other connection that
        ever held a lease (even one that already expired or was released) is fenced for good, so
        it cannot reclaim ownership by sending ``grant`` again."""
        with self._lock:
            others = [c for c, _t in self._conns.values() if c is not owner]
        for other in others:
            if other.ever_granted:
                other.superseded, other.lease = True, None

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
        try:
            reply = self._call_ok({"op": "hello"})
        except HostIpcError as exc:
            self.close()
            raise HostIpcError("hello_failed") from exc
        if type(reply.get("epoch")) is not int:
            self.close()
            raise HostIpcError("hello_failed")
        self.epoch: int = reply["epoch"]

    # ---- transport ----
    def _call(self, request: dict[str, Any]) -> dict[str, Any]:
        """One request/reply. RAISES ``HostIpcError`` when no well-formed reply arrived (unavailable
        or closed transport, timeout, truncated or malformed line): that is never a host decision."""
        with self._lock:
            sock = self._sock
            if sock is None:
                raise HostIpcError("host_unavailable")
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
            except HostIpcError:
                self.transport_errors += 1
                self._close_locked()
                raise
            except (OSError, ValueError) as exc:
                self.transport_errors += 1
                self._close_locked()
                raise HostIpcError(f"host_transport_failed:{type(exc).__name__}") from exc

    def _call_ok(self, request: dict[str, Any]) -> dict[str, Any]:
        """Like ``_call`` but the host must also report ``ok``. An ``ok: false`` reply is the host
        saying it could not process the request (bad request, internal fault), not a decision."""
        reply = self._call(request)
        if reply.get("ok") is not True:
            raise HostIpcError(f"host_error:{str(reply.get('error', 'unknown'))[:MAX_REASON_CHARS]}")
        return reply

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

    def _invalid_reply(self, what: str) -> HostIpcError:
        """A well-formed line whose content breaks the protocol: count it, drop the connection."""
        with self._lock:
            self.transport_errors += 1
            self._close_locked()
        return HostIpcError(f"invalid_{what}_reply")

    # ---- Display1LeaseHost surface ----
    # A returned GrantResult/SubmitResult is ALWAYS a decision the host actually made. Anything else
    # raises HostIpcError, so callers can tell "the host said no" from "the channel is broken".
    def grant(self, generation: int) -> tuple[fsc.GrantResult, fsc.LeaseGrant | None]:
        reply = self._call_ok({"op": "grant", "generation": generation})
        try:
            result = fsc.GrantResult(reply["result"])
            if result is not fsc.GrantResult.GRANTED:
                return result, None
            return result, fsc.LeaseGrant(_bounded_int(reply["epoch"]), _bounded_int(reply["generation"]))
        except (KeyError, ValueError, TypeError) as exc:
            raise self._invalid_reply("grant") from exc

    def submit(self, lease: fsc.LeaseGrant, sequence: int, content: Any) -> fsc.SubmitResult:
        text = _describe(content)
        reply = self._call_ok({"op": "submit", "epoch": lease.epoch, "generation": lease.generation,
                               "sequence": sequence, "content": text})
        try:
            return fsc.SubmitResult(reply["result"])
        except (KeyError, ValueError, TypeError) as exc:
            raise self._invalid_reply("submit") from exc

    def heartbeat(self, lease: fsc.LeaseGrant) -> bool:
        reply = self._call_ok({"op": "heartbeat", "epoch": lease.epoch, "generation": lease.generation})
        if type(reply.get("alive")) is not bool:
            raise self._invalid_reply("heartbeat")
        return reply["alive"]

    def revoke(self, reason: str) -> bool:
        """True if a lease was withdrawn. RAISES when the host did not confirm the withdrawal.

        Like the in-process host, a revoke that cannot be confirmed (cluster refused, or the
        transport is gone) is an error, never a quiet False: callers keep ``withdrawal_pending``
        set and report it. A dead transport also makes the host revoke on its own.
        """
        try:
            reply = self._call_ok({"op": "revoke", "reason": reason})
        except HostIpcError as exc:
            raise HostIpcError("revoke_unconfirmed") from exc  # keeps the transport cause
        if reply.get("withdrawal_pending"):
            raise HostIpcError("host_withdrawal_pending")
        return bool(reply.get("revoked"))

    def status(self) -> dict[str, Any]:
        """The host's own report. RAISES when unavailable: unknown state is never reported as clean."""
        try:
            reply = self._call_ok({"op": "status"})
        except HostIpcError as exc:
            raise HostIpcError("host_status_unavailable") from exc
        status = reply.get("status")
        if not isinstance(status, dict) \
                or any(type(status.get(key)) is not bool for key in _STATUS_BOOLS) \
                or type(status.get("residual")) is not int or not 0 <= status["residual"] <= MAX_RESIDUAL \
                or not isinstance(status.get("revocations"), list):
            raise self._invalid_reply("status")  # a field we act on is missing or mistyped
        return status

    @property
    def lease_held(self) -> bool:
        """RAISES when the host cannot be asked: unknown is neither held nor released."""
        return bool(self.status()["lease_held"])

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

    # Lab controls: a request the host never confirmed raises instead of looking applied.
    def activate_interrupt(self) -> None:
        self._call_ok({"op": "interrupt_on"})

    def clear_interrupt(self) -> None:
        self._call_ok({"op": "interrupt_off"})

    def lose_display(self) -> None:
        self._call_ok({"op": "lose_display"})

    def restore_display(self) -> bool:
        return bool(self._call_ok({"op": "restore_display"}).get("restored"))

    def select_page(self, selected: bool) -> None:
        self._call_ok({"op": "select_page", "selected": bool(selected)})
