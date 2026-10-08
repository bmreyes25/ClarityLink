package org.claritylink.android;

import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioTrack;
import android.content.Context;

/** Generic bounded PCM output. Routing is Android-selected; no Honda route is assumed. */
public final class AndroidAudioAdapter {
    public static final int MAX_WRITE_BYTES = 256 * 1024;
    private AudioTrack track;
    private final AudioManager audioManager;
    private boolean paused;
    private boolean focusHeld;
    private int errorState;
    private int channels;
    private int encoding;
    private final AudioManager.OnAudioFocusChangeListener focusListener = new AudioManager.OnAudioFocusChangeListener() {
        public void onAudioFocusChange(int change) {
            synchronized(AndroidAudioAdapter.this) {
                try {
                    if(change<=AudioManager.AUDIOFOCUS_LOSS_TRANSIENT && track!=null) { track.pause(); paused=true; }
                    else if(change==AudioManager.AUDIOFOCUS_GAIN && track!=null && paused) { track.play(); paused=false; }
                } catch(RuntimeException e) { errorState=AudioTrack.ERROR_INVALID_OPERATION; }
            }
        }
    };
    public AndroidAudioAdapter(Context context) {
        audioManager=(AudioManager)context.getSystemService(Context.AUDIO_SERVICE);
        if(audioManager==null) throw new IllegalStateException("AudioManager unavailable");
    }
    public synchronized int errorState() { return errorState; }
    public synchronized boolean open(int sampleRate, int channels, int encoding) {
        close();
        errorState=0;
        if (sampleRate < 8000 || sampleRate > 192000 || (channels != 1 && channels != 2) ||
            (encoding != AudioFormat.ENCODING_PCM_16BIT && encoding != AudioFormat.ENCODING_PCM_8BIT)) { errorState=AudioTrack.ERROR_BAD_VALUE; return false; }
        if(audioManager.requestAudioFocus(focusListener,AudioManager.STREAM_MUSIC,AudioManager.AUDIOFOCUS_GAIN)!=AudioManager.AUDIOFOCUS_REQUEST_GRANTED) {
            errorState=AudioManager.AUDIOFOCUS_REQUEST_FAILED; return false;
        }
        focusHeld=true;
        int mask = channels == 1 ? AudioFormat.CHANNEL_OUT_MONO : AudioFormat.CHANNEL_OUT_STEREO;
        int min = AudioTrack.getMinBufferSize(sampleRate,mask,encoding);
        if (min <= 0 || min > MAX_WRITE_BYTES) { errorState=AudioTrack.ERROR_BAD_VALUE; close(); return false; }
        try { track = new AudioTrack(AudioManager.STREAM_MUSIC,sampleRate,mask,encoding,min,AudioTrack.MODE_STREAM); }
        catch(RuntimeException e) { errorState=AudioTrack.ERROR_INVALID_OPERATION; close(); throw e; }
        if (track.getState() != AudioTrack.STATE_INITIALIZED) { errorState=AudioTrack.STATE_UNINITIALIZED; track.release(); track=null; close(); return false; }
        this.channels=channels; this.encoding=encoding;
        try { track.play(); } catch(RuntimeException e) { errorState=AudioTrack.ERROR_INVALID_OPERATION; close(); throw e; }
        paused=false; return true;
    }
    public synchronized int write(byte[] pcm, int offset, int length) {
        int bytesPerSample=encoding==AudioFormat.ENCODING_PCM_16BIT?2:1;
        if (track == null || pcm == null || offset < 0 || length < 0 || length > MAX_WRITE_BYTES ||
            offset > pcm.length-length || (offset%(bytesPerSample*channels))!=0 || (length%(bytesPerSample*channels))!=0)
            return AudioTrack.ERROR_BAD_VALUE;
        int result=track.write(pcm,offset,length); if(result<0) errorState=result; return result;
    }
    public synchronized void pause() { if (track != null && !paused) { track.pause(); paused=true; } }
    public synchronized void resume() { if (track != null && paused) { track.play(); paused=false; } }
    public synchronized void flush() { if (track != null) track.flush(); }
    public synchronized void close() {
        AudioTrack old=track; track=null; paused=false; channels=encoding=0;
        try { if(old!=null) { try { old.pause(); old.flush(); } finally { old.release(); } } }
        finally { if(focusHeld) { audioManager.abandonAudioFocus(focusListener); focusHeld=false; } }
    }
}
