package org.claritylink.android;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.os.Process;
import android.util.Log;

/** Started, separate-process Type110 laboratory sink that survives Type111 View-process death. */
public final class FrameLabSinkService extends Service {
    static final String EXTRA_SESSION_ID = "type110_session_id";
    private static final String TAG = "ClarityLinkCLIMP03";
    private FrameLabSink sink;
    private long sessionId;

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        long requestedSession = intent == null ? 0L : intent.getLongExtra(EXTRA_SESSION_ID, 0L);
        if (!ensureSink(requestedSession)) {
            Log.e(TAG, "TYPE110_LAB_SINK_START_REJECTED reason=missing_session");
            stopSelf(startId);
            return START_NOT_STICKY;
        }
        return START_NOT_STICKY;
    }

    @Override public IBinder onBind(Intent intent) {
        long requestedSession = intent == null ? 0L : intent.getLongExtra(EXTRA_SESSION_ID, 0L);
        return ensureSink(requestedSession) ? sink : null;
    }

    private synchronized boolean ensureSink(long requestedSession) {
        if (sink != null) return sessionId > 0L;
        if (requestedSession <= 0L) return false;
        if (sink == null) {
            sessionId = requestedSession;
            FrameStreamIdentity identity = new FrameStreamIdentity(sessionId,
                    FrameStreamIdentity.TYPE110, 11001L, sessionId,
                    FrameStreamIdentity.OUTPUT_PRIMARY_LAB);
            sink = new FrameLabSink(identity);
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
