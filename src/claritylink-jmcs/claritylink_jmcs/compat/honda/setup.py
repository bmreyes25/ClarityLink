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
        # The bounded Honda audit found no Type111 branch. Detect that stream
        # before the generic lab parser applies any Type111 descriptor rules;
        # Honda's Type111 request fields remain unknown.
        if isinstance(raw, Mapping):
            streams = raw.get("streams")
            if isinstance(streams, (list, tuple)) and any(
                    isinstance(stream, Mapping) and
                    isinstance(stream.get("type"), int) and
                    not isinstance(stream.get("type"), bool) and
                    stream.get("type") == 111 for stream in streams):
                raise EvidenceRequired("honda_type111_setup_dispatch")
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
