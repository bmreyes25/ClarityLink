from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "android/cl-imp-03-app/java/org/claritylink/android"


def test_sink_replacement_is_version4_owner_authorized_and_identity_checked():
    protocol = (APP / "FrameIpcProtocol.java").read_text()
    client = (APP / "FrameIpcClient.java").read_text()
    service = (APP / "CompositorService.java").read_text()

    assert "static final int VERSION = 4;" in protocol
    assert "TYPE111_REPLACE_SINK = 25" in protocol
    assert "FrameIpcProtocol.TYPE111_REPLACE_SINK" in client
    assert "type110Owner.streamType != FrameStreamIdentity.TYPE110" in client
    assert "oldIdentity.streamType != FrameStreamIdentity.TYPE111" in service
    assert "oldIdentity.sameStream(newIdentity)" in service
    assert "oldIdentity.sessionId != ownerIdentity.sessionId" in service
    assert "newIdentity.streamGeneration != oldIdentity.streamGeneration + 1L" in service
    assert "ownerIdentity.equals(owner.identity)" in service
    assert "plane.canTransportGeneration(oldIdentity, newIdentity)" in service
    assert "!state.transferActive.get()" in service


def test_death_and_end_callbacks_are_fenced_to_the_registered_generation():
    service = (APP / "CompositorService.java").read_text()

    assert "createSinkDeathRecipient(state, identity, sink, null)" in service
    assert "state, newIdentity, newSink, deathGate" in service
    assert "deadIdentity = state.sink == registeredSink ? state.identity : registeredIdentity;" in service
    assert "streams.get(identity.key()) != state || !identity.equals(state.identity)" in service
    assert "detachType111SinkIfCurrent(state, deadIdentity)" in service
    assert "parent_session_preserved=true" in service


def test_pipe_and_worker_start_failures_release_owned_resources():
    service = (APP / "CompositorService.java").read_text()
    client = (APP / "FrameIpcClient.java").read_text()

    assert "boolean writerStarted = false;" in service
    assert "if (!writerStarted) try { pipe[1].close();" in service
    assert "catch (RuntimeException startFailure)" in client
    assert "catch (OutOfMemoryError startFailure)" in client
    assert client.count("frameGate.release();") >= 3
    forwarder = service[service.index("private boolean forwardToViewSink"):]
    assert "if (pipe != null && !writerStarted)" in forwarder
    assert "state.activePfdTransfers.decrementAndGet();" in forwarder


def test_failed_replacement_unlinks_candidate_and_rolls_back_generation():
    service = (APP / "CompositorService.java").read_text()

    assert "if (!accepted) {" in service
    assert "newSink.unlinkToDeath(newRecipient, 0)" in service
    assert "ReplacementDeathGate deathGate = new ReplacementDeathGate();" in service
    assert "if (!deathGate.dead && stillCurrent" in service
    assert "state.compositor.end(newIdentity.streamGeneration);" in service


def test_activity_lifecycle_detaches_view_without_tearing_down_parent_session():
    protocol = (APP / "FrameIpcProtocol.java").read_text()
    client = (APP / "Type111ControlClient.java").read_text()
    service = (APP / "CompositorService.java").read_text()
    activity = (APP / "ClarityLinkDisplayActivity.java").read_text()

    assert "TYPE111_DETACH_SINK = 28" in protocol
    assert "detachType111Sink(final FrameStreamIdentity type110Owner" in client
    assert "ownerIdentity.streamType != FrameStreamIdentity.TYPE110" in service
    assert '"authorized_type110_owner=true"' in service
    lifecycle_start = activity.index("private void closeViewAttachmentPreservingParent")
    cleanup_start = activity.index("private void closeIpcSession", lifecycle_start)
    lifecycle = activity[lifecycle_start:cleanup_start]
    assert "control.detachType111Sink(owner, child)" in lifecycle
    assert "parentSessionPreservedForLifecycle = true;" in lifecycle
    assert 'closeViewAttachmentPreservingParent("activity-pause")' in activity
    assert 'closeViewAttachmentPreservingParent("activity-destroy")' in activity
    assert "parentTeardown(" not in lifecycle


