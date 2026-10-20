package org.claritylink.android;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/** Versioned capability facts require a source level. UNKNOWN never resolves to true. */
public final class CapabilityEvidence {
    public enum Level { DOCUMENTED_ANDROID, HONDA_STATIC, HONDA_READ_ONLY_OBSERVED,
        HONDA_PROTOTYPE_OBSERVED, UNKNOWN }
    public static final class Fact {
        public final String value, evidence;
        public final Level level;
        public Fact(String value,Level level,String evidence) {
            if(value==null || level==null || evidence==null) throw new IllegalArgumentException("complete evidence tuple required");
            this.value=value; this.level=level; this.evidence=evidence;
        }
        public boolean meets(Level minimum) { return minimum!=null && minimum!=Level.UNKNOWN &&
            level!=Level.UNKNOWN && level.ordinal()>=minimum.ordinal(); }
    }
    public final int version;
    private final Map<String,Fact> facts;
    public CapabilityEvidence(int version,Map<String,Fact> values) {
        if(version<1 || values==null) throw new IllegalArgumentException("versioned evidence required");
        this.version=version; facts=Collections.unmodifiableMap(new HashMap<String,Fact>(values));
    }
    public Fact get(String key) { return facts.get(key); }
    public boolean permits(String key,String requiredValue,Level minimumEvidence) {
        Fact fact=facts.get(key); return fact!=null && fact.meets(minimumEvidence) && requiredValue.equals(fact.value);
    }
}
