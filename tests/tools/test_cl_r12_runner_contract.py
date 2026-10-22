"""CL-HONDA-111-02: static contracts for the CL-R12 runner, workflow and gate.

These do not run an emulator. They keep three properties from regressing:
the lifecycle scenario and the performance gates stay separate verdicts, a
missing Activity teardown is judged only after a real grace period, and the
unchanged acceptance gate is not weakened.
"""
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNNER = (REPO / "tools/run_cl_r12_api17_ci.sh").read_text()
WORKFLOW = (REPO / ".github/workflows/cl-r12-api17-runtime-recovery.yml").read_text()
GATE = (REPO / "tools/check_cl_r12_perf_gate.py").read_text()


def test_runner_is_valid_bash():
    subprocess.run(["bash", "-n", str(REPO / "tools/run_cl_r12_api17_ci.sh")], check=True)
    subprocess.run(["bash", "-n", str(REPO / "tools/build_cl_r12_renderer_ab.sh")], check=True)


def test_runtime_pass_marker_is_not_unconditional():
    assert RUNNER.count("CL_R12_API17_RUNTIME_PASS'") == 1
    pass_at = RUNNER.index("echo 'CL_R12_API17_RUNTIME_PASS'")
    failure_exit = RUNNER.index("exit 11")
    assert failure_exit < pass_at, "gate failure must exit before the PASS marker"
    assert "CL_R12_API17_RUNTIME_SCENARIO=PASS" in RUNNER


def test_gate_verdicts_come_only_from_the_gate_script():
    assert re.search(r"check_cl_r12_perf_gate\.py", RUNNER)
    assert "gate_check " in RUNNER
    for verdict in ("baseline_gate", "candidate_gate", "soak_gate"):
        assert verdict in RUNNER
    assert "CL_R12_SOAK_SKIPPED" in RUNNER


def test_missing_teardown_evidence_is_not_declared_before_a_grace_period():
    assert "result_seen_at" in RUNNER and "destroy_grace" in RUNNER
    assert "SECONDS - deadline + timeout" not in RUNNER   # the old, immediate rule
    assert "|FD|" in RUNNER                               # FD detail lines are kept in receipts


def test_workflow_uses_the_renderer_isolating_pair_not_an_activity_swap():
    assert "build_cl_r12_renderer_ab.sh" in WORKFLOW
    assert "MessengerFramePerformanceActivity.baseline" not in WORKFLOW
    assert "baseline_source_sha" not in WORKFLOW


def test_acceptance_gate_thresholds_are_unchanged():
    expected = [
        '29 <= number("offered_fps") <= 31',
        'number("delivered_fps") >= 27',
        'number("latency_p95_ms") <= 50',
        'number("latency_p99_ms") <= 100',
        '<= 0.10',
        'number("source_fd_final") <= number("source_fd_base") + 2',
        'number("host_fd_final") <= number("host_fd_base") + 2',
        '8 * 1024 * 1024',
        'number("queue_high_water") <= 1',
    ]
    for fragment in expected:
        assert fragment in GATE, fragment


def test_runner_interleaves_repeated_pairs_and_reports_every_run():
    assert "CL_R12_AB_REPEATS" in RUNNER and "CL_R12_AB_REPEATS" in WORKFLOW
    assert "i % 2 == 1" in RUNNER                       # alternate A B / B A
    assert "summarize_cl_r12_ab.py" in RUNNER
    assert "CL_R12_GATE_CANDIDATE_RUN_" in RUNNER      # one unchanged-gate verdict per run
    # the candidate verdict can only worsen across runs
    assert 'candidate_gate=FAIL' in RUNNER and RUNNER.count('candidate_gate=PASS') == 1


def test_pane_lease_instrumentation_is_built_run_and_reported_separately():
    assert "build_cl_honda_111_pane_test_apk.sh" in WORKFLOW and "CL_PANE_LEASE_TEST_APK" in WORKFLOW
    assert "am instrument -w" in RUNNER and "Display1PaneLeaseLifecycleTest" in RUNNER
    assert "OK (7 tests)" in RUNNER and "SyntheticFrameFillTest" in RUNNER and "PaneLeaseFdLifecycleTest" in RUNNER and "Display1RendererViewportInPlaceTest" in RUNNER
    assert "CL_PANE_LEASE_INSTRUMENTATION=" in RUNNER
    assert RUNNER.index("exit 13") < RUNNER.index("echo 'CL_R12_API17_RUNTIME_PASS'")


def test_pane_test_apk_inputs_are_explicit_and_request_no_permission():
    script = (REPO / "tools/build_cl_honda_111_pane_test_apk.sh").read_text()
    manifest = (REPO / "android/cl-honda-111-pane-test/AndroidManifest.xml").read_text()
    assert "uses-permission" not in manifest and "<activity" not in manifest and "<service" not in manifest
    assert "PaneLeaseTest.java" in script and "Display1PaneLeaseLifecycleTest.java" in script
    assert "must request no permissions" in script


def test_workload_mode_changes_only_the_activity_and_is_recorded():
    script = (REPO / "tools/build_cl_r12_workload_ab.sh").read_text()
    assert "ab_mode=workload" in script and "renderer_tree_sha256_both" in script
    assert script.count('show "$baseline_sha:$activity"') == 1       # the only substituted file
    assert "build_cl_r12_workload_ab.sh" in WORKFLOW and "ab_mode" in WORKFLOW
    assert "workflow_dispatch" in WORKFLOW and "type: choice" in WORKFLOW


def test_renderer_mode_gives_the_baseline_the_candidates_workload_files():
    script = (REPO / "tools/build_cl_r12_renderer_ab.sh").read_text()
    assert "SyntheticFrameFill.java" in script and "workload_overlay_files" in script
    assert "ab_mode=renderer" in script
    # the activity and its helper are the only overlaid files; the renderer is never overlaid
    assert "src/claritylink-renderer" not in script.split("overlay=()")[1].split("done")[0]


def test_no_adb_call_can_block_the_runner_forever():
    assert "adbq()" in RUNNER and "timeout" in RUNNER
    # every adb invocation against the emulator goes through the bounded wrapper
    raw = [l for l in RUNNER.splitlines() if '"$adb" -s' in l and not l.lstrip().startswith("adbq()")]
    assert raw == [], raw
    assert "CL_R12_INSTRUMENT_TIMEOUT" in RUNNER      # am instrument has its own, longer bound


def test_an_aborted_runner_records_its_cause_in_the_receipt():
    assert "trap " in RUNNER and "CL_R12_RUNNER_ABORTED" in RUNNER and "ERR" in RUNNER
