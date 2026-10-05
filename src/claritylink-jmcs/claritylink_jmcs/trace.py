"""Allowlisted phase-only receiver trace. No peer or authentication values."""
from __future__ import annotations

from enum import Enum
from typing import Any


class TraceError(RuntimeError):
    pass


class TraceEvent(str, Enum):
    AUTH_START = "AUTH_START"
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"
    SESSION_OPEN = "SESSION_OPEN"
    SESSION_CLOSE = "SESSION_CLOSE"
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
    ALLOWED = {"generation", "stream_type", "status", "profile"}
    STATUSES = {"begin", "ok", "failed", "closed", "timeout", "blocked"}
    PROFILES = {"legacy", "modern", "unknown", "clear_lab"}

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
        self.events.append({"event": event.value, **metadata})
