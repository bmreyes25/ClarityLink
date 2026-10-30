package org.claritylink.renderer;

import java.nio.ByteBuffer;
import android.graphics.Rect;
import java.io.IOException;
import java.io.OutputStream;

/** API 17 CPU-backed RGBA frame. Surface-backed frames are contract-only. */
public final class DecodedFrame {
    /** Bounds each owned CPU frame to 4 MiB, including row padding. */
    public static final int MAX_RGBA_BYTES = 4 * 1024 * 1024;
    private static final int WRITE_CHUNK_BYTES = 8192;
    public final int width;
    public final int height;
    public final int rowStride;
    public final long presentationTimeNs;
    public final int rotationDegrees;
    public final int cropLeft;
    public final int cropTop;
    public final int cropRight;
    public final int cropBottom;
    /** Owned tightly-bounded snapshot; never exposed, so the frame stays immutable. */
    private final byte[] pixels;

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
        ByteBuffer owned = ByteBuffer.allocate((int) frameBytes);
        owned.put(source);
        // The backing array of the private heap copy: no further copy, and it is never exposed.
        this.pixels = owned.array();
    }

    public int byteSize() { return rowStride * height; }

    /** Streams the owned RGBA snapshot in bounded chunks without exposing its backing array. */
    public void writeRgbaTo(OutputStream output) throws IOException {
        if (output == null) throw new IllegalArgumentException("output required");
        byte[] chunk = new byte[WRITE_CHUNK_BYTES];
        for (int offset = 0; offset < pixels.length; offset += WRITE_CHUNK_BYTES) {
            int count = Math.min(WRITE_CHUNK_BYTES, pixels.length - offset);
            System.arraycopy(pixels, offset, chunk, 0, count);
            output.write(chunk, 0, count);
        }
    }

    public Rect cropRect() { return new Rect(cropLeft, cropTop, cropRight, cropBottom); }

    int[] toArgbPixels() {
        int[] out = new int[width * height];
        toArgbPixels(out);
        return out;
    }

    /**
     * Converts into a caller-owned array of at least width*height ints so a converter thread can reuse
     * one array across frames. Indexing the owned byte[] directly avoids four ByteBuffer.get() calls per
     * pixel. Entries past width*height are left untouched and row padding is skipped.
     */
    void toArgbPixels(int[] out) {
        if (out == null || out.length < width * height)
            throw new IllegalArgumentException("pixel buffer too small");
        final byte[] in = pixels;
        int target = 0;
        for (int y = 0; y < height; y++) {
            int source = y * rowStride;
            final int rowEnd = source + width * 4;
            while (source < rowEnd) {
                out[target++] = ((in[source + 3] & 255) << 24) | ((in[source] & 255) << 16)
                        | ((in[source + 1] & 255) << 8) | (in[source + 2] & 255);
                source += 4;
            }
        }
    }
}
