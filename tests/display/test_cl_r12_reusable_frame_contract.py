from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
ACTIVITY = (REPO / "android/cl-imp-03-app/java/org/claritylink/android/MessengerFramePerformanceActivity.java").read_text()


def test_performance_harness_reuses_single_frame_storage_without_changing_oracle():
    assert "private final byte[] syntheticFramePixels = new byte[FRAME_BYTES];" in ACTIVITY
    assert "byte[] pixels = syntheticFramePixels;" in ACTIVITY
    assert "Arrays.fill(pixels, marker);" in ACTIVITY
    assert "mismatch = !Arrays.equals(expectedPixels, result);" in ACTIVITY
    assert "FRAME_INTERVAL_NS = 1000000000L / 30L" in ACTIVITY


def test_next_frame_is_backpressured_until_current_reply_finishes():
    start = ACTIVITY.index("private void offerTick()")
    end = ACTIVITY.index("private void sendSyntheticFrame", start)
    offer_tick = ACTIVITY[start:end]

    assert "if (inFlight || remote == null)" in offer_tick
    assert "maxInFlight = 1;" in offer_tick
    assert "sender.post(new Runnable()" in offer_tick
    release = ACTIVITY[ACTIVITY.index("private void releaseActiveFrame"):
                       ACTIVITY.index("private void captureHostStats")]
    assert "inFlight = false;" in release
    assert "activePixels = null;" in release
