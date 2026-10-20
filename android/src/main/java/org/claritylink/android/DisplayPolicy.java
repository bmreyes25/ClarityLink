package org.claritylink.android;

import android.os.Build;

/** Honda policy is UNKNOWN by default and cannot be inferred from display enumeration. */
public final class DisplayPolicy {
    public enum Evidence { UNKNOWN, STATIC, OBSERVED, APPROVED }
    /**
     * Admission telemetry names the boundary actually reached. LAB states are
     * synthetic-only; WINDOW_REMOVED_VERIFIED is reserved for an independent
     * WindowManager receipt and is never inferred from Dialog.dismiss().
     */
    public enum Admission {
        DISABLED,
        DISPLAY_ENUMERATED,
        DISPLAY_CONTEXT_READY,
        WINDOW_CONSTRUCTED,
        WINDOW_ADMISSION_REQUESTED,
        WINDOW_ADMITTED_LAB,
        WINDOW_REJECTED,
        WARNING_PREEMPTED_LAB,
        DISMISS_REQUESTED,
        WINDOW_REMOVED_VERIFIED,
        FAULTED,
        BLOCKED_HONDA_SAFETY,
        SURFACE_CREATED,
        FIRST_FRAME_PRESENTED,
        /* Compatibility names for older listeners; new host code emits above. */
        DISPLAY_CONTEXT_CREATED, PRESENTATION_CONSTRUCTED, PRESENTATION_SHOWN, FAILED
    }
    public static final class WarningVisibilityPolicy {
        public final Evidence evidence;
        public final boolean warningsVisible, downstreamComposited, protectedRegionKnown, blankOnInterrupt;
        public WarningVisibilityPolicy(Evidence evidence, boolean visible, boolean downstream,
                                      boolean protectedKnown, boolean blank) {
            this.evidence = evidence; warningsVisible = visible; downstreamComposited = downstream;
            protectedRegionKnown = protectedKnown; blankOnInterrupt = blank;
        }
        /**
         * Caller-supplied flags are not proof of Honda warning arbitration.
         * Keep production admission closed until a trusted evidence source is
         * connected and validated against the real vehicle warning path.
         */
        public boolean safeForHonda() { return false; }
        public static WarningVisibilityPolicy unknown() {
            return new WarningVisibilityPolicy(Evidence.UNKNOWN, false, false, false, true);
        }
    }
    /** Positive, non-intent-controlled guard for synthetic API17 lab paths. */
    static boolean isIsolatedApi17EmulatorBuild() {
        String hardware = Build.HARDWARE == null ? "" : Build.HARDWARE.toLowerCase();
        String fingerprint = Build.FINGERPRINT == null ? "" : Build.FINGERPRINT.toLowerCase();
        return Build.VERSION.SDK_INT == 17 &&
                (hardware.contains("goldfish") || hardware.contains("ranchu")) &&
                fingerprint.startsWith("generic");
    }
    public static final class Layout {
        public final int logicalWidth, logicalHeight, x, y, width, height, rotation;
        public final boolean testOnly;
        public Layout(int lw,int lh,int x,int y,int w,int h,int rotation,boolean testOnly) {
            if (lw <= 0 || lh <= 0 || x < 0 || y < 0 || w <= 0 || h <= 0 || x > lw-w || y > lh-h ||
                (rotation!=0 && rotation!=90 && rotation!=180 && rotation!=270))
                throw new IllegalArgumentException("invalid layout bounds");
            this.logicalWidth=lw; this.logicalHeight=lh; this.x=x; this.y=y; this.width=w; this.height=h;
            this.rotation=rotation; this.testOnly=testOnly;
        }
    }
    /** FULL_FRAME_TEST_LAYOUT — synthetic only; NOT_HONDA_SAFETY_APPROVED. */
    public static final Layout FULL_FRAME_TEST_LAYOUT = new Layout(800,480,0,0,800,480,0,true);
    private DisplayPolicy() {}
}
