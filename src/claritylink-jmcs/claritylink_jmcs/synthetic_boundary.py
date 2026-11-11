"""In-memory receiver-boundary producer for synthetic replay sessions only.

This host lab source emits bounded binary-plist boundary records from the
structured replay transport. It cannot attach to, open, or observe a Honda or
any network receiver.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import plistlib
from typing import Any, Callable, Mapping


class BoundaryTraceError(ValueError):
    pass


class SyntheticBoundaryRecorder:
    MAX_RECORDS = 64
    MAX_BODY_BYTES = 1_000_000
    SCHEMA = "claritylink-receiver-boundary-v1"

    def __init__(self, session_id: str, phase: str, *, clock: Callable[[], str] | None = None) -> None:
        if not session_id.startswith("synthetic-") or not phase.startswith("synthetic-"):
            raise BoundaryTraceError("synthetic_identity_required")
        if len(session_id) > 100 or len(phase) > 100:
            raise BoundaryTraceError("boundary_identity_too_long")
        self.session_id = session_id
        self.phase = phase
        self._clock = clock or (lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
        self._records: list[dict[str, Any]] = []
        self._capture_incomplete = False
        self._window_emitted = False
        self._session_emitted = False

    def _append(self, boundary: str, **fields: Any) -> None:
        reserved = 0 if boundary in {"window_closed", "session_closed"} else 2
        if len(self._records) >= self.MAX_RECORDS - reserved:
            raise BoundaryTraceError("boundary_record_limit")
        timestamp = self._clock()
        if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
            raise BoundaryTraceError("boundary_timestamp_must_be_utc")
        self._records.append({
            "schema": self.SCHEMA, "session_id": self.session_id, "phase": self.phase,
            "timestamp": timestamp, "boundary": boundary, **fields,
        })

    @staticmethod
    def _plist_base64(value: Mapping[str, Any]) -> str:
        if not isinstance(value, Mapping):
            raise BoundaryTraceError("boundary_payload_must_be_dictionary")
        try:
            raw = plistlib.dumps(dict(value), fmt=plistlib.FMT_BINARY, sort_keys=True)
        except (TypeError, ValueError, OverflowError) as exc:
            raise BoundaryTraceError("boundary_payload_not_plist_serializable") from exc
        if len(raw) > SyntheticBoundaryRecorder.MAX_BODY_BYTES:
            raise BoundaryTraceError("boundary_body_limit")
        return base64.b64encode(raw).decode("ascii")

    def info_response(self, request_id: str, status: int, payload: Mapping[str, Any]) -> None:
        self._append("info_response", request_id=request_id, complete=True, http_status=status,
                     body_base64=self._plist_base64(payload))

    def setup_request(self, request_id: str, payload: Mapping[str, Any]) -> None:
        self._append("setup_request", request_id=request_id, complete=True,
                     body_base64=self._plist_base64(payload))

    def setup_response(self, request_id: str, status: int, payload: Mapping[str, Any]) -> None:
        self._append("setup_response", request_id=request_id, complete=True, http_status=status,
                     body_base64=self._plist_base64(payload))

    def stream_created(self, request_id: str, stream_id: str, stream_type: int) -> None:
        self._append("stream_created", request_id=request_id, stream_id=stream_id, stream_type=stream_type)

    def media_observation(self, stream_id: str, stream_type: int, available: bool, complete: bool) -> None:
        self._append("media_observation", stream_id=stream_id, stream_type=stream_type,
                     available=available, complete=complete)

    def stream_closed(self, request_id: str, stream_id: str, stream_type: int) -> None:
        self._append("stream_closed", request_id=request_id, stream_id=stream_id, stream_type=stream_type)

    def session_closed(self, reason: str) -> None:
        if self._session_emitted:
            raise BoundaryTraceError("boundary_session_already_closed")
        self._append("session_closed", reason=reason)
        self._session_emitted = True

    def window_closed(self, setup_observation_complete: bool) -> None:
        if self._window_emitted:
            raise BoundaryTraceError("boundary_window_already_closed")
        self._append("window_closed", setup_observation_complete=(
            setup_observation_complete and not self._capture_incomplete))
        self._window_emitted = True

    def jsonl_bytes(self) -> bytes:
        """Return the exact synthetic replay artifact in memory; never writes a file."""
        if not self._records:
            raise BoundaryTraceError("empty_boundary_trace")
        return ("\n".join(json.dumps(row, sort_keys=True, separators=(",", ":"))
                              for row in self._records) + "\n").encode("utf-8")

    def mark_capture_incomplete(self) -> None:
        self._capture_incomplete = True

    def finish(self) -> None:
        """Close the observation window conservatively and mark session end."""
        if not self._window_emitted:
            self.window_closed(False)
        if not self._session_emitted:
            self.session_closed("synthetic-session-close")
