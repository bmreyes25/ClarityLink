from pathlib import Path
import hashlib
import importlib.util
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
    assert "boolean accepted = endStreamWithReceipt(identity, affected);" in end_branch
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
    assert '"$adb" -P "$adb_port" -s "$serial" logcat -s ClarityLinkCLIMP03:I' in runner
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


def test_acceptance_runs_cross_uid_attack_while_owned_services_are_live():
    acceptance = (REPO / "tools/run_cl_r4_acceptance.py").read_text()
    shell = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert '("CL-R4-09", "Cross-UID security", "type110-failure"' in acceptance
    probe = shell[shell.index("invoke_type110_probe_privileged() {"):shell.index("start_lab_activity_privileged() {",
                                                                 shell.index("invoke_type110_probe_privileged() {"))]
    assert "parent teardown before its pass" in probe
    assert "assert_type110_probe_cross_uid_denied \"$1\" \"$2\"" not in probe
    assert "assert_type110_probe_cross_uid_denied \"$session_id\"" in shell


def test_acceptance_checkpoint_hashes_logs_and_rejects_source_drift():
    acceptance = (REPO / "tools/run_cl_r4_acceptance.py").read_text()
    assert '"evidence_log_sha256"' in acceptance
    assert "cached_log_valid" in acceptance
    assert "old_log_valid" in acceptance
    assert "final_source_hash, _final_source_files = fingerprint(repo)" in acceptance
    assert '"source_changed_during_run"' in acceptance
    assert "final_source_hash == source_hash" in acceptance
    assert '"phase": "cl_r7_regression"' in acceptance
    assert "post_r7_source_hash != source_hash" in acceptance
    assert 'return "BLOCKED" if exit_code in (2, 5, 7, 8) else "FAIL"' in acceptance
    assert acceptance.count('cached_mode.get("source_sha256") == source_hash') == 2


