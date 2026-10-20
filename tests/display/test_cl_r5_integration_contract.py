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
    assert 'setup_order=$expected_setup_order ' in runner
    assert 'api17-initial-setup-order-$adb_port.txt' in runner
    assert 'Initial API17 session did not prove setup_order=' in runner
    assert 'type111_view_pid=\\([0-9][0-9]*\\)' in runner
    assert 'generation=\\([0-9][0-9]*\\)' in runner
    assert 'Initial setup receipt Type111 PID did not match' in runner
    assert 'Pre-death session identity did not match the initial setup receipt generation.' in runner
    assert 'initial_compositor_pid=$(printf' in runner
    assert 'compositor_pid=$initial_compositor_pid' in runner
    assert 'CL_R4A_TYPE111_SINK_REPLACED ' in runner
    assert 'CL_R4A_VIEW_REATTACH_PASS' in runner


def test_api17_fixture_path_connects_control_and_media_lifecycle_to_binder_view():
    activity = (APP / "ClarityLinkDisplayActivity.java").read_text()
    compositor = (APP / "CompositorService.java").read_text()
    control = (APP / "Type111ControlPlane.java").read_text()
    assert "control.registerLabCapability(primaryIdentity" in activity
    assert "FrameIpcClient.openParentAuthority(compositorEndpoint, primaryIdentity" in activity
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
