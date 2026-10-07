package org.claritylink.android;

import android.app.Presentation;
import android.content.Context;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Display;
import android.view.Surface;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.Gravity;
import android.widget.FrameLayout;

/** Admission candidate only. Each state means only that specific step succeeded. */
public final class SecondaryDisplayHost {
    public interface Listener { void state(DisplayPolicy.Admission state); void surface(Surface surface); void error(String operation, String exceptionType); }
    private Candidate presentation;
    private long generation;
    private boolean surfaceAttached;
    private Listener listener;
    private final Handler mainHandler=new Handler(Looper.getMainLooper());
    public SecondaryDisplayHost(Listener listener) { this.listener = listener; }
    public boolean show(Context context, Display display, long generation,
                        DisplayPolicy.WarningVisibilityPolicy warningPolicy,
                        DisplayPolicy.Layout layout) {
        requireMainThread(); close();
        if (display == null || !display.isValid() || generation <= 0 || warningPolicy == null ||
            !warningPolicy.safeForHonda() || layout == null || layout.testOnly) {
            state(DisplayPolicy.Admission.FAILED); return false;
        }
        this.generation = generation;
        surfaceAttached=false;
        state(DisplayPolicy.Admission.DISPLAY_ENUMERATED);
        try {
            context.createDisplayContext(display);
            state(DisplayPolicy.Admission.DISPLAY_CONTEXT_CREATED);
            presentation = new Candidate(context, display, layout, generation);
            state(DisplayPolicy.Admission.PRESENTATION_CONSTRUCTED);
            presentation.show();
            state(DisplayPolicy.Admission.PRESENTATION_SHOWN);
            return true;
        } catch (RuntimeException e) {
            close(); state(DisplayPolicy.Admission.FAILED);
            if (listener != null) listener.error("presentation-admission", e.getClass().getName());
            return false;
        }
    }
    public void close() {
        requireMainThread(); Candidate old=presentation; boolean detach=surfaceAttached;
        presentation=null; surfaceAttached=false;
        if(detach && listener!=null) listener.surface(null);
        if(old!=null) old.dismiss();
    }
    /** Called by the generation owner after native present() reports success. */
    public void firstFramePresented(final long frameGeneration) {
        mainHandler.post(new Runnable() { public void run() {
            if(presentation!=null && surfaceAttached && frameGeneration==generation)
                state(DisplayPolicy.Admission.FIRST_FRAME_PRESENTED);
        }});
    }
    private static void requireMainThread() {
        if(Looper.myLooper()!=Looper.getMainLooper()) throw new IllegalStateException("display host must be used on the UI thread");
    }
    private void state(DisplayPolicy.Admission s) { if (listener != null) listener.state(s); }
    private final class Candidate extends Presentation {
        private final DisplayPolicy.Layout layout;
        private final long candidateGeneration;
        Candidate(Context context, Display display, DisplayPolicy.Layout layout,long generation) {
            super(context, display); this.layout=layout; candidateGeneration=generation;
        }
        protected void onCreate(Bundle state) {
            super.onCreate(state);
            FrameLayout root = new FrameLayout(getContext());
            SurfaceView view = new SurfaceView(getContext());
            FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(layout.width,layout.height,Gravity.TOP|Gravity.LEFT);
            lp.leftMargin=layout.x; lp.topMargin=layout.y; view.setLayoutParams(lp);
            view.setRotation(layout.rotation);
            view.getHolder().addCallback(new SurfaceHolder.Callback() {
                public void surfaceCreated(SurfaceHolder holder) {
                    if(generation!=candidateGeneration || presentation!=Candidate.this) return;
                    surfaceAttached=true; state(DisplayPolicy.Admission.SURFACE_CREATED);
                    if (listener != null) listener.surface(holder.getSurface());
                }
                public void surfaceChanged(SurfaceHolder h,int f,int w,int hgt) { }
                public void surfaceDestroyed(SurfaceHolder holder) {
                    if(generation!=candidateGeneration || presentation!=Candidate.this) return;
                    surfaceAttached=false; if (listener != null) listener.surface(null);
                }
            });
            root.addView(view); setContentView(root);
        }
        public void onDisplayRemoved() {
            super.onDisplayRemoved();
            if(generation==candidateGeneration && presentation==Candidate.this) {
                surfaceAttached=false;
                if(listener!=null) listener.surface(null);
                state(DisplayPolicy.Admission.FAILED);
                close();
            }
        }
    }
}
