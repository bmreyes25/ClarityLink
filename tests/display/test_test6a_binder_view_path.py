from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "android/cl-imp-03-app/java/org/claritylink/android"


def test_remote_binder_frame_is_forwarded_to_bounded_view_sink():
    client = (APP / "FrameIpcClient.java").read_text()
    service = (APP / "CompositorService.java").read_text()
    sink = (APP / "FrameViewSink.java").read_text()
    protocol = (APP / "FrameIpcProtocol.java").read_text()
    activity = (APP / "ClarityLinkDisplayActivity.java").read_text()
    gate = (ROOT / "src/claritylink-renderer/android-api17/FrameDispatchGate.java").read_text()

    assert "begin(long generation, IBinder viewSink)" in client
    assert "data.writeStrongBinder(viewSink)" in client
    assert "FrameIpcProtocol.PIXEL_FORMAT_RGBA_8888" in client
    assert "expectedRgbaBytes" in protocol
    assert "forwardToViewSink(state, identity" in service
    assert "state.compositor.accept(identity.streamGeneration" in service
    assert "IClarityLinkViewFrameSink" in service
    assert "FrameIpcProtocol.VIEW_FRAME" in sink
    assert "FrameIpcProtocol.VIEW_WARNING" in sink
    assert "dispatchGate.mayDispatch(frameGeneration, dispatchEpoch)" in sink
    assert "target.setWarningVisible(warningGeneration, visible)" in sink
    assert "warningEpoch" in gate and "capturedEpoch == warningEpoch" in gate
    assert "Binder.getCallingUid() != Process.myUid()" in sink
    assert "timestampNs <= lastTimestampNs" in sink
    assert "static final int MAX_QUEUED_FRAMES = 3" in sink
    assert "queuedFrames.incrementAndGet() > MAX_QUEUED_FRAMES" in sink
    assert "interface DispatchProbe" in sink
    assert "CountDownLatch" in sink and "handlerEntered" in sink and "releaseHandler" in sink
    assert "ui.post(new Runnable()" in sink
    assert "target.enqueue(frame, frameGeneration, frameId, dispatchEpoch)" in sink
    assert "!state.compositor.warningVisible()" in service
    assert "timestampNs > state.compositor.lastTimestampNs()" in service
    assert "forwardWarningToViewSink" in service
    assert service.index("!state.compositor.warningVisible()") < service.index("forwardToViewSink(state, identity")
    assert "BINDER_FRAME_DRAWN_ON_PRESENTATION_VIEW" in activity
    assert "SYNTHETIC_FRAME_DRAWN_ON_PRESENTATION_CANVAS" in activity
    assert "CLARITYLINK\\nTEST 6A\\nBINDER → VIEW\\nLAB ONLY" in activity
    assert "safeForHonda() { return false; }" in (
        ROOT / "android/src/main/java/org/claritylink/android/DisplayPolicy.java"
    ).read_text()


def test_emulator_runner_never_kills_unverified_private_adb_server():
    runner = (ROOT / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert "kill-server" not in runner
    assert "Cannot prove dedicated ADB server ownership" in runner
    assert "adb_server_owned" in runner
    assert "ISOLATED_ADB_SERVER" in runner
    assert "kill-server" not in runner
    assert "api17-binder-view-proof-$adb_port.png" in runner
    png_helper = (ROOT / "tools/normalize_api17_png.py").read_text()
    assert "adbd predates `exec-out`" in runner
    assert "binascii.crc32" in png_helper and "valid_png(data)" in png_helper
    assert "CL_R2_CONTROLLED_PROCESS_DEATH_PASS" in runner
    assert "CL_R2_UNCAUGHT_CRASH_FRAMEWORK_DIALOG_HANDLED" in runner
    assert "CrashDialogDismissTest" in runner
    assert "CL_R1_BINDER_HANDLER_VIEW_RACE_PASS" in runner


def test_diagnostic_binder_ack_restarts_draw_observation_and_sequence():
    activity = (APP / "ClarityLinkDisplayActivity.java").read_text()
    callback = activity[activity.index("private void submitDiagnosticFrame"):activity.index("private void closeDiagnosticSources")]
    assert "else awaitFrame(0, generation, expectedTimestampNs)" in callback
    assert "DIAGNOSTIC_FRAME_DRAWN counter=" in activity
    assert "submitNextSyntheticDiagnosticFrame(generation)" in activity
