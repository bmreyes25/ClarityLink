package org.claritylink.renderer;

import android.os.Handler;
import android.os.HandlerThread;
import android.os.Looper;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import java.util.WeakHashMap;

/** API 17 renderer adapter for a caller-supplied synthetic host. */
public final class Display1OutputBackend {
    public interface Host {
        FrameLayout getMainLayer();
        boolean isNavigationPageActive();
        boolean attachContent(View content, long generation);
        boolean detachContent(View content, long generation);
    }
    public interface PaneEventListener { void onPaneEvent(PaneEvent event); }
    /** Optional extension preserves source compatibility for existing Host implementations. */
    public interface EventHost extends Host {
        void addPaneEventListener(PaneEventListener listener);
        void removePaneEventListener(PaneEventListener listener);
        boolean isHostValid();
        boolean isInterruptActive();
        RendererViewport getPaneViewport();
        Object generationOwner();
    }
    public enum PresentStatus {
        PRESENTED, LEASE_INVALID, IDENTITY_MISMATCH, STALE_SEQUENCE,
        MALFORMED, UNSUPPORTED_STORAGE, GEOMETRY
    }

    public static final class Viewport {
        public final int left, top, width, height;
        public Viewport(int left, int top, int width, int height) {
            if (left < 0 || top < 0 || width <= 0 || height <= 0
                    || (long) left + width > 800L || (long) top + height > 480L)
                throw new IllegalArgumentException("viewport must fit Display 1 800x480");
            this.left = left; this.top = top; this.width = width; this.height = height;
        }
    }

    private static final WeakHashMap<Object, Long> USED_GENERATIONS = new WeakHashMap<Object, Long>();
    private final Host host;
    private final EventHost eventHost;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private final Viewport viewport;
    private volatile long generation;
    private volatile long paneGeneration;
    private long attachmentGeneration;
    private long attachSerial;
    private long lastEventSequence;
    private volatile long lastSubmittedTimestampNs = -1L;
    private volatile long activeStreamGeneration;
    private volatile long lastGateGeneration;
    private volatile RendererViewport rendererViewport;
    private FrameLayout root;
    private volatile ClarityLinkContentView view;
    /** One converter thread for the backend's lifetime, shared by every View it attaches. */
    private HandlerThread sharedConverter;
    private volatile PaneLease lease;
    private PaneEventListener listener;
    private volatile FrameDispatchGate activeGate;
    private volatile boolean closed;
    private boolean hostAvailable = true;
    private volatile boolean paneViewportValid = true;

    public Display1OutputBackend(Host host, Viewport viewport) {
        this(host, viewport, 1L, RendererViewport.fullCanvasTestOnly());
    }
    public Display1OutputBackend(Host host, Viewport viewport, long generation) {
        this(host, viewport, generation, RendererViewport.fullCanvasTestOnly());
    }
    public Display1OutputBackend(Host host, Viewport viewport, long generation,
            RendererViewport rendererViewport) {
        if (host == null || viewport == null || rendererViewport == null)
            throw new IllegalArgumentException("host, viewport, and renderer geometry required");
        if (generation <= 0) throw new IllegalArgumentException("positive generation required");
        this.host = host;
        this.eventHost = host instanceof EventHost ? (EventHost) host : null;
        this.viewport = viewport;
        this.generation = generation;
        this.paneGeneration = generation;
        this.rendererViewport = rendererViewport;
    }

    public synchronized void attach() { attach(paneGeneration); }

