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

## Step 17 status — winner remains unresolved (2026-09-28)

The offline pass confirms generic registration and ranking only. `dev_attach` selects the strictly highest unsigned slot `+0` result (initial best 0; ties retain the earlier node), then dispatches slot `+4`. The concrete list entry/interface/context installed for `"CarPlay Screen"` is not statically recoverable from the local `jmcs` artifact. Therefore this note does not assign an active backend, sink, decoder, or Surface. See [device-match-semantics.md](device-match-semantics.md) and [Step 17](../../step-reports/17-carplay-registration-winner.md). The exact blocker is runtime registration state (or its producer), not absent `jmcs`/DWARF. Display-B readiness remains **No**.

## Step 18 status — saved runtime captures insufficient (2026-09-28)

The offline capture audit found `/system/bin/jmcs` process/maps/status/fd snapshots and older CarPlay logs, but no registry head, candidate nodes, callback tables, contexts, or match results. `media_dev_attach` log messages are generic and are not proven to come from `mc_dev_attach("CarPlay Screen", ...)`. Registry owner is `jmcs`; known list-head field is manager `+0x08`, but its absolute runtime address and list contents are unavailable. Live observation is required to continue. See [runtime registry audit](runtime-device-registry.md) and [Step 18](../../step-reports/18-runtime-registration-resolution.md). No live action was performed.
