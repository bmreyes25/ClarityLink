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
    assert helpers.count("teardownType111Session(identity)") == 2
    assert "TYPE110_OWNER_SESSION_INVALIDATED" in helpers
    assert "return unregisterStream(identity);" in helpers
    assert "return unregisterStreamIfCurrent(state, identity);" in helpers


def test_type110_sink_rejects_a_second_session_identity():
    service = (APP / "java/org/claritylink/android/FrameLabSinkService.java").read_text()
    ensure = service[service.index("private synchronized boolean ensureSink"):
                    service.index("@Override public void onDestroy()")]
    assert "if (sink != null) return sessionId > 0L && requestedSession == sessionId;" in ensure


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
    assert "assert_type110_probe_cross_uid_denied" in runner
    assert "ATTACK_DENIED operation=service component=Type110SinkFailureTestService" in runner
    assert "ATTACK_DENIED operation=bind_service component=Type110SinkFailureTestService" in runner
    assert "target_session_id \"$session_id\"" in runner
    assert "TYPE111_PARENT_TEARDOWN session_id=$session_id streams_closed=2 result=accepted" in runner
    assert "cause=owner_sink_death streams_closed=2" in runner
    assert "IPC_STREAM_UNREGISTERED session_id=$session_id stream_type=111" in runner
    assert "active_pfd_transfers=0 retained_frame_bytes=0" in runner
    assert "CL_R4B_TYPE110_ONLY_FAILURE_PASS" in runner


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
    assert "PRESENTATION_DISMISS_REQUESTED reason=ipc-remote-disconnected" in runner
    assert "owner-death-window-state-$adb_port.txt" in runner
    assert "api17-compositor-owner-death-window-before-$adb_port.txt" in runner
    assert "App-owned secondary Presentation window remained" in runner
    assert "END {if (matched && on_secondary) found=1; exit !found}" in runner
    assert "PRESENTATION_CLOSE_FAILED" in runner

    attacker = (REPO / "android/cl-r4-boundary-attacker/java/org/claritylink/attacker/ExportBoundaryAttackActivity.java").read_text()
    assert 'attemptPrivateService("CompositorOwnerDeathTestService")' in attacker
    assert 'if (attempted == 23 && denied == attempted)' in attacker
    assert '"CompositorOwnerDeathTestService".equals(simpleName)' in attacker

    build = (REPO / "tools/build_cl_imp_03_apks.sh").read_text()
    assert "CompositorOwnerDeathTestService.java" in build


def test_parent_owner_loss_cancels_activity_fixture_worker():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    start = activity.index("private void stopOwnedDisplay")
    end = activity.index("/** Release only the Activity-owned View attachment", start)
    stop = activity[start:end]
    assert "runToken.cancelForDetach();" in stop
    assert "fixtureWorker.interrupt();" in stop
    assert "closeIpcSession();" in stop


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
    assert "Expected one parent teardown commit" in runner
    assert "Stream $stream_type unregister count was" in runner


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
    assert "labDelayedDeathSink == child.sink" in service
    assert "pauseLabDelayedDeathCallback(" in service
    assert "release.await(120000L, TimeUnit.MILLISECONDS)" in service
    assert "release.countDown()" in service
    assert "completed.await(10000L, TimeUnit.MILLISECONDS)" in service
    assert "old_callback_completed_after_replacement=true" in activity
    assert "armLabDelayedSinkDeathCallback" in client
    assert "fireLabDelayedSinkDeathCallback(primaryIdentity, replacement)" in activity
    assert "if (existing.sinkAttached && !delayedDeathCallbackTest)" in activity
    assert "replacement_preserved=true" in activity
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
