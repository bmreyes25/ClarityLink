from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "android/cl-imp-03-app/java/org/claritylink/android"


def test_view_close_is_admitted_only_for_exact_live_identity():
    sink = (APP / "FrameViewSink.java").read_text()
    assert "static final int VIEW_CLOSE = 42;" in (APP / "FrameIpcProtocol.java").read_text()
    branch = sink[sink.index("if (code == FrameIpcProtocol.VIEW_CLOSE)"):
                  sink.index("if (code == FrameIpcProtocol.VIEW_CHANGE_GENERATION)")]
    assert "identity.equals(requestIdentity)" in branch
    assert "generation == requestIdentity.streamGeneration" in branch
    assert "lastClosedIdentity.equals(requestIdentity)" in branch
    assert "lastClosedIdentity = null" in sink


def test_close_timeout_keeps_exact_stream_fenced_until_ack_or_death():
    compositor = (APP / "CompositorService.java").read_text()
    assert "VIEW_CLOSE_TIMEOUT_MS = 1000L" in compositor
    assert "MAX_VIEW_CLOSE_ATTEMPTS = 3" in compositor
    assert "VIEW_CLOSE_RETRY_DELAY_MS = 100L" in compositor
    assert "MAX_PENDING_VIEW_CLOSES = MAX_ACTIVE_PARENT_SESSIONS * 2" in compositor
    assert "new ArrayBlockingQueue<Runnable>(MAX_PENDING_VIEW_CLOSES - 2)" in compositor
    unregister = compositor[compositor.index("private boolean unregisterStreamState(StreamState state,"):
                            compositor.index("private boolean removeStreamRegistrationIfCurrent")]
    assert "closeViewSink(state, sinkToClose, identity)" in unregister
    assert "if (!closeViewSink(state, sinkToClose, identity)) return false;" in unregister
    assert "state.closing = true;" in unregister
    assert "resolution=retain_fenced_identity" in compositor
    timeout = compositor[compositor.index("} catch (TimeoutException timeout)"):
                         compositor.index("} catch (Exception failure)")]
    assert "close.cancel" not in timeout
    assert "resolution=retain_fenced_identity" in timeout
    assert "recovery=owner_or_sink_restart_required" in compositor
    assert "closeViewSink(state, sink, identity, attempt + 1, false)" in compositor
    remove = compositor[compositor.index("private boolean removeStreamRegistrationIfCurrent"):
                        compositor.index("private boolean closeViewSink")]
    assert "streams.get(identity.key()) != state" in remove
    assert "!identity.equals(state.identity)" in remove
    assert "finishPendingParentTeardown(identity.sessionId);" in compositor
    teardown = compositor[compositor.index("private String teardownType111Session(FrameStreamIdentity type110Owner,"):
                         compositor.index("private int countSessionStreams")]
    assert 'return "accepted_pending";' in teardown
    assert '"accepted_pending".equals(reason)' in compositor
    assert "pendingParentTeardowns.add(sessionId);" in teardown


def test_api17_reattach_accepts_async_teardown_only_with_completion_receipt():
    runner = (ROOT / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert 'grep -F "TYPE111_PARENT_TEARDOWN_COMPLETED session_id=$session_id result=accepted late_close_resolution=true"' in runner
    assert "wait_for_parent_teardown \"$session_id\"" in runner
    assert "parent_teardown_request=accepted" in runner
    assert "Parent teardown did not complete" in runner


def test_reentrant_mode_does_not_misclassify_stopped_producer_as_live_uid_target():
    runner = (ROOT / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert 'if [ "$probe_boundary_checked" -eq 0 ] && [ "$reentrant_teardown" -eq 1 ]; then' in runner
    assert "The combined producer-recovery fixture has already unbound its producer" in runner
    assert "CL_R4B_REENTRANT_CROSS_UID_NOT_RUN=true separate_final_source_test_required=true" in runner
    assert 'cross_uid_probe_denied=NOT_RUN admission=pass' in runner


def test_shutdown_owner_can_only_drain_held_test_transfer():
    compositor = (APP / "CompositorService.java").read_text()
    barrier = compositor[compositor.index("if (code == FrameIpcProtocol.LAB_WAIT_TRANSFER_BARRIER"):
                         compositor.index("if (code == FrameIpcProtocol.LAB_ARM_PARENT_TEARDOWN_BARRIER)")]
    assert "code == FrameIpcProtocol.LAB_RELEASE_TRANSFER_BARRIER" in barrier
    assert "code == FrameIpcProtocol.LAB_WAIT_TRANSFER_FINISHED" in barrier
    assert "isSessionOwnerCaller(identity.sessionId,\n                        ownerMayDrainDuringShutdown)" in barrier
    auth = compositor[compositor.index("private boolean isSessionOwnerCaller(long sessionId, boolean"):
                      compositor.index("private boolean isAuthorizedFrameCaller")]
    assert "expected.ownerPid != callerPid" in auth
    assert "expected.ownerSink.isBinderAlive()" in auth
    assert "current == expected" in auth
    assert "allowClosingForDrain || !closingSessions.contains(sessionId)" in auth


def test_view_close_cancels_pending_frame_accounting_once():
    sink = (APP / "FrameViewSink.java").read_text()
    close = sink[sink.index("synchronized void close(long value)"):
                 sink.index("@Override protected synchronized boolean onTransact")]
    assert "cancelPendingDispatches();" in close
    assert "releaseForClose()" in close
    assert "viewCloseExecutor.shutdown();" in (APP / "CompositorService.java").read_text()
    assert "ui.removeCallbacks(this)" in sink
    assert "accounted.compareAndSet(true, false)" in sink
    assert "queuedBytes.addAndGet(-payloadBytes)" in sink
    assert "queuedFrames.decrementAndGet()" in sink


def test_producer_queue_failure_uses_current_generation_and_forces_partial_test_transfer():
    activity = (APP / "ClarityLinkDisplayActivity.java").read_text()
    producer = (APP / "Type111ProducerService.java").read_text()
    queue_setup = activity[activity.index('"producer_failure_queue_generation_is_fresh"'):
                           activity.index('"arm_actual_inflight_pfd_barrier"')]
    assert "frameIpcClient.streamIdentity()" in queue_setup
    assert "fillType111QueueForProducerFailure" in queue_setup
    assert "expandFirstFrameForTransferTest" in producer
    assert "TYPE111_PRODUCER_TRANSFER_TEST_FRAME_EXPANDED" in producer
    assert "scale = 8" in producer
    assert "TYPE111_PRODUCER_TRANSFER_TEST" in producer or "expandFirstFrameForTransferTest" in activity
    assert "new DecodedFrame(width, height, rowStride, timestampNs" in activity
    assert "final int width = 64, height = 64, rowStride = width * 4" in activity
