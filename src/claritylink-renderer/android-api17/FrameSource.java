package org.claritylink.renderer;

/**
 * Bounded producer contract for project-owned laboratory frames.
 * Implementations receive a caller-owned generation and never acquire a display.
 */
public interface FrameSource {
    /** Returns the next owned CPU frame, or null when a finite source is exhausted. */
    DecodedFrame nextFrame(long generation);

    /** Prevents further frame production and releases source-owned resources. */
    void close();
}
