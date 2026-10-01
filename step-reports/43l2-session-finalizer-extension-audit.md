# Step 43L.2 — session finalizer extension and cleanup attachment audit

Date: 2026-10-01. Scope: offline static analysis of the SHA-256 matched Honda `jmcs` only. No Honda code was run or modified.

## Decision

Honda does expose an app-facing CarPlay interface event callback, and the existing finalizer emits `MC_DEV_CARPLAY_SESSION_DESTROYED` through it. That is a real Honda event path, but it is not a safe ClarityLink subscription mechanism: the callback is a single slot in a 24-byte interface callback record, `mc_carplay_iface_set_cbs` copies/replaces the complete record, and the callback receives `(interface, event)` rather than an `AirPlayReceiverSessionRef`. There is no subscriber list, add/remove API, prior-callback chaining, or session-to-event correlation in the recovered path. Replacing that slot would displace the current consumer. Therefore Honda finalization is an **optional diagnostic/cleanup signal only**, not the owner of project child resources.

The generation guard is now bounded in the offline project model: a new generation synchronously supersedes prior child state for the same opaque identity; all prepared/active children have a renewable project lease; an expiry reaper closes exact expired generations idempotently; and stale keys cannot renew or affect a replacement. The lease duration and renewal policy remain runtime design parameters and are not claimed as Honda facts.

## Finalizer handler and registration

`_AirPlayHandleSessionFinalized` is Thumb code at `0xae654` (size `0x41c`). Its direct references and installed callback path are summarized in [dataflow](../research/carplay/honda-session-finalizer-dataflow.md). CF `_Finalize` (`0x284d24`) invokes the per-session callback at `session+0x20` with `(session, context)` at `0x284d36`, then invokes `AirPlayReceiverSessionPlatformFinalize` at `0x284d3e`. The delegate at `session+0x14` is copied as 11 words by `AirPlayReceiverSessionSetDelegate` (`0x285040`); `_AirPlayHandleSessionCreated` installs the Honda table at `0xaf252`. This is one Honda-owned callback field, not an observer collection.

Inside `_AirPlayHandleSessionFinalized`, the indirect call at `0xae7fa` loads a callback from global `g_carplay_cbs` (`0x355b6c`) and passes an interface plus event value 2. DWARF identifies event 2 as `MC_DEV_CARPLAY_SESSION_DESTROYED` and the callback slot as `event_cb`. `mc_carplay_iface_set_cbs` copies 24 bytes to the global callback record. No second callback dispatch or list traversal is present in the bounded call path. The event arrives without the finalized session pointer, and a separate interface event cannot safely select a project `(session,generation)`.

## Failure coverage and guard

The handler is installed on CF object finalization, which is later than session creation and not guaranteed merely by successful Setup, plist serialization, or HTTP body installation. The HTTP connection finalizer conditionally tears down a session only when its private context contains one; deallocation/finalization after delivery failure is not established. Thus the scenario “Setup and local response preparation succeed, HTTP delivery fails before normal Start” does **not** prove this handler runs. See [cleanup reachability](../research/carplay/honda-project-child-cleanup-reachability.md).

The guard uses opaque identity plus monotonically increasing project generation, immediate supersession, exact-key commit/cleanup, and configurable lease expiry/renewal. It must run independently of Honda finalization. Project listener lifetime is bounded by the lease; project transport activity can renew only the exact current generation. No guessed Honda timeout is introduced. The serializer boundary in synthetic tests requires both `return_code == 0xc8` and `status_out == 0`.

## Readiness

`FINALIZER EXTENSION DESIGN: NO_SUPPORTED_EXTENSION` for non-destructive session-addressable attachment. The event callback exists, but its global single-slot replacement semantics and missing session identity disqualify it. `GENERATION GUARD MODEL: COMPLETE` as an offline ownership contract; timer scheduling and runtime lease policy are not implemented against Honda. `JMCS INTEGRATION DESIGN: LIFECYCLE_MODEL_READY_CALLOUT_UNRESOLVED`. No integration mechanism is selected. JMCS implementation, live test, Type111 live, and ExternalDisplay render remain NOT READY; LD_PRELOAD remains PARKED.

## Static provenance

Evidence is `HONDA_CONFIRMED` for instructions, DWARF names/layout and call paths; `HONDA_UNKNOWN` for runtime event coverage, exact event delivery timing, and session identity propagation beyond the interface event. Lease behavior and tests are `OFFLINE_PROJECT_IMPLEMENTATION` / `SYNTHETIC_TEST_VALUE`.

