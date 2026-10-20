from tools.run_cl_r4_acceptance import CASES, scenario_receipt
from pathlib import Path


def test_scenario_receipt_captures_revision_process_injection_lifecycle_and_cleanup():
    receipt = scenario_receipt(
        """API17_EMULATOR_PROCESS pid=400 launcher_pid=399 serial=emulator-5580 process_identity=verified
CL_R4B_QUEUE_SATURATED_PARENT_TEARDOWN_REQUESTED owner_pid=501 producer_pid=502
IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true active_pfd_transfers=0 retained_frame_bytes=0
""",
        ["IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true"],
        "abc123", "source-fingerprint", "apk-hash", "evidence-hash",
    )
    assert receipt["source_revision"] == {
        "git_head": "abc123", "fingerprint_sha256": "source-fingerprint"}
    assert receipt["actual_api17_execution"] == "EXECUTED"
    assert receipt["process_ids"] == {
        "pid": [400], "launcher_pid": [399], "owner_pid": [501], "producer_pid": [502]}
    assert len(receipt["failure_injection"]) == 1
    assert len(receipt["observed_lifecycle"]) == 1
    assert receipt["acceptance_assertions"] == {
        "IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true": True}
    assert len(receipt["resource_cleanup"]) == 1
    assert receipt["evidence_sha256"] == "evidence-hash"


def test_scenario_receipt_never_calls_missing_api17_execution_a_pass():
    receipt = scenario_receipt("emulator boot timeout", ["FAULT_PASS"], "abc", "src", "apk", "ev")
    assert receipt["actual_api17_execution"] == "NOT_EXECUTED"
    assert receipt["acceptance_assertions"] == {"FAULT_PASS": False}


def test_scenario_receipt_records_view_death_during_teardown_injection():
    receipt = scenario_receipt(
        """API17_EMULATOR_PROCESS pid=400 serial=emulator-5580 process_identity=verified
CL_R4B_VIEW_DEATH_DURING_TEARDOWN_BARRIER_HELD view_pid=501 session_id=77 active_pfd_transfers=1 parent_teardown_inflight=true
TYPE111_PARENT_TEARDOWN_RESOURCES session_id=77 remaining_streams=0 active_pfd_transfers=0 retained_frame_bytes=0
""",
        ["CL_R4B_VIEW_DEATH_DURING_TEARDOWN_BARRIER_HELD",
         "remaining_streams=0 active_pfd_transfers=0 retained_frame_bytes=0"],
        "abc123", "source-fingerprint", "apk-hash", "evidence-hash",
    )
    assert receipt["failure_injection"] == [
        "CL_R4B_VIEW_DEATH_DURING_TEARDOWN_BARRIER_HELD view_pid=501 session_id=77 active_pfd_transfers=1 parent_teardown_inflight=true"]
    assert "TYPE111_PARENT_TEARDOWN_RESOURCES" in receipt["resource_cleanup"][0]
    assert receipt["acceptance_assertions"]["remaining_streams=0 active_pfd_transfers=0 retained_frame_bytes=0"]


def test_priority_combination_receipts_include_process_and_cleanup_evidence():
    source = Path(__file__).parents[2] / "tools/run_cl_r4_acceptance.py"
    assert 'receipt = scenario_receipt(output, markers, head, source_hash' in source.read_text()
    assert '"evidence_log_sha256": mode_log_hash,\n                              **receipt' in source.read_text()


def test_producer_death_case_does_not_require_unrelated_preclaim_attack_receipt():
    markers = next(case[3] for case in CASES if case[0] == "CL-R4-01")
    assert "CL_R4_TYPE111_INFLIGHT_PRODUCER_DEATH_CLEANUP_PASS" in markers
    assert "CL_R4_TYPE111_PRODUCER_DEATH_RESTART_PASS" in markers
    assert "CL_R4B_SINK_ACTIVE_SESSION_PRECLAIM_ATTEMPT" not in markers
