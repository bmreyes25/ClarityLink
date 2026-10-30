package org.claritylink.renderer;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.RectF;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.Looper;
import android.view.View;

import org.claritylink.android.HostedContentLifecycle;

/**
 * API17 custom View for owned, decoded CPU RGBA frames. One pending frame is
 * retained at a time; warning/page/host lifecycle callbacks blank and fence it.
 * This View is a laboratory renderer and does not acquire a Honda display root.
 */
public final class ClarityLinkContentView extends View implements HostedContentLifecycle {
    public interface ProfileListener {
        void onFrameProfile(long timestampNs, long bitmapCreateNs, long pixelConvertNs,
                long installQueueNs, long installNs, long invalidateToDrawNs, long drawNs);
    }
    private static final String THREAD_NAME = "ClarityLinkFrameConvert";

    private final Object stateLock = new Object();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private HandlerThread converterThread;
    private Handler converterHandler;
    /** True when the converter thread belongs to the View's owner and must outlive this View. */
    private boolean sharedConverter;
    private final Paint paint = new Paint(Paint.FILTER_BITMAP_FLAG | Paint.DITHER_FLAG);
    private RendererViewport rendererViewport = RendererViewport.fullCanvasTestOnly();

    /** Converter-thread only: one frame-sized ARGB array reused for every conversion; freed with the View. */
    private int[] argbScratch;
    private FrameEnvelope pendingFrame;
    private Bitmap pendingBitmap;
    private long pendingBitmapGeneration;
    private long pendingBitmapTimestampNs;
    private Rect pendingBitmapCrop;
    private int pendingBitmapRotation;
    private FrameDispatchGate pendingDispatchGate;
    private long pendingDispatchGeneration;
    private long pendingDispatchEpoch = -1L;
    private boolean conversionScheduled;
    private boolean installScheduled;
    private long activeGeneration;
    private long frameEpoch;
    private long latestSubmittedTimestampNs = -1L;
    private long displayedGeneration;
    private long displayedTimestampNs = -1L;
    private long drawnGeneration;
    private long drawnTimestampNs = -1L;
    private boolean hostSuspended = true;
    private boolean sessionStarted;
    private boolean closed;
    private Bitmap displayedBitmap;
    private volatile ProfileListener profileListener;
    private long pendingBitmapCreateNs;
    private long pendingPixelConvertNs;
    private long pendingInstallQueueNs;
    private long displayedBitmapCreateNs;
    private long displayedPixelConvertNs;
    private long displayedInstallQueueDurationNs;
    private long displayedInstallDurationNs;
    private long displayedInstallNs;
    private long lastProfiledDrawTimestampNs = -1L;
    private Rect displayedCrop;
    private int displayedRotation;
    private FrameDispatchGate displayedDispatchGate;
    private long displayedDispatchEpoch = -1L;
    private long displayedGateGeneration;

    public ClarityLinkContentView(Context context) {
        super(context);
        setWillNotDraw(false);
    }

    /**
     * Lets the owner supply one long-lived converter thread so that repeated attach/revoke cycles do not
     * create a native Looper (a pipe pair and an epoll descriptor) per View, whose descriptors API 17
     * releases only when the quit thread's queue is finalized. The owner quits the thread when it is done;
     * this View never does. Call on the UI thread before {@link #beginSession}.
     */
    public void useSharedConverter(HandlerThread shared) {
        requireUiThread();
        if (shared == null || !shared.isAlive()) throw new IllegalArgumentException("a running converter thread is required");
        synchronized (stateLock) {
            if (closed || sessionStarted || converterThread != null)
                throw new IllegalStateException("converter must be chosen before the session starts");
            converterThread = shared;
            converterHandler = new Handler(shared.getLooper());
            sharedConverter = true;
        }
    }

    /** Starts a fresh frame generation. Call on the Android UI thread. */
    public void beginSession(long generation) {
        requireUiThread();
        if (generation <= 0) throw new IllegalArgumentException("positive generation required");
        synchronized (stateLock) {
            if (closed) throw new IllegalStateException("content view is closed");
            if (sessionStarted) throw new IllegalStateException("content view session already started");
            sessionStarted = true;
            if (converterThread == null) {
                converterThread = new HandlerThread(THREAD_NAME);
                converterThread.start();
                converterHandler = new Handler(converterThread.getLooper());
            }
            clearQueuedLocked();
            activeGeneration = generation;
            latestSubmittedTimestampNs = -1L;
            displayedGeneration = 0L;
            displayedTimestampNs = -1L;
            drawnGeneration = 0L;
            drawnTimestampNs = -1L;
            hostSuspended = false;
        }
        clearDisplayedBitmap();
    }

