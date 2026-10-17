package org.claritylink.android;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.test.InstrumentationTestCase;

/** Same-UID test launch; scenario extras select test behavior, not authorization. */
public final class Test4ProbeLaunchTest extends InstrumentationTestCase {
    public void testLaunchPrivateProbeActivity() {
        Intent intent = new Intent(getInstrumentation().getTargetContext(),
                Test4WindowAdmissionActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        Bundle arguments = Test4ProbeInstrumentationRunner.arguments();
        if (arguments != null) {
            if (arguments.containsKey("mode")) intent.putExtra("mode", arguments.getString("mode"));
            if (arguments.containsKey("confirm")) intent.putExtra("confirm", arguments.getString("confirm"));
        }
        Activity activity = getInstrumentation().startActivitySync(intent);
        assertNotNull("probe Activity launched by instrumentation", activity);
    }
}
