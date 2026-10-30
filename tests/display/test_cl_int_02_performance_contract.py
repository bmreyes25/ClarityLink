import shutil
import subprocess
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
ACTIVITY = (REPO / "android/cl-imp-03-app/java/org/claritylink/android/MessengerFramePerformanceActivity.java").read_text()
PARCEL = (REPO / "android/cl-imp-03-app/java/org/claritylink/android/MessengerFrameParcel.java").read_text()
DECODED_FRAME = (REPO / "src/claritylink-renderer/android-api17/DecodedFrame.java").read_text()
CONTENT_VIEW = (REPO / "src/claritylink-renderer/android-api17/ClarityLinkContentView.java").read_text()
WORKFLOW = (REPO / ".github/workflows/cl-int-02-api17-integration.yml").read_text()
RUNNER = (REPO / "tools/run_cl_int_02_api17_ci.sh").read_text()
GATE = (REPO / "tools/check_cl_r12_perf_gate.py").read_text()


def method_body(source, signature):
    start = source.index(signature)
    return source[start:source.index("\n    }\n", start)]


# --- Activity: workload and descriptor lifetime ------------------------------------------------

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
    assert "SyntheticFrameFill.fill(pixels, marker);" in ACTIVITY
    assert "mismatch = !Arrays.equals(expectedPixels, result);" in ACTIVITY


def test_renderer_exists_before_the_producer_fd_baseline_is_taken():
    # The renderer's converter thread owns a native Looper (three descriptors on API 17) that is only
    # released when its queue is finalized. Starting it after the baseline made every run end +3.
    baseline = method_body(ACTIVITY, "private void requestBaselineStats()")
    assert "ensureRenderer();" in baseline
    assert baseline.index("ensureRenderer();") < baseline.index("producerFdBaseline = fdCount();")


def test_renderer_is_created_by_one_helper_on_both_paths():
    assert ACTIVITY.count("new Display1OutputBackend(") == 1
    helper = method_body(ACTIVITY, "private void ensureRenderer()")
    assert "if (renderer != null) return;" in helper
    assert "created.attach();" in helper
    # Assigned before attach so a failing attach is still released by closeRenderer().
    assert helper.index("renderer = created;") < helper.index("created.attach();")
    deliver = method_body(ACTIVITY, "private void completeAcceptedReply(")
    assert "ensureRenderer();" in deliver


def test_producer_descriptors_are_closed_on_every_path():
    assert "input.close();" in PARCEL
    assert "memory.close();" in PARCEL
    send = method_body(ACTIVITY, "private void sendSyntheticFrame(")
    assert send.count("close(descriptor);") >= 2  # failure path and the finally block


# --- Renderer: conversion cost and buffer reuse -------------------------------------------------

def test_conversion_does_not_read_pixels_through_a_per_byte_buffer_accessor():
    assert "in.get()" not in DECODED_FRAME
    assert "void toArgbPixels(int[] out)" in DECODED_FRAME
    assert "private final byte[] pixels;" in DECODED_FRAME


def test_content_view_reuses_one_argb_scratch_array_on_the_converter_thread():
    convert = method_body(CONTENT_VIEW, "private void convertPendingFrames()")
    assert "frame.toArgbPixels(argb);" in convert
    assert "int[] argb = frame.toArgbPixels();" not in convert
    assert "private int[] argbScratch;" in CONTENT_VIEW
    # Only the converter thread touches the scratch, so it needs no lock and dies with the View.
    assert CONTENT_VIEW.count("argbScratch") == 1 + convert.count("argbScratch")


def test_pixel_validation_and_backpressure_remain():
    assert "!Arrays.equals(expectedPixels, result)" in ACTIVITY
    assert 'throw new IOException("pixel_identity_failure")' in ACTIVITY
    assert "if (inFlight || remote == null)" in ACTIVITY
    assert "queue_high_water" in ACTIVITY


# --- Workflow and runner: unchanged gate on exact source --------------------------------------

def test_gate_thresholds_are_unchanged():
    for expected in (
        'number("delivered_fps") >= 27',
        'number("latency_p95_ms") <= 50',
        'number("latency_p99_ms") <= 100',
        'number("dropped") / max(1, number("offered")) <= 0.10',
        'number("pixel_mismatches") == 0',
        'number("transport_errors") == 0',
        'number("host_rejected") == 0',
        'number("source_fd_final") <= number("source_fd_base") + 2',
        '29 <= number("offered_fps") <= 31',
    ):
        assert expected in GATE