    /** Replaces frame identity on the UI thread while preserving the live View/session. */
    public void replaceSessionGeneration(long oldGeneration, long newGeneration) {
        requireUiThread();
        if (oldGeneration <= 0 || newGeneration <= oldGeneration)
            throw new IllegalArgumentException("monotonic positive generation required");
        synchronized (stateLock) {
            if (closed || !sessionStarted || activeGeneration != oldGeneration)
                throw new IllegalStateException("frame session generation mismatch");
            clearQueuedLocked();
            activeGeneration = newGeneration;
            latestSubmittedTimestampNs = -1L;
            displayedGeneration = 0L;
            displayedTimestampNs = -1L;
            drawnGeneration = 0L;
            drawnTimestampNs = -1L;
            hostSuspended = false;
        }
        clearDisplayedBitmap();
    }

    /**
     * Queues an immutable DecodedFrame snapshot for conversion. Producers may
     * call from decoder threads. Newer frames replace the one pending frame.
     */
    public boolean submitFrame(final DecodedFrame frame, final long generation) {
        return submitFrame(frame, generation, null, -1L);
    }

    /** Submits a Binder frame fenced through its final Canvas draw. */
    public boolean submitFrame(final DecodedFrame frame, final long generation,
            FrameDispatchGate gate, long dispatchEpoch) {
        return submitFrame(frame, generation, gate, generation, dispatchEpoch);
    }

    /** Keeps the View's parent lifecycle generation separate from the stream dispatch generation. */
    public boolean submitFrame(final DecodedFrame frame, final long generation,
            FrameDispatchGate gate, long gateGeneration, long dispatchEpoch) {
        if (frame == null || frame.byteSize() > DecodedFrame.MAX_RGBA_BYTES) return false;
        if ((gate == null) != (dispatchEpoch < 0L)) return false;
        if ((gate == null && gateGeneration != generation) ||
                (gate != null && (gateGeneration <= 0 || !gate.mayDispatch(gateGeneration, dispatchEpoch)))) return false;
        synchronized (stateLock) {
            if (closed || hostSuspended || generation <= 0 || generation != activeGeneration
                    || frame.presentationTimeNs <= latestSubmittedTimestampNs) return false;
            latestSubmittedTimestampNs = frame.presentationTimeNs;
            pendingFrame = new FrameEnvelope(frame, generation, frameEpoch, gate, gateGeneration, dispatchEpoch);
            if (!conversionScheduled) {
                conversionScheduled = true;
                if (!converterHandler.post(new Runnable() { public void run() { convertPendingFrames(); } })) {
                    conversionScheduled = false;
                    pendingFrame = null;
                    return false;
                }
            }
            return true;
        }
    }

