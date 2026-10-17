package org.claritylink.android;

import android.os.IBinder;
import android.os.Parcel;
import android.os.RemoteException;

/** Typed control calls carried by the same private Binder v3 service as the media streams. */
final class Type111ControlClient {
    private final IBinder endpoint;

    Type111ControlClient(IBinder endpoint) { this.endpoint = endpoint; }

    boolean registerLabCapability(final long sessionId, final String uuid, final int width,
            final int height, final int fps)
            throws RemoteException {
        return transact(FrameIpcProtocol.TYPE111_CAPABILITY, new Writer() {
            public void write(Parcel data) {
                data.writeLong(sessionId); data.writeString(uuid);
                data.writeInt(width); data.writeInt(height); data.writeInt(fps);
                data.writeInt(2);
                data.writeString(Type111ControlPlane.MAP_CONTEXT);
                data.writeString(Type111ControlPlane.INSTRUCTION_CONTEXT);
            }
        });
    }

    boolean setup(FrameStreamIdentity identity) throws RemoteException {
        return identityCall(FrameIpcProtocol.TYPE111_SETUP, identity);
    }

    boolean navigation(FrameStreamIdentity identity, String provider, boolean active,
            boolean instruction) throws RemoteException {
        if (identity == null || !identity.isValid()) return false;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            header(data); writeIdentity(data, identity); data.writeString(provider);
            data.writeInt(active ? 1 : 0); data.writeInt(instruction ? 1 : 0);
            endpoint.transact(FrameIpcProtocol.TYPE111_NAVIGATION, data, reply, 0);
            reply.readException(); return readAccepted(reply);
        } finally { reply.recycle(); data.recycle(); }
    }

    boolean presentation(FrameStreamIdentity identity, String command, String context)
            throws RemoteException {
        if (identity == null || !identity.isValid()) return false;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            header(data); writeIdentity(data, identity); data.writeString(command); data.writeString(context);
            endpoint.transact(FrameIpcProtocol.TYPE111_PRESENTATION, data, reply, 0);
            reply.readException(); return readAccepted(reply);
        } finally { reply.recycle(); data.recycle(); }
    }

    boolean geometry(FrameStreamIdentity identity, int[] rect, boolean safe) throws RemoteException {
        if (identity == null || !identity.isValid() || rect == null || rect.length != 4) return false;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            header(data); writeIdentity(data, identity); data.writeInt(safe ? 1 : 0);
            for (int value : rect) data.writeInt(value);
            endpoint.transact(FrameIpcProtocol.TYPE111_GEOMETRY, data, reply, 0);
            reply.readException(); return readAccepted(reply);
        } finally { reply.recycle(); data.recycle(); }
    }

    long videoConfig(FrameStreamIdentity identity, int width, int height) throws RemoteException {
        if (identity == null || !identity.isValid()) return -1L;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            header(data); writeIdentity(data, identity); data.writeInt(width); data.writeInt(height);
            endpoint.transact(FrameIpcProtocol.TYPE111_VIDEO_CONFIG, data, reply, 0);
            reply.readException();
            if (!readAccepted(reply)) return -1L;
            return reply.readLong();
        } finally { reply.recycle(); data.recycle(); }
    }

    boolean parentTeardown(final FrameStreamIdentity type110Owner) throws RemoteException {
        if (type110Owner == null || !type110Owner.isValid() ||
                type110Owner.streamType != FrameStreamIdentity.TYPE110) return false;
        return transact(FrameIpcProtocol.TYPE111_PARENT_TEARDOWN, new Writer() {
            public void write(Parcel data) { writeIdentity(data, type110Owner); }
        });
    }

    private boolean identityCall(int code, final FrameStreamIdentity identity) throws RemoteException {
        if (identity == null || !identity.isValid()) return false;
        return transact(code, new Writer() { public void write(Parcel data) { writeIdentity(data, identity); } });
    }

    private boolean transact(int code, Writer writer) throws RemoteException {
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            header(data); writer.write(data);
            endpoint.transact(code, data, reply, 0);
            reply.readException(); return readAccepted(reply);
        } finally { reply.recycle(); data.recycle(); }
    }

    private static boolean readAccepted(Parcel reply) {
        boolean accepted = reply.readInt() != 0;
        reply.readString(); // Stable, bounded reason is available in the service log for failures.
        return accepted;
    }

    private static void header(Parcel data) {
        data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
        data.writeInt(FrameIpcProtocol.VERSION);
    }

    private static void writeIdentity(Parcel data, FrameStreamIdentity identity) {
        data.writeLong(identity.sessionId); data.writeInt(identity.streamType);
        data.writeLong(identity.connectionId); data.writeLong(identity.streamGeneration);
        data.writeInt(identity.outputId);
    }

    private interface Writer { void write(Parcel data); }
}
