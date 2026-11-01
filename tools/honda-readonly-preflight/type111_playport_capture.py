"""Bounded, private collector for PlayPort's allowlisted OracleDiagnostics stream.

The input can be the JSONL returned by PlayPort's OracleDiagnostics.jsonLines()
or its SLF4J SimpleLogger line (``type111-oracle - {json}``). Non-oracle log
lines are discarded in memory. Only validated OracleEvent JSON objects are
written to the private evidence directory.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Iterable

from type111_observation_events import EventError, Trace, classify
from type111_playport_source import MAX_EVENTS, parse_playport_jsonl

MAX_LOG_LINE_BYTES = 64 * 1024
MAX_LOG_BYTES = 32 * 1024 * 1024
MAX_EVENT_BYTES = 4 * 1024 * 1024
_COMMIT = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_LABEL = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
_LOGGER_MARKER = b"type111-oracle - "


class CaptureError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _event_payload(line: bytes) -> bytes | None:
    """Select only direct OracleEvent JSON or a line from its named logger."""
    stripped = line.rstrip(b"\r\n")
    if not stripped:
        return None
    if stripped.startswith(b"{"):
        return stripped
    if b"type111-oracle" not in stripped:
        return None
    if stripped.count(_LOGGER_MARKER) != 1:
        raise CaptureError("unrecognized PlayPort oracle logger line")
    payload = stripped.split(_LOGGER_MARKER, 1)[1].strip()
    if not payload.startswith(b"{"):
        raise CaptureError("PlayPort oracle logger message is not an event object")
    return payload


def _bounded_lines(stream) -> Iterable[bytes]:
    """Read without allowing a single hostile line to allocate unbounded memory."""
    while True:
        line = stream.readline(MAX_LOG_LINE_BYTES + 1)
        if not line:
            return
        yield line
        if len(line) > MAX_LOG_LINE_BYTES:
            return


def _coverage(events: tuple[dict, ...]) -> dict:
    has = lambda phase, event: any(row["phase"] == phase and row["event"] == event for row in events)
    session_markers = sum(row["phase"] == "SESSION_SETUP" and row["event"] == "features_negotiated"
                          for row in events)
    types = lambda phase, event: sorted({row["streamType"] for row in events
                                         if row["phase"] == phase and row["event"] == event
                                         and row["streamType"] in (110, 111)})
    stopped = set(types("TEARDOWN", "stopped"))
    return {
        "session_setup_marker_count": session_markers,
        "exactly_one_session_marker": session_markers == 1,
        "request_response_correlation_id_observed": False,
        "info_request_observed": has("INFO_REQUEST", "received"),
        "info_response_observed": has("INFO_RESPONSE", "advertised"),
        "display_types_observed": types("INFO_RESPONSE", "display"),
        "setup_request_observed": has("STREAM_SETUP", "requested"),
        "setup_listener_types_observed": types("STREAM_SETUP", "listener_ready"),
        "stream_active_types_observed": types("STREAM_ACTIVE", "active"),
        "stream_socket_types_observed": types("STREAM_ACTIVE", "socket_open"),
        "video_config_types_observed": types("VIDEO_CONFIG", "received"),
        "first_frame_types_observed": types("VIDEO_FRAME", "first_frame"),
        "stream_teardown_types_observed": sorted(stopped),
        # Current PlayPort oracle records do not report RTSP response status or
        # a parent-session close event. Never infer either from listener/media
        # events or server shutdown.
        "rtsp_response_status_observed": False,
        "parent_session_termination_observed": False,
        "protocol_observation_window_complete": False,
    }


@dataclass(frozen=True)
class CaptureArtifact:
    event_bytes: bytes
    manifest: dict


class PlayPortCapture:
    """Consume a bounded receiver event stream and retain only safe event JSON."""

    def __init__(self, *, receiver_commit: str, phase_label: str):
        if not isinstance(receiver_commit, str) or not _COMMIT.fullmatch(receiver_commit):
            raise CaptureError("receiver commit must be a full lowercase Git SHA")
        if not isinstance(phase_label, str) or not _LABEL.fullmatch(phase_label):
            raise CaptureError("phase label must be a short safe token")
        self.receiver_commit = receiver_commit
        self.phase_label = phase_label
        self.started_at = _utc_now()
        self._raw_bytes = 0
        self._event_bytes = 0
        self._accepted: list[bytes] = []
        self._seen: set[bytes] = set()
        self._failure: str | None = None
        self._finished = False

    def feed(self, line: bytes) -> None:
        if self._finished:
            raise CaptureError("capture already finalized")
        if self._failure:
            return
        if not isinstance(line, bytes):
            self._failure = "invalid_input_type"
            return
        self._raw_bytes += len(line)
        if len(line) > MAX_LOG_LINE_BYTES:
            self._failure = "log_line_limit"
            return
        if self._raw_bytes > MAX_LOG_BYTES:
            self._failure = "log_input_limit"
            return
        try:
            payload = _event_payload(line)
            if payload is None:
                return
            row_bytes = payload + b"\n"
            self._event_bytes += len(row_bytes)
            if self._event_bytes > MAX_EVENT_BYTES:
                self._failure = "event_bytes_limit"
                return
            trace = parse_playport_jsonl(row_bytes)
            row = trace.events[0]
            signature = json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
            if signature in self._seen:
                self._failure = "duplicate_event"
                return
            if len(self._accepted) >= MAX_EVENTS:
                self._failure = "event_count_limit"
                return
            self._seen.add(signature)
            self._accepted.append(row_bytes)
        except (CaptureError, EventError):
            self._failure = "invalid_or_unreviewed_event"

    @property
    def stopped(self) -> bool:
        return self._failure is not None

    def finish(self, *, interrupted: bool = False) -> CaptureArtifact:
        if self._finished:
            raise CaptureError("capture already finalized")
        self._finished = True
        ended_at = _utc_now()
        event_bytes = b"".join(self._accepted)
        trace: Trace | None = None
        if event_bytes:
            trace = parse_playport_jsonl(event_bytes)
        rows = trace.events if trace else ()
        event_times = [row["monotonicTimeNs"] for row in rows]
        source_complete = not interrupted and self._failure is None
        manifest = {
            "schema": "claritylink-playport-capture-v1",
            "receiver": "PlayPort",
            "receiver_commit_as_reported": self.receiver_commit,
            "receiver_commit_independently_bound_to_event_bytes": False,
            "capture_phase": self.phase_label,
            "ingest_started_utc": self.started_at,
            "ingest_finished_utc": ended_at,
            "ingest_time_is_source_event_wall_time": False,
            "source_stream_complete": source_complete,
            "observer_interrupted": bool(interrupted),
            "capture_failure": self._failure,
            "input_log_bytes_seen": self._raw_bytes,
            "validated_event_count": len(rows),
            "first_source_monotonic_time_ns": rows[0]["monotonicTimeNs"] if rows else None,
            "last_source_monotonic_time_ns": rows[-1]["monotonicTimeNs"] if rows else None,
            "minimum_source_monotonic_time_ns": min(event_times) if event_times else None,
            "maximum_source_monotonic_time_ns": max(event_times) if event_times else None,
            "event_times_monotonic_in_log_order": all(
                later >= earlier for earlier, later in zip(event_times, event_times[1:])),
            "source_event_sha256": hashlib.sha256(event_bytes).hexdigest(),
            "coverage": _coverage(rows),
            "findings": classify(trace) if trace else ["insufficient_playport_observation"],
            "raw_non_oracle_log_lines_retained": False,
        }
        return CaptureArtifact(event_bytes, manifest)


def ingest_lines(lines: Iterable[bytes], *, receiver_commit: str, phase_label: str,
                 interrupted: bool = False) -> CaptureArtifact:
    capture = PlayPortCapture(receiver_commit=receiver_commit, phase_label=phase_label)
    try:
        for line in lines:
            capture.feed(line)
            if capture.stopped:
                break
    except KeyboardInterrupt:
        interrupted = True
    return capture.finish(interrupted=interrupted)


def _write_private(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short write while finalizing private capture")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def write_private_capture(artifact: CaptureArtifact, destination: Path,
                          *, repository_root: Path) -> tuple[Path, Path]:
    destination = Path(destination).expanduser().resolve(strict=False)
    repository_root = Path(repository_root).resolve()
    if destination == repository_root or repository_root in destination.parents:
        raise CaptureError("private capture destination must be outside the repository")
    if destination.exists():
        raise CaptureError("private capture destination already exists")
    destination.mkdir(parents=True, mode=0o700, exist_ok=False)
    os.chmod(destination, 0o700)
    event_path = destination / "playport-events.jsonl"
    manifest_path = destination / "capture-manifest.json"
    manifest = dict(artifact.manifest)
    manifest["event_file"] = event_path.name
    manifest["event_file_sha256"] = hashlib.sha256(artifact.event_bytes).hexdigest()
    _write_private(event_path, artifact.event_bytes)
    manifest_path_bytes = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    _write_private(manifest_path, manifest_path_bytes)
    return event_path, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="-", help="PlayPort log or OracleDiagnostics JSONL; '-' reads stdin")
    parser.add_argument("--output", required=True, type=Path, help="new private output directory outside this checkout")
    parser.add_argument("--receiver-commit", required=True, help="full PlayPort Git SHA reported for the receiver build")
    parser.add_argument("--phase", required=True, dest="phase_label", help="short non-identifying capture phase label")
    args = parser.parse_args()
    source = sys.stdin.buffer if args.input == "-" else open(args.input, "rb")
    try:
        artifact = ingest_lines(_bounded_lines(source), receiver_commit=args.receiver_commit,
                                phase_label=args.phase_label)
    finally:
        if source is not sys.stdin.buffer:
            source.close()
    event_path, manifest_path = write_private_capture(
        artifact, args.output, repository_root=Path(__file__).resolve().parents[2])
    print(f"capture_events={artifact.manifest['validated_event_count']}")
    print(f"source_stream_complete={artifact.manifest['source_stream_complete']}")
    print(f"protocol_observation_window_complete={artifact.manifest['coverage']['protocol_observation_window_complete']}")
    print(f"event_sha256={hashlib.sha256(artifact.event_bytes).hexdigest()}")
    print(f"private_event_file={event_path}")
    print(f"private_manifest={manifest_path}")
    return 0 if artifact.manifest["source_stream_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
