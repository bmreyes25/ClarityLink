package org.claritylink.renderer;

/** One-slot in-flight gate shared by decoded-frame IPC adapters. */
public final class FrameBackpressureGate {
    private boolean occupied;
    private boolean closed;

    public synchronized boolean tryAcquire() {
        if (closed || occupied) return false;
        occupied = true;
        return true;
    }

    public synchronized void release() { occupied = false; }
    public synchronized void close() { closed = true; occupied = false; }
    public synchronized boolean isOccupied() { return occupied; }
}
