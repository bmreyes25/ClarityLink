package org.claritylink.android;

/** Present only in the API17 diagnostic APK; production ARM has no JNI exports for these hooks. */
final class R7C6TestBridge {
    static final int SETUP_PRIMARY_ALLOCATED = 1;
    static final int SETUP_SECONDARY_ALLOCATED = 2;
    static final int DECODE_PRIMARY_BEFORE_POST = 3;
    static final int DECODE_SECONDARY_BEFORE_POST = 4;
    static final int SOCKET_READ_ACTIVE = 5;
    static final int SOCKET_WRITE_ACTIVE = 6;

    private R7C6TestBridge() {}
    static native boolean armCheckpoint(int checkpoint, long generation, int stream, int timeoutMs);
    static native boolean waitForCheckpoint(int checkpoint, long generation, int stream, int timeoutMs);
    static native boolean releaseCheckpoint(int checkpoint, long generation, int stream);
    static native void clearCheckpoints();
    static boolean resetForNextCase(int timeoutMs) {
        clearCheckpoints();
        return waitForCheckpoint(0, 0, 0, timeoutMs);
    }
    static boolean raceControllerIdle() { return waitForCheckpoint(0, 0, 0, 1); }
    static native void requestReceiverClose(long receiverHandle, int stream);
    static native boolean setupStream(long receiverHandle, long generation, int stream, int connection);
    static native void shutdownActiveSocket();
    static native int connectAndWrite(String ipv4, int port, long generation, int stream,
                                      byte[] bytes, int timeoutMs);
}
