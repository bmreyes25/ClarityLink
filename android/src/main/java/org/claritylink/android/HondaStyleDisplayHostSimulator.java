package org.claritylink.android;

import android.content.Context;
import android.graphics.Color;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.os.Looper;
import android.widget.FrameLayout;
import android.widget.TextView;

/**
 * Project-owned API17 simulator for a layered external-display view host.
 * It models composition only; it has no Honda package, service, or hook access.
 */
public final class HondaStyleDisplayHostSimulator {
    private final HondaStyleHostModel model = new HondaStyleHostModel();
    private final FrameLayout displayRoot;
    private final FrameLayout bottomContentRoot;
    private final FrameLayout navigationRoot;
    private final FrameLayout customContentContainer;
    private final FrameLayout warningInterruptRoot;
    private final TextView simulatedWarning;
    private View clarityContent;

    public HondaStyleDisplayHostSimulator(Context context) {
        if (context == null) throw new IllegalArgumentException("context required");
        displayRoot = new FrameLayout(context);
        bottomContentRoot = new FrameLayout(context);
        navigationRoot = new FrameLayout(context);
        customContentContainer = new FrameLayout(context);
        warningInterruptRoot = new FrameLayout(context);
        simulatedWarning = new TextView(context);
        simulatedWarning.setText("SIMULATED STOCK WARNING");
        simulatedWarning.setTextColor(Color.WHITE);
        simulatedWarning.setBackgroundColor(Color.RED);
        simulatedWarning.setGravity(Gravity.CENTER);
        simulatedWarning.setVisibility(View.GONE);

        customContentContainer.setVisibility(View.GONE);
        warningInterruptRoot.addView(simulatedWarning, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        // FrameLayout draws later children above earlier children: warning > navigation > bottom.
        displayRoot.addView(bottomContentRoot, matchParent());
        displayRoot.addView(navigationRoot, matchParent());
        displayRoot.addView(warningInterruptRoot, matchParent());
        navigationRoot.addView(customContentContainer, matchParent());
        warningInterruptRoot.setVisibility(View.GONE);
    }

    private static FrameLayout.LayoutParams matchParent() {
        return new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT);
    }

    /** Root for a project-owned emulator Activity only. */
    public FrameLayout getDisplayRoot() { return displayRoot; }
    public FrameLayout getBottomContentRoot() { return bottomContentRoot; }
    public FrameLayout getNavigationRoot() { return navigationRoot; }
    public FrameLayout getCustomContentContainer() { return customContentContainer; }
    public FrameLayout getWarningInterruptRoot() { return warningInterruptRoot; }
    public int priorityRank(HondaStyleHostModel.Priority priority) { return model.priorityRank(priority); }

    /** Insert at most one caller-owned View for a live navigation generation. */
    public boolean attachClarityContent(View content, long generation) {
        requireOpen();
        if (content == null || clarityContent != null ||
                !model.attach(generation, content.getParent() == null)) return false;
        clarityContent = content;
        try {
            ViewGroup.LayoutParams supplied = content.getLayoutParams();
            FrameLayout.LayoutParams params = supplied instanceof FrameLayout.LayoutParams
                    ? (FrameLayout.LayoutParams) supplied : matchParent();
            if (params.leftMargin < 0 || params.topMargin < 0
                    || (params.width <= 0 && params.width != ViewGroup.LayoutParams.MATCH_PARENT
                        && params.width != ViewGroup.LayoutParams.WRAP_CONTENT)
                    || (params.height <= 0 && params.height != ViewGroup.LayoutParams.MATCH_PARENT
                        && params.height != ViewGroup.LayoutParams.WRAP_CONTENT)) {
                throw new IllegalArgumentException("invalid hosted content bounds");
            }
            customContentContainer.addView(content, params);
            customContentContainer.setVisibility(View.VISIBLE);
            resumeClarityContent(generation);
            return true;
        } catch (RuntimeException failure) {
            suspendClarityContent(HostedContentLifecycle.CONTENT_DETACHED, generation);
            if (content.getParent() == customContentContainer)
                customContentContainer.removeView(content);
            clarityContent = null;
            model.detach(generation);
            return false;
        }
    }

