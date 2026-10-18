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
    private volatile IBinder endpoint;
    private volatile boolean ownerDeathRequested;
    private volatile boolean endpointDisconnected;
    private volatile boolean finished;
    private boolean started;
    private int targetPid;
    private FrameStreamIdentity ownerIdentity;
    private FrameStreamIdentity childIdentity;
    private long oldOwnerLastFrame;
    private ServiceConnection connection;

    @Override public IBinder onBind(Intent intent) { return null; }

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
        connection = new ServiceConnection() {
            public void onServiceConnected(ComponentName name, final IBinder service) {
                endpoint = service;
                new Thread(new Runnable() {
                    public void run() { onEndpointConnected(service); }
                }, "ClarityLinkOwnerDeathObserver").start();
            }
            public void onServiceDisconnected(ComponentName name) {
                endpoint = null;
                endpointDisconnected = true;
                Log.i(TAG, "CL_R4B_OWNER_DEATH_BINDER_DISCONNECTED old_pid=" + targetPid +
                        " process=" + name.getClassName());
            }
        };
        handler.postDelayed(new Runnable() {
            public void run() { if (!finished) fail("owner_death_observation_timeout"); }
        }, 30000L);
        if (!bindService(new Intent(this, CompositorService.class), connection,
                Context.BIND_AUTO_CREATE)) fail("observer_bind_failed");
        return START_NOT_STICKY;
    }

    private void onEndpointConnected(IBinder service) {
        try {
            Type111ControlClient control = new Type111ControlClient(service);
            Type111ControlClient.StreamQuery query = control.queryType111Stream(ownerIdentity);
            if (query == null) throw new IllegalStateException("owner_query_missing");
            if (!ownerDeathRequested) {
                if (query.compositorPid != targetPid || !query.ownerValid || query.identity == null ||
                        !childIdentity.equals(query.identity) || !query.sinkAttached)
                    throw new IllegalStateException("live_parent_precondition_mismatch");
                ownerDeathRequested = true;
                Log.i(TAG, "CL_R4B_PARENT_OWNER_DEATH_REQUESTED pid=" + targetPid +
                        " observer_pid=" + Process.myPid() + " session_id=" + ownerIdentity.sessionId +
                        " streams=110,111 valid_frames_previously_observed=true");
                if (!service.isBinderAlive() || !isExactOwnedCompositorPid(targetPid))
                    throw new IllegalStateException("compositor_process_changed_before_kill");
                Process.killProcess(targetPid);
                return;
            }
            if (!endpointDisconnected || query.compositorPid == targetPid || query.ownerValid ||
                    query.identity != null || query.sinkAttached)
                throw new IllegalStateException("restarted_owner_retained_old_session");
            Type111ControlClient.FrameStats type110 = control.queryFrameStats(ownerIdentity);
            Type111ControlClient.FrameStats type111 = control.queryFrameStats(childIdentity);
            if (!zeroUnregistered(type110) || !zeroUnregistered(type111))
                throw new IllegalStateException("stale_owner_resource_state_present");
            requireOldFrameRejected(service, ownerIdentity, oldOwnerLastFrame + 1L);
            requireOldFrameRejected(service, childIdentity, 1L);
            Log.i(TAG, "CL_R4B_PARENT_OWNER_DEATH_PASS old_pid=" + targetPid +
                    " new_pid=" + query.compositorPid + " session_id=" + ownerIdentity.sessionId +
                    " binder_disconnected=true owner_valid=false child_present=false " +
                    "stale_type110_frame_rejected=true stale_type111_frame_rejected=true " +
                    "registrations=0 pfd_transfers=0 retained_bytes=0 transfer_active=false " +
                    "last_frame_ids=0");
            finishOnce();
        } catch (Throwable failure) {
            fail("observer_check_failed:" + failure.getClass().getSimpleName() + ":" +
                    String.valueOf(failure.getMessage()));
        }
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
                !"stream_identity_rejected".equals(reason[0]))
            throw new IllegalStateException("stale_frame_not_rejected:" + reason[0]);
    }

    private static boolean zeroUnregistered(Type111ControlClient.FrameStats stats) {
        return stats != null && !stats.registered && stats.activePfdTransfers == 0 &&
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
        if (finished) return;
        finished = true;
        handler.removeCallbacksAndMessages(null);
        if (connection != null) {
            try { unbindService(connection); } catch (IllegalArgumentException ignored) { }
            connection = null;
        }
        stopSelf();
    }
}
