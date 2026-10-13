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
    assert "byte[]" not in client


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
