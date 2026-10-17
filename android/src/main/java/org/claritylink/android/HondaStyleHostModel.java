package org.claritylink.android;

/** Pure-Java lifecycle and priority model shared by the API17 host simulator. */
public final class HondaStyleHostModel {
    public enum Priority { BOTTOM_CONTENT, NAVIGATION_CONTENT, WARNING_INTERRUPT }

    private long contentGeneration;
    private boolean navigationActive = true;
    private boolean warningVisible;
    private boolean closed;

    public int priorityRank(Priority priority) {
        if (priority == null) throw new IllegalArgumentException("priority required");
        return priority.ordinal();
    }

    public boolean attach(long generation, boolean contentUnparented) {
        if (closed || generation <= 0 || !contentUnparented || !navigationActive ||
                warningVisible || contentGeneration != 0) return false;
        contentGeneration = generation;
        return true;
    }

    public boolean detach(long generation) {
        if (closed || generation <= 0 || generation != contentGeneration) return false;
        contentGeneration = 0;
        return true;
    }

    public void setNavigationActive(boolean active) {
        requireOpen();
        navigationActive = active;
        if (!active) contentGeneration = 0;
    }

    public void setWarningVisible(boolean visible) {
        requireOpen();
        warningVisible = visible;
    }

    public boolean contentVisible() {
        return !closed && navigationActive && !warningVisible && contentGeneration > 0;
    }
    public long contentGeneration() { return contentGeneration; }
    public boolean isNavigationActive() { return navigationActive; }
    public boolean isWarningVisible() { return warningVisible; }
    public boolean isClosed() { return closed; }

    public void close() {
        if (closed) return;
        contentGeneration = 0;
        warningVisible = false;
        navigationActive = false;
        closed = true;
    }

    private void requireOpen() {
        if (closed) throw new IllegalStateException("host model is closed");
    }
}
