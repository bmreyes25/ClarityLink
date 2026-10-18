package org.claritylink.android;

import android.app.Service;
import android.content.ComponentName;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Binder;
import android.os.IBinder;
import android.os.Parcel;
import android.os.Process;
import android.os.RemoteException;
import android.os.Bundle;
import android.util.Log;

import org.claritylink.renderer.DecodedFrame;

import java.nio.ByteBuffer;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Same-UID sibling process attack fixture for the isolated API17 lab only. */
public final class SameUidRegistrationAttackTestService extends Service {
    private static final String TAG = "ClarityLinkCLIMP03";
    private static final long WAIT_MS = 10000L;
    private volatile boolean started;
    private IBinder compositor;
    private IBinder ownerSink;
    private IBinder probeEndpoint;
    private IBinder producerEndpoint;
    private ServiceConnection compositorConnection;
    private ServiceConnection sinkConnection;
    private ServiceConnection probeConnection;
    private ServiceConnection producerConnection;

    @Override public IBinder onBind(Intent intent) { return null; }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (started) return START_NOT_STICKY;
        started = true;
        final FrameStreamIdentity owner = new FrameStreamIdentity(
                intent == null ? 0L : intent.getLongExtra("session_id", 0L),
                FrameStreamIdentity.TYPE110,
                intent == null ? 0L : intent.getLongExtra("owner_connection", 0L),
                intent == null ? 0L : intent.getLongExtra("owner_generation", 0L),
                FrameStreamIdentity.OUTPUT_PRIMARY_LAB);
        final FrameStreamIdentity child = new FrameStreamIdentity(owner.sessionId,
                FrameStreamIdentity.TYPE111,
                intent == null ? 0L : intent.getLongExtra("child_connection", 0L),
                intent == null ? 0L : intent.getLongExtra("child_generation", 0L),
                FrameStreamIdentity.OUTPUT_SECONDARY_VIEW);
        final boolean holdAfterAttack = intent != null && intent.getBooleanExtra("hold_after_attack", false);
        if (!owner.isValid() || !child.isValid() || owner.sessionId != child.sessionId) {
            fail("invalid_attack_identity");
            return START_NOT_STICKY;
        }
        final CountDownLatch connected = new CountDownLatch(4);
        compositorConnection = new ServiceConnection() {
            public void onServiceConnected(ComponentName name, IBinder service) {
                compositor = service; connected.countDown();
            }
            public void onServiceDisconnected(ComponentName name) { compositor = null; }
        };
        sinkConnection = new ServiceConnection() {
            public void onServiceConnected(ComponentName name, IBinder service) {
                ownerSink = service; connected.countDown();
            }
            public void onServiceDisconnected(ComponentName name) { ownerSink = null; }
        };
        probeConnection = new ServiceConnection() {
            public void onServiceConnected(ComponentName name, IBinder service) {
                probeEndpoint = service; connected.countDown();
            }
            public void onServiceDisconnected(ComponentName name) { probeEndpoint = null; }
        };
        producerConnection = new ServiceConnection() {
            public void onServiceConnected(ComponentName name, IBinder service) {
                producerEndpoint = service; connected.countDown();
            }
            public void onServiceDisconnected(ComponentName name) { producerEndpoint = null; }
        };
        Intent compositorIntent = new Intent(this, CompositorService.class);
        Intent sinkIntent = new Intent(this, FrameLabSinkService.class);
        Intent probeIntent = new Intent(this, Type110ProgressProbeService.class);
        Intent producerIntent = new Intent(this, Type111ProducerService.class);
        sinkIntent.putExtra(FrameLabSinkService.EXTRA_SESSION_ID, owner.sessionId);
        if (!bindService(compositorIntent, compositorConnection, BIND_AUTO_CREATE) ||
                !bindService(sinkIntent, sinkConnection, BIND_AUTO_CREATE) ||
                !bindService(producerIntent, producerConnection, BIND_AUTO_CREATE)) {
            fail("attack_dependency_bind_failed");
            return START_NOT_STICKY;
        }
        if (!bindService(probeIntent, probeConnection, BIND_AUTO_CREATE)) {
            fail("probe_authority_bind_failed");
            return START_NOT_STICKY;
        }
        new Thread(new Runnable() {
            public void run() {
                try {
                    if (!connected.await(WAIT_MS, TimeUnit.MILLISECONDS) || compositor == null ||
                            ownerSink == null || probeEndpoint == null || producerEndpoint == null)
                        throw new IllegalStateException("attack_dependency_timeout");
                    executeAttackMatrix(owner, child);
                } catch (Throwable failure) {
                    fail(failure.getClass().getSimpleName() + ":" + String.valueOf(failure.getMessage()));
                } finally {
                    if (holdAfterAttack) awaitCrossUidRunnerRelease(owner.sessionId);
                    if (compositorConnection != null) try { unbindService(compositorConnection); }
                    catch (IllegalArgumentException ignored) { }
                    if (sinkConnection != null) try { unbindService(sinkConnection); }
                    catch (IllegalArgumentException ignored) { }
                    if (probeConnection != null) try { unbindService(probeConnection); }
                    catch (IllegalArgumentException ignored) { }
                    if (producerConnection != null) try { unbindService(producerConnection); }
                    catch (IllegalArgumentException ignored) { }
                    stopSelf();
                }
            }
        }, "ClarityLinkSameUidRegistrationAttacker").start();
        return START_NOT_STICKY;
    }

    private void awaitCrossUidRunnerRelease(long sessionId) {
        java.io.File release = new java.io.File(getFilesDir(),
                "cl-r4b-cross-uid-release-" + sessionId);
        long deadline = android.os.SystemClock.elapsedRealtime() + WAIT_MS * 12L;
        while (!release.exists() && android.os.SystemClock.elapsedRealtime() < deadline) {
            try { Thread.sleep(25L); }
            catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); return; }
        }
        if (!release.exists()) Log.e(TAG, "CL_R4B_CROSS_UID_ATTACK_GATE_TIMEOUT session_id=" + sessionId);
    }

    private void executeAttackMatrix(FrameStreamIdentity owner, FrameStreamIdentity child) throws Exception {
        Type111ControlClient control = new Type111ControlClient(compositor);
        Type111ControlClient.StreamQuery before = control.queryType111Stream(owner);
        Type111ControlClient.FrameStats ownerBefore = control.queryFrameStats(owner);
        Type111ControlClient.FrameStats childBefore = control.queryFrameStats(child);
        FrameLabSink.Stats sinkBefore = FrameLabSink.queryStats(ownerSink);
        FrameStreamIdentity sinkIdentityBefore = FrameLabSink.queryIdentity(ownerSink);
        if (before == null || !before.ownerValid || !before.sinkAttached || !child.equals(before.identity) ||
                ownerBefore == null || !ownerBefore.registered || childBefore == null ||
                !childBefore.registered || sinkBefore == null || !owner.equals(sinkIdentityBefore))
            throw new IllegalStateException("authorized_before_state_missing");
        ProducerState producerBefore = queryProducer();
        if (producerBefore.pid <= 0) throw new IllegalStateException("producer_not_live_before_attack");

        Parcel probeData = Parcel.obtain();
        Parcel probeReply = Parcel.obtain();
        boolean probeAuthorizationAccepted;
        try {
            writeIdentity(probeData, owner);
            writeIdentity(probeData, child);
            probeData.writeLong(sinkBefore.frameId);
            probeData.writeInt(sinkBefore.pid);
            if (!probeEndpoint.transact(FrameIpcProtocol.TYPE110_PROBE_AUTHORIZE,
                    probeData, probeReply, 0)) throw new IllegalStateException("probe_authorize_transaction_missing");
            probeReply.readException();
            probeAuthorizationAccepted = probeReply.readInt() != 0;
        } finally { probeData.recycle(); probeReply.recycle(); }

        boolean authority = FrameIpcClient.openParentAuthority(compositor, owner, ownerSink);
        boolean directSinkMutationDenied = rawSinkGenerationMutationDenied(ownerSink, owner,
                owner.streamGeneration + 1L);
        long forgedSessionId = owner.sessionId ^ 0x5a5a5a5a5a5a5a5aL;
        if (forgedSessionId <= 0L || forgedSessionId == owner.sessionId) forgedSessionId = owner.sessionId + 1L;
        IBinder unauthorizedAdmission = FrameIpcClient.requestType110SinkAdmission(
                compositor, forgedSessionId);
        boolean invalidOwner = FrameIpcClient.openParentAuthority(compositor,
                owner.withGeneration(owner.streamGeneration + 1L), ownerSink);
        boolean capability = control.registerLabCapability(owner,
                "same-uid-forged-capability", 800, 480, 30);
        boolean duplicateOwner = rawBegin(owner, ownerSink);
        boolean duplicateChild = rawBegin(child, new Binder());
        boolean wrongSession = rawBegin(new FrameStreamIdentity(owner.sessionId + 1L,
                FrameStreamIdentity.TYPE111, child.connectionId + 1L, child.streamGeneration,
                FrameStreamIdentity.OUTPUT_SECONDARY_VIEW));
        boolean wrongType = rawBegin(new FrameStreamIdentity(owner.sessionId, 109,
                child.connectionId + 1L, child.streamGeneration, FrameStreamIdentity.OUTPUT_SECONDARY_VIEW));
        boolean wrongConnection = rawBegin(new FrameStreamIdentity(child.sessionId, child.streamType,
                child.connectionId + 1L, child.streamGeneration, child.outputId));
        boolean wrongOutput = rawBegin(new FrameStreamIdentity(child.sessionId, child.streamType,
                child.connectionId + 1L, child.streamGeneration, FrameStreamIdentity.OUTPUT_PRIMARY_LAB));
        boolean warningChange = rawWarning(child, true);
        boolean oldGeneration = rawBegin(child.withGeneration(Math.max(1L, child.streamGeneration - 1L)));
        boolean futureGeneration = rawBegin(child.withGeneration(child.streamGeneration + 1L));
        boolean oldSinkReplacement = FrameIpcClient.replaceType111Sink(compositor, owner, child,
                child.withGeneration(child.streamGeneration + 1L), new Binder());
        boolean teardown = control.parentTeardown(owner);
        boolean end = rawEnd(owner);
        boolean producerStart = rawProducerStart(owner, child, childBefore.lastFrameId + 1L);
        boolean producerStop = rawProducerStop();
        boolean transferArm = rawBarrier(FrameIpcProtocol.LAB_ARM_TRANSFER_BARRIER, child, null);
        boolean transferWait = rawBarrier(FrameIpcProtocol.LAB_WAIT_TRANSFER_BARRIER, child, null);
        boolean transferFinishedWait = rawBarrier(FrameIpcProtocol.LAB_WAIT_TRANSFER_FINISHED, child, null);
        boolean transferRelease = rawBarrier(FrameIpcProtocol.LAB_RELEASE_TRANSFER_BARRIER, child, null);
        boolean teardownArm = rawBarrier(FrameIpcProtocol.LAB_ARM_PARENT_TEARDOWN_BARRIER, owner, null);
        boolean teardownWait = rawBarrier(FrameIpcProtocol.LAB_WAIT_PARENT_TEARDOWN_BARRIER, owner, null);
        boolean teardownContenderWait = rawBarrier(FrameIpcProtocol.LAB_WAIT_PARENT_TEARDOWN_CONTENDER, owner, null);
        boolean teardownRelease = rawBarrier(FrameIpcProtocol.LAB_RELEASE_PARENT_TEARDOWN_BARRIER, owner, null);
        boolean delayedArm = rawBarrier(FrameIpcProtocol.LAB_ARM_DELAYED_SINK_DEATH_CALLBACK, child, null);
        boolean delayedFire = rawBarrier(FrameIpcProtocol.LAB_FIRE_DELAYED_SINK_DEATH_CALLBACK, owner, child);
        final boolean[] frameAccepted = new boolean[] { true };
        final String[] frameReason = new String[] { "callback_missing" };
        FrameIpcClient frameClient = FrameIpcClient.attachExistingType111(
                compositor, child, childBefore.lastFrameId + 1L);
        if (frameClient == null) throw new IllegalStateException("attack_frame_client_missing");
        DecodedFrame frame = new DecodedFrame(2, 2, 8, System.nanoTime(), 0,
                0, 0, 2, 2, ByteBuffer.wrap(new byte[] {
                (byte) 0xff, 0, 0, (byte) 0xff, (byte) 0xff, 0, 0, (byte) 0xff,
                (byte) 0xff, 0, 0, (byte) 0xff, (byte) 0xff, 0, 0, (byte) 0xff }));
        if (!frameClient.submit(frame, child.streamGeneration, new FrameIpcClient.Callback() {
            public void complete(boolean accepted, String reason) {
                frameAccepted[0] = accepted; frameReason[0] = reason; frameDone.countDown();
            }
        })) throw new IllegalStateException("attack_frame_submit_not_started");
        if (!frameDone.await(WAIT_MS, TimeUnit.MILLISECONDS))
            throw new IllegalStateException("attack_frame_completion_timeout");

        Type111ControlClient.StreamQuery after = control.queryType111Stream(owner);
        Type111ControlClient.FrameStats ownerAfter = control.queryFrameStats(owner);
        Type111ControlClient.FrameStats childAfter = control.queryFrameStats(child);
        FrameLabSink.Stats sinkAfter = FrameLabSink.queryStats(ownerSink);
        FrameStreamIdentity sinkIdentityAfter = FrameLabSink.queryIdentity(ownerSink);
        ProducerState producerAfter = queryProducer();
        if (probeAuthorizationAccepted || authority || unauthorizedAdmission != null || !directSinkMutationDenied || invalidOwner || capability || duplicateOwner ||
                duplicateChild || wrongSession || wrongType || wrongConnection || wrongOutput ||
                oldGeneration || futureGeneration || oldSinkReplacement || warningChange || teardown || end ||
                producerStart || producerStop || producerAfter.pid != producerBefore.pid ||
                producerAfter.running != producerBefore.running || producerAfter.completed != producerBefore.completed ||
                transferArm || transferWait || transferFinishedWait || transferRelease || teardownArm ||
                teardownWait || teardownContenderWait || teardownRelease || delayedArm || delayedFire ||
                frameAccepted[0] || !"frame_caller_not_authorized".equals(frameReason[0]) ||
                after == null || !after.ownerValid || !after.sinkAttached || !child.equals(after.identity) ||
                !same(ownerBefore, ownerAfter) || !same(childBefore, childAfter) ||
                sinkAfter == null || sinkBefore.frames != sinkAfter.frames ||
                sinkBefore.frameId != sinkAfter.frameId || sinkBefore.checksum != sinkAfter.checksum ||
                !owner.equals(sinkIdentityAfter))
            throw new IllegalStateException("same_uid_attack_mutated_authorized_state");
        Log.i(TAG, "CL_R4B_SAME_UID_REGISTRATION_ATTACK_PASS caller_uid=" + Process.myUid() +
                " caller_pid=" + Process.myPid() + " owner_pid=" + before.compositorPid +
                " session_id=" + owner.sessionId + " authority_open_rejected=true invalid_owner_rejected=true " +
                "capability_rejected=true wrong_session_rejected=true wrong_stream_type_rejected=true " +
                "ownerless_sink_admission_rejected=true forged_session_id=" + forgedSessionId + " " +
                "wrong_connection_rejected=true wrong_output_rejected=true old_generation_rejected=true " +
                "unauthorized_warning_change_rejected=true " +
                "future_generation_rejected=true old_sink_replacement_rejected=true " +
                "duplicate_type110_rejected=true duplicate_type111_rejected=true teardown_rejected=true " +
                "probe_authorization_rejected=true unauthorized_type110_end_rejected=true " +
                "direct_type110_sink_generation_mutation_rejected=true " +
                "producer_start_rejected=true producer_terminate_rejected=true producer_pid_before=" +
                producerBefore.pid + " producer_pid_after=" + producerAfter.pid +
                " test_barrier_arm_wait_release_rejected=true delayed_callback_arm_fire_rejected=true" +
                " frame_rejected=true reason=" + frameReason[0] +
                " before_after_state_equal=true " +
                "authorized_owner_and_generations_preserved=true");
    }

    private boolean rawSinkGenerationMutationDenied(IBinder sink, FrameStreamIdentity identity,
            long nextGeneration) throws RemoteException {
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken("org.claritylink.android.IClarityLinkViewFrameSink");
            data.writeInt(FrameIpcProtocol.VERSION);
            writeIdentity(data, identity);
            data.writeLong(nextGeneration);
            if (!sink.transact(FrameIpcProtocol.VIEW_CHANGE_GENERATION, data, reply, 0)) return false;
            try { reply.readException(); }
            catch (SecurityException denied) { return true; }
            return false;
        } finally { reply.recycle(); data.recycle(); }
    }

    /** Sends raw malformed identity fields so Binder and the compositor perform validation. */
    private boolean rawBegin(FrameStreamIdentity identity) throws RemoteException {
        return rawBegin(identity, new Binder());
    }

    private boolean rawEnd(FrameStreamIdentity identity) throws RemoteException {
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeInt(FrameIpcProtocol.VERSION); writeIdentity(data, identity);
            if (!compositor.transact(FrameIpcProtocol.END, data, reply, 0))
                throw new IllegalStateException("raw_end_transaction_missing");
            reply.readException(); return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    private boolean rawWarning(FrameStreamIdentity identity, boolean visible) throws RemoteException {
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeInt(FrameIpcProtocol.VERSION); writeIdentity(data, identity);
            data.writeInt(visible ? 1 : 0);
            if (!compositor.transact(FrameIpcProtocol.WARNING, data, reply, 0)) return false;
            reply.readException(); return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    private boolean rawBarrier(int code, FrameStreamIdentity first, FrameStreamIdentity second)
            throws RemoteException {
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeInt(FrameIpcProtocol.VERSION); writeIdentity(data, first);
            if (code == FrameIpcProtocol.LAB_FIRE_DELAYED_SINK_DEATH_CALLBACK)
                writeIdentity(data, second);
            if (code == FrameIpcProtocol.LAB_WAIT_TRANSFER_BARRIER ||
                    code == FrameIpcProtocol.LAB_WAIT_TRANSFER_FINISHED ||
                    code == FrameIpcProtocol.LAB_WAIT_PARENT_TEARDOWN_BARRIER ||
                    code == FrameIpcProtocol.LAB_WAIT_PARENT_TEARDOWN_CONTENDER)
                data.writeLong(1L);
            if (!compositor.transact(code, data, reply, 0))
                throw new IllegalStateException("test_barrier_transaction_missing_" + code);
            reply.readException(); return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    private boolean rawProducerStart(FrameStreamIdentity owner, FrameStreamIdentity child, long frameId)
            throws RemoteException {
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken("org.claritylink.android.IType111LabProducer");
            data.writeStrongBinder(compositor); data.writeStrongBinder(ownerSink); writeIdentity(data, child);
            data.writeLong(Math.max(1L, frameId)); data.writeLong(12000000L);
            if (!producerEndpoint.transact(IBinder.FIRST_CALL_TRANSACTION, data, reply, 0)) return false;
            reply.readException(); return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    private boolean rawProducerStop() throws RemoteException {
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken("org.claritylink.android.IType111LabProducer");
            if (!producerEndpoint.transact(IBinder.FIRST_CALL_TRANSACTION + 1, data, reply, 0)) return false;
            reply.readException(); return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    private ProducerState queryProducer() throws RemoteException {
        Parcel data = Parcel.obtain(), reply = Parcel.obtain();
        try {
            data.writeInterfaceToken("org.claritylink.android.IType111LabProducer");
            if (!producerEndpoint.transact(IBinder.FIRST_CALL_TRANSACTION + 2, data, reply, 0))
                throw new IllegalStateException("producer_query_missing");
            reply.readException();
            ProducerState state = new ProducerState();
            state.pid = reply.readInt(); state.running = reply.readInt() != 0;
            state.completed = reply.readInt() != 0;
            int count = reply.readInt();
            if (count < 0 || count > 4) throw new IllegalStateException("producer_count_invalid");
            for (int i = 0; i < count; i++) reply.readLong();
            return state;
        } finally { reply.recycle(); data.recycle(); }
    }

    private static final class ProducerState { int pid; boolean running; boolean completed; }

    private boolean rawBegin(FrameStreamIdentity identity, IBinder sink) throws RemoteException {
        Parcel data = Parcel.obtain();
        Parcel reply = Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeInt(FrameIpcProtocol.VERSION);
            data.writeLong(identity.sessionId); data.writeInt(identity.streamType);
            data.writeLong(identity.connectionId); data.writeLong(identity.streamGeneration);
            data.writeInt(identity.outputId); data.writeStrongBinder(sink);
            if (!compositor.transact(FrameIpcProtocol.BEGIN, data, reply, 0))
                throw new IllegalStateException("raw_begin_transaction_missing");
            reply.readException();
            return reply.readInt() != 0;
        } finally { reply.recycle(); data.recycle(); }
    }

    private static void writeIdentity(Parcel data, FrameStreamIdentity identity) {
        data.writeLong(identity.sessionId); data.writeInt(identity.streamType);
        data.writeLong(identity.connectionId); data.writeLong(identity.streamGeneration);
        data.writeInt(identity.outputId);
    }

    private boolean same(Type111ControlClient.FrameStats left, Type111ControlClient.FrameStats right) {
        return left != null && right != null && left.registered == right.registered &&
                left.activePfdTransfers == right.activePfdTransfers &&
                left.retainedFrameBytes == right.retainedFrameBytes &&
                left.transferActive == right.transferActive && left.lastFrameId == right.lastFrameId;
    }

    private final CountDownLatch frameDone = new CountDownLatch(1);

    private void fail(String reason) {
        Log.e(TAG, "CL_R4B_SAME_UID_REGISTRATION_ATTACK_FAIL caller_uid=" + Process.myUid() +
                " caller_pid=" + Process.myPid() + " reason=" + reason);
        stopSelf();
    }
}
