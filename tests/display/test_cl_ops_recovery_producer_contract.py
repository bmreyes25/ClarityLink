"""CL-R12 producer contract: frame-buffer reuse, byte-identical fill, one frame in flight.

Source-level contract checks (the byte identity itself is proven by SyntheticFrameFillTest on an API 17
runtime and by a host JVM comparison against Arrays.fill). They cover the same invariants as the reuse
contract proposed in PR #75, adapted to the native-copy fill.
"""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ACTIVITY = (REPO / "android/cl-imp-03-app/java/org/claritylink/android/MessengerFramePerformanceActivity.java").read_text()
FILL = (REPO / "android/src/main/java/org/claritylink/android/SyntheticFrameFill.java").read_text()


def _between(text, start, end):
    s = text.index(start)
    return text[s:text.index(end, s)]


def test_one_buffer_is_reused_and_filled_only_by_the_sender():
    assert "private final byte[] syntheticFramePixels = new byte[FRAME_BYTES];" in ACTIVITY
    assert "byte[] pixels = syntheticFramePixels;" in ACTIVITY
    assert ACTIVITY.count("SyntheticFrameFill.fill(") == 1
    # exactly the two reusable fields (outgoing and returned frame) allocate a frame-sized array
    assert ACTIVITY.count("new byte[FRAME_BYTES]") == 2
    assert ACTIVITY.count("private final byte[]") >= 2
    send = _between(ACTIVITY, "private void sendSyntheticFrame", "private void onReply")
    assert "SyntheticFrameFill.fill(pixels, marker);" in send


def test_the_pixel_oracle_and_the_workload_definition_are_unchanged():
    assert "mismatch = !Arrays.equals(expectedPixels, result);" in ACTIVITY
    assert "FRAME_INTERVAL_NS = 1000000000L / 30L" in ACTIVITY
    assert "WIDTH = 800" in ACTIVITY and "HEIGHT = 480" in ACTIVITY


def test_the_next_frame_waits_until_the_current_reply_has_been_compared_and_released():
    offer = _between(ACTIVITY, "private void offerTick()", "private void sendSyntheticFrame")
    assert "if (inFlight || remote == null)" in offer and "maxInFlight = 1;" in offer
    release = _between(ACTIVITY, "private void releaseActiveFrame", "private void captureHostStats")
    assert "inFlight = false;" in release and "activePixels = null;" in release
    # the comparison runs on the sender thread that also refills the buffer, so the two are serialized
    assert ACTIVITY.index("sender.post(new Runnable()", ACTIVITY.index("final ParcelFileDescriptor returned")) < \
           ACTIVITY.index("mismatch = !Arrays.equals(expectedPixels, result);")


def test_a_stale_reply_is_rejected_before_it_can_touch_the_shared_buffer():
    reply = ACTIVITY[ACTIVITY.index("final byte[] expectedPixels = activePixels;"):]
    guard = reply[:reply.index("return;")]
    assert "activeGeneration != replyGeneration" in guard and "activeSequence != replySequence" in guard


def test_the_fill_is_a_seed_plus_native_copy_and_never_a_java_loop_over_the_frame():
    assert "System.arraycopy(destination, 0, destination, filled, chunk);" in FILL
    import re
    code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", FILL, flags=re.S))
    assert "Arrays.fill" not in code                # the comment may name it; the code must not call it
    assert "private static final int SEED = 4096;" in FILL


def test_the_returned_frame_is_read_into_one_buffer_that_is_copied_before_the_task_ends():
    assert "private final byte[] returnedFramePixels = new byte[FRAME_BYTES];" in ACTIVITY
    read = ACTIVITY[ACTIVITY.index("MessengerFrameParcel.read(returned, byteCount, returnReadTiming,"):]
    assert "returnedFramePixels);" in read[:140]
    task = read[:read.index("completedFrame")]
    # compared first, then wrapped into a DecodedFrame, whose constructor takes its own copy
    assert task.index("Arrays.equals(expectedPixels, result)") < task.index("MessengerFrameParcel.decoded(")
    renderer = (REPO / "src/claritylink-renderer/android-api17/DecodedFrame.java").read_text()
    assert "ByteBuffer.allocate((int) frameBytes)" in renderer and "owned.put(source)" in renderer
    parcel = (REPO / "android/cl-imp-03-app/java/org/claritylink/android/MessengerFrameParcel.java").read_text()
    assert "into.length == expectedBytes" in parcel
