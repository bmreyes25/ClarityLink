"""Parse host-side decoded Type111 observation events; no device access."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

EVENTS = {
    "info_response", "setup_request", "setup_response", "stream_created",
    "media_observation", "stream_closed", "session_closed", "window_closed",
}
HEX = re.compile(r"^[0-9a-f]{64}$")


class EventError(ValueError):
    pass


def _utc(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def validate_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise EventError("event must be an object")
    required = {"schema", "session_id", "phase", "timestamp", "source", "event", "data"}
    if set(event) != required:
        raise EventError("event has missing or unknown top-level fields")
    if event["schema"] != "claritylink-type111-observation-v1":
        raise EventError("unsupported event schema")
    for key in ("session_id", "phase"):
        if not isinstance(event[key], str) or not event[key] or len(event[key]) > 100:
            raise EventError(f"{key} must be a nonempty bounded string")
    if not _utc(event["timestamp"]):
        raise EventError("timestamp must be an ISO-8601 UTC timestamp ending in Z")
    source = event["source"]
    if (not isinstance(source, dict) or set(source) != {"method", "artifact_sha256", "record_id"}
            or not all(isinstance(source[k], str) and source[k] for k in source)
            or not HEX.fullmatch(source["artifact_sha256"])):
        raise EventError("source must identify a method, SHA-256 artifact, and record")
    kind, data = event["event"], event["data"]
    if kind not in EVENTS or not isinstance(data, dict):
        raise EventError("unknown event type or non-object data")
    expected = {
        "info_response": {"complete", "secondary_advertised"},
        "setup_request": {"complete", "stream_types"},
        "setup_response": {"complete", "stream_type", "result"},
        "stream_created": {"stream_type", "stream_id"},
        "media_observation": {"stream_type", "available", "complete"},
        "stream_closed": {"stream_type", "stream_id"},
        "session_closed": {"reason"},
        "window_closed": {"setup_observation_complete"},
    }[kind]
    if set(data) != expected:
        raise EventError(f"{kind} data fields do not match schema")
    if kind == "info_response":
        if type(data["complete"]) is not bool or type(data["secondary_advertised"]) is not bool:
            raise EventError("info response flags must be booleans")
    elif kind == "setup_request":
        types = data["stream_types"]
        if type(data["complete"]) is not bool or not isinstance(types, list) or any(type(t) is not int or t < 0 for t in types):
            raise EventError("setup request completeness or stream_types is invalid")
    elif kind == "setup_response":
        if type(data["complete"]) is not bool or type(data["stream_type"]) is not int or data["result"] not in {"accepted", "rejected"}:
            raise EventError("setup response needs a numeric type and accepted/rejected result")
    elif kind in {"stream_created", "stream_closed"}:
        if type(data["stream_type"]) is not int or not isinstance(data["stream_id"], str) or not data["stream_id"]:
            raise EventError("stream event needs a numeric type and nonempty stream_id")
    elif kind == "media_observation":
        if type(data["stream_type"]) is not int or type(data["available"]) is not bool or type(data["complete"]) is not bool:
            raise EventError("media observation fields have invalid types")
    elif kind == "session_closed":
        if not isinstance(data["reason"], str) or not data["reason"]:
            raise EventError("session close reason must be a nonempty string")
    elif type(data["setup_observation_complete"]) is not bool:
        raise EventError("window completeness must be boolean")
    return event


def parse_jsonl(text: str) -> list[dict[str, Any]]:
    result = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EventError(f"line {line_no}: invalid JSON") from exc
        try:
            result.append(validate_event(event))
        except EventError as exc:
            raise EventError(f"line {line_no}: {exc}") from exc
    if not result:
        raise EventError("event stream is empty")
    if len({e["session_id"] for e in result}) != 1:
        raise EventError("one JSONL file must contain exactly one session")
    if result != sorted(result, key=lambda e: e["timestamp"]):
        raise EventError("events must be ordered by timestamp")
    return result


def classify(events: Iterable[dict[str, Any]]) -> list[str]:
    events = [validate_event(e) for e in events]
    info = [e["data"] for e in events if e["event"] == "info_response"]
    requests = [e["data"] for e in events if e["event"] == "setup_request"]
    responses = [e["data"] for e in events if e["event"] == "setup_response" and e["data"]["stream_type"] == 111]
    streams = [e["data"] for e in events if e["event"] == "stream_created" and e["data"]["stream_type"] == 111]
    media = [e["data"] for e in events if e["event"] == "media_observation" and e["data"]["stream_type"] == 111]
    outcomes: list[str] = []
    if info and info[-1]["complete"] and not info[-1]["secondary_advertised"]:
        outcomes.append("no_secondary_capability_advertised")
    if any(r["complete"] and 111 in r["stream_types"] for r in requests):
        outcomes.append("type111_requested")
    if any(r["complete"] and r["result"] == "rejected" for r in responses):
        outcomes.append("type111_rejected")
    if any(r["complete"] and r["result"] == "accepted" for r in responses):
        outcomes.append("type111_accepted")
    if streams:
        outcomes.append("type111_stream_created")
    if streams and any(m["complete"] and not m["available"] for m in media):
        outcomes.append("stream_created_media_unavailable")
    if streams and any(m["complete"] and m["available"] for m in media):
        outcomes.append("stream_media_available")
    window_complete = any(e["data"]["setup_observation_complete"] for e in events if e["event"] == "window_closed")
    requests_complete = all(r["complete"] for r in requests)
    if (info and info[-1]["complete"] and info[-1]["secondary_advertised"]
            and not any(r["complete"] and 111 in r["stream_types"] for r in requests)
            and not responses and not streams and requests_complete and window_complete):
        outcomes.append("advertised_but_no_type111_request")
    if any(e["event"] == "stream_closed" and e["data"]["stream_type"] == 111 for e in events):
        outcomes.append("type111_stream_teardown_observed")
    if any(e["event"] == "session_closed" for e in events):
        outcomes.append("session_teardown_observed")
    if not outcomes:
        outcomes.append("insufficient_observation")
    return outcomes


def verify_artifact(data: bytes, expected_sha256: str) -> None:
    if not HEX.fullmatch(expected_sha256) or hashlib.sha256(data).hexdigest() != expected_sha256:
        raise EventError("source artifact SHA-256 mismatch")