def test_workflow_runs_the_unmodified_gate_and_never_edits_it():
    assert "tools/check_cl_r12_perf_gate.py" in WORKFLOW
    assert "sed -i" not in WORKFLOW
    assert "perf-optimized-soak-logcat.txt" in WORKFLOW
    assert "CL_INT_02_API17_ACCEPTANCE_PASS" in WORKFLOW
    gate_step = WORKFLOW[WORKFLOW.index("Enforce candidate and soak performance gates"):]
    assert gate_step.index("check_cl_r12_perf_gate.py") < gate_step.index("CL_INT_02_API17_ACCEPTANCE_PASS")
    assert "FUNCTIONAL_PASS" in gate_step


def test_workflow_keeps_the_offered_workload_and_runs_full_scenario():
    assert "tools/build_cl_r12_renderer_ab.sh" in WORKFLOW
    assert "tools/run_cl_int_02_api17_ci.sh" in WORKFLOW
    assert "--cl-r4b-multiple-view-replacements" in WORKFLOW
    assert "CL_INT_02_TYPE110_CONTINUITY_PASS" in WORKFLOW
    assert "CL_R12_AB_REPEATS" in WORKFLOW
    for forbidden in ("target_fps", "FRAME_INTERVAL_NS", "WIDTH", "HEIGHT"):
        assert forbidden not in WORKFLOW


def test_workflow_provides_the_mandatory_instrumentation_inputs_and_exact_source_identity():
    assert "tools/build_cl_honda_111_pane_test_apk.sh" in WORKFLOW
    assert "CL_PANE_LEASE_TEST_APK=" in WORKFLOW
    assert "tools/build_cl_int_04_host_test_apk.sh" in WORKFLOW
    assert "CL_INT_04_HOST_TEST_APK=" in WORKFLOW
    assert "CL_R12_BASELINE_APK=" in WORKFLOW
    assert "CL_R12_CANDIDATE_APK=" in WORKFLOW
    assert "tools/verify_apk_dex_classes.py" in WORKFLOW
    assert "fetch-depth: 0" in WORKFLOW
    assert "tested_merge_commit=$(git rev-parse HEAD)" in WORKFLOW


def test_workflow_reports_results_even_when_an_earlier_runtime_step_fails():
    assert "if: ${{ !cancelled() }}" in WORKFLOW
    assert "if: always()" in WORKFLOW  # bounded receipt upload
    assert "retention-days: 14" in WORKFLOW


def test_every_action_is_pinned_to_a_commit():
    for line in WORKFLOW.splitlines():
        if "uses:" in line:
            ref = line.split("uses:")[1].split("#")[0].strip().split("@")[1]
            assert len(ref) == 40 and all(c in "0123456789abcdef" for c in ref), line


def test_runner_requires_both_apks_and_every_scenario_marker():
    assert "CL_R12_BASELINE_APK is required" in RUNNER
    assert "CL_R12_CANDIDATE_APK is required" in RUNNER
    for marker in (
        "CL_FACTORY_03_API17_RUNTIME_PASS",
        "CL_R12_MESSENGER_LAB_PASS",
        "stale_generation_rejected=true",
        "navigation_withdrawal=true",
        "producer_host_process_recovery=true",
        "type110_untouched=true",
        "R12B_RESULT mode=soak",
    ):
        assert marker in RUNNER
    assert 'test -f "$r12_receipt/perf-optimized-soak-logcat.txt"' in RUNNER


def test_runner_is_valid_bash():
    subprocess.run(["bash", "-n", str(REPO / "tools/run_cl_int_02_api17_ci.sh")], check=True)


# --- DecodedFrame behaviour (compiled against a stub Rect when a JDK is present) -----------------

