"""CL-INT-02: static contracts for the Type110 continuity presentation host, runner and workflow.

Run 41005188914 timed out waiting for SURFACE_BORROWED_READY and then logged
RENDERER_ATTACH_FAILED type=IllegalStateException / RENDERER_RELEASED: the Activity handed the
renderer a plain Display1OutputBackend.Host, and attach() requires a callback-capable EventHost.
These tests do not run an emulator; the API17 workflow is the end-to-end regression test.
"""
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ACTIVITY = (REPO / "android/cl-imp-03-app/java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
BACKEND = (REPO / "src/claritylink-renderer/android-api17/Display1OutputBackend.java").read_text()
RUNNER_PATH = REPO / "tools/run_cl_int_02_api17_ci.sh"
RUNNER = RUNNER_PATH.read_text()
WORKFLOW = (REPO / ".github/workflows/cl-int-02-api17-integration.yml").read_text()
PRODUCER = (REPO / "android/cl-imp-03-app/java/org/claritylink/android/Type111ProducerService.java").read_text()


def host_class() -> str:
    start = ACTIVITY.index("private final class PresentationPaneHost")
    end = ACTIVITY.index("private void awaitFrame(", start)
    return ACTIVITY[start:end]


def method_body(source: str, signature: str) -> str:
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        depth += {"{": 1, "}": -1}.get(source[index], 0)
        if depth == 0:
            return source[brace:index + 1]
    raise AssertionError(f"unterminated body for {signature}")


def test_backend_still_requires_a_callback_capable_event_host():
    # The fix is in the Activity; the backend requirement must not be relaxed.
    assert "pane leases require a callback-capable simulated host" in BACKEND
    assert "host instanceof EventHost" in BACKEND


def test_presentation_host_is_an_event_host_not_a_plain_host():
    host = host_class()
    assert "implements Display1OutputBackend.EventHost" in host
    assert "new PresentationPaneHost(root, generation, geometry)" in method_body(
        ACTIVITY, "public void presentationRoot(")
    assert "new Display1OutputBackend.Host()" not in ACTIVITY


def test_host_exposes_every_event_host_member():
    host = host_class()
    for member in ("void addPaneEventListener(", "void removePaneEventListener(", "boolean isHostValid()",
                   "boolean isInterruptActive()", "RendererViewport getPaneViewport()",
                   "Object generationOwner()"):
        assert member in host, member


def test_pane_lifecycle_listeners_are_registered_and_forwarded():
    host = host_class()
    assert "listeners.add(listener)" in host and "listeners.remove(listener)" in host
    assert "listener.onPaneEvent(event)" in host
    assert "PaneEvent.Type.HOST_LOST" in host      # forwarded when the session is released
    assert "PaneEvent.Type.VIEWPORT_CHANGED" in host
    assert "eventSequence.incrementAndGet()" in host   # strictly increasing sequence for the backend filter
    release = method_body(ACTIVITY, "private void releaseRenderer()")
    assert release.index("oldHost.hostLost()") < release.index("old.close()")


def test_host_validity_fails_closed_on_session_state():
    valid = method_body(host_class(), "public boolean isHostValid()")
    for guard in ("hostAvailable", "!hostClosed", "active", "!closing", "presentationRoot == root"):
        assert guard in valid, guard
    assert "isHostValid() ? root : null" in host_class()


def test_warning_state_reaches_the_host_without_reviving_authority():
    host = host_class()
    assert "public boolean isInterruptActive() { return interruptActive; }" in host
    interrupt = method_body(host, "void setInterruptActive(boolean visible)")
    assert "PaneEvent.Type.INTERRUPT_ON" in interrupt
    assert "PaneEvent.Type.INTERRUPT_OFF" in interrupt
    sink_warning = method_body(ACTIVITY, "public boolean setWarningVisible(long generation, boolean visible)")
    assert "host.setInterruptActive(visible)" in sink_warning
    assert "explicit fresh attach is required" in sink_warning


def test_page_host_and_viewport_transitions_publish_real_state_changes():
    host = host_class()
    page = method_body(host, "void setNavigationPageSelected(boolean selected)")
    assert "pageSelected == selected" in page
    assert "PAGE_SELECTED" in page and "PAGE_DESELECTED" in page
    assert "isHostValid() && pageSelected" in method_body(host, "public boolean isNavigationPageActive()")
    viewport = method_body(host, "void changeViewport(RendererViewport viewport)")
    assert "paneViewport = viewport" in viewport
    assert "VIEWPORT_CHANGED" in viewport
    assert "paneViewport == viewport" in viewport
    assert "width == RendererViewport.LOGICAL_WIDTH" in host
    assert "changeViewport(width ==" in host
    layout_start = host.index("this.layoutListener = new View.OnLayoutChangeListener()")
    layout_end = host.index("this.attachStateListener = new View.OnAttachStateChangeListener()", layout_start)
    layout = host[layout_start:layout_end]
    assert "if (hostClosed) return;" in layout
    assert "if (width <= 0 || height <= 0)" in layout
    assert "changeViewport(null);" in layout


def test_cl_int_02_runtime_runner_proves_emulator_identity_before_device_mutation():
    runner = (REPO / "tools/run_cl_int_02_api17_ci.sh").read_text()
    assert 'adbq shell getprop ro.kernel.qemu' in runner
    assert 'adbq shell getprop ro.hardware' in runner
    assert '[[ "$qemu" == 1 && "$hardware" =~ ^(goldfish|ranchu|ranchu64)$ ]]' in runner
    assert runner.index('[[ "$qemu" == 1') < runner.index('adbq uninstall "$package"')
    assert 'emulator_identity=verified ro.kernel.qemu=$qemu ro.hardware=$hardware' in runner


def test_host_loss_restoration_and_listener_cleanup_are_fail_closed():
    host = host_class()
    availability = method_body(host, "void setHostAvailable(boolean available)")
    assert "HOST_RESTORED" in availability and "HOST_LOST" in availability
    assert "hostAvailable == available" in availability
    terminal = method_body(host, "void hostLost()")
    assert "hostClosed = true" in terminal
    assert "removeOnLayoutChangeListener" in terminal
    assert "removeOnAttachStateChangeListener" in terminal
    assert "listeners.remove(listener)" in method_body(host, "public void removePaneEventListener(")
    focus = method_body(ACTIVITY, "public void onWindowFocusChanged(boolean hasFocus)")
    assert "setNavigationPageSelected(hasFocus)" in focus


def test_simulator_can_publish_invalid_viewport_as_a_real_transition():
    simulator = (REPO / "src/claritylink-renderer/android-api17/HondaStyleSimulatorRendererHost.java").read_text()
    changed = method_body(simulator, "public void simulateViewportChanged(RendererViewport viewport)")
    assert "paneViewport = viewport" in changed
    assert "PaneEvent.Type.VIEWPORT_CHANGED" in changed
    assert "viewport == null" not in changed


def test_viewport_reattach_rechecks_current_host_state_with_new_generation():
    attach = method_body(BACKEND, "public synchronized void attach(long newPaneGeneration)")
    assert "paneViewportValid = eventHost.getPaneViewport() != null" in attach
    assert "paneViewportValid" in attach
    explicit_start = ACTIVITY.index("private boolean reattachPaneLeaseAfterInterrupt()")
    explicit_end = ACTIVITY.index("private boolean awaitLabWarningHostState(", explicit_start)
    explicit = ACTIVITY[explicit_start:explicit_end]
    for guard in ("host.isHostValid()", "host.isNavigationPageActive()", "host.isInterruptActive()",
                  "host.getPaneViewport() != null"):
        assert guard in explicit
    assert "Looper.myLooper() == Looper.getMainLooper()" in explicit
    assert "main.post(admission)" in explicit
    assert "completed.await(10L, TimeUnit.SECONDS)" in explicit
    assert "Math.max(paneAttachmentGeneration, expectedRenderer.paneGeneration()) + 1L" in " ".join(explicit.split())
    assert "expectedRenderer.attach(nextGeneration)" in explicit
    warning = method_body(ACTIVITY, "public boolean setWarningVisible(long generation, boolean visible)")
    assert "reattachPaneLeaseAfterInterrupt" not in warning


def test_warning_withdrawal_accepts_detached_view_and_forbids_stale_pixels():
    withdrawal = method_body(ACTIVITY, "private void submitDecodedFrameExpectWarningReject(")
    assert "(view == null || !view.hasDisplayedFrame())" in withdrawal
    assert "(view == null || view.drawnTimestampNs() != frame.presentationTimeNs)" in withdrawal
    assert "warning_blocked_decoded_pixels_withdrawn" in withdrawal


def test_actual_producer_death_withdraws_view_lease_before_fresh_reconnect():
    fault = method_body(ACTIVITY, "private void runIndependentType111ProducerFault(")
    callback_start = fault.index("public void onServiceDisconnected(ComponentName name)")
    callback_end = fault.index("\n            }", callback_start)
    callback = fault[callback_start:callback_end]
    withdraw = method_body(ACTIVITY, "private void withdrawType111PresentationOnProducerDeath(")
    backend_withdraw = method_body(BACKEND, "public synchronized void withdrawPresentation()")
    assert "AtomicReference<FrameStreamIdentity> producerIdentity" in fault
    assert "withdrawType111PresentationOnProducerDeath(name, producerIdentity.get());" in callback
    assert "producerIdentity.set(before);" in fault
    assert fault.index("producerIdentity.set(queueIdentity);") < fault.index(
        "prepareType111ProducerBinder(producerBinder[0], queueIdentity)")
    assert "current.withdrawPresentation();" in withdraw
    assert "view_detached_and_cleared=" in withdraw
    assert "!producerIdentity.equals(activeIdentity)" in withdraw
    assert "stale_callback_rejected=true" in withdraw
    assert "fresh_pane_lease_admitted_after_producer_death_clear" in fault
    assert fault.index("queued_predeath_frames_finish_after_view_withdrawal") < fault.index(
        "frameIpcClient.replaceGeneration(oldIdentity.streamGeneration, freshGeneration)")
    assert "TYPE111_PRODUCER_DEATH_VIEW_CLEAR_PASS" in fault
    assert '" old_generation=" + oldIdentity.streamGeneration' in fault
    assert '" new_generation=" + freshIdentity.streamGeneration' in fault
    assert "withdrawnAndReady" in method_body(ACTIVITY, "public boolean replaceGeneration(final long oldGeneration,")
    assert "revokeLease();" in backend_withdraw
    pane_test = (REPO / "android/src/test/java/org/claritylink/renderer/Display1PaneLeaseLifecycleTest.java").read_text()
    assert "replacementBackend.withdrawPresentation();" in pane_test
    assert "replacementBackend.attach(2L);" in pane_test


def test_frame_draw_wait_uses_parent_view_generation_after_stream_rebind():
    enqueue = method_body(ACTIVITY, "public boolean enqueue(DecodedFrame frame, long generation,")
    assert "identity.streamGeneration != generation" in enqueue
    assert "renderer.submit(frame, viewSink.dispatchGate(), generation, dispatchEpoch)" in enqueue
    assert "long viewGeneration = activeGeneration" in enqueue
    assert "awaitFrame(0, viewGeneration, frame.presentationTimeNs)" in enqueue
    assert "awaitRaceRecoveryFrame(0, viewGeneration, frame.presentationTimeNs)" in enqueue


def test_stream_rebind_advances_backend_identity_without_changing_pane_lease():
    replace_stream = method_body(BACKEND,
            "public synchronized boolean replaceStreamGeneration(long oldGeneration, long newGeneration)")
    for guard in ("requireUiThread()", "newGeneration <= oldGeneration", "lease.isValid()",
                  "activeStreamGeneration = newGeneration", "lastSubmittedTimestampNs = -1L"):
        assert guard in replace_stream
    assert "activeStreamGeneration == 0L || activeStreamGeneration == oldGeneration" in replace_stream
    replace_activity = method_body(ACTIVITY, "public boolean replaceGeneration(final long oldGeneration,")
    assert "renderer.replaceStreamGeneration(oldGeneration, newGeneration)" in replace_activity
    assert "renderer.clear()" in replace_activity
    pane_test = (REPO / "android/src/test/java/org/claritylink/renderer/Display1PaneLeaseLifecycleTest.java").read_text()
    assert "replaceStreamGeneration(55L, 56L)" in pane_test
    assert "replaceStreamGeneration(77L, 78L)" in pane_test
    assert "PresentStatus.IDENTITY_MISMATCH" in pane_test
    assert "captureEpoch(56L)" in pane_test


def test_real_producer_binder_is_authorized_before_decoder_readiness():
    fixture = method_body(ACTIVITY, "private void startType111FixtureRun(")
    prepare = method_body(ACTIVITY, "private void prepareType111Producer(")
    producer_prepare = method_body(PRODUCER, "private synchronized boolean prepareProducer(")
    assert fixture.index("prepareType111Producer(controlIdentity)") < fixture.index(
        "control.videoConfig(controlIdentity, 32, 32)")
    assert "PREPARE_PRODUCER" in PRODUCER
    assert "authorizeWithCompositor(endpoint, identity, ownerPid)" in producer_prepare
    assert "producer_pid=" in prepare
    assert "decoder_started=false" in prepare
    assert "producer_pid=" in prepare
    assert "new Api17BufferH264Decoder(32, 32, 960001L, blueConfig)" in fixture


def test_producer_prepare_is_scoped_to_authorized_view_and_type111_identity():
    prepare_dispatch = method_body(PRODUCER, "@Override protected boolean onTransact(")
    prepare = method_body(PRODUCER, "private synchronized boolean prepareProducer(")
    assert "isAuthorizedViewCaller(ownerPid)" in prepare_dispatch
    assert "identity.streamType != FrameStreamIdentity.TYPE111" in prepare
    assert "identity.outputId != FrameStreamIdentity.OUTPUT_SECONDARY_VIEW" in prepare
    assert "identity.isValid()" in prepare
    assert "endpoint == null" in prepare
    assert "control.isBinderAlive()" in prepare
    assert "preparedType111ProducerConnection" in method_body(ACTIVITY, "@Override protected void onDestroy()")


def test_producer_lifetime_binder_reports_descriptor_before_token_enforcement():
    dispatch = method_body(PRODUCER, "@Override protected boolean onTransact(")
    assert dispatch.index("code == IBinder.INTERFACE_TRANSACTION") < dispatch.index(
        "data.enforceInterface(DESCRIPTOR)")
    assert "reply.writeString(DESCRIPTOR)" in dispatch


def test_guarded_runner_executes_optional_pane_lease_instrumentation():
    guarded = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert "CL_PANE_LEASE_TEST_APK" in guarded
    assert "PANE_LEASE_API17_INSTRUMENTATION_PASS tests=" in guarded
    assert "org.claritylink.renderer.Display1PaneLeaseLifecycleTest" in guarded
    assert "check-emulator-inventory" in guarded and "process_identity=verified" in guarded


def test_reconnected_frame_waits_boundedly_for_prior_pfd_transfer():
    submission_start = ACTIVITY.index("private void submitDecodedFrame(final DecodedFrame frame,")
    submission_end = ACTIVITY.index("private boolean awaitFrameIpcIdle(", submission_start)
    submission = ACTIVITY[submission_start:submission_end]
    assert "client.hasFrameInFlight()" in submission
    assert "awaitFrameIpcIdle(client, 2000L)" in submission
    assert "type111_previous_frame_transfer_did_not_drain" in submission
    idle = method_body(ACTIVITY, "private boolean awaitFrameIpcIdle(FrameIpcClient client, long timeoutMs)")
    assert "SystemClock.elapsedRealtime() + timeoutMs" in idle
    assert "Thread.sleep(5L)" in idle
    assert "return !client.hasFrameInFlight()" in idle


def test_content_attach_keeps_generation_fencing_and_ownership():
    host = host_class()
    attach = method_body(host, "public boolean attachContent(")
    for guard in ("isNavigationPageActive()", "content == null", "requestedGeneration != hostGeneration",
                  "content.getParent() != null"):
        if guard == "requestedGeneration != hostGeneration":
            assert "requestedGeneration != hostGeneration" in attach
        else:
            assert guard in attach, guard
    assert "requestedGeneration <= lastAttachmentGeneration" in attach
    detach = method_body(host, "public boolean detachContent(")
    assert "ownedContent != content || ownedGeneration != requestedGeneration" in detach


def test_generation_owner_is_the_host_lifetime():
    assert "public Object generationOwner() { return this; }" in host_class()


def test_attach_failure_still_fails_closed():
    root = method_body(ACTIVITY, "public void presentationRoot(")
    assert "renderer.attach();" in root
    failure = root[root.index("catch (RuntimeException failure)"):]
    assert 'log("RENDERER_ATTACH_FAILED type="' in failure
    assert "releaseRenderer();" in failure and "active = false;" in failure


def test_runner_is_valid_bash_and_never_targets_a_non_emulator():
    subprocess.run(["bash", "-n", str(RUNNER_PATH)], check=True)
    assert r"^emulator-[0-9]+$" in RUNNER
    assert "VEHICLE_DEPLOYMENT_NOT_AUTHORIZED" in RUNNER and "safeForHonda=false" in RUNNER


def test_runner_requires_the_continuity_evidence_and_fails_on_attach_failure():
    for marker in ("SURFACE_BORROWED_READY valid=true", "CL_R4B_MULTI_VIEW_REPLACEMENT_PASS",
                   "IPC_VIEW_SINK_DEATH_CALLBACK", "IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true "
                   "active_pfd_transfers=0 retained_frame_bytes=0", "fresh_frame=true pixels_verified=true"):
        assert marker in RUNNER, marker
    assert "RENDERER_ATTACH_FAILED" in RUNNER
    assert "generation > last_generation && frame > last_type110_frame" in RUNNER
    assert "a View PID was reused" in RUNNER
    for ordinal_loop in ("for ordinal in 1 2 3", "unique_pids=true", "increasing_generations=true"):
        assert ordinal_loop in RUNNER


def test_producer_death_fallback_requires_exact_old_stream_generation():
    guarded = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert 'expected_rejection_identity="$producer_identity"' in guarded
    assert 'rejection_identity" = "$expected_rejection_identity"' in guarded


def test_pass_marker_is_only_emitted_after_every_check():
    final = RUNNER.index("echo \"CL_INT_02_TYPE110_CONTINUITY_API17_PASS")
    assert final > RUNNER.index("for ordinal in 1 2 3")
    assert final > RUNNER.index("IPC_STREAM_UNREGISTERED")
    assert final > RUNNER.index("RENDERER_ATTACH_FAILED present in the final log")


def test_workload_mode_delegates_to_the_unchanged_r12_gates():
    assert "tools/run_cl_r12_api17_ci.sh" in RUNNER
    for verdict in ("CL_R12_GATE_CANDIDATE=PASS", "CL_R12_GATE_SOAK=PASS", "CL_R12_API17_RUNTIME_PASS",
                    "CL_PANE_LEASE_INSTRUMENTATION=PASS", "CL_INT_04_HOST_WITHDRAWAL_INSTRUMENTATION=PASS"):
        assert verdict in RUNNER, verdict
    assert "check_cl_r12_perf_gate" not in WORKFLOW   # the workflow never re-implements or edits the gate


def test_workflow_pins_the_baseline_and_runs_both_kinds():
    assert "7e95839acfcb95af9fdab4f4b8e623b2907f6613" in WORKFLOW
    assert re.search(r"kind:\s*\[continuity, workload\]", WORKFLOW)
    assert "tools/build_cl_r12_workload_ab.sh" in WORKFLOW
    assert "./tools/run_cl_int_02_api17_ci.sh ${{ matrix.kind }}" in WORKFLOW
    assert "needs.api17.result" in WORKFLOW and "= success" in WORKFLOW
    for watched_input in (
        "tools/run_cl_imp_03_emulator.sh",
        "tools/build_cl_imp_03_apks.sh",
        "tools/build_cl_honda_111_pane_test_apk.sh",
        "tools/build_cl_r12_workload_ab.sh",
        "tools/build_cl_int_04_host_test_apk.sh",
        "tools/run_cl_r12_api17_ci.sh",
        "tools/api17_runner_guard.py",
        "tools/verify_apk_dex_classes.py",
        "android/src/test/**",
        "tests/display/test_cl_int_02_type110_continuity.py",
        "tests/display/test_cl_r4b_fault_acceptance_contract.py",
        "tests/display/test_cl_imp_04_ipc_contract.py",
    ):
        assert f"'{watched_input}'" in WORKFLOW, watched_input
    assert "PresentationPaneHost" in WORKFLOW        # DEX check covers the fixed class
    assert "permissions:\n  contents: read" in WORKFLOW


def test_workflow_stays_synthetic_lab_only():
    lowered = WORKFLOW.lower()
    for forbidden in ("secrets.", "pull_request_target", "adb connect"):
        assert forbidden not in lowered, forbidden
    assert "VEHICLE_DEPLOYMENT_NOT_AUTHORIZED" in WORKFLOW
