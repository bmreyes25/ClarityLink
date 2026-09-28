package org.claritylab.carplaycoexistence;

import android.app.ActivityManager;
import android.app.Notification;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.res.AssetFileDescriptor;
import android.media.MediaCodec;
import android.media.MediaCodecInfo;
import android.media.MediaCodecList;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import android.os.IBinder;
import android.os.SystemClock;
import android.util.Log;
import java.nio.ByteBuffer;

/** Foreground, no-UI API-17 diagnostic. One decoder; emits JSONL to logcat. */
public final class DecoderCoexistenceService extends Service {
    private static final String TAG = "ClarityCoexistence";
    private static final String MIME = "video/avc";
    private static final String CLIP = "avc-800x480-15fps.mp4";
    private static final int WIDTH = 800, HEIGHT = 480, FPS = 15, FRAMES = 900;
    private static final long FRAME_NS = 1_000_000_000L / FPS;
    private static final long DRAIN_LIMIT_NS = 5_000_000_000L;
    private volatile boolean cancelled;
    private boolean formatSeen;
    private long probeStartNs;
    private volatile Thread worker;
    private MediaCodec codec;
    private MediaExtractor extractor;

    @Override public IBinder onBind(Intent intent) { return null; }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? "" : intent.getStringExtra("action");
        if ("STOP".equals(action)) {
            cancelled = true;
            if (worker == null) stopSelf(startId);
            return START_NOT_STICKY;
        }
        if (!"START".equals(action)) {
            log("{\"event\":\"error\",\"message\":\"explicit START action required\"}");
            stopSelf(startId);
            return START_NOT_STICKY;
        }
        if (worker != null) {
            log("{\"event\":\"error\",\"message\":\"probe already running\"}");
            return START_NOT_STICKY;
        }
        cancelled = false;
        startForeground(71, notification());
        worker = new Thread(new Runnable() {
            @Override public void run() { runProbe(); }
        }, "clarity-coexistence-probe");
        worker.start();
        return START_NOT_STICKY;
    }

    private Notification notification() {
        Intent stop = new Intent(this, DecoderCoexistenceService.class);
        stop.putExtra("action", "STOP");
        PendingIntent pending = PendingIntent.getService(this, 71, stop, PendingIntent.FLAG_UPDATE_CURRENT);
        Notification notification = new Notification(android.R.drawable.ic_media_play,
            "Clarity decoder probe running (up to 66 seconds)", System.currentTimeMillis());
        notification.setLatestEventInfo(this, "Clarity Coexistence Probe",
            "One 800x480/15 fps decoder; tap to stop", pending);
        return notification;
    }

    private static String selectNvidiaAvc() {
        for (int i = 0; i < MediaCodecList.getCodecCount(); i++) {
            MediaCodecInfo info = MediaCodecList.getCodecInfoAt(i);
            if (info.isEncoder() || !"OMX.Nvidia.h264.decode".equalsIgnoreCase(info.getName())) continue;
            for (String type : info.getSupportedTypes())
                if (MIME.equalsIgnoreCase(type)) return info.getName();
        }
        return null;
    }

    private void runProbe() {
        long startedNs = 0;
        int submitted = 0, produced = 0;
        boolean eosOutput = false;
        String codecName = null;
        try {
            codecName = selectNvidiaAvc();
            if (codecName == null) throw new IllegalStateException("NVIDIA AVC decoder unavailable");
            extractor = new MediaExtractor();
            AssetFileDescriptor asset = getAssets().openFd(CLIP);
            try { extractor.setDataSource(asset.getFileDescriptor(), asset.getStartOffset(), asset.getLength()); }
            finally { asset.close(); }
            if (extractor.getTrackCount() != 1) throw new IllegalStateException("fixture must have one track");
            extractor.selectTrack(0);
            MediaFormat format = extractor.getTrackFormat(0);
            if (!MIME.equals(format.getString(MediaFormat.KEY_MIME)) ||
                format.getInteger(MediaFormat.KEY_WIDTH) != WIDTH ||
                format.getInteger(MediaFormat.KEY_HEIGHT) != HEIGHT)
                throw new IllegalStateException("fixture format mismatch");
            codec = MediaCodec.createByCodecName(codecName);
            codec.configure(format, null, null, 0);
            codec.start();
            startedNs = monoNs();
            probeStartNs = startedNs;
            ByteBuffer[] inputBuffers = codec.getInputBuffers();
            MediaCodec.BufferInfo outputInfo = new MediaCodec.BufferInfo();
            log("{\"event\":\"start\",\"planned_frames\":900,\"duration_ms\":60000,\"width\":800,\"height\":480,\"fps\":15,\"codec\":\"" + codecName + "\",\"mono_ns\":0}");
            logMemory("start");
            log("{\"event\":\"thermal\",\"status\":\"unavailable\",\"reason\":\"Android API 17 has no public thermal status API\"}");

            for (int frame = 0; frame < FRAMES && !cancelled; frame++) {
                long dueNs = startedNs + frame * FRAME_NS;
                while (!cancelled && monoNs() < dueNs) {
                    int output = codec.dequeueOutputBuffer(outputInfo, 0);
                    if (output >= 0) {
                        produced += consumeOutput(output, outputInfo);
                        if ((outputInfo.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) eosOutput = true;
                    } else if (output == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                        MediaFormat actual = codec.getOutputFormat();
                        recordFormat(actual);
                    }
                    SystemClock.sleep(1);
                }
                if (cancelled) break;
                int input = codec.dequeueInputBuffer(0);
                if (input < 0) {
                    log("{\"event\":\"dropped\",\"frame\":" + frame + ",\"reason\":\"no input buffer at deadline\"}");
                    throw new IllegalStateException("input buffer unavailable at frame " + frame);
                }
                long sampleTimeUs = extractor.getSampleTime();
                if (sampleTimeUs < 0) {
                    extractor.seekTo(0, MediaExtractor.SEEK_TO_CLOSEST_SYNC);
                    sampleTimeUs = extractor.getSampleTime();
                }
                ByteBuffer buffer = inputBuffers[input];
                ((java.nio.Buffer) buffer).clear();
                int size = extractor.readSampleData(buffer, 0);
                if (size < 0) throw new IllegalStateException("fixture loop read failed");
                long ptsUs = frame * (1_000_000L / FPS);
                codec.queueInputBuffer(input, 0, size, ptsUs, 0);
                extractor.advance();
                submitted++;
                log("{\"event\":\"input\",\"pts_us\":" + ptsUs + ",\"mono_ns\":" + traceNs() + "}");
                drainAvailable(outputInfo);
                if (eosOutput) throw new IllegalStateException("unexpected early decoder EOS");
            }

            if (!cancelled && submitted == FRAMES) {
                int input = codec.dequeueInputBuffer(1000);
                if (input < 0) throw new IllegalStateException("no input buffer to queue EOS");
                codec.queueInputBuffer(input, 0, 0, FRAMES * (1_000_000L / FPS), MediaCodec.BUFFER_FLAG_END_OF_STREAM);
                long drainUntil = monoNs() + DRAIN_LIMIT_NS;
                while (!cancelled && !eosOutput && monoNs() < drainUntil) {
                    int output = codec.dequeueOutputBuffer(outputInfo, 10_000);
                    if (output >= 0) {
                        produced += consumeOutput(output, outputInfo);
                        if ((outputInfo.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) eosOutput = true;
                    } else if (output == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                        MediaFormat actual = codec.getOutputFormat();
                        recordFormat(actual);
                    }
                }
            }
            if (!cancelled && !eosOutput) log("{\"event\":\"error\",\"message\":\"decoder EOS drain timed out\"}");
            logMemory("end");
            log("{\"event\":\"eos\",\"confirmed\":" + eosOutput + "}");
            log("{\"event\":\"summary\",\"submitted\":" + submitted + ",\"produced\":" + produced +
                ",\"elapsed_ms\":" + ((monoNs() - startedNs) / 1_000_000L) +
                ",\"cancelled\":" + cancelled + "}");
        } catch (Throwable error) {
            log("{\"event\":\"error\",\"message\":\"" + escape(error.getClass().getName() + ": " + error.getMessage()) + "\"}");
        } finally {
            releaseResources();
            log("{\"event\":\"cleanup\",\"released\":true}");
            stopForeground(true);
            worker = null;
            stopSelf();
        }
    }

    private int consumeOutput(int index, MediaCodec.BufferInfo info) {
        try {
            if (!formatSeen) recordFormat(codec.getOutputFormat());
            if ((info.flags & MediaCodec.BUFFER_FLAG_CODEC_CONFIG) == 0 &&
                ((info.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) == 0 || info.size > 0)) {
                log("{\"event\":\"output\",\"pts_us\":" + info.presentationTimeUs +
                    ",\"mono_ns\":" + traceNs() + "}");
                return 1;
            }
            return 0;
        } finally { codec.releaseOutputBuffer(index, false); }
    }

    private void drainAvailable(MediaCodec.BufferInfo info) {
        for (int i = 0; i < 8; i++) {
            int output = codec.dequeueOutputBuffer(info, 0);
            if (output >= 0) consumeOutput(output, info);
            else if (output == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                recordFormat(codec.getOutputFormat());
            } else break;
        }
    }

    private void recordFormat(MediaFormat format) {
        int width = format.getInteger(MediaFormat.KEY_WIDTH);
        int height = format.getInteger(MediaFormat.KEY_HEIGHT);
        formatSeen = true;
        log("{\"event\":\"format\",\"width\":" + width + ",\"height\":" + height + "}");
    }

    private void logMemory(String phase) {
        ActivityManager.MemoryInfo info = new ActivityManager.MemoryInfo();
        ((ActivityManager) getSystemService(ACTIVITY_SERVICE)).getMemoryInfo(info);
        log("{\"event\":\"metric\",\"phase\":\"" + phase + "\",\"name\":\"avail_mem_bytes\",\"value\":" + info.availMem + "}");
        log("{\"event\":\"metric\",\"phase\":\"" + phase + "\",\"name\":\"total_mem_bytes\",\"value\":" + info.totalMem + "}");
    }

    private void releaseResources() {
        if (codec != null) {
            try { codec.stop(); } catch (Throwable error) { log("{\"event\":\"cleanup_warning\",\"message\":\"codec stop\"}"); }
            try { codec.release(); } catch (Throwable ignored) { }
            codec = null;
        }
        if (extractor != null) { try { extractor.release(); } catch (Throwable ignored) { } extractor = null; }
    }

    private static String escape(String value) {
        return value == null ? "" : value.replace("\\", "\\\\").replace("\"", "'").replace("\n", " ");
    }
    // System.nanoTime is monotonic on Android and gives finer resolution than the 250 ms gate.
    private static long monoNs() { return System.nanoTime(); }
    private long traceNs() { return monoNs() - probeStartNs; }
    private static void log(String line) { Log.i(TAG, line); }

    @Override public void onDestroy() {
        cancelled = true;
        super.onDestroy();
    }
}
