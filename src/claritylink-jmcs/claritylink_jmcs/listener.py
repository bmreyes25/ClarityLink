"""One-connection, generation-owned loopback media listener for offline labs."""
from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import socket


class ListenerError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass
class HostListener:
    generation: int
    sock: socket.socket
    host: str
    port: int
    accepted: socket.socket | None = None
    closed: bool = False

    @classmethod
    def create(cls, generation: int, *, host: str = "127.0.0.1", port: int = 0) -> "HostListener":
        try:
            address = ipaddress.ip_address(host)
        except ValueError as exc:
            raise ListenerError("invalid_bind_address") from exc
        if address.version != 4 or not address.is_loopback:
            raise ListenerError("non_loopback_bind_prohibited")
        if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
            raise ListenerError("invalid_port")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.set_inheritable(False)
            sock.settimeout(1.0)
            sock.bind((str(address), port))
            sock.listen(1)
            return cls(generation, sock, str(address), int(sock.getsockname()[1]))
        except OSError as exc:
            sock.close()
            raise ListenerError("listener_prepare_failed") from exc

    def accept(self, generation: int, timeout: float = 1.0) -> socket.socket:
        if self.closed or generation != self.generation:
            raise ListenerError("stale_listener")
        if self.accepted is not None:
            raise ListenerError("connection_limit")
        self.sock.settimeout(min(max(timeout, 0.001), 5.0))
        conn: socket.socket | None = None
        try:
            conn, _ = self.sock.accept()
            conn.set_inheritable(False)
            conn.settimeout(1.0)
            self.accepted = conn
            return conn
        except OSError as exc:
            if conn is not None:
                conn.close()
            raise ListenerError("accept_failed") from exc

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        if self.accepted is not None:
            self.accepted.close()
            self.accepted = None
        self.sock.close()
