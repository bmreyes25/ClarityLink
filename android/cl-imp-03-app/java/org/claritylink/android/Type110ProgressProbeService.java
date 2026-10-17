package org.claritylink.android;

import android.app.Service;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Build;
import android.os.IBinder;
import android.os.Process;
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
    private Type110LabProbeOwnership.Record ownership;

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

    @Override public IBinder onBind(Intent intent) { return null; }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        synchronized (this) {
            if (started || finished) {
                Log.i(TAG, "TYPE110_POST_DEATH_PROBE_DUPLICATE_START_IGNORED start_id=" + startId);
                return START_NOT_STICKY;
            }
            started = true;
        }
        FrameStreamIdentity expectedDeath = Type110LabProbeOwnership.expectedDeathFrom(intent);
        ownership = Type110LabProbeOwnership.consume(this, expectedDeath);
        if (!isEmulator() || ownership == null ||
                ownership.identity.sessionId <= 0L || ownership.identity.streamGeneration <= 0L ||
                ownership.sinkPid == Process.myPid()) {
            Log.e(TAG, "CL_R4_TYPE110_AFTER_TYPE111_DEATH_FAIL reason=lab_guard_or_identity_rejected");
            complete();
            return START_NOT_STICKY;
        }
        FrameStreamIdentity owner = ownership.identity;
        Log.i(TAG, "TYPE110_POST_DEATH_PROBE_READY pid=" + Process.myPid() + " uid=" +
                Process.myUid() + " session_id=" + owner.sessionId + " stream_generation=" +
                owner.streamGeneration + " last_frame_id=" + ownership.lastFrameId +
                " expected_type111_connection_id=" + expectedDeath.connectionId +
                " expected_type111_generation=" + expectedDeath.streamGeneration +
                " type110_sink_pid=" + ownership.sinkPid + " owner_record=consumed_once");
        bound = bindService(new Intent(this, CompositorService.class), compositorConnection,
                Context.BIND_AUTO_CREATE);
        if (!bound) {
            Log.e(TAG, "CL_R4_TYPE110_AFTER_TYPE111_DEATH_FAIL reason=bind_failed");
            complete();
        }
        return START_NOT_STICKY;
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
            for (int i = 0; i < 16 && frame == null; i++)
                frame = decoder.decode(units[i % units.length], 5000000L + i * 100000L,
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
