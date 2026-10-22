package org.claritylink.renderer;

import android.os.Looper;
import android.view.Gravity;
import android.widget.FrameLayout;

/** Separate semantic navigation route into a caller-supplied synthetic main layer. */
public final class StructuredNavigationOutputBackend implements StructuredNavigationSink {
    private final Display1OutputBackend.Host host;
    private final Display1OutputBackend.Viewport viewport;
    private final NavigationGenerationLedger generationLedger;
    private StructuredNavigationContentView view;
    private long sessionId = -1L;
    private long generation;
    private long highestGeneration;
    private long attachmentGeneration;

    public StructuredNavigationOutputBackend(Display1OutputBackend.Host host,
            Display1OutputBackend.Viewport viewport, NavigationGenerationLedger generationLedger) {
        if (host == null || viewport == null || generationLedger == null)
            throw new IllegalArgumentException("host, viewport, and generation ledger required");
        this.host = host;
        this.viewport = viewport;
        this.generationLedger = generationLedger;
    }

    @Override public void beginSession(long newSessionId, long newGeneration) {
        requireUiThread();
        if (newSessionId < 0 || newGeneration <= highestGeneration
                || !generationLedger.advanceTo(newGeneration))
            throw new IllegalArgumentException("session must be non-negative and generation must increase");
        if (!host.isNavigationPageActive()) throw new IllegalStateException("Navigation host inactive");
        if (view == null) {
            FrameLayout root = host.getMainLayer();
            if (root == null) throw new IllegalStateException("synthetic main layer unavailable");
            StructuredNavigationContentView created = new StructuredNavigationContentView(root.getContext());
            FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(viewport.width,
                    viewport.height, Gravity.TOP | Gravity.LEFT);
            params.leftMargin = viewport.left;
            params.topMargin = viewport.top;
            created.setLayoutParams(params);
            if (!created.beginSession(newGeneration) || !host.attachContent(created, newGeneration)) {
                created.close();
                throw new IllegalStateException("synthetic host rejected navigation content");
            }
            view = created;
            attachmentGeneration = newGeneration;
        } else if (!view.beginSession(newGeneration)) {
            throw new IllegalArgumentException("navigation generation must increase");
        }
        sessionId = newSessionId;
        generation = newGeneration;
        highestGeneration = newGeneration;
    }

    @Override public boolean submit(NavigationUpdate update) {
        if (update == null || view == null || !host.isNavigationPageActive()
                || update.sessionId != sessionId || update.generation != generation) return false;
        return view.present(update);
    }

    /** Immediate fail-safe withdrawal; display state is never inferred from an unknown host. */
    @Override public void withdraw() {
        if (view != null) view.withdraw();
    }

    public StructuredNavigationContentView contentView() { return view; }

    @Override public void close() {
        requireUiThread();
        StructuredNavigationContentView old = view;
        view = null;
        sessionId = -1L;
        generation = 0L;
        if (old == null) return;
        try {
            host.detachContent(old, attachmentGeneration);
            old.close();
        } catch (RuntimeException failure) {
            old.close();
            throw failure;
        }
    }

    private static void requireUiThread() {
        if (Looper.myLooper() != Looper.getMainLooper())
            throw new IllegalStateException("navigation host lifecycle must run on the UI thread");
    }
}
