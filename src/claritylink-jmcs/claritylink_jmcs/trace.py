"""Allowlisted metadata trace. No peer or authentication values."""
from __future__ import annotations

from enum import Enum
from datetime import datetime, timezone
from typing import Any


class TraceError(RuntimeError):
    pass


class TraceEvent(str, Enum):
    AUTH_START = "AUTH_START"
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"
    SESSION_OPEN = "SESSION_OPEN"
    SESSION_CLOSE = "SESSION_CLOSE"
    CONTROL_REQUEST = "CONTROL_REQUEST"
    INFO_REQUEST = "INFO_REQUEST"
    INFO_RESPONSE = "INFO_RESPONSE"
    SETUP_REQUEST = "SETUP_REQUEST"
    SETUP_TYPE110 = "SETUP_TYPE110"
    SETUP_TYPE111 = "SETUP_TYPE111"
    SETUP_RESPONSE = "SETUP_RESPONSE"
    LISTENER_CREATE = "LISTENER_CREATE"
    LISTENER_CONNECT = "LISTENER_CONNECT"
    SECURITY_INIT = "SECURITY_INIT"
    MEDIA_CONNECT = "MEDIA_CONNECT"
    MEDIA_START = "MEDIA_START"
    MEDIA_STOP = "MEDIA_STOP"
    SESSION_TEARDOWN = "SESSION_TEARDOWN"


class SanitizedTrace:
    ALLOWED = {"generation", "stream_type", "status", "profile", "method", "path",
               "content_type", "field_types"}
    STATUSES = {"begin", "ok", "failed", "closed", "timeout", "blocked"}
    PROFILES = {"legacy", "modern", "unknown", "clear_lab"}
    METHODS = {"GET", "SETUP", "other"}
    PATHS = {"/info", "/session", "other"}
    CONTENT_TYPES = {"application/x-apple-binary-plist", "application/x-plist", "unknown"}
    FIELD_KEYS = {"streams", "type", "streamConnectionID", "enabledFeatures", "altScreenURLs",
                  "audioFormats", "audioLatencies", "hidDevices", "displays", "features",
                  "modes", "resources", "sourceVersion", "statusFlags"}

    def __init__(self, limit: int = 1024) -> None:
        if not 1 <= limit <= 100_000:
            raise TraceError("invalid_trace_limit")
        self.limit = limit
        self.events: list[dict[str, Any]] = []

    def emit(self, event: TraceEvent, **metadata: Any) -> None:
        if not isinstance(event, TraceEvent) or set(metadata) - self.ALLOWED:
            raise TraceError("unsafe_trace_event")
        if len(self.events) >= self.limit:
            raise TraceError("trace_limit")
        for key, value in metadata.items():
            if key == "generation" and (isinstance(value, bool) or not isinstance(value, int) or value < 1):
                raise TraceError("invalid_trace_generation")
            if key == "stream_type" and value not in (110, 111):
                raise TraceError("invalid_trace_stream_type")
            if key == "status" and value not in self.STATUSES:
                raise TraceError("invalid_trace_status")
            if key == "profile" and value not in self.PROFILES:
                raise TraceError("invalid_trace_profile")
            if key == "method" and value not in self.METHODS:
                raise TraceError("invalid_trace_method")
            if key == "path" and value not in self.PATHS:
                raise TraceError("invalid_trace_path")
            if key == "content_type" and value not in self.CONTENT_TYPES:
                raise TraceError("invalid_trace_content_type")
            if key == "field_types" and (not isinstance(value, list) or len(value) > 128 or
                                          any(not isinstance(x, str) or len(x) > 128 for x in value)):
                raise TraceError("invalid_field_types")
        self.events.append({"timestamp": datetime.now(timezone.utc).isoformat(),
                            "event": event.value, **metadata})

    def emit_request(self, request: Any) -> None:
        """Record known field paths, types and array sizes without values."""
        fields: list[str] = []
        def walk(value: Any, path: str, depth: int) -> None:
            if len(fields) >= 128 or depth > 8:
                return
            if isinstance(value, dict):
                for key, item in value.items():
                    name = key if isinstance(key, str) and key in self.FIELD_KEYS else "<unknown>"
                    child = (path + "." + name).strip(".")
                    kind = "dictionary" if isinstance(item, dict) else (
                        "array:" + str(len(item)) if isinstance(item, (list, tuple)) else type(item).__name__)
                    fields.append(child + ":" + kind)
                    walk(item, child, depth + 1)
            elif isinstance(value, (list, tuple)):
                for item in value[:16]:
                    walk(item, path + "[]", depth + 1)
        walk(request.body, "", 0)
        self.emit(TraceEvent.CONTROL_REQUEST, generation=request.generation,
                  method=request.method if request.method in self.METHODS else "other",
                  path=request.path if request.path in self.PATHS else "other",
                  content_type=request.content_type if request.content_type in self.CONTENT_TYPES else "unknown",
                  field_types=fields[:128])
