package org.claritylink.android;

import android.media.MediaCodec;
import android.media.MediaFormat;
import android.view.Surface;
import java.io.ByteArrayOutputStream;
import java.util.Arrays;
import java.nio.ByteBuffer;

/**
 * API16+ MediaCodec H.264 adapter for already-authenticated, clear lab access units.
 * Surface is borrowed from its display owner and is never released by this class.
 */
public final class Api17SurfaceH264Decoder {
    public static final int MAX_ACCESS_UNIT_BYTES = 2 * 1024 * 1024;
    private static final long CODEC_POLL_US = 10000L;

    private MediaCodec codec;
    private ByteBuffer[] inputBuffers;
    private Surface surface;
    private long generation;
    private int width;
    private int height;
    private byte[] codecConfig;
    private long lastQueuedPresentationTimeUs = -1;
    private long lastOutputPresentationTimeUs = -1;
    private boolean started;
    private boolean closed;
    private boolean configurationPending;

    public Api17SurfaceH264Decoder(int width, int height, Surface surface, long generation,
                                   byte[] codecConfig) {
        configure(width, height, surface, generation, codecConfig);
    }

    /**
     * Queues one Annex-B access unit and waits for at most its first decoded output.
     * Calls are synchronous, so at most one compressed access unit is in flight; callers
     * must provide one access unit per frame. Returns 1 when output is submitted to the
     * borrowed Surface, or 0 when a codec delays output. Submission does not confirm
     * physical scanout. Multi-picture access units are outside this adapter's contract.
     */
    public synchronized int decode(byte[] accessUnit, long presentationTimeUs,
                                    long frameGeneration, long timeoutMs) {
        ensureOpen();
        if (frameGeneration != generation || presentationTimeUs < 0 ||
                presentationTimeUs <= lastQueuedPresentationTimeUs) {
            throw new DecodeException("stale_frame_or_timestamp");
        }
        if (accessUnit == null || accessUnit.length == 0 || accessUnit.length > MAX_ACCESS_UNIT_BYTES ||
                !hasAnnexBStartCode(accessUnit)) {
            throw new DecodeException("invalid_h264_access_unit");
        }
        if (timeoutMs < 1 || timeoutMs > 5000) throw new DecodeException("invalid_decode_timeout");

        long deadline = System.nanoTime() + timeoutMs * 1000000L;
        try {
            if (configurationPending) {
                int configIndex = awaitInput(deadline);
                ByteBuffer config = inputBuffers[configIndex];
                config.clear();
                if (codecConfig.length > config.capacity()) {
                    codec.queueInputBuffer(configIndex, 0, 0, 0, 0);
                    throw new DecodeException("codec_config_exceeds_input_buffer");
                }
                config.put(codecConfig);
                codec.queueInputBuffer(configIndex, 0, codecConfig.length, 0,
                        MediaCodec.BUFFER_FLAG_CODEC_CONFIG);
                configurationPending = false;
            }
            int inputIndex = awaitInput(deadline);
            ByteBuffer input = inputBuffers[inputIndex];
            input.clear();
            if (accessUnit.length > input.capacity()) {
                codec.queueInputBuffer(inputIndex, 0, 0, presentationTimeUs, 0);
                throw new DecodeException("access_unit_exceeds_codec_input_buffer");
            }
            input.put(accessUnit);
            int flags = containsNalType(accessUnit, 5) ? MediaCodec.BUFFER_FLAG_SYNC_FRAME : 0;
            codec.queueInputBuffer(inputIndex, 0, accessUnit.length, presentationTimeUs, flags);
            lastQueuedPresentationTimeUs = presentationTimeUs;
            MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();
            int rendered = 0;
            while (System.nanoTime() < deadline) {
                int outputIndex = codec.dequeueOutputBuffer(info, CODEC_POLL_US);
                if (outputIndex >= 0) {
                    boolean render = info.size > 0;
                    if (render && (info.presentationTimeUs > presentationTimeUs ||
                            info.presentationTimeUs <= lastOutputPresentationTimeUs)) {
                        try { codec.releaseOutputBuffer(outputIndex, false); }
                        catch (RuntimeException ignored) { }
                        throw new DecodeException("decoder_timestamp_mismatch");
                    }
                    codec.releaseOutputBuffer(outputIndex, render);
                    if (render) {
                        lastOutputPresentationTimeUs = info.presentationTimeUs;
                        rendered++;
                        if (rendered > 0) return rendered;
                    }
                } else if (outputIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    validateOutputFormat(codec.getOutputFormat());
                } else if (outputIndex == MediaCodec.INFO_OUTPUT_BUFFERS_CHANGED ||
                           outputIndex == MediaCodec.INFO_TRY_AGAIN_LATER) {
                    // API17 exposes codec buffers as arrays; no array replacement is needed here.
                }
            }
            return 0;
        } catch (DecodeException error) {
            throw error;
        } catch (RuntimeException error) {
            throw new DecodeException("mediacodec_decode_failed", error);
        }
    }

