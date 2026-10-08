package org.claritylink.android;

/** Test APK-only methods. This class is absent from the production Java source set. */
final class R7C3TestBridge {
    private R7C3TestBridge() {}
    static native boolean receiveSocketFrame(long receiverHandle, long generation,
                                             String ipv4, int port, int timeoutMs, int stream);
    static native boolean pendingExceptionProbe();
    static native boolean lookupFailureProbe();
    static native int openSocketDescriptorCount();
}
