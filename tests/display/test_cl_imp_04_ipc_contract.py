from pathlib import Path
import xml.etree.ElementTree as ET


REPO = Path(__file__).resolve().parents[2]
APP = REPO / "android/cl-imp-03-app"
ANDROID = "{http://schemas.android.com/apk/res/android}"


def test_lab_compositor_is_private_and_runs_in_a_distinct_process():
    manifest = ET.parse(APP / "AndroidManifest.lab.xml").getroot()
    app = manifest.find("application")
    service = app.find("service")
    assert service is not None
    assert service.get(ANDROID + "process") == ":compositor"
    assert service.get(ANDROID + "exported") == "false"
    assert manifest.findall("uses-permission") == []


def test_frame_sink_closes_pfd_when_payload_allocation_fails():
    source = (APP / "java/org/claritylink/android/FrameViewSink.java").read_text()
    read_payload = source[source.index("private static byte[] readPayload"):
                          source.index("private static void closeQuietly")]
    assert read_payload.index("new ParcelFileDescriptor.AutoCloseInputStream(descriptor)") < read_payload.index("try {")
    assert read_payload.index("try {") < read_payload.index("new byte[expected]")
    assert "finally { input.close(); }" in read_payload


def test_frame_sink_releases_both_queue_budgets_after_allocation_failure():
    source = (APP / "java/org/claritylink/android/FrameViewSink.java").read_text()
    frame_creation = source[source.index("final DecodedFrame frame;"):
                            source.index("final boolean queued;")]
    assert "catch (OutOfMemoryError exhausted)" in frame_creation
    assert frame_creation.count("queuedBytes.addAndGet(-payloadBytes)") >= 2
    assert frame_creation.count("queuedFrames.decrementAndGet()") >= 2
    dispatch = source[source.index("final boolean queued;"):source.index("if (queued) {")]
    assert "catch (OutOfMemoryError exhausted)" in dispatch
    assert "queuedBytes.addAndGet(-payloadBytes)" in dispatch
    assert "queuedFrames.decrementAndGet()" in dispatch


def test_type110_lab_sink_survives_type111_view_process_death():
    manifest = ET.parse(APP / "AndroidManifest.lab.xml").getroot()
    app = manifest.find("application")
    services = {item.get(ANDROID + "name"): item for item in app.findall("service")}
    activities = {item.get(ANDROID + "name"): item for item in app.findall("activity")}
    assert services["org.claritylink.android.FrameLabSinkService"].get(ANDROID + "process") == ":type110_sink"
    assert activities["org.claritylink.android.ClarityLinkDisplayActivity"].get(ANDROID + "process") == ":type111_view"
    assert services["org.claritylink.android.FrameLabSinkService"].get(ANDROID + "exported") == "false"
    assert activities["org.claritylink.android.ClarityLinkDisplayActivity"].get(ANDROID + "exported") == "true"
    assert activities["org.claritylink.android.ClarityLinkDisplayActivity"].get(ANDROID + "permission") == "android.permission.DUMP"
    assert "TYPE110_LAB_SINK_READY" in (
        APP / "java/org/claritylink/android/FrameLabSinkService.java"
    ).read_text()
    probe = (APP / "java/org/claritylink/android/Type110ProgressProbeService.java").read_text()
    assert "attachExistingType110" in probe
    assert "CL_R4_TYPE110_AFTER_TYPE111_SINK_DEATH_PASS" in probe
    assert "record.lastFrameId" in probe


def test_type111_decoder_producer_is_private_and_separate_from_view_process():
    manifest = ET.parse(APP / "AndroidManifest.lab.xml").getroot()
    app = manifest.find("application")
    services = {item.get(ANDROID + "name"): item for item in app.findall("service")}
    producer = services["org.claritylink.android.Type111ProducerService"]
    assert producer.get(ANDROID + "process") == ":type111_producer"
    assert producer.get(ANDROID + "exported") == "false"
    activities = {item.get(ANDROID + "name"): item for item in app.findall("activity")}
    activity = activities["org.claritylink.android.ClarityLinkDisplayActivity"]
    assert activity.get(ANDROID + "process") == ":type111_view"
    service = (APP / "java/org/claritylink/android/Type111ProducerService.java").read_text()
    client = (APP / "java/org/claritylink/android/FrameIpcClient.java").read_text()
    assert "attachExistingType111" in service
    assert "client.submit(frame, identity.streamGeneration" in service
    assert "runFinished.await(timeout, TimeUnit.MILLISECONDS)" in service
    assert "timeout < 0L || timeout > MAX_WAIT_MS" in service
    assert "Process.killProcess(Process.myPid())" in service
    assert "static FrameIpcClient attachExistingType111" in client
    assert "streamIdentity.streamType != FrameStreamIdentity.TYPE111" in client


