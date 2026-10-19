package org.claritylink.android;

import android.app.Service;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Build;
import android.os.Binder;
import android.os.IBinder;
import android.os.Parcel;
import android.os.Process;
import android.os.RemoteException;
import android.util.Base64;
import android.util.Log;

import org.claritylink.renderer.DecodedFrame;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** Private recovery producer started only by the compositor after Type111 Binder death. */
public final class Type110ProgressProbeService extends Service {
    private static final String TAG = "ClarityLinkCLIMP03";
    private volatile boolean bound;
    private volatile boolean finished;
    private boolean started;
    private boolean startCommandConsumed;
    private Type110LabProbeOwnership.Record ownership;

    private final IBinder authorizationBinder = new Binder() {
        @Override protected boolean onTransact(int code, Parcel data, Parcel reply, int flags)
                throws RemoteException {
            if (code != FrameIpcProtocol.TYPE110_PROBE_AUTHORIZE) return super.onTransact(code, data, reply, flags);
            FrameStreamIdentity ownerIdentity = readIdentity(data);
            FrameStreamIdentity expectedDeath = readIdentity(data);
            long lastFrameId = data.readLong();
            int sinkPid = data.readInt();
            int callerPid = Binder.getCallingPid();
            boolean compositorCaller = (getPackageName() + ":compositor").equals(processNameForPid(callerPid));
            Type110LabProbeOwnership.Record claimed = compositorCaller && ownerIdentity != null &&
                    ownerIdentity.isValid() && ownerIdentity.streamType == FrameStreamIdentity.TYPE110 &&
                    expectedDeath != null && expectedDeath.isValid() &&
                    expectedDeath.streamType == FrameStreamIdentity.TYPE111 &&
                    ownerIdentity.sessionId == expectedDeath.sessionId && lastFrameId > 0L && sinkPid > 0
                    ? new Type110LabProbeOwnership.Record(ownerIdentity, expectedDeath, lastFrameId, sinkPid)
                    : null;
            boolean grantIssued = claimed != null && Type110LabProbeOwnership
                    .issueTeardownGrantAuthorized(Type110ProgressProbeService.this, claimed);
            if (!grantIssued) claimed = null;
            boolean accepted = false;
            synchronized (Type110ProgressProbeService.this) {
                if (claimed != null && !started && !finished && claimed.sinkPid != Process.myPid()) {
                    ownership = claimed;
                    started = true;
                    accepted = true;
                }
            }
            reply.writeNoException();
            reply.writeInt(accepted ? 1 : 0);
            if (accepted) {
                Intent launch = new Intent(Type110ProgressProbeService.this,
                        Type110ProgressProbeService.class);
                if (startService(launch) == null) {
                    synchronized (Type110ProgressProbeService.this) {
                        ownership = null; started = false;
                    }
                    reply.setDataPosition(0);
                    reply.writeNoException(); reply.writeInt(0);
                    accepted = false;
                }
            }
            Log.i(TAG, "TYPE110_POST_DEATH_PROBE_AUTHORIZATION caller_pid=" + callerPid +
                    " caller_process=" + processNameForPid(callerPid) + " accepted=" + accepted +
                    " expected_type111_death=" + (claimed != null));
            return true;
        }
    };

    private final ServiceConnection compositorConnection = new ServiceConnection() {
        public void onServiceConnected(ComponentName name, final IBinder endpoint) {
            new Thread(new Runnable() {
                public void run() { executeProbe(endpoint, ownership); }
            }, "ClarityLinkType110DeathProbe").start();
        }
        public void onServiceDisconnected(ComponentName name) {
            Log.e(TAG, "CL_R4_TYPE110_AFTER_TYPE111_DEATH_FAIL reason=compositor_disconnected");
            complete();
        }
    };

    @Override public IBinder onBind(Intent intent) { return authorizationBinder; }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        Type110LabProbeOwnership.Record authorized;
        synchronized (this) {
            if (!started || startCommandConsumed || finished || ownership == null) {
                Log.w(TAG, "TYPE110_POST_DEATH_PROBE_UNAUTHORIZED_START_IGNORED start_id=" + startId);
                stopSelf(startId);
                return START_NOT_STICKY;
            }
            startCommandConsumed = true;
            authorized = ownership;
        }
        if (!isEmulator() || authorized.identity.sessionId <= 0L ||
                authorized.identity.streamGeneration <= 0L || authorized.sinkPid == Process.myPid()) {
            Log.e(TAG, "CL_R4_TYPE110_AFTER_TYPE111_DEATH_FAIL reason=lab_guard_or_identity_rejected");
            complete();
            return START_NOT_STICKY;
        }
        FrameStreamIdentity owner = authorized.identity;
        Log.i(TAG, "TYPE110_POST_DEATH_PROBE_READY pid=" + Process.myPid() + " uid=" +
                Process.myUid() + " session_id=" + owner.sessionId + " stream_generation=" +
                owner.streamGeneration + " last_frame_id=" + ownership.lastFrameId +
                " expected_type111_connection_id=" + authorized.expectedType111Death.connectionId +
                " expected_type111_generation=" + authorized.expectedType111Death.streamGeneration +
                " type110_sink_pid=" + ownership.sinkPid + " owner_record=consumed_once");
        bound = bindService(new Intent(this, CompositorService.class), compositorConnection,
                Context.BIND_AUTO_CREATE);
        if (!bound) {
            Log.e(TAG, "CL_R4_TYPE110_AFTER_TYPE111_DEATH_FAIL reason=bind_failed");
            complete();
        }
        return START_NOT_STICKY;
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

