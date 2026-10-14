package org.claritylink.android;

import android.app.Activity;
import android.content.Context;
import android.content.ComponentName;
import android.content.Intent;
import android.content.ServiceConnection;
import android.graphics.Bitmap;
import android.graphics.Canvas;
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
import org.claritylink.renderer.RendererViewport;

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
    private boolean compositorBound;
    private boolean ipcSessionReady;
    private boolean ipcSubmitted;
    private boolean canvasDrawLogged;
    private boolean rendererScenarioValidated;
    private boolean warningResumeValidated;
    private FrameIpcClient frameIpcClient;
    private final ServiceConnection compositorConnection = new ServiceConnection() {
        public void onServiceConnected(ComponentName name, android.os.IBinder service) {
            if (!active || closing || activeGeneration <= 0) return;
            FrameIpcClient client = new FrameIpcClient(service);
            try {
                int remotePid = client.begin(activeGeneration);
                if (remotePid <= 0 || remotePid == android.os.Process.myPid()) {
                    log("IPC_SESSION_REJECTED separate_process_required=true");
                    stopOwnedDisplay("ipc-session-start-failed");
                    return;
                }
                frameIpcClient = client;
                ipcSessionReady = true;
                log("IPC_SESSION_STARTED generation=" + activeGeneration + " remote_pid=" + remotePid
                        + " transport=private_binder_pipe max_frame_bytes=4194304");
            } catch (Exception failure) {
                log("IPC_SESSION_REJECTED type=" + failure.getClass().getSimpleName());
                stopOwnedDisplay("ipc-session-start-failed");
            }
        }
        public void onServiceDisconnected(ComponentName name) {
            frameIpcClient = null;
            ipcSessionReady = false;
            log("IPC_REMOTE_DISCONNECTED");
            if (active && !closing) stopOwnedDisplay("ipc-remote-disconnected");
        }
    };

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        recreation = state != null;
        showStatus("ClarityLink disabled candidate. No display is selected automatically.");
        log("ACTIVITY_READY api=" + Build.VERSION.SDK_INT + " pid=" + android.os.Process.myPid()
                + " permissions_requested=none");
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
        ClarityLinkDisplayApplication application = (ClarityLinkDisplayApplication) getApplication();
        activeGeneration = application.nextGeneration();
        // Reserve generation 1 so the first lab run can exercise a positive stale generation.
        if (activeGeneration == 1L) activeGeneration = application.nextGeneration();
        active = true;
        closing = false;
        ipcSessionReady = false;
        ipcSubmitted = false;
        canvasDrawLogged = false;
        rendererScenarioValidated = false;
        warningResumeValidated = false;
        compositorBound = bindService(new Intent(this, CompositorService.class),
                compositorConnection, Context.BIND_AUTO_CREATE);
        if (!compositorBound) {
            stopOwnedDisplay("ipc-bind-failed");
            return;
        }
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
            closeIpcSession();
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
            RendererViewport geometry = new RendererViewport(
                    new RendererViewport.Bounds(100, 60, 700, 420),
                    java.util.Collections.singletonList(new RendererViewport.Bounds(300, 170, 500, 270)),
                    RendererViewport.SYNTHETIC_TEST_ONLY);
            renderer = new Display1OutputBackend(contentHost,
                    new Display1OutputBackend.Viewport(0, 0, 800, 480), generation, geometry);
            renderer.attach();
            TextView label = new TextView(root.getContext());
            label.setText("SYNTHETIC FRAME · API17 LAB ONLY");
            label.setTextColor(Color.WHITE);
            label.setBackgroundColor(0xcc000000);
            FrameLayout.LayoutParams labelParams = new FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT);
            root.addView(label, labelParams);
            renderer.submit(syntheticFrame(1L));
            awaitFrame(0, generation, 1L);
        } catch (RuntimeException failure) {
            log("RENDERER_ATTACH_FAILED type=" + failure.getClass().getSimpleName());
            releaseRenderer();
            if (displayHost != null) displayHost.close();
            active = false;
        }
    }

    private void awaitFrame(final int attempt, final long generation, final long expectedTimestampNs) {
        main.postDelayed(new Runnable() {
            public void run() {
                if (!active || closing || renderer == null || generation != activeGeneration) return;
                ClarityLinkContentView view = renderer.contentView();
                if (view != null && view.drawnGeneration() == generation &&
                        view.drawnTimestampNs() == expectedTimestampNs) {
                    if (expectedTimestampNs == 1L && !canvasDrawLogged) {
                        canvasDrawLogged = true;
                        log("SYNTHETIC_FRAME_DRAWN_ON_PRESENTATION_CANVAS generation=" + generation + " timestamp=1");
                    }
                    if (expectedTimestampNs == 1L && !rendererScenarioValidated) {
                        verifySyntheticGeometry(view);
                        if (generation <= 1L || view.submitFrame(syntheticFrame(2L), generation - 1L))
                            throw new IllegalStateException("stale_generation_accepted");
                        view.onHostSuspended(HostedContentLifecycle.WARNING_PREEMPTION, generation);
                        if (view.hasDisplayedFrame() || view.submitFrame(syntheticFrame(2L), generation))
                            throw new IllegalStateException("warning_preemption_did_not_clear_or_block");
                        if (hasVisiblePixels(view)) throw new IllegalStateException("warning_pixels_not_cleared");
                        view.onHostResumed(generation);
                        if (!view.submitFrame(syntheticFrame(2L), generation))
                            throw new IllegalStateException("matching_warning_resume_rejected");
                        rendererScenarioValidated = true;
                        log("CLIMP09_RENDER_GEOMETRY_PASS crop=top-row rotation=90 fit=portrait safeAreaAndProtectedMask=synthetic warning=preempt staleGeneration=rejected");
                        awaitFrame(0, generation, 2L);
                        return;
                    }
                    if (expectedTimestampNs == 2L && !warningResumeValidated) {
                        warningResumeValidated = true;
                        log("CLIMP09_WARNING_RESUME_PASS generation=" + generation + " timestamp=2");
                    }
                    if (ipcSessionReady && !ipcSubmitted) submitSyntheticFrame(generation);
                    else if (!ipcSessionReady) awaitFrame(attempt + 1, generation, expectedTimestampNs);
                    return;
                }
                if (attempt >= 40) {
                    log("SYNTHETIC_FRAME_TIMEOUT timestamp=" + expectedTimestampNs);
                    stopOwnedDisplay("frame-timeout");
                    return;
                }
                awaitFrame(attempt + 1, generation, expectedTimestampNs);
            }
        }, 50L);
    }

    private void verifySyntheticGeometry(ClarityLinkContentView view) {
        RendererViewport fractional = new RendererViewport(
                new RendererViewport.Bounds(101, 61, 699, 419),
                java.util.Collections.singletonList(new RendererViewport.Bounds(300, 170, 500, 270)),
                RendererViewport.SYNTHETIC_TEST_ONLY);
        android.graphics.Rect safe = fractional.scaledSafeArea(401, 241);
        android.graphics.Rect protectedRect = fractional.scaled(
                new RendererViewport.Bounds(300, 170, 500, 270), 401, 241);
        if (safe.left != 51 || safe.top != 31 || safe.right != 350 || safe.bottom != 210 ||
                protectedRect.left != 150 || protectedRect.top != 85 ||
                protectedRect.right != 251 || protectedRect.bottom != 136)
            throw new IllegalStateException("fractional_viewport_rounding_failed");
        Bitmap snapshot = Bitmap.createBitmap(view.getWidth(), view.getHeight(), Bitmap.Config.ARGB_8888);
        try {
            view.draw(new Canvas(snapshot));
            int minX = view.getWidth(), minY = view.getHeight(), maxX = -1, maxY = -1;
            int red = 0, green = 0, blue = 0, yellow = 0;
            for (int y = 0; y < snapshot.getHeight(); y++) {
                for (int x = 0; x < snapshot.getWidth(); x++) {
                    int pixel = snapshot.getPixel(x, y);
                    int alpha = Color.alpha(pixel);
                    if (alpha == 0) continue;
                    if (x < 100 || x >= 700 || y < 60 || y >= 420 ||
                            (x >= 300 && x < 500 && y >= 170 && y < 270))
                        throw new IllegalStateException("synthetic_viewport_clip_failed");
                    minX = Math.min(minX, x); minY = Math.min(minY, y);
                    maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
                    int r = Color.red(pixel), g = Color.green(pixel), b = Color.blue(pixel);
                    if (r > 200 && g < 40 && b < 40) red++;
                    if (g > 200 && r < 40 && b < 40) green++;
                    if (b > 200 && r < 40 && g < 40) blue++;
                    if (r > 200 && g > 200 && b < 40) yellow++;
                }
            }
            if (maxX < minX || maxY < minY || maxX - minX + 1 < 170 || maxX - minX + 1 > 190 ||
                    maxY - minY + 1 < 350 || maxY - minY + 1 > 370 || red < 100 || green < 100 ||
                    blue != 0 || yellow != 0)
                throw new IllegalStateException("synthetic_crop_rotation_aspect_ratio_failed");
        } finally {
            snapshot.recycle();
        }
    }

    private boolean hasVisiblePixels(ClarityLinkContentView view) {
        Bitmap snapshot = Bitmap.createBitmap(view.getWidth(), view.getHeight(), Bitmap.Config.ARGB_8888);
        try {
            view.draw(new Canvas(snapshot));
            for (int y = 0; y < snapshot.getHeight(); y++)
                for (int x = 0; x < snapshot.getWidth(); x++)
                    if (Color.alpha(snapshot.getPixel(x, y)) != 0) return true;
            return false;
        } finally {
            snapshot.recycle();
        }
    }

    private void submitSyntheticFrame(final long generation) {
        FrameIpcClient client = frameIpcClient;
        if (client == null || ipcSubmitted) return;
        ipcSubmitted = true;
        boolean started = client.submit(syntheticFrame(), generation, new FrameIpcClient.Callback() {
            public void complete(final boolean accepted, final String reason) {
                main.post(new Runnable() {
                    public void run() {
                        if (!active || closing || activeGeneration != generation) return;
                        if (!accepted) {
                            log("IPC_SYNTHETIC_FRAME_REJECTED generation=" + generation + " reason=" + reason);
                            stopOwnedDisplay("ipc-frame-rejected");
                            return;
                        }
                        log("IPC_SYNTHETIC_FRAME_ACCEPTED generation=" + generation
                                + " timestamp=1 bytes=16 backpressure=single_in_flight");
                        if (crashAfterFirstFrame) {
                            crashAfterFirstFrame = false;
                            throw new RuntimeException("CL-IMP-03 emulator-only crash recovery probe");
                        }
                    }
                });
            }
        });
        if (!started) log("IPC_FRAME_BACKPRESSURE_REJECT generation=" + generation);
    }

    private DecodedFrame syntheticFrame() { return syntheticFrame(1L); }

    private DecodedFrame syntheticFrame(long timestampNs) {
        byte[] rgba = new byte[] {
                (byte) 255, 0, 0, (byte) 255, 0, (byte) 255, 0, (byte) 255,
                0, 0, (byte) 255, (byte) 255, (byte) 255, (byte) 255, 0, (byte) 255
        };
        return new DecodedFrame(2, 2, 8, timestampNs, 90, 0, 0, 2, 1, ByteBuffer.wrap(rgba));
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
        closeIpcSession();
        activeGeneration = 0L;
        closing = false;
    }

    private void closeIpcSession() {
        FrameIpcClient client = frameIpcClient;
        frameIpcClient = null;
        ipcSessionReady = false;
        if (client != null) client.end(activeGeneration);
        if (compositorBound) {
            try { unbindService(compositorConnection); }
            catch (IllegalArgumentException ignored) { }
            compositorBound = false;
        }
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
