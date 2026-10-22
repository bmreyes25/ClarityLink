package org.claritylink.renderer;

import android.test.InstrumentationTestCase;
import android.util.Log;
import java.io.File;
import org.claritylink.android.HondaStyleDisplayHostSimulator;

/**
 * Repeated attach/revoke cycles create and quit a converter thread (a native Looper: a pipe pair and an
 * epoll descriptor) per View on API 17. Their descriptors are released only when the quit thread's queue
 * is finalized. This test measures how many are held at the end of a revocation storm and requires that
 * every one of them is returned once collection has run. The peak is logged for the record.
 */
public final class PaneLeaseFdLifecycleTest extends InstrumentationTestCase {
    private static final int CYCLES = 60;
    private static final int PEAK_SANITY_LIMIT = 600;   // the process limit is about 1024 descriptors

    public void testRevocationStormReturnsEveryDescriptorAfterCollection() throws Throwable {
        final HondaStyleDisplayHostSimulator simulator = new HondaStyleDisplayHostSimulator(
                getInstrumentation().getTargetContext());
        final HondaStyleSimulatorRendererHost host = new HondaStyleSimulatorRendererHost(simulator);
        final Display1OutputBackend backend = new Display1OutputBackend(host,
                new Display1OutputBackend.Viewport(0, 0, 800, 480), 1L);
        settle();
        final int base = fdCount();
        int peak = base;
        for (long generation = 1; generation <= CYCLES; generation++) {
            final long next = generation;
            runTestOnUiThread(new Runnable() { public void run() { backend.attach(next); } });
            assertTrue(backend.paneLease().isValid());
            runTestOnUiThread(new Runnable() { public void run() { host.simulatePageDeselected(); } });
            assertFalse(backend.paneLease().isValid());
            runTestOnUiThread(new Runnable() { public void run() { host.simulatePageSelected(); } });
            peak = Math.max(peak, fdCount());
        }
        runTestOnUiThread(new Runnable() { public void run() { backend.close(); } });
        final int beforeSettle = fdCount();
        settle();
        final int after = fdCount();
        Log.i("ClarityLinkR12B", "PANE_FD_CYCLES cycles=" + CYCLES + " base=" + base + " peak=" + peak +
                " before_settle=" + beforeSettle + " after_settle=" + after);
        assertTrue("peak " + peak + " exceeds sanity limit", peak < PEAK_SANITY_LIMIT);
        assertTrue("descriptors not returned after collection: base=" + base + " after=" + after, after <= base + 2);
    }

    private static int fdCount() {
        String[] names = new File("/proc/self/fd").list();
        return names == null ? -1 : names.length;
    }

    private static void settle() throws InterruptedException {
        for (int pass = 0; pass < 6; pass++) {
            System.gc();
            System.runFinalization();
            Thread.sleep(200L);
        }
    }
}
