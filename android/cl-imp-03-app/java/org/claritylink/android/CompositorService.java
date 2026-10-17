package org.claritylink.android;

import android.app.Service;
import android.content.ComponentName;
import android.content.Intent;
import android.os.Binder;
import android.os.IBinder;
import android.os.Parcel;
import android.os.ParcelFileDescriptor;
import android.os.Process;
import android.os.RemoteException;
import android.util.Log;

import org.claritylink.renderer.SimulatedExternalDisplayCompositor;

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.zip.CRC32;

/** Private second-process compositor endpoint for the emulator lab only. */
public final class CompositorService extends Service {
    private static final String TAG = "ClarityLinkCLIMP03";
    private static final int MAX_CLOSED_SESSION_IDS = 128;
    private final Object streamsLock = new Object();
    private final Map<String, StreamState> streams = new HashMap<String, StreamState>();
    private final Map<Long, Type111ControlPlane> type111Sessions = new HashMap<Long, Type111ControlPlane>();
    /** Session IDs are single-use; delayed Binder requests cannot revive a closed session. */
    private final java.util.HashSet<Long> closingSessions = new java.util.HashSet<Long>();
    /** At most 128 identities are admitted during this service lifetime; this bounds tombstones. */
    private final java.util.HashSet<Long> usedSessionIds = new java.util.HashSet<Long>();
    private final AtomicInteger activePfdTransfers = new AtomicInteger();
    private final AtomicInteger retainedFrameBytes = new AtomicInteger();
    private final Object labTransferBarrierLock = new Object();
    private FrameStreamIdentity labTransferBarrierIdentity;
    private CountDownLatch labTransferEntered = new CountDownLatch(0);
    private CountDownLatch labTransferRelease = new CountDownLatch(0);
    private CountDownLatch labTransferFinished = new CountDownLatch(0);
    private final AtomicBoolean labTransferBarrierArmed = new AtomicBoolean(false);
    private static final class StreamState {
        final Object lock = new Object();
        final SimulatedExternalDisplayCompositor compositor = new SimulatedExternalDisplayCompositor();
        final AtomicBoolean transferActive = new AtomicBoolean(false);
        final AtomicInteger activePfdTransfers = new AtomicInteger();
        final AtomicInteger retainedFrameBytes = new AtomicInteger();
        FrameStreamIdentity identity;
        IBinder sink;
        IBinder.DeathRecipient deathRecipient;
        volatile long lastFrameId;
        StreamState(FrameStreamIdentity identity, IBinder sink) {
            this.identity = identity;
            this.sink = sink;
        }
    }
    private static final class ReplacementDeathGate {
        boolean dead;
    }
    private final IBinder endpoint = new Binder() {
        @Override protected boolean onTransact(int code, Parcel data, Parcel reply, int flags)
                throws RemoteException {
            if (Binder.getCallingUid() != Process.myUid()) {
                reply.writeException(new SecurityException("private compositor caller rejected"));
                return true;
            }
            data.enforceInterface(FrameIpcProtocol.DESCRIPTOR);
            int version = data.readInt();
            if (version != FrameIpcProtocol.VERSION) {
                reply.writeException(new IllegalArgumentException("unsupported IPC version"));
                return true;
            }
            if (code == FrameIpcProtocol.LAB_ARM_TRANSFER_BARRIER) {
                FrameStreamIdentity identity = readIdentity(data);
                StreamState state = findStream(identity);
                boolean accepted = state != null && identity.streamType == FrameStreamIdentity.TYPE111 &&
                        identity.equals(state.identity) && !state.transferActive.get();
                if (accepted) synchronized (labTransferBarrierLock) {
                    labTransferBarrierIdentity = identity;
                    labTransferEntered = new CountDownLatch(1);
                    labTransferRelease = new CountDownLatch(1);
                    labTransferFinished = new CountDownLatch(1);
                    labTransferBarrierArmed.set(true);
                }
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                return true;
            }
            if (code == FrameIpcProtocol.LAB_WAIT_TRANSFER_BARRIER ||
                    code == FrameIpcProtocol.LAB_RELEASE_TRANSFER_BARRIER ||
                    code == FrameIpcProtocol.LAB_WAIT_TRANSFER_FINISHED) {
                FrameStreamIdentity identity = readIdentity(data);
                long timeoutMs = code == FrameIpcProtocol.LAB_RELEASE_TRANSFER_BARRIER ?
                        0L : data.readLong();
                if (timeoutMs < 0L || timeoutMs > 10000L) {
                    reply.writeException(new IllegalArgumentException("lab barrier timeout out of range"));
                    return true;
                }
                CountDownLatch latch;
                synchronized (labTransferBarrierLock) {
                    if (!identity.equals(labTransferBarrierIdentity)) {
                        reply.writeNoException();
                        reply.writeInt(0);
                        return true;
                    }
                    if (code == FrameIpcProtocol.LAB_RELEASE_TRANSFER_BARRIER) {
                        labTransferRelease.countDown();
                        reply.writeNoException();
                        reply.writeInt(1);
                        return true;
                    }
                    latch = code == FrameIpcProtocol.LAB_WAIT_TRANSFER_BARRIER ?
                            labTransferEntered : labTransferFinished;
                }
                boolean completed;
                try { completed = latch.await(timeoutMs, TimeUnit.MILLISECONDS); }
                catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    completed = false;
                }
                reply.writeNoException();
                reply.writeInt(completed ? 1 : 0);
                return true;
            }
            if (code == FrameIpcProtocol.FRAME_LAB_QUERY_STATS) {
                FrameStreamIdentity identity = readIdentity(data);
                StreamState state = findStream(identity);
                boolean matches = state != null && identity.equals(state.identity);
                reply.writeNoException();
                reply.writeInt(matches ? 1 : 0);
                reply.writeInt(matches ? state.activePfdTransfers.get() : 0);
                reply.writeInt(matches ? state.retainedFrameBytes.get() : 0);
                reply.writeInt(matches && state.transferActive.get() ? 1 : 0);
                reply.writeLong(matches ? state.lastFrameId : 0L);
                return true;
            }
            if (code == FrameIpcProtocol.BEGIN) {
                FrameStreamIdentity identity = readIdentity(data);
                final IBinder requestedSink = data.readStrongBinder();
                boolean accepted = registerStream(identity, requestedSink);
                Log.i(TAG, "IPC_REMOTE_BEGIN pid=" + Process.myPid() + " generation=" +
                        identity.streamGeneration + " session_id=" + identity.sessionId +
                        " stream_type=" + identity.streamType + " connection_id=" +
                        identity.connectionId + " output_id=" + identity.outputId + " accepted=" + accepted);
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                reply.writeInt(Process.myPid());
                return true;
            }
            if (code == FrameIpcProtocol.END) {
                FrameStreamIdentity identity = readIdentity(data);
                boolean accepted = unregisterStream(identity);
                Log.i(TAG, "IPC_REMOTE_END generation=" + identity.streamGeneration +
                        " stream_type=" + identity.streamType + " accepted=" + accepted);
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                return true;
            }
            if (code == FrameIpcProtocol.TYPE111_REPLACE_SINK) {
                FrameStreamIdentity ownerIdentity = readIdentity(data);
                FrameStreamIdentity oldIdentity = readIdentity(data);
                FrameStreamIdentity newIdentity = readIdentity(data);
                IBinder newSink = data.readStrongBinder();
                boolean accepted = replaceType111Sink(ownerIdentity, oldIdentity, newIdentity, newSink);
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                return true;
            }
            if (code == FrameIpcProtocol.CHANGE_GENERATION) {
                FrameStreamIdentity identity = readIdentity(data);
                long newGeneration = data.readLong();
                StreamState state = findStream(identity);
                boolean accepted = false;
                if (state != null) synchronized (state.lock) {
                    Type111ControlPlane plane = identity.streamType == FrameStreamIdentity.TYPE111 ?
                            controlPlane(identity.sessionId) : null;
                    boolean eligible = identity.equals(state.identity) && newGeneration > identity.streamGeneration &&
                            !state.transferActive.get() &&
                            (identity.streamType != FrameStreamIdentity.TYPE111 ||
                            (plane != null && plane.canTransportGeneration(identity,
                                    identity.withGeneration(newGeneration))));
                    boolean sinkAccepted = eligible && forwardGenerationChange(state.sink,
                            identity, newGeneration);
                    accepted = sinkAccepted && state.compositor.replaceGeneration(
                            identity.streamGeneration, newGeneration);
                    if (accepted && identity.streamType == FrameStreamIdentity.TYPE111)
                        accepted = plane != null && "accepted".equals(plane.transportGeneration(
                                identity, identity.withGeneration(newGeneration)));
                    if (accepted) {
                        state.identity = identity.withGeneration(newGeneration);
                        state.lastFrameId = 0L;
                    }
                }
                Log.i(TAG, "IPC_REMOTE_GENERATION_REPLACED old=" + identity.streamGeneration +
                        " new=" + newGeneration + " stream_type=" + identity.streamType +
                        " accepted=" + accepted +
                        " binder_session_preserved=true");
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                return true;
            }
            if (code == FrameIpcProtocol.WARNING) {
                FrameStreamIdentity identity = readIdentity(data);
                boolean visible = data.readInt() != 0;
                StreamState state = findStream(identity);
                boolean accepted = false;
                if (state != null) synchronized (state.lock) {
                    boolean stateAccepted = identity.equals(state.identity) &&
                            state.compositor.setWarningVisible(identity.streamGeneration, visible);
                    boolean sinkAccepted = stateAccepted && forwardWarningToViewSink(
                            state.sink, identity, visible);
                    if (!visible && stateAccepted && !sinkAccepted)
                        state.compositor.setWarningVisible(identity.streamGeneration, true);
                    accepted = stateAccepted && sinkAccepted;
                }
                Log.i(TAG, "IPC_REMOTE_WARNING generation=" + identity.streamGeneration +
                        " stream_type=" + identity.streamType + " visible=" + visible
                        + " accepted=" + accepted);
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                return true;
            }
            if (code == FrameIpcProtocol.TYPE111_CAPABILITY) {
                handleType111Capability(data, reply);
                return true;
            }
            if (code == FrameIpcProtocol.TYPE111_SETUP) {
                FrameStreamIdentity identity = readIdentity(data);
                Type111ControlPlane plane;
                boolean closing;
                synchronized (streamsLock) {
                    plane = type111Sessions.get(identity.sessionId);
                    closing = closingSessions.contains(identity.sessionId);
                }
                String reason = closing ? "session_closing" :
                        plane == null ? "session_unavailable" : plane.setup(identity);
                writeControlReply(reply, reason);
                Log.i(TAG, "TYPE111_CONTROL_SETUP session_id=" + identity.sessionId +
                        " connection_id=" + identity.connectionId + " result=" + reason);
                return true;
            }
            if (code == FrameIpcProtocol.TYPE111_NAVIGATION) {
                FrameStreamIdentity identity = readIdentity(data);
                String provider = data.readString();
                boolean active = data.readInt() != 0;
                boolean instruction = data.readInt() != 0;
                Type111ControlPlane plane = controlPlane(identity.sessionId);
                String reason = plane == null ? "session_unavailable" :
                        plane.navigation(identity, provider, active, instruction);
                writeControlReply(reply, reason);
                if (plane != null) logControlSnapshot("NAVIGATION", plane);
                return true;
            }
            if (code == FrameIpcProtocol.TYPE111_PRESENTATION) {
                FrameStreamIdentity identity = readIdentity(data);
                String command = data.readString();
                String context = data.readString();
                Type111ControlPlane plane = controlPlane(identity.sessionId);
                String reason = plane == null ? "session_unavailable" :
                        plane.presentation(identity, command, context);
                writeControlReply(reply, reason);
                if (plane != null) logControlSnapshot(command, plane);
                return true;
            }
            if (code == FrameIpcProtocol.TYPE111_GEOMETRY) {
                FrameStreamIdentity identity = readIdentity(data);
                boolean safe = data.readInt() != 0;
                int[] area = new int[] { data.readInt(), data.readInt(), data.readInt(), data.readInt() };
                Type111ControlPlane plane = controlPlane(identity.sessionId);
                String reason = plane == null ? "session_unavailable" : plane.geometry(identity, area, safe);
                writeControlReply(reply, reason);
                if (plane != null) logControlSnapshot(safe ? "SafeArea" : "ViewArea", plane);
                return true;
            }
            if (code == FrameIpcProtocol.TYPE111_VIDEO_CONFIG) {
                FrameStreamIdentity identity = readIdentity(data);
                int width = data.readInt(), height = data.readInt();
                Type111ControlPlane plane = controlPlane(identity.sessionId);
                String reason = plane == null ? "session_unavailable" :
                        plane.videoConfig(identity, width, height);
                reply.writeNoException();
                reply.writeInt("accepted".equals(reason) ? 1 : 0);
                reply.writeString(reason);
                reply.writeLong(plane == null ? 0L : plane.snapshot().decoderGeneration);
                Log.i(TAG, "TYPE111_VIDEO_CONFIG session_id=" + identity.sessionId +
                        " width=" + width + " height=" + height + " decoder_generation=" +
                        (plane == null ? 0L : plane.snapshot().decoderGeneration) + " result=" + reason);
                return true;
            }
            if (code == FrameIpcProtocol.TYPE111_PARENT_TEARDOWN) {
                String reason = teardownType111Session(readIdentity(data));
                writeControlReply(reply, reason);
                return true;
            }
            if (code == FrameIpcProtocol.FRAME) {
                receiveFrame(readIdentity(data), data, reply);
                return true;
            }
            return super.onTransact(code, data, reply, flags);
        }
    };

    @Override public void onCreate() {
        super.onCreate();
        Log.i(TAG, "IPC_REMOTE_PROCESS_READY pid=" + Process.myPid());
    }

    @Override public IBinder onBind(Intent intent) { return endpoint; }

    private Type111ControlPlane controlPlane(long sessionId) {
        synchronized (streamsLock) { return type111Sessions.get(sessionId); }
    }

    private void handleType111Capability(Parcel data, Parcel reply) {
        long sessionId = data.readLong();
        String uuid = data.readString();
        int width = data.readInt(), height = data.readInt(), fps = data.readInt();
        int count = data.readInt();
        String reason = "invalid_type111_capability";
        if (count > 0 && count <= 2) {
            java.util.HashSet<String> contexts = new java.util.HashSet<String>();
            for (int i = 0; i < count; i++) contexts.add(data.readString());
            Type111ControlPlane plane = new Type111ControlPlane(sessionId);
            try {
                reason = plane.registerCapability(new Type111ControlPlane.Capability(
                        sessionId, uuid, width, height, fps, contexts));
                if ("accepted".equals(reason)) synchronized (streamsLock) {
                    if (closingSessions.contains(sessionId) || usedSessionIds.contains(sessionId)) {
                        plane.parentTeardown();
                        reason = "session_id_closed";
                    } else if (usedSessionIds.size() >= MAX_CLOSED_SESSION_IDS) {
                        plane.parentTeardown();
                        reason = "session_capacity_exhausted";
                    } else if (type111Sessions.containsKey(sessionId)) {
                        plane.parentTeardown();
                        reason = "duplicate_session_capability";
                    } else {
                        type111Sessions.put(sessionId, plane);
                        usedSessionIds.add(sessionId);
                    }
                }
            } catch (IllegalArgumentException invalid) { reason = "invalid_type111_capability"; }
        } else {
            for (int i = 0; i < Math.min(Math.max(count, 0), 16); i++) data.readString();
        }
        writeControlReply(reply, reason);
        Log.i(TAG, "TYPE111_CAPABILITY session_id=" + sessionId + " display_uuid=" + uuid +
                " logical_size=" + width + "x" + height + " max_fps=" + fps + " result=" + reason +
                " authority=synthetic_lab_only");
    }

    private String teardownType111Session(FrameStreamIdentity type110Owner) {
        if (type110Owner == null || !type110Owner.isValid() ||
                type110Owner.streamType != FrameStreamIdentity.TYPE110)
            return "session_owner_identity_rejected";
        long sessionId = type110Owner.sessionId;
        synchronized (streamsLock) {
            StreamState owner = streams.get(type110Owner.key());
            if (owner == null || !type110Owner.equals(owner.identity))
                return "session_owner_stream_unregistered";
            if (!type111Sessions.containsKey(sessionId) || closingSessions.contains(sessionId))
                return "session_unavailable";
            // Close admission before taking the child snapshot. Registrations inserted before
            // this point are captured below; later registrations fail under this same lock.
            closingSessions.add(sessionId);
        }
        Type111ControlPlane plane = controlPlane(sessionId);
        if (plane == null) return "session_unavailable";
        ArrayList<FrameStreamIdentity> owned = new ArrayList<FrameStreamIdentity>();
        synchronized (streamsLock) {
            for (StreamState state : streams.values())
                if (state.identity.sessionId == sessionId) owned.add(state.identity);
        }
        for (FrameStreamIdentity identity : owned) unregisterStream(identity);
        plane.parentTeardown();
        synchronized (streamsLock) { type111Sessions.remove(sessionId); }
        Log.i(TAG, "TYPE111_PARENT_TEARDOWN session_id=" + sessionId +
                " streams_closed=" + owned.size() + " result=accepted");
        return "accepted";
    }

    private static void writeControlReply(Parcel reply, String reason) {
        reply.writeNoException();
        reply.writeInt("accepted".equals(reason) ? 1 : 0);
        reply.writeString(reason);
    }

    private static void logControlSnapshot(String event, Type111ControlPlane plane) {
        Type111ControlPlane.Snapshot s = plane.snapshot();
        Log.i(TAG, "TYPE111_CONTROL_" + event + " session_id=" + s.sessionId +
                " state=" + s.state + " connection_id=" + s.connectionId +
                " transport_generation=" + s.transportGeneration +
                " decoder_generation=" + s.decoderGeneration +
                " presentation_generation=" + s.presentationGeneration +
                " visible=" + s.visible + " context=" + s.selectedContext +
                " suggestion=" + s.suggestion + " video=" + s.width + "x" + s.height);
    }

    @Override public void onDestroy() {
        ArrayList<StreamState> active;
        synchronized (streamsLock) { active = new ArrayList<StreamState>(streams.values()); }
        for (StreamState state : active) unregisterStream(state.identity);
        synchronized (streamsLock) {
            for (Type111ControlPlane plane : type111Sessions.values()) plane.parentTeardown();
            type111Sessions.clear();
        }
        Log.i(TAG, "IPC_REMOTE_PROCESS_DESTROYED resources_cleared=" + streams.isEmpty() +
                " active_pfd_transfers=" + activePfdTransfers.get() +
                " retained_frame_bytes=" + retainedFrameBytes.get());
        super.onDestroy();
    }

    private void receiveFrame(FrameStreamIdentity identity, Parcel data, Parcel reply) {
        long frameId = data.readLong();
        long timestampNs = data.readLong();
        int width = data.readInt();
        int height = data.readInt();
        int rowStride = data.readInt();
        int pixelFormat = data.readInt();
        int rotation = data.readInt();
        int cropLeft = data.readInt();
        int cropTop = data.readInt();
        int cropRight = data.readInt();
        int cropBottom = data.readInt();
        final int payloadBytes = data.readInt();
        ParcelFileDescriptor descriptor = data.readParcelable(
                ParcelFileDescriptor.class.getClassLoader());
        final StreamState state = findStream(identity);
        if (state == null || !state.transferActive.compareAndSet(false, true)) {
            closeQuietly(descriptor);
            reply.writeNoException();
            reply.writeInt(0);
            reply.writeString(state == null ? "stream_identity_rejected" : "frame_dispatch_queue_full");
            return;
        }
        try { synchronized (state.lock) {
        final boolean trackedPfd = descriptor != null;
        if (trackedPfd) {
            activePfdTransfers.incrementAndGet();
            state.activePfdTransfers.incrementAndGet();
        }
        if (trackedPfd) pauseAtLabTransferBarrier(identity);
        byte[] payload = null;
        String rejection = "frame_contract_rejected";
        boolean contractValid = descriptor != null && identity.equals(state.identity) &&
                !state.compositor.warningVisible() &&
                timestampNs > state.compositor.lastTimestampNs() &&
                pixelFormat == FrameIpcProtocol.PIXEL_FORMAT_RGBA_8888 &&
                payloadBytes == FrameIpcProtocol.expectedRgbaBytes(width, height, rowStride) &&
                frameId > state.lastFrameId && timestampNs >= 0 &&
                identity.streamGeneration == state.compositor.activeGeneration() && state.sink != null &&
                (rotation == 0 || rotation == 90 || rotation == 180 || rotation == 270) &&
                cropLeft >= 0 && cropTop >= 0 && cropRight <= width && cropBottom <= height &&
                cropLeft < cropRight && cropTop < cropBottom;
        try {
            if (contractValid) {
                payload = readBoundedPayload(descriptor, payloadBytes);
                descriptor = null;
                if (payload == null) rejection = "frame_payload_length_rejected";
            } else if (descriptor != null) {
                descriptor.close();
                descriptor = null;
            }
        } catch (IOException failure) {
            rejection = "frame_payload_io_rejected";
            Log.i(TAG, "IPC_REMOTE_FRAME_IO_REJECT type=" + failure.getClass().getSimpleName());
        } catch (OutOfMemoryError exhausted) {
            Log.i(TAG, "IPC_REMOTE_FRAME_ALLOCATION_REJECT bounded_bytes=" + payloadBytes);
        } finally {
            if (descriptor != null) try { descriptor.close(); } catch (IOException ignored) { }
            if (trackedPfd) {
                activePfdTransfers.decrementAndGet();
                state.activePfdTransfers.decrementAndGet();
            }
        }
        long checksum = -1L;
        boolean accepted = false;
        if (payload != null) {
            retainedFrameBytes.addAndGet(payload.length);
            state.retainedFrameBytes.addAndGet(payload.length);
        }
        try {
        if (payload != null && payload.length == payloadBytes) {
            CRC32 crc = new CRC32();
            crc.update(payload);
            checksum = crc.getValue();
            String[] downstreamFailure = new String[1];
            accepted = forwardToViewSink(state, identity, frameId, timestampNs, width,
                    height, rowStride, pixelFormat, rotation, cropLeft, cropTop,
                    cropRight, cropBottom, payload, checksum, downstreamFailure) &&
                    state.compositor.accept(identity.streamGeneration, timestampNs, width, height, rowStride, payloadBytes);
            if (accepted) state.lastFrameId = frameId;
            else rejection = downstreamFailure[0] == null ? "frame_downstream_rejected" : downstreamFailure[0];
        }
        Log.i(TAG, "IPC_REMOTE_FRAME generation=" + identity.streamGeneration +
                " session_id=" + identity.sessionId + " stream_type=" + identity.streamType +
                " connection_id=" + identity.connectionId + " output_id=" + identity.outputId +
                " timestamp=" + timestampNs
                + " bytes=" + payloadBytes + " accepted=" + accepted
                + " downstream=view_sink frame_id=" + frameId + " format=" + pixelFormat +
                " bounded=true retained_frame_bytes=" + state.retainedFrameBytes.get() +
                " stream_active_pfds=" + state.activePfdTransfers.get());
        if (!accepted) Log.i(TAG, "IPC_REMOTE_FRAME_REJECT generation=" + identity.streamGeneration +
                " frame_id=" + frameId + " reason=" + rejection +
                " active_pfd_transfers=" + activePfdTransfers.get());
        reply.writeNoException();
        reply.writeInt(accepted ? 1 : 0);
        reply.writeString(accepted ? "accepted" : rejection);
        } finally {
            if (payload != null) {
                retainedFrameBytes.addAndGet(-payload.length);
                state.retainedFrameBytes.addAndGet(-payload.length);
            }
        }
        }} finally {
            state.transferActive.set(false);
            synchronized (labTransferBarrierLock) {
                if (identity.equals(labTransferBarrierIdentity) && !labTransferBarrierArmed.get())
                    labTransferFinished.countDown();
            }
        }
    }

    private boolean registerStream(final FrameStreamIdentity identity, final IBinder sink) {
        if (identity == null || !identity.isValid() || sink == null || !sink.isBinderAlive()) return false;
        final Type111ControlPlane control = identity.streamType == FrameStreamIdentity.TYPE111 ?
                controlPlane(identity.sessionId) : null;
        if (identity.streamType == FrameStreamIdentity.TYPE111 &&
                (control == null || !"accepted".equals(control.activate(identity)))) return false;
        final StreamState state = new StreamState(identity, sink);
        if (!state.compositor.begin(identity.streamGeneration)) {
            if (control != null) control.teardown(identity);
            return false;
        }
        state.deathRecipient = createSinkDeathRecipient(state, identity, sink, null);
        // Link before publication. If teardown wins the streamsLock race, registration rolls
        // back; if publication wins, teardown sees a state whose recipient is already linked.
        try {
            sink.linkToDeath(state.deathRecipient, 0);
        } catch (RemoteException deadSink) {
            state.compositor.end(identity.streamGeneration);
            if (control != null) control.teardown(identity);
            return false;
        }
        boolean registered = false;
        synchronized (streamsLock) {
            boolean validOwner = identity.streamType != FrameStreamIdentity.TYPE111 ||
                    type111Sessions.get(identity.sessionId) == control;
            if (!streams.containsKey(identity.key()) && validOwner &&
                    !closingSessions.contains(identity.sessionId) && sink.isBinderAlive()) {
                int sessionStreams = 0;
                boolean conflict = false;
                for (StreamState current : streams.values()) {
                    if (current.identity.sessionId == identity.sessionId) {
                        sessionStreams++;
                        if (current.identity.streamType == identity.streamType ||
                                current.identity.connectionId == identity.connectionId ||
                                current.identity.outputId == identity.outputId) {
                            conflict = true;
                            break;
                        }
                    }
                }
                if (!conflict && sessionStreams < 2) {
                    streams.put(identity.key(), state);
                    registered = true;
                }
            }
        }
        if (!registered) {
            try { sink.unlinkToDeath(state.deathRecipient, 0); }
            catch (RuntimeException ignored) { }
            state.compositor.end(identity.streamGeneration);
            if (control != null) control.teardown(identity);
            return false;
        }
        Log.i(TAG, "IPC_STREAM_REGISTERED session_id=" + identity.sessionId +
                " stream_type=" + identity.streamType + " connection_id=" + identity.connectionId +
                " stream_generation=" + identity.streamGeneration + " output_id=" + identity.outputId);
        return true;
    }

    private IBinder.DeathRecipient createSinkDeathRecipient(final StreamState state,
            final FrameStreamIdentity registeredIdentity, final IBinder registeredSink,
            final ReplacementDeathGate deathGate) {
        return new IBinder.DeathRecipient() {
            public void binderDied() {
                if (deathGate != null) synchronized (deathGate) { deathGate.dead = true; }
                final FrameStreamIdentity deadIdentity;
                synchronized (state.lock) {
                    deadIdentity = state.sink == registeredSink ? state.identity : registeredIdentity;
                    if (state.sink != registeredSink) return;
                }
                Log.i(TAG, "IPC_VIEW_SINK_DEATH_CALLBACK session_id=" + deadIdentity.sessionId +
                        " stream_type=" + deadIdentity.streamType + " connection_id=" +
                        deadIdentity.connectionId + " stream_generation=" + deadIdentity.streamGeneration);
                if (deadIdentity.streamType == FrameStreamIdentity.TYPE111)
                    detachType111SinkIfCurrent(state, deadIdentity);
                else unregisterStreamIfCurrent(state, deadIdentity);
                if (deadIdentity.streamType == FrameStreamIdentity.TYPE111 &&
                        Type110LabProbeOwnership.hasPending(CompositorService.this, deadIdentity)) {
                    try {
                        Intent recovery = new Intent(CompositorService.this,
                                Type110ProgressProbeService.class);
                        Type110LabProbeOwnership.putExpectedDeath(recovery, deadIdentity);
                        ComponentName started = startService(recovery);
                        Log.i(TAG, "TYPE110_POST_DEATH_PROBE_INTERNAL_START session_id=" +
                                deadIdentity.sessionId + " started=" + (started != null) +
                                " after_type111_binder_death=true");
                    } catch (RuntimeException failure) {
                        Log.e(TAG, "TYPE110_POST_DEATH_PROBE_INTERNAL_START_FAILED session_id=" +
                                deadIdentity.sessionId + " type=" + failure.getClass().getSimpleName());
                    }
                }
            }
        };
    }

    /** Preserve the Type111 stream/control identity after only its View Binder disappears. */
    private boolean detachType111SinkIfCurrent(StreamState state, FrameStreamIdentity identity) {
        synchronized (state.lock) {
            synchronized (streamsLock) {
                if (streams.get(identity.key()) != state || !identity.equals(state.identity) ||
                        identity.streamType != FrameStreamIdentity.TYPE111) return false;
                state.sink = null;
                state.deathRecipient = null;
            }
        }
        Log.i(TAG, "IPC_TYPE111_SINK_DETACHED session_id=" + identity.sessionId +
                " connection_id=" + identity.connectionId + " generation=" +
                identity.streamGeneration + " parent_session_preserved=true");
        return true;
    }

    private boolean replaceType111Sink(FrameStreamIdentity ownerIdentity,
            FrameStreamIdentity oldIdentity, FrameStreamIdentity newIdentity, IBinder newSink) {
        if (ownerIdentity == null || !ownerIdentity.isValid() ||
                ownerIdentity.streamType != FrameStreamIdentity.TYPE110 || oldIdentity == null ||
                !oldIdentity.isValid() || oldIdentity.streamType != FrameStreamIdentity.TYPE111 ||
                newIdentity == null || !newIdentity.isValid() || !oldIdentity.sameStream(newIdentity) ||
                oldIdentity.sessionId != ownerIdentity.sessionId ||
                newIdentity.streamGeneration != oldIdentity.streamGeneration + 1L ||
                newIdentity.streamGeneration <= oldIdentity.streamGeneration || newSink == null ||
                !newSink.isBinderAlive()) return false;
        final StreamState state = findStream(oldIdentity);
        final Type111ControlPlane plane = controlPlane(oldIdentity.sessionId);
        if (state == null || plane == null || !plane.canTransportGeneration(oldIdentity, newIdentity))
            return false;
        synchronized (streamsLock) {
            StreamState owner = streams.get(ownerIdentity.key());
            if (owner == null || !ownerIdentity.equals(owner.identity) ||
                    closingSessions.contains(oldIdentity.sessionId)) return false;
        }
        final ReplacementDeathGate deathGate = new ReplacementDeathGate();
        final IBinder.DeathRecipient newRecipient = createSinkDeathRecipient(
                state, newIdentity, newSink, deathGate);
        try { newSink.linkToDeath(newRecipient, 0); }
        catch (RemoteException deadSink) { return false; }
        IBinder oldSink = null;
        IBinder.DeathRecipient oldRecipient = null;
        boolean accepted = false;
        synchronized (state.lock) {
            synchronized (deathGate) {
                boolean stillCurrent;
                synchronized (streamsLock) {
                    stillCurrent = streams.get(oldIdentity.key()) == state &&
                            oldIdentity.equals(state.identity) &&
                            !closingSessions.contains(oldIdentity.sessionId);
                }
                if (!deathGate.dead && stillCurrent && !state.transferActive.get() &&
                        newSink.isBinderAlive() && plane.canTransportGeneration(oldIdentity, newIdentity) &&
                        state.compositor.replaceGeneration(oldIdentity.streamGeneration,
                                newIdentity.streamGeneration)) {
                    if ("accepted".equals(plane.transportGeneration(oldIdentity, newIdentity))) {
                        oldSink = state.sink;
                        oldRecipient = state.deathRecipient;
                        state.identity = newIdentity;
                        state.sink = newSink;
                        state.deathRecipient = newRecipient;
                        state.lastFrameId = 0L;
                        accepted = true;
                    } else {
                        // This should be unreachable while state.lock serializes Type111
                        // generation changes. Do not attempt a backwards compositor generation.
                        state.compositor.end(newIdentity.streamGeneration);
                        synchronized (streamsLock) { streams.remove(oldIdentity.key()); }
                        state.sink = null;
                        state.deathRecipient = null;
                    }
                }
            }
        }
        if (!accepted) {
            try { newSink.unlinkToDeath(newRecipient, 0); } catch (RuntimeException ignored) { }
            return false;
        }
        if (oldSink != null && oldRecipient != null)
            try { oldSink.unlinkToDeath(oldRecipient, 0); } catch (RuntimeException ignored) { }
        Log.i(TAG, "IPC_TYPE111_SINK_REPLACED session_id=" + oldIdentity.sessionId +
                " connection_id=" + oldIdentity.connectionId + " old_generation=" +
                oldIdentity.streamGeneration + " new_generation=" + newIdentity.streamGeneration +
                " type110_generation_preserved=" + ownerIdentity.streamGeneration);
        return true;
    }

    private void pauseAtLabTransferBarrier(FrameStreamIdentity identity) {
        CountDownLatch entered;
        CountDownLatch release;
        synchronized (labTransferBarrierLock) {
            if (!identity.equals(labTransferBarrierIdentity) ||
                    !labTransferBarrierArmed.compareAndSet(true, false)) return;
            entered = labTransferEntered;
            release = labTransferRelease;
        }
        entered.countDown();
        Log.i(TAG, "IPC_LAB_TRANSFER_BARRIER_ENTERED session_id=" + identity.sessionId +
                " stream_type=" + identity.streamType + " generation=" + identity.streamGeneration +
                " active_pfd=" + activePfdTransfers.get());
        try {
            if (!release.await(10000L, TimeUnit.MILLISECONDS))
                Log.w(TAG, "IPC_LAB_TRANSFER_BARRIER_TIMEOUT session_id=" + identity.sessionId);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
        }
    }

    private StreamState findStream(FrameStreamIdentity identity) {
        if (identity == null || !identity.isValid()) return null;
        synchronized (streamsLock) { return streams.get(identity.key()); }
    }

    private boolean unregisterStream(FrameStreamIdentity identity) {
        StreamState state = findStream(identity);
        if (state == null) return false;
        return unregisterStreamState(state, identity);
    }

    private boolean unregisterStreamIfCurrent(StreamState expectedState, FrameStreamIdentity identity) {
        return unregisterStreamState(expectedState, identity);
    }

    private boolean unregisterStreamState(StreamState state, FrameStreamIdentity identity) {
        synchronized (state.lock) {
            synchronized (streamsLock) {
                if (streams.get(identity.key()) != state || !identity.equals(state.identity))
                    return false;
                state.compositor.end(state.identity.streamGeneration);
                if (state.sink != null && state.deathRecipient != null) {
                    try { state.sink.unlinkToDeath(state.deathRecipient, 0); }
                    catch (RuntimeException ignored) { }
                }
                state.sink = null;
                streams.remove(identity.key());
            }
        }
        if (identity.streamType == FrameStreamIdentity.TYPE111) {
            Type111ControlPlane control = controlPlane(identity.sessionId);
            if (control != null) control.teardown(identity);
        }
        Log.i(TAG, "IPC_STREAM_UNREGISTERED session_id=" + identity.sessionId +
                " stream_type=" + identity.streamType + " connection_id=" + identity.connectionId +
                " active_pfd_transfers=" + state.activePfdTransfers.get());
        return true;
    }

    private static FrameStreamIdentity readIdentity(Parcel data) {
        return new FrameStreamIdentity(data.readLong(), data.readInt(), data.readLong(),
                data.readLong(), data.readInt());
    }

    private static void writeIdentity(Parcel data, FrameStreamIdentity identity) {
        data.writeLong(identity.sessionId);
        data.writeInt(identity.streamType);
        data.writeLong(identity.connectionId);
        data.writeLong(identity.streamGeneration);
        data.writeInt(identity.outputId);
    }

    private static void closeQuietly(ParcelFileDescriptor descriptor) {
        if (descriptor != null) try { descriptor.close(); } catch (IOException ignored) { }
    }

    private boolean forwardToViewSink(final StreamState state, FrameStreamIdentity identity, long frameId,
            long timestampNs, int width, int height, int rowStride, int pixelFormat,
            int rotation, int cropLeft, int cropTop, int cropRight, int cropBottom,
            byte[] payload, long checksum, String[] failureReason) {
        IBinder sink = state.sink;
        if (sink == null || !sink.isBinderAlive() || payload == null ||
                payload.length > FrameIpcProtocol.MAX_FRAME_BYTES) {
            if (failureReason != null) failureReason[0] = "view_sink_unavailable";
            return false;
        }
        ParcelFileDescriptor[] pipe = null;
        Thread writer = null;
        boolean writerStarted = false;
        try {
            pipe = ParcelFileDescriptor.createPipe();
            activePfdTransfers.incrementAndGet();
            state.activePfdTransfers.incrementAndGet();
            final ParcelFileDescriptor writeEnd = pipe[1];
            final byte[] bytes = payload;
            writer = new Thread(new Runnable() {
                public void run() {
                    FileOutputStream output = null;
                    try {
                        output = new ParcelFileDescriptor.AutoCloseOutputStream(writeEnd);
                        output.write(bytes);
                        output.flush();
                    } catch (IOException ignored) {
                    } finally {
                        if (output != null) try { output.close(); } catch (IOException ignored) { }
                        else try { writeEnd.close(); } catch (IOException ignored) { }
                        activePfdTransfers.decrementAndGet();
                        state.activePfdTransfers.decrementAndGet();
                    }
                }
            }, "ClarityLinkViewSinkPipe");
            writer.start();
            writerStarted = true;
            Parcel data = Parcel.obtain();
            Parcel reply = Parcel.obtain();
            boolean accepted;
            try {
                data.writeInterfaceToken("org.claritylink.android.IClarityLinkViewFrameSink");
                data.writeInt(FrameIpcProtocol.VERSION);
                writeIdentity(data, identity);
                data.writeLong(frameId);
                data.writeLong(timestampNs);
                data.writeInt(width);
                data.writeInt(height);
                data.writeInt(rowStride);
                data.writeInt(pixelFormat);
                data.writeInt(rotation);
                data.writeInt(cropLeft);
                data.writeInt(cropTop);
                data.writeInt(cropRight);
                data.writeInt(cropBottom);
                data.writeInt(payload.length);
                data.writeLong(checksum);
                data.writeParcelable(pipe[0], 0);
                sink.transact(FrameIpcProtocol.VIEW_FRAME, data, reply, 0);
                reply.readException();
                accepted = reply.readInt() != 0;
                String sinkReason = reply.readString();
                if (!accepted && failureReason != null) failureReason[0] = sinkReason;
            } finally { reply.recycle(); data.recycle(); }
            writer.join(5000L);
            return accepted && !writer.isAlive();
        } catch (Exception failure) {
            if (failureReason != null) failureReason[0] = "view_sink_transaction_" +
                    failure.getClass().getSimpleName();
            Log.i(TAG, "IPC_VIEW_SINK_REJECT type=" + failure.getClass().getSimpleName());
            return false;
        } finally {
            if (pipe != null) {
                try { pipe[0].close(); } catch (IOException ignored) { }
                if (!writerStarted) try { pipe[1].close(); } catch (IOException ignored) { }
            }
            if (writer != null && writer.isAlive()) {
                try { writer.join(5000L); } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                }
            }
            if (pipe != null && !writerStarted) {
                activePfdTransfers.decrementAndGet();
                state.activePfdTransfers.decrementAndGet();
            }
        }
    }

    private boolean forwardWarningToViewSink(IBinder sink, FrameStreamIdentity identity, boolean visible) {
        if (sink == null || !sink.isBinderAlive()) return false;
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken("org.claritylink.android.IClarityLinkViewFrameSink");
            data.writeInt(FrameIpcProtocol.VERSION);
            writeIdentity(data, identity);
            data.writeInt(visible ? 1 : 0);
            sink.transact(FrameIpcProtocol.VIEW_WARNING, data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } catch (Exception failure) {
            Log.i(TAG, "IPC_VIEW_WARNING_REJECT type=" + failure.getClass().getSimpleName());
            return false;
        } finally { reply.recycle(); data.recycle(); }
    }

    private boolean forwardGenerationChange(IBinder sink, FrameStreamIdentity identity, long newGeneration) {
        if (sink == null || !sink.isBinderAlive()) return false;
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken("org.claritylink.android.IClarityLinkViewFrameSink");
            data.writeInt(FrameIpcProtocol.VERSION);
            writeIdentity(data, identity);
            data.writeLong(newGeneration);
            sink.transact(FrameIpcProtocol.VIEW_CHANGE_GENERATION, data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } catch (Exception failure) {
            Log.i(TAG, "IPC_VIEW_GENERATION_REJECT type=" + failure.getClass().getSimpleName());
            return false;
        } finally { reply.recycle(); data.recycle(); }
    }

    private static byte[] readBoundedPayload(ParcelFileDescriptor descriptor, int expectedBytes)
            throws IOException {
        if (expectedBytes <= 0 || expectedBytes > FrameIpcProtocol.MAX_FRAME_BYTES) {
            descriptor.close();
            return null;
        }
        FileInputStream input = new ParcelFileDescriptor.AutoCloseInputStream(descriptor);
        try {
            byte[] result = new byte[expectedBytes];
            int offset = 0;
            while (offset < expectedBytes) {
                int count = input.read(result, offset, expectedBytes - offset);
                if (count < 0) return null;
                offset += count;
            }
            return input.read() == -1 ? result : null;
        } finally {
            input.close();
        }
    }
}
