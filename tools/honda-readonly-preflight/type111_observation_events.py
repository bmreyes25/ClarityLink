"""Correlated, provenance-bound Type111 boundary trace reader (host only).

The trace file is the preserved source artifact. Its digest and record offsets are
computed during ingestion; caller-supplied digest strings are never trusted.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

EVENTS = {
    "info_response", "setup_request", "setup_response", "stream_created",
    "media_observation", "stream_closed", "session_closed", "window_closed",
}
HEX = re.compile(r"^[0-9a-f]{64}$")
SCHEMA = "claritylink-type111-observation-v2"


class EventError(ValueError):
    pass


@dataclass(frozen=True)
class Trace:
    artifact_sha256: str
    method: str
    events: tuple[dict[str, Any], ...]
    source_records: tuple[tuple[int, int], ...]
    raw_artifact: bytes
    source_format: str


def _utc(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def _is_json_value(value: Any) -> bool:
    if value is None or type(value) in (str, int, float, bool):
        return True
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())
    return False


def validate_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise EventError("event must be an object")
    required = {"schema", "session_id", "phase", "timestamp", "event", "correlation", "data"}
    if set(event) != required:
        raise EventError("event has missing or unknown top-level fields")
    if event["schema"] != SCHEMA:
        raise EventError("unsupported event schema")
    for key in ("session_id", "phase"):
        if not isinstance(event[key], str) or not event[key] or len(event[key]) > 100:
            raise EventError(f"{key} must be a nonempty bounded string")
    if not _utc(event["timestamp"]):
        raise EventError("timestamp must be an ISO-8601 UTC timestamp ending in Z")
    corr = event["correlation"]
    if not isinstance(corr, dict) or set(corr) != {"request_id", "stream_id"}:
        raise EventError("correlation must contain request_id and stream_id")
    for key in ("request_id", "stream_id"):
        value = corr[key]
        if value is not None and (not isinstance(value, str) or not value or len(value) > 200):
            raise EventError(f"{key} must be null or a nonempty bounded string")
    kind, data = event["event"], event["data"]
    if kind not in EVENTS or not isinstance(data, dict) or not _is_json_value(data):
        raise EventError("unknown event type or non-JSON data")
    expected = {
        "info_response": {"complete", "http_status", "body_base64", "payload"},
        "setup_request": {"complete", "body_base64", "payload"},
        "setup_response": {"complete", "http_status", "body_base64", "payload"},
        "stream_created": {"stream_type"},
        "media_observation": {"stream_type", "available", "complete"},
        "stream_closed": {"stream_type"},
        "session_closed": {"reason"},
        "window_closed": {"setup_observation_complete"},
    }[kind]
    if set(data) != expected:
        raise EventError(f"{kind} data fields do not match schema")
    if kind == "info_response":
        if (type(data["complete"]) is not bool or type(data["http_status"]) is not int
                or not 100 <= data["http_status"] <= 599 or not isinstance(data["body_base64"], str)
                or not isinstance(data["payload"], dict) or corr["request_id"] is None):
            raise EventError("info response must preserve request ID, HTTP status, body bytes and decoded payload")
    elif kind == "setup_request":
        if type(data["complete"]) is not bool or not isinstance(data["body_base64"], str) or not isinstance(data["payload"], dict):
            raise EventError("setup request must preserve body bytes and decoded payload")
        if corr["request_id"] is None:
            raise EventError("setup request requires a request_id")
    elif kind == "setup_response":
        if (type(data["complete"]) is not bool or type(data["http_status"]) is not int
                or not 100 <= data["http_status"] <= 599 or not isinstance(data["body_base64"], str)
                or not isinstance(data["payload"], dict)):
            raise EventError("setup response must preserve HTTP status, body bytes and decoded payload")
        if corr["request_id"] is None:
            raise EventError("setup response requires a request_id")
    elif kind in {"stream_created", "stream_closed"}:
        if type(data["stream_type"]) is not int or corr["request_id"] is None or corr["stream_id"] is None:
            raise EventError("stream event requires type, request_id and stream_id")
    elif kind == "media_observation":
        if (type(data["stream_type"]) is not int or type(data["available"]) is not bool
                or type(data["complete"]) is not bool or corr["stream_id"] is None):
            raise EventError("media observation requires stream_id and typed fields")
    elif kind == "session_closed":
        if not isinstance(data["reason"], str) or not data["reason"]:
            raise EventError("session close reason must be a nonempty string")
    elif type(data["setup_observation_complete"]) is not bool:
        raise EventError("window completeness must be boolean")
    return event


def verify_artifact(data: bytes, expected_sha256: str) -> None:
    if not isinstance(expected_sha256, str) or not HEX.fullmatch(expected_sha256):
        raise EventError("expected SHA-256 must be 64 lowercase hexadecimal characters")
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise EventError("source artifact SHA-256 mismatch")


def parse_jsonl(raw: bytes | str, *, method: str, expected_sha256: str | None = None) -> Trace:
    """Load an actual trace artifact and derive provenance from its bytes."""
    if not isinstance(method, str) or not method or len(method) > 120:
        raise EventError("method must be a nonempty bounded source description")
    data = raw.encode("utf-8") if isinstance(raw, str) else raw
    if not isinstance(data, bytes):
        raise EventError("trace artifact must be bytes or text")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EventError("trace artifact must be UTF-8 JSONL") from exc
    events: list[dict[str, Any]] = []
    pointers: list[tuple[int, int]] = []
    offset = 0
    for line_no, line in enumerate(text.splitlines(keepends=True), 1):
        line_bytes = line.encode("utf-8")
        if not line.strip():
            offset += len(line_bytes)
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EventError(f"line {line_no}: invalid JSON") from exc
        try:
            events.append(validate_event(event))
            pointers.append((offset, len(line_bytes.rstrip(b"\r\n"))))
        except EventError as exc:
            raise EventError(f"line {line_no}: {exc}") from exc
        offset += len(line_bytes)
    if not events:
        raise EventError("event stream is empty")
    if len({e["session_id"] for e in events}) != 1:
        raise EventError("one JSONL file must contain exactly one session")
    if events != sorted(events, key=lambda e: e["timestamp"]):
        raise EventError("events must be ordered by timestamp")
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None:
        verify_artifact(data, expected_sha256)
    return Trace(digest, method, tuple(events), tuple(pointers), data, "events")


def _types(descriptors: Any) -> set[int]:
    if not isinstance(descriptors, list):
        raise EventError("stream descriptor array missing or malformed")
    result: set[int] = set()
    for descriptor in descriptors:
        if (not isinstance(descriptor, dict) or type(descriptor.get("type")) is not int
                or descriptor["type"] < 0):
            raise EventError("stream descriptor missing a valid numeric type")
        result.add(descriptor["type"])
    return result


def classify(trace: Trace) -> list[str]:
    if not isinstance(trace, Trace):
        raise EventError("classification requires a parsed, hashed trace artifact")
    # Re-derive from immutable source bytes. Never trust the mutable dictionaries
    # cached on a caller-constructed or previously modified Trace object.
    if trace.source_format == "boundary":
        from type111_boundary_source import parse_boundary_jsonl
        verified = parse_boundary_jsonl(trace.raw_artifact, method=trace.method,
                                        expected_sha256=trace.artifact_sha256)
    elif trace.source_format == "events":
        verified = parse_jsonl(trace.raw_artifact, method=trace.method,
                               expected_sha256=trace.artifact_sha256)
    else:
        raise EventError("unsupported trace source format")
    events = list(verified.events)
    phases = {event["phase"] for event in events}
    if len(phases) != 1:
        raise EventError("classify one phase at a time; cross-phase joins are forbidden")
    info = [e for e in events if e["event"] == "info_response"]
    requests = [e for e in events if e["event"] == "setup_request"]
    responses = [e for e in events if e["event"] == "setup_response"]
    windows = [e for e in events if e["event"] == "window_closed"]
    accepted: set[str] = set()
    setup_errors: set[str] = set()
    inconclusive: set[str] = set()
    request_types: dict[str, set[int]] = {}
    ambiguous_requests: set[str] = set()
    for request in requests:
        rid = request["correlation"]["request_id"]
        if not request["data"]["complete"]:
            continue
        try:
            request_types[rid] = _types(request["data"]["payload"].get("streams"))
        except EventError:
            ambiguous_requests.add(rid)
    requested = {rid for rid, types in request_types.items() if 111 in types}
    outcomes: list[str] = []
    if (info and info[-1]["data"]["complete"]
            and 200 <= info[-1]["data"]["http_status"] < 300):
        # Preserve all fields; count is an inventory observation, not a claim
        # about undocumented descriptor semantics.
        displays = info[-1]["data"]["payload"].get("displays")
        if isinstance(displays, list) and all(isinstance(item, dict) for item in displays):
            outcomes.append(f"info_display_descriptors:{len(displays)}")
        else:
            outcomes.append("info_display_inventory_inconclusive")
    req_by_id = {e["correlation"]["request_id"]: e for e in requests}
    if len(req_by_id) != len(requests):
        raise EventError("duplicate setup request_id values are ambiguous")
    response_ids = [e["correlation"]["request_id"] for e in responses]
    if len(set(response_ids)) != len(response_ids):
        raise EventError("duplicate setup response request_id values are ambiguous")
    for response in responses:
        rid = response["correlation"]["request_id"]
        req = req_by_id.get(rid)
        if req is None or rid not in requested or not response["data"]["complete"]:
            continue
        status = response["data"]["http_status"]
        if status >= 400:
            setup_errors.add(rid)
            continue
        try:
            response_types = _types(response["data"]["payload"].get("streams"))
        except EventError:
            inconclusive.add(rid)
            continue
        if 200 <= status < 300 and 111 in response_types:
            accepted.add(rid)
        else:
            inconclusive.add(rid)
    if requested:
        outcomes.append("type111_requested")
    responded_ids = {e["correlation"]["request_id"] for e in responses if e["data"]["complete"]}
    if requested - responded_ids:
        outcomes.append("type111_request_without_complete_response")
    if ambiguous_requests:
        outcomes.append("setup_request_descriptor_inconclusive")
    if setup_errors:
        outcomes.append("type111_setup_error_response_observed")
    if accepted:
        outcomes.append("type111_accepted")
    if inconclusive:
        outcomes.append("type111_response_semantics_inconclusive")
    successful_type110_responses: set[str] = set()
    for response in responses:
        if not response["data"]["complete"] or not 200 <= response["data"]["http_status"] < 300:
            continue
        try:
            types = _types(response["data"]["payload"].get("streams"))
        except EventError:
            continue
        if 110 in types:
            successful_type110_responses.add(response["correlation"]["request_id"])
    if any(rid in request_types and 110 in request_types[rid] and rid in successful_type110_responses
           for rid in request_types):
        outcomes.append("type110_setup_observed")
    streams = [e for e in events if e["event"] == "stream_created"
               and e["data"]["stream_type"] == 111
               and e["correlation"]["request_id"] in accepted]
    if streams:
        outcomes.append("type111_stream_created")
    stream_ids = {e["correlation"]["stream_id"] for e in streams}
    media = [e for e in events if e["event"] == "media_observation"
             and e["data"]["stream_type"] == 111 and e["correlation"]["stream_id"] in stream_ids]
    if any(e["data"]["complete"] and not e["data"]["available"] for e in media):
        outcomes.append("stream_created_media_unavailable")
    if any(e["data"]["complete"] and e["data"]["available"] for e in media):
        outcomes.append("stream_media_available")
    if (info and info[-1]["data"]["complete"] and 200 <= info[-1]["data"]["http_status"] < 300
            and windows and windows[-1]["data"]["setup_observation_complete"]):
        all_complete = all(e["data"]["complete"] for e in requests)
        if all_complete and not requested and not ambiguous_requests and not responses:
            outcomes.append("complete_info_and_setup_window_without_type111_request")
    closed_ids = {e["correlation"]["stream_id"] for e in events if e["event"] == "stream_closed" and e["data"]["stream_type"] == 111}
    if closed_ids & stream_ids:
        outcomes.append("type111_stream_teardown_observed")
    if any(e["event"] == "session_closed" for e in events):
        outcomes.append("session_teardown_observed")
    return outcomes or ["insufficient_observation"]
