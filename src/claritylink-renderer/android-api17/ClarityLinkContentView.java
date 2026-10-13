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
    private static final String THREAD_NAME = "ClarityLinkFrameConvert";

    private final Object stateLock = new Object();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private HandlerThread converterThread;
    private Handler converterHandler;
    private final Paint paint = new Paint(Paint.FILTER_BITMAP_FLAG | Paint.DITHER_FLAG);

    private FrameEnvelope pendingFrame;
    private Bitmap pendingBitmap;
    private long pendingBitmapGeneration;
    private long pendingBitmapTimestampNs;
    private Rect pendingBitmapCrop;
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
    private Rect displayedCrop;

    public ClarityLinkContentView(Context context) {
        super(context);
        setWillNotDraw(false);
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

    /**
     * Queues an immutable DecodedFrame snapshot for conversion. Producers may
     * call from decoder threads. Newer frames replace the one pending frame.
     */
    public boolean submitFrame(final DecodedFrame frame, final long generation) {
        if (frame == null || frame.rotationDegrees != 0 || frame.byteSize() > DecodedFrame.MAX_RGBA_BYTES)
            return false;
        synchronized (stateLock) {
            if (closed || hostSuspended || generation <= 0 || generation != activeGeneration
                    || frame.presentationTimeNs <= latestSubmittedTimestampNs) return false;
            latestSubmittedTimestampNs = frame.presentationTimeNs;
            pendingFrame = new FrameEnvelope(frame, generation, frameEpoch);
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
            try {
                DecodedFrame frame = envelope.frame;
                converted = Bitmap.createBitmap(frame.width, frame.height, Bitmap.Config.ARGB_8888);
                converted.setPixels(frame.toArgbPixels(), 0, frame.width,
                        0, 0, frame.width, frame.height);
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
        long timestampNs;
        synchronized (stateLock) {
            installScheduled = false;
            next = pendingBitmap;
            crop = pendingBitmapCrop;
            generation = pendingBitmapGeneration;
            timestampNs = pendingBitmapTimestampNs;
            pendingBitmap = null;
            pendingBitmapCrop = null;
            if (next == null || closed || hostSuspended || generation != activeGeneration) {
                if (next != null && !next.isRecycled()) next.recycle();
                return;
            }
            Bitmap previous = displayedBitmap;
            displayedBitmap = next;
            displayedCrop = crop;
            displayedGeneration = generation;
            displayedTimestampNs = timestampNs;
            if (previous != null && previous != next && !previous.isRecycled()) previous.recycle();
        }
        invalidate();
    }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        Bitmap bitmap;
        Rect crop;
        long generation;
        long timestampNs;
        synchronized (stateLock) {
            if (closed || hostSuspended) return;
            bitmap = displayedBitmap;
            crop = displayedCrop;
            generation = displayedGeneration;
            timestampNs = displayedTimestampNs;
        }
        if (bitmap == null || bitmap.isRecycled() || crop == null || getWidth() <= 0 || getHeight() <= 0)
            return;
        float scale = Math.min((float) getWidth() / crop.width(), (float) getHeight() / crop.height());
        float outWidth = crop.width() * scale;
        float outHeight = crop.height() * scale;
        float left = (getWidth() - outWidth) / 2.0f;
        float top = (getHeight() - outHeight) / 2.0f;
        canvas.drawBitmap(bitmap, crop, new RectF(left, top, left + outWidth, top + outHeight), paint);
        synchronized (stateLock) {
            if (!closed && !hostSuspended && displayedBitmap == bitmap && !bitmap.isRecycled()
                    && displayedGeneration == generation && displayedTimestampNs == timestampNs) {
                drawnGeneration = generation;
                drawnTimestampNs = timestampNs;
            }
        }
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
        if (converterThread != null) converterThread.quit();
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
    }

    private void clearDisplayedBitmap() {
        requireUiThread();
        synchronized (stateLock) {
            Bitmap previous = displayedBitmap;
            displayedBitmap = null;
            displayedCrop = null;
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
        FrameEnvelope(DecodedFrame frame, long generation, long epoch) {
            this.frame = frame;
            this.generation = generation;
            this.epoch = epoch;
        }
    }
}
