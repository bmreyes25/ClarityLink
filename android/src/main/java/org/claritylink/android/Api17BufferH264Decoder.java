package org.claritylink.android;

import android.media.MediaCodec;
import android.media.MediaCodecInfo;
import android.media.MediaFormat;
import android.util.Log;

import org.claritylink.renderer.DecodedFrame;

import java.nio.ByteBuffer;
import java.util.Arrays;

/** API17 H.264 decoder that copies supported YUV420 output buffers into bounded RGBA frames. */
public final class Api17BufferH264Decoder {
    private static final String TAG = "ClarityLinkCLIMP03";
    private static final long POLL_US = 10000L;
    private MediaCodec codec;
    private ByteBuffer[] inputBuffers;
    private ByteBuffer[] outputBuffers;
    private byte[] codecConfig;
    private int width, height, colorFormat, stride, sliceHeight;
    private int cropLeft, cropTop, cropRight, cropBottom;
    private long generation;
    private long lastQueuedPtsUs = -1L;
    private long lastOutputPtsUs = -1L;
    private boolean configPending;
    private boolean started;
    private boolean closed;

    public Api17BufferH264Decoder(int width, int height, long generation, byte[] codecConfig) {
        configure(width, height, generation, codecConfig);
    }

    /** Queues one Annex-B access unit and returns one copied output frame, or null if delayed. */
    public synchronized DecodedFrame decode(byte[] accessUnit, long presentationTimeUs,
            long frameGeneration, long timeoutMs) {
        ensureOpen();
        if (frameGeneration != generation || presentationTimeUs < 0 ||
                presentationTimeUs <= lastQueuedPtsUs)
            throw new Api17SurfaceH264Decoder.DecodeException("stale_frame_or_timestamp");
        if (accessUnit == null || accessUnit.length == 0 ||
                accessUnit.length > Api17SurfaceH264Decoder.MAX_ACCESS_UNIT_BYTES ||
                !hasAnnexBStartCode(accessUnit))
            throw new Api17SurfaceH264Decoder.DecodeException("invalid_h264_access_unit");
        if (timeoutMs < 1 || timeoutMs > 5000)
            throw new Api17SurfaceH264Decoder.DecodeException("invalid_decode_timeout");
        long deadline = System.nanoTime() + timeoutMs * 1000000L;
        try {
            if (configPending) {
                int index = awaitInput(deadline);
                ByteBuffer input = inputBuffers[index];
                input.clear();
                if (codecConfig.length > input.capacity()) {
                    codec.queueInputBuffer(index, 0, 0, 0L, 0);
                    throw new Api17SurfaceH264Decoder.DecodeException("codec_config_exceeds_input_buffer");
                }
                input.put(codecConfig);
                codec.queueInputBuffer(index, 0, codecConfig.length, 0L,
                        MediaCodec.BUFFER_FLAG_CODEC_CONFIG);
                configPending = false;
            }
            int index = awaitInput(deadline);
            ByteBuffer input = inputBuffers[index];
            input.clear();
            if (accessUnit.length > input.capacity()) {
                codec.queueInputBuffer(index, 0, 0, presentationTimeUs, 0);
                throw new Api17SurfaceH264Decoder.DecodeException("access_unit_exceeds_codec_input_buffer");
            }
            input.put(accessUnit);
            int flags = containsIdr(accessUnit) ? MediaCodec.BUFFER_FLAG_SYNC_FRAME : 0;
            codec.queueInputBuffer(index, 0, accessUnit.length, presentationTimeUs, flags);
            lastQueuedPtsUs = presentationTimeUs;

            MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();
            while (System.nanoTime() < deadline) {
                int outputIndex = codec.dequeueOutputBuffer(info, POLL_US);
                if (outputIndex >= 0) {
                    DecodedFrame result = null;
                    try {
                        if (info.size > 0) {
                            if (info.presentationTimeUs < 0 || info.presentationTimeUs <= lastOutputPtsUs ||
                                    info.presentationTimeUs > presentationTimeUs)
                                throw new Api17SurfaceH264Decoder.DecodeException("decoder_timestamp_mismatch");
                            ByteBuffer output = outputBuffers[outputIndex].duplicate();
                            long end = (long) info.offset + info.size;
                            if (info.offset < 0 || info.size < 0 || info.size > Yuv420FrameAdapter.MAX_YUV_BYTES ||
                                    end > output.capacity())
                                throw new Api17SurfaceH264Decoder.DecodeException("decoder_output_bounds_invalid");
                            output.clear();
                            output.position(info.offset);
                            output.limit((int) end);
                            byte[] yuv = new byte[info.size];
                            output.get(yuv);
                            result = convertOutput(yuv, info.presentationTimeUs);
                            lastOutputPtsUs = info.presentationTimeUs;
                        }
                    } finally { codec.releaseOutputBuffer(outputIndex, false); }
                    if (result != null) return result;
                } else if (outputIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    setOutputFormat(codec.getOutputFormat());
                    outputBuffers = codec.getOutputBuffers();
                } else if (outputIndex == MediaCodec.INFO_OUTPUT_BUFFERS_CHANGED) {
                    outputBuffers = codec.getOutputBuffers();
                    inputBuffers = codec.getInputBuffers();
                }
            }
            return null;
        } catch (Api17SurfaceH264Decoder.DecodeException failure) {
            throw failure;
        } catch (RuntimeException failure) {
            throw new Api17SurfaceH264Decoder.DecodeException("buffer_mediacodec_decode_failed", failure);
        }
    }