    private void convertPendingFrames() {
        while (true) {
            FrameEnvelope envelope;
            synchronized (stateLock) {
                if (closed || hostSuspended || pendingFrame == null) {
                    conversionScheduled = false;
                    return;
                }
                envelope = pendingFrame;
                pendingFrame = null;
            }

            Bitmap converted = null;
            long bitmapCreateNs = 0L;
            long pixelConvertNs = 0L;
            try {
                DecodedFrame frame = envelope.frame;
                ProfileListener listener = profileListener;
                long stageStartedNs = listener == null ? 0L : System.nanoTime();
                converted = Bitmap.createBitmap(frame.width, frame.height, Bitmap.Config.ARGB_8888);
                if (listener != null) bitmapCreateNs = System.nanoTime() - stageStartedNs;
                stageStartedNs = listener == null ? 0L : System.nanoTime();
                int pixelCount = frame.width * frame.height;
                int[] argb = argbScratch;
                if (argb == null || argb.length < pixelCount) {
                    argb = new int[pixelCount];
                    argbScratch = argb;
                }
                frame.toArgbPixels(argb);
                converted.setPixels(argb, 0, frame.width,
                        0, 0, frame.width, frame.height);
                if (listener != null) pixelConvertNs = System.nanoTime() - stageStartedNs;
            } catch (RuntimeException failure) {
                if (converted != null && !converted.isRecycled()) converted.recycle();
                continue;
            } catch (OutOfMemoryError exhausted) {
                if (converted != null && !converted.isRecycled()) converted.recycle();
                continue;
            }

            boolean keep;
            synchronized (stateLock) {
                FrameEnvelope newer = pendingFrame;
                keep = !closed && !hostSuspended && activeGeneration == envelope.generation
                        && frameEpoch == envelope.epoch
                        && (newer == null || newer.frame.presentationTimeNs <= envelope.frame.presentationTimeNs);
                if (keep) {
                    recyclePendingBitmapLocked();
                    pendingBitmap = converted;
                    pendingBitmapGeneration = envelope.generation;
                    pendingBitmapTimestampNs = envelope.frame.presentationTimeNs;
                    pendingBitmapCrop = envelope.frame.cropRect();
                    pendingBitmapRotation = envelope.frame.rotationDegrees;
                    pendingBitmapCreateNs = bitmapCreateNs;
                    pendingPixelConvertNs = pixelConvertNs;
                    pendingInstallQueueNs = profileListener == null ? 0L : System.nanoTime();
                    pendingDispatchGate = envelope.gate;
                    pendingDispatchGeneration = envelope.gateGeneration;
                    pendingDispatchEpoch = envelope.dispatchEpoch;
                    if (!installScheduled) {
                        installScheduled = true;
                        if (!mainHandler.post(new Runnable() { public void run() { installPendingBitmap(); } })) {
                            installScheduled = false;
                            recyclePendingBitmapLocked();
                        }
                    }
                }
            }
            if (!keep && !converted.isRecycled()) converted.recycle();
        }
    }

    private void installPendingBitmap() {
        requireUiThread();
        Bitmap next;
        Rect crop;
        long generation;
        long gateGeneration;
        long timestampNs;
        long bitmapCreateNs;
        long pixelConvertNs;
        long installQueueNs;
        long installStartedNs = profileListener == null ? 0L : System.nanoTime();
        synchronized (stateLock) {
            installScheduled = false;
            next = pendingBitmap;
            crop = pendingBitmapCrop;
            generation = pendingBitmapGeneration;
            timestampNs = pendingBitmapTimestampNs;
            bitmapCreateNs = pendingBitmapCreateNs;
            pixelConvertNs = pendingPixelConvertNs;
            installQueueNs = pendingInstallQueueNs;
            pendingBitmap = null;
            pendingBitmapCrop = null;
            if (next == null || closed || hostSuspended || generation != activeGeneration) {
                if (next != null && !next.isRecycled()) next.recycle();
                return;
            }
            Bitmap previous = displayedBitmap;
            displayedBitmap = next;
            displayedCrop = crop;
            displayedRotation = pendingBitmapRotation;
            displayedGeneration = generation;
            displayedTimestampNs = timestampNs;
            displayedBitmapCreateNs = bitmapCreateNs;
            displayedPixelConvertNs = pixelConvertNs;
            displayedInstallQueueDurationNs = profileListener == null ? 0L
                    : Math.max(0L, installStartedNs - installQueueNs);
            displayedDispatchGate = pendingDispatchGate;
            displayedGateGeneration = pendingDispatchGeneration;
            displayedDispatchEpoch = pendingDispatchEpoch;
            if (previous != null && previous != next && !previous.isRecycled()) previous.recycle();
        }
        invalidate();
        if (profileListener != null) {
            long installedNs = System.nanoTime();
            synchronized (stateLock) {
                if (displayedTimestampNs == timestampNs) {
                    displayedInstallDurationNs = installedNs - installStartedNs;
                    displayedInstallNs = installedNs;
                }
            }
        }
    }

    public void setProfileListener(ProfileListener listener) {
        profileListener = listener;
    }

