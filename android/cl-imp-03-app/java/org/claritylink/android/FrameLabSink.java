package org.claritylink.android;

import android.app.ActivityManager;
import android.content.Context;
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
    private final Context context;
    private IBinder compositorEpoch;
    private IBinder.DeathRecipient compositorDeathRecipient;
    private volatile long lastFrameId;
    private volatile long lastTimestampNs = -1L;
    private volatile long lastChecksum;
    private volatile int renderedFrames;
    private volatile int compositorPid;
    private volatile int statsOwnerPid;
    private IBinder statsOwnerToken;
    private IBinder.DeathRecipient statsOwnerDeathRecipient;
    private boolean ownerPidRebindPrepared;
    private boolean statsOwnerPidQueriesBlocked;
    private int pendingPreviousOwnerPid;
    private int pendingReplacementOwnerPid;
    private IBinder pendingOwnerPidRebindToken;

    FrameLabSink(Context context, FrameStreamIdentity identity) {
        if (context == null) throw new IllegalArgumentException("owner context required");
        if (identity == null || !identity.isValid() || identity.streamType != FrameStreamIdentity.TYPE110)
            throw new IllegalArgumentException("Type110 laboratory output identity required");
        this.context = context.getApplicationContext();
        this.identity = identity;
    }

    int renderedFrames() { return renderedFrames; }
    long lastFrameId() { return lastFrameId; }
    long lastChecksum() { return lastChecksum; }
    FrameStreamIdentity queryLocalIdentity() { return identity; }

    synchronized boolean clearIfUnbound(FrameStreamIdentity expected, String cause) {
        if (expected == null || identity == null || !identity.equals(expected) || compositorEpoch != null)
            return false;
        clearIdentityAndCompositorEpoch();
        android.util.Log.i("ClarityLinkCLIMP03", "TYPE110_UNBOUND_ADMISSION_REVOKED session_id=" +
                expected.sessionId + " cause=" + cause);
        return true;
    }

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
        return queryStats(remote, null);
    }
    static Stats queryStats(IBinder remote, IBinder ownerToken) throws RemoteException {
        if (remote == null || !remote.isBinderAlive()) return null;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(SINK_DESCRIPTOR);
            data.writeStrongBinder(ownerToken);
            remote.transact(FrameIpcProtocol.FRAME_LAB_QUERY_STATS, data, reply, 0);
            reply.readException();
            return new Stats(reply.readInt(), reply.readLong(), reply.readLong(),
                    reply.readInt(), reply.readInt());
        } finally { reply.recycle(); data.recycle(); }
    }

    static FrameStreamIdentity queryIdentity(IBinder remote) throws RemoteException {
        if (remote == null || !remote.isBinderAlive()) return null;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(SINK_DESCRIPTOR);
            remote.transact(FrameIpcProtocol.FRAME_LAB_QUERY_IDENTITY, data, reply, 0);
            reply.readException();
            if (reply.readInt() == 0) return null;
            return readIdentity(reply);
        } finally { reply.recycle(); data.recycle(); }
    }

    static boolean revokeParentAuthority(IBinder remote, FrameStreamIdentity expected)
            throws RemoteException {
        return revokeParentAuthority(remote, expected, null);
    }

    static boolean revokeParentAuthority(IBinder remote, FrameStreamIdentity expected,
            IBinder expectedOwnerToken) throws RemoteException {
        if (remote == null || !remote.isBinderAlive() || expected == null) return false;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(SINK_DESCRIPTOR);
            writeIdentity(data, expected);
            data.writeStrongBinder(expectedOwnerToken);
            remote.transact(FrameIpcProtocol.FRAME_LAB_REVOKE_PARENT_AUTHORITY, data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    static boolean bindCompositorEpoch(IBinder remote, FrameStreamIdentity expected,
            IBinder compositor, int ownerPid, IBinder ownerToken) throws RemoteException {
        if (remote == null || !remote.isBinderAlive() || expected == null ||
                compositor == null || !compositor.isBinderAlive() || ownerPid <= 0 ||
                ownerToken == null || !ownerToken.isBinderAlive()) return false;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(SINK_DESCRIPTOR);
            writeIdentity(data, expected);
            data.writeStrongBinder(compositor);
            data.writeInt(ownerPid);
            data.writeStrongBinder(ownerToken);
            remote.transact(FrameIpcProtocol.FRAME_LAB_BIND_COMPOSITOR_EPOCH, data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    static boolean prepareOwnerPidRebind(IBinder remote, FrameStreamIdentity expected, IBinder compositor,
            int previousOwnerPid, int replacementOwnerPid, IBinder ownerToken) throws RemoteException {
        return ownerPidRebindTransaction(remote, FrameIpcProtocol.FRAME_LAB_PREPARE_OWNER_PID_REBIND,
                expected, compositor, previousOwnerPid, replacementOwnerPid, ownerToken);
    }
    static boolean completeOwnerPidRebind(IBinder remote, FrameStreamIdentity expected, IBinder compositor,
            int previousOwnerPid, int replacementOwnerPid, IBinder ownerToken) throws RemoteException {
        return ownerPidRebindTransaction(remote, FrameIpcProtocol.FRAME_LAB_COMPLETE_OWNER_PID_REBIND,
                expected, compositor, previousOwnerPid, replacementOwnerPid, ownerToken);
    }
    static boolean cancelOwnerPidRebind(IBinder remote, FrameStreamIdentity expected, IBinder compositor,
            int previousOwnerPid, int replacementOwnerPid, IBinder ownerToken) throws RemoteException {
        return ownerPidRebindTransaction(remote, FrameIpcProtocol.FRAME_LAB_CANCEL_OWNER_PID_REBIND,
                expected, compositor, previousOwnerPid, replacementOwnerPid, ownerToken);
    }
    private static boolean ownerPidRebindTransaction(IBinder remote, int transaction,
            FrameStreamIdentity expected, IBinder compositor, int previousOwnerPid,
            int replacementOwnerPid, IBinder ownerToken) throws RemoteException {
        if (remote == null || !remote.isBinderAlive() || expected == null || compositor == null ||
                !compositor.isBinderAlive() || previousOwnerPid <= 0 || replacementOwnerPid <= 0 ||
                previousOwnerPid == replacementOwnerPid || ownerToken == null ||
                !ownerToken.isBinderAlive()) return false;
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(SINK_DESCRIPTOR);
            writeIdentity(data, expected);
            data.writeStrongBinder(compositor);
            data.writeInt(previousOwnerPid);
            data.writeInt(replacementOwnerPid);
            data.writeStrongBinder(ownerToken);
            remote.transact(transaction, data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    @Override protected synchronized boolean onTransact(int code, Parcel data, Parcel reply, int flags)
            throws RemoteException {
        if (code == FrameIpcProtocol.FRAME_LAB_QUERY_STATS) {
            data.enforceInterface(SINK_DESCRIPTOR);
            IBinder suppliedOwnerToken = data.readStrongBinder();
            int callerPid = Binder.getCallingPid();
            boolean compositorCaller = isCompositorProcessCaller() && suppliedOwnerToken != null &&
                    suppliedOwnerToken.isBinderAlive() &&
                    (statsOwnerToken == null || statsOwnerToken == suppliedOwnerToken) &&
                    (compositorEpoch == null || (compositorPid == callerPid &&
                    compositorEpoch.isBinderAlive() && statsOwnerToken != null &&
                    statsOwnerToken.isBinderAlive()));
            boolean ownerCaller = callerPid > 0 && callerPid == statsOwnerPid &&
                    !statsOwnerPidQueriesBlocked && statsOwnerToken != null &&
                    statsOwnerToken.isBinderAlive() && suppliedOwnerToken == statsOwnerToken;
            if (Binder.getCallingUid() != Process.myUid() || callerPid <= 0 ||
                    (!compositorCaller && !ownerCaller)) {
                reply.writeException(new SecurityException("lab output caller rejected"));
                return true;
            }
            reply.writeNoException();
            reply.writeInt(renderedFrames);
            reply.writeLong(lastFrameId);
            reply.writeLong(lastChecksum);
            reply.writeInt(Process.myPid());
            reply.writeInt(Process.myUid());
            return true;
        }
        if (code == FrameIpcProtocol.FRAME_LAB_QUERY_IDENTITY) {
            if (Binder.getCallingUid() != Process.myUid()) {
                reply.writeException(new SecurityException("lab output caller rejected"));
                return true;
            }
            data.enforceInterface(SINK_DESCRIPTOR);
            FrameStreamIdentity current = identity;
            reply.writeNoException();
            reply.writeInt(current == null ? 0 : 1);
            if (current != null) writeIdentity(reply, current);
            return true;
        }
        if (code == FrameIpcProtocol.FRAME_LAB_REVOKE_PARENT_AUTHORITY) {
            if (!isCompositorProcessCaller()) {
                reply.writeException(new SecurityException("lab owner revocation caller rejected"));
                return true;
            }
            data.enforceInterface(SINK_DESCRIPTOR);
            FrameStreamIdentity expected = readIdentity(data);
            IBinder expectedOwnerToken = data.readStrongBinder();
            boolean tokenMatches = expectedOwnerToken == null || statsOwnerToken == expectedOwnerToken;
            boolean accepted = identity != null && identity.equals(expected) && tokenMatches;
            if (accepted) clearIdentityAndCompositorEpoch();
            reply.writeNoException();
            reply.writeInt(accepted ? 1 : 0);
            return true;
        }
        if (code == FrameIpcProtocol.FRAME_LAB_BIND_COMPOSITOR_EPOCH) {
            if (!isCompositorProcessCaller()) {
                reply.writeException(new SecurityException("lab owner epoch caller rejected"));
                return true;
            }
            data.enforceInterface(SINK_DESCRIPTOR);
            FrameStreamIdentity expected = readIdentity(data);
            final IBinder compositor = data.readStrongBinder();
            final int ownerPid = data.readInt();
            final IBinder ownerToken = data.readStrongBinder();
            boolean accepted = false;
            if (ownerPid > 0 && identity != null && identity.equals(expected) && compositor != null &&
                    compositor.isBinderAlive() && ownerToken != null && ownerToken.isBinderAlive()) {
                if (compositorEpoch == compositor && compositorDeathRecipient != null) {
                    accepted = compositorPid == Binder.getCallingPid() && statsOwnerPid == ownerPid &&
                            statsOwnerToken == ownerToken && ownerToken.isBinderAlive();
                } else if (compositorEpoch == null || !compositorEpoch.isBinderAlive()) {
                    final FrameStreamIdentity boundIdentity = identity;
                    final IBinder.DeathRecipient ownerRecipient = new IBinder.DeathRecipient() {
                        public void binderDied() {
                            synchronized (FrameLabSink.this) {
                                if (statsOwnerToken == ownerToken) {
                                    statsOwnerPid = 0;
                                    if (identity != null && identity.sameStream(boundIdentity) &&
                                            compositorEpoch == compositor) {
                                        clearIdentityAndCompositorEpoch();
                                        android.util.Log.i("ClarityLinkCLIMP03",
                                                "TYPE110_OWNER_EPOCH_REVOKED session_id=" +
                                                boundIdentity.sessionId +
                                                " cause=owner_lifetime_token_death");
                                    } else {
                                        statsOwnerDeathRecipient = null;
                                    }
                                }
                            }
                        }
                    };
                    final IBinder.DeathRecipient recipient = new IBinder.DeathRecipient() {
                        public void binderDied() {
                            synchronized (FrameLabSink.this) {
                                if (compositorEpoch == compositor && identity != null &&
                                        identity.sameStream(boundIdentity)) {
                                    clearIdentityAndCompositorEpoch();
                                    android.util.Log.i("ClarityLinkCLIMP03",
                                            "TYPE110_OWNER_EPOCH_REVOKED session_id=" +
                                            boundIdentity.sessionId + " cause=compositor_process_death");
                                }
                            }
                        }
                    };
                    boolean ownerLinked = false;
                    try {
                        ownerToken.linkToDeath(ownerRecipient, 0);
                        ownerLinked = true;
                        compositor.linkToDeath(recipient, 0);
                        compositorEpoch = compositor;
                        compositorDeathRecipient = recipient;
                        compositorPid = Binder.getCallingPid();
                        statsOwnerPid = ownerPid;
                        statsOwnerToken = ownerToken;
                        statsOwnerDeathRecipient = ownerRecipient;
                        accepted = true;
                    } catch (RemoteException deadBinder) {
                        if (ownerLinked) {
                            try { ownerToken.unlinkToDeath(ownerRecipient, 0); }
                            catch (RuntimeException ignored) { }
                        }
                    }
                }
            }
            reply.writeNoException();
            reply.writeInt(accepted ? 1 : 0);
            return true;
        }
        if (code == FrameIpcProtocol.FRAME_LAB_PREPARE_OWNER_PID_REBIND ||
                code == FrameIpcProtocol.FRAME_LAB_COMPLETE_OWNER_PID_REBIND ||
                code == FrameIpcProtocol.FRAME_LAB_CANCEL_OWNER_PID_REBIND) {
            if (!isCompositorProcessCaller()) {
                reply.writeException(new SecurityException("lab owner rebind caller rejected"));
                return true;
            }
            data.enforceInterface(SINK_DESCRIPTOR);
            FrameStreamIdentity expected = readIdentity(data);
            IBinder compositor = data.readStrongBinder();
            int previousOwnerPid = data.readInt();
            int replacementOwnerPid = data.readInt();
            IBinder ownerToken = data.readStrongBinder();
            boolean identityValid = expected != null && expected.streamType == FrameStreamIdentity.TYPE110 &&
                    expected.equals(identity) && compositor != null && compositor == compositorEpoch &&
                    compositor.isBinderAlive() && compositorPid == Binder.getCallingPid() &&
                    previousOwnerPid > 0 && replacementOwnerPid > 0 &&
                    replacementOwnerPid != previousOwnerPid && statsOwnerToken == ownerToken &&
                    ownerToken != null && ownerToken.isBinderAlive();
            boolean accepted = false;
            if (identityValid && code == FrameIpcProtocol.FRAME_LAB_PREPARE_OWNER_PID_REBIND) {
                accepted = !ownerPidRebindPrepared && statsOwnerPid == previousOwnerPid;
                if (accepted) {
                    ownerPidRebindPrepared = true;
                    statsOwnerPidQueriesBlocked = true;
                    statsOwnerPid = replacementOwnerPid;
                    pendingPreviousOwnerPid = previousOwnerPid;
                    pendingReplacementOwnerPid = replacementOwnerPid;
                    pendingOwnerPidRebindToken = ownerToken;
                }
            } else if (identityValid && ownerPidRebindPrepared &&
                    pendingPreviousOwnerPid == previousOwnerPid &&
                    pendingReplacementOwnerPid == replacementOwnerPid &&
                    pendingOwnerPidRebindToken == ownerToken) {
                if (code == FrameIpcProtocol.FRAME_LAB_COMPLETE_OWNER_PID_REBIND &&
                        statsOwnerPid == replacementOwnerPid) {
                    ownerPidRebindPrepared = false;
                    statsOwnerPidQueriesBlocked = false;
                    pendingPreviousOwnerPid = 0;
                    pendingReplacementOwnerPid = 0;
                    pendingOwnerPidRebindToken = null;
                    accepted = true;
                } else if (code == FrameIpcProtocol.FRAME_LAB_CANCEL_OWNER_PID_REBIND &&
                        (statsOwnerPid == previousOwnerPid || statsOwnerPid == replacementOwnerPid)) {
                    statsOwnerPid = previousOwnerPid;
                    ownerPidRebindPrepared = false;
                    statsOwnerPidQueriesBlocked = false;
                    pendingPreviousOwnerPid = 0;
                    pendingReplacementOwnerPid = 0;
                    pendingOwnerPidRebindToken = null;
                    accepted = true;
                }
            }
            reply.writeNoException();
            reply.writeInt(accepted ? 1 : 0);
            return true;
        }
        if (code != FrameIpcProtocol.VIEW_FRAME && code != FrameIpcProtocol.VIEW_WARNING &&
                code != FrameIpcProtocol.VIEW_CHANGE_GENERATION)
            return super.onTransact(code, data, reply, flags);
        if (!isBoundCompositorCaller()) {
            android.util.Log.w("ClarityLinkCLIMP03", "TYPE110_LAB_SINK_MUTATION_REJECTED code=" +
                    code + " caller_pid=" + Binder.getCallingPid() + " owner_pid=" + compositorPid);
            reply.writeException(new SecurityException("compositor-bound lab output caller required"));
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

    private void clearIdentityAndCompositorEpoch() {
        IBinder oldCompositor = compositorEpoch;
        IBinder.DeathRecipient oldRecipient = compositorDeathRecipient;
        identity = null;
        compositorEpoch = null;
        compositorDeathRecipient = null;
        compositorPid = 0;
        statsOwnerPid = 0;
        ownerPidRebindPrepared = false;
        statsOwnerPidQueriesBlocked = false;
        pendingPreviousOwnerPid = 0;
        pendingReplacementOwnerPid = 0;
        pendingOwnerPidRebindToken = null;
        IBinder oldOwnerToken = statsOwnerToken;
        IBinder.DeathRecipient oldOwnerRecipient = statsOwnerDeathRecipient;
        statsOwnerToken = null;
        statsOwnerDeathRecipient = null;
        if (oldOwnerToken != null && oldOwnerRecipient != null) {
            try { oldOwnerToken.unlinkToDeath(oldOwnerRecipient, 0); }
            catch (RuntimeException ignored) { }
        }
        if (oldCompositor != null && oldRecipient != null) {
            try { oldCompositor.unlinkToDeath(oldRecipient, 0); }
            catch (RuntimeException ignored) { }
        }
    }

    private boolean isBoundCompositorCaller() {
        IBinder epoch = compositorEpoch;
        return Binder.getCallingUid() == Process.myUid() && compositorPid > 0 &&
                Binder.getCallingPid() == compositorPid && epoch != null && epoch.isBinderAlive();
    }

    private boolean isCompositorProcessCaller() {
        int callerPid = Binder.getCallingPid();
        if (callerPid <= 0 || Binder.getCallingUid() != Process.myUid()) return false;
        ActivityManager manager = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
        if (manager == null) return false;
        java.util.List<ActivityManager.RunningAppProcessInfo> processes = manager.getRunningAppProcesses();
        if (processes == null) return false;
        String expected = context.getPackageName() + ":compositor";
        for (ActivityManager.RunningAppProcessInfo process : processes)
            if (process.pid == callerPid && process.uid == Process.myUid())
                return expected.equals(process.processName);
        return false;
    }

    private static FrameStreamIdentity readIdentity(Parcel data) {
        return new FrameStreamIdentity(data.readLong(), data.readInt(), data.readLong(),
                data.readLong(), data.readInt());
    }

    private static void writeIdentity(Parcel data, FrameStreamIdentity identity) {
        data.writeLong(identity.sessionId); data.writeInt(identity.streamType);
        data.writeLong(identity.connectionId); data.writeLong(identity.streamGeneration);
        data.writeInt(identity.outputId);
    }

    private static void closeQuietly(ParcelFileDescriptor value) {
        if (value != null) try { value.close(); } catch (IOException ignored) { }
    }
}