    /** A stale generation cannot detach the active content. */
    public boolean detachClarityContent(long generation) {
        requireUiThread();
        if (clarityContent == null || generation != model.contentGeneration()) return false;
        suspendClarityContent(HostedContentLifecycle.CONTENT_DETACHED, generation);
        if (!model.detach(generation)) return false;
        removeViewOnly();
        return true;
    }

    /** Leaving Navigation removes project content so re-entry cannot resurrect stale frames. */
    public void setNavigationActive(boolean active) {
        requireOpen();
        if (!active && clarityContent != null)
            suspendClarityContent(HostedContentLifecycle.NAVIGATION_EXIT, model.contentGeneration());
        model.setNavigationActive(active);
        if (!active) removeClarityContent();
        else resumeClarityContent(model.contentGeneration());
        updateLayerVisibility();
    }

    /** Independent simulated factory warning source; never calls vehicle APIs. */
    public void setSimulatedStockWarningVisible(boolean visible) {
        requireOpen();
        if (visible && clarityContent != null)
            suspendClarityContent(HostedContentLifecycle.WARNING_PREEMPTION,
                    model.contentGeneration());
        model.setWarningVisible(visible);
        if (!visible) resumeClarityContent(model.contentGeneration());
        updateLayerVisibility();
    }

    public boolean isWarningVisible() { return model.isWarningVisible(); }
    public boolean isNavigationActive() { return model.isNavigationActive(); }
    public boolean hasClarityContent() { return clarityContent != null; }
    public boolean ownsClarityContent(View content, long generation) {
        return clarityContent == content && model.contentGeneration() == generation;
    }
    public long contentGeneration() { return model.contentGeneration(); }
    public boolean isClosed() { return model.isClosed(); }

    private void updateLayerVisibility() {
        warningInterruptRoot.setVisibility(model.isWarningVisible() ? View.VISIBLE : View.GONE);
        navigationRoot.setVisibility(model.isNavigationActive() && !model.isWarningVisible() ? View.VISIBLE : View.GONE);
        simulatedWarning.setVisibility(model.isWarningVisible() ? View.VISIBLE : View.GONE);
        customContentContainer.setVisibility(model.contentVisible() ? View.VISIBLE : View.GONE);
    }

    private void removeClarityContent() {
        if (clarityContent != null) model.detach(model.contentGeneration());
        removeViewOnly();
    }

    private void removeViewOnly() {
        if (clarityContent != null) customContentContainer.removeView(clarityContent);
        clarityContent = null;
        customContentContainer.setVisibility(View.GONE);
    }

    private void suspendClarityContent(int reason, long generation) {
        if (clarityContent instanceof HostedContentLifecycle)
            ((HostedContentLifecycle) clarityContent).onHostSuspended(reason, generation);
    }

    private void resumeClarityContent(long generation) {
        if (clarityContent instanceof HostedContentLifecycle && generation > 0)
            ((HostedContentLifecycle) clarityContent).onHostResumed(generation);
    }

    /** Idempotently remove only simulator-owned content and roots. */
    public void close() {
        if (model.isClosed()) return;
        requireUiThread();
        if (clarityContent != null)
            suspendClarityContent(HostedContentLifecycle.HOST_CLOSED, model.contentGeneration());
        removeClarityContent();
        model.close();
        warningInterruptRoot.removeAllViews();
        navigationRoot.removeAllViews();
        displayRoot.removeAllViews();
    }

    private void requireOpen() {
        requireUiThread();
        if (model.isClosed()) throw new IllegalStateException("simulator is closed");
    }

    private static void requireUiThread() {
        if (Looper.myLooper() != Looper.getMainLooper())
            throw new IllegalStateException("simulator mutations must run on the UI thread");
    }
}
