package org.claritylink.renderer;

/** Generation- and warning-epoch fence for queued UI frame work. */
public final class FrameDispatchGate {
    public interface DrawAction { void draw(); }
    private long activeGeneration;
    private long warningEpoch;
    private boolean warningVisible = true;

    public synchronized boolean begin(long generation) {
        if (generation <= 0 || activeGeneration != 0) return false;
        activeGeneration = generation;
        warningVisible = false;
        warningEpoch++;
        return true;
    }

    /** Atomically replaces an application frame generation without ending the View session. */
    public synchronized boolean replaceGeneration(long oldGeneration, long newGeneration) {
        if (oldGeneration <= 0 || oldGeneration != activeGeneration || newGeneration <= oldGeneration)
            return false;
        activeGeneration = newGeneration;
        warningVisible = false;
        warningEpoch++;
        return true;
    }

    public synchronized long captureEpoch(long generation) {
        if (generation <= 0 || generation != activeGeneration || warningVisible) return -1L;
        return warningEpoch;
    }

    public synchronized boolean mayDispatch(long generation, long capturedEpoch) {
        return generation > 0 && generation == activeGeneration && !warningVisible &&
                capturedEpoch == warningEpoch;
    }

    /**
     * Serializes the final Canvas draw with warning transitions. A warning that
     * acquires this monitor first suppresses the frame; one that arrives during
     * a draw takes effect only after that draw has completed.
     */
    public synchronized boolean drawIfCurrent(long generation, long capturedEpoch,
            DrawAction action) {
        if (action == null || !mayDispatch(generation, capturedEpoch)) return false;
        action.draw();
        return true;
    }

    public synchronized long setWarningVisible(long generation, boolean visible) {
        if (generation <= 0 || generation != activeGeneration) return -1L;
        if (warningVisible != visible) {
            warningVisible = visible;
            warningEpoch++;
        }
        return warningEpoch;
    }

    public synchronized boolean warningStateMatches(long generation, long epoch,
            boolean visible) {
        return generation > 0 && generation == activeGeneration &&
                warningEpoch == epoch && warningVisible == visible;
    }

    public synchronized boolean end(long generation) {
        if (generation <= 0 || generation != activeGeneration) return false;
        activeGeneration = 0L;
        warningVisible = true;
        warningEpoch++;
        return true;
    }
}
