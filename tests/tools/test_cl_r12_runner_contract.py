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


def test_host_withdrawal_instrumentation_is_built_run_and_reported_separately():
    # CL-INT-04: Display1HostExpiryTest runs on the same Android 4.2.2 x86 emulator, in its own package,
    # with its own verdict; the PaneLease and performance verdicts neither feed nor mask it.
    assert "build_cl_int_04_host_test_apk.sh" in WORKFLOW and "CL_INT_04_HOST_TEST_APK" in WORKFLOW
    assert "--label host-withdrawal-test" in WORKFLOW and "host-withdrawal-test-apk.sha256" in WORKFLOW
    assert "org.claritylink.renderer.Display1HostExpiryTest" in RUNNER
    assert "org.claritylink.hostwithdrawal.test/android.test.InstrumentationTestRunner" in RUNNER
    assert "host_withdrawal_instrumentation=NOT_RUN" in RUNNER   # absent APK = not run, never inferred PASS
    assert 'if [[ -n "${CL_INT_04_HOST_TEST_APK:-}" ]]' in RUNNER
    block = RUNNER.split("host_withdrawal_instrumentation=NOT_RUN", 1)[1].split("run_performance()", 1)[0]
    assert "OK (7 tests)" in block and "host_withdrawal_instrumentation=PASS" in block
    assert "adbq uninstall org.claritylink.hostwithdrawal.test" in block.split("INSTRUMENTATION=", 1)[1]
    assert "CL_INT_04_HOST_WITHDRAWAL_INSTRUMENTATION=" in RUNNER
    assert RUNNER.index("exit 14") < RUNNER.index("echo 'CL_R12_API17_RUNTIME_PASS'")
    assert RUNNER.index("exit 13") < RUNNER.index("exit 14")   # the PaneLease verdict keeps its place
    assert "tools/build_cl_int_04_host_test_apk.sh" in WORKFLOW.split("jobs:")[0]  # path-triggered


def test_host_withdrawal_expected_test_count_matches_the_java_class():
    source = (REPO / "android/src/test/java/org/claritylink/renderer/Display1HostExpiryTest.java").read_text()
    assert source.count("public void test") == 7   # the runner demands exactly "OK (7 tests)"


def test_host_withdrawal_apk_inputs_are_explicit_and_request_no_permission():
    script = (REPO / "tools/build_cl_int_04_host_test_apk.sh").read_text()
    manifest = (REPO / "android/cl-int-04-host-withdrawal-test/AndroidManifest.xml").read_text()
    assert "uses-permission" not in manifest and "<activity" not in manifest
    assert 'android:process=":producer"' in manifest and 'android:exported="false"' in manifest
    assert "Display1HostExpiryTest.java" in script and "ProducerDeathService.java" in script
    assert "must request no permissions" in script


def test_renderer_ab_lease_class_expectation_follows_the_baseline_tree():
    # A baseline from a main that already has PaneLease must REQUIRE the lease classes; only a
    # baseline that predates them may FORBID them. A hard-coded --forbid fails every renderer PR
    # branched from such a main, for a reason unrelated to the change under test.
    assert "sed -n 's/^baseline_commit=//p'" in WORKFLOW and "ab-identity.txt" in WORKFLOW
    assert 'git cat-file -e "$baseline_commit:src/claritylink-renderer/android-api17/PaneLease.java"' in WORKFLOW
    branch = WORKFLOW.split('git cat-file -e "$baseline_commit:src/claritylink-renderer/android-api17/PaneLease.java"')[1]
    then_part, else_part = branch.split("else", 1)
    assert "--require org.claritylink.renderer.PaneLease" in then_part and "--forbid" not in then_part
    assert "--forbid org.claritylink.renderer.PaneLease" in else_part.split("fi", 1)[0]
    assert '"${lease_expectation[@]}"' in WORKFLOW


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


def test_renderer_mode_overlays_workload_support_classes_the_activity_calls():
    script = (REPO / "tools/build_cl_r12_renderer_ab.sh").read_text()
    support = "android/cl-imp-03-app/java/org/claritylink/android/MessengerFrameParcel.java"
    assert support in script and "workload_support" in script
    # the candidate activity reads the returned frame into a reusable buffer through this class;
    # a baseline tree that predates the overload must receive the candidate's copy, or it cannot build
    activity = (REPO / "android/cl-imp-03-app/java/org/claritylink/android/MessengerFramePerformanceActivity.java").read_text()
    assert "MessengerFrameParcel.read(" in activity
    assert "Workload support source differs between variants" in script   # identity is verified, not assumed
    assert "src/claritylink-renderer" not in script.split("workload_support=")[1].split("\n")[0]


def test_no_adb_call_can_block_the_runner_forever():
    assert "adbq()" in RUNNER and "timeout" in RUNNER
    # every adb invocation against the emulator goes through the bounded wrapper
    raw = [l for l in RUNNER.splitlines() if '"$adb" -s' in l and not l.lstrip().startswith("adbq()")]
    assert raw == [], raw
    assert "CL_R12_INSTRUMENT_TIMEOUT" in RUNNER      # am instrument has its own, longer bound


def test_an_aborted_runner_records_its_cause_in_the_receipt():
    assert "trap " in RUNNER and "CL_R12_RUNNER_ABORTED" in RUNNER and "ERR" in RUNNER


def test_workflow_verifies_classes_in_the_built_dex_not_the_source_list():
    assert "tools/verify_apk_dex_classes.py" in WORKFLOW and "dex-verification.txt" in WORKFLOW
    assert "build-tools/35.0.0/dexdump" in WORKFLOW
    # candidate lab APK, pane-test APK and baseline APK are each inspected
    for label in ("candidate-lab", "pane-lease-test", "baseline-lab"):
        assert f"--label {label}" in WORKFLOW, label
    # the lab APK must carry the lease classes and the shared-converter and in-place viewport methods
    for needed in ("org.claritylink.renderer.PaneLease", "org.claritylink.renderer.PaneEvent",
                   "Display1OutputBackend#setRendererViewport", "ClarityLinkContentView#useSharedConverter",
                   "SyntheticFrameFill#fill", "MessengerFrameParcel#read"):
        assert needed in WORKFLOW, needed
    # in renderer A/B the pre-lease baseline must not contain the lease classes
    assert "--forbid org.claritylink.renderer.PaneLease" in WORKFLOW
    # the APK itself is never uploaded; only the text report and hashes are
    upload = WORKFLOW.split("upload-artifact@")[1]
    assert ".apk" not in upload.replace("apk.sha256", "").replace("apk-ab.sha256", "").replace("pane-test-apk.sha256", "")


def test_fd_instrumentation_asserts_converter_thread_reuse_not_only_a_bound():
    source = (REPO / "android/src/test/java/org/claritylink/renderer/PaneLeaseFdLifecycleTest.java").read_text()
    assert "liveConverterThreadIds()" in source and "exactly one converter thread" in source
    assert "PANE_CONVERTER_REUSE" in source and "firstConverterId" in source
    # the test must not retain Thread objects: a held HandlerThread keeps its quit Looper's queue (and its
    # descriptors) reachable, which made the settled-descriptor assertion fail in run 39873809281
    assert "Thread firstConverter" not in source and "List<Thread>" not in source
    assert "converter thread must be gone after close" in source
