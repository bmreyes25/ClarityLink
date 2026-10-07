package org.claritylink.android;

import android.content.Context;
import android.view.Surface;
import android.view.SurfaceHolder;
import android.view.SurfaceView;

/** Generic Display0 SurfaceView host; admission/window policy is supplied by its Activity. */
public class PrimaryDisplayHost extends SurfaceView implements SurfaceHolder.Callback {
    public interface Listener { void onSurface(Surface surface); void onSurfaceLost(); }
    private Listener listener;
    public PrimaryDisplayHost(Context context) { super(context); getHolder().addCallback(this); }
    public void setListener(Listener value) { listener = value; }
    public void surfaceCreated(SurfaceHolder holder) { if (listener != null) listener.onSurface(holder.getSurface()); }
    public void surfaceChanged(SurfaceHolder holder,int format,int width,int height) {
        if (width <= 0 || height <= 0) throw new IllegalArgumentException("invalid primary surface size");
    }
    public void surfaceDestroyed(SurfaceHolder holder) { if (listener != null) listener.onSurfaceLost(); }
    public void clear(long nativeSurfaceHandle,long generation) {
        NativeBridge.nativeClearSurface(nativeSurfaceHandle,generation);
    }
}
