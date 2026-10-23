package org.claritylink.renderer;

import android.os.Handler;
import android.os.Looper;
import java.util.ArrayList;
import java.util.List;

/** Single-use, revocable authority to present into one simulated pane generation. */
public final class PaneLease {
    public interface RevocationCallback { void onRevoked(PaneLease lease); }
    private static final Handler MAIN_HANDLER = new Handler(Looper.getMainLooper());

    private final long paneGeneration;
    private boolean valid = true;
    private List<RevocationCallback> callbacks = new ArrayList<RevocationCallback>();

    PaneLease(long paneGeneration) {
        if (paneGeneration <= 0) throw new IllegalArgumentException("positive pane generation required");
        this.paneGeneration = paneGeneration;
    }

    public long paneGeneration() { return paneGeneration; }
    public synchronized boolean isValid() { return valid; }

    public void addRevocationCallback(RevocationCallback callback) {
        if (callback == null) throw new IllegalArgumentException("callback required");
        boolean invoke;
        synchronized (this) {
            invoke = !valid;
            if (!invoke) callbacks.add(callback);
        }
        if (invoke) dispatch(callback);
    }

    void revoke() {
        List<RevocationCallback> pending;
        synchronized (this) {
            if (!valid) return;
            valid = false;
            pending = callbacks;
            callbacks = null;
        }
        for (int i = 0; i < pending.size(); i++) dispatch(pending.get(i));
    }

    private void dispatch(final RevocationCallback callback) {
        if (Looper.myLooper() == Looper.getMainLooper()) runContained(callback);
        else MAIN_HANDLER.post(new Runnable() {
            public void run() { runContained(callback); }
        });
    }

    private void runContained(RevocationCallback callback) {
        try { callback.onRevoked(this); } catch (RuntimeException ignored) { }
    }
}
