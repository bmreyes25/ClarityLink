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
    /** Optional hook for a host-owned content View that uses the Presentation display context. */
    public interface HostedContentListener extends Listener { void presentationRoot(FrameLayout root); }
    private Candidate presentation;
    private long generation;
    private boolean surfaceAttached;
    private boolean closing;
    private Listener listener;
    private final Handler mainHandler=new Handler(Looper.getMainLooper());
    public SecondaryDisplayHost(Listener listener) { this.listener = listener; }
    public boolean show(Context context, Display display, long generation,
                        DisplayPolicy.WarningVisibilityPolicy warningPolicy,
                        DisplayPolicy.Layout layout) {
        return showInternal(context, display, generation, warningPolicy, layout, false);
    }
    /** Synthetic-only adapter retained for API17 emulator compatibility tests. */
    boolean showOfflineLabForRuntimeTest(Context context, Display display, long generation,
                                         DisplayPolicy.Layout layout) {
        requireMainThread();
        if (!DisplayPolicy.isIsolatedApi17EmulatorBuild()) {
            close();
            state(DisplayPolicy.Admission.BLOCKED_HONDA_SAFETY);
            return false;
        }
        if (layout == null || !layout.testOnly) {
            close();
            state(DisplayPolicy.Admission.FAULTED);
            return false;
        }
        return showInternal(context, display, generation,
                DisplayPolicy.WarningVisibilityPolicy.unknown(), layout, true);
    }
    private boolean showInternal(Context context, Display display, long generation,
                        DisplayPolicy.WarningVisibilityPolicy warningPolicy,
                        DisplayPolicy.Layout layout, boolean offlineLab) {
        requireMainThread(); close();
        if (display == null || !display.isValid() || generation <= 0 || warningPolicy == null ||
            layout == null) {
            state(DisplayPolicy.Admission.FAULTED); return false;
        }
        // There is deliberately no lab or caller-controlled bypass in this
        // production host. Presentation admission remains disabled until a
        // separately reviewed Honda-safe policy exists.
        if (offlineLab) {
            if (!DisplayPolicy.isIsolatedApi17EmulatorBuild() || !layout.testOnly) {
                state(DisplayPolicy.Admission.BLOCKED_HONDA_SAFETY);
                return false;
            }
        } else if (!warningPolicy.safeForHonda() || layout.testOnly) {
            state(DisplayPolicy.Admission.BLOCKED_HONDA_SAFETY);
            return false;
        }
        this.generation = generation;
        surfaceAttached=false;
        state(DisplayPolicy.Admission.DISPLAY_ENUMERATED);
        try {
            context.createDisplayContext(display);
            state(DisplayPolicy.Admission.DISPLAY_CONTEXT_READY);
            presentation = new Candidate(context, display, layout, generation);
            state(DisplayPolicy.Admission.WINDOW_CONSTRUCTED);
            state(DisplayPolicy.Admission.WINDOW_ADMISSION_REQUESTED);
            presentation.show();
            state(offlineLab ? DisplayPolicy.Admission.WINDOW_ADMITTED_LAB :
                    DisplayPolicy.Admission.PRESENTATION_SHOWN);
            return true;
        } catch (RuntimeException e) {
            close(); state(DisplayPolicy.Admission.WINDOW_REJECTED);
            if (listener != null) listener.error("presentation-admission", e.getClass().getName());
            return false;
        }
    }
    public void close() {
        requireMainThread();
        if (closing) return;
        closing=true;
        Candidate old=presentation;
        boolean hadSurface=surfaceAttached;
        presentation=null;
        generation=0;
        surfaceAttached=false;
        try {
            if (old != null) {
                state(DisplayPolicy.Admission.DISMISS_REQUESTED);
                old.dismiss();
                // Dialog.dismiss() is a local request. Independent WMS evidence is
                // required before reporting WINDOW_REMOVED_VERIFIED.
            }
        } catch (RuntimeException failure) {
            error("presentation-dismiss", failure);
        } finally {
            if (hadSurface && listener != null) {
                try { listener.surface(null); }
                catch (RuntimeException failure) { error("surface-release-notification", failure); }
            }
            closing=false;
        }
    }
    boolean destroySurfaceForRuntimeTest() {
        requireMainThread();
        return presentation!=null && presentation.destroyLabSurface();
    }
    boolean recreateSurfaceForRuntimeTest() {
        requireMainThread();
        return presentation!=null && presentation.recreateLabSurface();
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
    private void state(DisplayPolicy.Admission s) {
        if (listener != null) {
            try { listener.state(s); }
            catch (RuntimeException failure) { error("admission-state-notification", failure); }
        }
    }
    private void error(String operation, RuntimeException failure) {
        if (listener != null) {
            try { listener.error(operation, failure.getClass().getName()); }
            catch (RuntimeException ignored) { /* A listener cannot prevent cleanup. */ }
        }
    }
    private final class Candidate extends Presentation {
        private final DisplayPolicy.Layout layout;
        private final long candidateGeneration;
        private FrameLayout root;
        private SurfaceView surfaceView;
        Candidate(Context context, Display display, DisplayPolicy.Layout layout,long generation) {
            super(context, display); this.layout=layout; candidateGeneration=generation;
        }
        protected void onCreate(Bundle state) {
            super.onCreate(state);
            root = new FrameLayout(getContext());
            attachLabSurface();
            setContentView(root);
            if (listener instanceof HostedContentListener && generation == candidateGeneration &&
                    presentation == Candidate.this) {
                ((HostedContentListener) listener).presentationRoot(root);
            }
        }
        private void attachLabSurface() {
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
            surfaceView=view;
            root.addView(view);
        }
        private boolean destroyLabSurface() {
            if(!layout.testOnly || root==null || surfaceView==null) return false;
            SurfaceView old=surfaceView; surfaceView=null; root.removeView(old); return true;
        }
        private boolean recreateLabSurface() {
            if(!layout.testOnly || root==null || surfaceView!=null) return false;
            attachLabSurface(); return true;
        }
        public void onDisplayRemoved() {
            super.onDisplayRemoved();
            if(generation==candidateGeneration && presentation==Candidate.this) {
                surfaceAttached=false;
                if(listener!=null) listener.surface(null);
                state(DisplayPolicy.Admission.FAULTED);
                if(!closing) close();
            }
        }
    }
}
