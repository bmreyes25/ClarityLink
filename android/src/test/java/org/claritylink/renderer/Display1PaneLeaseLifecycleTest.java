package org.claritylink.renderer;

import android.test.InstrumentationTestCase;
import android.graphics.SurfaceTexture;
import android.view.Surface;
import java.nio.ByteBuffer;
import java.util.Collections;
import org.claritylink.android.HondaStyleDisplayHostSimulator;

/** API 17 instrumentation acceptance matrix for the simulator-only pane lease. */
public final class Display1PaneLeaseLifecycleTest extends InstrumentationTestCase {
    public void testLeaseLifecycleTypedRejectionAndCleanup() throws Throwable {
        final Throwable[] contractFailure = new Throwable[1];
        runTestOnUiThread(new Runnable() {
            public void run() {
                try { PaneLeaseTest.main(new String[0]); }
                catch (Throwable failure) { contractFailure[0] = failure; }
            }
        });
        if (contractFailure[0] != null) throw new AssertionError(contractFailure[0]);
        final HondaStyleDisplayHostSimulator simulator = new HondaStyleDisplayHostSimulator(
                getInstrumentation().getTargetContext());
        final HondaStyleSimulatorRendererHost host = new HondaStyleSimulatorRendererHost(simulator);
        final Display1OutputBackend backend = new Display1OutputBackend(host,
                new Display1OutputBackend.Viewport(0, 0, 800, 480), 1L);
        runTestOnUiThread(new Runnable() { public void run() { backend.attach(); } });
        assertTrue(backend.paneLease().isValid());
        assertEquals(1, host.listenerCountForTest());

        runTestOnUiThread(new Runnable() { public void run() { host.simulatePageDeselected(); } });
        assertFalse(backend.paneLease().isValid());
        assertNull(backend.contentView());
        assertFalse(simulator.hasClarityContent());
        assertEquals(0, host.listenerCountForTest());
        runTestOnUiThread(new Runnable() { public void run() { host.simulatePageSelected(); } });
        assertAttachRejected(backend, 1L);
        attach(backend, 2L);

        final FrameDispatchGate gate = new FrameDispatchGate();
        assertTrue(gate.begin(22L));
        assertEquals(Display1OutputBackend.PresentStatus.PRESENTED,
                backend.submit(frame(1L, 2, 2), gate, 22L, gate.captureEpoch(22L)));
        final long queuedEpoch = gate.captureEpoch(22L);
        runTestOnUiThread(new Runnable() { public void run() { host.simulateInterruptOn(); } });
        assertFalse(backend.paneLease().isValid());
        assertFalse(gate.mayDispatch(22L, queuedEpoch));
        runTestOnUiThread(new Runnable() { public void run() { host.simulateInterruptOff(); } });
        assertFalse(simulator.hasClarityContent());
        assertAttachRejected(backend, 2L);
        attach(backend, 3L);

        runTestOnUiThread(new Runnable() { public void run() { host.simulateHostLost(); } });
        assertAttachRejected(backend, 4L);
        runTestOnUiThread(new Runnable() { public void run() { host.simulateHostRestored(false); } });
        assertAttachRejected(backend, 5L);
        runTestOnUiThread(new Runnable() { public void run() { host.simulateHostRestored(true); } });
        attach(backend, 6L);

        final RendererViewport changed = new RendererViewport(
                new RendererViewport.Bounds(0, 0, 640, 400),
                Collections.<RendererViewport.Bounds>emptyList(), RendererViewport.SYNTHETIC_TEST_ONLY);
        runTestOnUiThread(new Runnable() { public void run() { host.simulateViewportChanged(changed); } });
        assertFalse(backend.paneLease().isValid());
        attach(backend, 7L);

        boolean localViewportRejected = false;
        try {
            new RendererViewport(new RendererViewport.Bounds(0, 0, 400, 200),
                    Collections.<RendererViewport.Bounds>emptyList(), "LAYOUT_LOCAL_CANDIDATE");
        } catch (IllegalArgumentException expected) { localViewportRejected = true; }
        assertTrue("layout-local fixture must be rejected by the actual provenance guard", localViewportRejected);

        runTestOnUiThread(new Runnable() { public void run() {
            host.dispatchTestEvent(new PaneEvent(PaneEvent.Type.PAGE_DESELECTED, 1L));
        } });
        assertTrue("delayed stale callback must not revoke current lease", backend.paneLease().isValid());
        assertEquals(Display1OutputBackend.PresentStatus.MALFORMED,
                backend.submit((DecodedFrame) null));
        SurfaceTexture texture = new SurfaceTexture(0);
        Surface surface = new Surface(texture);
        assertEquals(Display1OutputBackend.PresentStatus.UNSUPPORTED_STORAGE,
                backend.submit((Object) surface));
        surface.release();
        texture.release();
        final FrameDispatchGate typedGate = new FrameDispatchGate();
        assertTrue(typedGate.begin(55L));
        final long typedEpoch = typedGate.captureEpoch(55L);
        assertEquals(Display1OutputBackend.PresentStatus.PRESENTED,
                backend.submit(frame(10L, 2, 2), typedGate, 55L, typedEpoch));
        assertEquals(Display1OutputBackend.PresentStatus.IDENTITY_MISMATCH,
                backend.submit(frame(11L, 2, 2), typedGate, 56L, typedEpoch));
        assertEquals(Display1OutputBackend.PresentStatus.STALE_SEQUENCE,
                backend.submit(frame(10L, 2, 2), typedGate, 55L, typedEpoch));
        assertEquals(Display1OutputBackend.PresentStatus.GEOMETRY,
                backend.submit(frame(12L, 801, 1), typedGate, 55L, typedEpoch));
        assertEquals(Display1OutputBackend.PresentStatus.STALE_SEQUENCE,
                backend.submit(frame(9L, 2, 2), typedGate, 55L, typedEpoch));
        assertTrue(backend.paneLease().isValid());
        runTestOnUiThread(new Runnable() { public void run() { backend.replaceGeneration(1L, 2L); } });
        assertEquals(7L, backend.paneGeneration());
        assertEquals(Display1OutputBackend.PresentStatus.PRESENTED,
                backend.submit(frame(1L, 2, 2), typedGate, 55L, typedEpoch));

        for (long generation = 8L; generation < 108L; generation++) {
            final long next = generation;
            runTestOnUiThread(new Runnable() { public void run() { host.simulatePageDeselected(); } });
            assertNull(backend.contentView());
            runTestOnUiThread(new Runnable() { public void run() { host.simulatePageSelected(); } });
            attach(backend, next);
            assertTrue(backend.paneLease().isValid());
        }
        assertEquals(1, host.listenerCountForTest());
        assertTrue(simulator.hasClarityContent());
        runTestOnUiThread(new Runnable() { public void run() { backend.close(); backend.close(); } });
        int detachCount = host.detachCallsForTest();
        assertFalse(simulator.hasClarityContent());
        assertNull(backend.contentView());
        assertEquals(0, host.listenerCountForTest());
        runTestOnUiThread(new Runnable() { public void run() {
            host.dispatchTestEvent(new PaneEvent(PaneEvent.Type.PAGE_SELECTED,
                    host.eventSequenceForTest() + 1L));
        }});
        assertEquals(detachCount, host.detachCallsForTest());
    }

    private void attach(final Display1OutputBackend backend, final long generation) throws Throwable {
        runTestOnUiThread(new Runnable() { public void run() { backend.attach(generation); } });
    }
    private void assertAttachRejected(final Display1OutputBackend backend, final long generation) throws Throwable {
        final boolean[] rejected = new boolean[] { false };
        runTestOnUiThread(new Runnable() { public void run() {
            try { backend.attach(generation); }
            catch (IllegalArgumentException expected) { rejected[0] = true; }
            catch (IllegalStateException expected) { rejected[0] = true; }
        } });
        assertTrue("attach must refuse stale generation or unavailable host", rejected[0]);
    }
    private static DecodedFrame frame(long timestamp, int width, int height) {
        int stride = width * 4;
        return new DecodedFrame(width, height, stride, timestamp, 0, 0, 0, width, height,
                ByteBuffer.allocate(stride * height));
    }
}
