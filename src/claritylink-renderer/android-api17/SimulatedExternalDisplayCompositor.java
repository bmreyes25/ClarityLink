package org.claritylink.renderer;

/**
 * Process-local compositor contract for the offline display lab. It owns only
 * bounded frame metadata; it never acquires Android or Honda display surfaces.
 */
public final class SimulatedExternalDisplayCompositor {
    public static final int MAX_FRAME_BYTES = DecodedFrame.MAX_RGBA_BYTES;

    private long activeGeneration;
    private long highestGeneration;
    private long lastTimestampNs = -1L;
    private long acceptedFrames;
    private int latestPayloadBytes;
    private boolean warningVisible;

    public synchronized boolean begin(long generation) {
        if (generation <= highestGeneration || activeGeneration != 0) return false;
        activeGeneration = generation;
        highestGeneration = generation;
        lastTimestampNs = -1L;
        acceptedFrames = 0L;
        latestPayloadBytes = 0;
        return true;
    }

    public synchronized boolean accept(long generation, long timestampNs,
            int width, int height, int rowStride, int payloadBytes) {
        if (generation <= 0 || generation != activeGeneration || warningVisible
                || timestampNs < 0 || timestampNs <= lastTimestampNs
                || width <= 0 || height <= 0 || width > 3840 || height > 2160
                || rowStride < (long) width * 4L
                || payloadBytes != (long) rowStride * (long) height
                || payloadBytes <= 0 || payloadBytes > MAX_FRAME_BYTES) return false;
        lastTimestampNs = timestampNs;
        acceptedFrames++;
        latestPayloadBytes = payloadBytes;
        return true;
    }

    /** Safety model: a visible higher-priority warning clears and blocks frames. */
    public synchronized boolean setWarningVisible(long generation, boolean visible) {
        if (generation <= 0 || generation != activeGeneration) return false;
        warningVisible = visible;
        if (visible) {
            lastTimestampNs = -1L;
            latestPayloadBytes = 0;
        }
        return true;
    }

    public synchronized boolean end(long generation) {
        if (generation <= 0 || generation != activeGeneration) return false;
        activeGeneration = 0L;
        lastTimestampNs = -1L;
        acceptedFrames = 0L;
        latestPayloadBytes = 0;
        warningVisible = false;
        return true;
    }

    public synchronized long activeGeneration() { return activeGeneration; }
    public synchronized long lastTimestampNs() { return lastTimestampNs; }
    public synchronized long acceptedFrames() { return acceptedFrames; }
    public synchronized int latestPayloadBytes() { return latestPayloadBytes; }
    public synchronized boolean warningVisible() { return warningVisible; }
}