def test_api17_type111_producer_fault_stage_is_required_by_runtime_harness():
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    assert "wait_for 'CL_R4_TYPE111_PRODUCER_DEATH_RESTART_PASS'" in runner
    assert "actual_type111_producer_death_and_binder_callback" in activity
    assert "type110_frame_progressed_after_actual_type111_producer_death" in activity
    assert "predeath_type111_generation_rejected_after_restart" in activity
    assert "new_pid=" in activity and "binder_pfd=true view_draw=true" in activity
    assert 'captureType111Proof("type111-independent-producer-frame.png")' in activity
    assert 'captureType111Proof("type111-restarted-producer-frame.png")' in activity
    assert "type111-independent-producer-frame.png" in runner
    assert "type111-restarted-producer-frame.png" in runner
    assert "verifyProducerWaitBounds(producerBinder[0], descriptor)" in activity
    assert "TYPE111_PRODUCER_WAIT_BOUNDS_PASS" in activity
    assert "LAB_ARM_TRANSFER_BARRIER" in activity
    assert "inflight_pfd_eof_cleanup_without_accepting_partial_frame" in activity
    assert "wait_for 'CL_R4_TYPE111_INFLIGHT_PRODUCER_DEATH_CLEANUP_PASS'" in runner



def test_type110_progress_probe_is_private_and_uses_one_shot_owner_record():
    manifest = ET.parse(APP / "AndroidManifest.lab.xml").getroot()
    app = manifest.find("application")
    services = {item.get(ANDROID + "name"): item for item in app.findall("service")}
    probe_manifest = services["org.claritylink.android.Type110ProgressProbeService"]
    assert probe_manifest.get(ANDROID + "exported") == "false"
    assert probe_manifest.get(ANDROID + "permission") is None
    assert probe_manifest.get(ANDROID + "process") == ":type110_probe"

    probe = (APP / "java/org/claritylink/android/Type110ProgressProbeService.java").read_text()
    owner = (APP / "java/org/claritylink/android/Type110LabProbeOwnership.java").read_text()
    assert "CL_IMP_03_OFFLINE_EMULATOR_ONLY" not in probe
    assert "EXTRA_CONFIRM" not in probe
    assert "Type110LabProbeOwnership.consume(this, expectedDeath)" in probe
    assert "getLongExtra" not in probe
    assert "parentTeardown(owner)" in probe
    assert "renameTo(claimed)" in owner
    assert "Files.readAllBytes" not in owner
    assert "parentTeardown(sessionId)" not in probe
    assert "DUPLICATE_START_IGNORED" in probe
    client = (APP / "java/org/claritylink/android/Type111ControlClient.java").read_text()
    service = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    assert "parentTeardown(final FrameStreamIdentity type110Owner)" in client
    assert "teardownType111Session(readIdentity(data))" in service
    assert "session_owner_stream_unregistered" in service
    assert "!type110Owner.equals(owner.identity)" in service
    assert "stopService(" not in probe[probe.index("catch (Throwable failure)"):]


