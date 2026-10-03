# 43T1-R1 memory ownership review

**Decision:** the project-side fake runtime contract is testable; Honda CFLite callsite semantics remain partial. This review does not import Apple's retain/copy behavior into Honda.

Evidence labels used here are `HONDA_CONFIRMED` (static Honda evidence only), `LAB_CONFIRMED` (synthetic project model), `EXTERNAL_REFERENCE` (Apple public CF), and `UNKNOWN` (unresolved target behavior).

| Object / boundary | Proposed classification | Evidence | Required rule / open point |
|---|---|---|---|
| Setup response pointer | Honda-owned borrowed input during synchronous bridge | `HONDA_CONFIRMED` static caller releases response after synchronous serializer; see [response ownership](../carplay/honda-response-ownership.md) | Never release or retain beyond its established lifetime; cross-thread escape is prohibited. |
| Honda `CFDictionary` | borrowed; mutable state and callback behavior unresolved | `HONDA_CONFIRMED` static Setup path creates/uses dictionary; callback mapping incomplete in [callback ledger](../carplay/honda-cf-callback-ownership.md) | Do not mutate the original graph until constructor callbacks, getter ownership, and rollback path are proven. |
| Honda `CFArray` | borrowed; callback behavior unresolved | same static ledger | Treat `CFArrayGetValueAtIndex`/dictionary getter results as borrowed until exact Honda wrapper contract is proven. |
| Type111 entry | project-owned when created; insertion ownership unknown | `LAB_CONFIRMED` fake-CF tests only | Keep project creator refs until a proved retain/copy boundary; no assumption that insertion retains. |
| Type111 key/value/port number | project-created immutable scalar objects or keys; ownership remains explicit per reference | clean-room bridge tests and external CoreFoundation docs | Release only project-owned +1 refs; never release Honda-owned values. Honda callback behavior still unknown. |
| Serializer inputs | borrowed for synchronous call only | `HONDA_CONFIRMED` static response call chain | Call stock serializer once; no object retention after return absent explicit retain proof. |
| Transaction context | project-owned, immutable and generation-tagged | `LAB_CONFIRMED` host models | Context valid only for that generation; callbacks with expired/mismatched generation must no-op and cannot close current resources. |
| Listener | project-owned by exactly one generation | `LAB_CONFIRMED` host socket model | No wildcard address; close exactly once via generation teardown. No Honda listener has run. |
| Accepted socket / worker | project-owned child resources | `LAB_CONFIRMED` host ownership model | Child cannot outlive its generation; do not operate on reused/stale descriptors. |
| Generation token | project-owned immutable identity | host tests model exact-generation cleanup | Stale cleanup denied, not redirected to current generation. |
| Temporary CF mutable copy | project-owned until transfer is proven | `LAB_CONFIRMED` FakeCF rollback model | Prepare complete candidate off-graph, commit once, rollback only if identity/version still equals the exact prior object. Honda callback semantics are unresolved. |

## Public CoreFoundation references

`EXTERNAL_REFERENCE` Apple's public headers distinguish immutable and mutable collections, describe callback retain/release behavior, and define create/copy ownership. These rules are useful for designing explicit contracts but are not proof of Honda's `CFLite` implementation/version or its callback tables. See the Apple CoreFoundation links in [runtime-feasibility-analysis](runtime-feasibility-analysis.md).

## Remaining ownership blockers

- Exact Setup response dictionary and `streams` array callback-table arguments in Honda.
- Getter retain conventions and mutation/alias behavior at the exact bridge boundary.
- Type111 entry and nested key/value callback ownership at insertion.
- Whether any callback can re-enter or observe partially prepared response state.
- Independently reachable cleanup after serializer failure, process termination, or host loss.

`UNKNOWN` on any one of these prevents treating the bridge's synthetic ownership success as a Honda runtime proof.
