package org.claritylink.android;

import android.media.MediaCodecInfo;
import org.claritylink.renderer.DecodedFrame;
import java.io.ByteArrayOutputStream;

/** Deterministic API17-compatible tests for YUV row/slice padding and crop adaptation. */
public final class Yuv420FrameAdapterTest {
    private static final int PLANAR = MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Planar;
    private static final int SEMIPLANAR = MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar;

    public static void main(String[] args) throws Exception {
        paddedPlanarStrideAndSliceHeight();
        paddedSemiplanarStrideAndSliceHeight();
        sourceOffsetAndNonzeroCropArePreserved();
        cropEdgesAndOddChromaAlignment();
        rejectsInvalidLayoutAndBounds();
        System.out.println("Yuv420FrameAdapterTest PASS cases=5");
    }

    private static void paddedPlanarStrideAndSliceHeight() throws Exception {
        int width = 4, height = 4, stride = 6, slice = 6;
        byte[] yuv = new byte[stride * slice + 2 * ((stride + 1) / 2) * ((slice + 1) / 2)];
        java.util.Arrays.fill(yuv, (byte) 0x55);
        for (int y = 0; y < height; y++) java.util.Arrays.fill(yuv, y * stride, y * stride + width, (byte) 81);
        int yBytes = stride * slice, chromaStride = (stride + 1) / 2, chromaBytes = chromaStride * ((slice + 1) / 2);
        for (int y = 0; y < 2; y++) {
            java.util.Arrays.fill(yuv, yBytes + y * chromaStride, yBytes + y * chromaStride + 2, (byte) 90);
            java.util.Arrays.fill(yuv, yBytes + chromaBytes + y * chromaStride,
                    yBytes + chromaBytes + y * chromaStride + 2, (byte) 240);
        }
        DecodedFrame frame = convert(yuv, width, height, stride, slice, PLANAR, 0, 0, width, height);
        int[] pixel = rgba(frame, 3, 3);
        require(pixel[0] > 230 && pixel[1] < 30 && pixel[2] < 30, "padded_planar_pixel");
        require(frame.width == width && frame.height == height, "padded_planar_dimensions");
    }

    private static void paddedSemiplanarStrideAndSliceHeight() throws Exception {
        int width = 4, height = 4, stride = 8, slice = 6;
        byte[] yuv = new byte[stride * slice + stride * ((slice + 1) / 2)];
        java.util.Arrays.fill(yuv, (byte) 0x22);
        for (int y = 0; y < height; y++) java.util.Arrays.fill(yuv, y * stride, y * stride + width, (byte) 41);
        int base = stride * slice;
        for (int y = 0; y < 2; y++) for (int x = 0; x < width; x += 2) {
            yuv[base + y * stride + x] = (byte) 240;
            yuv[base + y * stride + x + 1] = (byte) 110;
        }
        DecodedFrame frame = convert(yuv, width, height, stride, slice, SEMIPLANAR, 0, 0, width, height);
        int[] pixel = rgba(frame, 2, 2);
        require(pixel[2] > 220 && pixel[0] < 30, "padded_semiplanar_pixel");
    }

    private static void sourceOffsetAndNonzeroCropArePreserved() throws Exception {
        int width = 4, height = 4, stride = 4, slice = 4;
        byte[] data = planarSolid(width, height, stride, slice, 81, 90, 240);
        byte[] wrapped = new byte[data.length + 9];
        java.util.Arrays.fill(wrapped, (byte) 0x11);
        System.arraycopy(data, 0, wrapped, 3, data.length);
        DecodedFrame frame = Yuv420FrameAdapter.convert(wrapped, 3, data.length, width, height, stride, slice,
                PLANAR, 1, 1, 3, 4, 55L);
        require(frame.cropLeft == 1 && frame.cropTop == 1 && frame.cropRight == 3 && frame.cropBottom == 4,
                "nonzero_crop_preserved");
        require(frame.cropRight - frame.cropLeft == 2 && frame.cropBottom - frame.cropTop == 3,
                "crop_rect_dimensions");
        int[] pixel = rgba(frame, 2, 2);
        require(pixel[0] > 230 && pixel[1] < 30 && pixel[2] < 30, "source_offset_pixel");
    }

