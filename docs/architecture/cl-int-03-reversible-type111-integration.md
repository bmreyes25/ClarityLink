# CL-INT-03 — reversible custom Type111 integration architecture

**Status:** `CUSTOM_INTEGRATION_DESIGN_READY` with one offline component implemented and tested. **Vehicle:** `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED`. `safeForHonda()` remains `false`.

**Policy dependency.** The owner's revised offline direction (CL-POLICY-02) was **not published** when this was written: it existed only as uncommitted edits in a separate Codex worktree (`docs/cl-policy-02`, base `51fa9b1`). This document treats it as the owner's *proposed* engineering policy for this research campaign, does not depend on its unmerged text, and keeps the stricter existing deployment restrictions in [vehicle testing and safety boundaries](../safety/vehicle-testing.md). Historical conclusions of PRs #87, #88, #89 and #90 stand as written; they describe the operating model in force when written.

This is not Honda-supported, not OEM-authorized and not evidence about physical safety. Nothing here was run on, or connected to, a Honda or an iPhone.

## Evidence classes used below

| Tag | Meaning |
|---|---|
| **ESTABLISHED** | Recorded in reviewed static Honda evidence (see linked reports). |
| **SYNTHETIC** | Implemented and tested in this repository's offline models. Says nothing about Honda. |
| **CANDIDATE** | A modification proposed here. Unbuilt against Honda, unproven. |
| **MISSING** | Protocol or platform detail not established. Not invented here. |
| **UNSUPPORTED** | An assumption that must not be relied on. |

## 1. Receiver modification boundary

| Topic | Class | Basis |
|---|---|---|
| Honda's receiver runs a stock Type110 path; the reviewed static path has no Type111 handling and an unsupported type has no Setup side effect | ESTABLISHED | [type111-rollback](../../research/carplay/type111-rollback.md), [teardown lifecycle](../../research/carplay/honda-session-teardown-lifecycle.md) |
| Honda's finalizer/teardown path does not recognise a project Type111 child; no project subscription API for teardown is evidenced | ESTABLISHED (static) | [teardown lifecycle](../../research/carplay/honda-session-teardown-lifecycle.md), [runtime failure matrix](../safety/runtime-failure-matrix.md) |
| Stock-first Setup transaction: call stock unchanged, add project state only on success, return the stock response on any project failure | SYNTHETIC | `type111-rollback.md`, step 38/39 models |
| Type111 SETUP fields, capability advertisement, crypto/authentication context, data-port ownership, VideoConfig contract | MISSING | [unknown register](../../research/carplay/type111-unknown-register.md); no OEM contract |
| A Honda receiver that natively accepts Type111 | UNSUPPORTED | do not assume |

**What can live outside the factory receiver (sidecar):** the Type111 session state machine, decode, freshness/generation gating, the lease fence, and every cleanup. These touch only project-owned resources.

**What cannot:** advertising a second display in the receiver's SETUP response and owning a Type111 data port on the receiver's session. Those need a hook inside the factory receiver, and the protocol and authentication details they depend on are **MISSING**. The smallest conceivable receiver touch is therefore a *single, stock-first, fail-soft interposition at Setup* (CANDIDATE) that returns the unmodified stock response on any project failure. It must not replace any callback or dispatch table; the reviewed evidence shows that replacement displaces stock event/finalizer behavior. Nothing here fabricates Type111 messages or cryptographic contracts; the fail-safe component takes opaque closers and content and has no protocol knowledge.

**Recommendation:** keep every project-owned piece outside the receiver, and let the receiver hook (when and if its protocol gaps close) do only `grant lease` and `release`. The disconnect contract below does not depend on the receiver hook being correct.

## 2. Display 1 modification boundary

| Topic | Class | Basis |
|---|---|---|
| `ExternalDisplayOutService` owns the Display 1 context and attaches factory Views to bottom/main/interrupt roots; Navigation libraries supply *semantic* state, not frames | ESTABLISHED (static) | [CL-R9C](../research/cl-r9c-factory-display-boundary.md), [CL-HH-02](../research/cl-hh-02-display1-rendering-boundary.md) |
| No supported frame-admission input; warning precedence over a foreign View is not proven; geometry/crop/mask downstream of HDMI unknown | ESTABLISHED gap | CL-R9C |
| Host-owned view with revocable lease, interrupt-wins, no auto-restore | SYNTHETIC | `simulated_cluster_host.py`, `failsafe_coordinator.py` |
| Simulated pane-lease lifecycle on API17 | SYNTHETIC | `android/src/test/java/org/claritylink/renderer/PaneLease*Test.java` |
| Honda page selection effect on foreign views, meaning of internal layout rectangles, who may add a View | MISSING | needs bench observation; not derivable offline |

