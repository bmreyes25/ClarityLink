package org.claritylink.renderer;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.View;

import org.claritylink.android.HostedContentLifecycle;

/** Generic synthetic main-layer view for structured maneuvers; it accepts no frame data. */
public final class StructuredNavigationContentView extends View implements HostedContentLifecycle {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private NavigationUpdate latest;
    private long highestGeneration;
    private boolean hostAvailable = true;
    private boolean closed;
    private boolean withdrawn;

    public StructuredNavigationContentView(Context context) {
        super(context);
        if (context == null) throw new IllegalArgumentException("context required");
        setWillNotDraw(false);
        setBackgroundColor(Color.TRANSPARENT);
    }

    /** Starts a fresh navigation owner. Generations never move backwards or repeat. */
    public synchronized boolean beginSession(long generation) {
        if (closed || !hostAvailable || generation <= highestGeneration) return false;
        highestGeneration = generation;
        latest = null;
        withdrawn = false;
        invalidate();
        return true;
    }

    public synchronized boolean present(NavigationUpdate update) {
        if (closed || !hostAvailable || withdrawn || update == null || update.generation != highestGeneration
                || update.sequence <= (latest == null ? -1L : latest.sequence)) return false;
        latest = update;
        invalidate();
        return true;
    }

    /** Withdraws visible guidance synchronously, independent of a future draw callback. */
    public synchronized void withdraw() {
        latest = null;
        withdrawn = true;
        invalidate();
    }

    public synchronized void close() {
        latest = null;
        closed = true;
        setVisibility(View.GONE);
        invalidate();
    }

    public synchronized NavigationUpdate latestUpdate() { return latest; }
    public synchronized long activeGeneration() { return !hostAvailable || closed ? 0L : highestGeneration; }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        NavigationUpdate update;
        synchronized (this) { update = !hostAvailable || closed ? null : latest; }
        if (update == null) return;
        float width = getWidth();
        float height = getHeight();
        if (width <= 0 || height <= 0) return;
        paint.setColor(Color.BLACK);
        paint.setAlpha(210);
        canvas.drawRoundRect(new RectF(4.0f, 4.0f, width - 4.0f, height - 4.0f),
                12.0f, 12.0f, paint);
        paint.setAlpha(255);
        paint.setColor(Color.WHITE);
        paint.setTextSize(Math.max(16.0f, Math.min(28.0f, height * 0.20f)));
        canvas.drawText(label(update.maneuver), 16.0f, height * 0.43f, paint);
        paint.setTextSize(Math.max(14.0f, Math.min(24.0f, height * 0.16f)));
        canvas.drawText(formatDistance(update), 16.0f, height * 0.78f, paint);
        if (update.roadName.length() > 0) {
            float maxWidth = Math.max(0.0f, width - 32.0f);
            String road = update.roadName;
            while (road.length() > 0 && paint.measureText(road) > maxWidth)
                road = road.substring(0, road.length() - 1);
            canvas.drawText(road, 16.0f, height * 0.94f, paint);
        }
    }

    private static String label(NavigationUpdate.Maneuver maneuver) {
        switch (maneuver) {
            case STRAIGHT: return "Continue straight";
            case SLIGHT_LEFT: return "Bear left";
            case LEFT: return "Turn left";
            case SHARP_LEFT: return "Turn sharply left";
            case SLIGHT_RIGHT: return "Bear right";
            case RIGHT: return "Turn right";
            case SHARP_RIGHT: return "Turn sharply right";
            case U_TURN: return "Make a U-turn";
            case ROUNDABOUT: return "Enter roundabout";
            case ARRIVE: return "Arrive";
            default: return "Continue to route";
        }
    }

    private static String formatDistance(NavigationUpdate update) {
        String unit;
        switch (update.unit) {
            case KILOMETERS: unit = "km"; break;
            case FEET: unit = "ft"; break;
            case MILES: unit = "mi"; break;
            default: unit = "m";
        }
        return String.format(java.util.Locale.US, "%.1f %s", update.distance, unit);
    }

    @Override public synchronized void onHostSuspended(int reason, long generation) {
        latest = null;
        withdrawn = true;
        hostAvailable = false;
        invalidate();
    }

    /** Resume alone never restores guidance. A caller must begin a fresh generation. */
    @Override public synchronized void onHostResumed(long generation) {
        latest = null;
        withdrawn = true;
        hostAvailable = true;
        invalidate();
    }
}
