from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import plistlib
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/honda-readonly-preflight"))
import type111_boundary_source as source
import type111_observation_events as parser
import type111_playport_source as playport_source

FIXTURE = Path(__file__).parent / "fixtures/type111-events/accepted.jsonl"
PLAYPORT_43P = ROOT / "research/lab/captures/43p/oracle-events.redacted.jsonl"
PLAYPORT_43P_SHA256 = "d57d08e17354d868a08712595d1a05526497534243930a492aa36131c7ab9913"


def body(value):
    return base64.b64encode(plistlib.dumps(value, fmt=plistlib.FMT_BINARY)).decode("ascii")


def record(boundary, second, **values):
    return {
        "schema": "claritylink-receiver-boundary-v1",
        "session_id": "synthetic-session",
        "phase": "navigation-selected",
        "timestamp": f"2026-01-01T12:00:{second:02d}Z",
        "boundary": boundary,
        **values,
    }


def trace(records, method="synthetic-boundary-export"):
    raw = "\n".join(json.dumps(row, sort_keys=True) for row in records).encode() + b"\n"
    return source.parse_boundary_jsonl(raw, method=method), raw


def accepted_records():
    return [
        record("info_response", 0, request_id="info-1", complete=True, http_status=200,
               body_base64=body({"displays": [{"features": 1, "uuid": "main"}]})),
        record("setup_request", 1, request_id="setup-1", complete=True,
               body_base64=body({"streams": [{"type": 110}, {"type": 111, "custom": "kept"}]})),
        record("setup_response", 2, request_id="setup-1", complete=True, http_status=200,
               body_base64=body({"streams": [{"type": 110}, {"type": 111, "dataPort": 6000}]})),
        record("stream_created", 3, request_id="setup-1", stream_id="s111-a", stream_type=111),
        record("media_observation", 4, stream_id="s111-a", stream_type=111, available=False, complete=True),
        record("session_closed", 5, reason="normal-close"),
    ]


def test_boundary_source_decodes_and_preserves_raw_plist_fields_and_hash():
    parsed, raw = trace(accepted_records())
    assert parsed.artifact_sha256 == hashlib.sha256(raw).hexdigest()
    assert parsed.source_records[1][0] > parsed.source_records[0][0]
    request = parsed.events[1]
    assert request["data"]["payload"]["streams"][1] == {"custom": "kept", "type": 111}
    assert base64.b64decode(request["data"]["body_base64"]) == plistlib.dumps(
        {"streams": [{"type": 110}, {"type": 111, "custom": "kept"}]}, fmt=plistlib.FMT_BINARY
    )
    with pytest.raises(parser.EventError, match="SHA-256 mismatch"):
        source.parse_boundary_jsonl(raw, expected_sha256="0" * 64)


def test_correlated_type111_lifecycle_and_type110_coexistence():
    parsed, _ = trace(accepted_records())
    assert parser.classify(parsed) == [
        "info_display_descriptors:1", "type111_requested", "type111_accepted",
        "type110_setup_observed", "type111_stream_created", "stream_created_media_unavailable",
        "session_teardown_observed",
    ]


def test_committed_synthetic_boundary_fixture_replays_offline():
    parsed = source.parse_boundary_jsonl(FIXTURE.read_bytes())
    assert parser.classify(parsed) == [
        "info_display_descriptors:1", "type111_requested", "type111_accepted",
        "type110_setup_observed", "type111_stream_created", "stream_created_media_unavailable",
        "session_teardown_observed",
    ]


def test_generic_http_error_is_not_misreported_as_type111_rejection():
    matching, _ = trace([
        record("setup_request", 0, request_id="r", complete=True,
               body_base64=body({"streams": [{"type": 111}]})),
        record("setup_response", 1, request_id="r", complete=True, http_status=422,
               body_base64=body({"error": "unsupported"})),
    ])
    assert parser.classify(matching) == ["type111_requested", "type111_setup_error_response_observed"]
    orphan, _ = trace([
        record("setup_response", 0, request_id="unmatched", complete=True, http_status=500,
               body_base64=body({"error": "failure"})),
    ])
    assert parser.classify(orphan) == ["insufficient_observation"]


def test_requested_type111_without_response_is_not_called_rejected():
    parsed, _ = trace([
        record("setup_request", 0, request_id="r", complete=True,
               body_base64=body({"streams": [{"type": 111}]})),
    ])
    assert parser.classify(parsed) == ["type111_requested", "type111_request_without_complete_response"]


def test_stream_media_must_match_the_accepted_stream_identity():
    rows = accepted_records()[:-2] + [
        record("stream_created", 3, request_id="setup-1", stream_id="type111-stream", stream_type=111),
        record("media_observation", 4, stream_id="different-stream", stream_type=111, available=False, complete=True),
    ]
    parsed, _ = trace(rows)
    assert parser.classify(parsed) == [
        "info_display_descriptors:1", "type111_requested", "type111_accepted", "type110_setup_observed",
        "type111_stream_created",
    ]


