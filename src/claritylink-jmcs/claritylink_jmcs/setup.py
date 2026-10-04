"""Evidence-bounded Setup structures and pre-serialization transaction.

Honda static evidence establishes Type110's streamConnectionID input and
{type, dataPort} response. Type111 response shape is a lab/prior-art profile,
not a Honda-confirmed schema. The serializer is Python's binary plist, not
Honda's CoreFoundation implementation.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import plistlib
from typing import Any, Mapping

MAX_ID = (1 << 64) - 1
MAX_STREAMS = 16


class SetupError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class StreamDescriptor:
    type: int
    stream_connection_id: int | None
    fields: Mapping[str, Any]


@dataclass(frozen=True)
class SetupRequest:
    streams: tuple[StreamDescriptor, ...]
    session_generation: int

    @classmethod
    def parse(cls, value: Mapping[str, Any], generation: int) -> "SetupRequest":
        if not isinstance(value, Mapping) or isinstance(generation, bool) or generation < 1:
            raise SetupError("invalid_setup_root")
        raw = value.get("streams")
        if not isinstance(raw, (list, tuple)) or len(raw) > MAX_STREAMS:
            raise SetupError("invalid_stream_array")
        streams: list[StreamDescriptor] = []
        ids: set[int] = set()
        secondary_count = 0
        for item in raw:
            if not isinstance(item, Mapping):
                raise SetupError("invalid_stream_descriptor")
            kind = item.get("type")
            if isinstance(kind, bool) or not isinstance(kind, int):
                raise SetupError("invalid_stream_type")
            cid = item.get("streamConnectionID")
            if kind in (110, 111):
                if isinstance(cid, bool) or not isinstance(cid, int) or not 1 <= cid <= MAX_ID:
                    raise SetupError("invalid_stream_connection_id")
                if cid in ids:
                    raise SetupError("duplicate_stream_connection_id")
                ids.add(cid)
            if kind == 111:
                secondary_count += 1
                if secondary_count > 1:
                    raise SetupError("duplicate_secondary")
            streams.append(StreamDescriptor(kind, cid if isinstance(cid, int) else None, deepcopy(dict(item))))
        return cls(tuple(streams), generation)


@dataclass(frozen=True)
class SetupResponse:
    fields: Mapping[str, Any]
    wire: bytes


def serialize_lab_plist(fields: Mapping[str, Any]) -> bytes:
    """Serialize a lab response; not a Honda serializer or a complete wire exchange."""
    try:
        wire = plistlib.dumps(deepcopy(dict(fields)), fmt=plistlib.FMT_BINARY, sort_keys=True)
    except (ValueError, TypeError, OverflowError) as exc:
        raise SetupError("response_not_serializable") from exc
    if len(wire) > 1_000_000:
        raise SetupError("response_too_large")
    return wire


def append_secondary(
    original: Mapping[str, Any], request: SetupRequest, port: int
) -> SetupResponse:
    """Append Type111 only after the caller has provisioned its listener.

    Original primary response and request objects are never mutated.
    """
    if not isinstance(original, Mapping):
        raise SetupError("invalid_primary_response")
    source = original.get("streams")
    if not isinstance(source, (tuple, list)) or any(not isinstance(x, Mapping) for x in source):
        raise SetupError("invalid_primary_response")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise SetupError("invalid_secondary_port")
    secondary = [stream for stream in request.streams if stream.type == 111]
    if len(secondary) != 1:
        raise SetupError("secondary_not_requested")
    candidate = deepcopy(dict(original))
    response_streams = deepcopy(list(source))
    # Prior-art clone profile; Honda Type111 acceptance remains unknown.
    entry = deepcopy(dict(secondary[0].fields))
    entry["type"] = 111
    entry["streamID"] = 111
    entry["dataPort"] = port
    response_streams.append(entry)
    candidate["streams"] = response_streams
    return SetupResponse(candidate, serialize_lab_plist(candidate))


def primary_unchanged(original: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    before = [x for x in original.get("streams", ()) if isinstance(x, Mapping) and x.get("type") == 110]
    after = [x for x in candidate.get("streams", ()) if isinstance(x, Mapping) and x.get("type") == 110]
    return before == after and serialize_lab_plist({"streams": before}) == serialize_lab_plist({"streams": after})
