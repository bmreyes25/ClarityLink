from pathlib import Path
import xml.etree.ElementTree as ET


REPO = Path(__file__).resolve().parents[2]
APP = REPO / "android/cl-imp-03-app"
ANDROID = "{http://schemas.android.com/apk/res/android}"


def test_type110_owner_end_and_sink_death_close_the_parent_session():
    service = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    end_branch = service[service.index("if (code == FrameIpcProtocol.END)"):
                         service.index("if (code == FrameIpcProtocol.TYPE111_REPLACE_SINK)")]
    death_callback = service[service.index("private IBinder.DeathRecipient createSinkDeathRecipient"):
                             service.index("/** Preserve the Type111 stream/control identity")]
    helpers = service[service.index("private boolean endStream(FrameStreamIdentity identity)"):
                      service.index("private boolean unregisterStreamIfCurrent")]
    assert "boolean accepted = endStream(identity);" in end_branch
    assert "endStreamIfCurrent(state, deadIdentity)" in death_callback
    assert "teardownType111Session(identity)" in helpers
    assert "teardownType111Session(identity, true)" in helpers
    assert "TYPE110_OWNER_SESSION_INVALIDATED" in helpers
    assert "return unregisterStream(identity);" in helpers
    assert "return unregisterStreamIfCurrent(state, identity);" in helpers
    assert "IPC_TYPE110_PARENT_DEATH_LINKED" in service
    assert "IPC_TYPE110_PARENT_DEATH_CALLBACK_ENTERED" in service
    assert "IPC_STREAM_SINK_DEATH_LINKED" in service
    assert "IPC_STREAM_SINK_DEATH_CALLBACK_ENTERED" in death_callback


def test_type110_sink_rejects_live_reuse_and_replaces_only_after_owner_revocation():
    service = (APP / "java/org/claritylink/android/FrameLabSinkService.java").read_text()
    ensure = service[service.index("private synchronized boolean ensureSink"):
                    service.index("@Override public void onDestroy()")]
    assert "if (sessionId > 0L && requestedSession == sessionId) return true;" in ensure
    assert "if (requestedSession <= 0L || previous != null) return false;" in ensure
    assert "TYPE110_LAB_SINK_REPLACED_AFTER_OWNER_LOSS" in ensure


def test_type110_only_api17_failure_harness_is_guarded_and_checks_cleanup():
    manifest = ET.parse(APP / "AndroidManifest.lab.xml").getroot()
    service = next(item for item in manifest.find("application").findall("service")
                   if item.get(ANDROID + "name") ==
                   "org.claritylink.android.Type110SinkFailureTestService")
    assert service.get(ANDROID + "process") == ":type110_failure"
    assert service.get(ANDROID + "exported") == "true"
    assert service.get(ANDROID + "permission") == "android.permission.DUMP"

    injector = (APP / "java/org/claritylink/android/Type110SinkFailureTestService.java").read_text()
    assert "CL_R4B_OFFLINE_EMULATOR_ONLY" in injector
    assert "isOwnedSinkProcess(targetPid)" in injector
    assert "Process.killProcess(targetPid)" in injector
    assert "process.uid" in injector
    assert 'getLongExtra("target_session_id", 0L)' in injector
    assert "if (!isOwnedSinkProcess(targetPid))" in injector

    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert "--cl-r4b-type110-failure" in runner
    assert "shell am startservice" in runner
    assert "CL_R4B_TYPE110_SINK_FAILURE_TARGET_VERIFIED" in runner
    assert 'api17-type110-sink-death-process-$adb_port.txt' in runner
    assert 'api17-type110-sink-death-logcat-$adb_port.txt' in runner
    assert 'api17-type110-sink-death-services-$adb_port.txt' in runner
    assert 'did not exit after the guarded kill request.' in runner
    assert 'TYPE110_SINK_PID_EXIT_OBSERVED pid=$sink_pid' in runner
    assert 'seq 1 30' in runner
    assert 'api17-type110-sink-death-logcat-$adb_port.txt' in runner
    assert 'api17-type110-sink-death-services-$adb_port.txt' in runner
    assert "assert_type110_probe_cross_uid_denied" in runner
    assert "ATTACK_DENIED operation=service component=Type110SinkFailureTestService" in runner
    assert "ATTACK_DENIED operation=bind_service component=Type110SinkFailureTestService" in runner
    assert "target_session_id \"$session_id\"" in runner
    assert "TYPE111_PARENT_TEARDOWN session_id=$session_id streams_closed=2 result=accepted" in runner
    assert "cause=owner_sink_death streams_closed=2" in runner
    assert "IPC_STREAM_UNREGISTERED session_id=$session_id stream_type=111" in runner
    assert "active_pfd_transfers=0 retained_frame_bytes=0" in runner
    assert "CL_R4B_TYPE110_ONLY_FAILURE_PASS" in runner
    assert "wait_for 'TYPE111_SECURITY_TEST_PRODUCER_BOUND '" in runner
    assert 'IPC_TYPE110_PARENT_DEATH_CALLBACK_ENTERED session_id=$session_id ' in runner
    assert 'death_recipient_id=$owner_death_recipient_id' in runner
    assert 'TYPE110_PARENT_AUTHORITY_REVOKED session_id=$session_id ' in runner


