package org.claritylink.renderer;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.IBinder;
import android.os.Parcel;
import android.os.Process;
import android.os.SystemClock;
import android.test.InstrumentationTestCase;
import android.view.View;
import android.widget.FrameLayout;
import java.nio.ByteBuffer;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import org.claritylink.android.HondaStyleDisplayHostSimulator;

/**
 * CL-INT-04 API 17 runtime acceptance: the HOST ends a Display 1 lease by itself (expiry timer) and
 * when the producer's process dies (Binder death), with no producer callback of any kind.
 * Synthetic only: a project-owned simulator, a synthetic producer process, no Honda, vehicle or iPhone.
 */
public final class Display1HostExpiryTest extends InstrumentationTestCase {
    private static final long TTL_MS = 300L;
    private static final long WAIT_MS = 5000L;
    private static final long CONNECT_WAIT_MS = 30000L;

    private HondaStyleDisplayHostSimulator simulator;
    private HondaStyleSimulatorRendererHost host;
    private Display1OutputBackend backend;
    private Display1HostLeaseGuard guard;
    private View type110StandIn;

    @Override
    protected void setUp() throws Exception {
        super.setUp();
        try { setUpOnUiThread(); }
        catch (Exception e) { throw e; }
        catch (Throwable t) { throw new AssertionError(t); }
    }

    private void setUpOnUiThread() throws Throwable {
        final Context context = getInstrumentation().getTargetContext();
        runTestOnUiThread(new Runnable() { public void run() {
            simulator = new HondaStyleDisplayHostSimulator(context);
            host = new HondaStyleSimulatorRendererHost(simulator);
            host.simulatePageSelected();
            // Display 0 / Type110 stand-in: a project-owned view in the independent bottom layer.
            type110StandIn = new View(context);
            simulator.getBottomContentRoot().addView(type110StandIn,
                    new FrameLayout.LayoutParams(10, 10));
            backend = new Display1OutputBackend(host, new Display1OutputBackend.Viewport(0, 0, 800, 480), 1L);
            guard = new Display1HostLeaseGuard(backend, TTL_MS);
        } });
    }

    @Override
    protected void tearDown() throws Exception {
        try {
            runTestOnUiThread(new Runnable() { public void run() {
                backend.close();
                simulator.close();
            } });
        } catch (Exception e) { throw e; }
        catch (Throwable t) { throw new AssertionError(t); }
        assertEquals("no expiry timer may outlive its lease", 0, PaneLease.activeExpiryTimersForTest());
        assertEquals("close releases the host listener", 0, host.listenerCountForTest());
        super.tearDown();
    }

    // ---- expiry with no producer callbacks ----
    public void testLeaseExpiresAndDetachesWithoutAnyProducerCallback() throws Throwable {
        attach(1L);
        assertEquals(Display1OutputBackend.PresentStatus.PRESENTED, guard.submit(frame(1L)));
        assertTrue(simulator.hasClarityContent());
        final PaneLease lease = backend.paneLease();
        // From here on nothing calls the backend: no submit, no tick, no heartbeat, no close.
        assertTrue("host timer must revoke", waitUntil(new Condition() {
            public boolean holds() { return !lease.isValid(); } }));
        assertTrue(waitUntil(new Condition() {
            public boolean holds() { return !simulator.hasClarityContent(); } }));
        assertNull(backend.contentView());
        assertTrue("at most the one inert registration remains until the next attach/close",
                host.listenerCountForTest() <= 1);
        assertEquals(Display1OutputBackend.PresentStatus.LEASE_INVALID, guard.submit(frame(2L)));
        assertType110Intact();
    }

    public void testAcceptedFramesRenewTheLeaseAndSilenceEndsIt() throws Throwable {
        attach(1L);
        final PaneLease lease = backend.paneLease();
        for (int i = 1; i <= 8; i++) {
            assertEquals(Display1OutputBackend.PresentStatus.PRESENTED, guard.submit(frame(i)));
            Thread.sleep(TTL_MS / 3);
        }
        assertTrue("progress keeps the lease past one ttl", lease.isValid());
        assertTrue(waitUntil(new Condition() { public boolean holds() { return !lease.isValid(); } }));
    }

