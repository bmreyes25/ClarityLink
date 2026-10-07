package org.claritylink.android;

import android.view.Surface;

/** Narrow JNI facade. Handles are validated registry IDs, never native pointers. */
public final class NativeBridge {
    static { System.loadLibrary("claritylink_android"); }
    private NativeBridge() {}
    public static native long nativeAttachSurface(Surface surface, long generation, int stream, long token);
    public static native void nativeReleaseSurface(long surfaceHandle);
    public static native void nativeClearSurface(long surfaceHandle, long generation);
    public static native long nativeCreateReceiver(long generation, long primarySurface,
                                                    long secondarySurface, boolean explicitLabMode);
    public static native boolean nativeSetup(long receiverHandle, long generation, int primaryConnectionId,
                                             int secondaryConnectionId, boolean includeSecondary);
    /** Explicit synthetic test envelope. Production CarPlay transport never calls this method. */
    public static native boolean nativeTestIngestSyntheticPacket(long receiverHandle, long generation, byte[] packet);
    public static native void nativeDisconnect(long receiverHandle);
    public static native void nativeReleaseReceiver(long receiverHandle);
    /** Present only in explicitly built R7C2 test artifacts. */
    public static native long[] nativeDebugResourceCounts();
}
