package org.claritylink.android;

import android.app.Activity;
import android.hardware.display.DisplayManager;
import android.os.Bundle;
import android.graphics.Color;
import android.util.Base64;
import android.util.Log;
import android.view.Display;
import android.view.Gravity;
import android.view.Surface;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.widget.FrameLayout;
import android.widget.TextView;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;

/** Emulator-only API17 MediaCodec integration probe. Synthetic fixtures only. */
public final class Api17DecoderLabActivity extends Activity implements SecondaryDisplayHost.HostedContentListener {
    private static final String TAG = "ClarityLinkCLIMP03";
    private final Object lock = new Object();
    private Surface primarySurface;
    private Surface secondarySurface;
    private SecondaryDisplayHost secondaryHost;
    private TextView secondaryOverlay;
    private boolean started;
    private int secondaryFrameCount;

    public void onCreate(Bundle state) {
        super.onCreate(state);
        FrameLayout root = new FrameLayout(this);
        SurfaceView primary = new SurfaceView(this);
        root.addView(primary, new FrameLayout.LayoutParams(320, 240));
        setContentView(root);
        primary.getHolder().addCallback(new SurfaceHolder.Callback() {
            public void surfaceCreated(SurfaceHolder holder) {
                synchronized (lock) { primarySurface = holder.getSurface(); }
                maybeStart();
            }
            public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) { }
            public void surfaceDestroyed(SurfaceHolder holder) { synchronized (lock) { primarySurface = null; } }
        });
        DisplayManager manager = (DisplayManager) getSystemService(DISPLAY_SERVICE);
        Display chosen = null;
        if (manager != null) {
            Display[] displays = manager.getDisplays(DisplayManager.DISPLAY_CATEGORY_PRESENTATION);
            if (displays != null) for (Display display : displays) {
                if (display != null && display.isValid() && display.getDisplayId() != 0) {
                    if (chosen != null) { chosen = null; break; }
                    chosen = display;
                }
            }
        }
        if (chosen == null) { fail("unique_api17_presentation_display_required"); return; }
        secondaryHost = new SecondaryDisplayHost(this);
        if (!secondaryHost.showOfflineLabForRuntimeTest(this, chosen, 850002L,
                DisplayPolicy.FULL_FRAME_TEST_LAYOUT)) fail("synthetic_presentation_admission_failed");
    }

    private void maybeStart() {
        final Surface primary, secondary;
        synchronized (lock) {
            if (started || primarySurface == null || secondarySurface == null) return;
            started = true;
            primary = primarySurface;
            secondary = secondarySurface;
        }
        new Thread(new Runnable() { public void run() { decode(primary, secondary); } },
                "climp08-api17-codec-test").start();
    }

    private void decode(Surface primary, Surface secondary) {
        Api17SurfaceH264Decoder primaryDecoder = null, secondaryDecoder = null;
        try {
            byte[] red = fixture("type110-red-32x32.h264.b64");
            byte[] blue = fixture("type111-blue-32x32.h264.b64");
            byte[] green = fixture("type111-green-64x64.h264.b64");
            byte[] redConfig = Api17SurfaceH264Decoder.extractCodecConfig(red);
            byte[] blueConfig = Api17SurfaceH264Decoder.extractCodecConfig(blue);
            byte[] greenConfig = Api17SurfaceH264Decoder.extractCodecConfig(green);
            byte[][] redFrames = Api17SurfaceH264Decoder.extractVclFrames(red);
            byte[][] blueFrames = Api17SurfaceH264Decoder.extractVclFrames(blue);
            byte[][] greenFrames = Api17SurfaceH264Decoder.extractVclFrames(green);
            primaryDecoder = new Api17SurfaceH264Decoder(32, 32, primary, 850001L, redConfig);
            secondaryDecoder = new Api17SurfaceH264Decoder(32, 32, secondary, 850002L, blueConfig);
            int primaryFrames = feedTwoFrames(primaryDecoder, redFrames, 850001L);
            int secondaryFrames = feedTwoFrames(secondaryDecoder, blueFrames, 850002L);
            secondaryDecoder.reset(64, 64, secondary, 850003L, greenConfig);
            int resolutionFrames = feedTwoFrames(secondaryDecoder, greenFrames, 850003L);
            secondaryFrameCount = secondaryFrames + resolutionFrames;
            boolean staleRejected = false;
            try { secondaryDecoder.decode(blueFrames[0], 300000L, 850002L, 1000L); }
            catch (Api17SurfaceH264Decoder.DecodeException expected) { staleRejected = true; }
            if (!staleRejected || primaryFrames < 1 || secondaryFrames < 1 || resolutionFrames < 1)
                throw new IllegalStateException("decoder frame/generation validation failed");
            Log.i(TAG, "CLIMP08_API17_MEDIACODEC_PASS primaryFrames=" + primaryFrames +
                    " secondaryFrames=" + secondaryFrames + " resolutionFrames=" + resolutionFrames +
                    " resolutionReset=64x64 independentStreams=true surfaceSubmissionOnly=true physicalScanout=UNPROVEN");
            updateSecondaryOverlay("CLARITYLINK\nINDEPENDENT FRAME TEST\nLAB ONLY\n" +
                    "Type111 H.264 fixture (synthetic, unauthenticated)\n" +
                    "Frame: " + secondaryFrameCount + "\nGeneration: 850003\n" +
                    "Logical source: 64x64\nMonotonic timestamp ns: " + System.nanoTime() +
                    "\nType110 remains on separate lab Surface");
        } catch (Throwable error) {
            Log.e(TAG, "CLIMP08_API17_MEDIACODEC_FAIL", error);
        } finally {
            if (secondaryDecoder != null) secondaryDecoder.close();
            if (primaryDecoder != null) primaryDecoder.close();
            runOnUiThread(new Runnable() { public void run() {
                if (secondaryHost != null) secondaryHost.close();
                finish();
            }});
        }
    }

    private int feedTwoFrames(Api17SurfaceH264Decoder decoder, byte[][] frames, long generation) {
        if (frames.length < 2) throw new IllegalStateException("fixture_requires_two_vcl_frames");
        int count = decoder.decode(frames[0], 100000L, generation, 3000L);
        count += decoder.decode(frames[1], 200000L, generation, 3000L);
        return count;
    }

    private byte[] fixture(String name) throws Exception {
        InputStream in = getAssets().open(name);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[1024]; int count;
        while ((count = in.read(buffer)) != -1) {
            if (out.size() + count > 16384) throw new IllegalStateException("fixture_size_limit");
            out.write(buffer, 0, count);
        }
        in.close(); return Base64.decode(out.toByteArray(), Base64.DEFAULT);
    }

    private void fail(String reason) {
        Log.e(TAG, "CLIMP08_API17_MEDIACODEC_FAIL " + reason);
        finish();
    }

    public void presentationRoot(FrameLayout root) {
        TextView label = new TextView(root.getContext());
        label.setTextColor(Color.WHITE);
        label.setBackgroundColor(0xcc000000);
        label.setTextSize(12.0f);
        label.setPadding(8, 8, 8, 8);
        label.setText("CLARITYLINK\nINDEPENDENT FRAME TEST\nLAB ONLY\n" +
                "Type111 H.264 fixture (synthetic, unauthenticated)\n" +
                "Waiting for decoder output\nLogical source: 32x32\n" +
                "Monotonic timestamp ns: " + System.nanoTime());
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.TOP | Gravity.LEFT);
        root.addView(label, params);
        secondaryOverlay = label;
    }

    private void updateSecondaryOverlay(final String message) {
        runOnUiThread(new Runnable() { public void run() {
            if (secondaryOverlay != null) secondaryOverlay.setText(message);
        }});
    }

    public void state(DisplayPolicy.Admission state) { }
    public void surface(Surface surface) { synchronized (lock) { secondarySurface = surface; } maybeStart(); }
    public void error(String operation, String exceptionType) {
        Log.e(TAG, "CLIMP08_PRESENTATION_ERROR " + operation + ":" + exceptionType);
    }

    protected void onDestroy() {
        if (secondaryHost != null) secondaryHost.close();
        super.onDestroy();
    }
}
