# Display-B media interposer status

No implementation is proposed. Static analysis confirms that the primary screen requests `"CarPlay Screen"`, and the generic device manager selects a registry entry by callback score before calling that entry's attach slot. The winning entry for this key, its concrete sink, decoder, Surface, and ownership are unresolved.

| Design point | Status |
|---|---|
| Device duplication point | Unknown; `mc_dev_attach` call is per observed screen start, but repeated attach semantics are unproven |
| Sink duplication point | Unknown |
| Decoder duplication point | Unknown |
| Surface injection point | Unknown |
| Hardcoded one-screen/device/decoder/Surface assumption | Not established in the traced dispatch slice |
| Global assumptions | `mc_dev_attach` obtains manager through a global pointer; effect on independent instances unknown |
| Two complete media paths structurally supported | Unknown |
| Ready for Display-B implementation | No |

The highest-priority media blocker is the exact registration entry selected for `"CarPlay Screen"`, including its comparator result and attach callback. Display-B negotiation is a separate unresolved gate.