    /** Replaces the codec after a stream generation, size, or Surface change. */
    public synchronized void reset(int newWidth, int newHeight, Surface newSurface,
                                   long newGeneration, byte[] newCodecConfig) {
        ensureOpen();
        if (newGeneration <= generation) throw new DecodeException("non_monotonic_decoder_generation");
        releaseCodec();
        configure(newWidth, newHeight, newSurface, newGeneration, newCodecConfig);
    }

    public synchronized void close() {
        if (closed) return;
        releaseCodec();
        surface = null;
        if (codecConfig != null) Arrays.fill(codecConfig, (byte) 0);
        codecConfig = null;
        generation = 0;
        lastQueuedPresentationTimeUs = -1;
        lastOutputPresentationTimeUs = -1;
        closed = true;
    }

    private void configure(int newWidth, int newHeight, Surface newSurface, long newGeneration,
                           byte[] newCodecConfig) {
        if (closed || newWidth < 2 || newHeight < 2 || newWidth > 4096 || newHeight > 4096 ||
                (newWidth & 1) != 0 || (newHeight & 1) != 0 || newSurface == null ||
                !newSurface.isValid() || newGeneration <= 0 || !validCodecConfig(newCodecConfig)) {
            throw new DecodeException("invalid_decoder_configuration");
        }
        MediaCodec candidate = null;
        try {
            MediaFormat format = MediaFormat.createVideoFormat("video/avc", newWidth, newHeight);
            format.setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, MAX_ACCESS_UNIT_BYTES);
            candidate = MediaCodec.createDecoderByType("video/avc");
            candidate.configure(format, newSurface, null, 0);
            candidate.start();
            codec = candidate;
            inputBuffers = candidate.getInputBuffers();
            surface = newSurface;
            generation = newGeneration;
            width = newWidth;
            height = newHeight;
            lastQueuedPresentationTimeUs = -1;
            lastOutputPresentationTimeUs = -1;
            if (codecConfig != null) Arrays.fill(codecConfig, (byte) 0);
            codecConfig = newCodecConfig.clone();
            started = true;
            configurationPending = true;
        } catch (RuntimeException error) {
            if (candidate != null) {
                try { candidate.release(); } catch (RuntimeException ignored) { }
            }
            codec = null;
            inputBuffers = null;
            started = false;
            configurationPending = false;
            throw new DecodeException("mediacodec_configuration_failed", error);
        }
    }

    private int awaitInput(long deadline) {
        while (System.nanoTime() < deadline) {
            int index = codec.dequeueInputBuffer(CODEC_POLL_US);
            if (index >= 0) return index;
        }
        throw new DecodeException("decoder_input_timeout");
    }

    private void validateOutputFormat(MediaFormat format) {
        if (!format.containsKey(MediaFormat.KEY_WIDTH) || !format.containsKey(MediaFormat.KEY_HEIGHT)) {
            throw new DecodeException("decoder_output_dimensions_missing");
        }
        int outputWidth = format.getInteger(MediaFormat.KEY_WIDTH);
        int outputHeight = format.getInteger(MediaFormat.KEY_HEIGHT);
        if (outputWidth < 1 || outputHeight < 1 || outputWidth > 4096 || outputHeight > 4096) {
            throw new DecodeException("invalid_decoder_output_dimensions");
        }
        if (outputWidth != width || outputHeight != height) {
            throw new DecodeException("decoder_resolution_changed_without_reset:" +
                    outputWidth + "x" + outputHeight + " expected=" + width + "x" + height);
        }
    }

    private void ensureOpen() {
        if (closed || !started || codec == null || surface == null || !surface.isValid()) {
            throw new DecodeException("decoder_closed_or_surface_lost");
        }
    }

    private void releaseCodec() {
        MediaCodec old = codec;
        codec = null;
        inputBuffers = null;
        started = false;
        if (old == null) return;
        try { old.stop(); } catch (RuntimeException ignored) { }
        try { old.release(); } catch (RuntimeException ignored) { }
    }

    private static boolean hasAnnexBStartCode(byte[] data) {
        return data.length >= 4 && data[0] == 0 && data[1] == 0 &&
                (data[2] == 1 || (data[2] == 0 && data[3] == 1));
    }

    /** Extracts Annex-B SPS/PPS into MediaCodec's API17 csd-0 input. */
    public static byte[] extractCodecConfig(byte[] annexB) {
        if (annexB == null || annexB.length == 0 || annexB.length > MAX_ACCESS_UNIT_BYTES)
            throw new DecodeException("invalid_h264_configuration");
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        boolean sps = false, pps = false;
        int position = 0;
        while (position < annexB.length) {
            int start = findStartCode(annexB, position);
            if (start < 0) break;
            int prefix = startCodeLength(annexB, start);
            int nalStart = start + prefix;
            int next = findStartCode(annexB, nalStart);
            int end = next < 0 ? annexB.length : next;
            while (end > nalStart && annexB[end - 1] == 0) end--;
            if (end > nalStart) {
                int type = annexB[nalStart] & 31;
                if (type == 7 || type == 8) {
                    out.write(0); out.write(0); out.write(0); out.write(1);
                    out.write(annexB, nalStart, end - nalStart);
                    if (type == 7) sps = true;
                    if (type == 8) pps = true;
                }
            }
            position = end;
        }
        byte[] config = out.toByteArray();
        if (!sps || !pps || config.length > 65536)
            throw new DecodeException("h264_sps_pps_required");
        return config;
    }

    /** Extracts IDR slices from a fixture/transport access unit without parser guessing. */
    public static byte[] extractIdrAccessUnit(byte[] annexB) {
        if (annexB == null || annexB.length == 0 || annexB.length > MAX_ACCESS_UNIT_BYTES)
            throw new DecodeException("invalid_h264_access_unit");
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        int position = 0;
        while (position < annexB.length) {
            int start = findStartCode(annexB, position);
            if (start < 0) break;
            int prefix = startCodeLength(annexB, start);
            int nalStart = start + prefix;
            int next = findStartCode(annexB, nalStart);
            int end = next < 0 ? annexB.length : next;
            while (end > nalStart && annexB[end - 1] == 0) end--;
            if (end > nalStart && (annexB[nalStart] & 31) == 5) {
                out.write(0); out.write(0); out.write(0); out.write(1);
                out.write(annexB, nalStart, end - nalStart);
            }
            position = end;
        }
        byte[] idr = out.toByteArray();
        if (idr.length == 0) throw new DecodeException("h264_idr_required");
        return idr;
    }

    /** Splits the single-slice synthetic fixtures into bounded VCL access units. */
    public static byte[][] extractVclFrames(byte[] annexB) {
        if (annexB == null || annexB.length == 0 || annexB.length > MAX_ACCESS_UNIT_BYTES)
            throw new DecodeException("invalid_h264_access_unit");
        java.util.ArrayList<byte[]> frames = new java.util.ArrayList<byte[]>();
        int position = 0;
        while (position < annexB.length) {
            int start = findStartCode(annexB, position);
            if (start < 0) break;
            int nalStart = start + startCodeLength(annexB, start);
            int next = findStartCode(annexB, nalStart);
            int end = next < 0 ? annexB.length : next;
            if (end > nalStart) {
                int type = annexB[nalStart] & 31;
                if (type == 1 || type == 5) {
                    ByteArrayOutputStream frame = new ByteArrayOutputStream();
                    frame.write(0); frame.write(0); frame.write(0); frame.write(1);
                    frame.write(annexB, nalStart, end - nalStart);
                    frames.add(frame.toByteArray());
                }
            }
            position = end;
        }
        if (frames.isEmpty() || (frames.get(0)[4] & 31) != 5)
            throw new DecodeException("h264_initial_idr_required");
        return frames.toArray(new byte[frames.size()][]);
    }

    private static boolean validCodecConfig(byte[] data) {
        if (data == null || data.length < 8 || data.length > 65536) return false;
        try { return extractCodecConfig(data).length == data.length; }
        catch (DecodeException invalid) { return false; }
    }

    private static boolean containsNalType(byte[] data, int expected) {
        int position = 0;
        while (position < data.length) {
            int start = findStartCode(data, position);
            if (start < 0) return false;
            int nalStart = start + startCodeLength(data, start);
            if (nalStart < data.length && (data[nalStart] & 31) == expected) return true;
            position = nalStart;
        }
        return false;
    }

    private static int findStartCode(byte[] data, int from) {
        for (int i = Math.max(0, from); i + 3 <= data.length; i++)
            if (startCodeLength(data, i) != 0) return i;
        return -1;
    }

    private static int startCodeLength(byte[] data, int index) {
        if (index + 4 <= data.length && data[index] == 0 && data[index + 1] == 0 &&
                data[index + 2] == 0 && data[index + 3] == 1) return 4;
        if (index + 3 <= data.length && data[index] == 0 && data[index + 1] == 0 &&
                data[index + 2] == 1) return 3;
        return 0;
    }

    public static final class DecodeException extends RuntimeException {
        private static final long serialVersionUID = 1L;
        DecodeException(String code) { super(code); }
        DecodeException(String code, Throwable cause) { super(code, cause); }
    }
}