    /** Stops and recreates only the codec for a new size or decoder generation. */
    public synchronized void reset(int newWidth, int newHeight, long newGeneration, byte[] newConfig) {
        ensureOpen();
        if (newGeneration <= generation)
            throw new Api17SurfaceH264Decoder.DecodeException("non_monotonic_decoder_generation");
        releaseCodec();
        Log.i(TAG, "CL_R4_BUFFER_DECODER_RESET_REQUEST width=" + newWidth + " height=" +
                newHeight + " decoder_generation=" + newGeneration);
        configure(newWidth, newHeight, newGeneration, newConfig);
    }

    public synchronized void close() {
        if (closed) return;
        releaseCodec();
        if (codecConfig != null) Arrays.fill(codecConfig, (byte) 0);
        codecConfig = null;
        generation = 0L;
        closed = true;
    }

    public synchronized int colorFormat() { return colorFormat; }
    public synchronized int outputStride() { return stride; }
    public synchronized int outputSliceHeight() { return sliceHeight; }

    private void configure(int newWidth, int newHeight, long newGeneration, byte[] newConfig) {
        if (closed || newWidth < 2 || newHeight < 2 || newWidth > 1920 || newHeight > 1080 ||
                (newWidth & 1) != 0 || (newHeight & 1) != 0 || newGeneration <= 0 ||
                (long) newWidth * newHeight * 4L > DecodedFrame.MAX_RGBA_BYTES ||
                newConfig == null || newConfig.length < 8 || newConfig.length > 65536)
            throw new Api17SurfaceH264Decoder.DecodeException("invalid_buffer_decoder_configuration");
        MediaCodec candidate = null;
        try {
            MediaFormat format = MediaFormat.createVideoFormat("video/avc", newWidth, newHeight);
            format.setInteger(MediaFormat.KEY_MAX_INPUT_SIZE,
                    Api17SurfaceH264Decoder.MAX_ACCESS_UNIT_BYTES);
            candidate = MediaCodec.createDecoderByType("video/avc");
            // A null Surface requests codec-owned output ByteBuffers on API17.
            candidate.configure(format, null, null, 0);
            candidate.start();
            codec = candidate;
            inputBuffers = candidate.getInputBuffers();
            outputBuffers = candidate.getOutputBuffers();
            width = newWidth;
            height = newHeight;
            generation = newGeneration;
            codecConfig = newConfig.clone();
            lastQueuedPtsUs = -1L;
            lastOutputPtsUs = -1L;
            colorFormat = -1;
            stride = newWidth;
            sliceHeight = newHeight;
            cropLeft = 0; cropTop = 0; cropRight = newWidth; cropBottom = newHeight;
            configPending = true;
            started = true;
            Log.i(TAG, "CL_R4_BUFFER_DECODER_STARTED width=" + width + " height=" + height +
                    " generation=" + generation + " input_buffers=" + inputBuffers.length +
                    " output_buffers=" + outputBuffers.length + " surface=null");
        } catch (RuntimeException failure) {
            if (candidate != null) try { candidate.release(); } catch (RuntimeException ignored) { }
            codec = null;
            inputBuffers = null;
            outputBuffers = null;
            started = false;
            throw new Api17SurfaceH264Decoder.DecodeException("buffer_mediacodec_configuration_failed", failure);
        }
    }

    private void setOutputFormat(MediaFormat format) {
        if (!format.containsKey(MediaFormat.KEY_WIDTH) || !format.containsKey(MediaFormat.KEY_HEIGHT) ||
                !format.containsKey(MediaFormat.KEY_COLOR_FORMAT))
            throw new Api17SurfaceH264Decoder.DecodeException("api17_output_format_missing_yuv_metadata");
        int outputWidth = format.getInteger(MediaFormat.KEY_WIDTH);
        int outputHeight = format.getInteger(MediaFormat.KEY_HEIGHT);
        if (outputWidth != width || outputHeight != height)
            throw new Api17SurfaceH264Decoder.DecodeException("decoder_resolution_change_requires_reset");
        colorFormat = format.getInteger(MediaFormat.KEY_COLOR_FORMAT);
        stride = optionalInt(format, "stride", width);
        sliceHeight = optionalInt(format, "slice-height", height);
        if (stride < width || sliceHeight < height)
            throw new Api17SurfaceH264Decoder.DecodeException("invalid_yuv_stride_or_slice_height");
        // Only layouts whose plane ordering is explicitly handled below are accepted.
        if (colorFormat != MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Planar &&
                colorFormat != MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar)
            throw new Api17SurfaceH264Decoder.DecodeException("unsupported_api17_yuv420_color_format:" + colorFormat);
        readCrop(format);
        Log.i(TAG, "CL_R4_BUFFER_OUTPUT_FORMAT width=" + width + " height=" + height +
                " color_format=" + colorFormat + " stride=" + stride + " slice_height=" + sliceHeight +
                " crop=" + cropLeft + "," + cropTop + "," +
                (cropRight - 1) + "," + (cropBottom - 1));
    }

