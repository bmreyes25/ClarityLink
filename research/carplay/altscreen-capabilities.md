# AltScreen capability model

Evidence categories: **Apple documented** means WWDC19; **implementation** means xcertplay source at `3753867f0dd0e5c03490b987fb9df49b8ac96472`; **unknown** means no evidence sufficient to claim Honda compatibility.

| Field | Status | Evidence / caveat |
|---|---|---|
| distinct display UUID | implementation-observed | xcertplay uses separate `MAIN_UUID` and `ALT_UUID` in its `displays` array; exact values are receiver-chosen, not protocol constants |
| display type / stream type | implementation-observed | 110 main and 111 alt constants; Apple confirms streams, not numbers |
| width/height pixels | implementation-observed | configured per display in xcertplay model; exact values are receiver configuration |
| physical dimensions | implementation-observed / version-dependent | display profile fields are used in the modern receiver; legacy minimum unknown |
| maxFPS | implementation-observed / version-dependent | xcertplay configures it; legacy minimum unknown |
| features / `altScreen` | implementation-observed | xcertplay adds session `enabledFeatures` token conditionally; not proof this token is the sole legacy requirement |
| primaryInputDevice | optional/config-dependent in implementation | tied to HID readiness; omit/altering may affect interaction; Honda legacy requirement unknown |
| viewAreas / initialViewArea | modern / version-specific | Apple documents view/safe areas in R15-era features; exact requirement for legacy second screen unknown |
| initialURL | implementation-observed | `maps:/car/instrumentcluster` used by xcertplay profile; no claim it is mandatory |
| role | concept documented; encoding unknown | Apple identifies instrument cluster role; Honda wire encoding unavailable |
| array of displays | implementation-observed | xcertplay serializes a `displays` list; Honda observed code selects `ScreenCopyMain`, not an evidenced iteration over multiple displays |

Do not transplant this modern dictionary wholesale. Honda's own field names/types must be recovered from its serializer and peer exchange first. Legacy secondary requirements and compatibility negotiation remain **unknown**.
