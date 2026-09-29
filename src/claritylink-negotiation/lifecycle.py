"""Project-owned Type-111 generation lifecycle model; no sockets or secrets."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class State(Enum):
    IDLE = auto()
    PREPARED = auto()
    ADVERTISED = auto()
    ACTIVE = auto()
    CLOSED = auto()


@dataclass
class Type111Lifecycle:
    generation: int = 0
    state: State = State.IDLE
    stream_connection_id: int | None = None
    data_port: int | None = None

    def prepare(self, stream_connection_id: int, data_port: int) -> int:
        if isinstance(stream_connection_id, bool) or not isinstance(stream_connection_id, int) or not 1 <= stream_connection_id < (1 << 64):
            raise ValueError("stream_connection_id must be a nonzero uint64")
        if isinstance(data_port, bool) or not isinstance(data_port, int) or not 1 <= data_port <= 65535:
            raise ValueError("data_port must be an assigned TCP port")
        self.teardown()
        self.generation += 1
        self.stream_connection_id = stream_connection_id
        self.data_port = data_port
        self.state = State.PREPARED
        return self.generation

    def mark_advertised(self) -> None:
        if self.state is not State.PREPARED:
            raise RuntimeError("only prepared state can be advertised")
        self.state = State.ADVERTISED

    def mark_active(self) -> None:
        if self.state is not State.ADVERTISED:
            raise RuntimeError("only advertised state can become active")
        self.state = State.ACTIVE

    def rollback(self) -> None:
        """Forget a project-owned attempt; stock Setup is outside this model."""
        self._clear(State.IDLE)

    def teardown(self) -> None:
        self._clear(State.CLOSED)

    def _clear(self, next_state: State) -> None:
        self.stream_connection_id = None
        self.data_port = None
        self.state = next_state