    public void testOldGenerationCannotPresentAfterExpiryAndReactivationIsNewerOnly() throws Throwable {
        attach(1L);
        final PaneLease first = backend.paneLease();
        assertTrue(waitUntil(new Condition() { public boolean holds() { return !first.isValid(); } }));
        assertAttachRejected(1L);                   // same generation: fenced
        attach(2L);                                 // newer generation: allowed
        assertTrue(backend.paneLease().isValid());
        assertNotSame(first, backend.paneLease());
        assertFalse("the expired lease never revives", first.isValid());
        assertEquals(Display1OutputBackend.PresentStatus.PRESENTED, guard.submit(frame(1L)));
    }

    public void testRepeatedAttachExpireCloseLeavesNoTimerOrOwnership() throws Throwable {
        for (long generation = 1; generation <= 12; generation++) {
            attach(generation);
            guard.submit(frame(1L));
            if ((generation & 1) == 0) {
                final PaneLease lease = backend.paneLease();
                assertTrue(waitUntil(new Condition() { public boolean holds() { return !lease.isValid(); } }));
            } else {
                runTestOnUiThread(new Runnable() { public void run() { host.simulatePageDeselected();
                    host.simulatePageSelected(); } });
            }
            assertTrue(waitUntil(new Condition() { public boolean holds() { return !simulator.hasClarityContent(); } }));
        }
        assertEquals(0, PaneLease.activeExpiryTimersForTest());
        assertTrue(host.listenerCountForTest() <= 1);
        assertType110Intact();
    }

    // ---- producer process death ----
    public void testProducerProcessKillRevokesTheLeaseAndTheHostSurvives() throws Throwable {
        final Producer producer = bindProducer();
        try {
            attach(1L);
            assertTrue(onUi(new Query() { public boolean ask() { return guard.bindProducer(producer.binder); } }));
            assertEquals(Display1OutputBackend.PresentStatus.PRESENTED, guard.submit(frame(1L)));
            final PaneLease lease = backend.paneLease();
            // Prove the lease is NOT ending through the expiry timer: keep it renewed by frames
            // from the host side while the producer process is killed with no cleanup.
            producer.kill();
            long ts = 2L;
            long deadline = SystemClock.uptimeMillis() + WAIT_MS;
            while (lease.isValid() && SystemClock.uptimeMillis() < deadline) {
                guard.submit(frame(ts++));   // renews the ttl; only Binder death can end it now
                Thread.sleep(20);
            }
            assertFalse("Binder death must revoke while frames were still renewing the ttl", lease.isValid());
            assertTrue(waitUntil(new Condition() { public boolean holds() { return !simulator.hasClarityContent(); } }));
            assertTrue("the host process outlived the producer", Process.myPid() != producer.pid);
            assertType110Intact();
        } finally {
            producer.release();
        }
    }

    public void testStaleProducerDeathCannotRevokeANewerLease() throws Throwable {
        final Producer old = bindProducer();
        try {
            attach(1L);
            assertTrue(onUi(new Query() { public boolean ask() { return guard.bindProducer(old.binder); } }));
            runTestOnUiThread(new Runnable() { public void run() { host.simulatePageDeselected();
                host.simulatePageSelected(); } });
            assertFalse(backend.paneLease().isValid());
            attach(2L);                                   // the new generation has no dead producer bound
            final PaneLease current = backend.paneLease();
            old.kill();
            old.awaitDisconnected();
            Thread.sleep(150);
            assertTrue("late death of an old producer must not touch the new lease", current.isValid());
            assertEquals(Display1OutputBackend.PresentStatus.PRESENTED, guard.submit(frame(1L)));
        } finally {
            old.release();
        }
    }

