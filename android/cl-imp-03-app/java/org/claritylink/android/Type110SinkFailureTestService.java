package org.claritylink.android;

import android.app.ActivityManager;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.os.Process;
import android.util.Log;

import java.util.List;

/** Privileged, non-UI emulator fault injector for the separate Type110 lab sink. */
public final class Type110SinkFailureTestService extends Service {
    private static final String TAG = "ClarityLinkCLIMP03";
    private static final String PROCESS_SUFFIX = ":type110_sink";
    private static final String CONFIRMATION = "CL_R4B_OFFLINE_EMULATOR_ONLY";

    @Override public IBinder onBind(Intent intent) { return null; }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (!isEmulator() || intent == null ||
                !CONFIRMATION.equals(intent.getStringExtra("confirmation"))) {
            Log.e(TAG, "CL_R4B_TYPE110_SINK_FAILURE_REJECTED reason=emulator_guard");
            stopSelf(startId);
            return START_NOT_STICKY;
        }
        int targetPid = intent.getIntExtra("target_pid", -1);
        long targetSession = intent.getLongExtra("target_session_id", 0L);
        if (targetSession <= 0L || targetPid <= 0 || targetPid == Process.myPid() ||
                !isOwnedSinkProcess(targetPid)) {
            Log.e(TAG, "CL_R4B_TYPE110_SINK_FAILURE_REJECTED reason=pid_identity pid=" + targetPid);
            stopSelf(startId);
            return START_NOT_STICKY;
        }
        Log.i(TAG, "CL_R4B_TYPE110_SINK_FAILURE_TARGET_VERIFIED pid=" + targetPid +
                " uid=" + Process.myUid() + " session_id=" + targetSession +
                " process=" + getPackageName() + PROCESS_SUFFIX);
        if (!isOwnedSinkProcess(targetPid)) {
            Log.e(TAG, "CL_R4B_TYPE110_SINK_FAILURE_REJECTED reason=pid_changed pid=" + targetPid);
            stopSelf(startId);
            return START_NOT_STICKY;
        }
        Process.killProcess(targetPid);
        Log.i(TAG, "CL_R4B_TYPE110_SINK_FAILURE_REQUESTED pid=" + targetPid);
        stopSelf(startId);
        return START_NOT_STICKY;
    }

    private boolean isOwnedSinkProcess(int pid) {
        ActivityManager manager = (ActivityManager) getSystemService(ACTIVITY_SERVICE);
        List<ActivityManager.RunningAppProcessInfo> processes =
                manager == null ? null : manager.getRunningAppProcesses();
        if (processes == null) return false;
        for (ActivityManager.RunningAppProcessInfo process : processes) {
            if (process.pid == pid && Process.myUid() == process.uid &&
                    (getPackageName() + PROCESS_SUFFIX).equals(process.processName)) return true;
        }
        return false;
    }

    private static boolean isEmulator() {
        String hardware = Build.HARDWARE == null ? "" : Build.HARDWARE.toLowerCase();
        String fingerprint = Build.FINGERPRINT == null ? "" : Build.FINGERPRINT.toLowerCase();
        return hardware.contains("goldfish") || hardware.contains("ranchu") ||
                fingerprint.startsWith("generic") || fingerprint.contains("emulator");
    }
}