HARNESS = r"""
package org.claritylink.renderer;

import java.io.ByteArrayOutputStream;
import java.nio.ByteBuffer;

public final class ConversionHarness {
    static int reference(byte[] bytes, int stride, int x, int y) {
        int i = y * stride + x * 4;
        int red = bytes[i] & 255, green = bytes[i + 1] & 255, blue = bytes[i + 2] & 255, alpha = bytes[i + 3] & 255;
        return (alpha << 24) | (red << 16) | (green << 8) | blue;
    }

    static DecodedFrame frame(int width, int height, int stride, byte[] bytes) {
        return new DecodedFrame(width, height, stride, 1L, 0, 0, 0, width, height, ByteBuffer.wrap(bytes));
    }

    static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) throws Exception {
        for (int[] shape : new int[][] {{3, 2, 12}, {3, 2, 20}, {5, 4, 20}, {800, 480, 3200}}) {
            int width = shape[0], height = shape[1], stride = shape[2];
            byte[] bytes = new byte[stride * height];
            for (int i = 0; i < bytes.length; i++) bytes[i] = (byte) (i * 31 + 7);
            DecodedFrame frame = frame(width, height, stride, bytes);
            int[] exact = new int[width * height];
            frame.toArgbPixels(exact);
            for (int y = 0; y < height; y++)
                for (int x = 0; x < width; x++)
                    check(exact[y * width + x] == reference(bytes, stride, x, y), "pixel " + x + "," + y);
            check(java.util.Arrays.equals(exact, frame.toArgbPixels()), "allocating form matches scratch form");

            int[] oversized = new int[width * height + 17];
            java.util.Arrays.fill(oversized, 0x5a5a5a5a);
            frame.toArgbPixels(oversized);
            for (int i = 0; i < exact.length; i++) check(oversized[i] == exact[i], "oversized scratch pixel " + i);
            for (int i = exact.length; i < oversized.length; i++) check(oversized[i] == 0x5a5a5a5a, "tail untouched");

            // A reused scratch array that held an earlier frame must not leak any of it.
            byte[] next = new byte[bytes.length];
            for (int i = 0; i < next.length; i++) next[i] = (byte) (255 - i);
            frame(width, height, stride, next).toArgbPixels(exact);
            for (int y = 0; y < height; y++)
                for (int x = 0; x < width; x++)
                    check(exact[y * width + x] == reference(next, stride, x, y), "reused scratch " + x + "," + y);

            // The frame is an owned snapshot: later writes to the source cannot change it.
            byte[] before = bytes.clone();
            java.util.Arrays.fill(bytes, (byte) 0);
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            frame.writeRgbaTo(out);
            check(java.util.Arrays.equals(before, out.toByteArray()), "snapshot bytes incl. row padding");
            check(frame.byteSize() == before.length, "byteSize");
        }
        try {
            frame(2, 2, 8, new byte[16]).toArgbPixels(new int[3]);
            check(false, "short scratch must be rejected");
        } catch (IllegalArgumentException expected) { }
        try {
            frame(2, 2, 8, new byte[16]).toArgbPixels((int[]) null);
            check(false, "null scratch must be rejected");
        } catch (IllegalArgumentException expected) { }
        System.out.println("CONVERSION_HARNESS_OK");
    }
}
"""

RECT_STUB = """
package android.graphics;
public class Rect {
    public int left, top, right, bottom;
    public Rect(int left, int top, int right, int bottom) {
        this.left = left; this.top = top; this.right = right; this.bottom = bottom;
    }
}
"""


@pytest.mark.skipif(shutil.which("javac") is None or shutil.which("java") is None, reason="JDK not available")
def test_decoded_frame_conversion_is_pixel_exact_and_safe_to_reuse(tmp_path):
    sources = tmp_path / "src"
    (sources / "android/graphics").mkdir(parents=True)
    (sources / "org/claritylink/renderer").mkdir(parents=True)
    (sources / "android/graphics/Rect.java").write_text(RECT_STUB)
    (sources / "org/claritylink/renderer/DecodedFrame.java").write_text(DECODED_FRAME)
    (sources / "org/claritylink/renderer/ConversionHarness.java").write_text(HARNESS)
    classes = tmp_path / "classes"
    classes.mkdir()
    files = [str(path) for path in sources.rglob("*.java")]
    subprocess.run(["javac", "-d", str(classes), *files], check=True, capture_output=True, text=True)
    result = subprocess.run(
        ["java", "-cp", str(classes), "org.claritylink.renderer.ConversionHarness"],
        check=True, capture_output=True, text=True,
    )
    assert "CONVERSION_HARNESS_OK" in result.stdout