    public void testBindingAnAlreadyDeadProducerRevokesImmediately() throws Throwable {
        final Producer producer = bindProducer();
        final IBinder dead = producer.binder;
        producer.kill();
        producer.awaitDisconnected();
        producer.release();
        attach(1L);
        assertFalse(onUi(new Query() { public boolean ask() { return guard.bindProducer(dead); } }));
        assertFalse(backend.paneLease().isValid());
        assertTrue(waitUntil(new Condition() { public boolean holds() { return !simulator.hasClarityContent(); } }));
    }

    // ---- helpers ----
    private interface Condition { boolean holds(); }
    private interface Query { boolean ask(); }

    private boolean waitUntil(Condition condition) throws InterruptedException {
        long deadline = SystemClock.uptimeMillis() + WAIT_MS;
        while (SystemClock.uptimeMillis() < deadline) {
            if (condition.holds()) return true;
            Thread.sleep(10);
        }
        return condition.holds();
    }

    private boolean onUi(final Query query) throws Throwable {
        final boolean[] result = new boolean[1];
        runTestOnUiThread(new Runnable() { public void run() { result[0] = query.ask(); } });
        return result[0];
    }

    private void attach(final long generation) throws Throwable {
        runTestOnUiThread(new Runnable() { public void run() { guard.attach(generation); } });
    }

    private void assertAttachRejected(final long generation) throws Throwable {
        final boolean[] rejected = new boolean[1];
        runTestOnUiThread(new Runnable() { public void run() {
            try { backend.attach(generation); }
            catch (IllegalArgumentException expected) { rejected[0] = true; }
            catch (IllegalStateException expected) { rejected[0] = true; }
        } });
        assertTrue("stale generation must be refused", rejected[0]);
    }

    private void assertType110Intact() throws Throwable {
        assertTrue("Display 0 / Type110 stand-in must be untouched by Display 1 withdrawal",
                onUi(new Query() { public boolean ask() {
                    return type110StandIn.getParent() == simulator.getBottomContentRoot()
                            && !simulator.isClosed(); } }));
    }

    private static DecodedFrame frame(long timestamp) {
        return new DecodedFrame(2, 2, 8, timestamp, 0, 0, 0, 2, 2, ByteBuffer.allocate(16));
    }

    /** A bound synthetic producer in its own process. */
    private final class Producer implements ServiceConnection {
        final CountDownLatch connected = new CountDownLatch(1);
        final CountDownLatch disconnected = new CountDownLatch(1);
        volatile IBinder binder;
        volatile int pid;

        public void onServiceConnected(ComponentName name, IBinder service) {
            binder = service;
            connected.countDown();
        }
        public void onServiceDisconnected(ComponentName name) { disconnected.countDown(); }

        void kill() throws Exception {
            binder.transact(ProducerDeathService.TX_DIE, Parcel.obtain(), null, IBinder.FLAG_ONEWAY);
        }
        void awaitDisconnected() throws InterruptedException {
            assertTrue("producer process must die", disconnected.await(WAIT_MS, TimeUnit.MILLISECONDS));
        }
        void release() {
            try { getInstrumentation().getTargetContext().unbindService(this); }
            catch (RuntimeException alreadyUnbound) { }
        }
    }

    private Producer bindProducer() throws Exception {
        Context context = getInstrumentation().getTargetContext();
        Producer producer = new Producer();
        Intent intent = new Intent().setComponent(new ComponentName(context, ProducerDeathService.class));
        assertTrue(context.bindService(intent, producer, Context.BIND_AUTO_CREATE));
        // Android backs off restarting a service whose process was killed on purpose by an earlier
        // test (5 s, growing), so a rebind can legitimately take longer than WAIT_MS.
        assertTrue("producer service must connect",
                producer.connected.await(CONNECT_WAIT_MS, TimeUnit.MILLISECONDS));
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            producer.binder.transact(ProducerDeathService.TX_PID, data, reply, 0);
            reply.setDataPosition(0);
            producer.pid = reply.readInt();
        } finally {
            data.recycle();
            reply.recycle();
        }
        assertTrue("producer must be a separate process", producer.pid != Process.myPid());
        return producer;
    }
}
