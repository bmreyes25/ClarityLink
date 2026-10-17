package org.claritylink.attacker;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.Bundle;
import android.os.IBinder;
import android.os.Process;
import android.util.Log;

/** Separate-UID adversary used only by the isolated API17 security test. */
public final class ExportBoundaryAttackActivity extends Activity {
    private static final String TAG = "ClarityLinkCLIMP03";
    private static final String TARGET = "org.claritylink.independentdisplay.lab";
    private int denied = 0;
    private int attempted = 0;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        int appUid;
        try { appUid = getPackageManager().getApplicationInfo(TARGET, 0).uid; }
        catch (Exception missingTarget) {
            Log.e(TAG, "CL_R4_CROSS_UID_ATTACK_FAIL reason=target_package_missing", missingTarget);
            finish();
            return;
        }
        Log.i(TAG, "ATTACKER_UID uid=" + Process.myUid() + " target_uid=" + appUid);
        if (Process.myUid() == appUid) {
            Log.e(TAG, "CL_R4_CROSS_UID_ATTACK_FAIL reason=uid_not_distinct");
            finish();
            return;
        }

        for (int attack = 0; attack < 7; attack++) attemptProbe(attack);
        attemptLabActivity("ClarityLinkDisplayActivity");
        attemptLabActivity("Api17DecoderLabActivity");
        attemptLabActivity("Type110OwnerIsolationTestActivity");
        attemptPrivateService("FrameLabSinkService");
        attemptPrivateService("CompositorService");
        attemptPrivateService("Type111ProducerService");
        if (attempted == 19 && denied == attempted) {
            Log.i(TAG, "CL_R4_CROSS_UID_ATTACKS_PASS uid=" + Process.myUid() +
                    " target_uid=" + appUid + " attempts=" + attempted + " denied=" + denied);
        } else {
            Log.e(TAG, "CL_R4_CROSS_UID_ATTACK_FAIL uid=" + Process.myUid() +
                    " target_uid=" + appUid + " attempts=" + attempted + " denied=" + denied);
        }
        finish();
    }

    private void attemptLabActivity(String simpleName) {
        attempted++;
        Intent forged = new Intent().setComponent(new ComponentName(TARGET,
                "org.claritylink.android." + simpleName));
        forged.putExtra("mode", "EMULATOR_PRESENTATION");
        forged.putExtra("emulator_only_confirmation", "CL_IMP_03_OFFLINE_EMULATOR_ONLY");
        forged.putExtra("crash_after_first_frame", true);
        forged.putExtra("type111_fixture_mode", true);
        try {
            startActivity(forged);
            Log.e(TAG, "ATTACK_NOT_DENIED operation=start_activity component=" + simpleName);
        } catch (SecurityException expected) {
            denied++;
            Log.i(TAG, "ATTACK_DENIED operation=start_activity component=" + simpleName);
        }
    }

    private void attemptProbe(int variant) {
        attempted++;
        Intent forged = new Intent().setComponent(new ComponentName(TARGET,
                "org.claritylink.android.Type110ProgressProbeService"));
        long session = getIntent().getLongExtra("attack_session_id", 1L);
        long generation = getIntent().getLongExtra("attack_generation", 1L);
        forged.putExtra("probe_session_id", variant == 1 ? session + 900000L : session);
        forged.putExtra("probe_stream_generation", variant == 2 ? generation + 900000L : generation);
        forged.putExtra("probe_last_frame_id", getIntent().getLongExtra("attack_last_frame", 0L) + 1L + variant);
        forged.putExtra("probe_type110_sink_pid", getIntent().getIntExtra("attack_sink_pid", 1));
        forged.putExtra("probe_output_id", variant == 6 ? 2 : 1);
        forged.putExtra("probe_stream_type", variant == 5 ? 111 : 110);
        forged.putExtra("probe_connection_id", variant == 5 ? 999999L : 11001L);
        forged.putExtra("probe_operation", variant == 3 ? "parent_teardown" : "submit_frame");
        forged.putExtra("emulator_only_confirmation", "CL_IMP_03_OFFLINE_EMULATOR_ONLY");
        try {
            startService(forged);
            Log.e(TAG, "ATTACK_NOT_DENIED operation=probe variant=" + variant);
        } catch (SecurityException expected) {
            denied++;
            Log.i(TAG, "ATTACK_DENIED operation=probe variant=" + variant);
        }
    }

    private void attemptPrivateService(String simpleName) {
        attempted++;
        Intent target = new Intent().setComponent(new ComponentName(TARGET,
                "org.claritylink.android." + simpleName));
        boolean stopped = false;
        try { stopped = stopService(target); }
        catch (SecurityException expected) { /* private service boundary */ }
        if (stopped) {
            Log.e(TAG, "ATTACK_NOT_DENIED operation=stop_service component=" + simpleName);
            return;
        }
        denied++;
        attempted++;
        try {
            ServiceConnection connection = new ServiceConnection() {
                public void onServiceConnected(ComponentName name, IBinder service) {
                    Log.e(TAG, "ATTACK_NOT_DENIED operation=bind_service component=" + name);
                    try { unbindService(this); } catch (IllegalArgumentException ignored) { }
                }
                public void onServiceDisconnected(ComponentName name) { }
            };
            boolean bound = bindService(target, connection, BIND_AUTO_CREATE);
            if (bound) {
                Log.e(TAG, "ATTACK_NOT_DENIED operation=bind_service component=" + simpleName);
                try { unbindService(connection); } catch (IllegalArgumentException ignored) { }
            } else denied++;
        } catch (SecurityException expected) { denied++; }
        attempted++;
        try {
            startService(target);
            Log.e(TAG, "ATTACK_NOT_DENIED operation=start_service component=" + simpleName);
        } catch (SecurityException expected) {
            denied++;
            Log.i(TAG, "ATTACK_DENIED operation=service component=" + simpleName);
        }
    }
}
