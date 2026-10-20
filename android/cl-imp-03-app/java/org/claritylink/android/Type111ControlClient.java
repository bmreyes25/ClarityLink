package org.claritylink.android;

import android.os.IBinder;
import android.os.Parcel;
import android.os.RemoteException;

/** Typed control calls carried by the same private Binder v3 service as the media streams. */
final class Type111ControlClient {
    private final IBinder endpoint;

    Type111ControlClient(IBinder endpoint) { this.endpoint = endpoint; }

    boolean registerOwnerDeathQueryObserver(final FrameStreamIdentity owner, int observerPid,
            IBinder observerToken)
            throws RemoteException {
        if (owner == null || !owner.isValid() || owner.streamType != FrameStreamIdentity.TYPE110)
            return false;
        if (observerPid <= 0 || observerToken == null || !observerToken.isBinderAlive()) return false;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            header(data); writeIdentity(data, owner);
            data.writeInt(observerPid);
            data.writeStrongBinder(observerToken);
            endpoint.transact(FrameIpcProtocol.LAB_REGISTER_OWNER_DEATH_QUERY_OBSERVER,
                    data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    static final class StreamQuery {
        final boolean authorized;
        final boolean ownerValid;
        final boolean sinkAttached;
        final FrameStreamIdentity identity;
        final int compositorPid;
        StreamQuery(boolean authorized, boolean ownerValid, boolean sinkAttached, FrameStreamIdentity identity,
                int compositorPid) {
            this.authorized = authorized; this.ownerValid = ownerValid; this.sinkAttached = sinkAttached;
            this.identity = identity; this.compositorPid = compositorPid;
        }
    }

    static final class FrameStats {
        final boolean authorized;
        final boolean registered;
        final int activePfdTransfers;
        final int retainedFrameBytes;
        final boolean transferActive;
        final long lastFrameId;
        FrameStats(boolean authorized, boolean registered, int activePfdTransfers, int retainedFrameBytes,
                boolean transferActive, long lastFrameId) {
            this.authorized = authorized; this.registered = registered;
            this.activePfdTransfers = activePfdTransfers;
            this.retainedFrameBytes = retainedFrameBytes;
            this.transferActive = transferActive;
            this.lastFrameId = lastFrameId;
        }
    }

    FrameStats queryFrameStats(FrameStreamIdentity identity) throws RemoteException {
        if (identity == null || !identity.isValid()) return null;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            header(data); writeIdentity(data, identity);
            endpoint.transact(FrameIpcProtocol.FRAME_LAB_QUERY_STATS, data, reply, 0);
            reply.readException();
            boolean authorized = reply.readInt() != 0;
            return new FrameStats(authorized, reply.readInt() != 0, reply.readInt(), reply.readInt(),
                    reply.readInt() != 0, reply.readLong());
        } finally { reply.recycle(); data.recycle(); }
    }

    StreamQuery queryType111Stream(FrameStreamIdentity type110Owner) throws RemoteException {
        if (type110Owner == null || !type110Owner.isValid() ||
                type110Owner.streamType != FrameStreamIdentity.TYPE110) return null;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            header(data); writeIdentity(data, type110Owner);
            endpoint.transact(FrameIpcProtocol.TYPE111_QUERY_STREAM, data, reply, 0);
            reply.readException();
            boolean authorized = reply.readInt() != 0;
            boolean ownerValid = reply.readInt() != 0;
            boolean present = reply.readInt() != 0;
            boolean sinkAttached = reply.readInt() != 0;
            FrameStreamIdentity identity = present ? readIdentity(reply) : null;
            int pid = reply.readInt();
            return new StreamQuery(authorized, ownerValid, sinkAttached, identity, pid);
        } finally { reply.recycle(); data.recycle(); }
    }

    boolean detachType111Sink(final FrameStreamIdentity type110Owner,
            final FrameStreamIdentity type111Identity) throws RemoteException {
        if (type110Owner == null || !type110Owner.isValid() ||
                type110Owner.streamType != FrameStreamIdentity.TYPE110 ||
                type111Identity == null || !type111Identity.isValid() ||
                type111Identity.streamType != FrameStreamIdentity.TYPE111 ||
                type110Owner.sessionId != type111Identity.sessionId) return false;
        return transact(FrameIpcProtocol.TYPE111_DETACH_SINK, new Writer() {
            public void write(Parcel data) {
                writeIdentity(data, type110Owner); writeIdentity(data, type111Identity);
            }
        });
    }

