package org.claritylink.renderer;

public final class NavigationUpdateTest {
    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }

    private static void rejects(Runnable action, String message) {
        try { action.run(); }
        catch (IllegalArgumentException expected) { return; }
        throw new AssertionError(message);
    }

    public static void main(String[] args) {
        NavigationUpdate update = new NavigationUpdate(12, 4, 7, "sharp-left", 250.5,
                "meters", new String("Main Street"));
        require(update.sessionId == 12 && update.generation == 4 && update.sequence == 7,
                "session and ordering identity preserved");
        require(update.maneuver == NavigationUpdate.Maneuver.SHARP_LEFT,
                "known maneuver canonicalized");
        require(update.unit == NavigationUpdate.DistanceUnit.METERS && update.distance == 250.5,
                "distance and unit preserved");
        require(update.roadName.equals("Main Street"), "road name snapshot preserved");
        try {
            java.lang.reflect.Method submit = StructuredNavigationSink.class
                    .getDeclaredMethod("submit", NavigationUpdate.class);
            require(submit.getParameterTypes()[0] != DecodedFrame.class,
                    "semantic navigation sink is distinct from decoded video");
        } catch (NoSuchMethodException missing) {
            throw new AssertionError("structured sink must expose the navigation update type");
        }
        require(new NavigationUpdate(1, 1, 1, "future maneuver", 0, "mi", "").maneuver
                == NavigationUpdate.Maneuver.UNKNOWN, "unknown maneuver maps to UNKNOWN");
        rejects(new Runnable() { public void run() {
            new NavigationUpdate(-1, 1, 1, "left", 1, "m", "");
        } }, "negative session rejected");
        rejects(new Runnable() { public void run() {
            new NavigationUpdate(1, -1, 1, "left", 1, "m", "");
        } }, "negative generation rejected");
        rejects(new Runnable() { public void run() {
            new NavigationUpdate(1, 1, -1, "left", 1, "m", "");
        } }, "negative sequence rejected");
        rejects(new Runnable() { public void run() {
            new NavigationUpdate(1, 1, 1, "left", Double.NaN, "m", "");
        } }, "NaN distance rejected");
        rejects(new Runnable() { public void run() {
            new NavigationUpdate(1, 1, 1, "left", 1, "yards", "");
        } }, "unknown unit rejected");
        rejects(new Runnable() { public void run() {
            new NavigationUpdate(1, 1, 1, "left", 1, "m", repeat('x', 257));
        } }, "oversized road name rejected");
        NavigationGenerationLedger ledger = new NavigationGenerationLedger();
        require(ledger.advanceTo(4) && !ledger.advanceTo(4) && !ledger.advanceTo(3)
                && ledger.advanceTo(5), "generation high-water is strictly monotonic");
        System.out.println("NAVIGATION_UPDATE_CONTRACT_PASS validation=strict unknown=UNKNOWN ownership=immutable");
    }

    private static String repeat(char value, int count) {
        StringBuilder result = new StringBuilder(count);
        for (int i = 0; i < count; i++) result.append(value);
        return result.toString();
    }
}