**In-process adapter** (CANDIDATE): a contained adapter inside the factory display process submits frames to a host-owned View. Cheapest rendering, but a project crash is a host crash, and it shares the process that draws warnings. **Inter-process** (CANDIDATE): the adapter lives in a separate process and the factory host maps its output into a host-owned View. Costs a copy and needs a Binder/shared-memory path, but a project crash cannot take the host with it and the host can fence without the producer. Neither is shown to be safe or supported. The deciding property is *who can revoke*: the host must be able to withdraw content with no cooperation from the producer, which favors the inter-process shape and is exactly what `Display1LeaseHost` models.

**Warnings stay authoritative by withdrawal, not by layering.** The design never relies on a View stacking above the warning. Any factory interrupt revokes the lease (SYNTHETIC) and the lease must be re-granted explicitly. Whether Honda's real interrupt root actually draws above a foreign View is **UNSUPPORTED** as an assumption.

**Cluster-controller firmware** is kept out of scope as a separate, higher-risk option. It is not recommended: the host-side route is sufficient to *design* the contract, and replacing firmware without an independent recovery channel is blocked for deployment.

## 3. Disconnect contract

Invariant (design target, not a demonstrated property): `CARPLAY_DISCONNECTED => FACTORY_BEHAVIOR_ONLY`.

Rules, each implemented and tested in `src/claritylink-honda/failsafe_coordinator.py`:

1. **Host-owned fence.** Custom content is visible only while an unexpired lease exists, bound to a boot **epoch** and a strictly increasing **generation**, and the navigation page is selected.
2. **Lazy expiry, no callback needed.** Expiry is evaluated on every read, grant, submit and heartbeat. If the producer, receiver, decoder and heartbeat source all stop, output is factory-only after at most one lease period with no disconnect event. This is a property of the *model*: a real host must evaluate expiry on every composition **and** from a timer, otherwise it would keep drawing the last frame.
3. **Frame = heartbeat, with a frame-age cap.** Accepted frames extend the lease. Explicit heartbeats extend it only until `2 x lease` after the last accepted frame (`FRAME_AGE_LIMIT_LEASES`); after that the lease is revoked ("no frame progress"), so a hung decoder with a live heartbeat cannot hold a frozen frame. A revoked lease cannot be extended.
4. **Revoke first, then clean.** Any fault revokes host content before any project cleanup. Closers run in reverse acquisition order, each independently, so a failing closer cannot block the rest or leave content visible.
5. **No resurrection.** Generations are never reused; a lease from an earlier generation or boot epoch is rejected; clearing an interrupt, restoring a display or reconnecting never re-exposes earlier content. Presenting again needs an explicit new grant.
6. **Fail-closed on refusal.** If negotiation is refused (CarPlay inactive, interrupt active, no display), resources the caller already acquired are released.
7. **Safe-direction actions always succeed** (revoke, fault, restore, cleanup) and are idempotent.
8. **Faults only lower the link state.** A late or duplicate fault callback (for example decoder death after USB unplug) cannot move `FACTORY_ONLY` back to `CARPLAY_ACTIVE`, so it cannot re-open negotiation.
9. **Input validation.** Generation and sequence must be non-negative ints (not bool, float, NaN); otherwise a NaN would disable the monotonic comparisons.

**Limits of this model.** The epoch and lease grant are staleness fences, **not authenticators**: a caller that can read host memory can forge them, and the 32-bit epoch is not a secret. There is no locking (one coordinator per host, single-threaded). If a second grantee took the host lease, a first coordinator's stale grant would only be adopted by `sync()` once the host lease is gone. `reports` and `revocations` are diagnostic lists that grow without bound.

## 4. State machine

States: `FACTORY_ONLY → PHONE_PRESENT → CARPLAY_ACTIVE → TYPE111_NEGOTIATED → STREAMING`. Page selection is a host-side visibility gate, not a state.

