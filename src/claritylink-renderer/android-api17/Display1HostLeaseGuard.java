package org.claritylink.renderer;

import android.os.IBinder;

/**
 * CL-INT-04: host-owned end of life for a Display 1 pane lease (API 17, synthetic lab).
 *
 * <p>Wraps a {@link Display1OutputBackend} that lives in the HOST process. The lease it attaches is
 * revoked, and its View detached through the backend's existing revocation path, when
 * <ul>
 *   <li>no accepted frame renewed it within {@code ttlMillis} (timer on the host's main looper), or</li>
 *   <li>the bound producer's Binder dies ({@code linkToDeath}).</li>
 * </ul>
 * Neither needs a producer tick, heartbeat or cleanup callback. Limits: the timer needs a responsive
 * host main looper; the backend's host-event listener is released at the next {@code attach} or
 * {@code close}, not at expiry (it is inert once the lease is revoked).
 */
public final class Display1HostLeaseGuard {
    private final Display1OutputBackend backend;
    private final long ttlMillis;

    public Display1HostLeaseGuard(Display1OutputBackend backend, long ttlMillis) {
        if (backend == null) throw new IllegalArgumentException("backend required");
        if (ttlMillis <= 0) throw new IllegalArgumentException("positive ttl required");
        this.backend = backend;
        this.ttlMillis = ttlMillis;
    }

    /** Attaches a pane generation and arms host expiry for the new lease (UI thread, like attach). */
    public void attach(long paneGeneration) {
        backend.attach(paneGeneration);
        PaneLease lease = backend.paneLease();
        if (lease != null) lease.armHostExpiry(ttlMillis);  // false (no-op) if already revoked
    }

    /**
     * Ties the current lease to the producer's Binder. False when the lease is already revoked,
     * which includes a Binder that is already dead.
     */
    public boolean bindProducer(IBinder producer) {
        PaneLease lease = backend.paneLease();
        return lease != null && lease.isValid() && lease.revokeOnProducerDeath(producer);
    }

    /** Presents a frame; an accepted frame is progress and renews the host ttl. */
    public Display1OutputBackend.PresentStatus submit(DecodedFrame frame) {
        return renewIfPresented(backend.submit(frame));
    }

    /** For callers using the gated {@code submit} overloads: pass their status through here. */
    public Display1OutputBackend.PresentStatus renewIfPresented(Display1OutputBackend.PresentStatus status) {
        if (status == Display1OutputBackend.PresentStatus.PRESENTED) {
            PaneLease lease = backend.paneLease();
            if (lease != null) lease.armHostExpiry(ttlMillis);  // false (no-op) once revoked
        }
        return status;
    }
}