def test_type110_failure_launches_live_type111_producer_and_preserves_api17_receipts():
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    mode = runner[runner.index('--cl-r4b-type110-failure'):
                  runner.index('elif [ "${1:-}" = "--cl-r4b-parent-owner-death"')]
    assert "type110_failure=1" in mode and "type111_mode=1" in mode
    assert "256 KiB log buffers can be overwritten by EGL frame-render chatter" in runner
    assert 'runtime_logs_file="$campaign_evidence/api17-runtime-logcat-$adb_port.txt"' in runner
    assert 'adb_local -s "$serial" logcat -s ClarityLinkCLIMP03:I' in runner
    assert 'cat "$runtime_logs_file"' in runner
    assert '[ "${6:-}" = "ClarityLinkCLIMP03:I" ]' in runner
    assert '[ "${7:-}" = "*:S" ]' in runner
    assert "--cl-r4b-type110-failure-type111-first" in runner
    assert "start_lab_activity_privileged type111_first_type110_failure" in runner


def test_type111_producer_thread_start_failure_rolls_back_wait_state():
    producer = (APP / "java/org/claritylink/android/Type111ProducerService.java").read_text()
    start = producer.index("try {\n            new Thread")
    startup = producer[start:producer.index("return true;", start)]
    assert "catch (RuntimeException startupFailure)" in startup
    assert "catch (Error startupFailure)" in startup
    assert startup.count("rollbackProducerStart();") == 2
    rollback_start = producer.index("private synchronized void rollbackProducerStart")
    rollback = producer[rollback_start:producer.index("private void decodeAndSubmit", rollback_start)]
    assert "running = false;" in rollback
    assert "completed = true;" in rollback
    assert "runFinished.countDown();" in rollback


