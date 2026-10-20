package org.claritylink.renderer;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/** Deterministic queue, warning-transition, and final-draw-boundary regressions. */
public final class FrameDispatchGateTest {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    private static void await(CountDownLatch latch, String message) throws InterruptedException {
        check(latch.await(5, TimeUnit.SECONDS), message);
    }

    public static void main(String[] args) throws Exception {
        final FrameDispatchGate gate = new FrameDispatchGate();
        check(gate.begin(41L), "begin generation");

        // Frame accepted and queued before warning; every queued copy has the old epoch.
        long queuedEpoch = gate.captureEpoch(41L);
        check(queuedEpoch >= 0, "frame queued before warning");
        long secondQueuedEpoch = gate.captureEpoch(41L);
        check(secondQueuedEpoch == queuedEpoch, "multiple frames share active epoch");
        long warningEpoch = gate.setWarningVisible(41L, true);
        check(warningEpoch > queuedEpoch, "warning invalidates queued epoch");
        check(!gate.mayDispatch(41L, queuedEpoch), "queued frame rejected after warning");
        check(!gate.mayDispatch(41L, secondQueuedEpoch), "all queued frames rejected after warning");
        check(gate.captureEpoch(41L) == -1L, "frame queued during warning rejected");
        check(gate.warningStateMatches(41L, warningEpoch, true), "warning callback state current");

        // Rapid clear/re-enter cannot revive a pre-warning frame.
        long clearEpoch = gate.setWarningVisible(41L, false);
        long reenterEpoch = gate.setWarningVisible(41L, true);
        check(reenterEpoch > clearEpoch, "rapid warning transition increments epoch");
        check(!gate.mayDispatch(41L, queuedEpoch), "old frame remains stale across transitions");
        check(gate.setWarningVisible(41L, false) > reenterEpoch, "warning clears");
        final long resumedEpoch = gate.captureEpoch(41L);
        check(gate.mayDispatch(41L, resumedEpoch), "fresh frame accepted after clear");

        // A warning racing the final draw is serialized at the actual Canvas boundary.
        final CountDownLatch drawEntered = new CountDownLatch(1);
        final CountDownLatch releaseDraw = new CountDownLatch(1);
        final CountDownLatch warningStarted = new CountDownLatch(1);
        final CountDownLatch warningFinished = new CountDownLatch(1);
        final AtomicBoolean drew = new AtomicBoolean(false);
        Thread drawThread = new Thread(new Runnable() {
            public void run() {
                gate.drawIfCurrent(41L, resumedEpoch, new FrameDispatchGate.DrawAction() {
                    public void draw() {
                        drew.set(true);
                        drawEntered.countDown();
                        try { await(releaseDraw, "draw release"); }
                        catch (InterruptedException failure) { throw new AssertionError(failure); }
                    }
                });
            }
        }, "controlled-frame-draw");
        Thread warningThread = new Thread(new Runnable() {
            public void run() {
                warningStarted.countDown();
                gate.setWarningVisible(41L, true);
                warningFinished.countDown();
            }
        }, "controlled-warning");
        drawThread.start();
        await(drawEntered, "draw reached visible boundary");
        warningThread.start();
        await(warningStarted, "warning transition started");
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
        while (warningThread.getState() != Thread.State.BLOCKED &&
                warningFinished.getCount() != 0 && System.nanoTime() < deadline) Thread.yield();
        check(warningThread.getState() == Thread.State.BLOCKED,
                "warning waits behind in-progress final draw");
        check(warningFinished.getCount() == 1L, "warning cannot linearize during draw");
        releaseDraw.countDown();
        await(warningFinished, "warning completes after draw boundary");
        drawThread.join(5000L);
        warningThread.join(5000L);
        check(!drawThread.isAlive() && !warningThread.isAlive(), "controlled threads terminate");
        check(drew.get(), "draw ordered before warning transition");
        check(!gate.drawIfCurrent(41L, resumedEpoch, new FrameDispatchGate.DrawAction() {
            public void draw() { throw new AssertionError("stale draw executed"); }
        }), "no stale draw after warning transition");

        // End/restart fences stale generations; producer disconnect and renderer restart are ends.
        check(gate.end(41L), "end generation");
        check(!gate.mayDispatch(41L, resumedEpoch), "end invalidates queued frame");
        check(gate.begin(42L), "renderer restart begins new generation");
        check(!gate.mayDispatch(41L, resumedEpoch), "old producer generation stays stale");
        check(gate.setWarningVisible(42L, true) >= 0L, "warning transition accepted on restarted renderer");
        check(!gate.drawIfCurrent(42L, gate.captureEpoch(42L), new FrameDispatchGate.DrawAction() {
            public void draw() { throw new AssertionError("warning-active draw executed"); }
        }), "warning-active draw suppressed");
        check(gate.end(42L), "disconnect closes restarted generation");
        System.out.println("FRAME_DISPATCH_WARNING_RACE_PASS queued=invalidated finalDraw=serialized " +
                "rapidTransitions=stale generations=isolated");
    }
}
