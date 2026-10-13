package org.claritylink.renderer;

import android.view.Gravity;
import android.view.View;
import android.os.Looper;
import android.widget.FrameLayout;

/**
 * API 17 renderer adapter for a host explicitly supplied by its caller.
 *
 * Root acquisition is intentionally not implemented: HondaHack obtains it
 * through Xposed/private InterfaceWindow hooks. No direct framebuffer access.
 */
public final class Display1OutputBackend {
    public interface Host {
        FrameLayout getMainLayer();
        boolean isNavigationPageActive();
        boolean attachContent(View content, long generation);
        boolean detachContent(View content, long generation);
    }

    public static final class Viewport {
        public final int left;
        public final int top;
        public final int width;
        public final int height;

        public Viewport(int left, int top, int width, int height) {
            if (left < 0 || top < 0 || width <= 0 || height <= 0
                    || (long) left + width > 800L || (long) top + height > 480L) {
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
    private final long generation;
    private FrameLayout root;
    private ClarityLinkContentView view;

    public Display1OutputBackend(Host host, Viewport viewport) {
        this(host, viewport, 1L);
    }

    public Display1OutputBackend(Host host, Viewport viewport, long generation) {
        if (host == null || viewport == null) throw new IllegalArgumentException("host/viewport required");
        if (generation <= 0) throw new IllegalArgumentException("positive generation required");
        this.host = host;
        this.viewport = viewport;
        this.generation = generation;
    }

    public void attach() {
        requireUiThread();
        if (view != null) throw new IllegalStateException("already attached");
        if (!host.isNavigationPageActive()) throw new IllegalStateException("Navigation host inactive");
        root = host.getMainLayer();
        if (root == null) throw new IllegalStateException("ExternalDisplay main layer unavailable");
        view = new ClarityLinkContentView(root.getContext());
        view.beginSession(generation);
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(
                viewport.width, viewport.height, Gravity.TOP | Gravity.LEFT);
        params.leftMargin = viewport.left;
        params.topMargin = viewport.top;
        view.setLayoutParams(params);
        try {
            if (!host.attachContent(view, generation))
                throw new IllegalStateException("host rejected content View");
        } catch (RuntimeException failure) {
            view.close();
            view = null;
            root = null;
            throw failure;
        }
    }

    public void submit(final DecodedFrame frame) {
        if (view == null) throw new IllegalStateException("not attached");
        if (!host.isNavigationPageActive()) throw new IllegalStateException("Navigation host inactive");
        if (!view.submitFrame(frame, generation))
            throw new IllegalArgumentException("frame rejected by generation, timestamp, or format policy");
    }

    public void clear() {
        requireUiThread();
        ClarityLinkContentView current = view;
        if (current != null) current.clearFrame();
    }

    public void close() {
        requireUiThread();
        ClarityLinkContentView oldView = view;
        long oldGeneration = generation;
        view = null;
        root = null;
        if (oldView != null) {
            try {
                if (!host.detachContent(oldView, oldGeneration)) oldView.close();
            } catch (RuntimeException failure) {
                oldView.close();
                throw failure;
            }
        }
    }

    /** Exposes the currently owned View for host diagnostics and offline tests. */
    public ClarityLinkContentView contentView() { return view; }

    private static void requireUiThread() {
        if (Looper.myLooper() != Looper.getMainLooper())
            throw new IllegalStateException("renderer host lifecycle must run on the UI thread");
    }
}