    @Override protected void onDraw(Canvas canvas) {
        ProfileListener listener = profileListener;
        long drawStartedNs = listener == null ? 0L : System.nanoTime();
        super.onDraw(canvas);
        Bitmap bitmap;
        Rect crop;
        RendererViewport viewport;
        long generation;
        long gateGeneration;
        long timestampNs;
        int rotation;
        final FrameDispatchGate gate;
        final long dispatchEpoch;
        synchronized (stateLock) {
            if (closed || hostSuspended) return;
            bitmap = displayedBitmap;
            crop = displayedCrop;
            rotation = displayedRotation;
            viewport = rendererViewport;
            generation = displayedGeneration;
            gateGeneration = displayedGateGeneration;
            timestampNs = displayedTimestampNs;
            gate = displayedDispatchGate;
            dispatchEpoch = displayedDispatchEpoch;
        }
        int viewWidth = getWidth();
        int viewHeight = getHeight();
        if (bitmap == null || bitmap.isRecycled() || crop == null || viewWidth <= 0 || viewHeight <= 0)
            return;
        Rect safe = viewport.scaledSafeArea(viewWidth, viewHeight);
        if (safe.isEmpty()) return;
        boolean quarterTurn = rotation == 90 || rotation == 270;
        float rotatedWidth = quarterTurn ? crop.height() : crop.width();
        float rotatedHeight = quarterTurn ? crop.width() : crop.height();
        float scale = Math.min((float) safe.width() / rotatedWidth,
                (float) safe.height() / rotatedHeight);
        float centerX = (safe.left + safe.right) / 2.0f;
        float centerY = (safe.top + safe.bottom) / 2.0f;
        float outWidth = crop.width() * scale;
        float outHeight = crop.height() * scale;
        RectF destination = new RectF(centerX - outWidth / 2.0f, centerY - outHeight / 2.0f,
                centerX + outWidth / 2.0f, centerY + outHeight / 2.0f);
        final Canvas outputCanvas = canvas;
        final Bitmap outputBitmap = bitmap;
        final Rect outputCrop = crop;
        final RendererViewport outputViewport = viewport;
        final int outputWidth = viewWidth;
        final int outputHeight = viewHeight;
        final RectF output = destination;
        final int outputRotation = rotation;
        final float outputCenterX = centerX;
        final float outputCenterY = centerY;
        final boolean[] renderedResult = new boolean[] { false };
        FrameDispatchGate.DrawAction action = new FrameDispatchGate.DrawAction() {
            public void draw() {
                renderedResult[0] = drawBitmap(outputCanvas, outputBitmap, outputCrop, output,
                        outputViewport, outputWidth, outputHeight, outputRotation,
                        outputCenterX, outputCenterY);
            }
        };
        boolean rendered;
        if (gate == null) {
            action.draw();
            rendered = renderedResult[0];
        } else {
            rendered = gate.drawIfCurrent(gateGeneration, dispatchEpoch, action) && renderedResult[0];
        }
        if (!rendered) return;
        boolean reportProfile = false;
        synchronized (stateLock) {
            if (!closed && !hostSuspended && displayedBitmap == bitmap && !bitmap.isRecycled()
                    && displayedGeneration == generation && displayedTimestampNs == timestampNs) {
                drawnGeneration = generation;
                drawnTimestampNs = timestampNs;
                if (listener != null && lastProfiledDrawTimestampNs != timestampNs) {
                    lastProfiledDrawTimestampNs = timestampNs;
                    reportProfile = true;
                }
            }
        }
        if (listener != null && reportProfile) {
            long now = System.nanoTime();
            listener.onFrameProfile(timestampNs, displayedBitmapCreateNs,
                    displayedPixelConvertNs,
                    displayedInstallQueueDurationNs, displayedInstallDurationNs,
                    Math.max(0L, drawStartedNs - displayedInstallNs), now - drawStartedNs);
        }
    }

    private boolean drawBitmap(Canvas canvas, Bitmap bitmap, Rect crop, RectF destination,
            RendererViewport viewport, int viewWidth, int viewHeight, int rotation,
            float centerX, float centerY) {
        int save = canvas.save();
        try {
            if (!viewport.clip(canvas, viewWidth, viewHeight)) return false;
            if (rotation != 0) canvas.rotate(rotation, centerX, centerY);
            canvas.drawBitmap(bitmap, crop, destination, paint);
            return true;
        } finally { canvas.restoreToCount(save); }
    }

    @Override protected void onSizeChanged(int width, int height, int oldWidth, int oldHeight) {
        super.onSizeChanged(width, height, oldWidth, oldHeight);
        invalidate();
    }

