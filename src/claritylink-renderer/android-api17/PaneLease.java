package org.claritylink.renderer;

import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.RemoteException;
import java.util.ArrayList;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Single-use, revocable authority to present into one simulated pane generation.
 *
 * <p>CL-INT-04: the lease can also end by itself, owned by the HOST. An expiry timer posted on the
 * host's main looper revokes it unless renewed, and a Binder death link revokes it when the
 * producer process dies. Neither needs a producer tick, heartbeat or cleanup callback.
 */
public final class PaneLease {
    public interface RevocationCallback { void onRevoked(PaneLease lease); }
    private static final Handler MAIN_HANDLER = new Handler(Looper.getMainLooper());
    private static final AtomicInteger ACTIVE_EXPIRY_TIMERS = new AtomicInteger();

    private final long paneGeneration;
    private boolean valid = true;
    private List<RevocationCallback> callbacks = new ArrayList<RevocationCallback>();
    private Runnable expiry;
    private IBinder producer;
    private IBinder.DeathRecipient producerDeath;

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

    /** Host-owned expiry: revoke after {@code ttlMillis} unless renewed. False if already revoked. */
    synchronized boolean armHostExpiry(long ttlMillis) {
        if (ttlMillis <= 0) throw new IllegalArgumentException("positive ttl required");
        if (!valid) return false;
        cancelExpiryLocked();
        Runnable timer = new Runnable() { public void run() { expire(this); } };
        expiry = timer;
        ACTIVE_EXPIRY_TIMERS.incrementAndGet();
        MAIN_HANDLER.postDelayed(timer, ttlMillis);
        return true;
    }

    private void expire(Runnable fired) {
        synchronized (this) {
            if (expiry != fired) return;  // renewed or cancelled after this was queued
            expiry = null;
            ACTIVE_EXPIRY_TIMERS.decrementAndGet();
        }
        revoke();
    }

    private void cancelExpiryLocked() {
        if (expiry == null) return;
        MAIN_HANDLER.removeCallbacks(expiry);
        expiry = null;
        ACTIVE_EXPIRY_TIMERS.decrementAndGet();
    }

    /**
     * Revokes this lease if the producer's Binder dies. Returns false (lease revoked) when the Binder
     * is already dead or the lease is already revoked. The link is removed on revocation, so a stale
     * producer's late death can never touch a newer lease.
     */
    boolean revokeOnProducerDeath(IBinder binder) {
        if (binder == null) throw new IllegalArgumentException("binder required");
        IBinder.DeathRecipient recipient = new IBinder.DeathRecipient() {
            public void binderDied() { revoke(); }
        };
        boolean linked = false;
        synchronized (this) {
            if (!valid) return false;
            if (producer != null) throw new IllegalStateException("producer already bound");
            try {
                binder.linkToDeath(recipient, 0);
                producer = binder;
                producerDeath = recipient;
                linked = true;
            } catch (RemoteException alreadyDead) {
                linked = false;
            }
        }
        if (!linked) revoke();
        return linked;
    }

    static int activeExpiryTimersForTest() { return ACTIVE_EXPIRY_TIMERS.get(); }

    void revoke() {
        List<RevocationCallback> pending;
        IBinder unlinkBinder;
        IBinder.DeathRecipient unlinkRecipient;
        synchronized (this) {
            if (!valid) return;
            valid = false;
            cancelExpiryLocked();
            unlinkBinder = producer;
            unlinkRecipient = producerDeath;
            producer = null;
            producerDeath = null;
            pending = callbacks;
            callbacks = null;
        }
        if (unlinkBinder != null) {
            try { unlinkBinder.unlinkToDeath(unlinkRecipient, 0); }
            catch (NoSuchElementException ignored) { }  // already unlinked because the Binder died
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
