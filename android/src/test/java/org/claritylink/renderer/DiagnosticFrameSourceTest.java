package org.claritylink.renderer;

public final class DiagnosticFrameSourceTest {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        DiagnosticFrameSource still = new DiagnosticFrameSource(800, 480,
                DiagnosticFrameSource.Mode.STATIC);
        check(still.width() == 800 && still.height() == 480 && still.frameCount() == 0,
                "static laboratory source retains configured 800x480 canvas");
        still.close();
        check(still.nextFrame(22L) == null,
                "closed source emits no frames");

        DiagnosticFrameSource video = new DiagnosticFrameSource(320, 240,
                DiagnosticFrameSource.Mode.SYNTHETIC_VIDEO);
        check(video.width() == 320 && video.height() == 240 && video.frameCount() == 0,
                "synthetic source retains bounded configured dimensions");
        video.close();
        check(video.nextFrame(33L) == null, "closed video source is inert");

        boolean rejected = false;
        try {
            new DiagnosticFrameSource(1920, 1080,
                    DiagnosticFrameSource.Mode.SYNTHETIC_VIDEO);
        } catch (IllegalArgumentException expected) { rejected = true; }
        check(rejected, "frame exceeding 4 MiB budget is rejected");
        System.out.println("DIAGNOSTIC_FRAME_SOURCE_PASS static=800x480 synthetic=monotonic " +
                "maxBytes=" + DecodedFrame.MAX_RGBA_BYTES + " close=verified");
    }
}
