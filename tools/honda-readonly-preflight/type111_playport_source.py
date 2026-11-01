"""Parse the preserved allowlist-only PlayPort 43P lab event source.

This adapter is specific to the checked-in external iPhone/PlayPort trace. It
preserves original JSONL bytes and offsets and emits PlayPort-scoped findings;
it never treats those findings as Honda receiver behavior.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from type111_observation_events import EventError, Trace, verify_artifact

PAIRS = {
    ("SESSION_SETUP", "features_negotiated"),
    ("INFO_REQUEST", "received"), ("INFO_RESPONSE", "advertised"),
    ("INFO_RESPONSE", "display"), ("STREAM_SETUP", "requested"),
    ("STREAM_SETUP", "listener_ready"), ("STREAM_ACTIVE", "active"),
    ("STREAM_ACTIVE", "socket_open"), ("VIDEO_CONFIG", "received"),
    ("VIDEO_FRAME", "protection_classified"), ("VIDEO_FRAME", "first_frame"),
    ("VIDEO_FRAME", "stream_summary"), ("CONTROL", "suggestUI"),
    ("TEARDOWN", "stopped"),
}
METADATA_KEYS = {
    "active", "alt_screen_urls", "bitrate_estimate", "command", "config_size",
    "data_port", "display_count", "display_uuid_present", "enabled_features",
    "features", "fps", "fps_estimate", "frame_size", "framing",
    "height_physical", "height_pixels", "initial_url", "initial_view_area_present",
    "key_names", "listener_state", "relative_ms", "request_keys", "requested_features",
    "requested_keys", "response_keys", "returned_type", "security_mode", "source_version",
    "stream_connection_id_distinct", "stream_connection_id_present", "stream_count",
    "target_uuid_present", "url", "view_areas_present", "width_physical", "width_pixels",
    "keyframe",
}
NUMERIC_KEYS = {
    "bitrate_estimate", "config_size", "data_port", "display_count", "features", "fps",
    "fps_estimate", "frame_size", "height_physical", "height_pixels", "relative_ms",
    "returned_type", "stream_count", "width_physical", "width_pixels",
}
BOOLEAN_KEYS = {
    "active", "display_uuid_present", "initial_view_area_present", "keyframe",
    "stream_connection_id_distinct", "stream_connection_id_present", "target_uuid_present",
    "view_areas_present",
}
LIST_KEYS = {"enabled_features", "key_names", "request_keys", "requested_features",
             "requested_keys", "response_keys"}
MAX_EVENTS = 2_000
_TOKEN_LIST = re.compile(r"^[A-Za-z0-9_.-]+(?:,[A-Za-z0-9_.-]+)*$")
_DECIMAL = re.compile(r"^[0-9]{1,20}$")


def _validate_metadata(metadata: Any, line_no: int) -> None:
    if not isinstance(metadata, dict) or set(metadata) - METADATA_KEYS:
        raise EventError(f"line {line_no}: metadata is outside the reviewed allowlist")
    for key, value in metadata.items():
        if not isinstance(value, str) or len(value) > 4096:
            raise EventError(f"line {line_no}: metadata value is not a bounded string")
        if key in NUMERIC_KEYS and not _DECIMAL.fullmatch(value):
            raise EventError(f"line {line_no}: {key} is not a bounded decimal value")
        if key == "data_port" and not 1 <= int(value) <= 65535:
            raise EventError(f"line {line_no}: data_port is outside the TCP port range")
        if key in BOOLEAN_KEYS and value not in {"true", "false"}:
            raise EventError(f"line {line_no}: {key} is not an allowlisted boolean string")
        if key in LIST_KEYS and not _TOKEN_LIST.fullmatch(value):
            raise EventError(f"line {line_no}: {key} is not an allowlisted token list")
        if key in {"url", "alt_screen_urls"} and value != "":
            raise EventError(f"line {line_no}: URL metadata must remain redacted")
        if key == "initial_url" and value not in {"", "maps:/car/instrumentcluster/map"}:
            raise EventError(f"line {line_no}: initial URL is not the reviewed lab value")
        if key == "command" and value != "suggestUI":
            raise EventError(f"line {line_no}: control name is not allowlisted")
        if key == "framing" and value not in {
                "screen-header-128/video-config", "screen-header-128/video-frame"}:
            raise EventError(f"line {line_no}: framing label is not allowlisted")
        if key == "security_mode" and value != "MODERN_CHACHA_SCREEN":
            raise EventError(f"line {line_no}: parser label is not allowlisted")
        if key == "listener_state" and value not in {"UNKNOWN", "connected"}:
            raise EventError(f"line {line_no}: listener state is not allowlisted")
        if key == "source_version" and value != "366.0":
            raise EventError(f"line {line_no}: PlayPort source version is unexpected")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys so hidden raw values cannot evade redaction."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EventError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def parse_playport_jsonl(raw: bytes, *, method: str = "playport-43p-redacted-lab",
                         expected_sha256: str | None = None) -> Trace:
    if not isinstance(raw, bytes):
        raise EventError("PlayPort source must be bytes")
    if not isinstance(method, str) or not method or len(method) > 120:
        raise EventError("method must be a nonempty bounded source description")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EventError("PlayPort source must be UTF-8 JSONL") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None:
        verify_artifact(raw, expected_sha256)
    events: list[dict[str, Any]] = []
    pointers: list[tuple[int, int]] = []
    seen: set[bytes] = set()
    offset = 0
    for line_no, line in enumerate(text.splitlines(keepends=True), 1):
        encoded = line.encode("utf-8")
        if not line.strip():
            offset += len(encoded)
            continue
        try:
            event = json.loads(line, object_pairs_hook=_unique_object)
        except json.JSONDecodeError as exc:
            raise EventError(f"line {line_no}: invalid JSON") from exc
        except EventError as exc:
            raise EventError(f"line {line_no}: {exc}") from exc
        except (ValueError, RecursionError) as exc:
            raise EventError(f"line {line_no}: invalid JSON value") from exc
        if (not isinstance(event, dict)
                or set(event) != {"monotonicTimeNs", "phase", "streamType", "event", "metadata"}
                or not isinstance(event.get("phase"), str) or not isinstance(event.get("event"), str)
                or (event.get("phase"), event.get("event")) not in PAIRS
                or isinstance(event.get("monotonicTimeNs"), bool)
                or not isinstance(event.get("monotonicTimeNs"), int)
                or not 0 <= event["monotonicTimeNs"] <= (1 << 63) - 1
                or (event.get("streamType") is not None and type(event.get("streamType")) is not int)
                or event.get("streamType") not in {None, 110, 111}):
            raise EventError(f"line {line_no}: malformed or unsupported PlayPort event")
        _validate_metadata(event["metadata"], line_no)
        encoded_event = json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if encoded_event in seen:
            raise EventError(f"line {line_no}: duplicate PlayPort event")
        seen.add(encoded_event)
        events.append(event)
        pointers.append((offset, len(encoded.rstrip(b"\r\n"))))
        offset += len(encoded)
        if len(events) > MAX_EVENTS:
            raise EventError("PlayPort trace exceeds the 2000-event bound")
    if not events:
        raise EventError("PlayPort trace is empty")
    return Trace(digest, method, tuple(events), tuple(pointers), raw, "playport-oracle")


def classify_playport(trace: Trace) -> list[str]:
    events = trace.events
    session_markers = [e for e in events if e["phase"] == "SESSION_SETUP"
                       and e["event"] == "features_negotiated"]
    if len(session_markers) != 1:
        return ["playport_session_scope_ambiguous"]
    outcomes: list[str] = []
    advertised = [e for e in events if e["phase"] == "INFO_RESPONSE" and e["event"] == "advertised"]
    displays = [e for e in events if e["phase"] == "INFO_RESPONSE" and e["event"] == "display"]
    display_types = {e["streamType"] for e in displays}
    if advertised and advertised[-1]["metadata"].get("display_count") == str(len(displays)):
        outcomes.append(f"playport_info_display_descriptors:{len(displays)}")
    for stream_type in (110, 111):
        if stream_type in display_types:
            outcomes.append(f"playport_info_display_type_observed:{stream_type}")
    if any(e["phase"] == "INFO_REQUEST" and e["metadata"].get("key_names") == "altScreenURLs"
           for e in events):
        outcomes.append("playport_alt_screen_urls_key_observed")
    if any(e["phase"] == "INFO_RESPONSE" and e["event"] == "advertised"
           and e["metadata"].get("alt_screen_urls") == "" for e in events):
        outcomes.append("playport_alt_screen_urls_value_empty")

    listener_rows = [e for e in events if e["phase"] == "STREAM_SETUP" and e["event"] == "listener_ready"]
    for stream_type in (110, 111):
        if any(e["streamType"] == stream_type
               and e["metadata"].get("returned_type") == str(stream_type)
               and e["metadata"].get("requested_keys") == "latencyMs,streamConnectionID,type,uuid"
               and e["metadata"].get("response_keys") == "type,dataPort"
               and e["metadata"].get("data_port", "").isdecimal()
               for e in listener_rows):
            outcomes.append(f"playport_receiver_setup_listener_ready:{stream_type}")
    for stream_type in (110, 111):
        active = any(e["phase"] == "STREAM_ACTIVE" and e["event"] == "active"
                     and e["streamType"] == stream_type and e["metadata"].get("active") == "true"
                     for e in events)
        socket = any(e["phase"] == "STREAM_ACTIVE" and e["event"] == "socket_open"
                     and e["streamType"] == stream_type and e["metadata"].get("listener_state") == "connected"
                     for e in events)
        if active and socket:
            outcomes.append(f"playport_stream_socket_connected:{stream_type}")
        if any(e["phase"] == "VIDEO_CONFIG" and e["streamType"] == stream_type
               and e["event"] == "received" for e in events):
            outcomes.append(f"playport_video_config_received:{stream_type}")
        if any(e["phase"] == "VIDEO_FRAME" and e["streamType"] == stream_type
               and e["event"] == "first_frame" for e in events):
            outcomes.append(f"playport_first_frame_received:{stream_type}")
    if ("playport_first_frame_received:110" in outcomes
            and "playport_first_frame_received:111" in outcomes
            and any(e["phase"] == "VIDEO_FRAME" and e["event"] == "stream_summary"
                    and e["streamType"] == 110 for e in events)
            and any(e["phase"] == "VIDEO_FRAME" and e["event"] == "stream_summary"
                    and e["streamType"] == 111 for e in events)):
        outcomes.append("playport_type110_and_type111_media_observed")
    stopped = {e["streamType"] for e in events
               if e["phase"] == "TEARDOWN" and e["event"] == "stopped"
               and e["metadata"].get("active") == "false"}
    if {110, 111} <= stopped:
        outcomes.append("playport_type110_and_type111_teardown_observed")
    return outcomes or ["insufficient_playport_observation"]
