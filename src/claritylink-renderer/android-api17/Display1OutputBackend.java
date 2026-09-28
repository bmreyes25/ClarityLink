package org.claritylink.renderer;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Rect;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;

/**
 * API 17 renderer skeleton for a host supplied from Honda ExternalDisplay.
 *
 * Root acquisition is intentionally not implemented: HondaHack obtains it
 * through Xposed/private InterfaceWindow hooks. No direct framebuffer access.
 */
public final class Display1OutputBackend {
    public interface Host {
        FrameLayout getMainLayer();
        boolean isNavigationPageActive();
    }

    public static final class Viewport {
        public final int left;
        public final int top;
        public final int width;
        public final int height;

        public Viewport(int left, int top, int width, int height) {
            if (left < 0 || top < 0 || width <= 0 || height <= 0
                    || left + width > 800 || top + height > 480) {
                throw new IllegalArgumentException("viewport must fit Display 1 800x480");
            }
            this.left = left;
            this.top = top;
            this.width = width;
            this.height = height;
        }
    }

    private final Host host;
    private final Viewport viewport;
    private final Paint paint = new Paint(Paint.FILTER_BITMAP_FLAG);
    private FrameLayout root;
    private RenderView view;

    public Display1OutputBackend(Host host, Viewport viewport) {
        if (host == null || viewport == null) throw new IllegalArgumentException("host/viewport required");
        this.host = host;
        this.viewport = viewport;
    }

    public void attach() {
        if (view != null) throw new IllegalStateException("already attached");
        if (!host.isNavigationPageActive()) throw new IllegalStateException("Navigation host inactive");
        root = host.getMainLayer();
        if (root == null) throw new IllegalStateException("ExternalDisplay main layer unavailable");
        view = new RenderView();
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(
                viewport.width, viewport.height, Gravity.TOP | Gravity.LEFT);
        params.leftMargin = viewport.left;
        params.topMargin = viewport.top;
        root.addView(view, 0, params);
    }

    public void submit(final DecodedFrame frame) {
        if (view == null) throw new IllegalStateException("not attached");
        if (frame.rotationDegrees != 0) {
            throw new UnsupportedOperationException("rotation is not implemented");
        }
        final Bitmap bitmap = Bitmap.createBitmap(frame.width, frame.height, Bitmap.Config.ARGB_8888);
        bitmap.setPixels(frame.toArgbPixels(), 0, frame.width, 0, 0, frame.width, frame.height);
        view.post(new Runnable() {
            public void run() {
                if (view == null) {
                    bitmap.recycle();
                    return;
                }
                view.replaceFrame(bitmap, frame.cropLeft, frame.cropTop,
                        frame.cropRight, frame.cropBottom);
            }
        });
    }

    public void clear() {
        final RenderView current = view;
        if (current != null) current.post(new Runnable() {
            public void run() { current.clearFrame(); }
        });
    }

    public void close() {
        final RenderView oldView = view;
        final FrameLayout oldRoot = root;
        view = null;
        root = null;
        if (oldView != null && oldRoot != null) {
            oldView.post(new Runnable() {
                public void run() {
                    oldRoot.removeView(oldView);
                    oldView.clearFrame();
                }
            });
        }
    }

    private final class RenderView extends View {
        private Bitmap frame;
        private Rect crop;

        RenderView() { super(root.getContext()); setWillNotDraw(false); }

        void replaceFrame(Bitmap next, int left, int top, int right, int bottom) {
            Bitmap previous = frame;
            frame = next;
            crop = new Rect(left, top, right, bottom);
            if (previous != null && previous != next) previous.recycle();
            invalidate();
        }

        void clearFrame() {
            Bitmap previous = frame;
            frame = null;
            crop = null;
            if (previous != null) previous.recycle();
            invalidate();
        }

        @Override protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            if (frame != null && crop != null) {
                canvas.drawBitmap(frame, crop, new Rect(0, 0, getWidth(), getHeight()), paint);
            }
        }
    }
}
