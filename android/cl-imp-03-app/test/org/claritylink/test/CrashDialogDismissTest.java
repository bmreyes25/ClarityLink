package org.claritylink.test;

import com.android.uiautomator.core.UiObject;
import com.android.uiautomator.core.UiSelector;
import com.android.uiautomator.testrunner.UiAutomatorTestCase;

/** Dismisses only the positively identified API17 ClarityLink crash dialog. */
public final class CrashDialogDismissTest extends UiAutomatorTestCase {
    private static final String MESSAGE =
            "Unfortunately, ClarityLink Display Lab has stopped.";

    public void testDismissExactClarityLinkCrashDialog() throws Exception {
        UiObject message = new UiObject(new UiSelector().text(MESSAGE));
        assertTrue("ClarityLink crash message is not visible", message.waitForExists(5000L));
        UiObject close = new UiObject(new UiSelector()
                .className("android.widget.Button").text("OK"));
        assertTrue("the verified crash dialog has no OK action", close.waitForExists(2000L));
        close.click();
        assertTrue("ClarityLink crash dialog remained visible",
                message.waitUntilGone(10000L));
    }
}
