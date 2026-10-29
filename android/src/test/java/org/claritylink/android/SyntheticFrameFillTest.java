package org.claritylink.android;

import android.test.InstrumentationTestCase;
import java.util.Arrays;

/** Runs on the API 17 runtime: the fill must produce exactly the bytes Arrays.fill does. */
public final class SyntheticFrameFillTest extends InstrumentationTestCase {
    private static final int FRAME_BYTES = 800 * 4 * 480;

    public void testIdenticalToArraysFillForEdgeLengthsAndMarkers() {
        int[] lengths = { 0, 1, 2, 4095, 4096, 4097, 8191, 8192, 8193, 12345, 65537 };
        byte[] markers = { 0, 1, 0x7f, (byte) 0x80, (byte) 0xff, 0x55 };
        for (int length : lengths) {
            for (byte marker : markers) {
                byte[] expected = new byte[length];
                Arrays.fill(expected, marker);
                byte[] actual = new byte[length];
                Arrays.fill(actual, (byte) 0xA5);              // stale contents must be overwritten
                SyntheticFrameFill.fill(actual, marker);
                assertTrue("length " + length + " marker " + marker, Arrays.equals(expected, actual));
            }
        }
    }

    public void testFullFrameForSequenceMarkers() {
        byte[] reused = new byte[FRAME_BYTES];
        int[] sequences = { 1, 2, 127, 128, 255, 256, 257, 1000 };
        for (int sequence : sequences) {
            byte marker = (byte) (sequence & 0xff);
            byte[] expected = new byte[FRAME_BYTES];
            Arrays.fill(expected, marker);
            SyntheticFrameFill.fill(reused, marker);           // the same buffer is reused every frame
            assertTrue("sequence " + sequence, Arrays.equals(expected, reused));
        }
    }

    public void testRewritingTheBufferLeavesNoResidueFromThePreviousFrame() {
        byte[] reused = new byte[FRAME_BYTES];
        SyntheticFrameFill.fill(reused, (byte) 0x11);
        SyntheticFrameFill.fill(reused, (byte) 0x22);
        for (int i = 0; i < reused.length; i += 997) assertEquals(0x22, reused[i]);
        assertEquals(0x22, reused[reused.length - 1]);
    }

    public void testFillIsNotSlowerThanTheLoopItReplaces() {
        byte[] a = new byte[FRAME_BYTES];
        SyntheticFrameFill.fill(a, (byte) 1);                  // warm up
        Arrays.fill(a, (byte) 1);
        long start = System.nanoTime();
        for (int i = 0; i < 20; i++) SyntheticFrameFill.fill(a, (byte) i);
        long fast = System.nanoTime() - start;
        start = System.nanoTime();
        for (int i = 0; i < 20; i++) Arrays.fill(a, (byte) i);
        long loop = System.nanoTime() - start;
        android.util.Log.i("ClarityLinkR12B", "FILL_BENCH fast_ms=" + (fast / 1000000.0) + " loop_ms=" + (loop / 1000000.0));
        assertTrue("native-copy fill must not be slower than the Java loop (fast=" + fast + "ns loop=" + loop + "ns)", fast <= loop);
    }
}