def test_cross_phase_joins_are_rejected():
    rows = accepted_records()
    rows[2]["phase"] = "navigation-deselected"
    parsed, _ = trace(rows)
    with pytest.raises(parser.EventError, match="one phase"):
        parser.classify(parsed)


def test_negative_request_claim_needs_complete_same_phase_window():
    parsed, _ = trace([
        record("info_response", 0, request_id="i", complete=True, http_status=200, body_base64=body({"displays": []})),
        record("window_closed", 1, setup_observation_complete=True),
    ])
    assert parser.classify(parsed) == [
        "info_display_descriptors:0", "complete_info_and_setup_window_without_type111_request",
    ]
    incomplete, _ = trace([
        record("info_response", 0, request_id="i", complete=True, http_status=200, body_base64=body({"displays": []})),
        record("setup_request", 1, request_id="s", complete=False, body_base64=body({"streams": []})),
        record("window_closed", 2, setup_observation_complete=True),
    ])
    assert parser.classify(incomplete) == ["info_display_descriptors:0"]


def test_malformed_stream_or_display_arrays_never_look_empty():
    malformed_request, _ = trace([
        record("info_response", 0, request_id="i", complete=True, http_status=200,
               body_base64=body({"displays": []})),
        record("setup_request", 1, request_id="s", complete=True,
               body_base64=body({"streams": [{"type": True}]})),
        record("window_closed", 2, setup_observation_complete=True),
    ])
    assert parser.classify(malformed_request) == [
        "info_display_descriptors:0", "setup_request_descriptor_inconclusive",
    ]
    missing_displays, _ = trace([
        record("info_response", 0, request_id="i", complete=True, http_status=200,
               body_base64=body({"other": "field"})),
    ])
    assert parser.classify(missing_displays) == ["info_display_inventory_inconclusive"]
    malformed_displays, _ = trace([
        record("info_response", 0, request_id="i", complete=True, http_status=200,
               body_base64=body({"displays": ["not-a-descriptor"]})),
    ])
    assert parser.classify(malformed_displays) == ["info_display_inventory_inconclusive"]


def test_accepted_response_requires_matching_type111_request_and_descriptor():
    no_request, _ = trace([
        record("setup_response", 0, request_id="r", complete=True, http_status=200,
               body_base64=body({"streams": [{"type": 111}]})),
    ])
    assert parser.classify(no_request) == ["insufficient_observation"]
    no_descriptor, _ = trace([
        record("setup_request", 0, request_id="r", complete=True,
               body_base64=body({"streams": [{"type": 111}]})),
        record("setup_response", 1, request_id="r", complete=True, http_status=200,
               body_base64=body({"streams": [{"type": 110}]})),
    ])
    assert parser.classify(no_descriptor) == ["type111_requested", "type111_response_semantics_inconclusive"]


def test_event_classifier_requires_trace_with_computed_provenance():
    parsed, raw = trace(accepted_records())
    assert parsed.artifact_sha256 == hashlib.sha256(raw).hexdigest()
    with pytest.raises(parser.EventError, match="parsed, hashed"):
        parser.classify(list(parsed.events))


def test_classifier_rederives_events_from_hashed_source_bytes():
    parsed, raw = trace(accepted_records())
    expected = parser.classify(parsed)
    parsed.events[1]["correlation"]["request_id"] = "forged"
    assert parser.classify(parsed) == expected
    forged_cache = parser.Trace(parsed.artifact_sha256, parsed.method, tuple(), tuple(), raw, "boundary")
    assert parser.classify(forged_cache) == expected


def test_malformed_or_non_plist_boundary_payload_is_rejected():
    malformed = [record("setup_request", 0, request_id="r", complete=True, body_base64="eA==")]
    raw = (json.dumps(malformed[0]) + "\n").encode()
    with pytest.raises(parser.EventError, match="invalid encoded plist"):
        source.parse_boundary_jsonl(raw)


def test_published_json_schema_tracks_runtime_event_and_correlation_shapes():
    schema = json.loads((ROOT / "docs/diagnostics/type111-observation-events.schema.json").read_text())
    by_event = {
        item["properties"]["event"]["const"]: item["properties"]["data"]["required"]
        for item in schema["oneOf"]
    }
    assert set(by_event) == parser.EVENTS
    assert by_event["info_response"] == ["complete", "http_status", "body_base64", "payload"]
    correlation = {
        item["if"]["properties"]["event"]["const"]: item["then"]["properties"]["correlation"]["required"]
        for item in schema["allOf"]
    }
    assert correlation == {
        "info_response": ["request_id"], "setup_request": ["request_id"],
        "setup_response": ["request_id"], "stream_created": ["request_id", "stream_id"],
        "stream_closed": ["request_id", "stream_id"], "media_observation": ["stream_id"],
    }


