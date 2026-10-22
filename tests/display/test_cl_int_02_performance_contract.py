from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
ACTIVITY = (REPO / "android/cl-imp-03-app/java/org/claritylink/android/MessengerFramePerformanceActivity.java").read_text()


def test_host_disconnect_before_timed_run_uses_failure_cleanup():
    start = ACTIVITY.index("public void onServiceDisconnected(ComponentName name)")
    end = ACTIVITY.index("\n        }\n    };", start)
    callback = ACTIVITY[start:end]
    assert 'finishWithError("unexpected_ipc_closure")' in callback
    assert "if (running) finishWithError" not in callback


def test_synthetic_frame_storage_is_reused_under_single_frame_backpressure():
    assert "private final byte[] syntheticFramePixels = new byte[FRAME_BYTES];" in ACTIVITY
    assert "byte[] pixels = syntheticFramePixels;" in ACTIVITY
    offer_start = ACTIVITY.index("private void offerTick()")
    send_start = ACTIVITY.index("private void sendSyntheticFrame", offer_start)
    offer_tick = ACTIVITY[offer_start:send_start]
    assert "if (inFlight || remote == null)" in offer_tick
    assert "maxInFlight = 1;" in offer_tick
    assert "Arrays.fill(pixels, marker);" in ACTIVITY
    assert "mismatch = !Arrays.equals(expectedPixels, result);" in ACTIVITY
