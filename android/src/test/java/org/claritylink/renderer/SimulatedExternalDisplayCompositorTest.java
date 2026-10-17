package org.claritylink.renderer;

public final class SimulatedExternalDisplayCompositorTest {
    public static void main(String[] args) {
        SimulatedExternalDisplayCompositor model = new SimulatedExternalDisplayCompositor();
        FrameBackpressureGate gate = new FrameBackpressureGate();
        check(gate.tryAcquire(), "first in-flight frame admitted");
        check(!gate.tryAcquire(), "second in-flight frame rejected for backpressure");
        gate.release();
        check(gate.tryAcquire(), "slot available after completion");
        gate.close();
        check(!gate.tryAcquire() && !gate.isOccupied(), "closed channel rejects and clears work");
        check(model.begin(4), "begin generation");
        check(!model.begin(4), "duplicate generation rejected");
        check(model.accept(4, 1, 2, 2, 8, 16), "bounded frame accepted");
        check(!model.accept(3, 2, 2, 2, 8, 16), "stale generation rejected");
        check(!model.accept(4, 1, 2, 2, 8, 16), "non-increasing timestamp rejected");
        check(!model.accept(4, 2, 2, 2, 8, SimulatedExternalDisplayCompositor.MAX_FRAME_BYTES + 1),
                "over-limit payload rejected");
        check(model.setWarningVisible(4, true), "warning accepted");
        check(!model.accept(4, 2, 2, 2, 8, 16), "warning preempts frames");
        check(model.latestPayloadBytes() == 0, "warning clears retained-frame accounting");
        check(model.setWarningVisible(4, false), "warning clears");
        check(model.accept(4, 2, 2, 2, 8, 16), "fresh frame accepted after warning");
        check(model.end(4), "matching end accepted");
        check(!model.end(3), "stale end rejected");
        check(model.activeGeneration() == 0 && model.latestPayloadBytes() == 0,
                "end clears session resources");
        check(!model.begin(4), "generation cannot be reused after teardown");
        check(model.begin(5), "new generation admitted");
        model.end(5);
        System.out.println("SIMULATED_COMPOSITOR_MODEL_PASS generation fencing backpressure bounds warning cleanup");
    }

    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
}
