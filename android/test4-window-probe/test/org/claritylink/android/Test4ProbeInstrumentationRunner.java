package org.claritylink.android;

import android.os.Bundle;
import android.test.InstrumentationTestRunner;

/** Carries scenario selectors into the in-package test; they are not credentials. */
public final class Test4ProbeInstrumentationRunner extends InstrumentationTestRunner {
    private static Bundle arguments;

    @Override public void onCreate(Bundle values) {
        synchronized (Test4ProbeInstrumentationRunner.class) {
            arguments = values == null ? new Bundle() : new Bundle(values);
        }
        super.onCreate(values);
    }

    static Bundle arguments() {
        synchronized (Test4ProbeInstrumentationRunner.class) {
            return arguments == null ? new Bundle() : new Bundle(arguments);
        }
    }
}