def test_parent_owner_death_harness_kills_only_verified_compositor_and_checks_restart():
    manifest = ET.parse(APP / "AndroidManifest.lab.xml").getroot()
    activity = next(item for item in manifest.find("application").findall("service")
                    if item.get(ANDROID + "name") ==
                    "org.claritylink.android.CompositorOwnerDeathTestService")
    assert activity.get(ANDROID + "process") == ":owner_death_test"
    assert activity.get(ANDROID + "exported") == "true"
    assert activity.get(ANDROID + "permission") == "android.permission.DUMP"

    source = (APP / "java/org/claritylink/android/CompositorOwnerDeathTestService.java").read_text()
    assert 'expected.equals(process.processName)' in source
    assert 'bindOwnerObserver("observer_bind_failed")' in source
    assert 'bindOwnerObserver("observer_rebind_failed_after_owner_death")' in source
    assert "observerRebindStarted = true" in source
    assert "unbindService(deadConnection)" in source
    assert "private final Object lifecycleLock" in source
    assert "connection != this || endpointDisconnected ||" in source
    assert "endpointVerificationStarted = true" in source
    assert "ownerDeathObserved = true" in source
    assert "if (!ownerDeathObserved ||" in source
    assert "synchronized (lifecycleLock)" in source
    assert "process.uid == Process.myUid()" in source
    assert "Process.killProcess(targetPid);" in source
    assert "service.isBinderAlive() || !isExactOwnedCompositorPid(targetPid)" in source
    assert "query.compositorPid == targetPid" in source
    assert "!query.ownerValid" in source and "query.identity != null" in source
    assert "requireOldFrameRejected(service, ownerIdentity" in source
    assert "requireOldFrameRejected(service, childIdentity" in source
    assert '"stream_identity_rejected".equals(reason[0])' in source
    assert "activePfdTransfers == 0" in source
    assert "retainedFrameBytes == 0" in source
    assert "Build.VERSION.SDK_INT != 17 || !isEmulator()" in source
    assert "private static boolean isEmulator()" in source

    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert "--cl-r4b-parent-owner-death" in runner
    assert 'CL_R4B_OWNER_SESSION_READY ' in runner
    assert 'CL_R4B_PARENT_OWNER_DEATH_REQUESTED pid=$owner_pid ' in runner
    assert 'CL_R4B_OWNER_DEATH_BINDER_DISCONNECTED old_pid=$owner_pid ' in runner
    assert "'$2==pid {found=1} END {exit !found}'" in runner
    assert "old_pid_absent=true owner_valid=false child_present=false" in runner
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    assert "CL_R4B_ACTIVITY_OWNER_INVALIDATED " in runner
    assert "CL_R4B_ACTIVITY_OWNER_CLEANUP_PASS " in runner
    assert '"CL_R4B_ACTIVITY_OWNER_INVALIDATED old_pid="' in activity
    assert "binder.linkToDeath(compositorDeathRecipient, 0)" in activity
    assert "parent_teardown_request_skipped=true stale_stream_end_skipped=true" in activity
    assert "owner-death-window-state-$adb_port.txt" in runner
    assert "api17-compositor-owner-death-window-before-$adb_port.txt" in runner
    assert "App-owned secondary Presentation window remained" in runner
    assert "END {if (matched && on_secondary) found=1; exit !found}" in runner
    assert "PRESENTATION_CLOSE_FAILED" in runner

    attacker = (REPO / "android/cl-r4-boundary-attacker/java/org/claritylink/attacker/ExportBoundaryAttackActivity.java").read_text()
    assert 'attemptPrivateService("CompositorOwnerDeathTestService")' in attacker
    assert 'if (attempted == 23 && denied + unverifiedNoEffect == attempted && notDenied == 0)' in attacker
    assert '"CompositorOwnerDeathTestService".equals(simpleName)' in attacker

    build = (REPO / "tools/build_cl_imp_03_apks.sh").read_text()
    assert "CompositorOwnerDeathTestService.java" in build


def test_compositor_owner_restart_rejects_persisted_session_and_registers_fresh_session():
    compositor = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    observer = (APP / "java/org/claritylink/android/CompositorOwnerDeathTestService.java").read_text()
    assert "SESSION_ID_PREFS" in compositor and "SESSION_ID_SET" in compositor
    assert "preferences.getStringSet(SESSION_ID_SET" in compositor
    assert "preferences.getStringSet(LEGACY_SESSION_ID_SET" in compositor
    assert "legacySessionIds.contains(sessionId)" in compositor
    assert "ArrayList<Long> unsequenced" in compositor
    assert "sessionWindowReady = false" in compositor
    assert "legacySessionIds.add(sessionId)" in compositor
    assert 'LEGACY_SESSION_ID_SET = "session_ids"' in compositor
    assert 'SESSION_ID_SET = "session_ids_v2"' in compositor
    assert "MAX_RECENT_SESSION_IDS = 256" in compositor
    assert "preferences.edit().putStringSet(SESSION_ID_SET, encoded)" in compositor
    assert "putString(SESSION_ID_ORDER, ordered.toString())" in compositor
    assert "nextOrder.remove(evict)" in compositor
    assert "reserveSessionIdLocked(ownerIdentity.sessionId)" in compositor
    assert "ParentAuthority authority = parentAuthorities.get(sessionId)" in compositor
    assert "authority.ownerSink.isBinderAlive()" in compositor
    assert "FrameLabSink.bindCompositorEpoch(ownerSink, ownerIdentity, endpoint)" in compositor
    assert "MAX_ACTIVE_PARENT_SESSIONS = 8" in compositor
    assert "PROVISIONAL_PARENT_AUTHORITY_TIMEOUT_MS = 30000L" in compositor
    assert "provisional_authority_timeout" in compositor
    assert "authority.provisional = false" in compositor
    assert "verifyFreshSessionRecovery(service, query.compositorPid)" in observer
    assert "old_type110_identity_re_registered_after_owner_restart" in observer
    assert "old_session_capability_re_registered_after_owner_restart" in observer
    assert "fresh_type110_session_registration_failed" in observer
    assert "fresh_type111_stream_registration_failed" in observer
    assert "fresh_session_parent_teardown_failed" in observer
    assert "registrations_after_teardown=0" in observer
    assert "verifySessionAdmissionBeyondPreviousTombstoneLimit(service, control, compositorPid)" in observer
    assert "for (int i = 0; i < 257; i++)" in observer
    assert "active_session_evicted_from_replay_window" in observer
    assert "CL_R4B_OWNER_DEATH_SESSION_CAPACITY_PASS admitted_and_torn_down=257" in observer
    assert "same_process_session_id_reused_after_end_at=" in observer
    assert "MAX_CLOSED_SESSION_IDS" not in compositor
    assert "activeSessionIds.contains(sessionId)" in compositor
    assert "!activeSessionIds.contains(nextOrder.get(i))" in compositor
    assert "activeSessionIds.remove(identity.sessionId)" in compositor
    assert "SESSION_REPLAY_BLOOM_BYTES = 32768" in compositor
    assert "mightContainSessionReplay(sessionReplayBloom, sessionId)" in compositor
    assert "sessionReplayBloom = nextBloom" in compositor
    assert "old_owner_session_replayed_after_256_id_window_eviction" in observer
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert 'CL_R4B_OWNER_DEATH_FRESH_SESSION_RECOVERY_PASS ' in runner
    assert 'Type110 sink or Type111 producer service remained registered after owner loss.' in runner
    assert "api17-compositor-owner-death-processes-$adb_port.txt" in runner
    assert "api17-compositor-owner-death-services-$adb_port.txt" in runner


