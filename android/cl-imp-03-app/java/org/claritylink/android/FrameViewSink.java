package org.claritylink.android;

import android.os.Binder;
import android.os.Handler;
import android.os.Parcel;
import android.os.ParcelFileDescriptor;
import android.os.Process;
import android.os.RemoteException;
import android.util.Log;

import org.claritylink.renderer.DecodedFrame;
import org.claritylink.renderer.FrameDispatchGate;

import java.io.FileInputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.zip.CRC32;

/** Bounded reverse-Binder sink: validated frame bytes are queued onto the UI-owned View. */
final class FrameViewSink extends Binder {
    interface DispatchProbe {
        void beforeDispatch(long generation, long frameId, long timestampNs);
    }

    static final class TestControl implements DispatchProbe {
        volatile long handlerPauseTimestamp = -1L;
        volatile long viewPauseTimestamp = -1L;
        volatile long recoveryTimestamp = -1L;
        volatile CountDownLatch handlerEntered = new CountDownLatch(0);
        volatile CountDownLatch releaseHandler = new CountDownLatch(0);
        volatile CountDownLatch viewSubmitted = new CountDownLatch(0);
        volatile CountDownLatch releaseView = new CountDownLatch(0);
        volatile CountDownLatch warningApplied = new CountDownLatch(0);
        volatile CountDownLatch warningCleared = new CountDownLatch(0);
        volatile CountDownLatch recoveryDrawn = new CountDownLatch(0);
        volatile CountDownLatch dispatchFinished = new CountDownLatch(0);
        volatile boolean barrierTimedOut;

        void pauseHandlerAt(long timestampNs) {
            handlerPauseTimestamp = timestampNs;
            handlerEntered = new CountDownLatch(1);
            releaseHandler = new CountDownLatch(1);
        }

        void pauseViewAt(long timestampNs) {
            viewPauseTimestamp = timestampNs;
            viewSubmitted = new CountDownLatch(1);
            releaseView = new CountDownLatch(1);
        }

        void expectWarning(boolean visible) {
            if (visible) warningApplied = new CountDownLatch(1);
            else warningCleared = new CountDownLatch(1);
        }

        void expectDispatchCount(int count) { dispatchFinished = new CountDownLatch(count); }
        void dispatchFinished() { dispatchFinished.countDown(); }
        void releaseForClose() {
            releaseHandler.countDown();
            releaseView.countDown();
        }

        void warningApplied(boolean visible) {
            (visible ? warningApplied : warningCleared).countDown();
        }

        boolean beforeViewSubmit(long timestampNs) {
            if (timestampNs != viewPauseTimestamp) return false;
            viewSubmitted.countDown();
            barrierTimedOut |= !awaitBounded(releaseView);
            viewPauseTimestamp = -1L;
            return true;
        }

        void recoveryDrawn(long timestampNs) {
            if (timestampNs == recoveryTimestamp) recoveryDrawn.countDown();
        }

        @Override public void beforeDispatch(long generation, long frameId, long timestampNs) {
            if (timestampNs != handlerPauseTimestamp) return;
            handlerEntered.countDown();
            barrierTimedOut |= !awaitBounded(releaseHandler);
            handlerPauseTimestamp = -1L;
        }

