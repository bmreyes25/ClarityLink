"""Clean-room mapping of the *known* Honda Type110 Setup fields.

This is not an ABI bridge or a reimplementation of CoreFoundation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ...setup import SetupError, SetupRequest


class EvidenceRequired(RuntimeError):
    def __init__(self, fact: str) -> None:
        self.fact = fact
        super().__init__(fact)


@dataclass(frozen=True)
class HondaStaticType110Adapter:
    evidence: str = "HONDA_STATIC"

    def parse_known_request(self, raw: Mapping[str, Any], generation: int) -> SetupRequest:
        parsed = SetupRequest.parse(raw, generation)
        if any(s.type != 110 for s in parsed.streams):
            raise EvidenceRequired("honda_non_type110_setup_behavior")
        return parsed

    def known_response_entry(self, port: int) -> dict[str, int]:
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise SetupError("invalid_data_port")
        return {"type": 110, "dataPort": port}

    def type111_response(self, *_: object) -> None:
        raise EvidenceRequired("honda_type111_response_schema")
