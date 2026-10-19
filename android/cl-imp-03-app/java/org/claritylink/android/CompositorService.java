package org.claritylink.android;

import android.app.Service;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Binder;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Parcel;
import android.os.ParcelFileDescriptor;
import android.os.Process;
import android.os.RemoteException;
import android.util.Log;
import android.content.SharedPreferences;

import org.claritylink.renderer.SimulatedExternalDisplayCompositor;

import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.Callable;
import java.util.concurrent.FutureTask;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.zip.CRC32;

/** Private second-process compositor endpoint for the emulator lab only. */
public final class CompositorService extends Service {
    private static final String TAG = "ClarityLinkCLIMP03";
    private static final int MAX_RECENT_SESSION_IDS = 256;
    // The 32 KiB Bloom filter is intentionally bounded. Stop admitting new IDs before
    // its false-positive rate becomes material; this is a per-app-data lifetime cap.
    private static final int MAX_SESSION_IDS_SINCE_REPLAY_INITIALIZATION = 4096;
    private static final int MAX_ACTIVE_PARENT_SESSIONS = 8;
    private static final long PROVISIONAL_PARENT_AUTHORITY_TIMEOUT_MS = 30000L;
    private static final int SESSION_REPLAY_BLOOM_BYTES = 32768;
    private static final long VIEW_CLOSE_TIMEOUT_MS = 1000L;
    private static final int MAX_VIEW_CLOSE_ATTEMPTS = 3;
    private static final long VIEW_CLOSE_RETRY_DELAY_MS = 100L;
    private static final int MAX_PENDING_VIEW_CLOSES = MAX_ACTIVE_PARENT_SESSIONS * 2;
    private static final String SESSION_REPLAY_BLOOM = "session_replay_bloom_v1";
    private static final String SESSION_REPLAY_ISSUED_COUNT = "session_replay_issued_count_v1";
    private final Object streamsLock = new Object();
    private final Map<String, StreamState> streams = new HashMap<String, StreamState>();
    private final Map<Long, Type111ControlPlane> type111Sessions = new HashMap<Long, Type111ControlPlane>();
    private final Map<Long, ParentAuthority> parentAuthorities = new HashMap<Long, ParentAuthority>();
    private final Map<Long, SinkAdmissionGrant> sinkAdmissionGrants = new HashMap<Long, SinkAdmissionGrant>();
    private final Set<IBinder> pendingViewCloses = Collections.newSetFromMap(
            new IdentityHashMap<IBinder, Boolean>());
    private final ThreadPoolExecutor viewCloseExecutor = new ThreadPoolExecutor(2, 2, 0L,
            TimeUnit.MILLISECONDS, new ArrayBlockingQueue<Runnable>(MAX_PENDING_VIEW_CLOSES - 2),
            new java.util.concurrent.ThreadFactory() {
                private final AtomicInteger sequence = new AtomicInteger();
                @Override public Thread newThread(Runnable task) {
                    Thread worker = new Thread(task, "ClarityLink-view-close-" + sequence.incrementAndGet());
                    worker.setDaemon(true);
                    return worker;
                }
            }, new ThreadPoolExecutor.AbortPolicy());
    /** Sessions currently closing; retired IDs are tracked by the bounded replay window below. */
    private final java.util.HashSet<Long> closingSessions = new java.util.HashSet<Long>();
    /** Parent teardowns remain fenced until every exact child sink close is acknowledged or dead. */
    private final java.util.HashSet<Long> pendingParentTeardowns = new java.util.HashSet<Long>();
    /** Recent session IDs survive compositor death; replay protection retains the latest 256 IDs. */
    private final java.util.HashSet<Long> persistedSessionIds = new java.util.HashSet<Long>();
    /** Unordered IDs from the prior preference schema are retained intact; their age is unknown. */
    private final java.util.HashSet<Long> legacySessionIds = new java.util.HashSet<Long>();
    private final ArrayList<Long> persistedSessionOrder = new ArrayList<Long>();
    /** Fixed-size, no-false-negative replay fence; saturation fails closed through false positives. */
    private byte[] sessionReplayBloom = new byte[SESSION_REPLAY_BLOOM_BYTES];
    private int sessionReplayIssuedCount;
    /** IDs currently reserved by a live session; durable tombstones remain in persistedSessionIds. */
    private final java.util.HashSet<Long> activeSessionIds = new java.util.HashSet<Long>();
    private boolean sessionWindowReady = true;
    private Handler authorityHandler;
    private static final String SESSION_ID_PREFS = "claritylink_lab_session_tombstones_v1";
    private static final String LEGACY_SESSION_ID_SET = "session_ids";
    private static final String SESSION_ID_SET = "session_ids_v2";
    private static final String SESSION_ID_ORDER = "session_id_order_v2";
    private final AtomicInteger activePfdTransfers = new AtomicInteger();
    private final AtomicInteger retainedFrameBytes = new AtomicInteger();
    private final Object labTransferBarrierLock = new Object();
    private FrameStreamIdentity labTransferBarrierIdentity;
    private CountDownLatch labTransferEntered = new CountDownLatch(0);
    private CountDownLatch labTransferRelease = new CountDownLatch(0);
    private CountDownLatch labTransferFinished = new CountDownLatch(0);
    private final AtomicBoolean labTransferBarrierArmed = new AtomicBoolean(false);
    private final Object labParentTeardownBarrierLock = new Object();
    private long labParentTeardownBarrierSessionId;
    private CountDownLatch labParentTeardownEntered = new CountDownLatch(0);
    private CountDownLatch labParentTeardownRelease = new CountDownLatch(0);
    private CountDownLatch labParentTeardownContender = new CountDownLatch(0);
    private final Object labDelayedDeathLock = new Object();
    private FrameStreamIdentity labDelayedDeathIdentity;
    private StreamState labDelayedDeathState;
    private IBinder.DeathRecipient labDelayedDeathRecipient;
    private CountDownLatch labDelayedDeathEntered = new CountDownLatch(0);
    private CountDownLatch labDelayedDeathRelease = new CountDownLatch(0);
    private CountDownLatch labDelayedDeathCompleted = new CountDownLatch(0);
    private static final class StreamState {
        final Object lock = new Object();
        final SimulatedExternalDisplayCompositor compositor = new SimulatedExternalDisplayCompositor();
        final AtomicBoolean transferActive = new AtomicBoolean(false);
        final AtomicInteger activePfdTransfers = new AtomicInteger();
        final AtomicInteger retainedFrameBytes = new AtomicInteger();
        FrameStreamIdentity identity;
        IBinder sink;
        IBinder.DeathRecipient deathRecipient;
        volatile boolean closing;
        volatile long lastFrameId;
        StreamState(FrameStreamIdentity identity, IBinder sink) {
            this.identity = identity;
            this.sink = sink;
        }
    }
    /** Explicit lab parent authority, separate from either stream's registration/activation. */
    private static final class ParentAuthority {
        /** Current Type110 stream identity; generation advances do not change ownerEpoch. */
        FrameStreamIdentity ownerIdentity;
        final IBinder ownerSink;
        final long epoch;
        int ownerPid;
        final String ownerProcess;
        IBinder.DeathRecipient deathRecipient;
        volatile boolean dead;
        boolean provisional = true;
        Runnable provisionalExpiry;
        Type110LabProbeOwnership.Record pendingType110Recovery;
        int authorizedType111ProducerPid;
        FrameStreamIdentity authorizedType111ProducerIdentity;
        ParentAuthority(FrameStreamIdentity ownerIdentity, IBinder ownerSink, long epoch, int ownerPid,
                String ownerProcess) {
            this.ownerIdentity = ownerIdentity;
            this.ownerSink = ownerSink;
            this.epoch = epoch;
            this.ownerPid = ownerPid;
            this.ownerProcess = ownerProcess;
        }
    }
    private final class SinkAdmissionGrant extends Binder {
        final long sessionId;
        final long expiresAtNs;
        final AtomicBoolean consumed = new AtomicBoolean(false);
        SinkAdmissionGrant(long sessionId) {
            this.sessionId = sessionId;
            this.expiresAtNs = android.os.SystemClock.elapsedRealtimeNanos() +
                    TimeUnit.SECONDS.toNanos(30L);
        }
        @Override protected boolean onTransact(int code, Parcel data, Parcel reply, int flags)
                throws RemoteException {
            if (code != FrameIpcProtocol.TYPE110_SINK_ADMISSION_CONSUME) return super.onTransact(code, data, reply, flags);
            data.enforceInterface(FrameIpcProtocol.DESCRIPTOR);
            long requestedSession = data.readLong();
            int callerPid = Binder.getCallingPid();
            boolean sinkProcess = (getPackageName() + ":type110_sink").equals(processNameForPid(callerPid));
            boolean accepted = false;
            synchronized (streamsLock) {
                if (requestedSession == sessionId && sinkProcess &&
                        android.os.SystemClock.elapsedRealtimeNanos() <= expiresAtNs &&
                        sinkAdmissionGrants.get(sessionId) == this && consumed.compareAndSet(false, true)) {
                    sinkAdmissionGrants.remove(sessionId);
                    accepted = true;
                }
            }
            reply.writeNoException(); reply.writeInt(accepted ? 1 : 0);
            Log.i(TAG, "TYPE110_SINK_ADMISSION_CONSUMED session_id=" + sessionId +
                    " caller_pid=" + callerPid + " accepted=" + accepted);
            return true;
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
                if (identity == null || !isSessionOwnerCaller(identity.sessionId)) {
                    reply.writeNoException(); reply.writeInt(0); return true;
                }
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
                boolean ownerMayDrainDuringShutdown =
                        code == FrameIpcProtocol.LAB_RELEASE_TRANSFER_BARRIER ||
                        code == FrameIpcProtocol.LAB_WAIT_TRANSFER_FINISHED;
                if (identity == null || !isSessionOwnerCaller(identity.sessionId,
                        ownerMayDrainDuringShutdown)) {
                    reply.writeNoException(); reply.writeInt(0); return true;
                }
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
            if (code == FrameIpcProtocol.LAB_ARM_PARENT_TEARDOWN_BARRIER) {
                FrameStreamIdentity ownerIdentity = readIdentity(data);
                boolean accepted = ownerIdentity != null &&
                        isSessionOwnerCaller(ownerIdentity.sessionId) &&
                        armParentTeardownBarrier(ownerIdentity);
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                return true;
            }
            if (code == FrameIpcProtocol.LAB_ARM_DELAYED_SINK_DEATH_CALLBACK) {
                FrameStreamIdentity identity = readIdentity(data);
                boolean accepted = identity != null && isSessionOwnerCaller(identity.sessionId) &&
                        armDelayedSinkDeathCallback(identity);
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                return true;
            }
            if (code == FrameIpcProtocol.LAB_FIRE_DELAYED_SINK_DEATH_CALLBACK) {
                FrameStreamIdentity ownerIdentity = readIdentity(data);
                FrameStreamIdentity currentIdentity = readIdentity(data);
                boolean accepted = ownerIdentity != null &&
                        isSessionOwnerCaller(ownerIdentity.sessionId) &&
                        fireDelayedSinkDeathCallback(ownerIdentity, currentIdentity);
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                return true;
            }
            if (code == FrameIpcProtocol.LAB_WAIT_PARENT_TEARDOWN_BARRIER ||
                    code == FrameIpcProtocol.LAB_WAIT_PARENT_TEARDOWN_CONTENDER ||
                    code == FrameIpcProtocol.LAB_RELEASE_PARENT_TEARDOWN_BARRIER) {
                FrameStreamIdentity ownerIdentity = readIdentity(data);
                boolean ownerMayDrainDuringShutdown =
                        code == FrameIpcProtocol.LAB_WAIT_PARENT_TEARDOWN_BARRIER ||
                        code == FrameIpcProtocol.LAB_WAIT_PARENT_TEARDOWN_CONTENDER ||
                        code == FrameIpcProtocol.LAB_RELEASE_PARENT_TEARDOWN_BARRIER;
                if (ownerIdentity == null || !isSessionOwnerCaller(ownerIdentity.sessionId,
                        ownerMayDrainDuringShutdown)) {
                    reply.writeNoException(); reply.writeInt(0); return true;
                }
                long timeoutMs = code == FrameIpcProtocol.LAB_RELEASE_PARENT_TEARDOWN_BARRIER ?
                        0L : data.readLong();
                if (timeoutMs < 0L || timeoutMs > 10000L) {
                    reply.writeException(new IllegalArgumentException("lab teardown barrier timeout out of range"));
                    return true;
                }
                CountDownLatch latch;
                synchronized (labParentTeardownBarrierLock) {
                    if (ownerIdentity == null || ownerIdentity.sessionId != labParentTeardownBarrierSessionId) {
                        reply.writeNoException();
                        reply.writeInt(0);
                        return true;
                    }
                    if (code == FrameIpcProtocol.LAB_RELEASE_PARENT_TEARDOWN_BARRIER) {
                        labParentTeardownRelease.countDown();
                        reply.writeNoException();
                        reply.writeInt(1);
                        return true;
                    }
                    latch = code == FrameIpcProtocol.LAB_WAIT_PARENT_TEARDOWN_BARRIER ?
                            labParentTeardownEntered : labParentTeardownContender;
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
            if (code == FrameIpcProtocol.PARENT_OPEN_AUTHORITY) {
                FrameStreamIdentity ownerIdentity = readIdentity(data);
                IBinder ownerSink = data.readStrongBinder();
                boolean accepted = isAuthorizedParentCaller(Binder.getCallingPid()) &&
                        openParentAuthority(ownerIdentity, ownerSink);
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                return true;
            }
            if (code == FrameIpcProtocol.TYPE110_SINK_ADMISSION) {
                long sessionId = data.readLong();
                int callerPid = Binder.getCallingPid();
                IBinder grant = issueSinkAdmission(sessionId, callerPid);
                reply.writeNoException();
                reply.writeInt(grant == null ? 0 : 1);
                if (grant != null) reply.writeStrongBinder(grant);
                Log.i(TAG, "TYPE110_SINK_ADMISSION_ISSUED session_id=" + sessionId +
                        " caller_pid=" + callerPid + " accepted=" + (grant != null));
                return true;
            }
            if (code == FrameIpcProtocol.TYPE110_PROBE_REGISTER) {
                FrameStreamIdentity ownerIdentity = readIdentity(data);
                FrameStreamIdentity expectedDeath = readIdentity(data);
                long lastFrameId = data.readLong();
                int sinkPid = data.readInt();
                boolean accepted = registerType110Recovery(ownerIdentity, expectedDeath,
                        lastFrameId, sinkPid);
                reply.writeNoException(); reply.writeInt(accepted ? 1 : 0);
                return true;
            }
            if (code == FrameIpcProtocol.TYPE111_PRODUCER_AUTHORIZE) {
                int ownerPid = data.readInt();
                FrameStreamIdentity childIdentity = readIdentity(data);
                boolean accepted = authorizeType111Producer(ownerPid, childIdentity);
                reply.writeNoException(); reply.writeInt(accepted ? 1 : 0);
                return true;
            }
            if (code == FrameIpcProtocol.END) {
                FrameStreamIdentity identity = readIdentity(data);
                boolean accepted = endStream(identity);
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
                    boolean registeredAndOpen;
                    synchronized (streamsLock) {
                        registeredAndOpen = streams.get(identity.key()) == state &&
                                identity.equals(state.identity) &&
                                !closingSessions.contains(identity.sessionId);
                    }
                    boolean eligible = registeredAndOpen && isSessionOwnerCaller(identity.sessionId) &&
                            newGeneration > identity.streamGeneration &&
                            !state.transferActive.get() &&
                            (identity.streamType != FrameStreamIdentity.TYPE111 ||
                            (plane != null && plane.canTransportGeneration(identity,
                                    identity.withGeneration(newGeneration))));
                    boolean sinkAccepted = eligible && forwardGenerationChange(state.sink,
                            identity, newGeneration);
                    boolean compositorAccepted = sinkAccepted && state.compositor.replaceGeneration(
                            identity.streamGeneration, newGeneration);
                    boolean controlAccepted = compositorAccepted &&
                            (identity.streamType != FrameStreamIdentity.TYPE111 ||
                            (plane != null && "accepted".equals(plane.transportGeneration(
                                    identity, identity.withGeneration(newGeneration)))));
                    if (controlAccepted) {
                        synchronized (streamsLock) {
                            // If teardown closed admission while the sink was processing this
                            // already-admitted request, publish the new identity before teardown
                            // takes its state-locked snapshot. Teardown waits for state.lock.
                            ParentAuthority authority = parentAuthorities.get(identity.sessionId);
                            if (streams.get(identity.key()) == state && identity.equals(state.identity) &&
                                    authority != null && !authority.dead &&
                                    authority.ownerPid == Binder.getCallingPid() &&
                                    !closingSessions.contains(identity.sessionId)) {
                                state.identity = identity.withGeneration(newGeneration);
                                if (identity.streamType == FrameStreamIdentity.TYPE110 &&
                                        identity.equals(authority.ownerIdentity))
                                    authority.ownerIdentity = state.identity;
                                state.lastFrameId = 0L;
                                accepted = true;
                            }
                        }
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
                if (identity == null || !isSessionOwnerCaller(identity.sessionId)) {
                    reply.writeNoException(); reply.writeInt(0); return true;
                }
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
                FrameStreamIdentity ownerIdentity = readIdentity(data);
                handleType111Capability(ownerIdentity, data, reply);
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
                String reason = !isSessionOwnerCaller(identity.sessionId) ? "parent_authority_required" :
                        closing ? "session_closing" :
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
                String reason = !isSessionOwnerCaller(identity.sessionId) ? "parent_authority_required" :
                        plane == null ? "session_unavailable" :
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
                String reason = !isSessionOwnerCaller(identity.sessionId) ? "parent_authority_required" :
                        plane == null ? "session_unavailable" :
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
                String reason = !isSessionOwnerCaller(identity.sessionId) ? "parent_authority_required" :
                        plane == null ? "session_unavailable" : plane.geometry(identity, area, safe);
                writeControlReply(reply, reason);
                if (plane != null) logControlSnapshot(safe ? "SafeArea" : "ViewArea", plane);
                return true;
            }
            if (code == FrameIpcProtocol.TYPE111_VIDEO_CONFIG) {
                FrameStreamIdentity identity = readIdentity(data);
                int width = data.readInt(), height = data.readInt();
                Type111ControlPlane plane = controlPlane(identity.sessionId);
                String reason = !isSessionOwnerCaller(identity.sessionId) ? "parent_authority_required" :
                        plane == null ? "session_unavailable" :
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
                FrameStreamIdentity ownerIdentity = readIdentity(data);
                String reason = teardownType111Session(ownerIdentity);
                writeControlReply(reply, reason);
                if ("accepted".equals(reason) || "accepted_pending".equals(reason))
                    Log.i(TAG, "TYPE111_PARENT_TEARDOWN_REQUEST session_id=" +
                            ownerIdentity.sessionId + " result=" + reason);
                return true;
            }
            if (code == FrameIpcProtocol.TYPE111_QUERY_STREAM) {
                FrameStreamIdentity ownerIdentity = readIdentity(data);
                FrameStreamIdentity childIdentity = null;
                boolean sinkAttached = false;
                boolean ownerValid = false;
                synchronized (streamsLock) {
                    StreamState owner = ownerIdentity == null ? null : streams.get(ownerIdentity.key());
                    ownerValid = owner != null && ownerIdentity.streamType == FrameStreamIdentity.TYPE110 &&
                            ownerIdentity.equals(owner.identity) && !closingSessions.contains(ownerIdentity.sessionId);
                    if (ownerValid && type111Sessions.containsKey(ownerIdentity.sessionId)) {
                        for (StreamState current : streams.values()) {
                            if (current.identity.sessionId == ownerIdentity.sessionId &&
                                    current.identity.streamType == FrameStreamIdentity.TYPE111) {
                                childIdentity = current.identity;
                                sinkAttached = current.sink != null;
                                break;
                            }
                        }
                    } else ownerValid = false;
                }
                reply.writeNoException();
                reply.writeInt(ownerValid ? 1 : 0);
                reply.writeInt(childIdentity == null ? 0 : 1);
                reply.writeInt(sinkAttached ? 1 : 0);
                if (childIdentity != null) writeIdentity(reply, childIdentity);
                reply.writeInt(Process.myPid());
                return true;
            }
            if (code == FrameIpcProtocol.TYPE111_DETACH_SINK) {
                FrameStreamIdentity ownerIdentity = readIdentity(data);
                FrameStreamIdentity childIdentity = readIdentity(data);
                boolean accepted = detachType111Sink(ownerIdentity, childIdentity);
                reply.writeNoException();
                reply.writeInt(accepted ? 1 : 0);
                reply.writeString(accepted ? "type111_sink_detached" : "type111_detach_rejected");
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
        authorityHandler = new Handler(Looper.getMainLooper());
        SharedPreferences preferences = getSharedPreferences(SESSION_ID_PREFS, MODE_PRIVATE);
        java.util.Set<String> legacy = preferences.getStringSet(LEGACY_SESSION_ID_SET,
                java.util.Collections.<String>emptySet());
        java.util.Set<String> saved = preferences.getStringSet(SESSION_ID_SET,
                java.util.Collections.<String>emptySet());
        String savedBloom = preferences.getString(SESSION_REPLAY_BLOOM, null);
        boolean hasSavedIssuedCount = preferences.contains(SESSION_REPLAY_ISSUED_COUNT);
        int savedIssuedCount = -1;
        if (hasSavedIssuedCount) {
            try { savedIssuedCount = preferences.getInt(SESSION_REPLAY_ISSUED_COUNT, -1); }
            catch (RuntimeException corruptIssuedCount) { sessionWindowReady = false; }
        }
        synchronized (streamsLock) {
            int legacyCountBefore = legacySessionIds.size();
            if (legacy != null) for (String value : legacy) {
                try {
                    long sessionId = Long.parseLong(value);
                    if (sessionId > 0L) legacySessionIds.add(sessionId);
                } catch (NumberFormatException ignored) { }
            }
            if (saved != null) for (String value : saved) {
                try {
                    long sessionId = Long.parseLong(value);
                    if (sessionId > 0L) persistedSessionIds.add(sessionId);
                } catch (NumberFormatException ignored) { }
            }
            String order = preferences.getString(SESSION_ID_ORDER, "");
            if (order.length() > 0) for (String value : order.split(",")) {
                try {
                    long sessionId = Long.parseLong(value);
                    if (persistedSessionIds.contains(sessionId) && !persistedSessionOrder.contains(sessionId))
                        persistedSessionOrder.add(sessionId);
                } catch (NumberFormatException ignored) { }
            }
            // If an interrupted/corrupt v2 write left IDs without order metadata, move them
            // to the permanent fail-closed legacy set before replacing either v2 preference.
            ArrayList<Long> unsequenced = new ArrayList<Long>();
            for (Long sessionId : persistedSessionIds)
                if (!persistedSessionOrder.contains(sessionId)) unsequenced.add(sessionId);
            for (Long sessionId : unsequenced) {
                legacySessionIds.add(sessionId);
                persistedSessionIds.remove(sessionId);
            }
            // A missing Bloom value is migratable only for installs that predate
            // the count marker. If the marker exists, missing filter bytes mean
            // initialized replay state was lost; never rebuild from the 256-ID
            // window and accidentally forget identities already evicted from it.
            boolean migrateReplayBloom = savedBloom == null && !hasSavedIssuedCount;
            if (migrateReplayBloom) {
                for (Long sessionId : legacySessionIds) addSessionReplayBloom(sessionReplayBloom, sessionId);
                for (Long sessionId : persistedSessionIds) addSessionReplayBloom(sessionReplayBloom, sessionId);
                java.util.HashSet<Long> knownIds = new java.util.HashSet<Long>(legacySessionIds);
                knownIds.addAll(persistedSessionIds);
                sessionReplayIssuedCount = knownIds.size();
            } else if (savedBloom != null) {
                try {
                    byte[] decoded = android.util.Base64.decode(savedBloom, android.util.Base64.DEFAULT);
                    if (decoded.length != SESSION_REPLAY_BLOOM_BYTES) sessionWindowReady = false;
                    else sessionReplayBloom = decoded;
                } catch (IllegalArgumentException corruptBloom) { sessionWindowReady = false; }
                sessionReplayIssuedCount = savedIssuedCount;
                if (sessionReplayIssuedCount < 0 ||
                        sessionReplayIssuedCount > MAX_SESSION_IDS_SINCE_REPLAY_INITIALIZATION)
                    sessionWindowReady = false;
            } else {
                sessionWindowReady = false;
            }
            if (legacySessionIds.size() != legacyCountBefore) {
                java.util.HashSet<String> legacyEncoded = new java.util.HashSet<String>();
                for (Long sessionId : legacySessionIds) legacyEncoded.add(sessionId.toString());
                if (!preferences.edit().putStringSet(LEGACY_SESSION_ID_SET, legacyEncoded).commit())
                    sessionWindowReady = false;
            }
            boolean windowTrimmed = false;
            while (persistedSessionOrder.size() > MAX_RECENT_SESSION_IDS) {
                Long expired = persistedSessionOrder.remove(0);
                persistedSessionIds.remove(expired);
                windowTrimmed = true;
            }
            if (sessionWindowReady && (migrateReplayBloom || unsequenced.size() > 0 || windowTrimmed)) {
                if (!persistSessionWindowLocked(preferences, persistedSessionOrder,
                        persistedSessionIds, sessionReplayBloom, sessionReplayIssuedCount))
                    sessionWindowReady = false;
            }
        }
        Log.i(TAG, "IPC_REMOTE_SESSION_REPLAY_WINDOW_LOADED count=" + persistedSessionIds.size() +
                " legacy_unordered_count=" + legacySessionIds.size() +
                " retention=" + MAX_RECENT_SESSION_IDS + " bloom_bytes=" +
                sessionReplayBloom.length + " no_false_negatives_since_bloom_initialization=true");
        Log.i(TAG, "IPC_REMOTE_PROCESS_READY pid=" + Process.myPid());
    }

    /** Must be called under streamsLock; commit before any registration can be published. */
    private boolean reserveSessionIdLocked(long sessionId) {
        if (!sessionWindowReady || sessionId <= 0L) return false;
        if (activeSessionIds.contains(sessionId)) return true;
        if (sessionReplayIssuedCount >= MAX_SESSION_IDS_SINCE_REPLAY_INITIALIZATION) return false;
        if (mightContainSessionReplay(sessionReplayBloom, sessionId)) return false;
        if (persistedSessionIds.contains(sessionId) || legacySessionIds.contains(sessionId)) return false;
        ArrayList<Long> nextOrder = new ArrayList<Long>(persistedSessionOrder);
        java.util.HashSet<Long> nextIds = new java.util.HashSet<Long>(persistedSessionIds);
        if (nextOrder.size() >= MAX_RECENT_SESSION_IDS) {
            int evict = -1;
            for (int i = 0; i < nextOrder.size(); i++)
                if (!activeSessionIds.contains(nextOrder.get(i))) { evict = i; break; }
            if (evict < 0) return false;
            nextIds.remove(nextOrder.remove(evict));
        }
        nextOrder.add(sessionId);
        nextIds.add(sessionId);
        SharedPreferences preferences = getSharedPreferences(SESSION_ID_PREFS, MODE_PRIVATE);
        byte[] nextBloom = sessionReplayBloom.clone();
        addSessionReplayBloom(nextBloom, sessionId);
        int nextIssuedCount = sessionReplayIssuedCount + 1;
        if (!persistSessionWindowLocked(preferences, nextOrder, nextIds, nextBloom,
                nextIssuedCount)) return false;
        persistedSessionOrder.clear();
        persistedSessionOrder.addAll(nextOrder);
        persistedSessionIds.clear();
        persistedSessionIds.addAll(nextIds);
        sessionReplayBloom = nextBloom;
        sessionReplayIssuedCount = nextIssuedCount;
        activeSessionIds.add(sessionId);
        return true;
    }

    /** Must be called under streamsLock; write the bounded replay window atomically. */
    private boolean persistSessionWindowLocked(SharedPreferences preferences,
            ArrayList<Long> order, java.util.HashSet<Long> ids, byte[] replayBloom,
            int issuedCount) {
        java.util.HashSet<String> encoded = new java.util.HashSet<String>();
        StringBuilder ordered = new StringBuilder();
        for (Long sessionId : order) {
            encoded.add(sessionId.toString());
            if (ordered.length() > 0) ordered.append(',');
            ordered.append(sessionId);
        }
        return preferences.edit().putStringSet(SESSION_ID_SET, encoded)
                .putString(SESSION_ID_ORDER, ordered.toString())
                .putString(SESSION_REPLAY_BLOOM, android.util.Base64.encodeToString(
                        replayBloom, android.util.Base64.NO_WRAP))
                .putInt(SESSION_REPLAY_ISSUED_COUNT, issuedCount).commit();
    }

    private static boolean mightContainSessionReplay(byte[] bloom, long sessionId) {
        long first = mixSessionReplayHash(sessionId);
        long second = mixSessionReplayHash(sessionId ^ 0x9e3779b97f4a7c15L) | 1L;
        for (int i = 0; i < 4; i++) {
            int bit = (int) (first + i * second) & (bloom.length * 8 - 1);
            if ((bloom[bit >>> 3] & (1 << (bit & 7))) == 0) return false;
        }
        return true;
    }

    private static void addSessionReplayBloom(byte[] bloom, long sessionId) {
        long first = mixSessionReplayHash(sessionId);
        long second = mixSessionReplayHash(sessionId ^ 0x9e3779b97f4a7c15L) | 1L;
        for (int i = 0; i < 4; i++) {
            int bit = (int) (first + i * second) & (bloom.length * 8 - 1);
            bloom[bit >>> 3] = (byte) (bloom[bit >>> 3] | (1 << (bit & 7)));
        }
    }

    private static long mixSessionReplayHash(long value) {
        value ^= value >>> 33;
        value *= 0xff51afd7ed558ccdL;
        value ^= value >>> 33;
        value *= 0xc4ceb9fe1a85ec53L;
        value ^= value >>> 33;
        return value;
    }

    @Override public IBinder onBind(Intent intent) { return endpoint; }

    private Type111ControlPlane controlPlane(long sessionId) {
        synchronized (streamsLock) { return type111Sessions.get(sessionId); }
    }

    /** Establishes owner authority before capability registration; no video stream is activated here. */
    private boolean openParentAuthority(final FrameStreamIdentity ownerIdentity, final IBinder ownerSink) {
        if (ownerIdentity == null || !ownerIdentity.isValid() ||
                ownerIdentity.streamType != FrameStreamIdentity.TYPE110 || ownerSink == null ||
                !ownerSink.isBinderAlive()) return false;
        final int ownerPid = Binder.getCallingPid();
        if (!isAuthorizedParentCaller(ownerPid)) return false;
        final String callerProcess = processNameForPid(ownerPid);
        try {
            if (!ownerIdentity.equals(FrameLabSink.queryIdentity(ownerSink))) return false;
            FrameLabSink.Stats ownerStats = FrameLabSink.queryStats(ownerSink);
            String ownerProcess = processNameForPid(ownerStats == null ? -1 : ownerStats.pid);
            boolean realSinkService = (getPackageName() + ":type110_sink").equals(ownerProcess);
            boolean protectedOwnerDeathFixture = (getPackageName() + ":owner_death_test").equals(callerProcess) &&
                    ownerStats != null && ownerStats.pid == ownerPid;
            if (!realSinkService && !protectedOwnerDeathFixture) return false;
            if (!FrameLabSink.bindCompositorEpoch(ownerSink, ownerIdentity, endpoint)) return false;
        } catch (RemoteException | RuntimeException invalidOwner) {
            return false;
        }
        final ParentAuthority proposed = new ParentAuthority(ownerIdentity, ownerSink,
                android.os.SystemClock.elapsedRealtimeNanos(), ownerPid, callerProcess);
        proposed.deathRecipient = new IBinder.DeathRecipient() {
            public void binderDied() {
                Log.i(TAG, "IPC_TYPE110_PARENT_DEATH_CALLBACK_ENTERED session_id=" +
                        proposed.ownerIdentity.sessionId + " owner_epoch=" + proposed.epoch +
                        " owner_pid=" + proposed.ownerPid + " death_recipient_id=" +
                        System.identityHashCode(proposed.deathRecipient) +
                        " owner_binder_alive=" + proposed.ownerSink.isBinderAlive());
                proposed.dead = true;
                revokeParentAuthority(proposed);
            }
        };
        try { ownerSink.linkToDeath(proposed.deathRecipient, 0); }
        catch (RemoteException deadOwner) { return false; }
        Log.i(TAG, "IPC_TYPE110_PARENT_DEATH_LINK_ATTEMPTED session_id=" + ownerIdentity.sessionId +
                " owner_epoch=" + proposed.epoch + " owner_pid=" + ownerPid +
                " sink_binder_id=" + System.identityHashCode(ownerSink) +
                " death_recipient_id=" + System.identityHashCode(proposed.deathRecipient));
        boolean accepted = false;
        boolean installed = false;
        boolean rebound = false;
        long acceptedEpoch = proposed.epoch;
        ParentAuthority existingSnapshot;
        int existingOwnerPid = -1;
        String existingOwnerProcess = null;
        synchronized (streamsLock) {
            existingSnapshot = parentAuthorities.get(ownerIdentity.sessionId);
            if (existingSnapshot != null) {
                existingOwnerPid = existingSnapshot.ownerPid;
                existingOwnerProcess = existingSnapshot.ownerProcess;
            }
        }
        // ActivityManager is a Binder call. Keep it outside streamsLock so owner death,
        // stream registration, and teardown cannot be blocked behind process inspection.
        String observedExistingProcess = existingSnapshot == null ? null :
                processNameForPid(existingOwnerPid);
        synchronized (streamsLock) {
            ParentAuthority existing = parentAuthorities.get(ownerIdentity.sessionId);
            if (existing != null && existing == existingSnapshot &&
                    existing.ownerPid == existingOwnerPid &&
                    existing.ownerProcess.equals(existingOwnerProcess)) {
                boolean sameLiveOwner = existing.ownerPid == ownerPid &&
                        existing.ownerProcess.equals(callerProcess);
                boolean oldOwnerProcessGone = !existing.ownerProcess.equals(observedExistingProcess);
                boolean authorizedOwnerRebind = oldOwnerProcessGone &&
                        existing.ownerProcess.equals(callerProcess);
                accepted = existing.ownerIdentity.equals(ownerIdentity) &&
                        existing.ownerSink.equals(ownerSink) && (sameLiveOwner || authorizedOwnerRebind) &&
                        !existing.dead && ownerSink.isBinderAlive();
                if (accepted) acceptedEpoch = existing.epoch;
                if (accepted && authorizedOwnerRebind) {
                    existing.ownerPid = ownerPid;
                    rebound = true;
                }
            } else if (existing == null && existingSnapshot == null &&
                    !closingSessions.contains(ownerIdentity.sessionId) &&
                    !proposed.dead && ownerSink.isBinderAlive() &&
                    parentAuthorities.size() < MAX_ACTIVE_PARENT_SESSIONS &&
                    reserveSessionIdLocked(ownerIdentity.sessionId)) {
                parentAuthorities.put(ownerIdentity.sessionId, proposed);
                accepted = true;
                installed = true;
            }
        }
        if (!installed) {
            try { ownerSink.unlinkToDeath(proposed.deathRecipient, 0); }
            catch (RuntimeException ignored) { }
        }
        if (!accepted) {
            return false;
        }
        if (installed) {
            Log.i(TAG, "IPC_TYPE110_PARENT_DEATH_LINKED session_id=" +
                    ownerIdentity.sessionId + " owner_epoch=" + proposed.epoch +
                    " owner_pid=" + ownerPid + " sink_binder_id=" +
                    System.identityHashCode(ownerSink) + " death_recipient_id=" +
                    System.identityHashCode(proposed.deathRecipient));
            proposed.provisionalExpiry = new Runnable() {
                public void run() { expireProvisionalParentAuthority(proposed); }
            };
            authorityHandler.postDelayed(proposed.provisionalExpiry,
                    PROVISIONAL_PARENT_AUTHORITY_TIMEOUT_MS);
        }
        Log.i(TAG, "TYPE110_PARENT_AUTHORITY_OPEN session_id=" + ownerIdentity.sessionId +
                " owner_epoch=" + acceptedEpoch + " opener_pid=" + ownerPid +
                " owner_sink_alive=true stream_registered=" +
                (findStream(ownerIdentity) != null) + " authority=synthetic_lab_only rebind=" + rebound);
        return true;
    }

    private boolean isAuthorizedParentCaller(int pid) {
        String process = processNameForPid(pid);
        return (getPackageName() + ":type111_view").equals(process) ||
                (getPackageName() + ":owner_death_test").equals(process) ||
                (getPackageName() + ":owner_test").equals(process);
    }

    private IBinder issueSinkAdmission(long sessionId, int callerPid) {
        if (sessionId <= 0L || !isAuthorizedParentCaller(callerPid)) return null;
        synchronized (streamsLock) {
            long now = android.os.SystemClock.elapsedRealtimeNanos();
            java.util.Iterator<Map.Entry<Long, SinkAdmissionGrant>> iterator =
                    sinkAdmissionGrants.entrySet().iterator();
            while (iterator.hasNext()) {
                SinkAdmissionGrant grant = iterator.next().getValue();
                if (grant.consumed.get() || now > grant.expiresAtNs) iterator.remove();
            }
            if (parentAuthorities.containsKey(sessionId) || closingSessions.contains(sessionId)) return null;
            SinkAdmissionGrant existing = sinkAdmissionGrants.get(sessionId);
            if (existing != null) return null;
            if (sinkAdmissionGrants.size() >= MAX_ACTIVE_PARENT_SESSIONS) return null;
            SinkAdmissionGrant grant = new SinkAdmissionGrant(sessionId);
            sinkAdmissionGrants.put(sessionId, grant);
            return grant;
        }
    }

    private boolean registerType110Recovery(FrameStreamIdentity ownerIdentity,
            FrameStreamIdentity expectedDeath, long lastFrameId, int sinkPid) {
        int callerPid = Binder.getCallingPid();
        if (ownerIdentity == null || !ownerIdentity.isValid() ||
                ownerIdentity.streamType != FrameStreamIdentity.TYPE110 || expectedDeath == null ||
                !expectedDeath.isValid() || expectedDeath.streamType != FrameStreamIdentity.TYPE111 ||
                ownerIdentity.sessionId != expectedDeath.sessionId || lastFrameId <= 0L || sinkPid <= 0 ||
                !isSessionOwnerCaller(ownerIdentity.sessionId)) {
            Log.w(TAG, "TYPE110_POST_DEATH_RECOVERY_REJECT reason=identity_or_caller session_id=" +
                    (ownerIdentity == null ? 0L : ownerIdentity.sessionId) + " caller_pid=" + callerPid);
            return false;
        }
        StreamState ownerState = findStream(ownerIdentity);
        StreamState childState = findStream(expectedDeath);
        if (ownerState == null || childState == null || childState.sink == null) {
            Log.w(TAG, "TYPE110_POST_DEATH_RECOVERY_REJECT reason=stream_missing session_id=" +
                    ownerIdentity.sessionId + " owner_present=" + (ownerState != null) +
                    " child_present=" + (childState != null) + " child_sink=" +
                    (childState != null && childState.sink != null));
            return false;
        }
        try {
            FrameLabSink.Stats actual = FrameLabSink.queryStats(ownerState.sink);
            if (actual == null || actual.pid != sinkPid || actual.frameId != lastFrameId) {
                Log.w(TAG, "TYPE110_POST_DEATH_RECOVERY_REJECT reason=owner_sink_receipt_mismatch session_id=" +
                        ownerIdentity.sessionId + " expected_pid=" + sinkPid + " actual_pid=" +
                        (actual == null ? 0 : actual.pid) + " expected_frame=" + lastFrameId +
                        " actual_frame=" + (actual == null ? 0L : actual.frameId));
                return false;
            }
        } catch (RemoteException | RuntimeException unavailable) {
            Log.w(TAG, "TYPE110_POST_DEATH_RECOVERY_REJECT reason=owner_sink_unavailable session_id=" +
                    ownerIdentity.sessionId, unavailable);
            return false;
        }
        synchronized (streamsLock) {
            ParentAuthority authority = parentAuthorities.get(ownerIdentity.sessionId);
            if (authority == null || authority.dead || authority.ownerPid != callerPid ||
                    !authority.ownerIdentity.equals(ownerIdentity) || !authority.ownerSink.isBinderAlive() ||
                    streams.get(ownerIdentity.key()) != ownerState ||
                    streams.get(expectedDeath.key()) != childState ||
                    !expectedDeath.equals(childState.identity) || childState.sink == null ||
                    closingSessions.contains(ownerIdentity.sessionId)) {
                Log.w(TAG, "TYPE110_POST_DEATH_RECOVERY_REJECT reason=authority_changed session_id=" +
                        ownerIdentity.sessionId + " authority_present=" + (authority != null) +
                        " dead=" + (authority != null && authority.dead) + " owner_pid=" +
                        (authority == null ? 0 : authority.ownerPid) + " caller_pid=" + callerPid +
                        " owner_identity_match=" + (authority != null && authority.ownerIdentity.equals(ownerIdentity)) +
                        " owner_binder_alive=" + (authority != null && authority.ownerSink.isBinderAlive()) +
                        " owner_stream_match=" + (streams.get(ownerIdentity.key()) == ownerState) +
                        " child_stream_match=" + (streams.get(expectedDeath.key()) == childState) +
                        " child_identity_match=" + (expectedDeath.equals(childState.identity)) +
                        " shutting_down=" + closingSessions.contains(ownerIdentity.sessionId));
                return false;
            }
            authority.pendingType110Recovery = new Type110LabProbeOwnership.Record(
                    ownerIdentity, expectedDeath, lastFrameId, sinkPid);
        }
        Log.i(TAG, "TYPE110_POST_DEATH_RECOVERY_REGISTERED session_id=" + ownerIdentity.sessionId +
                " child_generation=" + expectedDeath.streamGeneration + " owner_pid=" + callerPid +
                " sink_pid=" + sinkPid + " frame_id=" + lastFrameId +
                " authority=compositor_memory");
        return true;
    }

    /** Grants one live Type111 producer PID access only to the exact owner-authorized child stream. */
    private boolean authorizeType111Producer(int ownerPid, FrameStreamIdentity childIdentity) {
        int producerPid = Binder.getCallingPid();
        String producerProcess = processNameForPid(producerPid);
        if (ownerPid <= 0 || childIdentity == null || !childIdentity.isValid() ||
                childIdentity.streamType != FrameStreamIdentity.TYPE111 ||
                !(getPackageName() + ":type111_producer").equals(producerProcess) ||
                !isAuthorizedParentCaller(ownerPid)) return false;
        final ParentAuthority authoritySnapshot;
        final int priorPid;
        synchronized (streamsLock) {
            ParentAuthority authority = parentAuthorities.get(childIdentity.sessionId);
            StreamState child = streams.get(childIdentity.key());
            if (authority == null || authority.dead || authority.ownerPid != ownerPid ||
                    !authority.ownerSink.isBinderAlive() || child == null ||
                    !childIdentity.equals(child.identity) || child.sink == null ||
                    type111Sessions.get(childIdentity.sessionId) == null ||
                    closingSessions.contains(childIdentity.sessionId)) return false;
            authoritySnapshot = authority;
            priorPid = authority.authorizedType111ProducerPid;
        }
        // Resolve a prior producer PID without holding the receiver-wide lock. Recheck
        // the authority and grant under the lock before changing the authorization.
        String priorProcess = processNameForPid(priorPid);
        synchronized (streamsLock) {
            ParentAuthority authority = parentAuthorities.get(childIdentity.sessionId);
            StreamState child = streams.get(childIdentity.key());
            if (authority != authoritySnapshot || authority == null || authority.dead ||
                    authority.ownerPid != ownerPid || !authority.ownerSink.isBinderAlive() ||
                    child == null || !childIdentity.equals(child.identity) || child.sink == null ||
                    type111Sessions.get(childIdentity.sessionId) == null ||
                    closingSessions.contains(childIdentity.sessionId) ||
                    authority.authorizedType111ProducerPid != priorPid) return false;
            if (priorPid > 0 && priorPid != producerPid &&
                    (getPackageName() + ":type111_producer").equals(priorProcess)) return false;
            authority.authorizedType111ProducerPid = producerPid;
            authority.authorizedType111ProducerIdentity = childIdentity;
            Log.i(TAG, "TYPE111_PRODUCER_SESSION_AUTHORIZED session_id=" +
                    childIdentity.sessionId + " connection_id=" + childIdentity.connectionId +
                    " generation=" + childIdentity.streamGeneration + " owner_pid=" + ownerPid +
                    " producer_pid=" + producerPid);
            return true;
        }
    }

    private String processNameForPid(int pid) {
        if (pid <= 0) return null;
        android.app.ActivityManager manager = (android.app.ActivityManager)
                getSystemService(ACTIVITY_SERVICE);
        if (manager == null) return null;
        java.util.List<android.app.ActivityManager.RunningAppProcessInfo> processes =
                manager.getRunningAppProcesses();
        if (processes == null) return null;
        for (android.app.ActivityManager.RunningAppProcessInfo process : processes)
            if (process.pid == pid && process.uid == Process.myUid()) return process.processName;
        return null;
    }

    private boolean isSessionOwnerCaller(long sessionId) {
        return isSessionOwnerCaller(sessionId, false);
    }

    /** Shutdown may still need the exact owner to release and observe a test-only held transfer. */
    private boolean isSessionOwnerCaller(long sessionId, boolean allowClosingForDrain) {
        final int callerPid = Binder.getCallingPid();
        final ParentAuthority expected;
        synchronized (streamsLock) {
            expected = parentAuthorities.get(sessionId);
            if (expected == null || expected.dead || expected.ownerPid != callerPid ||
                    !expected.ownerSink.isBinderAlive() ||
                    (!allowClosingForDrain && closingSessions.contains(sessionId))) return false;
        }
        // The owner PID is not a capability: API17 may reuse it after the Activity process dies.
        // Resolve the recorded role without holding streamsLock, then fence against authority
        // replacement and shutdown before admitting the operation.
        if (!expected.ownerProcess.equals(processNameForPid(callerPid))) return false;
        synchronized (streamsLock) {
            ParentAuthority current = parentAuthorities.get(sessionId);
            return current == expected && !current.dead && current.ownerPid == callerPid &&
                    current.ownerSink.isBinderAlive() &&
                    (allowClosingForDrain || !closingSessions.contains(sessionId));
        }
    }

    private boolean isAuthorizedFrameCaller(FrameStreamIdentity identity) {
        if (identity == null || Binder.getCallingUid() != Process.myUid()) return false;
        final int callerPid = Binder.getCallingPid();
        ParentAuthority producerAuthority = null;
        boolean ownerCandidate = false;
        synchronized (streamsLock) {
            ParentAuthority authority = parentAuthorities.get(identity.sessionId);
            if (authority == null || authority.dead || closingSessions.contains(identity.sessionId)) return false;
            if (authority.ownerPid == callerPid) ownerCandidate = true;
            if (authority.authorizedType111ProducerPid == callerPid &&
                    identity.streamType == FrameStreamIdentity.TYPE111 &&
                    identity.equals(authority.authorizedType111ProducerIdentity)) {
                StreamState child = streams.get(identity.key());
                if (child == null || !identity.equals(child.identity) || child.sink == null) return false;
                producerAuthority = authority;
            }
        }
        if (ownerCandidate) return isSessionOwnerCaller(identity.sessionId);
        if (producerAuthority != null) {
            // PID authorization alone is vulnerable to Android PID reuse. Resolve process role
            // outside streamsLock, then revalidate the exact authority and stream under the lock.
            if (!(getPackageName() + ":type111_producer").equals(processNameForPid(callerPid))) {
                Log.w(TAG, "IPC_REMOTE_FRAME_REJECT caller_pid=" + callerPid +
                        " session_id=" + identity.sessionId + " reason=producer_process_role_changed");
                return false;
            }
            synchronized (streamsLock) {
                ParentAuthority current = parentAuthorities.get(identity.sessionId);
                StreamState child = streams.get(identity.key());
                return current == producerAuthority && !current.dead &&
                        !closingSessions.contains(identity.sessionId) &&
                        current.authorizedType111ProducerPid == callerPid &&
                        identity.equals(current.authorizedType111ProducerIdentity) &&
                        child != null && identity.equals(child.identity) && child.sink != null;
            }
        }
        String process = processNameForPid(Binder.getCallingPid());
        return (getPackageName() + ":type110_probe").equals(process) ||
                (getPackageName() + ":owner_death_test").equals(process);
    }

    private void revokeParentAuthority(ParentAuthority expected) {
        revokeParentAuthority(expected, "owner_binder_death");
    }

    private void expireProvisionalParentAuthority(ParentAuthority expected) {
        synchronized (streamsLock) {
            if (parentAuthorities.get(expected.ownerIdentity.sessionId) != expected || !expected.provisional)
                return;
            expected.dead = true;
        }
        revokeParentAuthority(expected, "provisional_authority_timeout");
    }

    private void revokeParentAuthority(ParentAuthority expected, String cause) {
        if (expected == null) return;
        expected.dead = true;
        ArrayList<StreamState> owned = new ArrayList<StreamState>();
        Type111ControlPlane plane;
        synchronized (streamsLock) {
            if (parentAuthorities.get(expected.ownerIdentity.sessionId) != expected) return;
            closingSessions.add(expected.ownerIdentity.sessionId);
            pendingParentTeardowns.add(expected.ownerIdentity.sessionId);
            parentAuthorities.remove(expected.ownerIdentity.sessionId);
            if (expected.provisionalExpiry != null) authorityHandler.removeCallbacks(expected.provisionalExpiry);
            plane = type111Sessions.remove(expected.ownerIdentity.sessionId);
            for (StreamState state : streams.values())
                if (state.identity.sessionId == expected.ownerIdentity.sessionId) owned.add(state);
        }
        releaseParentTeardownBarrierOnOwnerLoss(expected.ownerIdentity.sessionId);
        for (StreamState state : owned) {
            FrameStreamIdentity identity;
            synchronized (state.lock) { identity = state.identity; }
            if (identity != null) unregisterStreamState(state, identity);
        }
        if (plane != null) plane.parentTeardown();
        boolean completed = finishPendingParentTeardown(expected.ownerIdentity.sessionId);
        if (!completed) {
            Log.w(TAG, "TYPE111_PARENT_TEARDOWN_PENDING session_id=" +
                    expected.ownerIdentity.sessionId + " streams_pending=" +
                    countSessionStreams(expected.ownerIdentity.sessionId) + " reason=owner_revoked");
        }
        synchronized (streamsLock) {
            synchronized (labDelayedDeathLock) {
                if (labDelayedDeathIdentity != null &&
                        labDelayedDeathIdentity.sessionId == expected.ownerIdentity.sessionId) {
                    labDelayedDeathRelease.countDown();
                    labDelayedDeathIdentity = null;
                    labDelayedDeathState = null;
                    labDelayedDeathRecipient = null;
                    labDelayedDeathEntered = new CountDownLatch(0);
                    labDelayedDeathRelease = new CountDownLatch(0);
                    labDelayedDeathCompleted = new CountDownLatch(0);
                }
            }
        }
        try { expected.ownerSink.unlinkToDeath(expected.deathRecipient, 0); }
        catch (RuntimeException ignored) { }
        Log.i(TAG, "TYPE110_PARENT_AUTHORITY_REVOKED session_id=" +
                expected.ownerIdentity.sessionId + " owner_epoch=" + expected.epoch +
                " streams_closed=" + owned.size() + " cause=" + cause);
    }

    /** Owner loss must not strand a test-only teardown gate after authority is revoked. */
    private void releaseParentTeardownBarrierOnOwnerLoss(long sessionId) {
        synchronized (labParentTeardownBarrierLock) {
            if (sessionId != labParentTeardownBarrierSessionId) return;
            labParentTeardownRelease.countDown();
            Log.i(TAG, "IPC_LAB_PARENT_TEARDOWN_BARRIER_RELEASED session_id=" + sessionId +
                    " cause=owner_authority_revoked");
        }
    }

    /** Arm an owner-only API test barrier; arbitrary UIDs are rejected by onTransact first. */
    private boolean armParentTeardownBarrier(FrameStreamIdentity ownerIdentity) {
        StreamState owner = findStream(ownerIdentity);
        if (ownerIdentity == null || ownerIdentity.streamType != FrameStreamIdentity.TYPE110 ||
                owner == null || !ownerIdentity.equals(owner.identity)) return false;
        synchronized (streamsLock) {
            if (closingSessions.contains(ownerIdentity.sessionId) ||
                    !type111Sessions.containsKey(ownerIdentity.sessionId)) return false;
        }
        synchronized (labParentTeardownBarrierLock) {
            labParentTeardownBarrierSessionId = ownerIdentity.sessionId;
            labParentTeardownEntered = new CountDownLatch(1);
            labParentTeardownRelease = new CountDownLatch(1);
            labParentTeardownContender = new CountDownLatch(1);
        }
        return true;
    }

    private void pauseAtParentTeardownBarrier(long sessionId) {
        CountDownLatch entered, release;
        synchronized (labParentTeardownBarrierLock) {
            if (sessionId != labParentTeardownBarrierSessionId) return;
            entered = labParentTeardownEntered;
            release = labParentTeardownRelease;
        }
        entered.countDown();
        Log.i(TAG, "IPC_LAB_PARENT_TEARDOWN_BARRIER_ENTERED session_id=" + sessionId);
        try {
            if (!release.await(10000L, TimeUnit.MILLISECONDS))
                Log.w(TAG, "IPC_LAB_PARENT_TEARDOWN_BARRIER_TIMEOUT session_id=" + sessionId);
        } catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
        synchronized (labParentTeardownBarrierLock) {
            if (sessionId == labParentTeardownBarrierSessionId) labParentTeardownBarrierSessionId = 0L;
        }
    }

    private void signalParentTeardownContender(long sessionId) {
        synchronized (labParentTeardownBarrierLock) {
            if (sessionId == labParentTeardownBarrierSessionId)
                labParentTeardownContender.countDown();
        }
    }

    /** Pause one real Type111 death callback before state mutation for the API17 race test. */
    private boolean armDelayedSinkDeathCallback(FrameStreamIdentity identity) {
        StreamState state = findStream(identity);
        if (identity == null || identity.streamType != FrameStreamIdentity.TYPE111 || state == null)
            return false;
        synchronized (state.lock) {
            if (!identity.equals(state.identity) || state.sink == null || state.deathRecipient == null)
                return false;
            synchronized (labDelayedDeathLock) {
                if (labDelayedDeathIdentity != null) return false;
                labDelayedDeathIdentity = identity;
                // The callback closes over this exact StreamState and is only invoked by
                // Binder after the registered sink dies. Binder interface proxies need not
                // have Java reference identity across transactions, so bind the test gate to
                // this state and its exact linked DeathRecipient.
                labDelayedDeathState = state;
                labDelayedDeathRecipient = state.deathRecipient;
                labDelayedDeathEntered = new CountDownLatch(1);
                labDelayedDeathRelease = new CountDownLatch(1);
                labDelayedDeathCompleted = new CountDownLatch(1);
            }
        }
        Log.i(TAG, "IPC_LAB_DELAYED_DEATH_CALLBACK_ARMED session_id=" + identity.sessionId +
                " stream_type=111 generation=" + identity.streamGeneration);
        return true;
    }

    /** Release the real old callback only after an owner-authorized replacement is current. */
    private boolean fireDelayedSinkDeathCallback(FrameStreamIdentity ownerIdentity,
            FrameStreamIdentity currentIdentity) {
        if (ownerIdentity == null || currentIdentity == null ||
                ownerIdentity.streamType != FrameStreamIdentity.TYPE110 ||
                currentIdentity.streamType != FrameStreamIdentity.TYPE111 ||
                ownerIdentity.sessionId != currentIdentity.sessionId) return false;
        StreamState owner = findStream(ownerIdentity);
        StreamState child = findStream(currentIdentity);
        if (owner == null || child == null) return false;
        CountDownLatch release, completed;
        synchronized (child.lock) {
            synchronized (streamsLock) {
                if (streams.get(ownerIdentity.key()) != owner || !ownerIdentity.equals(owner.identity) ||
                        streams.get(currentIdentity.key()) != child || !currentIdentity.equals(child.identity) ||
                        child.sink == null || closingSessions.contains(currentIdentity.sessionId))
                    return false;
                synchronized (labDelayedDeathLock) {
                    if (labDelayedDeathIdentity == null ||
                            !labDelayedDeathIdentity.sameStream(currentIdentity) ||
                            labDelayedDeathIdentity.streamGeneration + 1L != currentIdentity.streamGeneration ||
                            labDelayedDeathState != child || labDelayedDeathRecipient == null ||
                            labDelayedDeathEntered.getCount() != 0L)
                        return false;
                    release = labDelayedDeathRelease;
                    completed = labDelayedDeathCompleted;
                }
            }
        }
        release.countDown();
        try {
            if (!completed.await(10000L, TimeUnit.MILLISECONDS)) return false;
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            return false;
        }
        synchronized (child.lock) {
            boolean remainsCurrent = currentIdentity.equals(child.identity) && child.sink != null;
            synchronized (labDelayedDeathLock) {
                if (labDelayedDeathIdentity != null &&
                        labDelayedDeathIdentity.sessionId == currentIdentity.sessionId) {
                    labDelayedDeathIdentity = null;
                    labDelayedDeathState = null;
                    labDelayedDeathRecipient = null;
                }
            }
            Log.i(TAG, "IPC_LAB_DELAYED_DEATH_CALLBACK_RELEASED session_id=" + currentIdentity.sessionId +
                    " old_generation=" + (currentIdentity.streamGeneration - 1L) +
                    " current_generation=" + currentIdentity.streamGeneration +
                    " entered_before_replacement=true completed_after_replacement=true current_sink_preserved=" +
                    remainsCurrent);
            return remainsCurrent;
        }
    }

    private CountDownLatch pauseLabDelayedDeathCallback(StreamState state,
            FrameStreamIdentity identity, IBinder.DeathRecipient recipient) {
        CountDownLatch entered, release, completed;
        long currentGeneration;
        synchronized (labDelayedDeathLock) {
            if (labDelayedDeathIdentity == null || !labDelayedDeathIdentity.sameStream(identity) ||
                    labDelayedDeathState != state || labDelayedDeathRecipient != recipient) return null;
            entered = labDelayedDeathEntered;
            release = labDelayedDeathRelease;
            completed = labDelayedDeathCompleted;
            currentGeneration = labDelayedDeathIdentity.streamGeneration;
        }
        entered.countDown();
        Log.i(TAG, "IPC_LAB_DELAYED_DEATH_CALLBACK_ENTERED session_id=" + identity.sessionId +
                " stream_type=111 old_generation=" + currentGeneration +
                " state_mutation=paused");
        try {
            if (!release.await(120000L, TimeUnit.MILLISECONDS))
                Log.w(TAG, "IPC_LAB_DELAYED_DEATH_CALLBACK_TIMEOUT session_id=" + identity.sessionId);
        } catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
        return completed;
    }

    private void handleType111Capability(FrameStreamIdentity ownerIdentity, Parcel data, Parcel reply) {
        long sessionId = data.readLong();
        String uuid = data.readString();
        int width = data.readInt(), height = data.readInt(), fps = data.readInt();
        int count = data.readInt();
        String reason = "invalid_type111_capability";
        boolean ownerCaller = ownerIdentity != null && isSessionOwnerCaller(ownerIdentity.sessionId);
        if (count > 0 && count <= 2 && ownerIdentity != null &&
                ownerIdentity.sessionId == sessionId && ownerIdentity.streamType == FrameStreamIdentity.TYPE110 &&
                ownerCaller) {
            java.util.HashSet<String> contexts = new java.util.HashSet<String>();
            for (int i = 0; i < count; i++) contexts.add(data.readString());
            Type111ControlPlane plane = new Type111ControlPlane(sessionId);
            try {
                reason = plane.registerCapability(new Type111ControlPlane.Capability(
                        sessionId, uuid, width, height, fps, contexts));
                if ("accepted".equals(reason)) synchronized (streamsLock) {
                    ParentAuthority authority = parentAuthorities.get(sessionId);
                    if (ownerIdentity == null || ownerIdentity.streamType != FrameStreamIdentity.TYPE110 ||
                            authority == null || !authority.ownerIdentity.equals(ownerIdentity) ||
                            authority.ownerPid != Binder.getCallingPid() ||
                            !authority.ownerSink.isBinderAlive() || closingSessions.contains(sessionId)) {
                        plane.parentTeardown();
                        reason = "parent_authority_required";
                    } else if (type111Sessions.containsKey(sessionId)) {
                        plane.parentTeardown();
                        reason = "duplicate_session_capability";
                    } else {
                        type111Sessions.put(sessionId, plane);
                    }
                }
            } catch (IllegalArgumentException invalid) { reason = "invalid_type111_capability"; }
        } else {
            for (int i = 0; i < Math.min(Math.max(count, 0), 16); i++) data.readString();
            if (count > 0 && count <= 2) reason = "parent_authority_required";
        }
        writeControlReply(reply, reason);
        Log.i(TAG, "TYPE111_CAPABILITY session_id=" + sessionId + " display_uuid=" + uuid +
                " logical_size=" + width + "x" + height + " max_fps=" + fps + " result=" + reason +
                " owner_authorized=" + ("accepted".equals(reason)) +
                " authority=synthetic_lab_only");
    }

    private String teardownType111Session(FrameStreamIdentity type110Owner) {
        return teardownType111Session(type110Owner, false);
    }

    private String teardownType111Session(FrameStreamIdentity type110Owner, boolean internalOwnerDeath) {
        if (type110Owner == null || !type110Owner.isValid() ||
                type110Owner.streamType != FrameStreamIdentity.TYPE110)
            return "session_owner_identity_rejected";
        long sessionId = type110Owner.sessionId;
        boolean ownerCaller = !internalOwnerDeath && isSessionOwnerCaller(sessionId);
        boolean delegatedProbe = !internalOwnerDeath &&
                (getPackageName() + ":type110_probe").equals(processNameForPid(Binder.getCallingPid())) &&
                Type110LabProbeOwnership.consumeTeardownGrant(this, type110Owner, Binder.getCallingPid());
        synchronized (streamsLock) {
            StreamState owner = streams.get(type110Owner.key());
            if (owner == null || !type110Owner.equals(owner.identity))
                return "session_owner_stream_unregistered";
            if (closingSessions.contains(sessionId)) {
                signalParentTeardownContender(sessionId);
                return "session_unavailable";
            }
            ParentAuthority authority = parentAuthorities.get(sessionId);
            if (authority == null || !authority.ownerIdentity.equals(type110Owner) ||
                    (!internalOwnerDeath && !delegatedProbe && !ownerCaller) ||
                    (!internalOwnerDeath && !authority.ownerSink.isBinderAlive()))
                return "session_unavailable";
            // Close admission before taking the child snapshot. Registrations inserted before
            // this point are captured below; later registrations fail under this same lock.
            closingSessions.add(sessionId);
            pendingParentTeardowns.add(sessionId);
        }
        pauseAtParentTeardownBarrier(sessionId);
        Type111ControlPlane plane = controlPlane(sessionId);
        ArrayList<StreamState> ownedStates = new ArrayList<StreamState>();
        synchronized (streamsLock) {
            for (StreamState state : streams.values())
                if (state.identity.sessionId == sessionId) ownedStates.add(state);
        }
        ArrayList<FrameStreamIdentity> owned = new ArrayList<FrameStreamIdentity>();
        for (StreamState state : ownedStates) {
            FrameStreamIdentity identity;
            synchronized (state.lock) { identity = state.identity; }
            if (identity != null && identity.sessionId == sessionId) {
                owned.add(identity);
                unregisterStream(identity);
            }
        }
        if (!finishPendingParentTeardown(sessionId)) {
            Log.w(TAG, "TYPE111_PARENT_TEARDOWN_PENDING session_id=" + sessionId +
                    " streams_pending=" + countSessionStreams(sessionId) +
                    " reason=view_close_unacknowledged");
            // Teardown admission is already closed and every captured stream has been
            // revoked. A false Binder result here would make callers retry or report a
            // failed teardown even though this exact lifecycle is fenced and its bounded
            // close is still resolving. Report request acceptance while keeping the
            // separate completion receipt for callers that need proof of final cleanup.
            return "accepted_pending";
        }
        Log.i(TAG, "TYPE111_PARENT_TEARDOWN session_id=" + sessionId +
                " streams_closed=" + owned.size() + " result=accepted");
        return "accepted";
    }

    private int countSessionStreams(long sessionId) {
        synchronized (streamsLock) {
            int count = 0;
            for (StreamState state : streams.values())
                if (state.identity.sessionId == sessionId) count++;
            return count;
        }
    }

    private boolean finishPendingParentTeardown(long sessionId) {
        Type111ControlPlane plane;
        ParentAuthority authority;
        synchronized (streamsLock) {
            if (!pendingParentTeardowns.contains(sessionId)) return false;
            for (StreamState state : streams.values())
                if (state.identity.sessionId == sessionId) return false;
            plane = type111Sessions.remove(sessionId);
            authority = parentAuthorities.remove(sessionId);
            activeSessionIds.remove(sessionId);
            closingSessions.remove(sessionId);
            pendingParentTeardowns.remove(sessionId);
            synchronized (labDelayedDeathLock) {
                if (labDelayedDeathIdentity != null && labDelayedDeathIdentity.sessionId == sessionId) {
                    labDelayedDeathRelease.countDown();
                    labDelayedDeathIdentity = null;
                    labDelayedDeathState = null;
                    labDelayedDeathRecipient = null;
                    labDelayedDeathEntered = new CountDownLatch(0);
                    labDelayedDeathRelease = new CountDownLatch(0);
                    labDelayedDeathCompleted = new CountDownLatch(0);
                }
            }
        }
        if (authority != null) {
            try { FrameLabSink.revokeParentAuthority(authority.ownerSink, authority.ownerIdentity); }
            catch (RemoteException | RuntimeException ignored) { }
            try { authority.ownerSink.unlinkToDeath(authority.deathRecipient, 0); }
            catch (RuntimeException ignored) { }
        }
        if (plane != null) plane.parentTeardown();
        Log.i(TAG, "TYPE111_PARENT_TEARDOWN_COMPLETED session_id=" + sessionId +
                " result=accepted late_close_resolution=true");
        return true;
    }

    private static void writeControlReply(Parcel reply, String reason) {
        reply.writeNoException();
        reply.writeInt(("accepted".equals(reason) || "accepted_pending".equals(reason)) ? 1 : 0);
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
        viewCloseExecutor.shutdown();
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
        if (!isAuthorizedFrameCaller(identity)) {
            closeQuietly(descriptor);
            Log.i(TAG, "IPC_REMOTE_FRAME_REJECT caller_pid=" + Binder.getCallingPid() +
                    " session_id=" + (identity == null ? 0L : identity.sessionId) +
                    " reason=frame_caller_not_authorized");
            reply.writeNoException();
            reply.writeInt(0);
            reply.writeString("frame_caller_not_authorized");
            return;
        }
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
        boolean sessionClosing;
        synchronized (streamsLock) { sessionClosing = closingSessions.contains(identity.sessionId); }
        boolean contractValid = !sessionClosing && !state.closing && descriptor != null && identity.equals(state.identity) &&
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
            } else if (sessionClosing) {
                rejection = "session_closing";
                if (descriptor != null) {
                    descriptor.close();
                    descriptor = null;
                }
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
        if (identity == null || !identity.isValid() || sink == null || !sink.isBinderAlive() ||
                !isSessionOwnerCaller(identity.sessionId)) return false;
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
        boolean ownerSinkBinder = false;
        long ownerEpoch = -1L;
        synchronized (streamsLock) {
            ParentAuthority owner = parentAuthorities.get(identity.sessionId);
            ownerSinkBinder = owner != null && owner.ownerSink.equals(sink);
            if (owner != null) ownerEpoch = owner.epoch;
        }
        Log.i(TAG, "IPC_STREAM_SINK_DEATH_LINKED session_id=" + identity.sessionId +
                " stream_type=" + identity.streamType + " stream_generation=" +
                identity.streamGeneration + " owner_epoch=" + ownerEpoch +
                " sink_binder_id=" + System.identityHashCode(sink) +
                " owner_sink_binder=" + ownerSinkBinder + " death_recipient_id=" +
                System.identityHashCode(state.deathRecipient));
        boolean registered = false;
        final String registeringProcess = processNameForPid(Binder.getCallingPid());
        synchronized (streamsLock) {
            ParentAuthority authority = parentAuthorities.get(identity.sessionId);
            boolean validOwner = authority != null && !authority.dead && authority.ownerSink.isBinderAlive() &&
                    authority.ownerPid == Binder.getCallingPid() &&
                    authority.ownerProcess.equals(registeringProcess) &&
                    (identity.streamType != FrameStreamIdentity.TYPE110 ||
                    identity.equals(authority.ownerIdentity)) &&
                    (identity.streamType != FrameStreamIdentity.TYPE111 ||
                    type111Sessions.get(identity.sessionId) == control);
            boolean sessionAvailable = activeSessionIds.contains(identity.sessionId);
            if (!streams.containsKey(identity.key()) && validOwner && sessionAvailable &&
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
                    // Type111-first is a bounded provisional child setup. Only registration
                    // of the exact Type110 parent owner confirms session ownership.
                    if (identity.streamType == FrameStreamIdentity.TYPE110) {
                        authority.provisional = false;
                        if (authority.provisionalExpiry != null)
                            authorityHandler.removeCallbacks(authority.provisionalExpiry);
                    }
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
                Log.i(TAG, "IPC_STREAM_SINK_DEATH_CALLBACK_ENTERED session_id=" +
                        registeredIdentity.sessionId + " stream_type=" +
                        registeredIdentity.streamType + " stream_generation=" +
                        registeredIdentity.streamGeneration + " sink_binder_id=" +
                        System.identityHashCode(registeredSink) + " death_recipient_id=" +
                        System.identityHashCode(this));
                final CountDownLatch delayedCompletion = pauseLabDelayedDeathCallback(
                        state, registeredIdentity, this);
                try {
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
                else endStreamIfCurrent(state, deadIdentity);
                if (deadIdentity.streamType == FrameStreamIdentity.TYPE111) {
                    Type110LabProbeOwnership.Record recovery = takeType110RecoveryForDeath(deadIdentity);
                    if (recovery != null) authorizeType110PostDeathProbe(recovery);
                }
                } finally {
                    if (delayedCompletion != null) delayedCompletion.countDown();
                }
            }
        };
    }

    /** Only this process can authorize the private recovery service, and only after Binder death. */
    private Type110LabProbeOwnership.Record takeType110RecoveryForDeath(FrameStreamIdentity deadIdentity) {
        if (deadIdentity == null || deadIdentity.streamType != FrameStreamIdentity.TYPE111) return null;
        synchronized (streamsLock) {
            ParentAuthority authority = parentAuthorities.get(deadIdentity.sessionId);
            Type110LabProbeOwnership.Record record = authority == null ? null :
                    authority.pendingType110Recovery;
            if (authority == null || authority.dead || record == null ||
                    !deadIdentity.equals(record.expectedType111Death) ||
                    !authority.ownerIdentity.equals(record.identity) ||
                    !authority.ownerSink.isBinderAlive() || closingSessions.contains(deadIdentity.sessionId))
                return null;
            authority.pendingType110Recovery = null;
            Log.i(TAG, "TYPE110_POST_DEATH_RECOVERY_RECEIPT_CONSUMED session_id=" +
                    deadIdentity.sessionId + " child_generation=" + deadIdentity.streamGeneration +
                    " owner_epoch=" + authority.epoch + " authority=compositor_memory");
            return record;
        }
    }

    private void authorizeType110PostDeathProbe(final Type110LabProbeOwnership.Record record) {
        final FrameStreamIdentity deadIdentity = record.expectedType111Death;
        final Intent intent = new Intent(this, Type110ProgressProbeService.class);
        final ServiceConnection connection = new ServiceConnection() {
            private boolean unbound;
            private synchronized void unbindOnce() {
                if (unbound) return;
                unbound = true;
                try { unbindService(this); } catch (IllegalArgumentException ignored) { }
            }
            public void onServiceConnected(ComponentName name, IBinder probe) {
                Parcel data = Parcel.obtain();
                Parcel reply = Parcel.obtain();
                boolean accepted = false;
                try {
                    writeIdentity(data, record.identity);
                    writeIdentity(data, deadIdentity);
                    data.writeLong(record.lastFrameId); data.writeInt(record.sinkPid);
                    if (probe.transact(FrameIpcProtocol.TYPE110_PROBE_AUTHORIZE, data, reply, 0)) {
                        reply.readException();
                        accepted = reply.readInt() != 0;
                    }
                } catch (RemoteException | RuntimeException failure) {
                    Log.e(TAG, "TYPE110_POST_DEATH_PROBE_AUTHORIZATION_FAILED session_id=" +
                            deadIdentity.sessionId + " type=" + failure.getClass().getSimpleName());
                } finally {
                    data.recycle(); reply.recycle(); unbindOnce();
                }
                Log.i(TAG, "TYPE110_POST_DEATH_PROBE_INTERNAL_START session_id=" +
                        deadIdentity.sessionId + " authorized=" + accepted +
                        " after_type111_binder_death=true");
            }
            public void onServiceDisconnected(ComponentName name) {
                Log.w(TAG, "TYPE110_POST_DEATH_PROBE_BINDER_DISCONNECTED session_id=" +
                        deadIdentity.sessionId);
                unbindOnce();
            }
        };
        try {
            boolean bound = bindService(intent, connection, Context.BIND_AUTO_CREATE);
            if (!bound) Log.e(TAG, "TYPE110_POST_DEATH_PROBE_BIND_FAILED session_id=" +
                    deadIdentity.sessionId);
        } catch (RuntimeException failure) {
            Log.e(TAG, "TYPE110_POST_DEATH_PROBE_BIND_FAILED session_id=" +
                    deadIdentity.sessionId + " type=" + failure.getClass().getSimpleName());
        }
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

    /** Lifecycle detach requires the live Type110 session owner and the exact current child identity. */
    private boolean detachType111Sink(FrameStreamIdentity ownerIdentity,
            FrameStreamIdentity childIdentity) {
        if (ownerIdentity == null || !ownerIdentity.isValid() ||
                ownerIdentity.streamType != FrameStreamIdentity.TYPE110 ||
                childIdentity == null || !childIdentity.isValid() ||
                childIdentity.streamType != FrameStreamIdentity.TYPE111 ||
                ownerIdentity.sessionId != childIdentity.sessionId) return false;
        final StreamState owner = findStream(ownerIdentity);
        final StreamState child = findStream(childIdentity);
        if (owner == null || child == null) return false;
        synchronized (child.lock) {
            synchronized (streamsLock) {
                if (streams.get(ownerIdentity.key()) != owner ||
                        !ownerIdentity.equals(owner.identity) || streams.get(childIdentity.key()) != child ||
                        !childIdentity.equals(child.identity) || child.sink == null ||
                        closingSessions.contains(childIdentity.sessionId) || child.transferActive.get())
                    return false;
                if (child.deathRecipient != null) child.sink.unlinkToDeath(child.deathRecipient, 0);
                child.sink = null;
                child.deathRecipient = null;
            }
        }
        Log.i(TAG, "IPC_TYPE111_SINK_DETACHED session_id=" + childIdentity.sessionId +
                " connection_id=" + childIdentity.connectionId + " generation=" +
                childIdentity.streamGeneration + " parent_session_preserved=true " +
                "authorized_type110_owner=true");
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
                !newSink.isBinderAlive() || !isSessionOwnerCaller(ownerIdentity.sessionId)) return false;
        final StreamState state = findStream(oldIdentity);
        final Type111ControlPlane plane = controlPlane(oldIdentity.sessionId);
        if (state == null || plane == null || !plane.canTransportGeneration(oldIdentity, newIdentity))
            return false;
        synchronized (streamsLock) {
            StreamState owner = streams.get(ownerIdentity.key());
            ParentAuthority authority = parentAuthorities.get(ownerIdentity.sessionId);
            if (authority == null || authority.ownerPid != Binder.getCallingPid() || state.closing ||
                    owner == null || !ownerIdentity.equals(owner.identity) ||
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
                synchronized (streamsLock) {
                    boolean stillCurrent = streams.get(oldIdentity.key()) == state && !state.closing &&
                            oldIdentity.equals(state.identity) &&
                            !closingSessions.contains(oldIdentity.sessionId) &&
                            streams.get(ownerIdentity.key()) != null &&
                            ownerIdentity.equals(streams.get(ownerIdentity.key()).identity);
                    // Keep admission, identity publication, and the parent's teardown snapshot
                    // atomic under streamsLock. All identity/sink reads used by QUERY_STREAM are
                    // protected by the same lock.
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
                            // Keep the registry and compositor from diverging if control-plane
                            // publication unexpectedly fails after the compositor advanced.
                            state.compositor.end(newIdentity.streamGeneration);
                            streams.remove(oldIdentity.key());
                            state.sink = null;
                            state.deathRecipient = null;
                        }
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

    /** A Type110 owner ending or dying closes the entire child session it authorized. */
    private boolean endStream(FrameStreamIdentity identity) {
        if (identity != null && identity.streamType == FrameStreamIdentity.TYPE110) {
            String teardown = teardownType111Session(identity);
            if ("accepted".equals(teardown)) {
                Log.i(TAG, "TYPE110_OWNER_SESSION_INVALIDATED session_id=" + identity.sessionId +
                        " cause=owner_end streams_closed=2");
                return true;
            }
            // Type110 is the authority-bearing parent stream. Never fall through to a
            // stream-only unregister after parent teardown authorization was rejected.
            Log.w(TAG, "IPC_REMOTE_END_REJECT session_id=" + identity.sessionId +
                    " stream_type=110 reason=" + teardown);
            return false;
        } else if (identity == null || !isSessionOwnerCaller(identity.sessionId)) {
            return false;
        }
        return unregisterStream(identity);
    }

    private boolean endStreamIfCurrent(StreamState state, FrameStreamIdentity identity) {
        if (identity != null && identity.streamType == FrameStreamIdentity.TYPE110) {
            String teardown = teardownType111Session(identity, true);
            if ("accepted".equals(teardown)) {
                Log.i(TAG, "TYPE110_OWNER_SESSION_INVALIDATED session_id=" + identity.sessionId +
                        " cause=owner_sink_death streams_closed=2");
                return true;
            }
        }
        return unregisterStreamIfCurrent(state, identity);
    }

    private boolean unregisterStreamIfCurrent(StreamState expectedState, FrameStreamIdentity identity) {
        return unregisterStreamState(expectedState, identity);
    }

    private boolean unregisterStreamState(StreamState state, FrameStreamIdentity identity) {
        IBinder sinkToClose = null;
        synchronized (state.lock) {
            synchronized (streamsLock) {
                if (streams.get(identity.key()) != state || !identity.equals(state.identity))
                    return false;
                state.closing = true;
                if (identity.streamType == FrameStreamIdentity.TYPE111) sinkToClose = state.sink;
            }
        }
        // Keep the exact registration fenced until the View acknowledges closure or Binder
        // reports death. A timeout is not evidence that queued UI work was released.
        if (sinkToClose != null && sinkToClose.isBinderAlive()) {
            if (!closeViewSink(state, sinkToClose, identity)) return false;
        }
        return removeStreamRegistrationIfCurrent(state, identity);
    }

    private boolean removeStreamRegistrationIfCurrent(StreamState state, FrameStreamIdentity identity) {
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
                state.closing = true;
                streams.remove(identity.key());
                if (identity.streamType == FrameStreamIdentity.TYPE110 &&
                        !type111Sessions.containsKey(identity.sessionId))
                    activeSessionIds.remove(identity.sessionId);
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

    private boolean closeViewSink(final StreamState state, final IBinder sink,
            final FrameStreamIdentity identity) {
        return closeViewSink(state, sink, identity, 1, true);
    }

    private boolean closeViewSink(final StreamState state, final IBinder sink,
            final FrameStreamIdentity identity, final int attempt, final boolean waitForResult) {
        if (sink == null || !sink.isBinderAlive()) {
            removeStreamRegistrationIfCurrent(state, identity);
            finishPendingParentTeardown(identity.sessionId);
            return true;
        }
        synchronized (pendingViewCloses) {
            if (pendingViewCloses.contains(sink)) {
                Log.w(TAG, "IPC_VIEW_SINK_CLOSE_ALREADY_PENDING session_id=" + identity.sessionId +
                        " generation=" + identity.streamGeneration);
                return false;
            }
            if (pendingViewCloses.size() >= MAX_PENDING_VIEW_CLOSES) {
                Log.w(TAG, "IPC_VIEW_SINK_CLOSE_CAPACITY_REACHED session_id=" + identity.sessionId +
                        " generation=" + identity.streamGeneration);
                return false;
            }
            pendingViewCloses.add(sink);
        }
        FutureTask<Boolean> close = new FutureTask<Boolean>(new Callable<Boolean>() {
            @Override public Boolean call() throws Exception {
                Parcel data = Parcel.obtain();
                Parcel reply = Parcel.obtain();
                try {
                    data.writeInterfaceToken("org.claritylink.android.IClarityLinkViewFrameSink");
                    data.writeInt(FrameIpcProtocol.VERSION);
                    writeIdentity(data, identity);
                    if (!sink.transact(FrameIpcProtocol.VIEW_CLOSE, data, reply, 0)) return Boolean.FALSE;
                    reply.readException();
                    return Boolean.valueOf(reply.readInt() != 0);
                } finally {
                    reply.recycle();
                    data.recycle();
                }
            }
        }) {
            @Override protected void done() {
                synchronized (pendingViewCloses) { pendingViewCloses.remove(sink); }
                boolean acknowledged = false;
                try { acknowledged = get().booleanValue() || !sink.isBinderAlive(); }
                catch (Exception ignored) { acknowledged = !sink.isBinderAlive(); }
                if (acknowledged) {
                    removeStreamRegistrationIfCurrent(state, identity);
                    finishPendingParentTeardown(identity.sessionId);
                } else if (attempt < MAX_VIEW_CLOSE_ATTEMPTS && authorityHandler != null) {
                    scheduleViewCloseRetry(state, sink, identity, attempt);
                } else if (sink.isBinderAlive()) {
                    Log.e(TAG, "IPC_VIEW_SINK_CLOSE_UNRESOLVED session_id=" + identity.sessionId +
                            " generation=" + identity.streamGeneration + " attempts=" + attempt +
                            " recovery=owner_or_sink_restart_required");
                }
            }
        };
        try {
            viewCloseExecutor.execute(close);
        } catch (RejectedExecutionException full) {
            synchronized (pendingViewCloses) { pendingViewCloses.remove(sink); }
            Log.w(TAG, "IPC_VIEW_SINK_CLOSE_REJECTED session_id=" + identity.sessionId +
                    " generation=" + identity.streamGeneration + " reason=bounded_executor_full");
            if (attempt < MAX_VIEW_CLOSE_ATTEMPTS) scheduleViewCloseRetry(state, sink, identity, attempt);
            return false;
        }
        if (!waitForResult) return true;
        try {
            boolean accepted = close.get(VIEW_CLOSE_TIMEOUT_MS, TimeUnit.MILLISECONDS).booleanValue();
            Log.i(TAG, "IPC_VIEW_SINK_CLOSE session_id=" + identity.sessionId +
                    " generation=" + identity.streamGeneration + " accepted=" + accepted +
                    " timeout_ms=" + VIEW_CLOSE_TIMEOUT_MS);
            return accepted;
        } catch (TimeoutException timeout) {
            Log.w(TAG, "IPC_VIEW_SINK_CLOSE_TIMEOUT session_id=" + identity.sessionId +
                    " generation=" + identity.streamGeneration + " resolution=retain_fenced_identity");
            return false;
        } catch (Exception failure) {
            boolean dead = !sink.isBinderAlive();
            Log.w(TAG, "IPC_VIEW_SINK_CLOSE_FAILED session_id=" + identity.sessionId +
                    " generation=" + identity.streamGeneration + " binder_dead=" + dead +
                    " type=" + failure.getClass().getSimpleName());
            return dead;
        }
    }

    private void scheduleViewCloseRetry(final StreamState state, final IBinder sink,
            final FrameStreamIdentity identity, final int attempt) {
        if (authorityHandler == null || attempt >= MAX_VIEW_CLOSE_ATTEMPTS) return;
        authorityHandler.postDelayed(new Runnable() {
            @Override public void run() {
                closeViewSink(state, sink, identity, attempt + 1, false);
            }
        }, VIEW_CLOSE_RETRY_DELAY_MS * attempt);
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