def test_verified_playport_43p_source_replays_through_type111_parser():
    raw = PLAYPORT_43P.read_bytes()
    parsed = playport_source.parse_playport_jsonl(raw, expected_sha256=PLAYPORT_43P_SHA256)
    assert parsed.source_format == "playport-oracle"
    assert parsed.artifact_sha256 == PLAYPORT_43P_SHA256
    assert len(parsed.events) == 945
    assert len(parsed.source_records) == len(parsed.events)
    assert parser.classify(parsed) == [
        "playport_info_display_descriptors:2",
        "playport_info_display_type_observed:110",
        "playport_info_display_type_observed:111",
        "playport_alt_screen_urls_key_observed",
        "playport_alt_screen_urls_value_empty",
        "playport_receiver_setup_listener_ready:110",
        "playport_receiver_setup_listener_ready:111",
        "playport_stream_socket_connected:110",
        "playport_video_config_received:110",
        "playport_first_frame_received:110",
        "playport_stream_socket_connected:111",
        "playport_video_config_received:111",
        "playport_first_frame_received:111",
        "playport_type110_and_type111_media_observed",
        "playport_type110_and_type111_teardown_observed",
    ]


def test_playport_source_rejects_digest_drift_and_unreviewed_metadata():
    raw = PLAYPORT_43P.read_bytes()
    with pytest.raises(parser.EventError, match="SHA-256 mismatch"):
        playport_source.parse_playport_jsonl(raw, expected_sha256="0" * 64)
    row = json.loads(raw.splitlines()[0])
    row["metadata"]["raw_uuid"] = "must-not-enter"
    unsafe = (json.dumps(row) + "\n").encode()
    with pytest.raises(parser.EventError, match="metadata.*allowlist"):
        playport_source.parse_playport_jsonl(unsafe)


def test_playport_source_refuses_unredacted_url_metadata():
    row = {"monotonicTimeNs": 1, "phase": "INFO_RESPONSE", "streamType": None,
           "event": "advertised", "metadata": {"alt_screen_urls": "maps:/sensitive"}}
    with pytest.raises(parser.EventError, match="URL metadata must remain redacted"):
        playport_source.parse_playport_jsonl((json.dumps(row) + "\n").encode())


def test_playport_classifier_does_not_infer_missing_type111_events():
    rows = [json.loads(line) for line in PLAYPORT_43P.read_text().splitlines()]
    reduced = [row for row in rows if not (
        row["phase"] == "VIDEO_FRAME" and row["event"] == "first_frame"
        and row["streamType"] == 111)]
    raw = b"".join((json.dumps(row, separators=(",", ":")) + "\n").encode()
                   for row in reduced)
    outcomes = parser.classify(playport_source.parse_playport_jsonl(raw))
    assert "playport_first_frame_received:111" not in outcomes
    assert "playport_type110_and_type111_media_observed" not in outcomes
    assert "playport_receiver_setup_listener_ready:111" in outcomes
    assert "playport_type110_and_type111_teardown_observed" in outcomes


def test_playport_source_rejects_duplicate_keys_that_hide_sensitive_values():
    row = ('{"monotonicTimeNs":1,"phase":"INFO_RESPONSE","streamType":null,'
           '"event":"advertised","metadata":{"url":"maps:/private","url":""}}\n')
    with pytest.raises(parser.EventError, match="duplicate JSON object key: url"):
        playport_source.parse_playport_jsonl(row.encode())


def test_playport_source_rejects_duplicate_event_rows_and_preserves_logger_order():
    raw = PLAYPORT_43P.read_bytes()
    first, second = raw.splitlines(keepends=True)[:2]
    with pytest.raises(parser.EventError, match="duplicate PlayPort event"):
        playport_source.parse_playport_jsonl(first + first)
    rows = [json.loads(first), json.loads(second)]
    rows[0]["monotonicTimeNs"], rows[1]["monotonicTimeNs"] = 2, 1
    reordered_times = b"".join((json.dumps(row) + "\n").encode() for row in rows)
    parsed = playport_source.parse_playport_jsonl(reordered_times)
    assert [row["monotonicTimeNs"] for row in parsed.events] == [2, 1]


def test_playport_classifier_refuses_to_join_events_across_session_markers():
    rows = [json.loads(line) for line in PLAYPORT_43P.read_text().splitlines()]
    marker = next(row for row in rows if row["phase"] == "SESSION_SETUP")
    second = dict(marker, monotonicTimeNs=marker["monotonicTimeNs"] + 1)
    raw = b"".join((json.dumps(row, separators=(",", ":")) + "\n").encode()
                   for row in rows + [second])
    parsed = playport_source.parse_playport_jsonl(raw)
    assert parser.classify(parsed) == ["playport_session_scope_ambiguous"]