    boolean registerLabCapability(final FrameStreamIdentity type110Owner, final String uuid, final int width,
            final int height, final int fps)
            throws RemoteException {
        if (type110Owner == null || !type110Owner.isValid() ||
                type110Owner.streamType != FrameStreamIdentity.TYPE110) return false;
        return transact(FrameIpcProtocol.TYPE111_CAPABILITY, new Writer() {
            public void write(Parcel data) {
                writeIdentity(data, type110Owner);
                data.writeLong(type110Owner.sessionId); data.writeString(uuid);
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

    /** Register a compositor-held recovery receipt for this exact live parent/child identity. */
    boolean registerType110Recovery(FrameStreamIdentity owner, FrameStreamIdentity expectedDeath,
            long lastFrameId, int sinkPid) {
        if (endpoint == null || owner == null || !owner.isValid() ||
                owner.streamType != FrameStreamIdentity.TYPE110 || expectedDeath == null ||
                !expectedDeath.isValid() || expectedDeath.streamType != FrameStreamIdentity.TYPE111 ||
                owner.sessionId != expectedDeath.sessionId || lastFrameId <= 0L || sinkPid <= 0)
            return false;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            header(data); writeIdentity(data, owner); writeIdentity(data, expectedDeath);
            data.writeLong(lastFrameId); data.writeInt(sinkPid);
            endpoint.transact(FrameIpcProtocol.TYPE110_PROBE_REGISTER, data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } catch (Exception failure) { return false; }
        finally { reply.recycle(); data.recycle(); }
    }

    boolean armLabParentTeardownBarrier(final FrameStreamIdentity type110Owner) throws RemoteException {
        if (!validOwner(type110Owner)) return false;
        return transact(FrameIpcProtocol.LAB_ARM_PARENT_TEARDOWN_BARRIER, new Writer() {
            public void write(Parcel data) { writeIdentity(data, type110Owner); }
        });
    }

    boolean awaitLabParentTeardownBarrier(final FrameStreamIdentity type110Owner,
            final boolean contender, final long timeoutMs) throws RemoteException {
        if (!validOwner(type110Owner) || timeoutMs < 0L || timeoutMs > 10000L) return false;
        return barrierWait(contender ? FrameIpcProtocol.LAB_WAIT_PARENT_TEARDOWN_CONTENDER :
                FrameIpcProtocol.LAB_WAIT_PARENT_TEARDOWN_BARRIER, type110Owner, timeoutMs);
    }

    boolean releaseLabParentTeardownBarrier(final FrameStreamIdentity type110Owner) throws RemoteException {
        if (!validOwner(type110Owner)) return false;
        return barrierWait(FrameIpcProtocol.LAB_RELEASE_PARENT_TEARDOWN_BARRIER, type110Owner, 0L);
    }

    boolean armLabDelayedSinkDeathCallback(final FrameStreamIdentity type111Identity)
            throws RemoteException {
        if (type111Identity == null || !type111Identity.isValid() ||
                type111Identity.streamType != FrameStreamIdentity.TYPE111) return false;
        return identityCall(FrameIpcProtocol.LAB_ARM_DELAYED_SINK_DEATH_CALLBACK, type111Identity);
    }

    boolean fireLabDelayedSinkDeathCallback(final FrameStreamIdentity type110Owner,
            final FrameStreamIdentity currentType111Identity) throws RemoteException {
        if (!validOwner(type110Owner) || currentType111Identity == null ||
                !currentType111Identity.isValid() ||
                currentType111Identity.streamType != FrameStreamIdentity.TYPE111 ||
                currentType111Identity.sessionId != type110Owner.sessionId) return false;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            header(data);
            writeIdentity(data, type110Owner);
            writeIdentity(data, currentType111Identity);
            endpoint.transact(FrameIpcProtocol.LAB_FIRE_DELAYED_SINK_DEATH_CALLBACK, data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    private boolean barrierWait(int code, FrameStreamIdentity owner, long timeoutMs)
            throws RemoteException {
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            header(data); writeIdentity(data, owner);
            if (code != FrameIpcProtocol.LAB_RELEASE_PARENT_TEARDOWN_BARRIER) data.writeLong(timeoutMs);
            endpoint.transact(code, data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    private static boolean validOwner(FrameStreamIdentity identity) {
        return identity != null && identity.isValid() && identity.streamType == FrameStreamIdentity.TYPE110;
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

    private static FrameStreamIdentity readIdentity(Parcel data) {
        return new FrameStreamIdentity(data.readLong(), data.readInt(), data.readLong(),
                data.readLong(), data.readInt());
    }

    private interface Writer { void write(Parcel data); }
}
