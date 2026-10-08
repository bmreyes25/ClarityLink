package org.claritylink.android;

import android.app.Activity;
import android.os.Bundle;
import android.util.Log;

/** Minimal identity-only launch used before the emulator runs any receiver test. */
public final class R7C6SmokeActivity extends Activity {
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        Log.i("ClarityLinkR7C6", "R7C6_SMOKE_PASS api=" + android.os.Build.VERSION.SDK_INT +
                " release=" + android.os.Build.VERSION.RELEASE +
                " abi=" + android.os.Build.CPU_ABI +
                " runtime=" + System.getProperty("java.vm.name"));
        finish();
    }
}
