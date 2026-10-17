package org.claritylink.android;

import android.app.Activity;
import android.app.Dialog;
import android.app.Presentation;
import android.content.Context;
import android.content.DialogInterface;
import android.hardware.display.DisplayManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Display;
import android.view.Gravity;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.TextView;

/** API17 window admission experiment. Actual admission is blocked outside an isolated emulator. */
public final class Test4WindowAdmissionActivity extends Activity {
    private static final String TAG = "ClarityLinkTest4Probe";
    private static final String MODE_ADMISSION = "EMULATOR_ADMISSION";
    private static final String CONFIRM = "CL_T4_ISOLATED_API17_EMULATOR_ONLY";
    private static final int DISPLAY_ID = 1;
    private static final long MAX_WINDOW_MS = 5000L;
    private final Handler main = new Handler(Looper.getMainLooper());
    private DisplayManager manager;
    private ProbePresentation presentation;
    private boolean admissionRequested;
    private boolean dismissalRequested;
    private boolean terminated;
    private final Runnable timeoutDismiss = new Runnable() {
        public void run() { dismissOwnedWindow("deadline"); }
    };
    private final DisplayManager.DisplayListener displayListener = new DisplayManager.DisplayListener() {
        public void onDisplayAdded(int id) { }
        public void onDisplayChanged(int id) {
            if (id == DISPLAY_ID && admissionRequested) dismissOwnedWindow("display_changed");
        }
        public void onDisplayRemoved(int id) {
            if (id == DISPLAY_ID) dismissOwnedWindow("display_removed");
        }
    };

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        TextView center = new TextView(this);
        center.setText("ClarityLink Test 4 laboratory probe");
        setContentView(center);
        log("CREATED api=" + Build.VERSION.SDK_INT + " uid=" + android.os.Process.myUid());
        if (state != null) {
            log("TERMINATED restored_instance_requires_fresh_launch=true");
            finish();
            return;
        }
        if (Build.VERSION.SDK_INT != 17) {
            log("ADMISSION_REJECTED reason=api_mismatch");
            finish();
            return;
        }
        final Display target;
        try {
            manager = (DisplayManager)getSystemService(Context.DISPLAY_SERVICE);
            if (manager == null) throw new IllegalStateException("display_manager_missing");
            Display[] visible = manager.getDisplays();
            if (visible == null || visible.length > 8) throw new IllegalStateException("display_list_invalid");
            int count = 0;
            Display found = null;
            for (Display item : visible) if (item.getDisplayId() == DISPLAY_ID) { count++; found = item; }
            if (count != 1 || found == null || !found.isValid())
                throw new IllegalStateException("target_not_unique_or_valid");
            target = found;
            log("DISPLAY_ENUMERATED id=1 count=" + visible.length);
            Display[] eligible = manager.getDisplays(DisplayManager.DISPLAY_CATEGORY_PRESENTATION);
            boolean categoryMember = false;
            if (eligible != null) for (Display item : eligible)
                if (item.getDisplayId() == DISPLAY_ID) categoryMember = true;
            log("PRESENTATION_CATEGORY_MEMBER id=1 value=" + categoryMember);
            if (!categoryMember) throw new IllegalStateException("not_presentation_category_member");
            Context displayContext = createDisplayContext(target);
            if (displayContext == null) throw new IllegalStateException("display_context_null");
            DisplayMetrics metrics = displayContext.getResources().getDisplayMetrics();
            log("DISPLAY_CONTEXT_READY id=1 size=" + metrics.widthPixels + "x" + metrics.heightPixels);
            presentation = new ProbePresentation(this, target);
            Window window = presentation.getWindow();
            if (window == null) throw new IllegalStateException("window_object_null");
            // This changes only the not-yet-admitted Dialog attributes.
            window.setLayout(120, 48);
            window.setGravity(Gravity.TOP | Gravity.LEFT);
            window.addFlags(WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE |
                    WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE);
            log("PRESENTATION_OBJECT_READY id=1 type=" + window.getAttributes().type +
                    " flags=0x" + Integer.toHexString(window.getAttributes().flags));
            if (!modeBRequested()) {
                log("ADMISSION_NOT_REQUESTED windows_created=0 surfaces_allocated=0");
                finish();
                return;
            }
            if (!isIsolatedEmulator()) {
                log("ADMISSION_REJECTED reason=emulator_guard");
                finish();
                return;
            }
            manager.registerDisplayListener(displayListener, main);
            admissionRequested = true;
            log("ADMISSION_REQUESTED id=1");
            presentation.setOnDismissListener(new DialogInterface.OnDismissListener() {
                public void onDismiss(DialogInterface dialog) {
                    log("DISMISSED_CALLBACK id=1");
                    finish();
                }
            });
            presentation.show();
            View decor = presentation.getWindow().getDecorView();
            log("ADMITTED_EMULATOR_ONLY id=1 type=" + presentation.getWindow().getAttributes().type +
                    " token_present=" + (decor.getWindowToken() != null));
            main.postDelayed(timeoutDismiss, MAX_WINDOW_MS);
        } catch (SecurityException denied) {
            log("ADMISSION_REJECTED type=" + denied.getClass().getName());
            dismissOwnedWindow("security_exception");
        } catch (WindowManager.BadTokenException denied) {
            log("ADMISSION_REJECTED type=" + denied.getClass().getName());
            dismissOwnedWindow("bad_token");
        } catch (RuntimeException failure) {
            log("ADMISSION_REJECTED type=" + failure.getClass().getName());
            dismissOwnedWindow("runtime_exception");
        }
    }

    private boolean modeBRequested() {
        Bundle extras = getIntent() == null ? null : getIntent().getExtras();
        return extras != null && MODE_ADMISSION.equals(extras.getString("mode")) &&
                CONFIRM.equals(extras.getString("confirm"));
    }

    private static boolean isIsolatedEmulator() {
        String hardware = Build.HARDWARE == null ? "" : Build.HARDWARE.toLowerCase();
        String fingerprint = Build.FINGERPRINT == null ? "" : Build.FINGERPRINT.toLowerCase();
        return (hardware.contains("goldfish") || hardware.contains("ranchu")) &&
                fingerprint.startsWith("generic");
    }

    private void dismissOwnedWindow(String reason) {
        if (dismissalRequested) return;
        dismissalRequested = true;
        main.removeCallbacks(timeoutDismiss);
        log("DISMISS_REQUESTED reason=" + reason);
        if (presentation != null) {
            try { presentation.dismiss(); }
            catch (RuntimeException failure) { log("DISMISS_FAILED type=" + failure.getClass().getName()); }
        }
        log("WINDOW_REMOVAL_LOCAL token_present=" +
                (presentation != null && presentation.getWindow() != null &&
                 presentation.getWindow().getDecorView().getWindowToken() != null));
        finish();
    }

    @Override protected void onNewIntent(android.content.Intent intent) {
        super.onNewIntent(intent);
        log("DUPLICATE_LAUNCH_IGNORED");
    }

    @Override protected void onStop() {
        if (admissionRequested) dismissOwnedWindow("activity_stopped");
        super.onStop();
    }

    @Override protected void onDestroy() {
        if (!terminated) {
            terminated = true;
            if (manager != null && admissionRequested) manager.unregisterDisplayListener(displayListener);
            if (presentation != null) {
                try { presentation.dismiss(); }
                catch (RuntimeException failure) { log("DESTROY_DISMISS_FAILED"); }
                presentation = null;
            }
            main.removeCallbacks(timeoutDismiss);
            log("TERMINATED");
        }
        super.onDestroy();
    }

    private static void log(String message) { Log.i(TAG, message); }

    private static final class ProbePresentation extends Presentation {
        ProbePresentation(Context outer, Display display) { super(outer, display); }
        @Override protected void onCreate(Bundle state) {
            super.onCreate(state);
            FrameLayout content = new FrameLayout(getContext());
            content.setBackgroundColor(0xff223344);
            TextView label = new TextView(getContext());
            label.setText("TEST 4 LAB");
            label.setTextColor(0xffffffff);
            content.addView(label);
            setContentView(content);
        }
    }
}
