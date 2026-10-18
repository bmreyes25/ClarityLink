package org.claritylink.android;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.os.Process;
import android.util.Log;
import android.os.Handler;
import android.os.Looper;

/** Started, separate-process Type110 laboratory sink that survives Type111 View-process death. */
public final class FrameLabSinkService extends Service {
    static final String EXTRA_SESSION_ID = "type110_session_id";
    static final String EXTRA_ADMISSION = "type110_sink_admission";
    private static final String TAG = "ClarityLinkCLIMP03";
    private FrameLabSink sink;
    private long sessionId;
    private final Handler admissionHandler = new Handler(Looper.getMainLooper());

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        long requestedSession = intent == null ? 0L : intent.getLongExtra(EXTRA_SESSION_ID, 0L);
        FrameLabSinkAdmission admission = intent == null ? null :
                (FrameLabSinkAdmission) intent.getParcelableExtra(EXTRA_ADMISSION);
        boolean admitted = admission != null && admission.sessionId == requestedSession &&
                consumeAdmission(admission.grant, requestedSession);
        if (!admitted && !(sink != null && sessionId == requestedSession)) {
            Log.e(TAG, "TYPE110_LAB_SINK_START_REJECTED reason=admission_required session_id=" +
                    requestedSession);
            stopSelf(startId);
            return START_NOT_STICKY;
        }
        if (!ensureSink(requestedSession)) {
            Log.e(TAG, "TYPE110_LAB_SINK_START_REJECTED reason=invalid_session session_id=" +
                    requestedSession);
            stopSelf(startId);
            return START_NOT_STICKY;
        }
        if (admitted) watchUnboundAdmission(admission, requestedSession);
        return START_NOT_STICKY;
    }

    private void watchUnboundAdmission(FrameLabSinkAdmission admission, long requestedSession) {
        final FrameStreamIdentity expected;
        synchronized (this) { expected = sink == null ? null : sink.queryLocalIdentity(); }
        if (expected == null) return;
        final IBinder grant = admission.grant;
        final IBinder.DeathRecipient recipient = new IBinder.DeathRecipient() {
            public void binderDied() {
                admissionHandler.post(new Runnable() {
                    public void run() { clearUnboundAdmission(expected, "compositor_process_death"); }
                });
            }
        };
        try { grant.linkToDeath(recipient, 0); }
        catch (android.os.RemoteException deadGrant) {
            clearUnboundAdmission(expected, "compositor_already_dead");
            return;
        }
        admissionHandler.postDelayed(new Runnable() {
            public void run() { clearUnboundAdmission(expected, "parent_authority_open_timeout"); }
        }, 30000L);
    }

    private synchronized void clearUnboundAdmission(FrameStreamIdentity expected, String cause) {
        if (sink != null && sink.clearIfUnbound(expected, cause)) {
            sessionId = 0L;
        }
    }

    @Override public synchronized IBinder onBind(Intent intent) {
        long requestedSession = intent == null ? 0L : intent.getLongExtra(EXTRA_SESSION_ID, 0L);
        if (sink != null && sessionId == requestedSession) return sink;
        FrameLabSinkAdmission admission = intent == null ? null :
                (FrameLabSinkAdmission) intent.getParcelableExtra(EXTRA_ADMISSION);
        if (admission == null || admission.sessionId != requestedSession ||
                !consumeAdmission(admission.grant, requestedSession) || !ensureSink(requestedSession)) {
            Log.e(TAG, "TYPE110_LAB_SINK_BIND_REJECTED reason=admission_required session_id=" +
                    requestedSession);
            return null;
        }
        watchUnboundAdmission(admission, requestedSession);
        return sink;
    }

    private boolean consumeAdmission(IBinder admission, long requestedSession) {
        if (admission == null || requestedSession <= 0L || !admission.isBinderAlive()) return false;
        android.os.Parcel data = android.os.Parcel.obtain(), reply = android.os.Parcel.obtain();
        try {
            data.writeInterfaceToken(FrameIpcProtocol.DESCRIPTOR);
            data.writeLong(requestedSession);
            admission.transact(FrameIpcProtocol.TYPE110_SINK_ADMISSION_CONSUME, data, reply, 0);
            reply.readException();
            return reply.readInt() != 0;
        } catch (android.os.RemoteException | RuntimeException rejected) {
            return false;
        } finally { reply.recycle(); data.recycle(); }
    }

    private synchronized boolean ensureSink(long requestedSession) {
        if (sink != null) {
            if (sessionId > 0L && requestedSession == sessionId) return true;
            // A compositor death revokes the old owner Binder's identity. A different
            // parent session may then receive a fresh sink Binder; the retired Binder
            // remains unusable by clients that still hold its reference.
            long previousSessionId = sessionId;
            FrameStreamIdentity previous = null;
            try { previous = FrameLabSink.queryIdentity(sink); }
            catch (android.os.RemoteException unavailable) { }
            if (requestedSession <= 0L || previous != null) return false;
            sessionId = requestedSession;
            FrameStreamIdentity next = new FrameStreamIdentity(sessionId,
                    FrameStreamIdentity.TYPE110, 11001L, sessionId,
                    FrameStreamIdentity.OUTPUT_PRIMARY_LAB);
            sink = new FrameLabSink(this, next);
            Log.i(TAG, "TYPE110_LAB_SINK_REPLACED_AFTER_OWNER_LOSS pid=" + Process.myPid() +
                    " old_session_id=" + previousSessionId + " session_id=" + sessionId);
            return true;
        }
        if (requestedSession <= 0L) return false;
        if (sink == null) {
            sessionId = requestedSession;
            FrameStreamIdentity identity = new FrameStreamIdentity(sessionId,
                    FrameStreamIdentity.TYPE110, 11001L, sessionId,
                    FrameStreamIdentity.OUTPUT_PRIMARY_LAB);
            sink = new FrameLabSink(this, identity);
            Log.i(TAG, "TYPE110_LAB_SINK_READY pid=" + Process.myPid() + " uid=" + Process.myUid() +
                    " component=FrameLabSinkService process=:type110_sink session_id=" + sessionId);
        }
        return true;
    }

    @Override public void onDestroy() {
        Log.i(TAG, "TYPE110_LAB_SINK_DESTROYED pid=" + Process.myPid() + " session_id=" + sessionId +
                " frames=" + (sink == null ? 0 : sink.renderedFrames()) +
                " last_frame_id=" + (sink == null ? 0 : sink.lastFrameId()));
        super.onDestroy();
    }
}
