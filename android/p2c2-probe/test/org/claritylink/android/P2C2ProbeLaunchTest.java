package org.claritylink.android;

import android.app.Activity;
import android.content.Intent;
import android.test.InstrumentationTestCase;

/** Launches the private probe as its own UID; external Activities cannot invoke it. */
public final class P2C2ProbeLaunchTest extends InstrumentationTestCase {
    public void testLaunchPrivateProbeActivity() {
        Intent intent = new Intent(getInstrumentation().getTargetContext(),
                P2C2AdmissionProbeActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        Activity activity = getInstrumentation().startActivitySync(intent);
        assertNotNull("probe Activity launched by instrumentation", activity);
    }
}