| Situation | Custom content visible | Frame owner | Old frames | Cleanup owner | State after | Recovery needs modified component? |
|---|---|---|---|---|---|---|
| No iPhone / boot | No | none | none | none | `FACTORY_ONLY` | No (startup default, nothing persisted) |
| iPhone, CarPlay inactive | No | none | none | none | `PHONE_PRESENT` | No |
| Primary CarPlay active | No | none | none | none | `CARPLAY_ACTIVE` | No |
| Type111 negotiated | No (no frame yet) | lease holder | none | coordinator + host lease | `TYPE111_NEGOTIATED` | No (lease expires alone) |
| Frames arriving, page not selected | No | lease holder | retained but hidden | coordinator + host lease | `STREAMING` | No |
| Frames arriving, page selected | Yes | lease holder | replaced by newest | coordinator + host lease | `STREAMING` | No |
| Disconnect requested | No | released | dropped | coordinator | `PHONE_PRESENT` | No |
| Unexpected USB disconnect | No | released; or lease expiry if no callback | dropped | coordinator, else host lease | `FACTORY_ONLY` | No |
| Type111 transport failure | No | released | dropped | coordinator, else host lease | `CARPLAY_ACTIVE` | No |
| Receiver crash | No | none | dropped by expiry | host lease alone | `FACTORY_ONLY` | No |
| Decoder crash | No | released | dropped | coordinator, else host lease | `CARPLAY_ACTIVE` | No |
| Display host crash / restart | No | released; new epoch | dropped | new host instance | `CARPLAY_ACTIVE` | **Yes, if the host itself is the modified component**: see §6 |
| Head-unit restart | No | none | none; old tokens rejected | boot default | `FACTORY_ONLY` | No for the invariant; persistence of any modification does matter (§6) |

Timeout behavior: bounded by the lease period (`DEFAULT_LEASE_SECONDS = 1.0` in the model). The real value is a tuning decision that requires bench data on frame cadence and acceptable flicker; the model does not justify a number for a vehicle.

## 5. Protecting factory functionality

Preserved by construction in the model: factory interrupt wins and is never dependent on custom rendering; interrupt clear never re-exposes content; stale frames are rejected on generation, epoch and sequence; hiding the page is not ownership.

**Not demonstrated, and not claimed:** that real cluster warnings, indicators, steering-wheel controls, audio/calls, host display lifecycle or vehicle start/shutdown are unaffected. The synthetic model has no audio, no controls and no ECU; the existing replay test checks a *synthetic* audio snapshot only. Forced immediate removal conditions in the design: factory interrupt, display loss, lease expiry, any fault in §4, supersession by a newer generation, and a failed or refused grant. The factory warning path is *not modified* by this design; direct changes to safety-critical ECU behavior are out of scope and prohibited.

## 6. Reversibility and recovery

| Technique | Persistence | Reversibility | Failure impact | Verdict |
|---|---|---|---|---|
| Sidecar project process + host-owned lease (no factory byte changed) | None; dies with the process | Highest: stop the process | Lease expiry restores factory output | Preferred |
| Stock-first Setup interposition, in memory | None; gone on restart | High if fail-soft; unproven on Honda | A bug in the hook can break stock Type110 | CANDIDATE, bench-gated |
| In-process View adapter in the display host | None if in memory | Medium: project fault is a host fault | Could blank Navigation | CANDIDATE, bench-gated |
| Persistent APK/native replacement of a factory component | Survives reboot | Needs an independent restore path | Could prevent boot or navigation | Blocked until restoration is proven independent |
| Cluster-controller firmware change | Survives power cycle | Only with an independent recovery channel | Cluster, warnings | Blocked for deployment; separate review |

