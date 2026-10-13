package org.claritylink.renderer;

import java.nio.ByteBuffer;
import android.graphics.Rect;
import java.nio.ByteOrder;
import java.io.IOException;
import java.io.OutputStream;

/** API 17 CPU-backed RGBA frame. Surface-backed frames are contract-only. */
public final class DecodedFrame {
    /** Bounds each owned CPU frame to 4 MiB, including row padding. */
    public static final int MAX_RGBA_BYTES = 4 * 1024 * 1024;
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
        long minimumRowBytes = (long) width * 4L;
        long frameBytes = (long) rowStride * (long) height;
        if (width <= 0 || height <= 0 || width > 3840 || height > 2160
                || rowStride < minimumRowBytes || rgba == null
                || frameBytes > MAX_RGBA_BYTES || frameBytes > Integer.MAX_VALUE) {
            throw new IllegalArgumentException("invalid CPU RGBA frame");
        }
        if (rotationDegrees != 0 && rotationDegrees != 90
                && rotationDegrees != 180 && rotationDegrees != 270) {
            throw new IllegalArgumentException("invalid rotation");
        }
        if (presentationTimeNs < 0) throw new IllegalArgumentException("invalid presentation timestamp");
        if (cropLeft < 0 || cropTop < 0 || cropRight > width || cropBottom > height
                || cropLeft >= cropRight || cropTop >= cropBottom) {
            throw new IllegalArgumentException("invalid crop");
        }
        if (rgba.remaining() < frameBytes) {
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
        ByteBuffer source = rgba.slice();
        source.limit((int) frameBytes);
        ByteBuffer owned = ByteBuffer.allocate((int) frameBytes).order(ByteOrder.BIG_ENDIAN);
        owned.put(source);
        owned.flip();
        this.rgba = owned.asReadOnlyBuffer();
    }

    public int byteSize() { return rowStride * height; }

    /** Streams the owned RGBA snapshot without allocating a second frame-sized array. */
    public void writeRgbaTo(OutputStream output) throws IOException {
        if (output == null) throw new IllegalArgumentException("output required");
        ByteBuffer source = rgba.duplicate();
        byte[] chunk = new byte[8192];
        while (source.hasRemaining()) {
            int count = Math.min(source.remaining(), chunk.length);
            source.get(chunk, 0, count);
            output.write(chunk, 0, count);
        }
    }

    public Rect cropRect() { return new Rect(cropLeft, cropTop, cropRight, cropBottom); }

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