    /** Explicit recovery always requires a generation newer than this host has used. */
    public synchronized void attach(long newPaneGeneration) {
        requireUiThread();
        if (closed) throw new IllegalStateException("backend is closed");
        if (eventHost == null) throw new IllegalStateException("pane leases require a callback-capable simulated host");
        if (lease != null && lease.isValid()) throw new IllegalStateException("already attached");
        if (newPaneGeneration <= 0) throw new IllegalArgumentException("positive pane generation required");
        if (listener != null) unsubscribe();
        if (eventHost != null) hostAvailable = eventHost.isHostValid();
        Object owner = eventHost == null ? host : eventHost.generationOwner();
        synchronized (USED_GENERATIONS) {
            Long previous = USED_GENERATIONS.get(owner);
            if (previous != null && newPaneGeneration <= previous.longValue())
                throw new IllegalArgumentException("pane generation must increase for host lifetime");
            USED_GENERATIONS.put(owner, Long.valueOf(newPaneGeneration));
        }
        paneGeneration = newPaneGeneration;
        final long serial = ++attachSerial;
        try {
            if (eventHost != null) {
                listener = new PaneEventListener() {
                    public void onPaneEvent(final PaneEvent event) {
                        if (event == null) return;
                        if (Looper.myLooper() == Looper.getMainLooper()) acceptEvent(event, serial);
                        else mainHandler.post(new Runnable() {
                            public void run() { acceptEvent(event, serial); }
                        });
                    }
                };
                eventHost.addPaneEventListener(listener);
            }
            if (!hostAvailable || !host.isNavigationPageActive() || (eventHost != null &&
                    (!eventHost.isHostValid() || eventHost.isInterruptActive() ||
                     eventHost.getPaneViewport() == null || !paneViewportValid)))
                throw new IllegalStateException("simulated pane host is unavailable");
            root = host.getMainLayer();
            if (root == null) throw new IllegalStateException("simulated pane layer unavailable");
        } catch (RuntimeException failure) {
            unsubscribe();
            throw failure;
        }
        final PaneLease newLease = new PaneLease(newPaneGeneration);
        lease = newLease;
        newLease.addRevocationCallback(new PaneLease.RevocationCallback() {
            public void onRevoked(PaneLease revoked) { releaseView(revoked, serial); }
        });
        try {
            if (sharedConverter == null || !sharedConverter.isAlive()) {
                sharedConverter = new HandlerThread("ClarityLinkFrameConvert");
                sharedConverter.start();
            }
            view = new ClarityLinkContentView(root.getContext());
            view.useSharedConverter(sharedConverter);
            view.setRendererViewport(rendererViewport);
            view.beginSession(generation);
            attachmentGeneration = newPaneGeneration;
            lastSubmittedTimestampNs = -1L;
            activeStreamGeneration = 0L;
            FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(
                    viewport.width, viewport.height, Gravity.TOP | Gravity.LEFT);
            params.leftMargin = viewport.left;
            params.topMargin = viewport.top;
            view.setLayoutParams(params);
            if (!host.attachContent(view, newPaneGeneration))
                throw new IllegalStateException("host rejected content View");
        } catch (RuntimeException failure) {
            newLease.revoke();
            unsubscribe();
            throw failure;
        }
    }

    public synchronized PresentStatus submit(DecodedFrame frame) {
        return submit(frame, null, activeStreamGeneration == 0L ? generation : activeStreamGeneration, -1L);
    }
    public synchronized PresentStatus submit(DecodedFrame frame, FrameDispatchGate gate, long dispatchEpoch) {
        return submit(frame, gate,
                activeStreamGeneration == 0L ? generation : activeStreamGeneration, dispatchEpoch);
    }
    public synchronized PresentStatus submit(DecodedFrame frame, FrameDispatchGate gate,
            long streamGeneration, long dispatchEpoch) {
        if (frame == null) return PresentStatus.MALFORMED;
        if (lease == null || !lease.isValid() || view == null || closed) return PresentStatus.LEASE_INVALID;
        if (streamGeneration <= 0) throw new IllegalArgumentException("positive stream generation required");
        if (activeStreamGeneration != 0L && streamGeneration != activeStreamGeneration)
            return PresentStatus.IDENTITY_MISMATCH;
        if (frame.presentationTimeNs <= lastSubmittedTimestampNs) return PresentStatus.STALE_SEQUENCE;
        RendererViewport.Bounds safe = rendererViewport.safeArea();
        int cropWidth = frame.cropRight - frame.cropLeft;
        int cropHeight = frame.cropBottom - frame.cropTop;
        if (frame.rotationDegrees == 90 || frame.rotationDegrees == 270) {
            int swap = cropWidth; cropWidth = cropHeight; cropHeight = swap;
        }
        if (cropWidth > Math.min(viewport.width, safe.right - safe.left) ||
                cropHeight > Math.min(viewport.height, safe.bottom - safe.top))
            return PresentStatus.GEOMETRY;
        if (eventHost != null && (!eventHost.isHostValid() || !host.isNavigationPageActive() ||
                eventHost.isInterruptActive())) return PresentStatus.LEASE_INVALID;
        if (gate != null) {
            activeGate = gate;
            lastGateGeneration = streamGeneration;
        }
        long gateGeneration = gate == null ? generation : streamGeneration;
        if (!view.submitFrame(frame, generation, gate, gateGeneration, dispatchEpoch))
            return PresentStatus.STALE_SEQUENCE;
        if (activeStreamGeneration == 0L) activeStreamGeneration = streamGeneration;
        lastSubmittedTimestampNs = frame.presentationTimeNs;
        return PresentStatus.PRESENTED;
    }