        private static boolean awaitBounded(CountDownLatch latch) {
            try { return latch.await(10L, TimeUnit.SECONDS); }
            catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                return false;
            }
        }
    }

    static final int MAX_QUEUED_FRAMES = 3;
    static final int MAX_QUEUED_FRAME_BYTES = 8 * 1024 * 1024;
    interface Target {
        boolean enqueue(DecodedFrame frame, long generation, long frameId, long dispatchEpoch);
        boolean setWarningVisible(long generation, boolean visible);
        boolean replaceGeneration(long oldGeneration, long newGeneration);
    }

    private static final String DESCRIPTOR = "org.claritylink.android.IClarityLinkViewFrameSink";
    private static final String TAG = "ClarityLinkCLIMP03";
    private final Handler ui;
    private final Target target;
    private final AtomicInteger queuedFrames = new AtomicInteger();
    private final AtomicInteger queuedBytes = new AtomicInteger();
    private final Object pendingDispatchLock = new Object();
    private final Set<PendingDispatch> pendingDispatches = new HashSet<PendingDispatch>();
    private final FrameDispatchGate dispatchGate = new FrameDispatchGate();
    private volatile FrameStreamIdentity identity;
    private volatile FrameStreamIdentity lastClosedIdentity;
    private volatile long generation;
    private volatile long lastFrameId;
    private volatile long lastTimestampNs = -1L;
    private volatile boolean closed;
    private volatile DispatchProbe dispatchProbe;

    FrameDispatchGate dispatchGate() { return dispatchGate; }
    int queuedFrameCount() { return queuedFrames.get(); }
    int queuedByteCount() { return queuedBytes.get(); }
    synchronized boolean closeSession(long sessionId, boolean releaseProbeBarrier) {
        if (identity == null || identity.sessionId != sessionId ||
                identity.streamType != FrameStreamIdentity.TYPE111) return false;
        close(identity.streamGeneration, releaseProbeBarrier);
        return isGenerationFenced(sessionId);
    }

    synchronized boolean isGenerationFenced(long sessionId) {
        return closed && generation == 0L && lastClosedIdentity != null &&
                lastClosedIdentity.sessionId == sessionId &&
                lastClosedIdentity.streamType == FrameStreamIdentity.TYPE111;
    }

    void setDispatchProbe(DispatchProbe probe) { dispatchProbe = probe; }

    FrameViewSink(Handler ui, Target target) {
        if (ui == null || target == null) throw new IllegalArgumentException("UI and target required");
        this.ui = ui;
        this.target = target;
    }

    synchronized void begin(long value) {
        begin(new FrameStreamIdentity(value, FrameStreamIdentity.TYPE111, 11101L, value,
                FrameStreamIdentity.OUTPUT_SECONDARY_VIEW));
    }

    synchronized void begin(FrameStreamIdentity value) {
        if (value == null || !value.isValid()) throw new IllegalArgumentException("valid stream identity required");
        if (!dispatchGate.begin(value.streamGeneration))
            throw new IllegalStateException("dispatch gate already active");
        identity = value;
        lastClosedIdentity = null;
        generation = value.streamGeneration;
        lastFrameId = 0L;
        lastTimestampNs = -1L;
        closed = false;
    }

    synchronized void beginLegacy(long value) {
        if (value <= 0) throw new IllegalArgumentException("positive generation required");
        if (!dispatchGate.begin(value)) throw new IllegalStateException("dispatch gate already active");
        generation = value;
        lastFrameId = 0L;
        lastTimestampNs = -1L;
        closed = false;
    }

    synchronized void close(long value) {
        close(value, true);
    }

    synchronized void close(long value, boolean releaseProbeBarrier) {
        if (generation == value) {
            lastClosedIdentity = identity;
            dispatchGate.end(value);
            closed = true;
            DispatchProbe probe = dispatchProbe;
            if (releaseProbeBarrier && probe instanceof TestControl)
                ((TestControl) probe).releaseForClose();
            cancelPendingDispatches();
            generation = 0L;
            identity = null;
            lastFrameId = 0L;
            lastTimestampNs = -1L;
        }
    }

    @Override protected synchronized boolean onTransact(int code, Parcel data, final Parcel reply, int flags)
            throws RemoteException {
        if (code != FrameIpcProtocol.VIEW_FRAME && code != FrameIpcProtocol.VIEW_WARNING &&
                code != FrameIpcProtocol.VIEW_CHANGE_GENERATION && code != FrameIpcProtocol.VIEW_CLOSE)
            return super.onTransact(code, data, reply, flags);
        if (Binder.getCallingUid() != Process.myUid()) {
            reply.writeException(new SecurityException("view frame caller rejected"));
            return true;
        }
        data.enforceInterface(DESCRIPTOR);
        int version = data.readInt();
        if (code == FrameIpcProtocol.VIEW_CLOSE) {
            FrameStreamIdentity requestIdentity = readIdentity(data);
            boolean currentMatch = version == FrameIpcProtocol.VERSION && identity != null &&
                    identity.equals(requestIdentity) && generation == requestIdentity.streamGeneration;
            boolean duplicateMatch = version == FrameIpcProtocol.VERSION && lastClosedIdentity != null &&
                    lastClosedIdentity.equals(requestIdentity) && closed && generation == 0L;
            if (currentMatch) close(requestIdentity.streamGeneration);
            reply.writeNoException();
            reply.writeInt(currentMatch || duplicateMatch ? 1 : 0);
            Log.i(TAG, "BINDER_VIEW_STREAM_CLOSE session_id=" + requestIdentity.sessionId +
                    " stream_type=" + requestIdentity.streamType + " generation=" +
                    requestIdentity.streamGeneration + " accepted=" + (currentMatch || duplicateMatch) +
                    " queued_frames=" + queuedFrames.get() + " queued_bytes=" + queuedBytes.get());
            return true;
        }
        if (code == FrameIpcProtocol.VIEW_CHANGE_GENERATION) {
            FrameStreamIdentity requestIdentity = readIdentity(data);
            long oldGeneration = requestIdentity.streamGeneration;
            long newGeneration = data.readLong();
            boolean accepted = version == FrameIpcProtocol.VERSION && !closed && identity != null &&
                    identity.equals(requestIdentity) &&
                    oldGeneration == generation && newGeneration > oldGeneration &&
                    dispatchGate.replaceGeneration(oldGeneration, newGeneration);
            if (accepted) {
                accepted = target.replaceGeneration(oldGeneration, newGeneration);
                if (accepted) {
                    generation = newGeneration;
                    identity = requestIdentity.withGeneration(newGeneration);
                    lastFrameId = 0L;
                    lastTimestampNs = -1L;
                    Log.i(TAG, "BINDER_VIEW_GENERATION_REPLACED old=" + oldGeneration +
                            " new=" + newGeneration + " session_preserved=true");
                } else {
                    closed = true;
                }
            }
            reply.writeNoException();
            reply.writeInt(accepted ? 1 : 0);
            return true;
        }
        if (code == FrameIpcProtocol.VIEW_WARNING) {
            final FrameStreamIdentity warningIdentity = readIdentity(data);
            final long warningGeneration = warningIdentity.streamGeneration;
            final boolean visible = data.readInt() != 0;
            final long warningEpoch = version == FrameIpcProtocol.VERSION && identity != null &&
                    identity.equals(warningIdentity)
                    ? dispatchGate.setWarningVisible(warningGeneration, visible) : -1L;
            boolean queued = warningEpoch >= 0 && ui.post(new Runnable() {
                public void run() {
                    if (dispatchGate.warningStateMatches(warningGeneration, warningEpoch, visible)) {
                        boolean applied = target.setWarningVisible(warningGeneration, visible);
                        Log.i(TAG, "BINDER_WARNING_VIEW_APPLIED generation=" + warningGeneration +
                                " visible=" + visible + " applied=" + applied +
                                " epoch=" + warningEpoch);
                    }
                }
            });
            reply.writeNoException();
            reply.writeInt(queued ? 1 : 0);
            return true;
        }
        final FrameStreamIdentity frameIdentity = readIdentity(data);
        final long frameGeneration = frameIdentity.streamGeneration;
        final long frameId = data.readLong();
        final long timestampNs = data.readLong();
        final int width = data.readInt();
        final int height = data.readInt();
        final int rowStride = data.readInt();
        int pixelFormat = data.readInt();
        final int rotation = data.readInt();
        final int cropLeft = data.readInt();
        final int cropTop = data.readInt();
        final int cropRight = data.readInt();
        final int cropBottom = data.readInt();
        final int payloadBytes = data.readInt();
        long expectedCrc = data.readLong();
        ParcelFileDescriptor descriptor = data.readParcelable(
                ParcelFileDescriptor.class.getClassLoader());

        final long dispatchEpoch = dispatchGate.captureEpoch(frameGeneration);
        if (version != FrameIpcProtocol.VERSION || closed || identity == null ||
                !identity.equals(frameIdentity) || frameGeneration != generation ||
                dispatchEpoch < 0 ||
                frameId <= lastFrameId || timestampNs < 0 || timestampNs <= lastTimestampNs ||
                pixelFormat != FrameIpcProtocol.PIXEL_FORMAT_RGBA_8888 ||
                (rotation != 0 && rotation != 90 && rotation != 180 && rotation != 270) ||
                cropLeft < 0 || cropTop < 0 || cropRight > width || cropBottom > height ||
                cropLeft >= cropRight || cropTop >= cropBottom ||
                payloadBytes != FrameIpcProtocol.expectedRgbaBytes(width, height, rowStride) ||
                payloadBytes > DecodedFrame.MAX_RGBA_BYTES || descriptor == null) {
            closeQuietly(descriptor);
            reply.writeNoException();
            reply.writeInt(0);
            reply.writeString("frame_contract_rejected");
            return true;
        }
        if (queuedFrames.incrementAndGet() > MAX_QUEUED_FRAMES) {
            queuedFrames.decrementAndGet();
            Log.i(TAG, "BINDER_FRAME_REJECTED reason=frame_dispatch_queue_full queued_frames=" +
                    queuedFrames.get() + " queued_bytes=" + queuedBytes.get());
            closeQuietly(descriptor);
            reply.writeNoException();
            reply.writeInt(0);
            reply.writeString("frame_dispatch_queue_full");
            return true;
        }
        if (queuedBytes.addAndGet(payloadBytes) > MAX_QUEUED_FRAME_BYTES) {
            queuedBytes.addAndGet(-payloadBytes);
            queuedFrames.decrementAndGet();
            Log.i(TAG, "BINDER_FRAME_REJECTED reason=frame_dispatch_byte_budget_full queued_frames=" +
                    queuedFrames.get() + " queued_bytes=" + queuedBytes.get());
            closeQuietly(descriptor);
            reply.writeNoException();
            reply.writeInt(0);
            reply.writeString("frame_dispatch_byte_budget_full");
            return true;
        }

        byte[] pixels;
        try {
            pixels = readPayload(descriptor, payloadBytes);
        } catch (IOException failure) {
            queuedBytes.addAndGet(-payloadBytes);
            queuedFrames.decrementAndGet();
            reply.writeNoException();
            reply.writeInt(0);
            reply.writeString("frame_payload_rejected");
            return true;
        } catch (OutOfMemoryError exhausted) {
            queuedBytes.addAndGet(-payloadBytes);
            queuedFrames.decrementAndGet();
            reply.writeNoException();
            reply.writeInt(0);
            reply.writeString("frame_allocation_rejected");
            return true;
        }
        final DecodedFrame frame;
        try {
            CRC32 crc = new CRC32();
            crc.update(pixels);
            if (crc.getValue() != expectedCrc || closed || frameGeneration != generation) {
                queuedBytes.addAndGet(-payloadBytes);
                queuedFrames.decrementAndGet();
                reply.writeNoException();
                reply.writeInt(0);
                reply.writeString("frame_integrity_or_generation_rejected");
                return true;
            }
            frame = new DecodedFrame(width, height, rowStride, timestampNs, rotation,
                    cropLeft, cropTop, cropRight, cropBottom, ByteBuffer.wrap(pixels));
        } catch (RuntimeException invalid) {
            queuedBytes.addAndGet(-payloadBytes);
            queuedFrames.decrementAndGet();
            reply.writeNoException();
            reply.writeInt(0);
            reply.writeString("decoded_frame_rejected");
            return true;
        } catch (OutOfMemoryError exhausted) {
            queuedBytes.addAndGet(-payloadBytes);
            queuedFrames.decrementAndGet();
            reply.writeNoException();
            reply.writeInt(0);
            reply.writeString("frame_allocation_rejected");
            return true;
        }
        final PendingDispatch pending = new PendingDispatch(frame, frameGeneration, frameId,
                timestampNs, dispatchEpoch, payloadBytes);
        synchronized (pendingDispatchLock) { pendingDispatches.add(pending); }
        final boolean queued;
        try {
            queued = ui.post(pending);
        } catch (OutOfMemoryError exhausted) {
            pending.releaseAccounting();
            reply.writeNoException();
            reply.writeInt(0);
            reply.writeString("frame_dispatch_allocation_rejected");
            return true;
        }
        if (queued) {
            lastFrameId = frameId;
            lastTimestampNs = timestampNs;
        } else {
            pending.releaseAccounting();
        }
        reply.writeNoException();
        reply.writeInt(queued ? 1 : 0);
        reply.writeString(queued ? "queued" : "ui_dispatch_rejected");
        return true;
    }

    private final class PendingDispatch implements Runnable {
        private final DecodedFrame frame;
        private final long frameGeneration, frameId, timestampNs, dispatchEpoch;
        private final int payloadBytes;
        private final AtomicBoolean accounted = new AtomicBoolean(true);
        PendingDispatch(DecodedFrame frame, long generation, long frameId, long timestampNs,
                long dispatchEpoch, int payloadBytes) {
            this.frame = frame; this.frameGeneration = generation; this.frameId = frameId;
            this.timestampNs = timestampNs; this.dispatchEpoch = dispatchEpoch;
            this.payloadBytes = payloadBytes;
        }
        @Override public void run() {
            try {
                DispatchProbe probe = dispatchProbe;
                if (probe != null) probe.beforeDispatch(frameGeneration, frameId, timestampNs);
                if (!closed && generation == frameGeneration &&
                        dispatchGate.mayDispatch(frameGeneration, dispatchEpoch)) {
                    boolean accepted = target.enqueue(frame, frameGeneration, frameId, dispatchEpoch);
                    if (accepted) Log.i(TAG, "BINDER_FRAME_QUEUED_FOR_VIEW generation=" +
                            frameGeneration + " frame_id=" + frameId + " timestamp_ns=" +
                            timestampNs + " bytes=" + payloadBytes);
                    else Log.i(TAG, "BINDER_FRAME_VIEW_REJECTED generation=" + frameGeneration +
                            " frame_id=" + frameId + " reason=view_not_ready");
                } else Log.i(TAG, "BINDER_FRAME_DROPPED generation=" + frameGeneration +
                        " frame_id=" + frameId + " reason=warning_or_stale_epoch");
            } finally {
                releaseAccounting();
                DispatchProbe probe = dispatchProbe;
                if (probe instanceof TestControl) ((TestControl) probe).dispatchFinished();
            }
        }
        void cancel() { ui.removeCallbacks(this); releaseAccounting(); }
        void releaseAccounting() {
            if (!accounted.compareAndSet(true, false)) return;
            synchronized (pendingDispatchLock) { pendingDispatches.remove(this); }
            queuedBytes.addAndGet(-payloadBytes);
            queuedFrames.decrementAndGet();
        }
    }

    private void cancelPendingDispatches() {
        ArrayList<PendingDispatch> pending;
        synchronized (pendingDispatchLock) { pending = new ArrayList<PendingDispatch>(pendingDispatches); }
        for (PendingDispatch dispatch : pending) dispatch.cancel();
    }

    private static byte[] readPayload(ParcelFileDescriptor descriptor, int expected) throws IOException {
        if (expected <= 0 || expected > FrameIpcProtocol.MAX_FRAME_BYTES) {
            closeQuietly(descriptor);
            throw new IOException("invalid frame length");
        }
        FileInputStream input = new ParcelFileDescriptor.AutoCloseInputStream(descriptor);
        try {
            byte[] result = new byte[expected];
            int offset = 0;
            while (offset < expected) {
                int count = input.read(result, offset, expected - offset);
                if (count < 0) throw new IOException("short frame");
                offset += count;
            }
            if (input.read() != -1) throw new IOException("trailing frame bytes");
            return result;
        } finally { input.close(); }
    }

    private static void closeQuietly(ParcelFileDescriptor descriptor) {
        if (descriptor != null) try { descriptor.close(); } catch (IOException ignored) { }
    }

    private static FrameStreamIdentity readIdentity(Parcel data) {
        return new FrameStreamIdentity(data.readLong(), data.readInt(), data.readLong(),
                data.readLong(), data.readInt());
    }
}