def test_generation_change_and_parent_snapshot_are_fenced_against_teardown():
    service = (APP / "CompositorService.java").read_text()
    generation_change = service[service.index("if (code == FrameIpcProtocol.CHANGE_GENERATION)"):
                               service.index("if (code == FrameIpcProtocol.WARNING)")]
    teardown = service[service.index("private String teardownType111Session"):
                       service.index("private static void writeControlReply")]

    assert "synchronized (streamsLock)" in generation_change
    assert "!closingSessions.contains(identity.sessionId)" in generation_change
    assert "state.identity = identity.withGeneration(newGeneration);" in generation_change
    assert "ArrayList<StreamState> ownedStates" in teardown
    assert "synchronized (state.lock) { identity = state.identity; }" in teardown


def test_lifecycle_detach_cancels_fixture_worker_without_parent_teardown():
    activity = (APP / "ClarityLinkDisplayActivity.java").read_text()
    detach_start = activity.index("private void closeViewAttachmentPreservingParent")
    cleanup_start = activity.index("private void closeIpcSession", detach_start)
    lifecycle = activity[detach_start:cleanup_start]
    worker_catch = activity[activity.index("private void startType111FixtureRun"):
                            activity.index("private byte[] type111Fixture")]

    assert "runToken.cancelForDetach();" in lifecycle
    assert "fixtureWorker.interrupt();" in lifecycle
    assert "if (!runToken.isCancelled())" in worker_catch
    assert "if (!runToken.claimTeardown())" in worker_catch
    assert "if (previousWorker != null && previousWorker.isAlive())" in worker_catch
    assert "CL_R4A_FIXTURE_CANCELLED_BY_VIEW_LIFECYCLE" in worker_catch


def test_api17_reattach_harness_restarts_view_with_the_existing_parent_session():
    activity = (APP / "ClarityLinkDisplayActivity.java").read_text()
    runner = (ROOT / "tools/run_cl_imp_03_emulator.sh").read_text()

    assert 'control.queryType111Stream(primaryIdentity)' in activity
    assert 'FrameIpcClient.replaceType111Sink(compositorEndpoint, primaryIdentity' in activity
    assert '"stale_frame_rejected=true"' in activity
    assert '"CL_R4A_VIEW_REATTACH_PASS session_id="' in activity
    assert '" type110_generation=" + reattachType110Generation' in activity
    assert 'if (reattachSessionId > 0L && type111FixtureMode)' in activity
    assert 'else submitSyntheticFrame(activeGeneration);' in activity
    assert 'fixtureTimestampOffsetNs = reattachSessionId > 0L ? 1000000000000L : 0L;' in activity
    assert 'firstPtsUs += fixtureTimestampOffsetNs / 1000L;' in activity
    assert 'long inputPts = fixturePtsUs(100000L);' in activity
    assert 'lastType111SubmissionTimestampNs + 1L' in activity
    assert 'copyWithTimestamp(frame, timestamp)' in activity
    assert 'control.pauseHandlerAt(handlerBarrierFrame.presentationTimeNs);' in activity
    assert 'if (reattachSessionId <= 0L)' in activity
    assert 'timestamp_bounds_preserved=true' in activity
    assert 'type110_identity_unchanged_since_type111_sink_replacement' in activity
    assert '--cl-r4-type111-reattach' in runner
    assert 'start_lab_activity_privileged type111_reattach "$session_id"' in runner
    assert 'initial_type111_pid=$(printf' in runner
    assert 'api17-type111-reattach-logcat-$adb_port.txt"' in runner
    assert "grep -F 'IPC_REMOTE_FRAME ' | grep -F \"session_id=$session_id \"" in runner
    assert 'grep -F "IPC_TYPE111_SINK_REPLACED session_id=$session_id "' in runner
    assert "grep -F 'streams=110:primary_lab,111:secondary_view'" in runner
    assert 'if [ "$type111_reattach" -eq 0 ]; then' in runner
    assert 'replacement_pid=$replacement_pid parent_session_reused=true' in runner
    assert "type110_last_frame_id=\\([0-9]" in runner
