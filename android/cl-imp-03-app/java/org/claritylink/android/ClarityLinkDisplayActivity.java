package org.claritylink.android;

import android.app.Activity;
import android.content.Context;
import android.graphics.Color;
import android.hardware.display.DisplayManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Log;
import android.view.Display;
import android.view.Surface;
import android.view.View;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.TextView;

import org.claritylink.renderer.ClarityLinkContentView;
import org.claritylink.renderer.DecodedFrame;
import org.claritylink.renderer.Display1OutputBackend;

import java.nio.ByteBuffer;
import java.util.List;

/** Standalone API17 adapter. Display admission is emulator-only and opt-in per launch. */
public final class ClarityLinkDisplayActivity extends Activity
        implements SecondaryDisplayHost.HostedContentListener {
    private static final String TAG = "ClarityLinkCLIMP03";
    private static final String EXTRA_MODE = "mode";
    private static final String EXTRA_CONFIRM = "emulator_only_confirmation";
    private static final String EXTRA_CRASH = "crash_after_first_frame";
    private static final String LAB_MODE = "EMULATOR_PRESENTATION";
    private static final String LAB_CONFIRM = "CL_IMP_03_OFFLINE_EMULATOR_ONLY";
    private static final boolean PRODUCTION_HONDA_INTEGRATION_ENABLED = false;
    private final Handler main = new Handler(Looper.getMainLooper());
    private SecondaryDisplayHost displayHost;
    private Display1OutputBackend renderer;
    private FrameLayout presentationRoot;
    private TextView status;
    private Surface borrowedPresentationSurface;
    private long activeGeneration;
    private boolean active;
    private boolean closing;
    private boolean recreation;
    private boolean crashAfterFirstFrame;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        recreation = state != null;
        showStatus("ClarityLink disabled candidate. No display is selected automatically.");
        log("ACTIVITY_READY api=" + Build.VERSION.SDK_INT + " permissions_requested=none");
        if (!recreation && isExplicitLabRequest(getIntent().getExtras())) startEmulatorLab();
        else log("STATUS_ONLY feature_disabled=true recovered_state=discarded");
    }

    private void showStatus(String message) {
        FrameLayout root = new FrameLayout(this);
        status = new TextView(this);
        status.setTextColor(Color.WHITE);
        status.setTextSize(16.0f);
        status.setPadding(24, 24, 24, 24);
        status.setText(message);
        root.addView(status, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT));
        Button lab = new Button(this);
        lab.setText("Start emulator display lab");
        lab.setOnClickListener(new View.OnClickListener() {
            public void onClick(View view) {
                if (isEmulator()) startEmulatorLab();
                else setStatus("Display lab is restricted to an API17 emulator.");
            }
        });
        FrameLayout.LayoutParams button = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT);
        button.topMargin = 128;
        root.addView(lab, button);
        setContentView(root);
    }

    private void setStatus(String message) {
        if (status != null) status.setText(message);
        log(message.replace(' ', '_'));
    }

    private boolean isExplicitLabRequest(Bundle extras) {
        return extras != null && LAB_MODE.equals(extras.getString(EXTRA_MODE)) &&
                LAB_CONFIRM.equals(extras.getString(EXTRA_CONFIRM));
    }

    private boolean isEmulator() {
        String hardware = Build.HARDWARE == null ? "" : Build.HARDWARE.toLowerCase();
        String fingerprint = Build.FINGERPRINT == null ? "" : Build.FINGERPRINT.toLowerCase();
        return hardware.contains("goldfish") || hardware.contains("ranchu") ||
                fingerprint.startsWith("generic") || fingerprint.contains("emulator");
    }

    private void startEmulatorLab() {
        if (PRODUCTION_HONDA_INTEGRATION_ENABLED) {
            setStatus("Production Honda integration is disabled in this candidate.");
            return;
        }
        if (!isEmulator()) {
            setStatus("Emulator-only display admission refused.");
            return;
        }
        if (active || displayHost != null) stopOwnedDisplay("replace");
        Bundle launch = getIntent() == null ? null : getIntent().getExtras();
        crashAfterFirstFrame = launch != null && launch.getBoolean(EXTRA_CRASH, false);
        DisplayDiscovery discovery;
        List<DisplayDiscovery.Info> inventory;
        try {
            discovery = new DisplayDiscovery(this);
            inventory = discovery.enumerate();
        } catch (RuntimeException failure) {
            setStatus("Display discovery failed: " + failure.getClass().getSimpleName());
            return;
        }
        log("DISPLAY_ENUMERATION count=" + inventory.size());
        for (DisplayDiscovery.Info info : inventory)
            log("DISPLAY id=" + info.id + " valid=" + info.valid + " size=" + info.width + "x" + info.height);
        final Display selected;
        try {
            selected = discovery.select(new DisplayDiscovery.Selector() {
                public boolean matches(DisplayDiscovery.Info info) {
                    return info.valid && info.id != 0 && info.width == 800 && info.height == 480;
                }
            });
        } catch (RuntimeException failure) {
            setStatus("Display selection failed closed: " + failure.getClass().getSimpleName());
            return;
        }
        if (selected == null) {
            setStatus("No unique synthetic 800x480 emulator display; admission refused.");
            return;
        }
        activeGeneration = ((ClarityLinkDisplayApplication) getApplication()).nextGeneration();
        active = true;
        closing = false;
        displayHost = new SecondaryDisplayHost(this);
        DisplayPolicy.Layout layout;
        try {
            layout = new DisplayPolicy.Layout(800, 480, 0, 0, 800, 480, 0, true);
        } catch (IllegalArgumentException invalid) {
            stopOwnedDisplay("invalid-lab-layout");
            return;
        }
        boolean shown = displayHost.showOfflineLabForRuntimeTest(this, selected, activeGeneration, layout);
        if (!shown) {
            stopOwnedDisplay("presentation-admission-failed");
            setStatus("Presentation admission failed closed.");
            return;
        }
        setStatus("SYNTHETIC API17 DISPLAY LAB — NOT CARPLAY — NOT HONDA INTEGRATION");
    }

    public void state(DisplayPolicy.Admission state) {
        log("ADMISSION_STATE=" + state.name());
        if (state == DisplayPolicy.Admission.FAILED && !closing) {
            releaseRenderer();
            active = false;
        }
    }

    /** The Presentation/SurfaceView owns this borrowed handle; this app never releases it. */
    public void surface(Surface surface) {
        borrowedPresentationSurface = surface;
        if (surface == null) {
            log("SURFACE_BORROWED_LOST owner=Presentation_SurfaceHolder released_by_app=false");
            if (!closing && active) releaseRenderer();
        } else {
            log("SURFACE_BORROWED_READY valid=" + surface.isValid() +
                    " owner=Presentation_SurfaceHolder released_by_app=false");
        }
    }

    public void error(String operation, String exceptionType) {
        log("ADMISSION_ERROR operation=" + operation + " type=" + exceptionType);
        setStatus("Presentation failed closed: " + exceptionType);
    }

    public void presentationRoot(final FrameLayout root) {
        if (!active || closing || root == null || activeGeneration <= 0) return;
        presentationRoot = root;
        final long generation = activeGeneration;
        Display1OutputBackend.Host contentHost = new Display1OutputBackend.Host() {
            private View ownedContent;
            private long ownedGeneration;
            public FrameLayout getMainLayer() { return active && !closing ? root : null; }
            public boolean isNavigationPageActive() { return active && !closing && presentationRoot == root; }
            public boolean attachContent(View content, long requestedGeneration) {
                if (!isNavigationPageActive() || content == null || requestedGeneration != generation ||
                        content.getParent() != null) return false;
                root.addView(content);
                ownedContent = content;
                ownedGeneration = requestedGeneration;
                return true;
            }
            public boolean detachContent(View content, long requestedGeneration) {
                if (ownedContent != content || ownedGeneration != requestedGeneration) return false;
                root.removeView(content);
                ownedContent = null;
                ownedGeneration = 0L;
                return true;
            }
        };
        try {
            renderer = new Display1OutputBackend(contentHost,
                    new Display1OutputBackend.Viewport(0, 0, 800, 480), generation);
            renderer.attach();
            TextView label = new TextView(root.getContext());
            label.setText("SYNTHETIC FRAME · API17 LAB ONLY");
            label.setTextColor(Color.WHITE);
            label.setBackgroundColor(0xcc000000);
            FrameLayout.LayoutParams labelParams = new FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT);
            root.addView(label, labelParams);
            renderer.submit(syntheticFrame());
            awaitFrame(0, generation);
        } catch (RuntimeException failure) {
            log("RENDERER_ATTACH_FAILED type=" + failure.getClass().getSimpleName());
            releaseRenderer();
            if (displayHost != null) displayHost.close();
            active = false;
        }
    }

    private void awaitFrame(final int attempt, final long generation) {
        main.postDelayed(new Runnable() {
            public void run() {
                if (!active || closing || renderer == null || generation != activeGeneration) return;
                ClarityLinkContentView view = renderer.contentView();
                if (view != null && view.drawnGeneration() == generation &&
                        view.drawnTimestampNs() == 1L) {
                    log("SYNTHETIC_FRAME_DRAWN_ON_PRESENTATION_CANVAS generation=" + generation + " timestamp=1");
                    if (crashAfterFirstFrame) {
                        crashAfterFirstFrame = false;
                        throw new RuntimeException("CL-IMP-03 emulator-only crash recovery probe");
                    }
                    return;
                }
                if (attempt >= 40) {
                    log("SYNTHETIC_FRAME_TIMEOUT");
                    stopOwnedDisplay("frame-timeout");
                    return;
                }
                awaitFrame(attempt + 1, generation);
            }
        }, 50L);
    }

    private DecodedFrame syntheticFrame() {
        byte[] rgba = new byte[] {
                (byte) 255, (byte) 40, 0, (byte) 255, 0, (byte) 80, (byte) 255, (byte) 255,
                0, (byte) 180, (byte) 80, (byte) 255, (byte) 255, (byte) 180, 0, (byte) 255
        };
        return new DecodedFrame(2, 2, 8, 1L, 0, 0, 0, 2, 2, ByteBuffer.wrap(rgba));
    }

    private void releaseRenderer() {
        Display1OutputBackend old = renderer;
        renderer = null;
        presentationRoot = null;
        if (old != null) {
            try { old.close(); }
            catch (RuntimeException failure) { log("RENDERER_CLOSE_FAILED type=" + failure.getClass().getSimpleName()); }
            log("RENDERER_RELEASED");
        }
    }

    private void stopOwnedDisplay(String reason) {
        if (closing) return;
        closing = true;
        active = false;
        log("LIFECYCLE_STOP reason=" + reason);
        releaseRenderer();
        SecondaryDisplayHost old = displayHost;
        displayHost = null;
        if (old != null) {
            try { old.close(); }
            catch (RuntimeException failure) { log("PRESENTATION_CLOSE_FAILED type=" + failure.getClass().getSimpleName()); }
        }
        borrowedPresentationSurface = null;
        activeGeneration = 0L;
        closing = false;
    }

    @Override protected void onPause() {
        if (active || displayHost != null) stopOwnedDisplay("activity-pause");
        super.onPause();
    }

    @Override protected void onDestroy() {
        if (active || displayHost != null || renderer != null) stopOwnedDisplay("activity-destroy");
        super.onDestroy();
    }

    @Override protected void onSaveInstanceState(Bundle state) {
        // Deliberately do not persist lab admission or replay a Presentation after process recovery.
        super.onSaveInstanceState(state);
    }

    @Override protected void onNewIntent(android.content.Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (isExplicitLabRequest(intent.getExtras())) startEmulatorLab();
    }

    private static void log(String message) { Log.i(TAG, message); }
}
