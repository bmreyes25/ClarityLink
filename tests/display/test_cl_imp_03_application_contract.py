from pathlib import Path
import xml.etree.ElementTree as ET


REPO = Path(__file__).resolve().parents[2]
APP = REPO / "android/cl-imp-03-app"
ANDROID = "{http://schemas.android.com/apk/res/android}"


def test_emulator_manifest_targets_api17_and_requests_no_permissions():
    manifest = ET.parse(APP / "AndroidManifest.lab.xml").getroot()
    sdk = manifest.find("uses-sdk")
    assert sdk is not None
    assert sdk.get(ANDROID + "minSdkVersion") == "17"
    assert sdk.get(ANDROID + "targetSdkVersion") == "17"
    assert manifest.findall("uses-permission") == []
    app = manifest.find("application")
    assert app is not None and app.get(ANDROID + "allowBackup") == "false"


def test_future_candidate_is_disabled_and_declares_no_permissions():
    manifest = ET.parse(APP / "AndroidManifest.candidate.xml").getroot()
    app = manifest.find("application")
    assert app is not None and app.get(ANDROID + "enabled") == "false"
    activity = app.find("activity")
    assert activity is not None
    assert activity.get(ANDROID + "enabled") == "false"
    assert activity.get(ANDROID + "exported") == "false"
    assert manifest.findall("uses-permission") == []


def test_activity_is_fail_closed_outside_confirmed_emulator_lab():
    source = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    assert "PRODUCTION_HONDA_INTEGRATION_ENABLED = false" in source
    assert "private boolean isExplicitLabRequest" in source
    assert "LAB_CONFIRM.equals(extras.getString(EXTRA_CONFIRM))" in source
    assert "if (!isEmulator())" in source
    assert "permissions_requested=none" in source
    assert "onSaveInstanceState(Bundle state)" in source
    assert "Deliberately do not persist lab admission" in source


def test_surface_is_borrowed_from_presentation_and_renderer_is_released_on_lifecycle():
    source = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    assert "released_by_app=false" in source
    assert "borrowedPresentationSurface = surface" in source
    assert "old.close()" in source
    assert 'closeViewAttachmentPreservingParent("activity-pause")' in source
    assert 'closeViewAttachmentPreservingParent("activity-destroy")' in source
    assert "parent_session_preserved=true" in source
    assert "new Display1OutputBackend" in source
    host = (REPO / "android/src/main/java/org/claritylink/android/SecondaryDisplayHost.java").read_text()
    assert "HostedContentListener" in host
    assert "presentationRoot(root)" in host


def test_emulator_runner_is_restricted_to_isolated_api17_and_uninstalls_only_lab_package():
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert "--one-device CL_IMP_03_NO_PHYSICAL_USB" in runner
    assert '[ "$api:$release:$qemu" = "17:4.2.2:1" ]' in runner
    assert "install \"$apk\"" in runner
    assert 'uninstall "$package"' in runner
    assert "claritylink-disabled-candidate.apk" not in runner
    assert "am force-stop \"$package\"" in runner


def test_frame_evidence_is_canvas_draw_not_native_presentation_or_scanout():
    renderer = (REPO / "src/claritylink-renderer/android-api17/ClarityLinkContentView.java").read_text()
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    on_draw = renderer[renderer.index("@Override protected void onDraw"):renderer.index("private boolean drawBitmap")]
    draw_helper = renderer[renderer.index("private boolean drawBitmap"):renderer.index("@Override protected void onSizeChanged")]
    assert "canvas.drawBitmap(bitmap" in draw_helper
    assert on_draw.index("drawIfCurrent(gateGeneration, dispatchEpoch, action)") < on_draw.index("drawnGeneration = generation")
    assert "gateGeneration = displayedGateGeneration" in on_draw
    assert "drawBitmap(outputCanvas, outputBitmap" in on_draw
    assert "view.drawnGeneration() == generation" in activity
    assert "SYNTHETIC_FRAME_DRAWN_ON_PRESENTATION_CANVAS" in activity
    assert "CLIMP09_RENDER_GEOMETRY_PASS" in activity
    assert "CLIMP09_WARNING_RESUME_PASS" in activity
    assert "firstFramePresented(generation)" not in activity
    assert "SYNTHETIC_FRAME_DISPLAYED" not in runner
    assert "FIRST_FRAME_PRESENTED" not in runner