def test_acceptance_revalidates_unselected_cached_case_logs(tmp_path):
    path = REPO / "tools/run_cl_r4_acceptance.py"
    spec = importlib.util.spec_from_file_location("cl_r4_acceptance", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    log = tmp_path / "case.log"
    log.write_text("REQUIRED_RECEIPT\n")
    record = {"source_sha256": "source", "apk_sha256": "apk", "log": str(log),
              "evidence_log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()}
    assert module.case_evidence_valid(record, ["REQUIRED_RECEIPT"], "source", "apk")
    log.write_text("tampered\n")
    assert not module.case_evidence_valid(record, ["REQUIRED_RECEIPT"], "source", "apk")
    assert not module.case_evidence_valid(record, ["REQUIRED_RECEIPT"], "other", "apk")


def test_producer_process_death_is_observed_inside_parent_teardown_barrier():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    shell = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    acceptance = (REPO / "tools/run_cl_r4_acceptance.py").read_text()
    test = activity[activity.index("private void runReentrantParentTeardown"):
                    activity.index("private void killType110SinkForTeardownRace")]
    assert "EXTRA_PRODUCER_DEATH_DURING_TEARDOWN_TEST" in activity
    assert "awaitViewFrameDrawn(activeGeneration, produced[produced.length - 1])" in test
    assert "firstPaused" in test and "producerBinderDied.await(5L" in test
    assert "parent_teardown_barrier_held=true admission_closed=true" in test
    assert "processAbsent" in test and "CL_R4B_PRODUCER_DEATH_DURING_TEARDOWN_PASS" in test
    assert "advanceNextFrameIdHint(frameIpcClient.nextFrameIdHint() + produced.length)" in test
    assert "terminateData.writeLong(child.sessionId)" in test
    service = (APP / "java/org/claritylink/android/Type111ProducerService.java").read_text()
    assert "ownerPid != activeOwnerPid" in service and "sameIdentity(identity, activeIdentity)" in service
    assert "terminationPending || endpoint == null" in service
    assert "terminationPending = true" in service
    assert "unbindTeardownProducer(teardownProducerConnection, teardownProducerBound)" in test
    assert "--cl-r4b-producer-death-teardown" in shell
    assert "P03 producer precondition or process-death receipts were absent or incomplete" in shell
    assert "decoded_frames=([2-9]|[1-9][0-9]+) view_drawn=true" in shell
    assert 'grep -F \'CL_R4B_PRODUCER_TEARDOWN_PRECONDITION_PASS \' | grep -E "session_id=$initial_session_generation([[:space:]]|$)"' in shell
    assert "run only named case or priority IDs" in acceptance
    assert "selected_combinations = (selected & known_combinations) if ns.only else known_combinations" in acceptance
    assert "type111_reentrant_producer_death" in shell
    assert '"CL-R4B-P03": ("producer-death-teardown"' in acceptance
    assert '"CL_R4B_PRODUCER_DEATH_DURING_TEARDOWN_PASS"' in acceptance
    assert '"default": "--cl-r4-type111"' in acceptance
    assert '("CL-R4-07", "Generation, ownership, and replay attacks", "owner-death"' in acceptance
    assert "Required owner-death runtime receipt missing" in shell
    assert "CL_R4B_OWNER_DEATH_SESSION_CAPACITY_PASS" in shell


def test_actual_view_process_death_is_injected_at_parent_teardown_barrier():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    shell = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    acceptance = (REPO / "tools/run_cl_r4_acceptance.py").read_text()
    test = activity[activity.index("private void runReentrantParentTeardown"):
                    activity.index("private void killType110SinkForTeardownRace")]
    assert "EXTRA_VIEW_DEATH_DURING_TEARDOWN_TEST" in activity
    assert "CL_R4B_VIEW_DEATH_DURING_TEARDOWN_BARRIER_HELD" in test
    assert "activePfdTransfers != 1" in test
    assert "view_death_teardown_runner_did_not_kill_view" not in test
    assert "--cl-r4b-view-death-teardown" in shell
    assert 'expected_view_process="$package:type111_view"' in shell
    assert 'shell ps | tr -d \'\\r\' > "$before_ps"' in shell
    assert 'kill_command="kill -KILL' in shell
    assert 'remote_kill_command="run-as $package sh -c' in shell
    assert 'shell "$remote_kill_command" 2>&1) || {' in shell
    assert "CL_R4B_REMOTE_VIEW_KILL_STATUS=0" in shell
    assert 'host_identity_checked=true package_uid_signal=true' in shell
    assert 'printf \'%s\\n\' "$held"' in shell
    assert 'TYPE111_PARENT_TEARDOWN_COMPLETED session_id=$held_session result=accepted" | tail -1' in shell
    assert 'TYPE111_PARENT_TEARDOWN_RESOURCES session_id=$held_session remaining_streams=0 active_pfd_transfers=0 retained_frame_bytes=0" | tail -1' in shell
    assert 'CL_R4B_VIEW_DEATH_KILL_COMMAND_ACCEPTED' in shell
    assert 'new CountDownLatch(1).await();' in test
    assert 'await(12000L, TimeUnit.MILLISECONDS)' not in test
    assert 'view_pid" = "$initial_type111_pid"' in shell
    assert 'held_type110_pid" = "$initial_type110_sink_pid"' in shell
    assert "CL_R4B_VIEW_DEATH_DURING_TEARDOWN_API17_PASS" in shell
    assert '"CL-R4B-P04": ("view-death-teardown"' in acceptance
    assert '"IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true active_pfd_transfers=0 retained_frame_bytes=0"' in acceptance


def test_status_only_recovery_checks_only_new_live_log_lines():
    shell = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert shell.count('recovery_log_line_start=$(adb_local -s "$serial" logcat -d') == 2
    assert shell.count('tail -n +$((recovery_log_line_start + 1))') == 2


def test_warning_preemption_case_runs_the_reattached_type111_fixture():
    acceptance = (REPO / "tools/run_cl_r4_acceptance.py").read_text()
    assert '("CL-R4-11", "Warning preemption", "reattach"' in acceptance
    assert '"CL_R6_DECODED_TYPE111_WARNING_BLOCK_PASS"' in acceptance
    assert '"CL_R6_DECODED_TYPE111_WARNING_RECOVERY_PASS"' in acceptance


def test_parent_owner_death_harness_kills_only_verified_compositor_and_checks_restart():
    manifest = ET.parse(APP / "AndroidManifest.lab.xml").getroot()
    activity = next(item for item in manifest.find("application").findall("service")
                    if item.get(ANDROID + "name") ==
                    "org.claritylink.android.CompositorOwnerDeathTestService")
    assert activity.get(ANDROID + "process") == ":owner_death_test"
    # The child-cleanup trigger is an in-process lab control surface; it must
    # not be externally callable even by another same-UID package.
    assert activity.get(ANDROID + "exported") == "false"
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
    assert "query.compositorPid != targetPid" in source
    assert "query.ownerValid || query.identity != null" in source
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
    assert "The owner Activity lacked a live, surfaced API17 View window" in runner
    assert "The exact Type111 View process was not live before compositor death." in runner
    assert "verify_api17_dual_output_content.swift" in runner
    assert "CL_R4B_OWNER_DEATH_PRECONDITION_PASS" in runner
    assert "SURFACE_BORROWED_LOST owner=Presentation_SurfaceHolder released_by_app=false" in runner
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
    assert "FrameLabSink.bindCompositorEpoch(ownerSink, ownerIdentity, endpoint," in compositor
    assert "MAX_ACTIVE_PARENT_SESSIONS = 8" in compositor
    assert "PROVISIONAL_PARENT_AUTHORITY_TIMEOUT_MS = 30000L" in compositor
    assert "provisional_authority_timeout" in compositor
    assert "authority.provisional = false" in compositor
    assert "verifyFreshSessionRecovery(service, freshCompositorPid)" in observer
    assert "currentOwnedCompositorPid()" in observer
    assert "old_type110_identity_re_registered_after_owner_restart" in observer
    assert "old_session_capability_re_registered_after_owner_restart" in observer
    assert "fresh_type110_session_registration_failed" in observer
    assert "fresh_type111_stream_registration_failed" in observer
    assert "fresh_session_teardown_left_resources" in observer
    assert "newOwnerClient.endWithCleanupReceipt(newSessionId)" in observer
    assert "describeCleanup(freshCleanup)" in observer
    assert "describeStats(ownerStats)" in observer
    assert "describeStats(childStats)" in observer
    assert "describeStreamQuery(ended)" in observer
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
    assert "FrameLabSink.revokeParentAuthority(ownerSink, ownerIdentity, ownerToken)" in compositor
    assert "cause=owner_end" in compositor
    assert "MAX_RECENT_SESSION_IDS = 256" in compositor
    sink = (APP / "java/org/claritylink/android/FrameLabSink.java").read_text()
    assert "isCompositorProcessCaller()" in sink
    assert 'context.getPackageName() + ":compositor"' in sink


def test_owner_capacity_cleanup_assertion_respects_revoked_query_authority():
    source = (APP / "java/org/claritylink/android/CompositorOwnerDeathTestService.java").read_text()
    assert "cleanup.isClean()" in source
    assert "freshCleanup.isClean()" in source
    assert "queryIsFenced(endedStats)" in source
    helper = source[source.index("private static boolean queryIsFenced("):
                    source.index("private static String describeCleanup(")]
    assert "!stats.authorized" in helper
    assert "!stats.registered" in helper


def test_parent_authority_revokes_with_owner_lifetime_token_death():
    compositor = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    sink = (APP / "java/org/claritylink/android/FrameLabSink.java").read_text()
    authority = compositor[compositor.index("private static final class ParentAuthority"):
                           compositor.index("private final class SinkAdmissionGrant")]
    opening = compositor[compositor.index("private boolean openParentAuthority("):
                        compositor.index("private boolean isAuthorizedParentCaller(")]
    revocation = compositor[compositor.index("private void revokeParentAuthority(ParentAuthority expected, String cause)"):
                           compositor.index("/** Owner loss must not strand")]
    assert "final IBinder ownerLifetimeToken;" in authority
    assert "ownerToken.linkToDeath(proposed.ownerLifetimeDeathRecipient, 0)" in opening
    assert 'revokeParentAuthority(proposed, "owner_lifetime_token_death")' in opening
    assert "if (proposed.dead)" in opening
    assert "FrameLabSink.revokeParentAuthority(ownerSink, ownerIdentity, ownerToken)" in opening
    assert "expectedOwnerToken == null || statsOwnerToken == expectedOwnerToken" in sink
    assert "existing.ownerLifetimeToken == ownerToken" in opening
    assert "expected.ownerLifetimeToken.unlinkToDeath(expected.ownerLifetimeDeathRecipient, 0)" in revocation
    assert "unregisterStreamState(state, identity)" in revocation


def test_completed_parent_teardown_unlinks_both_owner_death_recipients():
    compositor = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    finish = compositor[compositor.index("private boolean finishPendingParentTeardown("):
                        compositor.index("private static void writeControlReply(")]
    assert "authority.ownerSink.unlinkToDeath(authority.deathRecipient, 0)" in finish
    assert "authority.ownerLifetimeToken.unlinkToDeath(" in finish
    assert "authority.ownerLifetimeDeathRecipient, 0)" in finish


def test_parent_teardown_completion_is_idempotent_after_close_ack_race():
    compositor = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    finish = compositor[compositor.index("private boolean finishPendingParentTeardown("):
                        compositor.index("private static void writeControlReply(")]
    already_completed = finish[finish.index("if (!pendingParentTeardowns.contains(sessionId))"):
                               finish.index("return !type111Sessions.containsKey(sessionId)")]
    assert "if (state.identity.sessionId == sessionId) return false" in already_completed
    assert "return !type111Sessions.containsKey(sessionId)" in finish
    assert "!parentAuthorities.containsKey(sessionId)" in finish
    assert "!activeSessionIds.contains(sessionId)" in finish
    assert "!closingSessions.contains(sessionId)" in finish


def test_activity_uses_one_owner_lifetime_token_for_all_type110_authority_openers():
    client = (APP / "java/org/claritylink/android/FrameIpcClient.java").read_text()
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    assert "private final IBinder ownerLifetimeToken;" in client
    assert "FrameIpcClient(IBinder endpoint, IBinder ownerLifetimeToken)" in client
    assert "new FrameIpcClient(compositorEndpoint, ownerLifetimeToken)" in activity
    assert activity.count("new FrameIpcClient(compositorEndpoint, ownerLifetimeToken)") == 2


def test_type110_owner_token_lives_with_sink_process_across_view_death():
    compositor = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    manifest = ET.parse(APP / "AndroidManifest.lab.xml").getroot()
    services = manifest.find("application").findall("service")
    sink = next(item for item in services if item.get(ANDROID + "name") ==
                "org.claritylink.android.FrameLabSinkService")
    view = next(item for item in manifest.find("application").findall("activity") if
                item.get(ANDROID + "name") ==
                "org.claritylink.android.ClarityLinkDisplayActivity")
    assert sink.get(ANDROID + "process") == ":type110_sink"
    assert view.get(ANDROID + "process") == ":type111_view"
    assert "ownerLifetimeToken = service;" in activity
    assert "private final IBinder ownerLifetimeToken = new Binder()" not in activity
    assert "processVerifiedAbsent(existingOwnerPid, existingOwnerProcess)" in compositor
    assert "existing.ownerLifetimeToken == ownerToken && ownerToken.isBinderAlive()" in compositor
    assert "existing.ownerSink.equals(ownerSink)" in compositor
    assert "existing.ownerPid = ownerPid" in compositor
    assert "FrameLabSink.prepareOwnerPidRebind(ownerSink, ownerIdentity, endpoint" in compositor
    assert "FrameLabSink.completeOwnerPidRebind(ownerSink, ownerIdentity, endpoint" in compositor
    assert "FrameLabSink.cancelOwnerPidRebind(ownerSink, ownerIdentity, endpoint" in compositor
    assert "current.ownerPidRebindInProgress = true" in compositor
    assert "existing.ownerPidRebindInProgress" in compositor
    assert "!pendingParentTeardowns.contains(ownerIdentity.sessionId)" in compositor
    assert "owner_pid_rebind_rollback_failed" in compositor
    sink_java = (APP / "java/org/claritylink/android/FrameLabSink.java").read_text()
    assert "FRAME_LAB_PREPARE_OWNER_PID_REBIND" in sink_java
    assert "FRAME_LAB_COMPLETE_OWNER_PID_REBIND" in sink_java
    assert "FRAME_LAB_CANCEL_OWNER_PID_REBIND" in sink_java
    assert "statsOwnerPidQueriesBlocked = true" in sink_java
    assert "statsOwnerPidQueriesBlocked = false" in sink_java
    assert "statsOwnerPid == previousOwnerPid" in sink_java
    assert "statsOwnerToken == ownerToken" in sink_java
    assert "statsOwnerPid = replacementOwnerPid" in sink_java


def test_reattach_runtime_receipts_are_forwarded_to_acceptance_manifest():
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert 'if [ "$type111_reattach" -eq 1 ]; then' in runner
    assert 'printf \'%s\\n\' "$progress_line"' in runner
    assert "CL_R4_TYPE111_CONSUMER_REATTACH_PASS" in runner
    assert "actual_view_process_death=true" in runner
    assert "type110_generation_preserved=true" in runner


def test_api17_same_uid_sibling_attack_cannot_query_session_or_mutate_state():
    source = (APP / "java/org/claritylink/android/SameUidRegistrationAttackTestService.java").read_text()
    manifest = ET.parse(APP / "AndroidManifest.lab.xml").getroot()
    service = next(item for item in manifest.find("application").findall("service")
                   if item.get(ANDROID + "name") ==
                   "org.claritylink.android.SameUidRegistrationAttackTestService")
    assert service.get(ANDROID + "process") == ":registration_attacker"
    assert service.get(ANDROID + "exported") == "false"
    assert '"same_uid_query_disclosure_not_blocked"' in source
    assert "queryDenied(before)" in source and "statsDenied(ownerBefore)" in source
    assert "sinkStatsDenied(ownerSink)" in source
    sink = (APP / "java/org/claritylink/android/FrameLabSink.java").read_text()
    assert "callerPid == statsOwnerPid" in sink
    assert "suppliedOwnerToken == statsOwnerToken" in sink
    assert "statsOwnerPidQueriesBlocked" in sink
    assert "statsOwnerPid = ownerPid" in sink and "statsOwnerPid = 0" in sink
    assert "statsOwnerToken = ownerToken" in sink and "statsOwnerToken.isBinderAlive()" in sink
    assert "ownerToken.linkToDeath(ownerRecipient, 0)" in sink
    assert "statsOwnerToken == ownerToken" in sink
    assert "!queryDenied(after)" in source and "!statsDenied(ownerAfter)" in source
    assert "process_identity_hidden=true" in source
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
    stats_query = compositor[compositor.index("if (code == FrameIpcProtocol.FRAME_LAB_QUERY_STATS) {"):
                             compositor.index("if (code == FrameIpcProtocol.BEGIN) {")]
    stream_query = compositor[compositor.index("if (code == FrameIpcProtocol.TYPE111_QUERY_STREAM) {"):
                              compositor.index("if (code == FrameIpcProtocol.TYPE111_DETACH_SINK) {")]
    assert "isAuthorizedSessionQueryCaller(identity.sessionId)" in stats_query
    assert "reply.writeInt(authorized ? 1 : 0)" in stats_query
    assert "isAuthorizedSessionQueryCaller(ownerIdentity.sessionId)" in stream_query
    assert "reply.writeInt(authorized ? 1 : 0)" in stream_query
    assert "authorized ? Process.myPid() : 0" in stream_query
    query_auth = compositor[compositor.index("private boolean isAuthorizedSessionQueryCaller"):
                            compositor.index("/** Shutdown may still need", compositor.index(
                                "private boolean isAuthorizedSessionQueryCaller"))]
    assert "isSessionOwnerCaller(sessionId, true)" in query_auth
    assert "inspect cleanup state while teardown is in progress" in query_auth
    assert "caller_not_bound_to_session_owner" in query_auth
    observer_registration = compositor[compositor.index(
        "if (code == FrameIpcProtocol.LAB_REGISTER_OWNER_DEATH_QUERY_OBSERVER) {"):
        compositor.index("if (code == FrameIpcProtocol.FRAME_LAB_QUERY_STATS)")]
    assert 'getPackageName() + ":owner_death_test"' in observer_registration
    assert "isSessionOwnerCaller(ownerIdentity.sessionId)" in observer_registration
    assert "final int observerPid = data.readInt()" in observer_registration
    assert "authorizedOwnerDeathObserverPid == 0" in observer_registration
    assert "authorizedOwnerDeathObserverPid == callerPid" in query_auth
    assert "observerToken.linkToDeath" in observer_registration
    assert "ownerDeathObserverToken.isBinderAlive()" in query_auth
    assert '":owner_death_test").equals(callerProcess)' in query_auth
    assert query_auth.index("processNameForPid(callerPid)") < query_auth.index("synchronized (streamsLock)")
    assert "isSessionOwnerCaller(ownerIdentity.sessionId)" in observer_registration
    owner_grant = activity[activity.index("private void startOwnerDeathQueryObserver"):
                           activity.index("private void runReentrantParentTeardown")]
    assert "startService(observer)" in owner_grant


    assert "registerOwnerDeathQueryObserver(owner, observerPid, token[0])" in owner_grant
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


def test_owner_death_cleanup_receipt_does_not_confuse_denial_with_zero_resource_stats():
    control = (APP / "java/org/claritylink/android/Type111ControlClient.java").read_text()
    owner = (APP / "java/org/claritylink/android/CompositorOwnerDeathTestService.java").read_text()
    assert "final boolean authorized" in control
    assert "!ownerDeathObserved || query.authorized || query.compositorPid != 0" in owner
    assert "awaitPredeathResourceCleanup(control)" in owner
    assert "resource_state=not_observable_after_owner_death" in owner
    post_death = owner[owner.index("if (!ownerDeathObserved"):owner.index(
        "requireOldFrameRejected(service, ownerIdentity")]
    assert "queryFrameStats(ownerIdentity)" not in post_death


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
    assert "reentrant_parent_teardown_query_not_fenced_after_exit" in activity
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
    assert "primaryStats = ensureType110RecoveryFrame(primaryIdentity, primaryStats);" in activity
    recovery_receipt = activity[activity.index("private FrameLabSink.Stats ensureType110RecoveryFrame"):
                               activity.index("/** Holds the Type111 Handler at a known frame")]
    assert "submitForReceipt(primaryLabIpcClient" in recovery_receipt
    assert '"accepted".equals(receipt)' in recovery_receipt
    assert "verified.frameId <= currentStats.frameId" in recovery_receipt
    assert "CL_R2_TYPE110_RECOVERY_FRAME_READY" in recovery_receipt
    fixture = activity[activity.index("private DecodedFrame syntheticType110RecoveryFrame"):
                       activity.index("/** Holds the Type111 Handler at a known frame")]
    assert "return new DecodedFrame(2, 2, 8, timestampNs, 0, 0, 0, 2, 2," in fixture
    assert "ByteBuffer.wrap(rgba)" in fixture
    warning_race = activity[activity.index("private void startBinderWarningRace"):
                            activity.index("private void startDiagnosticRun")]
    crash_branch = warning_race[warning_race.index("if (crashAfterFirstFrame) {"):
                                warning_race.index("if (controlledExitAfterValidation) {")]
    controlled_exit_branch = warning_race[warning_race.index("if (controlledExitAfterValidation) {"):]
    for branch in (crash_branch, controlled_exit_branch):
        assert branch.index("ensureType110RecoveryFrame(primaryIdentity, primaryStats)") < \
            branch.index("issueType110ProbeOwnership(primaryIdentity, primaryStats)")
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
    assert 'IPC_TYPE111_SINK_DETACHED session_id=$crash_session' in runner
    assert 'session_id=$crash_session ' in runner
    assert 'connection_id=$child_connection ' in runner
    assert 'generation=$child_generation ' in runner
    assert '[ "$request_line_no" -lt "$receipt_line_no" ]' in runner
    assert 'Compositor recorded neither Type111 Binder death nor exact-session sink detach after the crash.' in runner
    assert 'IPC_STREAM_UNREGISTERED session_id=$crash_session stream_type=111' not in runner
    assert 'IPC_TYPE111_SINK_DETACHED session_id=$controlled_session' in runner
    assert 'IPC_STREAM_UNREGISTERED session_id=$controlled_session stream_type=111' not in runner
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
    progress_order = runner[runner.index("assert_type110_progress_precedes_parent_teardown()"):
                           runner.index("adb_local -s \"$serial\" logcat -c")]
    assert "IPC_STREAM_REGISTERED session_id=$session stream_type=111 " in progress_order
    assert "IPC_VIEW_SINK_DEATH_CALLBACK session_id=$session stream_type=111 connection_id=$child_connection " in progress_order
    assert "child_generation=$(printf '%s\\n' \"$death_event\"" in progress_order
    assert "IPC_TYPE111_SINK_DETACHED session_id=$session connection_id=$child_connection generation=$child_generation" in progress_order
    assert "Type110 did not progress after exact Type111 death/detach" in progress_order


def test_delayed_callback_runtime_receipts_are_forwarded_to_acceptance_stdout():
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert 'grep -F "CL_R4B_DELAYED_SINK_CALLBACK_PASS session_id=$session_id "' in runner
    assert "grep -F 'CL_R4B_DELAYED_CALLBACK_POST_TEARDOWN_PASS stale_release_rejected=true session_not_resurrected=true'" in runner
    assert 'printf \'%s\\n\' "$delayed_callback_receipt" "$delayed_teardown_receipt"' in runner
    assert "Delayed callback runtime receipts are missing for the tested session or teardown." in runner
    assert 'logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I' in runner


def test_saturated_type111_view_queue_is_present_when_actual_view_process_crashes():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    crash_at = activity.index("if (crashAfterFirstFrame) {", activity.index(
        "for (int index = 0; index < 8 && blueOutputs < 4"))
    crash_block = activity[crash_at:activity.index("byte[] greenFixture", crash_at)]
    assert "crashWithSaturatedQueue" in crash_block
    assert "fillType111QueueForProducerFailure(binderGeneration)" in crash_block
    assert "CL_R4B_QUEUE_SATURATED_VIEW_DEATH_REQUEST" in crash_block
    assert crash_block.index("viewSink.queuedFrameCount()") < crash_block.index(
        "requestType111CrashAfterDecodedFrame()")

    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert "--cl-r4b-view-crash-queue-saturated" in runner
    assert "type111_crash_queue_saturated" in runner
    assert "--ez crash_with_saturated_type111_queue true" in runner
    assert 'CL_R4B_QUEUE_SATURATED_VIEW_DEATH_REQUEST' in (REPO / "tools/run_cl_r4_acceptance.py").read_text()


def test_saturated_type111_view_queue_is_cleaned_by_parent_teardown():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    teardown = activity[activity.index("private void runReentrantParentTeardown"):
                        activity.index("/** Kill the real separate Type110 sink", activity.index(
                            "private void runReentrantParentTeardown"))]
    assert "queueSaturatedTeardownTest" in teardown
    assert "fillType111QueueForProducerFailure(child.streamGeneration)" in teardown
    assert "parent_teardown_starts_with_saturated_view_queue" in teardown
    assert "saturated_parent_teardown_resources_retained" in teardown
    assert "CL_R4B_QUEUE_SATURATED_PARENT_TEARDOWN_PASS" in teardown
    assert "saturatedQueueControl.releaseForClose()" in teardown
    assert "saturatedQueueControl.dispatchFinished.await" in teardown
    assert "held_dispatch_finished=true" in teardown
    assert teardown.index("fillType111QueueForProducerFailure") < teardown.index(
        "LAB_ARM_TRANSFER_BARRIER")

    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert "--cl-r4b-reentrant-teardown-queue-saturated" in runner
    assert "type111_reentrant_queue_saturated" in runner
    assert "--ez queue_saturated_teardown_test true" in runner
    assert "queue_request_line=$(printf '%s\\n' \"$logs\" | grep -F \"CL_R4B_QUEUE_SATURATED_PARENT_TEARDOWN_REQUEST" in runner
    assert 'post_exit_query_fenced=true handler_released=true held_dispatch_finished=true' in runner
    assert 'printf \'%s\\n\' "$teardown_completed_line" "$process_destroyed_line" "$pass_line"' in runner
    acceptance = (REPO / "tools/run_cl_r4_acceptance.py").read_text()
    assert '"CL-R4B-P02"' in acceptance
    assert "CL_R4B_QUEUE_SATURATED_PARENT_TEARDOWN_PASS" in acceptance


def test_type111_queue_fixture_advances_past_restarted_producer_frame_ids():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    restart = activity[activity.index("long restartedProducerFirstFrameId"):
                       activity.index('Log.i(TAG, "CL_R4_TYPE111_PRODUCER_DEATH_RESTART_PASS')]
    assert "frameIpcClient.advanceNextFrameIdHint(restartedProducerFirstFrameId +" in restart
    assert "restartedFrames.length" in restart
    queue_helper = activity[activity.index("private FrameViewSink.TestControl fillType111QueueForProducerFailure"):
                            activity.index("private static DecodedFrame queueSaturationFrame")]
    assert "submitForReceipt(frameIpcClient, firstFrame, generation)" in queue_helper
    client = (APP / "java/org/claritylink/android/FrameIpcClient.java").read_text()
    assert "void advanceNextFrameIdHint(long minimumNextFrameId)" in client
    assert "nextFrameId.compareAndSet(current, minimumNextFrameId)" in client


def test_end_receipt_snapshots_all_parent_streams_when_admission_closes():
    compositor = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    end = compositor[compositor.index("private boolean endStreamWithReceipt("):
                     compositor.index("private boolean endStreamIfCurrent(")]
    marker = "private String teardownType111Session(FrameStreamIdentity type110Owner, boolean internalOwnerDeath,"
    teardown = compositor[compositor.index(marker):
                         compositor.index("private int countSessionStreams(")]
    assert "endStreamWithReceipt(identity, affected)" in compositor
    assert "teardownType111Session(identity, false, receiptStates)" in end
    close = teardown.index("closingSessions.add(sessionId)")
    capture = teardown.index("if (receiptStates != null)")
    assert close < capture
    assert "synchronized (streamsLock)" in teardown
    assert "receiptStates.add(state)" in teardown


def test_frame_transfer_reservation_is_atomic_with_session_close_admission():
    compositor = (APP / "java/org/claritylink/android/CompositorService.java").read_text()
    receive = compositor[compositor.index("private void receiveFrame("):
                        compositor.index("private static byte[] readBoundedPayload(")]
    reserve = receive[receive.index("synchronized (streamsLock)"):receive.index("if (state == null)")]
    assert "streams.get(identity.key())" in reserve
    assert "closingSessions.contains(identity.sessionId)" in reserve
    assert "candidate.transferActive.compareAndSet(false, true)" in reserve
    assert reserve.index("closingSessions.contains") < reserve.index("compareAndSet")
    assert "admissionFailure = \"session_closing\"" in reserve


def test_stale_type110_probe_accepts_actual_identity_or_contract_rejection():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    probe = activity[activity.index("long staleProbeGeneration = reattachSessionId > 0L ?"):
                     activity.index("submitType110DecodedFrame(decodedType110, binderGeneration)")]
    assert '"frame_contract_rejected".equals(stalePrimary)' in probe
    assert '"stream_identity_rejected".equals(stalePrimary)' in probe
    assert "long staleProbeGeneration = reattachSessionId > 0L ?" in probe
    assert "primaryBefore.streamGeneration : newPrimaryGeneration" in probe
    assert '"stale_reason=" + stalePrimary' in probe


def test_stale_type111_probe_records_actual_binder_rejection_reason():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    probe = activity[activity.index('String staleType111 = frameIpcClient.probeMalformed("stale_generation"'):
                     activity.index("DecodedFrame recoveredType111 = decodeFixtureFrame")]
    assert '"frame_contract_rejected".equals(staleType111)' in probe
    assert '"stream_identity_rejected".equals(staleType111)' in probe
    assert 'stale_reason=" + staleType111' in activity[
        activity.index('Log.i(TAG, "CL_R4_TYPE111_LIVE_GENERATION_PASS'):
        activity.index("if (reattachSessionId <= 0L)", activity.index('Log.i(TAG, "CL_R4_TYPE111_LIVE_GENERATION_PASS'))]


def test_all_stale_generation_fixtures_accept_only_real_receiver_denials():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    assert '"frame_contract_rejected".equals(staleFrame)' in activity
    assert '"stream_identity_rejected".equals(staleFrame)' in activity
    assert 'stale_reason=" + staleFrame' in activity
    assert '"frame_contract_rejected".equals(staleReason)' in activity
    assert '"stream_identity_rejected".equals(staleReason)' in activity
    assert 'receiver_reason=" + staleReason' in activity
    assert '"frame_contract_rejected".equals(staleProducerGeneration)' in activity
    assert '"stream_identity_rejected".equals(staleProducerGeneration)' in activity


def test_multiple_view_replacement_mode_checks_three_unique_process_generations():
    shell = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    acceptance = (REPO / "tools/run_cl_r4_acceptance.py").read_text()
    assert "--cl-r4b-multiple-view-replacements" in shell
    assert "for ordinal in 1 2 3" in shell
    assert "unique_pids=true increasing_generations=true" in shell
    assert "stream_generation=$replacement_generation" in shell
    assert "replacement_ordinal_arg=${3:-0}" in shell
    assert 'view_replacement_ordinal "$replacement_ordinal_arg"' in shell
    assert "multiple_view_replacement_test" in activity
    assert "CL_R4B_MULTI_VIEW_REPLACEMENT_PASS" in activity
    assert "CL_R4B_MULTI_VIEW_REPLACEMENT_EXIT_REQUESTED" in activity
    assert '" type110_last_frame_id=" + reattachedType110Stats.frameId' in activity
    assert "1000000000000L * Math.max(1, viewReplacementOrdinal)" in activity
    assert 'index($NF, package ":")==1' in shell
    assert "api17-replacement-pid-reuse-$ordinal-$adb_port.txt" in shell
    assert '"CL-R4B-P08": ("multiple-view-replacements"' in acceptance


def test_owner_death_during_child_cleanup_requires_held_queue_and_zero_cleanup():
    shell = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    acceptance = (REPO / "tools/run_cl_r4_acceptance.py").read_text()
    assert "--cl-r4b-owner-death-child-cleanup" in shell
    assert "owner_death_child_cleanup_test" in shell
    assert "CL_R4B_OWNER_DEATH_CHILD_QUEUE_READY" in activity
    assert "CL_R4B_OWNER_DEATH_CHILD_BARRIER_RELEASED" in activity
    assert "cause=binder-death-recipient" in activity
    assert "owner_death_trigger_line" in shell
    assert "child_barrier_release_line" in shell
    assert "trigger_child_queue_owner_death" in activity
    assert "childQueueDeathTrigger.await(5L, TimeUnit.SECONDS)" in (
        REPO / "android/cl-imp-03-app/java/org/claritylink/android/CompositorOwnerDeathTestService.java"
    ).read_text()
    assert "CL_R4B_OWNER_DEATH_CHILD_CLEANUP_PASS" in activity
    assert "viewSink.closeSession(observedSessionId, false)" in activity
    assert "ownerDeathChildViewFencePassed && !ownerDeathChildCleanupControl.barrierTimedOut" in activity
    assert "CL_R4B_OWNER_DEATH_CHILD_VIEW_FENCED" in activity
    assert "CL_R4B_OWNER_DEATH_CHILD_QUEUE_DRAINED" in activity
    assert "isGenerationFenced(observedSessionId)" in activity
    assert "A stale Type111 frame was enqueued after Binder owner death." in shell
    assert "ownerDeathChildBarrierReleasedByDeath && ownerDeathChildCleanupControl != null" in activity
    assert "!ownerDeathChildCleanupControl.barrierTimedOut" in activity
    assert "queued_frames_before=3" in shell
    assert '"CL-R4B-P05": ("owner-death-child-cleanup"' in acceptance


def test_decoder_shutdown_delivery_mode_closes_codec_while_view_dispatch_is_held():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    shell = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    acceptance = (REPO / "tools/run_cl_r4_acceptance.py").read_text()
    assert "--cl-r4b-decoder-shutdown-delivery" in shell
    assert "decoder_shutdown_delivery_test true" in shell
    assert "handlerEntered.await(5L, TimeUnit.SECONDS)" in activity
    assert "decoder.close();" in activity
    assert "finally {\n                                deliveryControl.releaseHandler.countDown();" in activity
    assert "requireType111(!deliveryControl.barrierTimedOut" in activity
    assert "frame_drawn_after_decoder_close=true" in activity
    assert "pending_frames=[1-9]" in shell
    assert "decoder_closed_before_delivery_release=true frame_drawn_after_decoder_close=true" in shell
    assert '"CL-R4B-P06": ("decoder-shutdown-delivery"' in acceptance
