package org.claritylink.android;

/** Allowlisted sanitized health state; values must not contain credentials or device identities. */
public final class RuntimeDiagnostic {
    public enum State { PROCESS_READY, PRIMARY_SURFACE_READY, SECONDARY_DISPLAY_ENUMERATED,
        SECONDARY_PRESENTATION_CREATED, SECONDARY_SURFACE_READY, USB_READY, IAP2_READY,
        AUTHORITY_READY, CARPLAY_CONTROL_READY, TYPE110_ACTIVE, TYPE111_ACTIVE, AUDIO_READY, RESTORED }
    public enum Evidence { IMPLEMENTED_OFFLINE, DOCUMENTED_ANDROID, HONDA_STATIC,
        HONDA_READ_ONLY_OBSERVED, HONDA_PROTOTYPE_OBSERVED, UNKNOWN }
    public final State state; public final Evidence evidence; public final long generation;
    public RuntimeDiagnostic(State state,Evidence evidence,long generation) {
        if(state==null || evidence==null || generation<0) throw new IllegalArgumentException("invalid diagnostic tuple");
        this.state=state; this.evidence=evidence; this.generation=generation;
    }
    public String toSafeString() { return state.name()+" evidence="+evidence.name()+" generation="+generation; }
}