def test_renderer_viewport_is_synthetic_bounded_and_clips_protected_regions():
    viewport = (REPO / "src/claritylink-renderer/android-api17/RendererViewport.java").read_text()
    renderer = (REPO / "src/claritylink-renderer/android-api17/ClarityLinkContentView.java").read_text()
    assert "LOGICAL_WIDTH = 800" in viewport and "LOGICAL_HEIGHT = 480" in viewport
    assert "SYNTHETIC_TEST_ONLY" in viewport
    assert "MAX_PROTECTED_REGIONS = 32" in viewport
    assert "protectedRegions.size() > MAX_PROTECTED_REGIONS" in viewport
    assert "this(new Bounds(0, 0, LOGICAL_WIDTH, LOGICAL_HEIGHT), safeArea" in viewport
    assert "safe area must fit inside the ViewArea" in viewport
    assert "canvas.clipRect(scaled(viewArea, viewWidth, viewHeight))" in viewport
    assert "Region.Op.DIFFERENCE" in viewport
    assert "scaledSafeArea" in viewport and "scaledSafeArea" in renderer
    assert "right > LOGICAL_WIDTH" in viewport
    assert "bottom > LOGICAL_HEIGHT" in viewport
    assert "quarterTurn = rotation == 90 || rotation == 270" in renderer
    assert "canvas.rotate(rotation, centerX, centerY)" in renderer
    assert "viewport.clip(canvas, viewWidth, viewHeight)" in renderer
    assert "MAX_RGBA_BYTES" in renderer


def test_accepted_type111_geometry_is_fenced_into_live_api17_output_view():
    activity = (REPO / "android/cl-imp-03-app/java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    backend = (REPO / "src/claritylink-renderer/android-api17/Display1OutputBackend.java").read_text()
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert "accepted_view_and_safe_areas_applied_to_live_output" in activity
    assert "current.equals(identity)" in activity
    assert "expectedRenderer.setRendererViewport(viewport)" in activity
    assert "public void setRendererViewport(RendererViewport viewport)" in backend
    assert "current.setRendererViewport(viewport)" in backend
    assert "wait_for 'CL_R6_OUTPUT_GEOMETRY_APPLIED'" in runner


def test_cl_imp_09_probe_checks_crop_geometry_warning_and_fresh_resume():
    activity = (APP / "java/org/claritylink/android/ClarityLinkDisplayActivity.java").read_text()
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert "syntheticFrame(1L)" in activity
    assert "rotationDegrees" in (REPO / "src/claritylink-renderer/android-api17/DecodedFrame.java").read_text()
    assert "synthetic_viewport_clip_failed" in activity
    assert "synthetic_crop_rotation_aspect_ratio_failed" in activity
    assert "warning_preemption_did_not_clear_or_block" in activity
    assert "warning_pixels_not_cleared" in activity
    assert "matching_warning_resume_rejected" in activity
    assert "stale_generation_accepted" in activity
    assert "generation <= 1L || view.submitFrame(syntheticFrame(2L), generation - 1L)" in activity
    assert "awaitViewFrameDrawn(activeGeneration, frameTimestamp)" in activity
    assert "CL_R3_GENERATION_FRAME_PASS stream_generation=" in activity
    assert '" parent_display_generation=" + activeGeneration' in activity
    assert "awaitViewFrameDrawn(activeGeneration, resumedTimestamp)" in activity
    assert "CL_R2_CONTROLLED_PROCESS_EXIT_REQUESTED pid=" in activity
    assert "CL_R2_UNCAUGHT_CRASH_REQUESTED pid=" in activity
    assert 'stream_type=110" >/dev/null ||' in runner
    assert "CL_R4_TYPE110_AFTER_TYPE111_SINK_DEATH_PASS" in runner
    assert "CL_R2_UNCAUGHT_CRASH_FRAMEWORK_DIALOG_HANDLED" in runner
    assert 'index($NF,name ":")==1' in runner
    assert "fractional_viewport_rounding_failed" in activity
    assert "wait_for 'CLIMP09_RENDER_GEOMETRY_PASS'" in runner
    assert "wait_for 'CLIMP09_WARNING_RESUME_PASS'" in runner
