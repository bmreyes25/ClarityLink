package org.claritylink.android;

import android.media.MediaCodecInfo;

import org.claritylink.renderer.DecodedFrame;

import java.nio.ByteBuffer;

/**
 * Bounded conversion for the two Android YUV420 layouts implemented by the CL-R4 path.
 * Crop coordinates are exclusive right/bottom values in coded-frame coordinates.
 */
public final class Yuv420FrameAdapter {
    public static final int MAX_YUV_BYTES = 8 * 1024 * 1024;

    private Yuv420FrameAdapter() { }

    public static DecodedFrame convert(byte[] source, int sourceOffset, int sourceSize,
            int width, int height, int rowStride, int sliceHeight, int colorFormat,
            int cropLeft, int cropTop, int cropRight, int cropBottom, long timestampNs) {
        validate(source, sourceOffset, sourceSize, width, height, rowStride, sliceHeight,
                colorFormat, cropLeft, cropTop, cropRight, cropBottom, timestampNs);

        boolean semiPlanar = colorFormat == MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar;
        long yBytes = (long) rowStride * sliceHeight;
        int chromaStride = semiPlanar ? rowStride : (rowStride + 1) / 2;
        int chromaRows = (sliceHeight + 1) / 2;
        long chromaPlaneBytes = (long) chromaStride * chromaRows;
        long uBase = yBytes;
        long vBase = semiPlanar ? yBytes + 1L : yBytes + chromaPlaneBytes;

        byte[] rgba = new byte[width * height * 4];
        for (int y = 0; y < height; y++) {
            int lumaRow = sourceOffset + y * rowStride;
            int chromaRow = sourceOffset + (int) yBytes + (y / 2) * chromaStride;
            for (int x = 0; x < width; x++) {
                int yy = source[lumaRow + x] & 255;
                int chromaColumn = semiPlanar ? (x / 2) * 2 : x / 2;
                int u = source[chromaRow + chromaColumn] & 255;
                int v = source[sourceOffset + (int) vBase + (y / 2) * chromaStride + chromaColumn] & 255;
                int c = Math.max(0, yy - 16), d = u - 128, e = v - 128;
                int out = (y * width + x) * 4;
                rgba[out] = clamp((298 * c + 409 * e + 128) >> 8);
                rgba[out + 1] = clamp((298 * c - 100 * d - 208 * e + 128) >> 8);
                rgba[out + 2] = clamp((298 * c + 516 * d + 128) >> 8);
                rgba[out + 3] = (byte) 255;
            }
        }
        return new DecodedFrame(width, height, width * 4, timestampNs, 0,
                cropLeft, cropTop, cropRight, cropBottom, ByteBuffer.wrap(rgba));
    }

    private static void validate(byte[] source, int sourceOffset, int sourceSize,
            int width, int height, int rowStride, int sliceHeight, int colorFormat,
            int cropLeft, int cropTop, int cropRight, int cropBottom, long timestampNs) {
        if (source == null || sourceOffset < 0 || sourceSize < 0 || sourceSize > MAX_YUV_BYTES ||
                (long) sourceOffset + sourceSize > source.length)
            throw new IllegalArgumentException("invalid_yuv_source_bounds");
        if (width < 1 || height < 1 || width > 3840 || height > 2160 ||
                (long) width * height * 4L > DecodedFrame.MAX_RGBA_BYTES ||
                rowStride < width || rowStride > 8192 || sliceHeight < height || sliceHeight > 4096)
            throw new IllegalArgumentException("invalid_yuv_dimensions_or_stride");
        boolean semiPlanar = colorFormat == MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar;
        boolean planar = colorFormat == MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Planar;
        if (!semiPlanar && !planar) throw new IllegalArgumentException("unsupported_yuv420_color_format");
        int chromaSamples = (width + 1) / 2;
        int chromaStride = semiPlanar ? rowStride : (rowStride + 1) / 2;
        if (chromaStride < (semiPlanar ? chromaSamples * 2 : chromaSamples))
            throw new IllegalArgumentException("invalid_chroma_stride");
        if (cropLeft < 0 || cropTop < 0 || cropRight > width || cropBottom > height ||
                cropLeft >= cropRight || cropTop >= cropBottom)
            throw new IllegalArgumentException("invalid_crop_bounds");
        if (timestampNs < 0) throw new IllegalArgumentException("invalid_presentation_timestamp");

        long yBytes = (long) rowStride * sliceHeight;
        long chromaBytes = (long) chromaStride * ((sliceHeight + 1L) / 2L);
        long required = yBytes + (semiPlanar ? chromaBytes : chromaBytes * 2L);
        if (required > sourceSize || required > MAX_YUV_BYTES)
            throw new IllegalArgumentException("truncated_or_oversized_yuv_output");
    }

    private static byte clamp(int value) { return (byte) Math.max(0, Math.min(255, value)); }
}
