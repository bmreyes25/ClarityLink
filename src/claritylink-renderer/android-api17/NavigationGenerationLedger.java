package org.claritylink.renderer;

/** Caller-owned generation high-water mark retained across synthetic host recreation. */
public final class NavigationGenerationLedger {
    private long highestGeneration;

    public synchronized boolean advanceTo(long generation) {
        if (generation <= highestGeneration) return false;
        highestGeneration = generation;
        return true;
    }

    public synchronized long highestGeneration() { return highestGeneration; }
}
