package org.claritylink.android;

import android.app.ActivityManager;
import android.app.Service;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Handler;
import android.os.IBinder;
import android.os.Process;
import android.os.Build;
import android.os.Binder;
import android.os.SystemClock;
import android.util.Log;

import org.claritylink.renderer.DecodedFrame;

import java.nio.ByteBuffer;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Explicit API17 lab fault injector for the separate compositor-owner process. */
public final class CompositorOwnerDeathTestService extends Service {
    private static final String TAG = "ClarityLinkCLIMP03";
    private static final String CONFIRMATION = "CL_R4B_OFFLINE_EMULATOR_ONLY";
    private final Handler handler = new Handler();
    private final Object lifecycleLock = new Object();
    private final IBinder ownerDeathQueryToken = new Binder();
    private volatile IBinder endpoint;
    private volatile boolean ownerDeathRequested;
    private volatile boolean endpointDisconnected;
    private volatile boolean ownerDeathObserved;
    private volatile boolean finished;
    private boolean observerRebindStarted;
    private boolean endpointVerificationStarted;
    private boolean started;
    private int targetPid;
    private FrameStreamIdentity ownerIdentity;
    private FrameStreamIdentity childIdentity;
    private long oldOwnerLastFrame;
    private ServiceConnection connection;

    @Override public IBinder onBind(Intent intent) { return ownerDeathQueryToken; }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (started) return START_NOT_STICKY;
        started = true;
        if (intent == null || Build.VERSION.SDK_INT != 17 || !isEmulator()) {
            fail("api17_emulator_guard_rejected");
            return START_NOT_STICKY;
        }
        targetPid = intent.getIntExtra("target_pid", -1);
        long sessionId = intent.getLongExtra("session_id", 0L);
        ownerIdentity = new FrameStreamIdentity(sessionId, FrameStreamIdentity.TYPE110,
                intent.getLongExtra("type110_connection_id", 0L),
                intent.getLongExtra("type110_generation", 0L),
                FrameStreamIdentity.OUTPUT_PRIMARY_LAB);
        childIdentity = new FrameStreamIdentity(sessionId, FrameStreamIdentity.TYPE111,
                intent.getLongExtra("type111_connection_id", 0L),
                intent.getLongExtra("type111_generation", 0L),
                FrameStreamIdentity.OUTPUT_SECONDARY_VIEW);
        oldOwnerLastFrame = intent.getLongExtra("type110_last_frame_id", 0L);
        if (!CONFIRMATION.equals(intent.getStringExtra("confirmation")) || targetPid <= 0 ||
                targetPid == Process.myPid() || !ownerIdentity.isValid() ||
                !childIdentity.isValid() || ownerIdentity.sessionId != childIdentity.sessionId ||
                oldOwnerLastFrame <= 0L || !isExactOwnedCompositorPid(targetPid)) {
            fail("guard_identity_or_process_rejected");
            return START_NOT_STICKY;
        }
        Log.i(TAG, "CL_R4B_OWNER_DEATH_TARGET_VERIFIED pid=" + targetPid +
                " process=" + getPackageName() + ":compositor uid=" + Process.myUid() +
                " session_id=" + sessionId);
        handler.postDelayed(new Runnable() {
            public void run() { if (!finished) fail("owner_death_observation_timeout"); }
        }, 900000L);
        bindOwnerObserver("observer_bind_failed");
        return START_NOT_STICKY;
    }

    /** API17 does not reliably reconnect a bound-only service after its process is killed. */
    private void bindOwnerObserver(final String failureReason) {
        final ServiceConnection observer;
        synchronized (lifecycleLock) {
            if (finished) return;
            endpointVerificationStarted = false;
            observer = new ServiceConnection() {
            public void onServiceConnected(ComponentName name, final IBinder service) {
                synchronized (lifecycleLock) {
                    // Ignore a late reconnect from the binding that reported owner death.
                    if (finished || connection != this || endpointDisconnected ||
                            endpointVerificationStarted) return;
                    endpointVerificationStarted = true;
                    endpoint = service;
                }
                new Thread(new Runnable() {
                    public void run() { onEndpointConnected(service); }
                }, "ClarityLinkOwnerDeathObserver").start();
            }
            public void onServiceDisconnected(ComponentName name) {
                final ServiceConnection deadConnection = this;
                synchronized (lifecycleLock) {
                    if (finished || connection != deadConnection) return;
                    endpoint = null;
                    endpointDisconnected = true;
                    ownerDeathObserved = true;
                    if (observerRebindStarted) return;
                    observerRebindStarted = true;
                }
                Log.i(TAG, "CL_R4B_OWNER_DEATH_BINDER_DISCONNECTED old_pid=" + targetPid +
                        " process=" + name.getClassName());
                handler.post(new Runnable() {
                    public void run() {
                        synchronized (lifecycleLock) {
                            if (finished || connection != deadConnection) return;
                            try { unbindService(deadConnection); }
                            catch (IllegalArgumentException ignored) { }
                            connection = null;
                            observerRebindStarted = false;
                            endpointDisconnected = false;
                        }
                        bindOwnerObserver("observer_rebind_failed_after_owner_death");
                    }
                });
            }
            };
            connection = observer;
            if (!bindService(new Intent(this, CompositorService.class), observer,
                    Context.BIND_AUTO_CREATE)) {
                connection = null;
            }
        }
        if (connection != observer) fail(failureReason);
        else Log.i(TAG, "CL_R4B_OWNER_DEATH_OBSERVER_BIND_STARTED rebind=" + observerRebindStarted);
    }

    private void onEndpointConnected(IBinder service) {
        try {
            Type111ControlClient control = new Type111ControlClient(service);
            Type111ControlClient.StreamQuery query = control.queryType111Stream(ownerIdentity);
            if (!ownerDeathRequested && (query == null || query.compositorPid <= 0)) {
                long grantDeadline = SystemClock.elapsedRealtime() + 10000L;
                while (!ownerDeathRequested && SystemClock.elapsedRealtime() < grantDeadline &&
                        (query == null || query.compositorPid <= 0)) {
                    Thread.sleep(50L);
                    query = control.queryType111Stream(ownerIdentity);
                }
            }
            if (query == null) throw new IllegalStateException("owner_query_missing");
            if (!ownerDeathRequested) {
                if (!query.authorized || query.compositorPid != targetPid || !query.ownerValid || query.identity == null ||
                        !childIdentity.equals(query.identity) || !query.sinkAttached)
                    throw new IllegalStateException("live_parent_precondition_mismatch");
                awaitPredeathResourceCleanup(control);
                ownerDeathRequested = true;
                Log.i(TAG, "CL_R4B_PARENT_OWNER_DEATH_REQUESTED pid=" + targetPid +
                        " observer_pid=" + Process.myPid() + " session_id=" + ownerIdentity.sessionId +
                        " streams=110,111 valid_frames_previously_observed=true");
                if (!service.isBinderAlive() || !isExactOwnedCompositorPid(targetPid))
                    throw new IllegalStateException("compositor_process_changed_before_kill");
                Process.killProcess(targetPid);
                return;
            }
            if (!ownerDeathObserved || query.authorized || query.compositorPid != 0 ||
                    query.ownerValid || query.identity != null || query.sinkAttached)
                throw new IllegalStateException("restarted_owner_retained_old_session");
            requireOldFrameRejected(service, ownerIdentity, oldOwnerLastFrame + 1L);
            requireOldFrameRejected(service, childIdentity, 1L);
            int freshCompositorPid = currentOwnedCompositorPid();
            if (freshCompositorPid <= 0 || freshCompositorPid == targetPid)
                throw new IllegalStateException("fresh_compositor_process_identity_missing");
            verifyFreshSessionRecovery(service, freshCompositorPid);
            Log.i(TAG, "CL_R4B_PARENT_OWNER_DEATH_PASS old_pid=" + targetPid +
                    " new_pid=" + freshCompositorPid + " session_id=" + ownerIdentity.sessionId +
                    " binder_disconnected=true owner_valid=false child_present=false " +
                    "stale_type110_frame_rejected=true stale_type111_frame_rejected=true " +
                    "predeath_pfd_transfers=0 predeath_retained_bytes=0 " +
                    "resource_state=not_observable_after_owner_death old_session_query_denied=true " +
                    "fresh_session_resources=zero");
            finishOnce();
        } catch (Throwable failure) {
            fail("observer_check_failed:" + failure.getClass().getSimpleName() + ":" +
                    String.valueOf(failure.getMessage()));
        }
    }

    private void awaitPredeathResourceCleanup(Type111ControlClient control) throws Exception {
        long deadline = SystemClock.elapsedRealtime() + 5000L;
        Type111ControlClient.FrameStats owner = null, child = null;
        while (SystemClock.elapsedRealtime() < deadline) {
            owner = control.queryFrameStats(ownerIdentity);
            child = control.queryFrameStats(childIdentity);
            if (owner == null || child == null || !owner.authorized || !child.authorized)
                throw new IllegalStateException("predeath_resource_query_unauthorized");
            if (owner.activePfdTransfers == 0 && child.activePfdTransfers == 0 &&
                    owner.retainedFrameBytes == 0 && child.retainedFrameBytes == 0 &&
                    !owner.transferActive && !child.transferActive) return;
            Thread.sleep(25L);
        }
        throw new IllegalStateException("predeath_resources_not_released owner_pfd=" +
                (owner == null ? -1 : owner.activePfdTransfers) + " child_pfd=" +
                (child == null ? -1 : child.activePfdTransfers) + " owner_bytes=" +
                (owner == null ? -1 : owner.retainedFrameBytes) + " child_bytes=" +
                (child == null ? -1 : child.retainedFrameBytes));
    }

    private int currentOwnedCompositorPid() {
        ActivityManager manager = (ActivityManager) getSystemService(ACTIVITY_SERVICE);
        if (manager == null) return 0;
        java.util.List<ActivityManager.RunningAppProcessInfo> processes =
                manager.getRunningAppProcesses();
        if (processes == null) return 0;
        String expected = getPackageName() + ":compositor";
        for (ActivityManager.RunningAppProcessInfo process : processes)
            if (process.uid == Process.myUid() && expected.equals(process.processName)) return process.pid;
        return 0;
    }

    /** Replays old identities against the new owner, then registers and tears down a fresh session. */
    private void verifyFreshSessionRecovery(IBinder service, int compositorPid) throws Exception {
        FrameIpcClient staleOwner = new FrameIpcClient(service);
        if (staleOwner.begin(ownerIdentity, new Binder()) > 0)
            throw new IllegalStateException("old_type110_identity_re_registered_after_owner_restart");
        Type111ControlClient control = new Type111ControlClient(service);
        if (control.registerLabCapability(ownerIdentity, "stale-owner-replay",
                800, 480, 30))
            throw new IllegalStateException("old_session_capability_re_registered_after_owner_restart");

        verifySessionAdmissionBeyondPreviousTombstoneLimit(service, control, compositorPid);

        long newSessionId = SystemClock.elapsedRealtimeNanos();
        if (newSessionId <= 0L || newSessionId == ownerIdentity.sessionId)
            newSessionId = (System.nanoTime() & Long.MAX_VALUE);
        FrameStreamIdentity newOwner = new FrameStreamIdentity(newSessionId,
                FrameStreamIdentity.TYPE110, 21001L, newSessionId,
                FrameStreamIdentity.OUTPUT_PRIMARY_LAB);
        FrameStreamIdentity newChild = new FrameStreamIdentity(newSessionId,
                FrameStreamIdentity.TYPE111, 21101L, newSessionId,
                FrameStreamIdentity.OUTPUT_SECONDARY_VIEW);
        FrameIpcClient newOwnerClient = new FrameIpcClient(service);
        FrameLabSink newOwnerSink = new FrameLabSink(this, newOwner);
        int registeredOwnerPid = newOwnerClient.begin(newOwner, newOwnerSink);
        if (registeredOwnerPid != compositorPid)
            throw new IllegalStateException("fresh_type110_session_registration_failed");
        if (!control.registerLabCapability(newOwner, "claritylink-owner-recovery", 800, 480, 30) ||
                !control.setup(newChild))
            throw new IllegalStateException("fresh_type111_setup_failed");
        FrameViewSink newSink = new FrameViewSink(handler, new FrameViewSink.Target() {
            public boolean enqueue(DecodedFrame frame, long generation, long frameId, long epoch) {
                return false;
            }
            public boolean setWarningVisible(long generation, boolean visible) { return true; }
            public boolean replaceGeneration(long oldGeneration, long nextGeneration) { return false; }
        });
        newSink.begin(newChild);
        FrameIpcClient newChildClient = new FrameIpcClient(service);
        if (newChildClient.begin(newChild, newSink) != compositorPid)
            throw new IllegalStateException("fresh_type111_stream_registration_failed");
        Type111ControlClient.StreamQuery fresh = control.queryType111Stream(newOwner);
        if (fresh == null || !fresh.ownerValid || !fresh.sinkAttached ||
                !newChild.equals(fresh.identity) || fresh.compositorPid != compositorPid)
            throw new IllegalStateException("fresh_dual_stream_state_not_observed");

        requireOldFrameRejected(service, ownerIdentity, oldOwnerLastFrame + 2L);
        requireOldFrameRejected(service, childIdentity, 2L);
        Type111ControlClient.StreamQuery unchanged = control.queryType111Stream(newOwner);
        if (unchanged == null || !newChild.equals(unchanged.identity) || !unchanged.sinkAttached)
            throw new IllegalStateException("old_identity_probe_changed_fresh_session");
        if (!control.parentTeardown(newOwner))
            throw new IllegalStateException("fresh_session_parent_teardown_failed");
        Type111ControlClient.FrameStats ownerStats = control.queryFrameStats(newOwner);
        Type111ControlClient.FrameStats childStats = control.queryFrameStats(newChild);
        Type111ControlClient.StreamQuery ended = control.queryType111Stream(newOwner);
        if (!zeroUnregistered(ownerStats) || !zeroUnregistered(childStats) || ended == null ||
                ended.ownerValid || ended.identity != null || ended.sinkAttached)
            throw new IllegalStateException("fresh_session_teardown_left_resources");
        newSink.close(newChild.streamGeneration);
        Log.i(TAG, "CL_R4B_OWNER_DEATH_FRESH_SESSION_RECOVERY_PASS old_session_id=" +
                ownerIdentity.sessionId + " new_session_id=" + newSessionId +
                " compositor_pid=" + compositorPid + " old_type110_registration_rejected=true " +
                "old_type111_capability_rejected=true fresh_type110_registered=true " +
                "fresh_type111_registered=true stale_frames_rejected=true " +
                "fresh_session_teardown=true registrations_after_teardown=0");
    }

    /** Ensures the exact recent-ID window can roll without replaying IDs or losing active sessions. */
    private void verifySessionAdmissionBeyondPreviousTombstoneLimit(IBinder service,
            Type111ControlClient control, int compositorPid) throws Exception {
        long pinnedSessionId = SystemClock.elapsedRealtimeNanos();
        FrameStreamIdentity pinnedIdentity = new FrameStreamIdentity(pinnedSessionId,
                FrameStreamIdentity.TYPE110, 32000L, pinnedSessionId,
                FrameStreamIdentity.OUTPUT_PRIMARY_LAB);
        FrameIpcClient pinnedClient = new FrameIpcClient(service);
        FrameLabSink pinnedSink = new FrameLabSink(this, pinnedIdentity);
        if (pinnedClient.begin(pinnedIdentity, pinnedSink) != compositorPid)
            throw new IllegalStateException("active_session_pin_setup_failed");
        for (int i = 0; i < 257; i++) {
            long sessionId = SystemClock.elapsedRealtimeNanos();
            FrameStreamIdentity identity = new FrameStreamIdentity(sessionId,
                    FrameStreamIdentity.TYPE110, 31000L + i, sessionId,
                    FrameStreamIdentity.OUTPUT_PRIMARY_LAB);
            FrameIpcClient client = new FrameIpcClient(service);
            FrameLabSink sink = new FrameLabSink(this, identity);
            if (sessionId <= 0L || client.begin(identity, sink) != compositorPid)
                throw new IllegalStateException("session_admission_capacity_regressed_at=" + i);
            client.end(sessionId);
            if (!zeroUnregistered(control.queryFrameStats(identity)))
                throw new IllegalStateException("session_capacity_trial_cleanup_failed_at=" + i);
            if (new FrameIpcClient(service).begin(identity, sink) == compositorPid)
                throw new IllegalStateException("revoked_owner_binder_reused_after_end_at=" + i);
            if (new FrameIpcClient(service).begin(identity,
                    new FrameLabSink(this, identity)) == compositorPid)
                throw new IllegalStateException("same_process_session_id_reused_after_end_at=" + i);
        }
        if (new FrameIpcClient(service).begin(ownerIdentity,
                new FrameLabSink(this, ownerIdentity)) == compositorPid ||
                control.registerLabCapability(ownerIdentity, "evicted-owner-replay", 800, 480, 30))
            throw new IllegalStateException("old_owner_session_replayed_after_256_id_window_eviction");
        if (!control.queryFrameStats(pinnedIdentity).registered)
            throw new IllegalStateException("active_session_evicted_from_replay_window");
        pinnedClient.end(pinnedSessionId);
        if (!zeroUnregistered(control.queryFrameStats(pinnedIdentity)) ||
                new FrameIpcClient(service).begin(pinnedIdentity, pinnedSink) == compositorPid)
            throw new IllegalStateException("pinned_owner_binder_reused_after_end");
        if (new FrameIpcClient(service).begin(pinnedIdentity,
                new FrameLabSink(this, pinnedIdentity)) == compositorPid)
            throw new IllegalStateException("active_session_replay_after_window_pressure");
        Log.i(TAG, "CL_R4B_OWNER_DEATH_SESSION_CAPACITY_PASS admitted_and_torn_down=257 " +
                "active_session_pinned=true replay_window=256 owner_replay_after_window_eviction_rejected=true " +
                "same_process_replay_rejected=true");
    }

    private void requireOldFrameRejected(IBinder service, FrameStreamIdentity identity,
            long frameId) throws Exception {
        FrameIpcClient client = identity.streamType == FrameStreamIdentity.TYPE110 ?
                FrameIpcClient.attachExistingType110(service, identity, frameId) :
                FrameIpcClient.attachExistingType111(service, identity, frameId);
        if (client == null) throw new IllegalStateException("stale_client_attach_unavailable");
        final CountDownLatch completed = new CountDownLatch(1);
        final boolean[] accepted = new boolean[] { true };
        final String[] reason = new String[] { "callback_missing" };
        DecodedFrame frame = new DecodedFrame(2, 2, 8, 3000000000L + frameId, 0,
                0, 0, 2, 2, ByteBuffer.wrap(new byte[] {
                (byte) 0xff, 0, 0, (byte) 0xff, (byte) 0xff, 0, 0, (byte) 0xff,
                (byte) 0xff, 0, 0, (byte) 0xff, (byte) 0xff, 0, 0, (byte) 0xff }));
        if (!client.submit(frame, identity.streamGeneration, new FrameIpcClient.Callback() {
            public void complete(boolean value, String why) {
                accepted[0] = value; reason[0] = why; completed.countDown();
            }
        })) throw new IllegalStateException("stale_frame_submit_not_started");
        if (!completed.await(8L, TimeUnit.SECONDS) || accepted[0] ||
                !("stream_identity_rejected".equals(reason[0]) ||
                "frame_caller_not_authorized".equals(reason[0])))
            throw new IllegalStateException("stale_frame_not_rejected:" + reason[0]);
    }

    private static boolean zeroUnregistered(Type111ControlClient.FrameStats stats) {
        return stats != null && stats.authorized && !stats.registered && stats.activePfdTransfers == 0 &&
                stats.retainedFrameBytes == 0 && !stats.transferActive && stats.lastFrameId == 0L;
    }

    private boolean isExactOwnedCompositorPid(int pid) {
        ActivityManager manager = (ActivityManager) getSystemService(ACTIVITY_SERVICE);
        List<ActivityManager.RunningAppProcessInfo> processes = manager == null ? null :
                manager.getRunningAppProcesses();
        if (processes == null) return false;
        String expected = getPackageName() + ":compositor";
        for (ActivityManager.RunningAppProcessInfo process : processes)
            if (process.pid == pid && process.uid == Process.myUid() && expected.equals(process.processName))
                return true;
        return false;
    }

    private static boolean isEmulator() {
        String hardware = Build.HARDWARE == null ? "" : Build.HARDWARE.toLowerCase();
        String fingerprint = Build.FINGERPRINT == null ? "" : Build.FINGERPRINT.toLowerCase();
        return hardware.contains("goldfish") || hardware.contains("ranchu") ||
                fingerprint.startsWith("generic") || fingerprint.contains("emulator");
    }

    private void fail(String reason) {
        Log.e(TAG, "CL_R4B_PARENT_OWNER_DEATH_FAIL reason=" + reason + " target_pid=" + targetPid);
        finishOnce();
    }

    private void finishOnce() {
        final ServiceConnection observer;
        synchronized (lifecycleLock) {
            if (finished) return;
            finished = true;
            observer = connection;
            connection = null;
        }
        handler.removeCallbacksAndMessages(null);
        if (observer != null) {
            try { unbindService(observer); } catch (IllegalArgumentException ignored) { }
        }
        stopSelf();
    }
}
