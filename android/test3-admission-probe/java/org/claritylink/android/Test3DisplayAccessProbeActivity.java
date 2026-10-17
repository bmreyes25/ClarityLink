package org.claritylink.android;

import android.app.Activity;
import android.content.Context;
import android.content.res.Resources;
import android.hardware.display.DisplayManager;
import android.os.Bundle;
import android.os.Build;
import android.os.Process;
import android.util.DisplayMetrics;
import android.util.Log;
import android.view.Display;
import java.util.List;

/** No-display, read-only API17 inventory probe. It never creates a display window. */
public final class Test3DisplayAccessProbeActivity extends Activity {
    private static final String TAG = "ClarityLinkTest3Probe";
    private static final int MAX_DISPLAYS = 8;
    private static final int TARGET_DISPLAY_ID = 1;
    private static final int KNOWN_FLAGS = Display.FLAG_SECURE |
            Display.FLAG_SUPPORTS_PROTECTED_BUFFERS;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        log("PROBE_START api=" + Build.VERSION.SDK_INT + " uid=" + Process.myUid());
        try {
            enumerate();
        } catch (RuntimeException failure) {
            log("PROBE_FAILED type=" + failure.getClass().getName());
        } finally {
            log("PROBE_COMPLETE windows_created=0 surfaces_allocated=0");
            finish();
        }
    }

    private void enumerate() {
        final DisplayManager manager;
        try {
            manager = (DisplayManager)getSystemService(Context.DISPLAY_SERVICE);
        } catch (RuntimeException failure) {
            log("DISPLAY_MANAGER_FAILED type=" + failure.getClass().getName());
            return;
        }
        if (manager == null) {
            log("DISPLAY_MANAGER_UNAVAILABLE");
            return;
        }
        log("DISPLAY_MANAGER_AVAILABLE");

        final DisplayDiscovery discovery;
        try {
            discovery = new DisplayDiscovery(this);
        } catch (RuntimeException failure) {
            log("DISPLAY_MANAGER_UNAVAILABLE type=" + failure.getClass().getName());
            return;
        }
        final List<DisplayDiscovery.Info> displays;
        try {
            displays = discovery.enumerate();
        } catch (RuntimeException failure) {
            log("DISPLAY_LIST_FAILED type=" + failure.getClass().getName());
            return;
        }
        log("DISPLAY_LIST count=" + displays.size() + " limit=" + MAX_DISPLAYS);
        int targetCount = 0;
        for (int i = 0; i < displays.size(); i++) {
            DisplayDiscovery.Info info = displays.get(i);
            if (i < MAX_DISPLAYS) {
                log("DISPLAY id=" + info.id + " name=" + clean(info.name) + " type=" + info.type +
                        " valid=" + info.valid + " size=" + info.width + "x" + info.height +
                        " refresh_hz=" + info.refreshHz + " rotation=" + info.rotation);
            }
            if (info.id == TARGET_DISPLAY_ID) targetCount++;
        }
        if (displays.size() > MAX_DISPLAYS) log("DISPLAY_LIST_TRUNCATED");
        if (targetCount == 0) {
            log("TARGET_DISPLAY_NOT_VISIBLE id=" + TARGET_DISPLAY_ID);
        } else if (targetCount > 1) {
            log("TARGET_DISPLAY_AMBIGUOUS id=" + TARGET_DISPLAY_ID + " count=" + targetCount);
        } else {
            try {
                Display target = discovery.select(new DisplayDiscovery.Selector() {
                    public boolean matches(DisplayDiscovery.Info info) {
                        return info.id == TARGET_DISPLAY_ID;
                    }
                });
                if (target == null) {
                    log("TARGET_DISPLAY_UNAVAILABLE id=" + TARGET_DISPLAY_ID);
                } else {
                    reportTargetFlags(target);
                    createTargetDisplayContext(target);
                }
            } catch (SecurityException denied) {
                log("TARGET_DISPLAY_ACCESS_DENIED type=" + denied.getClass().getName());
            } catch (RuntimeException failure) {
                log("TARGET_DISPLAY_LOOKUP_FAILED type=" + failure.getClass().getName());
            }
        }

        try {
            Display[] presentation = manager.getDisplays(DisplayManager.DISPLAY_CATEGORY_PRESENTATION);
            int presentationCount = presentation == null ? -1 : presentation.length;
            log("PRESENTATION_CATEGORY_LIST count=" + presentationCount +
                    " meaning=public_display_category_only");
        } catch (SecurityException denied) {
            log("PRESENTATION_CATEGORY_DENIED type=" + denied.getClass().getName());
        } catch (RuntimeException failure) {
            log("PRESENTATION_CATEGORY_FAILED type=" + failure.getClass().getName());
        }
    }

    private void reportTargetFlags(Display display) {
        try {
            int flags = display.getFlags();
            log("DISPLAY_FLAGS id=" + TARGET_DISPLAY_ID + " flags=0x" + Integer.toHexString(flags) +
                    " secure=" + ((flags & Display.FLAG_SECURE) != 0) +
                    " protected_buffers=" + ((flags & Display.FLAG_SUPPORTS_PROTECTED_BUFFERS) != 0) +
                    " unknown_flag_bits=0x" + Integer.toHexString(flags & ~KNOWN_FLAGS));
        } catch (SecurityException denied) {
            log("DISPLAY_FLAGS_DENIED id=" + TARGET_DISPLAY_ID + " type=" + denied.getClass().getName());
        } catch (RuntimeException failure) {
            log("DISPLAY_FLAGS_FAILED id=" + TARGET_DISPLAY_ID + " type=" + failure.getClass().getName());
        }
    }

    private void createTargetDisplayContext(Display display) {
        try {
            Context displayContext = createDisplayContext(display);
            if (displayContext == null) {
                log("DISPLAY_CONTEXT_NULL id=" + TARGET_DISPLAY_ID);
                return;
            }
            Resources resources = displayContext.getResources();
            DisplayMetrics metrics = resources.getDisplayMetrics();
            log("DISPLAY_CONTEXT_CREATED id=" + TARGET_DISPLAY_ID +
                    " metrics=" + metrics.widthPixels + "x" + metrics.heightPixels +
                    " density_dpi=" + metrics.densityDpi);
        } catch (SecurityException denied) {
            log("DISPLAY_CONTEXT_DENIED id=" + TARGET_DISPLAY_ID +
                    " type=" + denied.getClass().getName());
        } catch (RuntimeException failure) {
            log("DISPLAY_CONTEXT_FAILED id=" + TARGET_DISPLAY_ID +
                    " type=" + failure.getClass().getName());
        }
    }

    private static String clean(String value) {
        if (value == null) return "null";
        StringBuilder result = new StringBuilder();
        for (int i = 0; i < value.length() && result.length() < 48; i++) {
            char c = value.charAt(i);
            result.append((c >= 32 && c <= 126) ? c : '_');
        }
        return result.toString();
    }

    private static void log(String message) {
        Log.i(TAG, message);
    }
}