def test_type111_capability_requires_explicit_live_type110_authority_without_stream_ordering():
    compositor = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    client = (APP / "java/org/claritylink/android/FrameIpcClient.java").read_text()
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    protocol = (APP / "java/org/claritylink/android/FrameIpcProtocol.java").read_text()
    assert "PARENT_OPEN_AUTHORITY = 35" in protocol
    assert "ownerIdentity.sessionId == sessionId" in compositor
    assert 'reason = "parent_authority_required"' in compositor
    assert "authority.ownerIdentity.equals(ownerIdentity)" in compositor
    assert "authority.ownerPid == Binder.getCallingPid()" in compositor
    assert "isAuthorizedParentCaller(Binder.getCallingPid())" in compositor
    assert 'getPackageName() + ":type111_view"' in compositor
    assert "reserveSessionIdLocked(ownerIdentity.sessionId)" in compositor
    assert "static boolean openParentAuthority" in client
    assert "if (streamIdentity.streamType == FrameStreamIdentity.TYPE110" in client
    open_index = activity.index("FrameIpcClient.openParentAuthority(compositorEndpoint, primaryIdentity")
    capability_index = activity.index("boolean capability = control.registerLabCapability(primaryIdentity")
    type111_first_index = activity.index("if (type111FirstMode)")
    assert open_index < capability_index < type111_first_index


def test_parent_identity_is_revoked_on_session_end_and_compositor_process_death():
    sink = (APP / "java/org/claritylink/android/FrameLabSink.java").read_text()
    compositor = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    assert "FRAME_LAB_BIND_COMPOSITOR_EPOCH" in sink
    assert "compositor.linkToDeath(recipient, 0)" in sink
    assert "cause=compositor_process_death" in sink
    assert "clearIdentityAndCompositorEpoch();" in sink
    assert "FrameLabSink.revokeParentAuthority(authority.ownerSink, authority.ownerIdentity)" in compositor
    assert "cause=owner_end" in compositor
    assert "MAX_RECENT_SESSION_IDS = 256" in compositor
    sink = (APP / "java/org/claritylink/android/FrameLabSink.java").read_text()
    assert "isCompositorProcessCaller()" in sink
    assert 'context.getPackageName() + ":compositor"' in sink


