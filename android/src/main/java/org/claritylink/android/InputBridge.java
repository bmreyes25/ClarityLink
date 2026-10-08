package org.claritylink.android;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

/** Events require an explicit per-deployment allowlist; unknown keys are diagnostic only. */
public final class InputBridge {
    public enum Kind { TOUCH, KEY, ROTARY, STEERING, VOICE }
    public static final class Event {
        public final int source, code, value; public final Kind kind; public final long timestamp, generation;
        public Event(int source,Kind kind,int code,int value,long timestamp,long generation) {
            this.source=source; this.kind=kind; this.code=code; this.value=value; this.timestamp=timestamp; this.generation=generation;
        }
    }
    private final Set<String> allow;
    public InputBridge(Set<String> allowlist) { allow=Collections.unmodifiableSet(new HashSet<String>(allowlist)); }
    public boolean accept(Event event,long activeGeneration) {
        if (event == null || activeGeneration <= 0 || event.generation != activeGeneration || event.timestamp < 0) return false;
        return allow.contains(event.kind.name()+":"+event.source+":"+event.code);
    }
    public static InputBridge unavailableHondaDefault() { return new InputBridge(Collections.<String>emptySet()); }
}