    private DecodedFrame convertOutput(byte[] data, long ptsUs) {
        if (colorFormat < 0)
            throw new Api17SurfaceH264Decoder.DecodeException("decoder_output_format_not_announced");
        if (ptsUs > Long.MAX_VALUE / 1000L)
            throw new Api17SurfaceH264Decoder.DecodeException("presentation_timestamp_overflow");
        try {
            return Yuv420FrameAdapter.convert(data, 0, data.length, width, height, stride, sliceHeight,
                    colorFormat, cropLeft, cropTop, cropRight, cropBottom, ptsUs * 1000L);
        } catch (IllegalArgumentException invalidOutput) {
            throw new Api17SurfaceH264Decoder.DecodeException("invalid_decoder_yuv_layout", invalidOutput);
        }
    }

    private void readCrop(MediaFormat format) {
        String[] keys = { "crop-left", "crop-top", "crop-right", "crop-bottom" };
        int present = 0;
        for (String key : keys) if (format.containsKey(key)) present++;
        if (present == 0) {
            cropLeft = 0; cropTop = 0; cropRight = width; cropBottom = height;
            return;
        }
        if (present != keys.length)
            throw new Api17SurfaceH264Decoder.DecodeException("incomplete_decoder_crop_metadata");
        int left = format.getInteger("crop-left");
        int top = format.getInteger("crop-top");
        int rightInclusive = format.getInteger("crop-right");
        int bottomInclusive = format.getInteger("crop-bottom");
        long rightExclusive = (long) rightInclusive + 1L;
        long bottomExclusive = (long) bottomInclusive + 1L;
        if (rightExclusive > Integer.MAX_VALUE || bottomExclusive > Integer.MAX_VALUE ||
                left < 0 || top < 0 || rightExclusive > width || bottomExclusive > height ||
                rightExclusive <= left || bottomExclusive <= top)
            throw new Api17SurfaceH264Decoder.DecodeException("invalid_decoder_crop_metadata");
        cropLeft = left; cropTop = top;
        cropRight = (int) rightExclusive; cropBottom = (int) bottomExclusive;
    }

    private static int optionalInt(MediaFormat format, String key, int fallback) {
        return format.containsKey(key) ? format.getInteger(key) : fallback;
    }
    private int awaitInput(long deadline) {
        int polls = 0;
        while (System.nanoTime() < deadline) {
            polls++;
            int index = codec.dequeueInputBuffer(POLL_US);
            if (index >= 0) return index;
        }
        Log.e(TAG, "CL_R4_BUFFER_INPUT_TIMEOUT width=" + width + " height=" + height +
                " generation=" + generation + " input_buffers=" +
                (inputBuffers == null ? -1 : inputBuffers.length) + " polls=" + polls);
        throw new Api17SurfaceH264Decoder.DecodeException("decoder_input_timeout");
    }
    private void ensureOpen() {
        if (closed || !started || codec == null)
            throw new Api17SurfaceH264Decoder.DecodeException("decoder_closed");
    }
    private void releaseCodec() {
        MediaCodec old = codec;
        codec = null; inputBuffers = null; outputBuffers = null; started = false; configPending = false;
        if (old != null) {
            try { old.stop(); } catch (RuntimeException ignored) { }
            try { old.release(); } catch (RuntimeException ignored) { }
        }
        if (codecConfig != null) Arrays.fill(codecConfig, (byte) 0);
        codecConfig = null;
    }
    private static boolean hasAnnexBStartCode(byte[] data) {
        return data.length >= 4 && data[0] == 0 && data[1] == 0 &&
                (data[2] == 1 || (data[2] == 0 && data[3] == 1));
    }
    private static boolean containsIdr(byte[] data) {
        for (int i = 0; i + 4 < data.length; i++) {
            int prefix = data[i] == 0 && data[i + 1] == 0 && data[i + 2] == 1 ? 3 :
                    (data[i] == 0 && data[i + 1] == 0 && data[i + 2] == 0 && data[i + 3] == 1 ? 4 : 0);
            if (prefix != 0 && (data[i + prefix] & 31) == 5) return true;
        }
        return false;
    }
}
