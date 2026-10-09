package org.claritylink.android;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Rect;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.util.Log;
import android.view.Display;
import android.view.Surface;
import android.widget.TextView;
import android.hardware.display.DisplayManager;
import java.io.InputStream;
import java.util.List;

/** Explicit-mode diagnostic. Default launch performs no display query or output. */
public final class R7E1DisplayDiagnosticActivity extends Activity {
    private static final String TAG = "ClarityLinkR7E1";
    private static final String EXTRA_MODE = "mode";
    private static final String EXTRA_LAB_ACK = "offline_emulator_confirmation";
    private static final String LAB_ACK = "R7E1_OFFLINE_EMULATOR_ONLY";
    private static final long GENERATION = 1L;
    private final Handler handler = new Handler();
    private SecondaryDisplayHost displayHost;
    private Bitmap diagnosticFrame;
    private boolean framePosted;
    private TextView status;

    @Override protected void onCreate(Bundle savedState) {
        super.onCreate(savedState);
        status = new TextView(this);
        status.setText("Status only. Choose an explicit offline diagnostic mode.");
        setContentView(status);
        final String mode = getIntent() == null ? null : getIntent().getStringExtra(EXTRA_MODE);
        if (mode == null || "STATUS".equals(mode)) {
            report("STATUS_ONLY no_display_action=true");
        } else if ("DISPLAY_ENUMERATION".equals(mode)) {
            enumerateDisplays();
        } else if ("PRESENTATION_PREFLIGHT".equals(mode) || "SINGLE_FRAME_DIAGNOSTIC".equals(mode)) {
            if (!isOfflineEmulator() || !LAB_ACK.equals(getIntent().getStringExtra(EXTRA_LAB_ACK))) {
                report("BLOCKED emulator_only_test_mode=true guest_abi=" + Build.CPU_ABI +
                    " hardware=" + Build.HARDWARE + " product=" + Build.PRODUCT +
                    " fingerprint=" + Build.FINGERPRINT);
            } else {
                runEmulatorOnlyDisplayMode(mode);
            }
        } else if ("SHUTDOWN".equals(mode)) {
            closeOwnedDisplay();
            report("SHUTDOWN complete=true");
            finish();
        } else {
            report("UNSUPPORTED_MODE no_action=true");
        }
    }

    private boolean isOfflineEmulator() {
        final boolean x86Guest = "x86".equals(Build.CPU_ABI);
        final boolean emulatorHardware = "ranchu".equals(Build.HARDWARE) ||
            "goldfish".equals(Build.HARDWARE) || "vbox86".equals(Build.HARDWARE);
        final boolean genericFingerprint = Build.FINGERPRINT != null && Build.FINGERPRINT.contains("generic");
        final boolean sdkProduct = Build.PRODUCT != null && Build.PRODUCT.startsWith("sdk");
        return x86Guest && (emulatorHardware || genericFingerprint || sdkProduct);
    }

    private void enumerateDisplays() {
        try {
            final DisplayDiscovery discovery = new DisplayDiscovery(this);
            final List<DisplayDiscovery.Info> infos = discovery.enumerate();
            report("DISPLAY_ENUMERATION count=" + infos.size());
            for (DisplayDiscovery.Info info : infos) {
                report("DISPLAY id=" + info.id + " type=" + info.type + " width=" + info.width +
                    " height=" + info.height + " refresh_hz=" + info.refreshHz + " valid=" + info.valid);
            }
        } catch (RuntimeException error) {
            report("DISPLAY_ENUMERATION_FAILED type=" + error.getClass().getName());
        }
    }

    private void runEmulatorOnlyDisplayMode(final String mode) {
        final DisplayManager manager = (DisplayManager)getSystemService(DISPLAY_SERVICE);
        final Display candidate = selectSyntheticSecondary(manager);
        if (candidate == null) {
            report("PRESENTATION_BLOCKED reason=no_synthetic_secondary_display");
            return;
        }
        report("DISPLAY_ENUMERATED id=" + candidate.getDisplayId());
        displayHost = new SecondaryDisplayHost(new SecondaryDisplayHost.Listener() {
            public void state(DisplayPolicy.Admission state) {
                report("ADMISSION_STATE=" + state.name());
            }
            public void surface(Surface surface) {
                if (surface != null && "SINGLE_FRAME_DIAGNOSTIC".equals(mode) && !framePosted) {
                    framePosted = postOneFrame(surface);
                }
                if (surface == null) report("SURFACE_RELEASED");
            }
            public void error(String operation, String exceptionType) {
                report("DISPLAY_ERROR operation=" + operation + " type=" + exceptionType);
            }
        });
        final boolean shown = displayHost.showOfflineLabForRuntimeTest(this, candidate, GENERATION,
                DisplayPolicy.FULL_FRAME_TEST_LAYOUT);
        if (!shown) {
            report("PRESENTATION_FAILED no_frame=true");
            closeOwnedDisplay();
        } else if ("SINGLE_FRAME_DIAGNOSTIC".equals(mode)) {
            handler.postDelayed(new Runnable() { public void run() {
                closeOwnedDisplay();
                report(framePosted ? "FRAME_CLEARED_AND_RELEASED" : "FRAME_NOT_POSTED");
            }}, 750L);
        }
    }

    private Display selectSyntheticSecondary(DisplayManager manager) {
        if (manager == null) return null;
        Display selected = null;
        final Display[] displays = manager.getDisplays();
        if (displays == null) return null;
        for (Display display : displays) {
            if (display == null || !display.isValid() || display.getDisplayId() == 0) continue;
            if (selected != null) return null;
            selected = display;
        }
        return selected;
    }

    private boolean postOneFrame(Surface surface) {
        Canvas canvas = null;
        try {
            if (diagnosticFrame == null) {
                InputStream stream = getAssets().open("r7e1-diagnostic-frame.png");
                try { diagnosticFrame = BitmapFactory.decodeStream(stream); }
                finally { stream.close(); }
            }
            if (diagnosticFrame == null || diagnosticFrame.getWidth() != 800 || diagnosticFrame.getHeight() != 480) {
                report("FRAME_FAILED reason=asset_invalid");
                return false;
            }
            canvas = surface.lockCanvas(null);
            if (canvas == null) return false;
            canvas.drawBitmap(diagnosticFrame, null, new Rect(0, 0, canvas.getWidth(), canvas.getHeight()), null);
            surface.unlockCanvasAndPost(canvas);
            canvas = null;
            report("FRAME_POSTED count=1");
            return true;
        } catch (Exception error) {
            report("FRAME_FAILED type=" + error.getClass().getName());
            if (canvas != null) {
                try { surface.unlockCanvasAndPost(canvas); } catch (RuntimeException ignored) { }
            }
            return false;
        }
    }

    private void closeOwnedDisplay() {
        if (displayHost != null) {
            displayHost.close();
            displayHost = null;
        }
        if (diagnosticFrame != null) {
            diagnosticFrame.recycle();
            diagnosticFrame = null;
        }
    }

    private void report(String message) {
        Log.i(TAG, message);
        if (status != null) status.setText(message);
    }

    @Override protected void onDestroy() {
        closeOwnedDisplay();
        super.onDestroy();
    }
}
