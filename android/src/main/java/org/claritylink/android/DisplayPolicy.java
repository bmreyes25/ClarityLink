package org.claritylink.android;

/** Honda policy is UNKNOWN by default and cannot be inferred from display enumeration. */
public final class DisplayPolicy {
    public enum Evidence { UNKNOWN, STATIC, OBSERVED, APPROVED }
    public enum Admission { DISPLAY_ENUMERATED, DISPLAY_CONTEXT_CREATED, PRESENTATION_CONSTRUCTED,
        PRESENTATION_SHOWN, SURFACE_CREATED, FIRST_FRAME_PRESENTED, FAILED }
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