## Decision-gate evidence detail

| Question | Result | Evidence boundary |
|---|---|---|
| Handler trace | COMPLETE | `_Finalize` is the direct caller of the installed per-session callback; indirect global app event call is resolved to `g_carplay_cbs.event_cb`. The app event itself does not carry the session. |
| Registration | COMPLETE | Session creator installs the Honda finalizer in a 44-byte session delegate; setter copies all 44 bytes. App interface setter copies all 24 callback bytes. Both are replacement semantics. |
| Multi-subscriber | DISPROVEN for the recovered finalizer/interface callback records | Fixed single function-pointer slots and whole-record `memcpy`; no list/table iteration or chain field on these paths. A global callback API not represented in this binary remains outside proof. |
| Non-destructive attachment | DISPROVEN for these mechanisms | Any newly installed callback replaces the existing function/table; interface event has no session identity. |
| Identity | PARTIAL | AirPlay session pointer/context are available in CF `_Finalize` → Honda app callback. The app-facing interface event only has interface+event. No Honda session generation/counter/creation timestamp was recovered; opaque pointer reuse is not excluded. |
| Coverage | PARTIAL | CF object finalization is statically real. Normal disconnect/failed Setup/HTTP error/server stop are not each proven to force that finalization. HTTP connection close only conditionally calls session teardown. |
| Pre-Session failure after local serializer success | NOT_PROVEN | HTTP body installation is distinct from HTTP send and SessionStart. Connection cleanup is conditional; no guaranteed reference release/finalizer edge was established for every such failure. |
| Alternate callback | NONE suitable | Session teardown and HTTP close paths were reviewed from the existing lifecycle reports. No additional multi-subscriber, session-addressable callback with pre-session delivery-failure coverage was found. |
| Generation guard | COMPLETE as offline ownership contract | New generation supersedes old exact child; lease expiration reaps stale resources; idempotent stop and stale key rejection are tested. Runtime timer/renewal policy is not implemented. |
| JMCS design | LIFECYCLE_MODEL_READY_CALLOUT_UNRESOLVED | Cleanup no longer depends on Honda. Only safe callout placement remains in this bounded lifecycle seam. |

### Finalizer event coverage (static only)

| Event | Reaches `_AirPlayHandleSessionFinalized`? | Path / classification |
|---|---|---|
| CF object finalization | Yes | `_Finalize` direct callback at `0x284d36`; HONDA_CONFIRMED |
| Normal CarPlay disconnect | Not individually proven | teardown/final reference flow does not establish a universal finalization event; HONDA_UNKNOWN |
| Setup failure | Not established | Setup error branch returns through handler cleanup; no static proof it forces CF object finalization; HONDA_UNKNOWN |
| HTTP delivery failure before normal Start | Not proven | HTTP close conditionally tears down a non-null session, but no guaranteed release/finalizer trigger; HONDA_UNKNOWN |
| Receiver/session teardown | Conditional/later | teardown and CF finalization are distinct paths; whether every teardown finalizes promptly is unknown |
| Connection loss | Conditional | `_connectionFinalize` checks private session pointer before invoking teardown; finalizer reachability beyond that is unknown |
| ScreenStream failure | Not individually proven | no complete error-to-finalizer path established in this bounded audit |
| Server stop | Not individually proven | no universal server-stop-to-session-finalizer edge established |

### Registrations and callers

| Object/table | Base/creation | Field | Stored callback | Owner/lifetime | Mutability |
|---|---|---:|---|---|---|
| Session delegate | session allocated by `AirPlayReceiverSessionCreate` (`0x284e58`); installed by `_AirPlayHandleSessionCreated` at `0xaf252` | session `+0x20` function slot; table starts `+0x14` | `_AirPlayHandleSessionFinalized` (`0xae654`, Thumb) | Honda per-session context | setter overwrites all 11 words |
| CarPlay app callback record | global `g_carplay_cbs` at `0x355b6c` | `event_cb` offset 0 | client-supplied event function; callback call at `0xae7fa` | Honda app/global interface consumer | `mc_carplay_iface_set_cbs` copies all 24 bytes |

The Honda handler's entry arguments are `(session, context)` by the `_Finalize` caller. Return handling is by CF runtime finalization; the caller does not branch on a meaningful project result. The global event callback's return type is `void` and cannot signal cleanup ownership back to the AirPlay lifecycle.
