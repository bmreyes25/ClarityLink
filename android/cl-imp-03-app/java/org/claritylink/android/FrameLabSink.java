package org.claritylink.android;

import android.os.Binder;
import android.os.IBinder;
import android.os.Parcel;
import android.os.ParcelFileDescriptor;
import android.os.Process;
import android.os.RemoteException;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.zip.CRC32;

/** Primary-output recorder used only by the isolated two-stream API17 laboratory. */
final class FrameLabSink extends Binder {
    private static final String SINK_DESCRIPTOR = "org.claritylink.android.IClarityLinkViewFrameSink";
    private volatile FrameStreamIdentity identity;
    private volatile long lastFrameId;
    private volatile long lastTimestampNs = -1L;
    private volatile long lastChecksum;
    private volatile int renderedFrames;

    FrameLabSink(FrameStreamIdentity identity) {
        if (identity == null || !identity.isValid() || identity.streamType != FrameStreamIdentity.TYPE110)
            throw new IllegalArgumentException("Type110 laboratory output identity required");
        this.identity = identity;
    }

    int renderedFrames() { return renderedFrames; }
    long lastFrameId() { return lastFrameId; }
    long lastChecksum() { return lastChecksum; }

    static final class Stats {
        final int frames;
        final long frameId;
        final long checksum;
        final int pid;
        final int uid;
        Stats(int frames, long frameId, long checksum, int pid, int uid) {
            this.frames = frames; this.frameId = frameId; this.checksum = checksum;
            this.pid = pid; this.uid = uid;
        }
    }

