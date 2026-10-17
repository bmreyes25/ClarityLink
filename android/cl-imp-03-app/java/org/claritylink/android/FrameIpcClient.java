package org.claritylink.android;

import android.os.IBinder;
import android.os.Parcel;
import android.os.ParcelFileDescriptor;
import android.os.RemoteException;

import org.claritylink.renderer.DecodedFrame;
import org.claritylink.renderer.FrameBackpressureGate;

import java.io.FileOutputStream;
import java.io.IOException;
import java.util.concurrent.atomic.AtomicLong;

/** Single-flight, bounded API17 Binder/pipe client for the project-owned compositor process. */
final class FrameIpcClient {
    interface Callback { void complete(boolean accepted, String reason); }

    private final IBinder endpoint;
    private final FrameBackpressureGate frameGate = new FrameBackpressureGate();
    private volatile long activeGeneration;
    private volatile FrameStreamIdentity identity;
    private volatile boolean closed;
    private final AtomicLong nextFrameId = new AtomicLong(1L);

    FrameIpcClient(IBinder endpoint) { this.endpoint = endpoint; }

    /** Test-only producer reattachment to an existing Type110 registration after a peer dies. */
    static FrameIpcClient attachExistingType110(IBinder endpoint, FrameStreamIdentity streamIdentity,
            long nextFrameId) {
        if (endpoint == null || !endpoint.isBinderAlive() || streamIdentity == null ||
                !streamIdentity.isValid() || streamIdentity.streamType != FrameStreamIdentity.TYPE110 ||
                nextFrameId <= 0 || nextFrameId == Long.MAX_VALUE) return null;
        FrameIpcClient client = new FrameIpcClient(endpoint);
        client.identity = streamIdentity;
        client.activeGeneration = streamIdentity.streamGeneration;
        client.nextFrameId.set(nextFrameId);
        return client;
    }

    /** App-private Type111 producer attachment to a registration owned by the test session. */
    static FrameIpcClient attachExistingType111(IBinder endpoint, FrameStreamIdentity streamIdentity,
            long nextFrameId) {
        if (endpoint == null || !endpoint.isBinderAlive() || streamIdentity == null ||
                !streamIdentity.isValid() || streamIdentity.streamType != FrameStreamIdentity.TYPE111 ||
                streamIdentity.outputId != FrameStreamIdentity.OUTPUT_SECONDARY_VIEW ||
                nextFrameId <= 0 || nextFrameId == Long.MAX_VALUE) return null;
        FrameIpcClient client = new FrameIpcClient(endpoint);
        client.identity = streamIdentity;
        client.activeGeneration = streamIdentity.streamGeneration;
        client.nextFrameId.set(nextFrameId);
        return client;
    }

    int begin(long generation, IBinder viewSink) throws RemoteException {
        return begin(new FrameStreamIdentity(generation, FrameStreamIdentity.TYPE111,
                11101L, generation, FrameStreamIdentity.OUTPUT_SECONDARY_VIEW), viewSink);
    }

