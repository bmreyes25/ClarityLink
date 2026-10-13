"""Fail-closed historic chronology tests; fixture timestamps are synthetic."""
import copy
import datetime as dt

import pytest

from tools import r7e7i_historical_chronology as c


@pytest.fixture
def input_data():
    run = {"databaseId": c.RUN_ID, "headSha": c.RUN_HEAD, "event": "pull_request",
           "url": c.RUN_URL, "createdAt": "2026-10-12T02:36:36Z"}
    commit = {"sha": c.RUN_HEAD, "review_path": c.REVIEW_PATH,
              "review_text": "collector-failure-20261012T021444Z-b64f.json\nTEST_A_PROCESS_STATE_UNCERTAIN"}
    history = {"decision": "TEST_A_PROCESS_STATE_UNCERTAIN", "diagnostic_started": True,
               "finished_utc": "2026-10-12T02:14:44.929697+00:00"}
    return run, commit, history


def test_exact_report_and_run_yield_conditional_only(input_data):
    run, commit, history = input_data
    result = c.analyze(run, commit, history, c.HISTORICAL_SHA256)
    assert result["decision"] == "HISTORICAL_UPPER_BOUND_CONDITIONAL"
    assert result["source_clock_accuracy_bound_seconds"] is None
    assert result["numeric_historical_upper_bound_utc"] is None


@pytest.mark.parametrize("change", ["run_id", "head", "event", "url", "report", "history_hash", "decision", "start", "creation"])
def test_unmatched_or_invalid_evidence_never_proves_upper_bound(input_data, change):
    run, commit, history = input_data
    run, commit, history = copy.deepcopy(run), copy.deepcopy(commit), copy.deepcopy(history)
    digest = c.HISTORICAL_SHA256
    if change == "run_id": run["databaseId"] = 1
    elif change == "head": run["headSha"] = "0" * 40
    elif change == "event": run["event"] = "push"
    elif change == "url": run["url"] = "https://example.invalid/"
    elif change == "report": commit["review_text"] = "unrelated"
    elif change == "history_hash": digest = "0" * 64
    elif change == "decision": history["decision"] = "PASS"
    elif change == "start": history["finished_utc"] = "bad"
    elif change == "creation": run["createdAt"] = "2026-10-12T02:00:00Z"
    result = c.analyze(run, commit, history, digest)
    assert result["decision"] == "HISTORICAL_UPPER_BOUND_NOT_PROVEN"
    assert result["numeric_historical_upper_bound_utc"] is None