    static Stats queryStats(IBinder remote) throws RemoteException {
        if (remote == null || !remote.isBinderAlive()) return null;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(SINK_DESCRIPTOR);
            remote.transact(FrameIpcProtocol.FRAME_LAB_QUERY_STATS, data, reply, 0);
            reply.readException();
            return new Stats(reply.readInt(), reply.readLong(), reply.readLong(),
                    reply.readInt(), reply.readInt());
        } finally { reply.recycle(); data.recycle(); }
    }

    @Override protected synchronized boolean onTransact(int code, Parcel data, Parcel reply, int flags)
            throws RemoteException {
        if (code == FrameIpcProtocol.FRAME_LAB_QUERY_STATS) {
            if (Binder.getCallingUid() != Process.myUid()) {
                reply.writeException(new SecurityException("lab output caller rejected"));
                return true;
            }
            data.enforceInterface(SINK_DESCRIPTOR);
            reply.writeNoException();
            reply.writeInt(renderedFrames);
            reply.writeLong(lastFrameId);
            reply.writeLong(lastChecksum);
            reply.writeInt(Process.myPid());
            reply.writeInt(Process.myUid());
            return true;
        }
        if (code != FrameIpcProtocol.VIEW_FRAME && code != FrameIpcProtocol.VIEW_WARNING &&
                code != FrameIpcProtocol.VIEW_CHANGE_GENERATION)
            return super.onTransact(code, data, reply, flags);
        if (Binder.getCallingUid() != Process.myUid()) {
            reply.writeException(new SecurityException("lab output caller rejected"));
            return true;
        }
        data.enforceInterface("org.claritylink.android.IClarityLinkViewFrameSink");
        int version = data.readInt();
        if (version != FrameIpcProtocol.VERSION) {
            if (code == FrameIpcProtocol.VIEW_FRAME) {
                FrameStreamIdentity ignored = readIdentity(data);
                data.readLong(); data.readLong(); data.readInt(); data.readInt(); data.readInt();
                data.readInt(); data.readInt(); data.readInt(); data.readInt(); data.readInt();
                data.readInt(); data.readInt(); data.readLong();
                closeQuietly((ParcelFileDescriptor) data.readParcelable(
                        ParcelFileDescriptor.class.getClassLoader()));
            }
            reply.writeNoException(); reply.writeInt(0);
            if (code == FrameIpcProtocol.VIEW_FRAME) reply.writeString("ipc_version_rejected");
            return true;
        }
        FrameStreamIdentity request = readIdentity(data);
        if (code == FrameIpcProtocol.VIEW_CHANGE_GENERATION) {
            long nextGeneration = data.readLong();
            boolean accepted = identity != null && identity.equals(request) &&
                    nextGeneration > request.streamGeneration;
            if (accepted) {
                identity = request.withGeneration(nextGeneration);
                lastFrameId = 0L;
                lastTimestampNs = -1L;
            }
            reply.writeNoException(); reply.writeInt(accepted ? 1 : 0);
            return true;
        }
        if (code == FrameIpcProtocol.VIEW_WARNING) {
            int visible = data.readInt();
            boolean accepted = identity != null && identity.equals(request) &&
                    (visible == 0 || visible == 1);
            reply.writeNoException(); reply.writeInt(accepted ? 1 : 0);
            return true;
        }

        long frameId = data.readLong();
        long timestampNs = data.readLong();
        int width = data.readInt(); int height = data.readInt(); int stride = data.readInt();
        int format = data.readInt(); int rotation = data.readInt();
        int left = data.readInt(); int top = data.readInt(); int right = data.readInt(); int bottom = data.readInt();
        int length = data.readInt(); long expectedCrc = data.readLong();
        ParcelFileDescriptor descriptor = data.readParcelable(ParcelFileDescriptor.class.getClassLoader());
        int expectedLength = FrameIpcProtocol.expectedRgbaBytes(width, height, stride);
        boolean valid = identity != null && identity.equals(request) && request.streamType == FrameStreamIdentity.TYPE110 &&
                request.outputId == FrameStreamIdentity.OUTPUT_PRIMARY_LAB && frameId > lastFrameId &&
                timestampNs > lastTimestampNs && format == FrameIpcProtocol.PIXEL_FORMAT_RGBA_8888 &&
                rotation == 0 && left >= 0 && top >= 0 && right > left && bottom > top &&
                right <= width && bottom <= height && expectedLength == length && descriptor != null;
        CRC32 crc = new CRC32();
        boolean payloadValid = false;
        try {
            if (valid) {
                FileInputStream input = new ParcelFileDescriptor.AutoCloseInputStream(descriptor);
                descriptor = null;
                byte[] buffer = new byte[8192];
                int remaining = length;
                while (remaining > 0) {
                    int count = input.read(buffer, 0, Math.min(buffer.length, remaining));
                    if (count < 0) break;
                    crc.update(buffer, 0, count);
                    remaining -= count;
                }
                payloadValid = remaining == 0 && input.read() == -1 && crc.getValue() == expectedCrc;
                input.close();
            }
        } catch (IOException ignored) {
            payloadValid = false;
        } finally { closeQuietly(descriptor); }
        boolean accepted = valid && payloadValid;
        if (accepted) {
            lastFrameId = frameId;
            lastTimestampNs = timestampNs;
            lastChecksum = crc.getValue();
            renderedFrames++;
            android.util.Log.i("ClarityLinkCLIMP03", "TYPE110_LAB_SINK_FRAME_ACCEPTED pid=" +
                    Process.myPid() + " session_id=" + request.sessionId + " connection_id=" +
                    request.connectionId + " generation=" + request.streamGeneration +
                    " frame_id=" + frameId + " timestamp_ns=" + timestampNs +
                    " accepted_count=" + renderedFrames);
        }
        reply.writeNoException(); reply.writeInt(accepted ? 1 : 0);
        reply.writeString(accepted ? "primary_lab_recorded" : "primary_lab_frame_rejected");
        return true;
    }

    private static FrameStreamIdentity readIdentity(Parcel data) {
        return new FrameStreamIdentity(data.readLong(), data.readInt(), data.readLong(),
                data.readLong(), data.readInt());
    }

    private static void closeQuietly(ParcelFileDescriptor value) {
        if (value != null) try { value.close(); } catch (IOException ignored) { }
    }
}
