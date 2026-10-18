package org.claritylink.attacker;

import android.app.Service;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.IBinder;
import android.os.Process;
import android.util.Log;

/** Non-foreground separate-UID attacker; avoids pausing the receiver under test. */
public final class ExportBoundaryAttackService extends Service {
    private static final String TAG = "ClarityLinkCLIMP03";
    private static final String TARGET = "org.claritylink.independentdisplay.lab";
    private int denied;
    private int unverifiedNoEffect;
    private int notDenied;
    private int attempted;

    @Override public IBinder onBind(Intent intent) { return null; }

    @Override public int onStartCommand(final Intent intent, int flags, final int startId) {
        Thread attack = new Thread(new Runnable() {
            public void run() { execute(intent, startId); }
        }, "ClarityLinkCrossUidAttack");
        attack.start();
        return START_NOT_STICKY;
    }

    private void execute(Intent intent, int startId) {
        int appUid;
        try { appUid = getPackageManager().getApplicationInfo(TARGET, 0).uid; }
        catch (Exception missingTarget) {
            Log.e(TAG, "CL_R4_CROSS_UID_ATTACK_FAIL reason=target_package_missing", missingTarget);
            stopSelf(startId);
            return;
        }
        Log.i(TAG, "ATTACKER_UID uid=" + Process.myUid() + " target_uid=" + appUid +
                " caller=background_service");
        if (Process.myUid() == appUid) {
            Log.e(TAG, "CL_R4_CROSS_UID_ATTACK_FAIL reason=uid_not_distinct");
            stopSelf(startId);
            return;
        }
        for (int attack = 0; attack < 7; attack++) attemptProbe(attack, intent);
        attemptLabActivity("ClarityLinkDisplayActivity");
        attemptLabActivity("Api17DecoderLabActivity");
        attemptLabActivity("Type110OwnerIsolationTestActivity");
        attemptPrivateService("FrameLabSinkService", intent);
        attemptPrivateService("CompositorService", intent);
        attemptPrivateService("Type111ProducerService", intent);
        attemptPrivateService("Type110SinkFailureTestService", intent);
        attemptPrivateService("CompositorOwnerDeathTestService", intent);
        if (attempted == 23 && denied + unverifiedNoEffect == attempted && notDenied == 0) {
            Log.i(TAG, "CL_R4_CROSS_UID_ATTACKS_COMPLETE uid=" + Process.myUid() +
                    " target_uid=" + appUid + " attempts=" + attempted +
                    " explicit_denials=" + denied + " unverified_no_effect=" + unverifiedNoEffect +
                    " caller=background_service");
        } else {
            Log.e(TAG, "CL_R4_CROSS_UID_ATTACK_FAIL uid=" + Process.myUid() +
                    " target_uid=" + appUid + " attempts=" + attempted + " explicit_denials=" + denied +
                    " unverified_no_effect=" + unverifiedNoEffect + " not_denied=" + notDenied);
        }
        stopSelf(startId);
    }

    private void attemptLabActivity(String simpleName) {
        attempted++;
        Intent forged = new Intent().setComponent(new ComponentName(TARGET,
                "org.claritylink.android." + simpleName));
        forged.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        forged.putExtra("mode", "EMULATOR_PRESENTATION");
        forged.putExtra("emulator_only_confirmation", "CL_IMP_03_OFFLINE_EMULATOR_ONLY");
        forged.putExtra("crash_after_first_frame", true);
        forged.putExtra("type111_fixture_mode", true);
        try {
            startActivity(forged);
            Log.e(TAG, "ATTACK_NOT_DENIED operation=start_activity component=" + simpleName);
            notDenied++;
        } catch (SecurityException expected) {
            denied++;
            Log.i(TAG, "ATTACK_DENIED operation=start_activity component=" + simpleName);
        }
    }