Required before any deployment proposal (matches the vehicle-testing guide's reversibility contract): exact original component versions and SHA-256 fingerprints; complete offline-verified image backups; a restoration **demonstrated on non-vehicle equipment through a channel independent of the modified component**; dependency isolation so a project package cannot be a boot dependency of a factory one; an unmodified startup default with an enable/disable control that fails to *off*; behavior on partial initialization, factory crash and version mismatch (mismatch must default to factory-only). **A backup is not a verified recovery process**, and none is claimed here. The independent restoration method and its bench demonstration remain **unproven**.

If the display host is itself the modified component, the host fence cannot protect against the host's own crash; recovery then rests on the factory supervisor restarting an unmodified host and on persistence being absent. This is the main unproven recovery assumption.

## 7. Offline milestone implemented

`src/claritylink-honda/failsafe_coordinator.py` (extends the existing `SimulatedClusterHost`): `Display1LeaseHost` (epoch + generation + lazy-expiry fence, page gate, interrupt and display-loss handling) and `FailSafeCoordinator` (link state machine, eight fault kinds, ordered independent cleanup, host-revocation adoption). Boundary interfaces take opaque content and closers; no protocol, key or Honda identifier appears.

Tests: `tests/honda/test_failsafe_coordinator.py`, 39 tests (the fault matrix is parametrized), deterministic fake clock except one real-process test. That test SIGKILLs a live producer **stand-in** and then neither reads its socket nor calls the coordinator; it shows lazy expiry on the real clock clears content with no disconnect event. It does **not** show the host reacting to the process death, and the producer is not Honda's receiver; exact timing is asserted only with the fake clock. Twelve deliberate mutations of the safety properties (lazy expiry, epoch check, revoke removed, revoke reordered after cleanup, closer isolation, generation monotonicity, interrupt revocation, sequence ordering, fault-only-lowers-state, frame-age cap, input validation, page gate) were each caught by at least one test. Independent code and security review findings (a fault could raise the link state; unvalidated generation/sequence; untested revoke ordering; heartbeat-held frozen frame; flaky SIGKILL test) were fixed and regression-tested.

## 8. Laboratory acceptance matrix

| Case | Result | Notes |
|---|---|---|
| No phone at boot | PASS (synthetic) | refuses frames and negotiation |
| Normal Type110 session | Existing only | Type110 is not modeled here; `test_synthetic_type111_replay.py` covers a synthetic Type110 preservation |
| Type111 initialization | PASS (synthetic) | grant path; protocol itself MISSING |
| Secondary navigation visible only when appropriate | PASS (synthetic) | page gate and lease |
| Primary audio continuity | NOT TESTED here | no audio in this model |
| USB unplug during video | PASS (synthetic) | fault path |
| Rapid reconnect | PASS (synthetic) | old lease rejected |
| Type111 stream termination | PASS (synthetic) | fault path and lease expiry |
| Receiver process death | PASS (stand-in) | real SIGKILL of a *producer stand-in*; lease expiry only, not host reaction; not Honda's receiver |
| Decoder process death | Fault path + frame-age cap | no real decoder process |
| Display host restart | Fault path only | modeled display loss/restore; no real host process |
| Stale-frame rejection | PASS (synthetic) | generation, epoch, sequence |
| Frame ownership transfer | PASS (synthetic) | old cleanup runs, old frames rejected |
| Factory warning withdrawal | PASS (synthetic) | interrupt revokes; no re-exposure |
| Factory Navigation restoration | NOT TESTED | no factory Navigation view is modeled; only that custom content is gone |
| Repeated connect/disconnect | PASS (synthetic) | 50 cycles, zero residue, generations strictly increasing |
| Failure during initialization | PASS (synthetic) | grant refused releases resources |
| Restart after incomplete teardown | PASS (synthetic) | new epoch rejects old lease; real reboot persistence not modeled |

Full-suite result and environment are in the PR description. None of this verifies Honda behavior.

## 9. Staged validation path (not an executable vehicle procedure)

| Stage | Required evidence | Stop conditions | Acceptance |
|---|---|---|---|
| 1. Offline simulation | This suite plus the existing lab, extended per matrix gaps (audio, factory Navigation restore) | any residue after any fault | all matrix rows PASS with real code paths |
| 2. Independent bench hardware | Approved bench equipment, not the vehicle; frame cadence, lease tuning, host-crash behavior | unrecoverable or unexplained state | measured bounded withdrawal; no residual views/sessions |
| 3. Reversibility and recovery proof | Fingerprints, verified backups, restoration through a channel independent of the modified component, version-mismatch default | restore not reproducible | restore demonstrated repeatedly on non-vehicle equipment, separately reviewed |
| 4. Qualified safety review | Written review of warning ownership, startup, failure matrix | any open safety finding | explicit written approval |
| 5. Owner-approved parked vehicle validation | Separate explicit owner authorization (Level C), parked, supervised, abort plan | any anomaly | only stage-1 to 4 behavior reproduced; no deviation |
| 6. Longer reliability | Separately justified approval | any regression | not planned |

Cluster firmware modification would be considered only if the host-side routes (sidecar plus host-owned view) are shown on the bench to be unable to meet the disconnect contract; today nothing shows that, so it is not justified. This document authorizes no live ADB, installation or firmware write.

## 10. Remaining gaps

Type111 protocol and authentication contract; a real host-side timer and per-composition expiry check; Honda-side admission and warning layering; audio and factory-Navigation restoration in the model; real decoder and display-host processes in the lab; lease tuning data; the independent restoration channel and its demonstration; any qualified safety review.