    int begin(FrameStreamIdentity streamIdentity, IBinder viewSink) throws RemoteException {
        if (closed || streamIdentity == null || !streamIdentity.isValid() || viewSink == null ||
                !endpoint.isBinderAlive()) return -1;
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeInt(FrameIpcProtocol.VERSION);
            writeIdentity(data, streamIdentity);
            data.writeStrongBinder(viewSink);
            endpoint.transact(FrameIpcProtocol.BEGIN, data, reply, 0);
            reply.readException();
            if (reply.readInt() == 0) return -1;
            identity = streamIdentity;
            activeGeneration = streamIdentity.streamGeneration;
            nextFrameId.set(1L);
            return reply.readInt();
        } finally { reply.recycle(); data.recycle(); }
    }

    boolean submit(final DecodedFrame frame, final long generation, final Callback callback) {
        if (frame == null || callback == null || closed || generation <= 0
                || generation != activeGeneration || frame.byteSize() > FrameIpcProtocol.MAX_FRAME_BYTES)
            return false;
        if (!frameGate.tryAcquire()) {
            callback.complete(false, "backpressure");
            return false;
        }
        final long frameId = nextFrameId.getAndIncrement();
        if (frameId <= 0 || frameId == Long.MAX_VALUE) {
            frameGate.release();
            callback.complete(false, "frame_id_exhausted");
            return false;
        }
        Thread worker = new Thread(new Runnable() {
            public void run() {
                boolean accepted = false;
                String reason = "remote_rejected";
                ParcelFileDescriptor[] pipe = null;
                Thread writer = null;
                boolean writerStarted = false;
                try {
                    pipe = ParcelFileDescriptor.createPipe();
                    final ParcelFileDescriptor writeEnd = pipe[1];
                    writer = new Thread(new Runnable() {
                        public void run() {
                            FileOutputStream output = null;
                            try {
                                output = new ParcelFileDescriptor.AutoCloseOutputStream(writeEnd);
                                frame.writeRgbaTo(output);
                                output.flush();
                            } catch (IOException ignored) {
                                // A remote rejection closes the pipe; the transaction reports it.
                            } finally {
                                if (output != null) {
                                    try { output.close(); } catch (IOException ignored) { }
                                } else {
                                    try { writeEnd.close(); } catch (IOException ignored) { }
                                }
                            }
                        }
                    }, "ClarityLinkFramePipeWriter");
                    writer.start();
                    writerStarted = true;
                    Parcel data = Parcel.obtain();
                    Parcel reply = Parcel.obtain();
                    try {
                        data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
                        data.writeInt(FrameIpcProtocol.VERSION);
                        FrameStreamIdentity currentIdentity = identity;
                        if (currentIdentity == null || currentIdentity.streamGeneration != generation)
                            throw new IOException("stream_identity_changed");
                        writeIdentity(data, currentIdentity);
                        data.writeLong(frameId); // sequence is local to this stream generation
                        data.writeLong(frame.presentationTimeNs);
                        data.writeInt(frame.width);
                        data.writeInt(frame.height);
                        data.writeInt(frame.rowStride);
                        data.writeInt(FrameIpcProtocol.PIXEL_FORMAT_RGBA_8888);
                        data.writeInt(frame.rotationDegrees);
                        data.writeInt(frame.cropLeft);
                        data.writeInt(frame.cropTop);
                        data.writeInt(frame.cropRight);
                        data.writeInt(frame.cropBottom);
                        data.writeInt(frame.byteSize());
                        data.writeParcelable(pipe[0], 0);
                        endpoint.transact(FrameIpcProtocol.FRAME, data, reply, 0);
                        reply.readException();
                        accepted = reply.readInt() != 0;
                        reason = reply.readString();
                    } finally { reply.recycle(); data.recycle(); }
                    writer.join(5000L);
                    if (writer.isAlive()) {
                        accepted = false;
                        reason = "writer_timeout";
                    }
                } catch (Exception failure) {
                    reason = failure.getClass().getSimpleName();
                } finally {
                    if (pipe != null) {
                        try { pipe[0].close(); } catch (IOException ignored) { }
                        if (!writerStarted) try { pipe[1].close(); } catch (IOException ignored) { }
                    }
                    if (writerStarted && writer != null && writer.isAlive()) {
                        try { writer.join(5000L); } catch (InterruptedException interrupted) {
                            Thread.currentThread().interrupt();
                        }
                        if (writer.isAlive()) {
                            accepted = false;
                            reason = "writer_timeout";
                        }
                    }
                    frameGate.release();
                    callback.complete(accepted, reason);
                }
            }
        }, "ClarityLinkFrameIpc");
        worker.start();
        return true;
    }

    void end(long generation) {
        if (closed || generation <= 0 || generation != activeGeneration) return;
        closed = true;
        frameGate.close();
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeInt(FrameIpcProtocol.VERSION);
            FrameStreamIdentity currentIdentity = identity;
            if (currentIdentity == null || currentIdentity.streamGeneration != generation) return;
            writeIdentity(data, currentIdentity);
            endpoint.transact(FrameIpcProtocol.END, data, reply, 0);
            reply.readException();
        } catch (Exception ignored) {
            // Binder death also causes the bound service process to be reclaimed.
        } finally {
            activeGeneration = 0L;
            reply.recycle(); data.recycle();
        }
    }

    boolean setWarningVisible(long generation, boolean visible) throws RemoteException {
        if (closed || generation <= 0 || generation != activeGeneration || !endpoint.isBinderAlive())
            return false;
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeInt(FrameIpcProtocol.VERSION);
            FrameStreamIdentity currentIdentity = identity;
            if (currentIdentity == null || currentIdentity.streamGeneration != generation) return false;
            writeIdentity(data, currentIdentity);
            data.writeInt(visible ? 1 : 0);
            endpoint.transact(FrameIpcProtocol.WARNING, data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    boolean replaceGeneration(long oldGeneration, long newGeneration) throws RemoteException {
        if (closed || oldGeneration != activeGeneration || newGeneration <= oldGeneration ||
                !endpoint.isBinderAlive() || frameGate.isOccupied()) return false;
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeInt(FrameIpcProtocol.VERSION);
            FrameStreamIdentity currentIdentity = identity;
            if (currentIdentity == null || currentIdentity.streamGeneration != oldGeneration) return false;
            writeIdentity(data, currentIdentity);
            data.writeLong(newGeneration);
            endpoint.transact(FrameIpcProtocol.CHANGE_GENERATION, data, reply, 0);
            reply.readException();
            boolean accepted = reply.readInt() != 0;
            if (accepted) {
                activeGeneration = newGeneration;
                identity = currentIdentity.withGeneration(newGeneration);
                nextFrameId.set(1L);
            }
            return accepted;
        } finally { reply.recycle(); data.recycle(); }
    }

    boolean probeEndIdentity(FrameStreamIdentity requestedIdentity) throws RemoteException {
        if (closed || requestedIdentity == null || !endpoint.isBinderAlive()) return false;
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeInt(FrameIpcProtocol.VERSION);
            writeIdentity(data, requestedIdentity);
            endpoint.transact(FrameIpcProtocol.END, data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    boolean hasFrameInFlight() { return frameGate.isOccupied(); }
    int sessionIdentity() { return System.identityHashCode(endpoint); }
    FrameStreamIdentity streamIdentity() { return identity; }
    long nextFrameIdHint() { return nextFrameId.get(); }

    private static void writeIdentity(Parcel data, FrameStreamIdentity streamIdentity) {
        data.writeLong(streamIdentity.sessionId);
        data.writeInt(streamIdentity.streamType);
        data.writeLong(streamIdentity.connectionId);
        data.writeLong(streamIdentity.streamGeneration);
        data.writeInt(streamIdentity.outputId);
    }

    /** Sends a deliberately malformed request through the production Binder transaction. */
    String probeMalformed(String kind, long generation, long timestampNs) throws Exception {
        final int width = 2, height = 2;
        int rowStride = 8, format = FrameIpcProtocol.PIXEL_FORMAT_RGBA_8888;
        long requestGeneration = generation;
        int declaredBytes = 16;
        byte[] bytes = new byte[16];
        boolean includeDescriptor = true;
        if ("negative_dimensions".equals(kind)) { rowStride = 8; }
        else if ("zero_dimensions".equals(kind)) { rowStride = 8; }
        else if ("oversized_dimensions".equals(kind)) { rowStride = 8192; declaredBytes = 8192 * 8192; }
        else if ("unsupported_pixel_format".equals(kind)) format = 99;
        else if ("invalid_stride".equals(kind)) rowStride = 4;
        else if ("integer_overflow_dimensions".equals(kind)) {
            rowStride = Integer.MAX_VALUE;
            declaredBytes = Integer.MAX_VALUE;
        }
        else if ("stale_generation".equals(kind)) requestGeneration = generation - 1L;
        else if ("missing_pfd".equals(kind)) includeDescriptor = false;
        else if ("short_payload".equals(kind) || "premature_pfd_close".equals(kind)) bytes = new byte[8];
        else if ("long_payload".equals(kind)) bytes = new byte[24];
        else if ("invalid_crop".equals(kind)) { }
        else throw new IllegalArgumentException("unknown malformed case: " + kind);
        int frameWidth = "negative_dimensions".equals(kind) ? -2 :
                ("zero_dimensions".equals(kind) ? 0 :
                ("integer_overflow_dimensions".equals(kind) ? Integer.MAX_VALUE : width));
        int frameHeight = "negative_dimensions".equals(kind) ? -2 :
                ("zero_dimensions".equals(kind) ? 0 :
                ("integer_overflow_dimensions".equals(kind) ? Integer.MAX_VALUE : height));
        ParcelFileDescriptor[] pipe = includeDescriptor ? ParcelFileDescriptor.createPipe() : null;
        final ParcelFileDescriptor writerEnd = pipe == null ? null : pipe[1];
        Thread writer = null;
        if (writerEnd != null) {
            final byte[] payload = bytes;
            writer = new Thread(new Runnable() {
                public void run() {
                    FileOutputStream output = null;
                    try {
                        output = new ParcelFileDescriptor.AutoCloseOutputStream(writerEnd);
                        output.write(payload);
                        output.flush();
                    } catch (IOException ignored) {
                    } finally { if (output != null) try { output.close(); } catch (IOException ignored) { } }
                }
            }, "ClarityLinkMalformedFrameWriter");
            writer.start();
        }
        long frameId = nextFrameId.getAndIncrement();
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeInt(FrameIpcProtocol.VERSION);
            FrameStreamIdentity currentIdentity = identity;
            if (currentIdentity == null) throw new IllegalStateException("stream_not_registered");
            writeIdentity(data, currentIdentity.withGeneration(requestGeneration));
            data.writeLong(frameId);
            data.writeLong(timestampNs);
            data.writeInt(frameWidth); data.writeInt(frameHeight); data.writeInt(rowStride);
            data.writeInt(format); data.writeInt(0);
            data.writeInt(0); data.writeInt(0);
            data.writeInt("invalid_crop".equals(kind) ? 3 : frameWidth);
            data.writeInt(frameHeight);
            data.writeInt(declaredBytes);
            data.writeParcelable(pipe == null ? null : pipe[0], 0);
            endpoint.transact(FrameIpcProtocol.FRAME, data, reply, 0);
            reply.readException();
            boolean accepted = reply.readInt() != 0;
            String reason = reply.readString();
            if (accepted) throw new IllegalStateException("malformed request accepted: " + kind);
            if (writer != null) writer.join(5000L);
            if (writer != null && writer.isAlive()) throw new IllegalStateException("malformed PFD writer blocked: " + kind);
            return reason;
        } finally {
            if (pipe != null) {
                try { pipe[0].close(); } catch (IOException ignored) { }
                if (writer == null) try { pipe[1].close(); } catch (IOException ignored) { }
            }
            reply.recycle(); data.recycle();
        }
    }
}