def test_recovery_probe_is_bound_to_the_exact_type111_death_identity():
    owner = (APP / "java/org/claritylink/android/Type110LabProbeOwnership.java").read_text()
    compositor = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    service = (APP / "java/org/claritylink/android/Type110ProgressProbeService.java").read_text()
    assert "VERSION = 2" in owner
    issue_body = owner[owner.index("static synchronized boolean issue("):owner.index("/** Atomically claims")]
    assert "if (!clearAbandonedClaim(claimed)) return false" in issue_body
    assert "File record = sessionFile(directory, identity.sessionId, RECORD_SUFFIX)" in issue_body
    assert "if (existing != null || !record.delete()) return false" in issue_body
    assert "pending >= MAX_PENDING_OWNERS" in issue_body
    assert "private static File sessionFile(File directory, long sessionId, String suffix)" in owner
    assert "RECORD_PREFIX + Long.toHexString(sessionId) + suffix" in owner
    assert "MAX_PENDING_OWNERS = 32" in owner
    assert "OWNER_RECORD_TTL_MS = 5L * 60L * 1000L" in owner
    assert "private static boolean pruneAbandonedArtifacts(Context context, File directory)" in owner
    assert 'name.endsWith(".tmp")' in owner
    assert 'name.endsWith(".claimed")' in owner
    assert "now - modified > OWNER_RECORD_TTL_MS" in owner
    has_pending_body = owner[owner.index("static synchronized boolean hasPending("):owner.index("static synchronized boolean issue(")]
    consume_body = owner[owner.index("static synchronized Record consume("):owner.index("private static Record read(")]
    assert "sessionFile(directory, expectedDeath.sessionId, RECORD_SUFFIX)" in has_pending_body
    assert "sessionFile(directory, expectedDeath.sessionId, RECORD_SUFFIX)" in consume_body
    assert 'sessionFile(directory, expectedDeath.sessionId, ".claimed")' in consume_body
    assert "FileChannel.tryLock" in owner or "channel.tryLock()" in owner
    assert "LOCK_WAIT_MS = 1000L" in owner
    assert "static synchronized Record consume(" in owner
    assert "if (!clearAbandonedClaim(claimed) || !record.renameTo(claimed)) return null" in owner
    assert "claimed.delete()" not in issue_body
    application = (APP / "java/org/claritylink/android/ClarityLinkDisplayApplication.java").read_text()
    assert "new SecureRandom().nextLong()" in application
    assert "SESSION_COUNTER_MASK = 0xffffL" in application
    assert "return nonce << 16" in application
    assert "expectedType111Death.equals(expectedDeath)" in owner
    assert "identity.sessionId != expectedType111Death.sessionId" in owner
    assert "deadIdentity = state.sink == registeredSink ? state.identity : registeredIdentity;" in compositor
    assert "hasPending(CompositorService.this, deadIdentity)" in compositor
    assert "putExpectedDeath(recovery, deadIdentity)" in compositor
    assert "frameIpcClient.streamIdentity()" in activity
    assert "expectedType111Death, stats.frameId, stats.pid" in activity
    assert "consume(this, expectedDeath)" in service
    assert "TYPE110_POST_DEATH_PROBE_DUPLICATE_START_IGNORED" in service
    assert "expected_type111_connection_id=" in service
    assert "expected_type111_generation=" in service


def test_recovery_owner_handoffs_are_keyed_and_bounded_per_session():
    owner = (APP / "java/org/claritylink/android/Type110LabProbeOwnership.java").read_text()
    issue_body = owner[owner.index("static synchronized boolean issue("):owner.index("/** Atomically claims")]
    has_pending_body = owner[owner.index("static synchronized boolean hasPending("):owner.index("static synchronized boolean issue(")]
    consume_body = owner[owner.index("static synchronized Record consume("):owner.index("private static Record read(")]
    test_activity = (APP / "java/org/claritylink/android/Type110OwnerIsolationTestActivity.java").read_text()
    manifest = ET.parse(APP / "AndroidManifest.lab.xml").getroot()
    app = manifest.find("application")
    activity = next(item for item in app.findall("activity")
                    if item.get(ANDROID + "name") == "org.claritylink.android.Type110OwnerIsolationTestActivity")
    assert activity.get(ANDROID + "exported") == "true"
    assert activity.get(ANDROID + "permission") == "android.permission.DUMP"
    assert activity.get(ANDROID + "process") == ":owner_test"
    assert "Long.toHexString(sessionId)" in owner
    assert "sessionFile(directory, identity.sessionId, RECORD_SUFFIX)" in issue_body
    assert "sessionFile(directory, expectedDeath.sessionId, RECORD_SUFFIX)" in has_pending_body
    assert "sessionFile(directory, expectedDeath.sessionId, RECORD_SUFFIX)" in consume_body
    assert "MAX_PENDING_OWNERS = 32" in owner
    assert "CountDownLatch" in test_activity
    assert "TYPE110_OWNER_SESSION_ISOLATION_PASS" in test_activity
    assert "reverse_consume=true records_remaining=0" in test_activity
    assert "TYPE110_OWNER_CAP_RECOVERY_PASS" in test_activity
    assert "pending_cap=32 cap_rejected=true" in test_activity
    assert "expired_records_pruned=32 orphan_temp_pruned=true orphan_claim_pruned=true" in test_activity
    assert "new_session_issued=true artifacts_remaining=0" in test_activity


