package org.claritylab.decoderprobe;

import android.app.Activity;
import android.content.res.AssetFileDescriptor;
import android.media.MediaCodec;
import android.media.MediaCodecInfo;
import android.media.MediaCodecList;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.Log;
import android.view.Surface;
import android.view.TextureView;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.nio.ByteBuffer;

/** Bounded center-screen-only, actual-frame AVC concurrency probe for API 17. */
public final class DecoderCapacityProbeActivity extends Activity {
    private static final String TAG = "ClarityDecoderProbe";
    private static final String MIME = "video/avc";
    private static final String CLIP = "avc-800x480-15fps.mp4";
    private static final int WIDTH = 800, HEIGHT = 480, EXPECTED_FRAMES = 30;
    private static final long MAX_RUN_MS = 7000;
    private TextureView firstView, secondView;
    private TextView results;
    private Button oneButton, twoButton;
    private boolean running;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        results = new TextView(this);
        results.setText("800x480 H.264, 15 fps, 2 seconds. Park before testing.");
        layout.addView(results);
        firstView = new TextureView(this);
        secondView = new TextureView(this);
        layout.addView(firstView, new LinearLayout.LayoutParams(32, 32));
        layout.addView(secondView, new LinearLayout.LayoutParams(32, 32));
        oneButton = new Button(this);
        oneButton.setText("Decode one stream");
        layout.addView(oneButton);
        twoButton = new Button(this);
        twoButton.setText("Decode two streams");
        layout.addView(twoButton);
        setContentView(layout);
        oneButton.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View view) { begin(1); }
        });
        twoButton.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View view) { begin(2); }
        });
    }

    private void begin(final int count) {
        if (running) return;
        if (!firstView.isAvailable() || (count == 2 && !secondView.isAvailable())) {
            report("Surfaces not ready; try again.");
            return;
        }
        running = true;
        oneButton.setEnabled(false);
        twoButton.setEnabled(false);
        new Thread(new Runnable() {
            @Override public void run() { runProbe(count); }
        }, "clarity-decoder-probe").start();
    }

    private static String selectCodec() {
        String fallback = null;
        for (int i = 0; i < MediaCodecList.getCodecCount(); i++) {
            MediaCodecInfo info = MediaCodecList.getCodecInfoAt(i);
            if (info.isEncoder()) continue;
            for (String type : info.getSupportedTypes()) {
                if (!MIME.equalsIgnoreCase(type)) continue;
                if ("OMX.Nvidia.h264.decode".equalsIgnoreCase(info.getName())) return info.getName();
                if (fallback == null) fallback = info.getName();
            }
        }
        return fallback;
    }

    private final class Stream {
        MediaExtractor extractor;
        MediaCodec codec;
        Surface surface;
        MediaCodec.BufferInfo info = new MediaCodec.BufferInfo();
        ByteBuffer[] inputBuffers;
        int frames, outputWidth = -1, outputHeight = -1;
        boolean inputDone, outputDone, started;

        Stream(TextureView view, String codecName) throws Exception {
            try {
                extractor = new MediaExtractor();
                AssetFileDescriptor asset = getAssets().openFd(CLIP);
                try {
                    extractor.setDataSource(asset.getFileDescriptor(), asset.getStartOffset(), asset.getLength());
                } finally {
                    asset.close();
                }
                if (extractor.getTrackCount() != 1) throw new IllegalStateException("Fixture track count");
                MediaFormat format = extractor.getTrackFormat(0);
                if (!MIME.equals(format.getString(MediaFormat.KEY_MIME)) ||
                    format.getInteger(MediaFormat.KEY_WIDTH) != WIDTH ||
                    format.getInteger(MediaFormat.KEY_HEIGHT) != HEIGHT)
                    throw new IllegalStateException("Fixture format mismatch");
                extractor.selectTrack(0);
                surface = new Surface(view.getSurfaceTexture());
                codec = MediaCodec.createByCodecName(codecName);
                codec.configure(format, surface, null, 0);
                codec.start();
                started = true;
                inputBuffers = codec.getInputBuffers();
            } catch (Exception error) {
                close();
                throw error;
            }
        }

        void tick(long elapsedMs) {
            if (!inputDone) {
                long ptsUs = extractor.getSampleTime();
                if (ptsUs < 0 || ptsUs / 1000 <= elapsedMs) {
                    int slot = codec.dequeueInputBuffer(1000);
                    if (slot >= 0) {
                        if (ptsUs < 0) {
                            codec.queueInputBuffer(slot, 0, 0, 2000000, MediaCodec.BUFFER_FLAG_END_OF_STREAM);
                            inputDone = true;
                        } else {
                            ByteBuffer buffer = inputBuffers[slot];
                            // Android 4.2 exposes Buffer.clear(): Buffer. Force the
                            // pre-Java-9 return signature instead of ByteBuffer.clear().
                            ((java.nio.Buffer) buffer).clear();
                            int size = extractor.readSampleData(buffer, 0);
                            if (size < 0) {
                                codec.queueInputBuffer(slot, 0, 0, 2000000, MediaCodec.BUFFER_FLAG_END_OF_STREAM);
                                inputDone = true;
                            } else {
                                codec.queueInputBuffer(slot, 0, size, ptsUs, 0);
                                extractor.advance();
                            }
                        }
                    }
                }
            }
            int output = codec.dequeueOutputBuffer(info, 1000);
            if (output == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                MediaFormat changed = codec.getOutputFormat();
                outputWidth = changed.getInteger(MediaFormat.KEY_WIDTH);
                outputHeight = changed.getInteger(MediaFormat.KEY_HEIGHT);
            } else if (output >= 0) {
                if (outputWidth < 0) {
                    MediaFormat changed = codec.getOutputFormat();
                    outputWidth = changed.getInteger(MediaFormat.KEY_WIDTH);
                    outputHeight = changed.getInteger(MediaFormat.KEY_HEIGHT);
                }
                if ((info.flags & MediaCodec.BUFFER_FLAG_CODEC_CONFIG) == 0 &&
                    ((info.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) == 0 || info.size > 0)) frames++;
                if ((info.flags & MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) outputDone = true;
                codec.releaseOutputBuffer(output, false);
            }
        }

        void close() {
            if (codec != null) {
                if (started) try { codec.stop(); } catch (Throwable error) { report("codec stop: " + error); }
                try { codec.release(); } catch (Throwable error) { report("codec release: " + error); }
            }
            if (extractor != null) try { extractor.release(); } catch (Throwable error) { report("extractor release: " + error); }
            if (surface != null) surface.release();
        }
    }

    private void runProbe(int count) {
        Stream first = null, second = null;
        try {
            String codecName = selectCodec();
            if (codecName == null) throw new IllegalStateException("No AVC decoder listed");
            boolean nvidia = "OMX.Nvidia.h264.decode".equalsIgnoreCase(codecName);
            report("Selected " + codecName + "; hardware gate=" + nvidia);
            first = new Stream(firstView, codecName);
            if (count == 2) second = new Stream(secondView, codecName);
            long startMs = SystemClock.elapsedRealtime();
            while (SystemClock.elapsedRealtime() - startMs < MAX_RUN_MS) {
                long elapsed = SystemClock.elapsedRealtime() - startMs;
                first.tick(elapsed);
                if (second != null) second.tick(elapsed);
                if (first.outputDone && (second == null || second.outputDone)) break;
                SystemClock.sleep(3);
            }
            long elapsed = SystemClock.elapsedRealtime() - startMs;
            report("elapsedMs=" + elapsed + " firstFrames=" + first.frames + "/" + EXPECTED_FRAMES +
                   " firstFormat=" + first.outputWidth + "x" + first.outputHeight +
                   " firstEOS=" + first.outputDone);
            if (second != null)
                report("secondFrames=" + second.frames + "/" + EXPECTED_FRAMES +
                       " secondFormat=" + second.outputWidth + "x" + second.outputHeight +
                       " secondEOS=" + second.outputDone);
            boolean firstPass = first.outputDone && first.frames >= EXPECTED_FRAMES &&
                                first.outputWidth == WIDTH && first.outputHeight == HEIGHT;
            boolean secondPass = second == null || (second.outputDone && second.frames >= EXPECTED_FRAMES &&
                                 second.outputWidth == WIDTH && second.outputHeight == HEIGHT);
            String result = firstPass && secondPass ? (nvidia ? "NVIDIA_PASS" : "SOFTWARE_PASS") : "INCOMPLETE";
            report("RESULT=" + result +
                   " count=" + count + " codec=" + codecName);
        } catch (Throwable error) {
            report("RESULT=ERROR count=" + count + " " + error.getClass().getName() + ": " + error.getMessage());
        } finally {
            if (second != null) second.close();
            if (first != null) first.close();
            report("Probe finished; all created codecs released");
            runOnUiThread(new Runnable() {
                @Override public void run() {
                    running = false;
                    oneButton.setEnabled(true);
                    twoButton.setEnabled(true);
                }
            });
        }
    }

    private void report(final String message) {
        Log.i(TAG, message);
        runOnUiThread(new Runnable() {
            @Override public void run() { results.append("\n" + message); }
        });
    }
}
