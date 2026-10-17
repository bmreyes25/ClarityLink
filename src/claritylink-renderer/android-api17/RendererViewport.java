package org.claritylink.renderer;

import android.graphics.Canvas;
import android.graphics.Rect;
import android.graphics.Region;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Synthetic-only logical Display 1 geometry; physical cluster dimensions remain unknown. */
public final class RendererViewport {
    public static final int LOGICAL_WIDTH = 800;
    public static final int LOGICAL_HEIGHT = 480;
    public static final String SYNTHETIC_TEST_ONLY = "SYNTHETIC_TEST_ONLY";
    private static final int MAX_PROTECTED_REGIONS = 32;

    public static final class Bounds {
        public final int left;
        public final int top;
        public final int right;
        public final int bottom;

        public Bounds(int left, int top, int right, int bottom) {
            if (left < 0 || top < 0 || right <= left || bottom <= top ||
                    right > LOGICAL_WIDTH || bottom > LOGICAL_HEIGHT) {
                throw new IllegalArgumentException("viewport bounds outside synthetic logical canvas");
            }
            this.left = left;
            this.top = top;
            this.right = right;
            this.bottom = bottom;
        }
    }

    private final Bounds safeArea;
    private final List<Bounds> protectedRegions;

    public RendererViewport(Bounds safeArea, List<Bounds> protectedRegions, String provenance) {
        if (!SYNTHETIC_TEST_ONLY.equals(provenance) || safeArea == null ||
                protectedRegions == null || protectedRegions.size() > MAX_PROTECTED_REGIONS) {
            throw new IllegalArgumentException("synthetic viewport provenance and bounded regions required");
        }
        ArrayList<Bounds> copy = new ArrayList<Bounds>(protectedRegions.size());
        for (Bounds bounds : protectedRegions) {
            if (bounds == null) throw new IllegalArgumentException("null protected region");
            copy.add(bounds);
        }
        this.safeArea = safeArea;
        this.protectedRegions = Collections.unmodifiableList(copy);
    }

    public static RendererViewport fullCanvasTestOnly() {
        return new RendererViewport(new Bounds(0, 0, LOGICAL_WIDTH, LOGICAL_HEIGHT),
                Collections.<Bounds>emptyList(), SYNTHETIC_TEST_ONLY);
    }

    public Bounds safeArea() { return safeArea; }

    /** Scales excluded rectangles outward so no protected source pixel is exposed. */
    public Rect scaled(Bounds bounds, int viewWidth, int viewHeight) {
        if (bounds == null || viewWidth <= 0 || viewHeight <= 0)
            throw new IllegalArgumentException("positive view size required");
        int left = (int) (((long) bounds.left * viewWidth) / LOGICAL_WIDTH);
        int top = (int) (((long) bounds.top * viewHeight) / LOGICAL_HEIGHT);
        int right = (int) ((((long) bounds.right * viewWidth) + LOGICAL_WIDTH - 1) / LOGICAL_WIDTH);
        int bottom = (int) ((((long) bounds.bottom * viewHeight) + LOGICAL_HEIGHT - 1) / LOGICAL_HEIGHT);
        return new Rect(left, top, right, bottom);
    }

    /** Scales the allowed safe area inward so fractional edges never admit outside pixels. */
    public Rect scaledSafeArea(int viewWidth, int viewHeight) {
        if (viewWidth <= 0 || viewHeight <= 0)
            throw new IllegalArgumentException("positive view size required");
        int left = (int) ((((long) safeArea.left * viewWidth) + LOGICAL_WIDTH - 1) / LOGICAL_WIDTH);
        int top = (int) ((((long) safeArea.top * viewHeight) + LOGICAL_HEIGHT - 1) / LOGICAL_HEIGHT);
        int right = (int) (((long) safeArea.right * viewWidth) / LOGICAL_WIDTH);
        int bottom = (int) (((long) safeArea.bottom * viewHeight) / LOGICAL_HEIGHT);
        return new Rect(left, top, right, bottom);
    }

    /** Clips the Canvas to the supplied synthetic safe area and subtracts protected rectangles. */
    public boolean clip(Canvas canvas, int viewWidth, int viewHeight) {
        if (canvas == null || viewWidth <= 0 || viewHeight <= 0)
            throw new IllegalArgumentException("canvas and positive view size required");
        if (!canvas.clipRect(scaledSafeArea(viewWidth, viewHeight))) return false;
        for (Bounds bounds : protectedRegions) {
            if (!canvas.clipRect(scaled(bounds, viewWidth, viewHeight), Region.Op.DIFFERENCE)) return false;
        }
        return true;
    }
}
