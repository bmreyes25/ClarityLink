from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
APP = REPO / "android/cl-imp-03-app/java/org/claritylink/android"


def test_api17_runner_can_exercise_first_order_and_same_session_view_replacement():
    runner = (REPO / "tools/run_cl_imp_03_emulator.sh").read_text()
    assert '"--cl-r5-type111-first-reattach"' in runner
    assert 'type111_first=1' in runner
    assert 'type111_reattach=1' in runner
    assert 'start_lab_activity_privileged type111_first_reattach' in runner
    assert '--ez type111_first_mode true --ez type111_reattach_test true' in runner
    assert 'start_lab_activity_privileged type111_reattach "$session_id"' in runner
    assert 'CL_R4A_TYPE111_SINK_REPLACED ' in runner
    assert 'CL_R4A_VIEW_REATTACH_PASS' in runner


def test_api17_fixture_path_connects_control_and_media_lifecycle_to_binder_view():
    activity = (APP / "ClarityLinkDisplayActivity.java").read_text()
    compositor = (APP / "CompositorService.java").read_text()
    control = (APP / "Type111ControlPlane.java").read_text()
    assert "control.registerLabCapability(activeGeneration" in activity
    assert "control.setup(secondaryIdentity)" in activity
    assert "TYPE111_CONTROL_SETUP" in compositor
    assert "control.videoConfig(controlIdentity, 64, 64)" in activity
    assert "Api17BufferH264Decoder" in activity
    assert "submitDecodedFrame(frame, binderGeneration" in activity
    assert '"suggestUI".equals(command)' in control
    assert '"showUI".equals(command)' in control
    assert '"stopUI".equals(command)' in control
    assert '"maps".equals(provider)' in control and '"waze".equals(provider)' in control
    assert '"CL_R5_API17_PRESENTATION_LIFETIME_PASS' in activity
