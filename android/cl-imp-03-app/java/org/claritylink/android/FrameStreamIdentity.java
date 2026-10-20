package org.claritylink.android;

/** Identity carried on every private laboratory Binder frame transaction. */
final class FrameStreamIdentity {
    static final int TYPE110 = 110;
    static final int TYPE111 = 111;
    static final int OUTPUT_PRIMARY_LAB = 1;
    static final int OUTPUT_SECONDARY_VIEW = 2;

    final long sessionId;
    final int streamType;
    final long connectionId;
    final long streamGeneration;
    final int outputId;

    FrameStreamIdentity(long sessionId, int streamType, long connectionId,
                        long streamGeneration, int outputId) {
        this.sessionId = sessionId;
        this.streamType = streamType;
        this.connectionId = connectionId;
        this.streamGeneration = streamGeneration;
        this.outputId = outputId;
    }

    boolean isValid() {
        return sessionId > 0 && connectionId > 0 && streamGeneration > 0 &&
                ((streamType == TYPE110 && outputId == OUTPUT_PRIMARY_LAB) ||
                 (streamType == TYPE111 && outputId == OUTPUT_SECONDARY_VIEW));
    }

    boolean sameStream(FrameStreamIdentity other) {
        return other != null && sessionId == other.sessionId &&
                streamType == other.streamType && connectionId == other.connectionId &&
                outputId == other.outputId;
    }

    boolean equals(FrameStreamIdentity other) {
        return sameStream(other) && streamGeneration == other.streamGeneration;
    }

    @Override public boolean equals(Object value) {
        return value instanceof FrameStreamIdentity && equals((FrameStreamIdentity) value);
    }

    @Override public int hashCode() {
        int result = (int) (sessionId ^ (sessionId >>> 32));
        result = 31 * result + streamType;
        result = 31 * result + (int) (connectionId ^ (connectionId >>> 32));
        result = 31 * result + (int) (streamGeneration ^ (streamGeneration >>> 32));
        result = 31 * result + outputId;
        return result;
    }

    FrameStreamIdentity withGeneration(long generation) {
        return new FrameStreamIdentity(sessionId, streamType, connectionId, generation, outputId);
    }

    String key() { return sessionId + ":" + streamType + ":" + connectionId; }
}
