import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/honda-readonly-preflight"))
import type111_playport_capture as capture_module

SOURCE = ROOT / "research/lab/captures/43p/oracle-events.redacted.jsonl"
SOURCE_SHA256 = "d57d08e17354d868a08712595d1a05526497534243930a492aa36131c7ab9913"
PLAYPORT_COMMIT = "f2679a26a593f544ba7822dfbac870544b4af92a"


def capture(lines, *, interrupted=False):
    return capture_module.ingest_lines(
        lines, receiver_commit=PLAYPORT_COMMIT, phase_label="43p-canonical",
        interrupted=interrupted,
    )


def test_actual_playport_trace_capture_preserves_source_and_marks_unobserved_boundaries():
    raw = SOURCE.read_bytes()
    artifact = capture(raw.splitlines(keepends=True))
    manifest = artifact.manifest
    assert hashlib.sha256(artifact.event_bytes).hexdigest() == SOURCE_SHA256
    assert manifest["validated_event_count"] == 945
    assert manifest["event_times_monotonic_in_log_order"] is False
    assert manifest["source_stream_complete"] is True
    assert manifest["coverage"]["info_request_observed"] is True
    assert manifest["coverage"]["info_response_observed"] is True
    assert manifest["coverage"]["display_types_observed"] == [110, 111]
    assert manifest["coverage"]["setup_listener_types_observed"] == [110, 111]
    assert manifest["coverage"]["first_frame_types_observed"] == [110, 111]
    assert manifest["coverage"]["stream_teardown_types_observed"] == [110, 111]
    assert manifest["coverage"]["rtsp_response_status_observed"] is False
    assert manifest["coverage"]["parent_session_termination_observed"] is False
    assert manifest["coverage"]["protocol_observation_window_complete"] is False
    assert manifest["raw_non_oracle_log_lines_retained"] is False


def test_capture_extracts_only_named_receiver_events_and_accepts_simplelogger_format():
    first, second = SOURCE.read_bytes().splitlines(keepends=True)[:2]
    lines = [b"INFO unrelated - private_marker=must-not-persist\n",
             b"[test] INFO type111-oracle - " + first.rstrip(b"\r\n") + b"\n",
             second]
    artifact = capture(lines)
    assert artifact.manifest["validated_event_count"] == 2
    assert b"must-not-persist" not in artifact.event_bytes
    assert b"unrelated" not in artifact.event_bytes
    assert b"type111-oracle - " not in artifact.event_bytes


def test_missing_stream_events_do_not_become_negative_protocol_evidence():
    rows = [json.loads(line) for line in SOURCE.read_text().splitlines()]
    lines = [(json.dumps(row, separators=(",", ":")) + "\n").encode()
             for row in rows if not (
                 row["phase"] == "VIDEO_FRAME" and row["event"] == "first_frame"
                 and row["streamType"] == 111)]
    artifact = capture(lines)
    assert artifact.manifest["coverage"]["first_frame_types_observed"] == [110]
    assert artifact.manifest["coverage"]["protocol_observation_window_complete"] is False
    assert "playport_type110_and_type111_media_observed" not in artifact.manifest["findings"]


def test_interrupted_source_is_retained_as_incomplete():
    lines = SOURCE.read_bytes().splitlines(keepends=True)[:4]
    artifact = capture(lines, interrupted=True)
    assert artifact.manifest["validated_event_count"] == 4
    assert artifact.manifest["source_stream_complete"] is False
    assert artifact.manifest["observer_interrupted"] is True


def test_duplicate_event_stops_capture_and_keeps_only_unique_prefix():
    first = SOURCE.read_bytes().splitlines(keepends=True)[0]
    artifact = capture([first, first])
    assert artifact.manifest["capture_failure"] == "duplicate_event"
    assert artifact.manifest["validated_event_count"] == 1
    assert artifact.manifest["source_stream_complete"] is False
    assert artifact.event_bytes == first


def test_oversized_log_line_is_bounded_before_allocation_and_marks_failure():
    stream = BytesIO(b"x" * (10 * 1024 * 1024))
    artifact = capture_module.ingest_lines(
        capture_module._bounded_lines(stream), receiver_commit=PLAYPORT_COMMIT,
        phase_label="43p-canonical")
    assert artifact.manifest["capture_failure"] == "log_line_limit"
    assert artifact.manifest["input_log_bytes_seen"] == capture_module.MAX_LOG_LINE_BYTES + 1
    assert artifact.event_bytes == b""


def test_parse_failure_discards_unsafe_line_and_private_value():
    first = SOURCE.read_bytes().splitlines(keepends=True)[0]
    bad = (b'{"monotonicTimeNs":2,"phase":"INFO_RESPONSE","streamType":null,'
           b'"event":"advertised","metadata":{"raw_token":"never-store-this"}}\n')
    artifact = capture([first, bad])
    assert artifact.manifest["capture_failure"] == "invalid_or_unreviewed_event"
    assert artifact.manifest["source_stream_complete"] is False
    assert b"never-store-this" not in artifact.event_bytes
    assert b"raw_token" not in json.dumps(artifact.manifest).encode()


def test_private_writer_uses_owner_only_files_and_refuses_overwrite_or_repo_path(tmp_path):
    artifact = capture(SOURCE.read_bytes().splitlines(keepends=True))
    private_dir = tmp_path / "private-capture"
    event_path, manifest_path = capture_module.write_private_capture(
        artifact, private_dir, repository_root=ROOT)
    assert private_dir.stat().st_mode & 0o777 == 0o700
    assert event_path.stat().st_mode & 0o777 == 0o600
    assert manifest_path.stat().st_mode & 0o777 == 0o600
    manifest = json.loads(manifest_path.read_text())
    assert manifest["event_file_sha256"] == SOURCE_SHA256
    assert event_path.read_bytes() == SOURCE.read_bytes()
    with pytest.raises(capture_module.CaptureError, match="already exists"):
        capture_module.write_private_capture(artifact, private_dir, repository_root=ROOT)
    with pytest.raises(capture_module.CaptureError, match="outside the repository"):
        capture_module.write_private_capture(artifact, ROOT / "should-never-exist",
                                             repository_root=ROOT)