    private void attemptProbe(int variant, Intent request) {
        attempted++;
        Intent forged = new Intent().setComponent(new ComponentName(TARGET,
                "org.claritylink.android.Type110ProgressProbeService"));
        long session = request.getLongExtra("attack_session_id", 1L);
        long generation = request.getLongExtra("attack_generation", 1L);
        forged.putExtra("probe_session_id", variant == 1 ? session + 900000L : session);
        forged.putExtra("probe_stream_generation", variant == 2 ? generation + 900000L : generation);
        forged.putExtra("probe_last_frame_id", request.getLongExtra("attack_last_frame", 0L) + 1L + variant);
        forged.putExtra("probe_type110_sink_pid", request.getIntExtra("attack_sink_pid", 1));
        forged.putExtra("probe_output_id", variant == 6 ? 2 : 1);
        forged.putExtra("probe_stream_type", variant == 5 ? 111 : 110);
        forged.putExtra("probe_connection_id", variant == 5 ? 999999L : 11001L);
        forged.putExtra("probe_operation", variant == 3 ? "parent_teardown" : "submit_frame");
        forged.putExtra("emulator_only_confirmation", "CL_IMP_03_OFFLINE_EMULATOR_ONLY");
        try {
            startService(forged);
            Log.e(TAG, "ATTACK_NOT_DENIED operation=probe variant=" + variant);
            notDenied++;
        } catch (SecurityException expected) {
            denied++;
            Log.i(TAG, "ATTACK_DENIED operation=probe variant=" + variant);
        }
    }

    private void attemptPrivateService(String simpleName, Intent request) {
        boolean destructiveHelper = "Type110SinkFailureTestService".equals(simpleName) ||
                "CompositorOwnerDeathTestService".equals(simpleName);
        Intent target = new Intent().setComponent(new ComponentName(TARGET,
                "org.claritylink.android." + simpleName));
        if (destructiveHelper) {
            target.putExtra("confirmation", "CL_R4B_OFFLINE_EMULATOR_ONLY");
            String pidKey = "CompositorOwnerDeathTestService".equals(simpleName) ?
                    "attack_compositor_pid" : "attack_sink_pid";
            target.putExtra("target_pid", request.getIntExtra(pidKey, 1));
            target.putExtra("target_session_id", request.getLongExtra("attack_session_id", 1L));
            target.putExtra("session_id", request.getLongExtra("attack_session_id", 1L));
            target.putExtra("type110_connection_id", 11001L);
            target.putExtra("type110_generation", request.getLongExtra("attack_generation", 1L));
            target.putExtra("type110_last_frame_id", request.getLongExtra("attack_last_frame", 1L));
            target.putExtra("type111_connection_id", 11101L);
            target.putExtra("type111_generation", request.getLongExtra("attack_generation", 1L) + 1L);
        }
        if (!destructiveHelper) {
            attempted++;
            boolean stopped = false;
            boolean stopDenied = false;
            try { stopped = stopService(target); }
            catch (SecurityException expected) {
                denied++;
                stopDenied = true;
                Log.i(TAG, "ATTACK_DENIED operation=stop_service component=" + simpleName);
            }
            if (stopped) {
                Log.e(TAG, "ATTACK_NOT_DENIED operation=stop_service component=" + simpleName);
                notDenied++;
                return;
            }
            if (!stopDenied) {
                unverifiedNoEffect++;
                Log.w(TAG, "ATTACK_UNVERIFIED operation=stop_service result=false component=" + simpleName);
            }
        }
        attempted++;
        final boolean strictBindDenial = destructiveHelper;
        try {
            ServiceConnection connection = new ServiceConnection() {
                public void onServiceConnected(ComponentName name, IBinder service) {
                    Log.e(TAG, "ATTACK_NOT_DENIED operation=bind_service component=" + name);
                    try { unbindService(this); } catch (IllegalArgumentException ignored) { }
                }
                public void onServiceDisconnected(ComponentName name) { }
            };
            boolean bound = bindService(target, connection, Context.BIND_AUTO_CREATE);
            if (bound) {
                Log.e(TAG, "ATTACK_NOT_DENIED operation=bind_service component=" + simpleName);
                notDenied++;
                try { unbindService(connection); } catch (IllegalArgumentException ignored) { }
            } else if (strictBindDenial) {
                Log.e(TAG, "ATTACK_UNVERIFIED operation=bind_service component=" + simpleName);
                unverifiedNoEffect++;
            } else {
                Log.w(TAG, "ATTACK_UNVERIFIED operation=bind_service result=false component=" + simpleName);
                unverifiedNoEffect++;
            }
        } catch (SecurityException expected) {
            denied++;
            Log.i(TAG, "ATTACK_DENIED operation=bind_service component=" + simpleName);
        }
        attempted++;
        try {
            startService(target);
            Log.e(TAG, "ATTACK_NOT_DENIED operation=start_service component=" + simpleName);
            notDenied++;
        } catch (SecurityException expected) {
            denied++;
            Log.i(TAG, "ATTACK_DENIED operation=service component=" + simpleName);
        }
    }
}
