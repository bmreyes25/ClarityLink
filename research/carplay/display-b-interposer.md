# Display-B media interposer status

No implementation is proposed. The primary CarPlay screen requests the device named `"CarPlay Screen"` from `mc_dev_attach`, but the matching registry entry, construction callback, concrete sink, decoder, and Surface are unresolved.

| Design point | Status |
|---|---|
| Device duplication point | Unknown; candidate is the `mc_dev_attach` call in `mc_ScreenStreamStart`, but repeated attach semantics are unproven |
| Sink duplication point | Unknown |
| Decoder duplication point | Unknown |
| Surface injection point | Unknown |
| Primary-only assumptions in proven device path | Not yet audited beyond manager global; no claim of singleton backend is justified |
| Two complete media paths structurally supported | Unknown |
| Ready for Display-B implementation | No |

The next action is to recover the `dev_attach` lookup/registration match, then follow that callback and its object ownership. Display-B negotiation remains outside this milestone.
