package org.claritylink.renderer;

/** Immutable semantic navigation message. It is deliberately not a video frame. */
public final class NavigationUpdate {
    public enum Maneuver { UNKNOWN, STRAIGHT, SLIGHT_LEFT, LEFT, SHARP_LEFT,
        SLIGHT_RIGHT, RIGHT, SHARP_RIGHT, U_TURN, ROUNDABOUT, ARRIVE }
    public enum DistanceUnit { METERS, KILOMETERS, FEET, MILES }

    public final long sessionId;
    public final long generation;
    public final long sequence;
    public final Maneuver maneuver;
    public final double distance;
    public final DistanceUnit unit;
    public final String roadName;

    /** Unrecognized maneuver names are retained as UNKNOWN; other malformed input is rejected. */
    public NavigationUpdate(long sessionId, long generation, long sequence,
            String maneuver, double distance, String unit, String roadName) {
        if (sessionId < 0 || generation < 0 || sequence < 0)
            throw new IllegalArgumentException("session, generation, and sequence must be non-negative");
        if (Double.isNaN(distance) || Double.isInfinite(distance) || distance < 0.0d)
            throw new IllegalArgumentException("distance must be finite and non-negative");
        if (maneuver == null || unit == null || roadName == null)
            throw new IllegalArgumentException("maneuver, unit, and road name are required");
        if (roadName.length() > 256)
            throw new IllegalArgumentException("road name exceeds 256 characters");
        this.sessionId = sessionId;
        this.generation = generation;
        this.sequence = sequence;
        this.maneuver = parseManeuver(maneuver);
        this.distance = distance;
        this.unit = parseUnit(unit);
        this.roadName = new String(roadName);
    }

    private static Maneuver parseManeuver(String value) {
        String key = value.trim().toUpperCase(java.util.Locale.US).replace('-', '_').replace(' ', '_');
        try { return Maneuver.valueOf(key); }
        catch (IllegalArgumentException unknown) { return Maneuver.UNKNOWN; }
    }

    private static DistanceUnit parseUnit(String value) {
        String key = value.trim().toUpperCase(java.util.Locale.US);
        if ("M".equals(key) || "METER".equals(key) || "METERS".equals(key)) return DistanceUnit.METERS;
        if ("KM".equals(key) || "KILOMETER".equals(key) || "KILOMETERS".equals(key)) return DistanceUnit.KILOMETERS;
        if ("FT".equals(key) || "FOOT".equals(key) || "FEET".equals(key)) return DistanceUnit.FEET;
        if ("MI".equals(key) || "MILE".equals(key) || "MILES".equals(key)) return DistanceUnit.MILES;
        throw new IllegalArgumentException("unknown distance unit");
    }
}
