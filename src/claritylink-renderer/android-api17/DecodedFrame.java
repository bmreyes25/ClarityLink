package org.claritylink.renderer;

import java.nio.ByteBuffer;

/** API 17 CPU-backed RGBA frame. Surface-backed frames are contract-only. */
public final class DecodedFrame {
    public final int width;
    public final int height;
    public final int rowStride;
    public final long presentationTimeNs;
    public final int rotationDegrees;
    public final int cropLeft;
    public final int cropTop;
    public final int cropRight;
    public final int cropBottom;
    private final ByteBuffer rgba;

    public DecodedFrame(int width, int height, int rowStride, long presentationTimeNs,
            int rotationDegrees, int cropLeft, int cropTop, int cropRight, int cropBottom,
            ByteBuffer rgba) {
        if (width <= 0 || height <= 0 || width > 3840 || height > 2160
                || rowStride < width * 4 || rgba == null) {
            throw new IllegalArgumentException("invalid CPU RGBA frame");
        }
        if (rotationDegrees != 0 && rotationDegrees != 90
                && rotationDegrees != 180 && rotationDegrees != 270) {
            throw new IllegalArgumentException("invalid rotation");
        }
        if (cropLeft < 0 || cropTop < 0 || cropRight > width || cropBottom > height
                || cropLeft >= cropRight || cropTop >= cropBottom) {
            throw new IllegalArgumentException("invalid crop");
        }
        if (rgba.remaining() < rowStride * height) {
            throw new IllegalArgumentException("short RGBA buffer");
        }
        this.width = width;
        this.height = height;
        this.rowStride = rowStride;
        this.presentationTimeNs = presentationTimeNs;
        this.rotationDegrees = rotationDegrees;
        this.cropLeft = cropLeft;
        this.cropTop = cropTop;
        this.cropRight = cropRight;
        this.cropBottom = cropBottom;
        this.rgba = rgba.slice();
    }

    int[] toArgbPixels() {
        int[] out = new int[width * height];
        ByteBuffer in = rgba.duplicate();
        for (int y = 0; y < height; y++) {
            in.position(y * rowStride);
            for (int x = 0; x < width; x++) {
                int red = in.get() & 255;
                int green = in.get() & 255;
                int blue = in.get() & 255;
                int alpha = in.get() & 255;
                out[y * width + x] = (alpha << 24) | (red << 16) | (green << 8) | blue;
            }
        }
        return out;
    }
}
