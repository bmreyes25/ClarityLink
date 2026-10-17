package org.claritylink.android;

import android.app.Application;
import java.security.SecureRandom;
import java.util.concurrent.atomic.AtomicLong;

/** Process-local lifecycle owner. Session IDs also carry a fresh process incarnation nonce. */
public final class ClarityLinkDisplayApplication extends Application {
    private static final long SESSION_COUNTER_MASK = 0xffffL;
    private final AtomicLong generation = new AtomicLong(newProcessPrefix());

    private static long newProcessPrefix() {
        long nonce = new SecureRandom().nextLong() & 0x00007fffffffffffL;
        if (nonce == 0L) nonce = 1L;
        return nonce << 16;
    }

    public long nextGeneration() {
        long next = generation.incrementAndGet();
        if (next <= 0L || (next & SESSION_COUNTER_MASK) == 0L)
            throw new IllegalStateException("session generation exhausted");
        return next;
    }
}
