package org.claritylink.android;

import android.app.Activity;
import android.content.Context;
import android.hardware.display.DisplayManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.Display;
import android.view.Surface;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;

/** Emulator-only probe. Its synthetic overlay display is never Honda evidence. */
public final class P2C2AdmissionProbeActivity extends Activity {
    private static final String TAG = "ClarityLinkP2C2";
    private static final int CYCLES = 3;
    private final Handler main = new Handler(Looper.getMainLooper());
    private Display display;
    private SecondaryDisplayHost host;
    private int cycle;
    private int created;
    private int destroyed;
    private boolean surfaceActive;
    private boolean cyclesFinished;
    private boolean removed;

    private void event(String value) { Log.i(TAG, "P2C2_" + value); }
    private void fail(String value) { event("FAIL case=" + value); }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        setContentView(new FrameLayout(this));
        event("READY api=" + android.os.Build.VERSION.SDK_INT);
        if (android.os.Build.VERSION.SDK_INT != 17) { fail("wrong_api"); return; }
        awaitDisplay(0);
    }

    private void awaitDisplay(final int attempt) {
        DisplayManager manager = (DisplayManager) getSystemService(Context.DISPLAY_SERVICE);
        Display[] candidates = manager.getDisplays(DisplayManager.DISPLAY_CATEGORY_PRESENTATION);
        Display selected = null;
        if (candidates != null) for (Display item : candidates) {
            if (item != null && item.isValid() && item.getDisplayId() != Display.DEFAULT_DISPLAY) {
                if (selected != null) { fail("ambiguous_display"); return; }
                selected = item;
            }
        }
        if (selected == null) {
            if (attempt >= 40) { fail("display_unavailable"); return; }
            main.postDelayed(new Runnable() { public void run() { awaitDisplay(attempt + 1); } }, 250);
            return;
        }
        display = selected;
        event("DISPLAY_ENUMERATED id=" + selected.getDisplayId());
        if (manager.getDisplay(selected.getDisplayId()) == null) { fail("display_lookup"); return; }
        if (manager.getDisplay(0x7ffffffe) != null) { fail("invalid_display_accepted"); return; }
        SecondaryDisplayHost invalid = new SecondaryDisplayHost(null);
        if (invalid.showOfflineLabForRuntimeTest(this, null, 1,
                DisplayPolicy.FULL_FRAME_TEST_LAYOUT)) { fail("invalid_host_accepted"); return; }
        event("INVALID_DISPLAY_PASS");
        if (!permissionDenied(selected)) { fail("system_overlay_permission"); return; }
        startCycle();
    }

    private boolean permissionDenied(Display target) {
        Context context = createDisplayContext(target);
        WindowManager manager = (WindowManager) context.getSystemService(Context.WINDOW_SERVICE);
        View view = new View(context);
        WindowManager.LayoutParams params = new WindowManager.LayoutParams();
        params.width = 1; params.height = 1;
        params.type = WindowManager.LayoutParams.TYPE_SYSTEM_OVERLAY;
        params.flags = WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE;
        try {
            manager.addView(view, params);
            manager.removeViewImmediate(view);
            event("UNEXPECTED_SYSTEM_OVERLAY_ADMISSION");
            return false;
        } catch (SecurityException denied) {
            event("PERMISSION_DENIED_PASS exception=" + denied.getClass().getName());
            return true;
        } catch (WindowManager.BadTokenException denied) {
            String detail = denied.getMessage();
            if (detail != null && detail.contains("permission denied for this window type")) {
                event("PERMISSION_DENIED_PASS exception=BadTokenException");
                return true;
            }
            event("PERMISSION_RESULT_INCONCLUSIVE exception=BadTokenException");
            return false;
        } catch (RuntimeException other) {
            event("PERMISSION_RESULT_INCONCLUSIVE exception=" + other.getClass().getName());
            return false;
        }
    }

    private void startCycle() {
        if (display == null || !display.isValid()) { fail("cycle_display_lost"); return; }
        cycle++;
        host = new SecondaryDisplayHost(new SecondaryDisplayHost.Listener() {
            public void state(DisplayPolicy.Admission state) {
                event("STATE_" + state.name() + " cycle=" + cycle);
                if (state == DisplayPolicy.Admission.FAILED && cyclesFinished && !removed) {
                    removed = true;
                    main.post(new Runnable() { public void run() { checkRemoval(); } });
                }
            }
            public void surface(Surface surface) {
                if (surface == null) {
                    if (surfaceActive) { surfaceActive = false; destroyed++; }
                } else {
                    if (surfaceActive) { fail("duplicate_surface"); return; }
                    surfaceActive = true; created++;
                    final int thisCycle = cycle;
                    main.postDelayed(new Runnable() { public void run() {
                        if (thisCycle == cycle && !cyclesFinished) completeCycle();
                    } }, 150);
                }
            }
            public void error(String operation, String type) { fail(operation + ":" + type); }
        });
        if (!host.showOfflineLabForRuntimeTest(this, display, cycle,
                DisplayPolicy.FULL_FRAME_TEST_LAYOUT)) fail("presentation_show");
    }

    private void completeCycle() {
        if (!surfaceActive) { fail("surface_missing"); return; }
        host.close();
        if (surfaceActive || destroyed != created) { fail("cycle_cleanup"); return; }
        event("CYCLE_PASS index=" + cycle);
        if (cycle < CYCLES) {
            main.postDelayed(new Runnable() { public void run() { startCycle(); } }, 150);
        } else {
            cyclesFinished = true;
            startFinalPresentation();
        }
    }

    private void startFinalPresentation() {
        host = new SecondaryDisplayHost(new SecondaryDisplayHost.Listener() {
            public void state(DisplayPolicy.Admission state) {
                event("FINAL_STATE_" + state.name());
                if (state == DisplayPolicy.Admission.FAILED && !removed) {
                    removed = true;
                    main.post(new Runnable() { public void run() { checkRemoval(); } });
                }
            }
            public void surface(Surface surface) {
                if (surface != null) { surfaceActive = true; created++; }
                else if (surfaceActive) { surfaceActive = false; destroyed++; }
            }
            public void error(String operation, String type) { fail(operation + ":" + type); }
        });
        if (!host.showOfflineLabForRuntimeTest(this, display, CYCLES + 1,
                DisplayPolicy.FULL_FRAME_TEST_LAYOUT)) { fail("final_show"); return; }
        main.postDelayed(new Runnable() { public void run() {
            if (surfaceActive && created == CYCLES + 1 && destroyed == CYCLES)
                event("PRESENTATION_PASS cycles=" + CYCLES + " activeSurface=1");
            else fail("final_surface_count");
        } }, 400);
    }

    private void checkRemoval() {
        if (host != null) host.close();
        DisplayManager manager = (DisplayManager) getSystemService(Context.DISPLAY_SERVICE);
        if (display != null && manager.getDisplay(display.getDisplayId()) == null &&
                !surfaceActive && destroyed == created && created == CYCLES + 1) {
            event("DISPLAY_REMOVED_PASS created=" + created + " destroyed=" + destroyed);
        } else fail("display_removal_cleanup");
    }

    @Override protected void onDestroy() {
        if (host != null) host.close();
        super.onDestroy();
    }
}
