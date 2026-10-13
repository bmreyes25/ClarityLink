package org.claritylink.android;

/** Versioned private Binder protocol used only by the project-owned lab processes. */
final class FrameIpcProtocol {
    static final String DESCRIPTOR = "org.claritylink.android.IClarityLinkCompositor";
    static final int VERSION = 1;
    static final int BEGIN = 1;
    static final int FRAME = 2;
    static final int END = 3;
    static final int WARNING = 4;
    static final int MAX_FRAME_BYTES = 4 * 1024 * 1024;

    private FrameIpcProtocol() { }
}