def test_api17_runner_proves_cross_uid_denial_and_uses_privileged_shell_launch():
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    attacker = (REPO / "android/cl-r4-boundary-attacker/java/org/claritylink/attacker/ExportBoundaryAttackActivity.java").read_text()
    assert "assert_type110_probe_cross_uid_denied" in runner
    assert "CL_R4_CROSS_UID_ATTACKS_PASS" in runner
    assert "attempts=23 denied=23" in runner
    assert "attacker_uid" in runner
    assert "invoke_type110_probe_privileged" in runner
    assert 'shell am start -n "$attacker_package/$attacker_component"' in runner
    assert "shell am instrument" not in runner
    assert "Process.myUid() == appUid" in attacker
    assert "Type110ProgressProbeService" in attacker
    assert "stopService(target)" in attacker
    assert "startService(target)" in attacker
    assert "TYPE110_OWNER_SESSION_ISOLATION_RUNTIME_PASS" in runner
    assert "TYPE110_OWNER_CAP_RECOVERY_RUNTIME_PASS" in runner
    assert "Type110OwnerIsolationTestActivity" in runner
    assert 'attemptLabActivity("Type110OwnerIsolationTestActivity")' in attacker


def test_lab_activities_require_dump_permission_and_attacker_cannot_admit_or_crash_them():
    manifest = ET.parse(APP / "AndroidManifest.lab.xml").getroot()
    app = manifest.find("application")
    activities = {item.get(ANDROID + "name"): item for item in app.findall("activity")}
    for name in ("org.claritylink.android.ClarityLinkDisplayActivity",
                 "org.claritylink.android.Api17DecoderLabActivity",
                 "org.claritylink.android.Type110OwnerIsolationTestActivity"):
        assert activities[name].get(ANDROID + "exported") == "true"
        assert activities[name].get(ANDROID + "permission") == "android.permission.DUMP"
    attacker = (REPO / "android/cl-r4-boundary-attacker/java/org/claritylink/attacker/ExportBoundaryAttackActivity.java").read_text()
    for name in ("ClarityLinkDisplayActivity", "Api17DecoderLabActivity"):
        assert f'attemptLabActivity("{name}")' in attacker
    assert '"crash_after_first_frame", true' in attacker
    assert 'attemptPrivateService("Type111ProducerService")' in attacker
    assert 'attemptPrivateService("Type110SinkFailureTestService")' in attacker
    assert 'attemptPrivateService("CompositorOwnerDeathTestService")' in attacker
    assert 'target.putExtra("confirmation", "CL_R4B_OFFLINE_EMULATOR_ONLY")' in attacker
    assert "attempted == 23 && denied == attempted" in attacker