    private static FrameStreamIdentity readIdentity(Parcel data) {
        return new FrameStreamIdentity(data.readLong(), data.readInt(), data.readLong(),
                data.readLong(), data.readInt());
    }

    private void executeProbe(IBinder endpoint, Type110LabProbeOwnership.Record record) {
        if (record == null) {
            Log.e(TAG, "CL_R4_TYPE110_AFTER_TYPE111_DEATH_FAIL reason=owner_record_missing");
            complete();
            return;
        }
        FrameStreamIdentity owner = record.identity;
        long sessionId = owner.sessionId;
        long generation = owner.streamGeneration;
        long lastFrameId = record.lastFrameId;
        int sinkPid = record.sinkPid;
        Api17BufferH264Decoder decoder = null;
        try {
            FrameIpcClient client = FrameIpcClient.attachExistingType110(endpoint,
                    owner, lastFrameId + 1L);
            if (client == null) throw new IllegalStateException("existing_type110_stream_unavailable");

            byte[] fixture = readFixture("type110-red-32x32.h264.b64");
            byte[] config = Api17SurfaceH264Decoder.extractCodecConfig(fixture);
            byte[][] units = Api17SurfaceH264Decoder.extractVclFrames(fixture);
            if (units.length == 0 || (units[0][4] & 31) != 5)
                throw new IllegalStateException("type110_fixture_has_no_initial_idr");
            decoder = new Api17BufferH264Decoder(32, 32, 990001L, config);
            DecodedFrame frame = null;
            long firstTimestampUs = System.nanoTime() / 1000L + 1000L;
            for (int i = 0; i < 16 && frame == null; i++)
                frame = decoder.decode(units[i % units.length], firstTimestampUs + i * 100L,
                        990001L, 3000L);
            if (frame == null || frame.presentationTimeNs <= 1400000000L)
                throw new IllegalStateException("post_death_type110_decode_missing_or_stale");

            final CountDownLatch completed = new CountDownLatch(1);
            final boolean[] accepted = new boolean[] { false };
            final String[] reason = new String[] { "callback_missing" };
            if (!client.submit(frame, generation, new FrameIpcClient.Callback() {
                public void complete(boolean value, String why) {
                    accepted[0] = value; reason[0] = why; completed.countDown();
                }
            })) throw new IllegalStateException("type110_probe_submission_not_started");
            if (!completed.await(10L, TimeUnit.SECONDS) || !accepted[0])
                throw new IllegalStateException("type110_after_type111_death_rejected:" + reason[0]);

            Log.i(TAG, "CL_R4_TYPE110_AFTER_TYPE111_SINK_DEATH_PASS session_id=" + sessionId +
                    " stream_generation=" + generation + " old_last_frame_id=" + lastFrameId +
                    " decoder_generation=990001 timestamp_ns=" + frame.presentationTimeNs +
                    " type111_sink_dead=true type110_sink_pid=" + sinkPid +
                    " producer_pid=" + Process.myPid() + " accepted=true same_stream=true fixture_only=true");
            decoder.close(); decoder = null;

            if (!new Type111ControlClient(endpoint).parentTeardown(owner))
                throw new IllegalStateException("parent_session_teardown_rejected");
            Log.i(TAG, "CL_R4_PARENT_SESSION_TEARDOWN_PASS session_id=" + sessionId +
                    " type110_closed=true type111_closed=true");
            boolean sinkStopRequested = stopService(new Intent(this, FrameLabSinkService.class));
            boolean compositorStopRequested = stopService(new Intent(this, CompositorService.class));
            if (!sinkStopRequested || !compositorStopRequested)
                throw new IllegalStateException("owned_service_graceful_stop_not_accepted");
            Log.i(TAG, "CL_R4_OWNED_SERVICES_STOP_REQUESTED session_id=" + sessionId +
                    " sink=true compositor=true after_parent_teardown=true");
            complete();
        } catch (Throwable failure) {
            Log.e(TAG, "CL_R4_TYPE110_AFTER_TYPE111_DEATH_FAIL type=" +
                    failure.getClass().getSimpleName() + " message=" + failure.getMessage(), failure);
            complete();
        } finally {
            if (decoder != null) decoder.close();
        }
    }

    private byte[] readFixture(String name) throws Exception {
        InputStream input = getAssets().open(name);
        ByteArrayOutputStream encoded = new ByteArrayOutputStream();
        byte[] buffer = new byte[1024];
        int count;
        try {
            while ((count = input.read(buffer)) != -1) {
                if (encoded.size() + count > 16384) throw new IllegalStateException("fixture_size_limit");
                encoded.write(buffer, 0, count);
            }
        } finally { input.close(); }
        return Base64.decode(encoded.toByteArray(), Base64.DEFAULT);
    }

    private boolean isEmulator() {
        return "goldfish".equals(Build.HARDWARE) || Build.PRODUCT.contains("sdk") ||
                Build.FINGERPRINT.contains("generic");
    }

    private synchronized void complete() {
        if (finished) return;
        finished = true;
        if (bound) {
            try { unbindService(compositorConnection); } catch (IllegalArgumentException ignored) { }
            bound = false;
        }
        stopSelf();
    }
}
