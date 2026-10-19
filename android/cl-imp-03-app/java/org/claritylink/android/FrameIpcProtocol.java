package org.claritylink.android;

/** Versioned private Binder protocol used only by the project-owned lab processes. */
final class FrameIpcProtocol {
    static final String DESCRIPTOR = "org.claritylink.android.IClarityLinkCompositor";
    // Version 3 added mandatory session/stream/output identity. Version 4 adds
    // explicit authorization bits to stream and frame-stat query replies.
    static final int VERSION = 4;
    static final int BEGIN = 1;
    static final int FRAME = 2;
    static final int END = 3;
    static final int WARNING = 4;
    static final int CHANGE_GENERATION = 5;
    static final int REGISTER_STREAM = 6;
    static final int UNREGISTER_STREAM = 7;
    static final int VIEW_FRAME = 10;
    static final int VIEW_WARNING = 11;
    static final int VIEW_CHANGE_GENERATION = 12;
    static final int TYPE111_CAPABILITY = 13;
    static final int TYPE111_SETUP = 14;
    static final int TYPE111_NAVIGATION = 15;
    static final int TYPE111_PRESENTATION = 16;
    static final int TYPE111_GEOMETRY = 17;
    static final int TYPE111_VIDEO_CONFIG = 18;
    static final int TYPE111_PARENT_TEARDOWN = 19;
    static final int FRAME_LAB_QUERY_STATS = 20;
    static final int LAB_ARM_TRANSFER_BARRIER = 21;
    static final int LAB_WAIT_TRANSFER_BARRIER = 22;
    static final int LAB_RELEASE_TRANSFER_BARRIER = 23;
    static final int LAB_WAIT_TRANSFER_FINISHED = 24;
    static final int TYPE111_REPLACE_SINK = 25;
    static final int TYPE111_QUERY_STREAM = 27;
    static final int TYPE111_DETACH_SINK = 28;
    static final int LAB_ARM_PARENT_TEARDOWN_BARRIER = 29;
    static final int LAB_WAIT_PARENT_TEARDOWN_BARRIER = 30;
    static final int LAB_WAIT_PARENT_TEARDOWN_CONTENDER = 31;
    static final int LAB_RELEASE_PARENT_TEARDOWN_BARRIER = 32;
    static final int LAB_ARM_DELAYED_SINK_DEATH_CALLBACK = 33;
    static final int LAB_FIRE_DELAYED_SINK_DEATH_CALLBACK = 34;
    static final int PARENT_OPEN_AUTHORITY = 35;
    static final int FRAME_LAB_REVOKE_PARENT_AUTHORITY = 36;
    static final int FRAME_LAB_BIND_COMPOSITOR_EPOCH = 37;
    static final int FRAME_LAB_PREPARE_OWNER_PID_REBIND = 44;
    static final int FRAME_LAB_COMPLETE_OWNER_PID_REBIND = 45;
    static final int FRAME_LAB_CANCEL_OWNER_PID_REBIND = 46;
    static final int TYPE110_PROBE_AUTHORIZE = 38;
    static final int TYPE110_PROBE_REGISTER = 39;
    static final int TYPE111_PRODUCER_AUTHORIZE = 40;
    static final int TYPE110_SINK_ADMISSION = 41;
    static final int VIEW_CLOSE = 42;
    static final int LAB_REGISTER_OWNER_DEATH_QUERY_OBSERVER = 43;
    static final int TYPE110_SINK_ADMISSION_CONSUME = 1;
    static final int FRAME_LAB_QUERY_IDENTITY = 26;
    static final int PIXEL_FORMAT_RGBA_8888 = 1;
    static final int MAX_FRAME_BYTES = 4 * 1024 * 1024;

    static int expectedRgbaBytes(int width, int height, int rowStride) {
        if (width <= 0 || height <= 0 || width > 1920 || height > 1080 ||
                rowStride < (long) width * 4L) return -1;
        long bytes = (long) rowStride * (long) height;
        return bytes > 0 && bytes <= MAX_FRAME_BYTES ? (int) bytes : -1;
    }

    private FrameIpcProtocol() { }
}
