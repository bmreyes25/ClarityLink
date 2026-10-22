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
    assert "OK (2 tests)" in RUNNER and "Display1RendererViewportInPlaceTest" in RUNNER
    assert "CL_PANE_LEASE_INSTRUMENTATION=" in RUNNER
    assert RUNNER.index("exit 13") < RUNNER.index("echo 'CL_R12_API17_RUNTIME_PASS'")


def test_pane_test_apk_inputs_are_explicit_and_request_no_permission():
    script = (REPO / "tools/build_cl_honda_111_pane_test_apk.sh").read_text()
    manifest = (REPO / "android/cl-honda-111-pane-test/AndroidManifest.xml").read_text()
    assert "uses-permission" not in manifest and "<activity" not in manifest and "<service" not in manifest
    assert "PaneLeaseTest.java" in script and "Display1PaneLeaseLifecycleTest.java" in script
    assert "must request no permissions" in script
