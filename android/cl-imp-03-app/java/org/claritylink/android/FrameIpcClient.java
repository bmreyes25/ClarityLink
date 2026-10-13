package org.claritylink.android;

import android.os.IBinder;
import android.os.Parcel;
import android.os.ParcelFileDescriptor;
import android.os.RemoteException;

import org.claritylink.renderer.DecodedFrame;
import org.claritylink.renderer.FrameBackpressureGate;

import java.io.FileOutputStream;
import java.io.IOException;

/** Single-flight, bounded API17 Binder/pipe client for the project-owned compositor process. */
final class FrameIpcClient {
    interface Callback { void complete(boolean accepted, String reason); }

    private final IBinder endpoint;
    private final FrameBackpressureGate frameGate = new FrameBackpressureGate();
    private volatile long activeGeneration;
    private volatile boolean closed;

    FrameIpcClient(IBinder endpoint) { this.endpoint = endpoint; }

    int begin(long generation) throws RemoteException {
        if (closed || generation <= 0 || !endpoint.isBinderAlive()) return -1;
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeInt(FrameIpcProtocol.VERSION);
            data.writeLong(generation);
            endpoint.transact(FrameIpcProtocol.BEGIN, data, reply, 0);
            reply.readException();
            if (reply.readInt() == 0) return -1;
            activeGeneration = generation;
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
                        data.writeLong(generation);
                        data.writeLong(frame.presentationTimeNs);
                        data.writeInt(frame.width);
                        data.writeInt(frame.height);
                        data.writeInt(frame.rowStride);
                        data.writeInt(frame.byteSize());
                        data.writeParcelable(pipe[0], 0);
                        endpoint.transact(FrameIpcProtocol.FRAME, data, reply, 0);
                        reply.readException();
                        accepted = reply.readInt() != 0;
                        reason = accepted ? "accepted" : "remote_rejected";
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
            data.writeLong(generation);
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
            data.writeLong(generation);
            data.writeInt(visible ? 1 : 0);
            endpoint.transact(FrameIpcProtocol.WARNING, data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    boolean hasFrameInFlight() { return frameGate.isOccupied(); }
}
