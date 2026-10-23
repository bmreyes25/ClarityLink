package org.claritylink.renderer;

import android.test.InstrumentationTestCase;
import java.nio.ByteBuffer;
import java.util.Collections;
import org.claritylink.android.HondaStyleDisplayHostSimulator;

/**
 * Accepted Type111 ViewArea/SafeArea geometry is applied to the live View inside the current
 * lease. It must neither revoke the lease nor detach the View; a host viewport change does.
 */
public final class Display1RendererViewportInPlaceTest extends InstrumentationTestCase {
    public void testAcceptedGeometryIsAppliedInPlaceWithoutRevocation() throws Throwable {
        final HondaStyleDisplayHostSimulator simulator = new HondaStyleDisplayHostSimulator(
                getInstrumentation().getTargetContext());
        final HondaStyleSimulatorRendererHost host = new HondaStyleSimulatorRendererHost(simulator);
        final Display1OutputBackend backend = new Display1OutputBackend(host,
                new Display1OutputBackend.Viewport(0, 0, 800, 480), 1L);
        runTestOnUiThread(new Runnable() { public void run() { backend.attach(); } });
        final PaneLease lease = backend.paneLease();
        final ClarityLinkContentView view = backend.contentView();
        assertTrue(lease.isValid());

        final RendererViewport accepted = new RendererViewport(
                new RendererViewport.Bounds(0, 0, 640, 400),
                new RendererViewport.Bounds(10, 10, 630, 390),
                Collections.<RendererViewport.Bounds>emptyList(), RendererViewport.SYNTHETIC_TEST_ONLY);
        runTestOnUiThread(new Runnable() { public void run() { backend.setRendererViewport(accepted); } });

        assertTrue("accepted geometry must not revoke the lease", lease.isValid());
        assertSame("the live View must be kept", view, backend.contentView());
        assertTrue(simulator.hasClarityContent());
        final FrameDispatchGate gate = new FrameDispatchGate();
        assertTrue(gate.begin(7L));
        assertEquals(Display1OutputBackend.PresentStatus.PRESENTED,
                backend.submit(frame(1L), gate, 7L, gate.captureEpoch(7L)));

        // A host viewport change is a different event and does revoke.
        final RendererViewport hostChanged = new RendererViewport(
                new RendererViewport.Bounds(0, 0, 320, 200),
                Collections.<RendererViewport.Bounds>emptyList(), RendererViewport.SYNTHETIC_TEST_ONLY);
        runTestOnUiThread(new Runnable() { public void run() { host.simulateViewportChanged(hostChanged); } });
        assertFalse(lease.isValid());

        // Without a valid lease there is nothing to apply geometry to.
        final boolean[] refused = new boolean[] { false };
        runTestOnUiThread(new Runnable() { public void run() {
            try { backend.setRendererViewport(accepted); }
            catch (IllegalStateException expected) { refused[0] = true; }
        } });
        assertTrue(refused[0]);
        runTestOnUiThread(new Runnable() { public void run() { backend.close(); } });
    }

    private static DecodedFrame frame(long timestamp) {
        return new DecodedFrame(2, 2, 8, timestamp, 0, 0, 0, 2, 2, ByteBuffer.allocate(16));
    }
}