def test_api17_runner_uses_internal_probe_and_gracefully_stops_owned_services():
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    probe = (APP / "java/org/claritylink/android/Type110ProgressProbeService.java").read_text()
    assert "TYPE110_POST_DEATH_PROBE_INTERNAL_START" in runner
    assert "TYPE110_RECOVERY_PRODUCER_PROCESS_PASS" in runner
    assert "TYPE110_POST_DEATH_PROBE_INTERNAL_START session_id=" in (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    assert "shell am instrument" not in runner
    assert "TYPE110_PROBE_UNOWNED_SESSION_REJECTED" not in runner
    assert "probe_session_id \"$live_session\"" not in runner
    assert "TYPE111_PARENT_TEARDOWN session_id=$live_session" not in runner
    assert "CL_R4_OWNED_SERVICES_STOP_REQUESTED" in probe
    assert "TYPE110_PROBE_OWNER_RECORD_ISSUED" in (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    assert 'stopService(new Intent(this, FrameLabSinkService.class))' in probe
    assert 'stopService(new Intent(this, CompositorService.class))' in probe
    cleanup = runner[runner.index("complete_probe_session_and_stop_isolated_package()"):
                    runner.index("adb_local -s \"$serial\" logcat -c", runner.index("complete_probe_session_and_stop_isolated_package()"))]
    assert "TYPE110_LAB_SINK_DESTROYED" in cleanup
    assert "IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true active_pfd_transfers=0 retained_frame_bytes=0" in cleanup
    assert 'shell am force-stop "$package"' not in cleanup


def test_cross_uid_attacker_has_distinct_uid_and_requests_no_permissions():
    manifest = ET.parse(REPO / "android/cl-r4-boundary-attacker/AndroidManifest.xml").getroot()
    app = manifest.find("application")
    activity = app.find("activity")
    assert activity.get(ANDROID + "exported") == "true"
    assert manifest.findall("uses-permission") == []
    source = (REPO / "android/cl-r4-boundary-attacker/java/org/claritylink/attacker/ExportBoundaryAttackActivity.java").read_text()
    assert 'attemptPrivateService("Type111ProducerService")' in source
    assert "attempted == 23 && denied == attempted" in source
    assert "ATTACK_NOT_DENIED" in source
    assert 'attemptLabActivity("ClarityLinkDisplayActivity")' in source
    assert 'attemptLabActivity("Api17DecoderLabActivity")' in source
    assert 'attemptLabActivity("Type110OwnerIsolationTestActivity")' in source
    assert '"crash_after_first_frame", true' in source

def test_type111_decoder_fault_hook_is_lab_gated_and_recovers_with_new_codec():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert "if (!type111FixtureMode || !isEmulator())" in activity
    assert "lab_injected_type111_decoder_failure" in activity
    assert "decoder.close();\n                    decoder = null;" in activity
    assert "new Api17BufferH264Decoder(32, 32, 960002L, blueConfig)" in activity
    assert "CL_R4_TYPE111_DECODER_FAULT_RECOVERY_PASS" in activity
    assert "wait_for 'CL_R4_TYPE111_DECODER_FAULT_RECOVERY_PASS'" in runner


def test_parent_teardown_closes_registration_admission_before_child_snapshot():
    source = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    teardown = source[source.index("private String teardownType111Session"):
                      source.index("private static void writeControlReply")]
    register = source[source.index("private boolean registerStream"):
                      source.index("private void pauseAtLabTransferBarrier")]
    setup = source[source.index("if (code == FrameIpcProtocol.TYPE111_SETUP)"):
                   source.index("if (code == FrameIpcProtocol.TYPE111_NAVIGATION)")]
    capability = source[source.index("private void handleType111Capability"):
                        source.index("private String teardownType111Session")]
    register_body = source[source.index("private boolean registerStream"):
                           source.index("private void pauseAtLabTransferBarrier")]
    unregister_body = source[source.index("private boolean unregisterStream(FrameStreamIdentity"):
                             source.index("private static FrameStreamIdentity readIdentity")]
    assert teardown.index("closingSessions.add(sessionId)") < teardown.index(
        "for (StreamState state : streams.values())")
    assert "closingSessions.contains(identity.sessionId)" in register
    assert register_body.index("sink.linkToDeath(state.deathRecipient, 0)") < register_body.index(
        "streams.put(identity.key(), state)")
    assert "sink.unlinkToDeath(state.deathRecipient, 0)" in register_body
    assert "closing = closingSessions.contains(identity.sessionId)" in setup
    assert "closingSessions.contains(sessionId)" in capability
    assert "MAX_CLOSED_SESSION_IDS" not in source
    assert "MAX_RECENT_SESSION_IDS = 256" in source
    assert "legacySessionIds.contains(sessionId)" in source
    assert "ArrayList<Long> unsequenced" in source
    assert "persistSessionWindowLocked(preferences, nextOrder, nextIds)" in source
    assert "if (!activeSessionIds.contains(nextOrder.get(i)))" in source
    assert "closingSessions.remove(sessionId)" in teardown
    assert "endStreamIfCurrent(state, deadIdentity)" in source
    assert "streams.get(identity.key()) != state" in unregister_body
    assert "!identity.equals(state.identity)" in unregister_body


def test_stale_stream_end_cannot_tear_down_newer_type111_generation():
    compositor = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    control = (APP / "java/org/claritylink/android/Type111ControlPlane.java").read_text()
    client = (APP / "java/org/claritylink/android/FrameIpcClient.java").read_text()
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    unregister = compositor[compositor.index("private boolean unregisterStreamState"):
                            compositor.index("private static FrameStreamIdentity readIdentity")]
    teardown = control[control.index("synchronized String teardown("):
                       control.index("synchronized Snapshot snapshot()")]
    # sameStream ignores generation; END and control-plane teardown require the full generation.
    assert "!identity.equals(state.identity)" in unregister
    assert "!identity.equals(requestIdentity)" in teardown
    assert "!identity.sameStream(state.identity)" not in unregister
    assert "!identity.sameStream(requestIdentity)" not in teardown
    assert "boolean probeEndIdentity(FrameStreamIdentity requestedIdentity)" in client
    assert "liveClient.probeEndIdentity(previousIdentity)" in activity
    assert 'stale_end_rejected=true " +' in activity
    assert '"current generation draws after stale Binder END"' in activity


def test_display_probe_entrypoints_are_private_and_emulator_gated():
    import xml.etree.ElementTree as ET

    p2c2 = ET.parse(REPO / "android/p2c2-probe/AndroidManifest.xml").getroot()
    p2c2_activity = p2c2.find("application/activity")
    assert p2c2_activity is not None
    assert p2c2_activity.get(ANDROID + "exported") == "false"
    p2c2_instrumentation = p2c2.find("instrumentation")
    assert p2c2_instrumentation.get(ANDROID + "name") == "android.test.InstrumentationTestRunner"
    instrumentation = (REPO / "android/p2c2-probe/test/org/claritylink/android/"
                       "P2C2ProbeLaunchTest.java").read_text()
    assert "getInstrumentation().startActivitySync(intent)" in instrumentation
    p2c2_source = (REPO / "android/p2c2-probe/java/org/claritylink/android/"
                   "P2C2AdmissionProbeActivity.java").read_text()
    p2c2_api_guard = p2c2_source.index("if (android.os.Build.VERSION.SDK_INT != 17)")
    p2c2_guard = p2c2_source.index("if (!isIsolatedEmulator())")
    assert p2c2_api_guard < p2c2_guard
    assert p2c2_api_guard < p2c2_source.index("new HondaStyleDisplayHostSimulator(this)")
    assert p2c2_api_guard < p2c2_source.index("getSystemService(Context.DISPLAY_SERVICE)")
    assert p2c2_guard < p2c2_source.index("new HondaStyleDisplayHostSimulator(this)")
    assert p2c2_guard < p2c2_source.index("getSystemService(Context.DISPLAY_SERVICE)")
    assert p2c2_guard < p2c2_source.index("verifyClarityContentView(0)")
    assert "manager.registerDisplayListener(displayListener, main)" in p2c2_source
    assert "displayManager.unregisterDisplayListener(displayListener)" in p2c2_source
    assert 'event("DISPLAY_REMOVED_PASS created=' in p2c2_source
    assert 'event("DISPLAY_LISTENER_REGISTERED id="' in p2c2_source
    assert 'event("DISPLAY_REMOVAL_POLL_CONFIRMED id="' in p2c2_source

    window = ET.parse(REPO / "android/test4-window-probe/AndroidManifest.xml").getroot()
    window_activity = window.find("application/activity")
    assert window_activity is not None
    assert window_activity.get(ANDROID + "exported") == "false"
    assert not window_activity.findall("intent-filter")
    assert window.find("instrumentation").get(ANDROID + "name") == \
        "org.claritylink.android.Test4ProbeInstrumentationRunner"
    test4_launch = (REPO / "android/test4-window-probe/test/org/claritylink/android/"
                    "Test4ProbeLaunchTest.java").read_text()
    assert "getInstrumentation().startActivitySync(intent)" in test4_launch
    window_source = (REPO / "android/test4-window-probe/java/org/claritylink/android/"
                    "Test4WindowAdmissionActivity.java").read_text()
    window_api_guard = window_source.index("if (Build.VERSION.SDK_INT != 17)")
    window_guard = window_source.index("if (!isIsolatedEmulator())")
    assert window_api_guard < window_guard
    assert window_api_guard < window_source.index("getSystemService(Context.DISPLAY_SERVICE)")
    assert window_api_guard < window_source.index("new ProbePresentation")
    assert window_guard < window_source.index("getSystemService(Context.DISPLAY_SERVICE)")
    assert window_guard < window_source.index("createDisplayContext(target)")
    assert window_guard < window_source.index("new ProbePresentation")


def test_candidate_compositor_remains_disabled_and_unexported():
    manifest = ET.parse(APP / "AndroidManifest.candidate.xml").getroot()
    app = manifest.find("application")
    service = app.find("service")
    assert app.get(ANDROID + "enabled") == "false"
    assert service.get(ANDROID + "enabled") == "false"
    assert service.get(ANDROID + "exported") == "false"


def test_frame_payload_uses_bounded_pipe_not_binder_byte_array():
    client = (APP / "java/org/claritylink/android/FrameIpcClient.java").read_text()
    service = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    protocol = (APP / "java/org/claritylink/android/FrameIpcProtocol.java").read_text()
    assert "ParcelFileDescriptor.createPipe()" in client
    assert "writeParcelable(pipe[0], 0)" in client
    assert "frame.writeRgbaTo(output)" in client
    assert "MAX_FRAME_BYTES = 4 * 1024 * 1024" in protocol
    assert "expectedBytes > FrameIpcProtocol.MAX_FRAME_BYTES" in service
    assert "Binder.getCallingUid() != Process.myUid()" in service
    production_submit = client[client.index("boolean submit("):client.index("void end(")]
    assert "writeByteArray" not in production_submit
    assert "ParcelFileDescriptor.createPipe()" in production_submit


def test_single_flight_generation_cleanup_and_canvas_boundary_are_preserved():
    client = (APP / "java/org/claritylink/android/FrameIpcClient.java").read_text()
    service = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    protocol = (APP / "java/org/claritylink/android/FrameIpcProtocol.java").read_text()
    model = (REPO / "src/claritylink-renderer/android-api17/SimulatedExternalDisplayCompositor.java").read_text()
    app = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert "frameGate.tryAcquire()" in client
    assert "frameGate.close()" in client
    assert "timestampNs <= lastTimestampNs" in model
    assert "generation != activeGeneration" in model
    assert "setWarningVisible" in model
    assert "FrameIpcProtocol.WARNING" in service
    assert "static final int WARNING" in protocol
    assert "boolean setWarningVisible(long generation, boolean visible)" in client
    assert "client.end(activeGeneration)" in app
    assert "IPC_SESSION_STARTED" in runner
    assert "IPC_SYNTHETIC_FRAME_ACCEPTED" in runner
    assert "remote_pid" in runner
    assert "SYNTHETIC_FRAME_DRAWN_ON_PRESENTATION_CANVAS" in runner


def test_pipe_streams_own_their_descriptors_exactly_once():
    client = (APP / "java/org/claritylink/android/FrameIpcClient.java").read_text()
    service = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    assert "new ParcelFileDescriptor.AutoCloseOutputStream(writeEnd)" in client
    assert "new ParcelFileDescriptor.AutoCloseInputStream(descriptor)" in service
    assert "new FileOutputStream(writeEnd.getFileDescriptor())" not in client
    assert "new FileInputStream(descriptor.getFileDescriptor())" not in service


def test_v3_binder_contract_preserves_stream_identity_and_per_stream_ownership():
    identity = (APP / "java/org/claritylink/android/FrameStreamIdentity.java").read_text()
    protocol = (APP / "java/org/claritylink/android/FrameIpcProtocol.java").read_text()
    client = (APP / "java/org/claritylink/android/FrameIpcClient.java").read_text()
    service = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    sink = (APP / "java/org/claritylink/android/FrameViewSink.java").read_text()
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    lab_sink = (APP / "java/org/claritylink/android/FrameLabSink.java").read_text()

    assert "static final int VERSION = 3" in protocol
    assert "Version 2 is intentionally rejected" in protocol
    for field in ("sessionId", "streamType", "connectionId", "streamGeneration", "outputId"):
        assert field in identity
        assert field in client and field in service
    assert "streamType == TYPE110 && outputId == OUTPUT_PRIMARY_LAB" in identity
    assert "streamType == TYPE111 && outputId == OUTPUT_SECONDARY_VIEW" in identity
    assert "Map<String, StreamState> streams" in service
    assert "final Object lock = new Object()" in service
    assert "final AtomicBoolean transferActive" in service
    assert "synchronized boolean onTransact" not in service
    assert "forwardToViewSink(state, identity" in service
    assert "state.retainedFrameBytes" in service
    assert "MAX_QUEUED_FRAME_BYTES" in sink
    assert "writeIdentity(data, currentIdentity)" in client
    assert "FrameLabSinkService.class" in activity
    assert "FrameLabSink.queryStats(primaryLabSinkBinder)" in activity
    assert "primaryClient.begin(primaryIdentity, primaryLabSinkBinder)" in activity
    assert "primary_lab_recorded" in lab_sink
