package org.claritylink.renderer;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import java.nio.ByteBuffer;

/**
 * Project-owned API17-only laboratory source. The static mode emits one frame;
 * the synthetic-video mode emits changing frames. It has no Honda/device API.
 */
public final class DiagnosticFrameSource implements FrameSource {
    public enum Mode { STATIC, SYNTHETIC_VIDEO }

    private static final long MAX_FRAME_BYTES = DecodedFrame.MAX_RGBA_BYTES;
    private final int width;
    private final int height;
    private final Mode mode;
    private long frameCounter;
    private long lastTimestampNs;
    private boolean closed;

    public DiagnosticFrameSource(int width, int height, Mode mode) {
        long bytes = (long) width * (long) height * 4L;
        if (width <= 0 || height <= 0 || width > 1920 || height > 1080 ||
                bytes > MAX_FRAME_BYTES || mode == null) {
            throw new IllegalArgumentException("diagnostic_frame_configuration_invalid");
        }
        this.width = width;
        this.height = height;
        this.mode = mode;
    }

    public synchronized DecodedFrame nextFrame(long generation) {
        if (closed || generation <= 0) return null;
        if (mode == Mode.STATIC && frameCounter != 0) return null;
        if (frameCounter == Long.MAX_VALUE) throw new IllegalStateException("frame_counter_exhausted");
        long nextCounter = ++frameCounter;
        long timestampNs = System.nanoTime();
        if (timestampNs <= lastTimestampNs) timestampNs = lastTimestampNs + 1L;
        lastTimestampNs = timestampNs;

        Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        try {
            Canvas canvas = new Canvas(bitmap);
            int background = mode == Mode.STATIC ? Color.rgb(18, 48, 74) : videoColor(nextCounter);
            canvas.drawColor(background);
            Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.DITHER_FLAG);
            paint.setColor(Color.rgb(30, 150, 200));
            canvas.drawRect(new RectF(0, 0, width, Math.max(8, height / 48)), paint);
            paint.setColor(Color.WHITE);
            paint.setTextSize(Math.max(12.0f, width / 32.0f));
            float x = Math.max(8.0f, width / 32.0f);
            float y = Math.max(24.0f, height / 8.0f);
            float step = Math.max(18.0f, height / 11.0f);
            canvas.drawText("CLARITYLINK", x, y, paint);
            canvas.drawText("INDEPENDENT FRAME TEST", x, y + step, paint);
            canvas.drawText("LAB ONLY", x, y + step * 2, paint);
            paint.setTextSize(Math.max(10.0f, width / 64.0f));
            float detailsY = Math.min(height - 12.0f, y + step * 3.6f);
            float detailStep = Math.max(14.0f, height / 24.0f);
            canvas.drawText("Frame: " + nextCounter, x, detailsY, paint);
            canvas.drawText("Generation: " + generation, x, detailsY + detailStep, paint);
            canvas.drawText("Logical source: " + width + "x" + height, x,
                    detailsY + detailStep * 2, paint);
            canvas.drawText("Monotonic timestamp ns: " + timestampNs, x,
                    detailsY + detailStep * 3, paint);

            int[] argb = new int[width * height];
            bitmap.getPixels(argb, 0, width, 0, 0, width, height);
            ByteBuffer rgba = ByteBuffer.allocate((int) (width * (long) height * 4L));
            for (int color : argb) {
                rgba.put((byte) Color.red(color));
                rgba.put((byte) Color.green(color));
                rgba.put((byte) Color.blue(color));
                rgba.put((byte) Color.alpha(color));
            }
            rgba.flip();
            return new DecodedFrame(width, height, width * 4, timestampNs,
                    0, 0, 0, width, height, rgba);
        } finally {
            if (!bitmap.isRecycled()) bitmap.recycle();
        }
    }

    private static int videoColor(long counter) {
        switch ((int) ((counter - 1L) % 3L)) {
            case 0: return Color.rgb(64, 20, 24);
            case 1: return Color.rgb(20, 64, 32);
            default: return Color.rgb(24, 32, 72);
        }
    }

    public synchronized void close() { closed = true; }
    public synchronized long frameCount() { return frameCounter; }
    public int width() { return width; }
    public int height() { return height; }
}