    private static void cropEdgesAndOddChromaAlignment() throws Exception {
        int width = 5, height = 3, stride = 6, slice = 4;
        int chromaStride = 3, chromaRows = 2, yBytes = stride * slice;
        byte[] yuv = new byte[yBytes + 2 * chromaStride * chromaRows];
        java.util.Arrays.fill(yuv, (byte) 16);
        for (int y = 0; y < height; y++) java.util.Arrays.fill(yuv, y * stride, y * stride + width, (byte) 81);
        int cbytes = chromaStride * chromaRows;
        java.util.Arrays.fill(yuv, yBytes, yBytes + cbytes, (byte) 90);
        java.util.Arrays.fill(yuv, yBytes + cbytes, yuv.length, (byte) 240);
        DecodedFrame frame = convert(yuv, width, height, stride, slice, PLANAR, 1, 0, 5, 2);
        require(frame.cropLeft == 1 && frame.cropRight == 5 && frame.cropBottom == 2,
                "odd_crop_edges");
        int[] pixel = rgba(frame, 4, 1);
        require(pixel[0] > 230 && pixel[1] < 30, "odd_crop_chroma");
    }

    private static void rejectsInvalidLayoutAndBounds() {
        final byte[] good = planarSolid(4, 4, 4, 4, 81, 90, 240);
        rejects(new Runnable() { public void run() { Yuv420FrameAdapter.convert(good, -1, good.length, 4, 4, 4, 4, PLANAR, 0, 0, 4, 4, 1); } }, "negative_offset");
        rejects(new Runnable() { public void run() { Yuv420FrameAdapter.convert(good, Integer.MAX_VALUE, 16, 4, 4, 4, 4, PLANAR, 0, 0, 4, 4, 1); } }, "overflowing_offset");
        rejects(new Runnable() { public void run() { Yuv420FrameAdapter.convert(good, 0, good.length - 1, 4, 4, 4, 4, PLANAR, 0, 0, 4, 4, 1); } }, "truncated_payload");
        rejects(new Runnable() { public void run() { Yuv420FrameAdapter.convert(good, 0, good.length, 4, 4, 4, 4, 999, 0, 0, 4, 4, 1); } }, "unsupported_format");
        rejects(new Runnable() { public void run() { Yuv420FrameAdapter.convert(good, 0, good.length, 4, 4, 3, 4, PLANAR, 0, 0, 4, 4, 1); } }, "short_stride");
        rejects(new Runnable() { public void run() { Yuv420FrameAdapter.convert(good, 0, good.length, Integer.MAX_VALUE, 4, 4, 4, PLANAR, 0, 0, 4, 4, 1); } }, "dimension_overflow");
        rejects(new Runnable() { public void run() { Yuv420FrameAdapter.convert(good, 0, good.length, 4, 4, 4, 4, PLANAR, 2, 0, 2, 4, 1); } }, "empty_crop");
        rejects(new Runnable() { public void run() { Yuv420FrameAdapter.convert(good, 0, good.length, 4, 4, 4, 4, PLANAR, 0, 0, 4, 4, -1); } }, "negative_timestamp");
    }

    private static DecodedFrame convert(byte[] data, int width, int height, int stride, int slice,
            int format, int left, int top, int right, int bottom) {
        return Yuv420FrameAdapter.convert(data, 0, data.length, width, height, stride, slice,
                format, left, top, right, bottom, 1L);
    }

    private static byte[] planarSolid(int width, int height, int stride, int slice, int yy, int uu, int vv) {
        int cs = (stride + 1) / 2, cr = (slice + 1) / 2;
        byte[] data = new byte[stride * slice + 2 * cs * cr];
        java.util.Arrays.fill(data, (byte) yy);
        java.util.Arrays.fill(data, stride * slice, stride * slice + cs * cr, (byte) uu);
        java.util.Arrays.fill(data, stride * slice + cs * cr, data.length, (byte) vv);
        return data;
    }

    private static int[] rgba(DecodedFrame frame, int x, int y) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream(); frame.writeRgbaTo(out);
        byte[] data = out.toByteArray(); int i = (y * frame.width + x) * 4;
        return new int[] { data[i] & 255, data[i + 1] & 255, data[i + 2] & 255, data[i + 3] & 255 };
    }

    private static void rejects(Runnable operation, String name) {
        try { operation.run(); } catch (IllegalArgumentException expected) { return; }
        throw new AssertionError("accepted_invalid_" + name);
    }
    private static void require(boolean value, String name) {
        if (!value) throw new AssertionError(name);
    }
}