    /** Non-CPU objects are rejected as ordinary unsupported storage, not programmer errors. */
    public synchronized PresentStatus submit(Object frame) {
        if (frame == null) return PresentStatus.MALFORMED;
        return frame instanceof DecodedFrame ? submit((DecodedFrame) frame) : PresentStatus.UNSUPPORTED_STORAGE;
    }

    public void clear() { requireUiThread(); if (view != null) view.clearFrame(); }

    /**
     * Applies an accepted Type111 ViewArea/SafeArea to the live View inside the current lease.
     * This is presentation geometry admitted by the matching control identity, not a change of
     * the host's destination viewport. A host viewport change arrives as a PaneEvent and revokes
     * the lease; this method never does, and it refuses to act without a valid lease and View.
     */
    public synchronized void setRendererViewport(RendererViewport viewport) {
        requireUiThread();
        if (viewport == null) throw new IllegalArgumentException("viewport required");
        ClarityLinkContentView current = view;
        if (lease == null || !lease.isValid() || current == null || closed)
            throw new IllegalStateException("not attached");
        current.setRendererViewport(viewport);
        rendererViewport = viewport;
    }

    /** Changes frame/config identity inside the current pane lease only. */
    public synchronized void replaceGeneration(long oldGeneration, long newGeneration) {
        requireUiThread();
        if (lease == null || !lease.isValid() || view == null || generation != oldGeneration ||
                newGeneration <= oldGeneration) throw new IllegalStateException("renderer generation mismatch");
        view.replaceSessionGeneration(oldGeneration, newGeneration);
        generation = newGeneration;
        lastSubmittedTimestampNs = -1L;
    }

    public synchronized void close() {
        requireUiThread();
        if (closed) return;
        closed = true;
        unsubscribe();
        revokeLease();
        if (sharedConverter != null) {
            sharedConverter.quit();   // discards any queued conversion; no View remains to use it
            sharedConverter = null;
        }
    }

    public PaneLease paneLease() { return lease; }
    public ClarityLinkContentView contentView() { return view; }
    public long paneGeneration() { return paneGeneration; }

    private synchronized void acceptEvent(PaneEvent event, long serial) {
        requireUiThread();
        if (closed || serial != attachSerial || listener == null || event.sequence <= lastEventSequence) return;
        lastEventSequence = event.sequence;
        switch (event.type) {
            case PAGE_DESELECTED: case INTERRUPT_ON: case HOST_LOST: case VIEWPORT_CHANGED:
                if (event.type == PaneEvent.Type.HOST_LOST) hostAvailable = false;
                if (event.type == PaneEvent.Type.INTERRUPT_ON && activeGate != null && lastGateGeneration > 0)
                    activeGate.setWarningVisible(lastGateGeneration, true);
                if (event.type == PaneEvent.Type.VIEWPORT_CHANGED) {
                    paneViewportValid = event.viewport != null;
                    if (event.viewport != null) rendererViewport = event.viewport;
                }
                revokeLease();
                break;
            case HOST_RESTORED:
                hostAvailable = event.valid;
                if (!event.valid) revokeLease();
                break;
            case PAGE_SELECTED:
            case INTERRUPT_OFF:
                // State notifications never create or revive authority.
                break;
        }
    }

    private void revokeLease() {
        PaneLease current = lease;
        if (current != null) current.revoke();
        if (listener != null) unsubscribe();
    }

    private synchronized void releaseView(final PaneLease revoked, final long serial) {
        if (Looper.myLooper() != Looper.getMainLooper()) {
            mainHandler.post(new Runnable() { public void run() { releaseView(revoked, serial); } });
            return;
        }
        if (lease != revoked || serial != attachSerial) return;
        ClarityLinkContentView old = view;
        long oldGeneration = attachmentGeneration;
        view = null; root = null; activeGate = null; lastGateGeneration = 0L;
        if (old != null) {
            try { host.detachContent(old, oldGeneration); }
            catch (RuntimeException ignored) { }
            old.close();
        }
    }

    private void unsubscribe() {
        PaneEventListener old = listener;
        listener = null;
        if (old != null && eventHost != null) {
            try { eventHost.removePaneEventListener(old); } catch (RuntimeException ignored) { }
        }
    }

    private static void requireUiThread() {
        if (Looper.myLooper() != Looper.getMainLooper())
            throw new IllegalStateException("renderer lifecycle must run on the UI thread");
    }
}