    @Override public void onHostSuspended(int reason, long generation) {
        requireUiThread();
        synchronized (stateLock) {
            if (closed || generation <= 0 || activeGeneration != generation) return;
            hostSuspended = true;
            clearQueuedLocked();
        }
        clearDisplayedBitmap();
        if (reason != WARNING_PREEMPTION) close();
    }

    @Override public void onHostResumed(long generation) {
        requireUiThread();
        synchronized (stateLock) {
            if (!closed && generation > 0 && generation == activeGeneration) hostSuspended = false;
        }
    }

    /** Changes to a bounded synthetic logical viewport. No Honda geometry is represented. */
    public void setRendererViewport(RendererViewport viewport) {
        requireUiThread();
        if (viewport == null) throw new IllegalArgumentException("viewport required");
        synchronized (stateLock) {
            if (closed) throw new IllegalStateException("content view is closed");
            rendererViewport = viewport;
        }
        invalidate();
    }

    /** Clears pixels immediately and rejects frames until a matching resume. */
    public void clearFrame() {
        requireUiThread();
        synchronized (stateLock) {
            if (closed) return;
            clearQueuedLocked();
            latestSubmittedTimestampNs = -1L;
        }
        clearDisplayedBitmap();
    }

    /** Idempotent; releases this View's worker and all bitmap ownership. */
    public void close() {
        requireUiThread();
        synchronized (stateLock) {
            if (closed) return;
            closed = true;
            hostSuspended = true;
            activeGeneration = 0L;
            clearQueuedLocked();
        }
        clearDisplayedBitmap();
        if (converterThread == null) return;
        if (sharedConverter) {
            // The thread outlives this View: drop only this View's queued conversions.
            if (converterHandler != null) converterHandler.removeCallbacksAndMessages(null);
        } else {
            converterThread.quit();
        }
    }

    public boolean hasDisplayedFrame() {
        synchronized (stateLock) { return displayedBitmap != null && !displayedBitmap.isRecycled(); }
    }
    public long displayedGeneration() { synchronized (stateLock) { return displayedGeneration; } }
    public long displayedTimestampNs() { synchronized (stateLock) { return displayedTimestampNs; } }
    /** Frame last drawn successfully by this View's Canvas; does not imply display scanout. */
    public long drawnGeneration() { synchronized (stateLock) { return drawnGeneration; } }
    public long drawnTimestampNs() { synchronized (stateLock) { return drawnTimestampNs; } }
    public boolean isClosed() { synchronized (stateLock) { return closed; } }

    private void clearQueuedLocked() {
        frameEpoch++;
        pendingFrame = null;
        recyclePendingBitmapLocked();
        installScheduled = false;
    }

    private void recyclePendingBitmapLocked() {
        if (pendingBitmap != null && !pendingBitmap.isRecycled()) pendingBitmap.recycle();
        pendingBitmap = null;
        pendingBitmapCrop = null;
        pendingDispatchGate = null;
        pendingDispatchGeneration = 0L;
        pendingDispatchEpoch = -1L;
    }

    private void clearDisplayedBitmap() {
        requireUiThread();
        synchronized (stateLock) {
            Bitmap previous = displayedBitmap;
            displayedBitmap = null;
            displayedCrop = null;
            displayedRotation = 0;
            displayedDispatchGate = null;
            displayedDispatchEpoch = -1L;
            displayedGateGeneration = 0L;
            displayedGeneration = 0L;
            displayedTimestampNs = -1L;
            drawnGeneration = 0L;
            drawnTimestampNs = -1L;
            if (previous != null && !previous.isRecycled()) previous.recycle();
        }
        invalidate();
    }

    private static void requireUiThread() {
        if (Looper.myLooper() != Looper.getMainLooper())
            throw new IllegalStateException("content lifecycle must run on the UI thread");
    }

    private static final class FrameEnvelope {
        final DecodedFrame frame;
        final long generation;
        final long epoch;
        final FrameDispatchGate gate;
        final long gateGeneration;
        final long dispatchEpoch;
        FrameEnvelope(DecodedFrame frame, long generation, long epoch,
                FrameDispatchGate gate, long gateGeneration, long dispatchEpoch) {
            this.frame = frame;
            this.generation = generation;
            this.epoch = epoch;
            this.gate = gate;
            this.gateGeneration = gateGeneration;
            this.dispatchEpoch = dispatchEpoch;
        }
    }
}
