from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/honda-readonly-preflight"))
import type111_observation_events as parser

FIXTURES = Path(__file__).parent / "fixtures/type111-events"


def event(kind, data, second=0):
    return {
        "schema": "claritylink-type111-observation-v1",
        "session_id": "synthetic",
        "phase": "synthetic-phase",
        "timestamp": f"2026-01-01T12:00:{second:02d}Z",
        "source": {
            "method": "synthetic",
            "artifact_sha256": "a" * 64,
            "record_id": f"r{second}",
        },
        "event": kind,
        "data": data,
    }


def test_synthetic_accepted_stream_without_media_and_teardown():
    events = parser.parse_jsonl((FIXTURES / "accepted.jsonl").read_text())
    result = parser.classify(events)
    assert result == [
        "type111_requested", "type111_accepted", "type111_stream_created",
        "stream_created_media_unavailable", "session_teardown_observed",
    ]


def test_no_advertisement_is_supported_by_complete_decoded_info_only():
    assert parser.classify([event("info_response", {
        "complete": True, "secondary_advertised": False,
    })]) == ["no_secondary_capability_advertised"]
    assert parser.classify([event("info_response", {
        "complete": False, "secondary_advertised": False,
    })]) == ["insufficient_observation"]


def test_no_request_requires_complete_setup_window():
    base = event("info_response", {"complete": True, "secondary_advertised": True})
    assert parser.classify([base]) == ["insufficient_observation"]
    closed = event("window_closed", {"setup_observation_complete": True}, 1)
    assert parser.classify([base, closed]) == ["advertised_but_no_type111_request"]


def test_rejected_setup_is_separate_from_accepted_and_stream_created():
    events = [
        event("setup_request", {"complete": True, "stream_types": [110, 111]}, 0),
        event("setup_response", {"complete": True, "stream_type": 111, "result": "rejected"}, 1),
    ]
    assert parser.classify(events) == ["type111_requested", "type111_rejected"]


def test_decoded_response_proves_acceptance_even_if_request_record_is_missing():
    response = event("setup_response", {
        "complete": True, "stream_type": 111, "result": "accepted",
    })
    assert parser.classify([response]) == ["type111_accepted"]


def test_stream_teardown_is_distinct_from_parent_session_teardown():
    closed = event("stream_closed", {"stream_type": 111, "stream_id": "synthetic"})
    assert parser.classify([closed]) == ["type111_stream_teardown_observed"]


def test_incomplete_setup_request_prevents_negative_request_claim():
    info = event("info_response", {"complete": True, "secondary_advertised": True})
    request = event("setup_request", {"complete": False, "stream_types": [110]}, 1)
    window = event("window_closed", {"setup_observation_complete": True}, 2)
    assert parser.classify([info, request, window]) == ["insufficient_observation"]


@pytest.mark.parametrize("change", [
    {"timestamp": "yesterday"},
    {"source": {"method": "synthetic", "artifact_sha256": "bad", "record_id": "x"}},
    {"data": {"complete": True}},
])
def test_invalid_event_fields_fail_closed(change):
    item = event("info_response", {"complete": True, "secondary_advertised": True})
    item.update(change)
    with pytest.raises(parser.EventError):
        parser.validate_event(item)


def test_jsonl_rejects_mixed_sessions_and_out_of_order_events():
    first = event("session_closed", {"reason": "synthetic"}, 1)
    second = event("session_closed", {"reason": "synthetic"}, 0)
    with pytest.raises(parser.EventError, match="ordered"):
        parser.parse_jsonl("\n".join(map(json.dumps, [first, second])))
    second["session_id"] = "other"
    with pytest.raises(parser.EventError, match="one session"):
        parser.parse_jsonl("\n".join(map(json.dumps, [first, second])))


def test_source_artifact_hash_is_verified():
    payload = b"synthetic decoded evidence"
    digest = hashlib.sha256(payload).hexdigest()
    parser.verify_artifact(payload, digest)
    with pytest.raises(parser.EventError, match="mismatch"):
        parser.verify_artifact(payload, "0" * 64)
