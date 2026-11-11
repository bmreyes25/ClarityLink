"""Decode a private exported receiver-boundary trace into correlated events.

This is an offline source adapter, not target instrumentation. The trace format
preserves raw plist bodies and the receiver call-boundary label chosen by the
capture producer. No ADB, socket, device, or receiver process is opened here.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import plistlib
from datetime import datetime, timezone
from typing import Any

from type111_observation_events import EventError, Trace, validate_event, verify_artifact

SCHEMA = "claritylink-receiver-boundary-v1"
BASE = {"schema", "session_id", "phase", "timestamp", "boundary"}


def _plist(value: Any, line_no: int) -> tuple[bytes, dict[str, Any]]:
    if not isinstance(value, str):
        raise EventError(f"line {line_no}: body_base64 must be a string")
    try:
        raw = base64.b64decode(value, validate=True)
        decoded = plistlib.loads(raw) if raw else {}
    except (binascii.Error, plistlib.InvalidFileException, ValueError) as exc:
        raise EventError(f"line {line_no}: invalid encoded plist body") from exc
    if not isinstance(decoded, dict):
        raise EventError(f"line {line_no}: decoded plist must be a dictionary")
    return raw, decoded


def _json_value(value: Any) -> Any:
    """Preserve plist-only values in explicit JSON-safe encodings."""
    if isinstance(value, bytes):
        return {"$plist_data_base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, datetime):
        normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        return {"$plist_date_utc": normalized.isoformat().replace("+00:00", "Z")}
    if isinstance(value, plistlib.UID):
        return {"$plist_uid": value.data}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise EventError("plist dictionary keys must be strings")
        return {key: _json_value(item) for key, item in value.items()}
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise EventError("unsupported plist value type")


def parse_boundary_jsonl(raw: bytes, *, method: str = "receiver-boundary-export", expected_sha256: str | None = None) -> Trace:
    """Parse an exported plaintext application-boundary JSONL source artifact.

    The upstream exporter must label the decoded receiver boundary and retain
    the exact body bytes. This adapter validates and derives protocol facts;
    it does not manufacture missing receiver observations.
    """
    if not isinstance(raw, bytes):
        raise EventError("boundary source must be bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EventError("boundary source must be UTF-8 JSONL") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None:
        verify_artifact(raw, expected_sha256)
    events: list[dict[str, Any]] = []
    pointers: list[tuple[int, int]] = []
    offset = 0
    session_id: str | None = None
    for line_no, line in enumerate(text.splitlines(keepends=True), 1):
        encoded = line.encode("utf-8")
        if not line.strip():
            offset += len(encoded)
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EventError(f"line {line_no}: invalid JSON") from exc
        if not isinstance(record, dict) or not BASE <= set(record) or record.get("schema") != SCHEMA:
            raise EventError(f"line {line_no}: invalid boundary record header")
        if session_id is None:
            session_id = record["session_id"]
        if record["session_id"] != session_id:
            raise EventError("one source artifact must contain exactly one session")
        boundary = record["boundary"]
        corr = {"request_id": record.get("request_id"), "stream_id": record.get("stream_id")}
        if boundary in {"info_response", "setup_request", "setup_response"}:
            allowed = BASE | {"request_id", "body_base64", "complete"}
            if boundary in {"info_response", "setup_response"}:
                allowed |= {"http_status"}
            if set(record) != allowed:
                raise EventError(f"line {line_no}: unexpected fields for {boundary}")
            body, payload = _plist(record["body_base64"], line_no)
            data: dict[str, Any] = {
                "complete": record["complete"],
                "body_base64": base64.b64encode(body).decode("ascii"),
                "payload": _json_value(payload),
            }
            if boundary in {"info_response", "setup_response"}:
                data["http_status"] = record["http_status"]
        elif boundary == "stream_created":
            if set(record) != BASE | {"request_id", "stream_id", "stream_type"}:
                raise EventError(f"line {line_no}: invalid stream_created fields")
            data = {"stream_type": record["stream_type"]}
        elif boundary == "media_observation":
            if set(record) != BASE | {"stream_id", "stream_type", "available", "complete"}:
                raise EventError(f"line {line_no}: invalid media_observation fields")
            corr["request_id"] = None
            data = {k: record[k] for k in ("stream_type", "available", "complete")}
        elif boundary == "stream_closed":
            if set(record) != BASE | {"request_id", "stream_id", "stream_type"}:
                raise EventError(f"line {line_no}: invalid stream_closed fields")
            data = {"stream_type": record["stream_type"]}
        elif boundary == "session_closed":
            if set(record) != BASE | {"reason"}:
                raise EventError(f"line {line_no}: invalid session_closed fields")
            corr = {"request_id": None, "stream_id": None}
            data = {"reason": record["reason"]}
        elif boundary == "window_closed":
            if set(record) != BASE | {"setup_observation_complete"}:
                raise EventError(f"line {line_no}: invalid window_closed fields")
            corr = {"request_id": None, "stream_id": None}
            data = {"setup_observation_complete": record["setup_observation_complete"]}
        else:
            raise EventError(f"line {line_no}: unknown receiver boundary")
        event = {
            "schema": "claritylink-type111-observation-v2",
            "session_id": record["session_id"], "phase": record["phase"],
            "timestamp": record["timestamp"], "event": boundary,
            "correlation": corr, "data": data,
        }
        events.append(validate_event(event))
        pointers.append((offset, len(encoded.rstrip(b"\r\n"))))
        offset += len(encoded)
    if not events:
        raise EventError("boundary source is empty")
    if events != sorted(events, key=lambda e: e["timestamp"]):
        raise EventError("boundary records must be ordered by timestamp")
    return Trace(digest, method, tuple(events), tuple(pointers), raw, "boundary")
