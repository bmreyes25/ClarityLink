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
        final DecodedFrame frame = new DecodedFrame(2, 2, 12, 123L, 0, 0, 0, 2, 2, source);
        source.put(0, (byte) 0);
        int[] pixels = frame.toArgbPixels();
        require(pixels[0] == 0xffff0000, "frame owns a stable RGBA snapshot");
        require(pixels[1] == 0xff00ff00, "row stride and channel order preserved");
        require(pixels[2] == 0xff0000ff && pixels[3] == 0xffffffff, "second row pixels preserved");
        int[] reusable = new int[6];
        java.util.Arrays.fill(reusable, 0x5a5a5a5a);
        frame.toArgbPixels(reusable);
        require(reusable[0] == 0xffff0000 && reusable[1] == 0xff00ff00
                && reusable[2] == 0xff0000ff && reusable[3] == 0xffffffff,
                "reusable output preserves pixels and skips row padding");
        require(reusable[4] == 0x5a5a5a5a && reusable[5] == 0x5a5a5a5a,
                "reusable output does not touch capacity beyond the frame");
        rejects(new Runnable() { public void run() {
            frame.toArgbPixels(new int[3]);
        } }, "undersized reusable pixel buffer rejected");
        try {
            frame.writeRgbaTo(new java.io.OutputStream() {
                public void write(int value) { }
                public void write(byte[] bytes, int offset, int length) {
                    if (length > 0) bytes[offset] = 0;
                }
            });
        } catch (java.io.IOException failure) {
            throw new AssertionError("hostile output stream write: " + failure);
        }
        require(frame.toArgbPixels()[0] == 0xffff0000,
                "mutating output stream cannot alter the immutable frame snapshot");
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
