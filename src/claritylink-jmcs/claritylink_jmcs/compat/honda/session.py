"""Static field model, not a Honda session ABI or object layout."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HondaType110SessionModel:
    generation: int
    stream_connection_id: int

    def __post_init__(self) -> None:
        if self.generation < 1 or not 1 <= self.stream_connection_id < 2**64:
            raise ValueError("invalid_static_session_model")
