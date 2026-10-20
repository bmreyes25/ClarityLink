package org.claritylink.android;

/** Plain-Java offline stand-in preserving attach, frame, detach, and generation semantics. */
public final class MockPrimaryDisplayHost {
    private long generation;
    private boolean attached, framePresent;
    private int width,height;
    public synchronized boolean attach(long generation,int width,int height) {
        detach(); if(generation<=0 || width<=0 || height<=0) return false;
        this.generation=generation; this.width=width; this.height=height; attached=true; return true;
    }
    public synchronized boolean frame(long generation,int width,int height) {
        if(!attached || generation!=this.generation || width!=this.width || height!=this.height) return false;
        framePresent=true; return true;
    }
    public synchronized void detach() { attached=false; framePresent=false; generation=0; width=0; height=0; }
    public synchronized boolean isAttached() { return attached; }
    public synchronized boolean hasFrame() { return framePresent; }
}
