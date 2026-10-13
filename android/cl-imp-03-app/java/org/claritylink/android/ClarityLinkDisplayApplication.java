package org.claritylink.android;

import android.app.Application;
import java.util.concurrent.atomic.AtomicLong;

/** Process-local lifecycle owner. Nothing is persisted or started at boot. */
public final class ClarityLinkDisplayApplication extends Application {
    private final AtomicLong generation = new AtomicLong(0L);

    public long nextGeneration() {
        long next = generation.incrementAndGet();
        if (next <= 0L) throw new IllegalStateException("session generation exhausted");
        return next;
    }
}
