package org.claritylink.renderer;

import java.nio.ByteBuffer;

public final class DecodedFrameTest {
    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static void rejects(Runnable action, String message) {
        boolean rejected = false;
        try { action.run(); }
        catch (IllegalArgumentException expected) { rejected = true; }
        require(rejected, message);
    }

    public static void main(String[] args) {
        ByteBuffer source = ByteBuffer.allocate(24);
        source.put(new byte[] {
                (byte) 255, 0, 0, (byte) 255, 0, (byte) 255, 0, (byte) 255, 9, 9, 9, 9,
                0, 0, (byte) 255, (byte) 255, (byte) 255, (byte) 255, (byte) 255, (byte) 255, 8, 8, 8, 8
        });
        source.flip();
        DecodedFrame frame = new DecodedFrame(2, 2, 12, 123L, 0, 0, 0, 2, 2, source);
        source.put(0, (byte) 0);
        int[] pixels = frame.toArgbPixels();
        require(pixels[0] == 0xffff0000, "frame owns a stable RGBA snapshot");
        require(pixels[1] == 0xff00ff00, "row stride and channel order preserved");
        require(pixels[2] == 0xff0000ff && pixels[3] == 0xffffffff, "second row pixels preserved");
        require(frame.byteSize() == 24, "bounded frame metadata");

        rejects(new Runnable() { public void run() {
            new DecodedFrame(1024, 1025, 4096, 1L, 0, 0, 0, 1024, 1025, ByteBuffer.allocate(0));
        } }, "frame exceeding 4 MiB aggregate budget rejected before copying");
        rejects(new Runnable() { public void run() {
            new DecodedFrame(1, 1, 4, -1L, 0, 0, 0, 1, 1, ByteBuffer.allocate(4));
        } }, "negative presentation timestamp rejected");
        rejects(new Runnable() { public void run() {
            new DecodedFrame(2, 1, 7, 1L, 0, 0, 0, 2, 1, ByteBuffer.allocate(8));
        } }, "short row stride rejected");
        System.out.println("DECODED_FRAME_CONTRACT_PASS snapshot=owned row_stride=checked max_bytes=" +
                DecodedFrame.MAX_RGBA_BYTES);
    }
}
