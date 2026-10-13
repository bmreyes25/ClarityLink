package org.claritylink.android;

import android.app.Activity;
import android.content.Context;
import android.hardware.display.DisplayManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.view.Display;
import android.view.Surface;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;

import org.claritylink.renderer.ClarityLinkContentView;
import org.claritylink.renderer.DecodedFrame;
import org.claritylink.renderer.Display1OutputBackend;
import org.claritylink.renderer.HondaStyleSimulatorRendererHost;

import java.nio.ByteBuffer;

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
    private HondaStyleDisplayHostSimulator simulatedHost;
    private HondaStyleDisplayHostSimulator contentHost;
    private ClarityLinkContentView contentView;
    private Display1OutputBackend contentBackend;

    private void event(String value) { Log.i(TAG, "P2C2_" + value); }
    private void fail(String value) { event("FAIL case=" + value); }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        simulatedHost = new HondaStyleDisplayHostSimulator(this);
        setContentView(simulatedHost.getDisplayRoot());
        if (!verifyHostSimulator()) { fail("host_simulator"); return; }
        event("READY api=" + android.os.Build.VERSION.SDK_INT);
        if (android.os.Build.VERSION.SDK_INT != 17) { fail("wrong_api"); return; }
        verifyClarityContentView(0);
    }

    private boolean verifyHostSimulator() {
        if (!(simulatedHost.priorityRank(HondaStyleHostModel.Priority.BOTTOM_CONTENT) <
                simulatedHost.priorityRank(HondaStyleHostModel.Priority.NAVIGATION_CONTENT) &&
                simulatedHost.priorityRank(HondaStyleHostModel.Priority.NAVIGATION_CONTENT) <
                simulatedHost.priorityRank(HondaStyleHostModel.Priority.WARNING_INTERRUPT))) return false;
        android.widget.TextView content = new android.widget.TextView(this);
        content.setText("SYNTHETIC CLARITYLINK CONTENT");
        if (!simulatedHost.attachClarityContent(content, 41)) return false;
        if (!simulatedHost.hasClarityContent() || simulatedHost.contentGeneration() != 41) return false;
        if (simulatedHost.detachClarityContent(40) || !simulatedHost.hasClarityContent()) return false;
        simulatedHost.setSimulatedStockWarningVisible(true);
        if (simulatedHost.getWarningInterruptRoot().getVisibility() != android.view.View.VISIBLE ||
                simulatedHost.getNavigationRoot().getVisibility() != android.view.View.GONE ||
                simulatedHost.attachClarityContent(new android.view.View(this), 42)) return false;
        simulatedHost.setSimulatedStockWarningVisible(false);
        if (!simulatedHost.detachClarityContent(41)) return false;
        android.widget.TextView stale = new android.widget.TextView(this);
        if (!simulatedHost.attachClarityContent(stale, 43)) return false;
        simulatedHost.setNavigationActive(false);
        if (simulatedHost.hasClarityContent() || simulatedHost.contentGeneration() != 0) return false;
        simulatedHost.setNavigationActive(true);
        if (simulatedHost.hasClarityContent()) return false;
        simulatedHost.setSimulatedStockWarningVisible(true);
        simulatedHost.close();
        simulatedHost.close();
        if (!simulatedHost.isClosed()) return false;
        event("HOST_SIMULATOR_PASS layers=bottom,navigation,warning stale_generation=reject navigation_exit=clear close=idempotent evidence=synthetic");
        return true;
    }

    private void verifyClarityContentView(final int attempt) {
        if (attempt == 0) {
            contentHost = new HondaStyleDisplayHostSimulator(this);
            contentBackend = new Display1OutputBackend(
                    new HondaStyleSimulatorRendererHost(contentHost),
                    new Display1OutputBackend.Viewport(0, 0, 800, 480), 77);
            contentBackend.attach();
            contentView = contentBackend.contentView();
            boolean sessionChangeRejected = false;
            try { contentView.beginSession(78); }
            catch (IllegalStateException expected) { sessionChangeRejected = true; }
            if (!sessionChangeRejected) { fail("content_session_mutable"); return; }
            contentBackend.submit(solidFrame(1, 255, 0, 0));
            contentBackend.clear();
            contentBackend.submit(solidFrame(1, 255, 0, 0));
        }
        if (contentView == null || contentView.displayedTimestampNs() != 1L) {
            if (attempt >= 60) { fail("content_initial_timeout"); return; }
            main.postDelayed(new Runnable() { public void run() {
                verifyClarityContentView(attempt + 1);
            } }, 50);
            return;
        }
        contentView.measure(View.MeasureSpec.makeMeasureSpec(100, View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(100, View.MeasureSpec.EXACTLY));
        contentView.layout(0, 0, 100, 100);
        if (drawCenterColor(contentView, 100, 100) != 0xffff0000) {
            fail("content_initial_pixels"); return;
        }
        contentView.layout(0, 0, 120, 60);
        if (drawCenterColor(contentView, 120, 60) != 0xffff0000) {
            fail("content_resize"); return;
        }
        contentHost.setSimulatedStockWarningVisible(true);
        if (contentView.hasDisplayedFrame() || contentView.submitFrame(solidFrame(2, 0, 0, 255), 77)) {
            fail("content_warning_preemption"); return;
        }
        contentHost.setSimulatedStockWarningVisible(false);
        try { contentBackend.submit(solidFrame(2, 0, 255, 0)); }
        catch (RuntimeException failure) { fail("content_resume"); return; }
        awaitSecondContentFrame(0);
    }

    private void awaitSecondContentFrame(final int attempt) {
        if (contentView.displayedTimestampNs() != 2L) {
            if (attempt >= 60) { fail("content_second_timeout"); return; }
            main.postDelayed(new Runnable() { public void run() {
                awaitSecondContentFrame(attempt + 1);
            } }, 50);
            return;
        }
        if (drawCenterColor(contentView, 120, 60) != 0xff00ff00) {
            fail("content_second_pixels"); return;
        }
        contentHost.setNavigationActive(false);
        if (!contentView.isClosed() || contentView.hasDisplayedFrame() || contentHost.hasClarityContent()) {
            fail("content_navigation_exit"); return;
        }
        contentHost.close();
        contentBackend.close();
        event("CONTENT_VIEW_PASS frames=2 session=immutable clear=before_install warning=clears resize=fit generation=77 evidence=synthetic");
        awaitDisplay(0);
    }

    private DecodedFrame solidFrame(long timestamp, int red, int green, int blue) {
        byte[] rgba = new byte[16];
        for (int pixel = 0; pixel < 4; pixel++) {
            int offset = pixel * 4;
            rgba[offset] = (byte) red;
            rgba[offset + 1] = (byte) green;
            rgba[offset + 2] = (byte) blue;
            rgba[offset + 3] = (byte) 255;
        }
        return new DecodedFrame(2, 2, 8, timestamp, 0, 0, 0, 2, 2, ByteBuffer.wrap(rgba));
    }

    private int drawCenterColor(View view, int width, int height) {
        Bitmap target = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        view.draw(new Canvas(target));
        int color = target.getPixel(width / 2, height / 2);
        target.recycle();
        return color;
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
        if (contentBackend != null) contentBackend.close();
        if (contentHost != null) contentHost.close();
        if (simulatedHost != null) simulatedHost.close();
        super.onDestroy();
    }
}
