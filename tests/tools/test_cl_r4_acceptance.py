from tools.run_cl_r4_acceptance import scenario_receipt


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
