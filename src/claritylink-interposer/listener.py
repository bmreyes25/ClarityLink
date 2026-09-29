"""Deterministic fake listener. It never creates an operating-system socket."""
from dataclasses import dataclass
from typing import Protocol

class ListenerError(RuntimeError): pass
class SecondaryListener(Protocol):
    @property
    def port(self) -> int: ...
    def close(self) -> None: ...

@dataclass
class FakeSecondaryListener:
    assigned_port: int
    fail_at: str | None = None
    closed: bool = False
    close_count: int = 0
    accepted: bool = False
    @property
    def port(self) -> int: return self.assigned_port
    def close(self) -> None:
        self.close_count += 1
        self.closed = True
    def accept(self):
        if self.closed: raise ListenerError("listener is closed")
        if self.fail_at == "accept": raise ListenerError("synthetic accept failure")
        self.accepted = True
        return SyntheticAcceptedSocket()

@dataclass
class SyntheticAcceptedSocket:
    closed: bool = False
    def close(self): self.closed = True

class FakeSecondaryListenerFactory:
    def __init__(self, first_port: int = 41000, fail_at: str | None = None):
        self.next_port = first_port
        self.fail_at = fail_at
        self.created: list[FakeSecondaryListener] = []
    def create(self, requested_port: int = 0) -> FakeSecondaryListener:
        for phase in ("socket", "bind", "getsockname", "listen"):
            if self.fail_at == phase: raise ListenerError(f"synthetic {phase} failure")
        port = requested_port or self.next_port
        if requested_port == 0: self.next_port += 1
        listener = FakeSecondaryListener(port, self.fail_at)
        self.created.append(listener)
        return listener
