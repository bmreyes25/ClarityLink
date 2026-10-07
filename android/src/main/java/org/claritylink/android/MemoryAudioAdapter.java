package org.claritylink.android;

/** Offline backend with the same format/write/lifecycle limits as the Android sink contract. */
public final class MemoryAudioAdapter {
    private boolean open,paused;
    private int sampleRate,channels,encoding;
    private long bytesWritten;
    public boolean open(int rate,int channels,int encoding) {
        close(); if(rate<8000 || rate>192000 || (channels!=1 && channels!=2) || (encoding!=8 && encoding!=16)) return false;
        sampleRate=rate; this.channels=channels; this.encoding=encoding; open=true; return true;
    }
    public boolean write(byte[] bytes,int offset,int length) {
        int bytesPerSample=encoding==16?2:1;
        if(!open || bytes==null || offset<0 || length<0 || length>AndroidAudioAdapter.MAX_WRITE_BYTES ||
           offset>bytes.length-length || offset%(bytesPerSample*channels)!=0 || length%(bytesPerSample*channels)!=0) return false;
        bytesWritten=Math.min(Long.MAX_VALUE-bytesWritten,length)+bytesWritten; return true;
    }
    public void pause() { if(open) paused=true; }
    public void resume() { if(open) paused=false; }
    public void flush() { bytesWritten=0; }
    public void close() { open=false; paused=false; sampleRate=channels=encoding=0; bytesWritten=0; }
    public boolean isOpen() { return open; }
    public boolean isPaused() { return paused; }
    public long bytesWritten() { return bytesWritten; }
}