def test_api17_same_uid_sibling_attack_compares_authorized_state_before_and_after():
    source = (APP / "java/org/claritylink/android/SameUidRegistrationAttackTestService.java").read_text()
    manifest = ET.parse(APP / "AndroidManifest.lab.xml").getroot()
    service = next(item for item in manifest.find("application").findall("service")
                   if item.get(ANDROID + "name") ==
                   "org.claritylink.android.SameUidRegistrationAttackTestService")
    assert service.get(ANDROID + "process") == ":registration_attacker"
    assert service.get(ANDROID + "exported") == "false"
    assert '"authorized_before_state_missing"' in source
    assert "boolean authority = FrameIpcClient.openParentAuthority" in source
    assert "boolean capability = control.registerLabCapability" in source
    assert "boolean teardown = control.parentTeardown" in source
    assert "boolean end = rawEnd(owner)" in source
    assert "boolean producerStart = rawProducerStart" in source
    assert "boolean producerStop = rawProducerStop()" in source
    assert "producer_pid_before=" in source and "producer_pid_after=" in source
    assert "test_barrier_arm_wait_release_rejected=true" in source
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    assert "awaitCrossUidRunnerRelease" in activity
    assert "SystemClock.elapsedRealtime() + 120000L" in activity
    assert "hold_after_same_uid_attack" in activity
    assert '"hold_after_attack"' in source
    assert "awaitCrossUidRunnerRelease(owner.sessionId)" in source
    assert '"frame_caller_not_authorized".equals(frameReason[0])' in source
    assert "same_uid_attack_mutated_authorized_state" in source
    assert "CL_R4B_SAME_UID_REGISTRATION_ATTACK_PASS" in source
    compositor = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    barrier_blocks = {}
    for handler in ("LAB_ARM_TRANSFER_BARRIER", "LAB_WAIT_TRANSFER_BARRIER",
                    "LAB_ARM_PARENT_TEARDOWN_BARRIER", "LAB_WAIT_PARENT_TEARDOWN_BARRIER",
                    "LAB_ARM_DELAYED_SINK_DEATH_CALLBACK", "LAB_FIRE_DELAYED_SINK_DEATH_CALLBACK"):
        block = compositor[compositor.index("if (code == FrameIpcProtocol." + handler):]
        next_handler = block.find("if (code == FrameIpcProtocol.", 1)
        if next_handler >= 0:
            block = block[:next_handler]
        barrier_blocks[handler] = block
        assert "isSessionOwnerCaller" in block
    wait_block = barrier_blocks["LAB_WAIT_TRANSFER_BARRIER"]
    assert "ownerMayDrainDuringShutdown" in wait_block
    assert "code == FrameIpcProtocol.LAB_RELEASE_TRANSFER_BARRIER ||\n                        code == FrameIpcProtocol.LAB_WAIT_TRANSFER_FINISHED" in wait_block
    assert "code == FrameIpcProtocol.LAB_WAIT_TRANSFER_BARRIER" not in wait_block[
        wait_block.index("boolean ownerMayDrainDuringShutdown"):wait_block.index("if (identity == null")]
    assert "ownerMayDrainDuringShutdown" not in barrier_blocks["LAB_ARM_TRANSFER_BARRIER"]
    assert "ownerMayDrainDuringShutdown" not in barrier_blocks["LAB_ARM_TRANSFER_BARRIER"]
    assert "ownerMayDrainDuringShutdown" not in barrier_blocks["LAB_ARM_PARENT_TEARDOWN_BARRIER"]
    assert "ownerMayDrainDuringShutdown" not in barrier_blocks["LAB_ARM_DELAYED_SINK_DEATH_CALLBACK"]
    parent_barrier_block = barrier_blocks["LAB_WAIT_PARENT_TEARDOWN_BARRIER"]
    assert "ownerMayDrainDuringShutdown" in parent_barrier_block
    assert "code == FrameIpcProtocol.LAB_WAIT_PARENT_TEARDOWN_BARRIER ||\n" in parent_barrier_block
    assert "code == FrameIpcProtocol.LAB_WAIT_PARENT_TEARDOWN_CONTENDER ||\n" in parent_barrier_block
    assert "code == FrameIpcProtocol.LAB_RELEASE_PARENT_TEARDOWN_BARRIER" in parent_barrier_block
    assert "isSessionOwnerCaller(ownerIdentity.sessionId,\n                        ownerMayDrainDuringShutdown)" in parent_barrier_block
    assert "releaseParentTeardownBarrierOnOwnerLoss(expected.ownerIdentity.sessionId)" in compositor
    assert "cause=owner_authority_revoked" in compositor
    assert "SameUidRegistrationAttackTestService.java" in (REPO / "tools/build_cl_imp_03_apks.sh").read_text()
    assert "CL_R4B_SAME_UID_REGISTRATION_ATTACK_PASS" in (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()


def test_parent_owner_loss_cancels_activity_fixture_worker():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    start = activity.index("private void stopOwnedDisplay")
    end = activity.index("/** Release only the Activity-owned View attachment", start)
    stop = activity[start:end]
    assert "runToken.cancelForDetach();" in stop
    assert "fixtureWorker.interrupt();" in stop
    assert "closeIpcSession();" in stop
    assert "binder.linkToDeath(compositorDeathRecipient, 0)" in activity
    assert "parentOwnerLossSessionId = observedSessionId" in activity
    assert "CL_R4B_ACTIVITY_OWNER_REATTACH_ABORTED" in activity
    assert "detached_owner_loss=" in activity
    assert "TYPE111_LIFECYCLE_DETACH_SKIPPED reason=parent-owner-lost stale_session_rpc=false" in activity
    close_start = activity.index("private void closeIpcSession()")
    close_end = activity.index("@Override protected void onPause()", close_start)
    close = activity[close_start:close_end]
    assert "if (!ownerLost && control != null && type110Owner != null)" in close
    assert "if (!ownerLost && client != null) client.end(activeGeneration)" in close
    assert "if (!ownerLost && primaryClient != null) primaryClient.end(activeGeneration)" in close


def test_parent_teardown_request_receipt_distinguishes_pending_close_completion():
    compositor = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    assert '"TYPE111_PARENT_TEARDOWN_REQUEST session_id="' in compositor
    assert '"accepted_pending".equals(reason)' in compositor
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert "TYPE111_PARENT_TEARDOWN_REQUEST session_id=$initial_session_generation" in runner
    assert "result=accepted(_pending)?$" in runner


def test_api17_reentrant_teardown_uses_bounded_concurrent_binder_calls_and_verifies_empty_state():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    service = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    client = (APP / "java/org/claritylink/android/Type111ControlClient.java").read_text()
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert "EXTRA_REENTRANT_TEARDOWN_TEST" in activity
    assert "runReentrantParentTeardown(type110Identity, frameIpcClient.streamIdentity())" in activity
    assert "new CountDownLatch(2)" in activity
    assert "start.await(5L, TimeUnit.SECONDS)" in activity
    assert "done.await(8L, TimeUnit.SECONDS)" in activity
    assert "armLabParentTeardownBarrier(owner)" in activity
    assert "awaitLabParentTeardownBarrier(owner, true, 5000L)" in activity
    assert "releaseLabParentTeardownBarrier(owner)" in activity
    assert "results[0] == results[1]" in activity
    assert "repeated_parent_teardown_changed_state" in activity
    assert "reentrant_parent_teardown_left_resources" in activity
    assert "CL_R4B_REENTRANT_PARENT_TEARDOWN_PASS" in activity
    assert "overlap_barrier=first_paused_contender_rejected" in activity
    assert "pauseAtParentTeardownBarrier(sessionId)" in service
    assert "signalParentTeardownContender(sessionId)" in service
    assert "LAB_WAIT_PARENT_TEARDOWN_CONTENDER" in service
    assert "LAB_ARM_PARENT_TEARDOWN_BARRIER" in client
    assert "LAB_RELEASE_PARENT_TEARDOWN_BARRIER" in client
    assert "--cl-r4b-reentrant-teardown" in runner
    assert "--cl-r4b-reentrant-teardown-type111-first" in runner
    assert "accepted_calls=1 rejected_calls=1" in runner
    assert "overlap_barrier=first_paused_contender_rejected" in runner
    assert "Expected one accepted parent teardown request" in runner
    assert "TYPE111_PARENT_TEARDOWN_REQUEST session_id=$initial_session_generation" in runner
    assert "Stream $stream_type unregister count was" in runner
    assert "frameIpcClient.submit(pendingFrame" in activity
    assert "LAB_ARM_TRANSFER_BARRIER" in activity
    assert "pending_teardown_pfd_barrier_not_reached" in activity
    assert "CL_R4B_TEARDOWN_PENDING_PFD_REJECTED" in activity
    assert "session_closing" in service
    assert "replacement_registered_during_parent_shutdown" in activity
    assert "CL_R4B_TEARDOWN_REPLACEMENT_REJECTED" in activity
    assert "killType110SinkForTeardownRace(owner)" in activity
    assert "CL_R4B_TEARDOWN_TYPE110_DEATH_PASS" in activity
    assert "reentrantTeardownInProgress" in activity
    assert "CL_R4B_TYPE110_DEATH_DURING_TEARDOWN_CLEANUP_DEFERRED=true" in activity
    assert "CL_R4B_TEARDOWN_REGISTRATION_REJECTED" in activity
    assert "stream_registration_accepted_during_parent_shutdown" in activity
    assert "Type110 sink process death was not observed during parent teardown" in runner
    assert "actual in-flight PFD entered the transfer barrier" in runner
    assert "Pending PFD transfer was not rejected and released" in runner


def test_api17_delayed_old_sink_callback_is_injected_only_after_fresh_owner_authorized_replacement():
    protocol = (APP / "java/org/claritylink/android/FrameIpcProtocol.java").read_text()
    service = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    client = (APP / "java/org/claritylink/android/Type111ControlClient.java").read_text()
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()

    assert "LAB_ARM_DELAYED_SINK_DEATH_CALLBACK = 33" in protocol
    assert "LAB_FIRE_DELAYED_SINK_DEATH_CALLBACK = 34" in protocol
    assert "Binder.getCallingUid() != Process.myUid()" in service
    assert "armDelayedSinkDeathCallback(identity)" in service
    assert "fireDelayedSinkDeathCallback(ownerIdentity, currentIdentity)" in service
    assert "labDelayedDeathIdentity.streamGeneration + 1L != currentIdentity.streamGeneration" in service
    assert "labDelayedDeathState != child" in service
    assert "labDelayedDeathState != state" in service
    assert "labDelayedDeathRecipient != recipient" in service
    assert "labDelayedDeathRecipient = state.deathRecipient" in service
    assert "if (labDelayedDeathIdentity != null) return false" in service
    assert "pauseLabDelayedDeathCallback(" in service
    assert "release.await(120000L, TimeUnit.MILLISECONDS)" in service
    assert "release.countDown()" in service
    assert "completed.await(10000L, TimeUnit.MILLISECONDS)" in service
    assert "old_callback_completed_after_replacement=true" in activity
    assert "armLabDelayedSinkDeathCallback" in client
    assert "fireLabDelayedSinkDeathCallback(primaryIdentity, replacement)" in activity
    assert "if (existing.sinkAttached && !delayedDeathCallbackTest)" in activity
    assert "replacement_preserved=true" in activity
    assert "wrong_owner_callback_release_rejected" in activity
    assert "duplicate_callback_release_rejected" in activity
    assert "callback_release_after_parent_teardown_rejected" in activity
    assert "CL_R4B_DELAYED_CALLBACK_NEGATIVE_IDENTITY_PASS" in runner
    assert "CL_R4B_DELAYED_CALLBACK_POST_TEARDOWN_PASS" in runner
    assert "--cl-r4b-delayed-callback" in runner
    assert "--cl-r4b-delayed-callback-type111-first" in runner
    assert "IPC_LAB_DELAYED_DEATH_CALLBACK_ENTERED session_id=$initial_session_generation " in runner
    assert "Delayed callback detached the old sink after entering its pre-mutation barrier but before replacement." in runner
    assert 'NR > entered && index($0, "IPC_TYPE111_SINK_DETACHED session_id=" session " ")' in runner
    assert 'api17-delayed-callback-before-replacement-$adb_port.txt' in runner
    assert "entered_before_replacement=true completed_after_replacement=true current_sink_preserved=true" in runner
    assert "replacement_activity_pid" in runner
    assert runner.index('start_lab_activity_privileged type111_delayed_callback_replacement "$initial_session_generation"') < runner.index('window_state=$(adb_local -s "$serial" shell dumpsys window windows')
    delayed_flow = runner[runner.index("wait_for 'CL_R4_TYPE111_SINK_PROCESS_EXIT_REQUESTED'"):runner.index('app_pid=$initial_type111_pid')]
    assert delayed_flow.index('IPC_LAB_DELAYED_DEATH_CALLBACK_ENTERED') < delayed_flow.index('start_lab_activity_privileged type111_delayed_callback_replacement')
    assert delayed_flow.index('start_lab_activity_privileged type111_delayed_callback_replacement') < delayed_flow.index('IPC_LAB_DELAYED_DEATH_CALLBACK_RELEASED')
    assert 'grep -F "pid=$app_pid " | tail -1' in runner
    assert 'grep -F "session_id=$initial_session_generation "' in runner
    assert 'else\n    wait_for \'IPC_VIEW_SINK_DEATH_CALLBACK session_id=\'' in delayed_flow


def test_api17_producer_recovery_rebinds_only_after_real_binder_death():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    recovery = activity[activity.index("private void runIndependentType111ProducerFault"):]
    assert 'awaitRace(death), "producer_binding_death_callback_observed"' in recovery
    assert "unbindService(connection);" in recovery
    assert '"type111_producer_rebind_accepted_after_death"' in recovery
    assert '"producer_rebound_after_process_death"' in recovery
    assert "CL_R4_TYPE111_PRODUCER_REBIND_PASS" in recovery
    assert "bound_service_recreated_after_process_death" not in recovery


def test_api17_producer_wait_retries_only_bounded_unfinished_binder_replies():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    start = activity.index("private long[] awaitIsolatedProducerFrames")
    end = activity.index("private void verifyProducerWaitBounds", start)
    wait = activity[start:end]
    assert "attempt < 3" in wait
    assert "data.writeLong(15000L)" in wait
    assert "if (finished)" in wait
    assert "isolated_producer_did_not_finish_within_bounded_waits" in wait
    assert "Thread.sleep" not in wait


def test_api17_crash_recovery_uses_live_decoded_type111_and_preserves_type110():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    producer_loop = activity[activity.index("for (int index = 0; index < 8 && blueOutputs < 4"):
                              activity.index("requireType111(blueOutputs >= 2")]
    assert "submitDecodedFrame(frame, binderGeneration" in producer_loop
    type110_frame = activity[activity.index('"CL_R4_TYPE110_FIXTURE_FRAME_PASS timing=before_type111_reset'):
                             activity.index('byte[] greenFixture = type111Fixture')]
    assert "requestType111CrashAfterDecodedFrame();" in type110_frame
    crash = activity[activity.index("private void requestType111CrashAfterDecodedFrame()"):
                     activity.index("private void startSameUidRegistrationAttack")]
    assert "primaryLabIpcClient.streamIdentity()" in crash
    assert "frameIpcClient.streamIdentity()" in crash
    assert "!owner.isValid() || !child.isValid()" in crash
    assert "owner.streamType != FrameStreamIdentity.TYPE110" in crash
    assert "child.sessionId != owner.sessionId" in crash
    assert "issueType110ProbeOwnership(owner, stats)" in crash
    assert "decoded_type111_frame_drawn=true" in crash
    assert "CL-IMP-03 emulator-only crash recovery probe" in crash

    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert "--cl-r4b-view-crash" in runner
    assert "type111_crash) set -- \"$@\" --ez type111_fixture_mode true --ez crash_after_first_frame true ;;" in runner
    assert "CL_R4B_TYPE111_CRASH_RECOVERY_API17_PASS" in runner
    assert 'IPC_VIEW_SINK_DEATH_CALLBACK session_id=$crash_session stream_type=111' in runner
    assert "CL_R2_UNCAUGHT_CRASH_REQUESTED pid=\\([0-9][0-9]*\\) session_id=" in runner
    assert 'index($0, "): FATAL EXCEPTION:")' in runner
    assert 'if (line == pid) fatal=1' in runner
    assert 'if (line == pid) exception=1' in runner
    assert 'package=org.claritylink.independentdisplay.lab fatal=FATAL_EXCEPTION' in runner
    assert 'matched-fatal-record.txt' in runner
    assert 'hierarchy-before-dismissal.xml' in runner and 'windows-after-dismissal.txt' in runner
    assert 'processes-after-dismissal.txt' in runner
    assert 'TYPE110_LAB_SINK_FRAME_ACCEPTED pid=$crash_sink_pid' in runner
    assert 'IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true active_pfd_transfers=0 retained_frame_bytes=0' in runner
    crash_flow = runner[runner.index("if [ \"$view_crash\" -eq 1 ]; then"):
                        runner.index("wait_for 'TYPE110_LAB_SINK_START_REJECTED")]
    assert crash_flow.index("probe_boundary_checked=1") < crash_flow.index("invoke_type110_probe_privileged")
