# 43T1-R1 — offline runtime feasibility review

**Decision: `RETURN_TO_OFFLINE_WORK`.** This is an offline decision following D4/R0. It does not authorize a Honda experiment.

## Scope and start state

- Starting HEAD: `9117b4f2f458adc14e30452ac1e9a01e3429b0ae` on clean `main`, equal to `origin/main`.
- Honda contacted: no.
- ADB used: no.
- RAM attachment/runtime modification/deployment/vehicle work: none.
- This milestone examined repository files and public sources only; no private D4 network binding values were read into or written from this public record.

## What changed

- Added a version-scoped API-17 AOSP, ARMv7/AAPCS32/AAELF32, Bionic, cache, signal, and external CoreFoundation review with explicit evidence labels: [runtime-feasibility-analysis](../research/runtime/runtime-feasibility-analysis.md).
- Expanded the independent host-side restoration verifier in `prep2_runtime.py`. A positive result now requires exact expected/observed stock bytes, SHA-256, address, Thumb alignment, decoded instruction sequence, branch target/continuation, fresh context/resource evidence, explicit rollback completion, and at least two independent readbacks (first `RESTORED` then idempotent `ALREADY_RESTORED`). Interrupted operation requires an explicit final readback.
- Added a pure runtime state/invariant model in `runtime_safety_model.py` and focused tests. It has no process, device, ADB, memory, or listener backend.
- Added the [runtime failure matrix](../docs/safety/runtime-failure-matrix.md), [state-machine contract](../research/runtime/43t1-r1-runtime-state-machine.md), [ownership review](../research/runtime/43t1-r1-memory-ownership-audit.md), and [future experiment checklist](../research/runtime/43t1-r1-future-experiment-checklist.md). The checklist explicitly marks itself NOT AUTHORIZED / NOT EXECUTABLE.

## Findings

- **Android assumptions:** API 17 must use the older AOSP linker and Bionic source baseline. The documented API-22 lookup and API-23 loader changes are not applied. Generic API-17 source does not establish Honda's vendor code or permission behavior.
- **ARM/runtime:** ABI/ELF/Thumb and cache-maintenance rules narrow implementation assumptions. Cache synchronization does not make a two-halfword Thumb callsite patch atomic and does not stop concurrent execution. Honda API-17 thread quiescence, permission changes, cache effects, and safe re-entry remain unknown.
- **CFLite:** public Apple CF behavior is explicitly only an external reference. Honda constructor callbacks/getter ownership and exact Type111 nested-object lifetimes remain unresolved.
- **Restoration verifier:** local logic can reject incomplete evidence. It cannot generate independent process readbacks, establish a target write happened safely, or prove physical stock state.
- **State and invariants:** fail-closed transitions and assertions are executable on host data, but cannot represent every hardware, kernel, scheduler, or power-failure outcome.

## Readiness gates

| Area | Result | Remaining blocker |
|---|---|---|
| G1 exact Honda binary identity | Existing static evidence remains PASS within artifact scope | Fresh live process epoch/mapping is future-session evidence |
| G2-G4 callsite, target, continuation | Static Honda artifact facts remain PASS | Runtime address/load bias unknown |
| G5 executable ABI | Offline ARM build/emulator work only | Honda runtime execution/permissions/fault behavior unknown |
| G6-G10 stock path, serializer, transaction, malformed behavior, Type110 | PASS in offline models/static scope | Honda reentrancy and runtime CF mutations unknown |
| G11 network contract | D4 G11-A-D PASS; PREP2 BIND_POLICY_READY | G11-E/F and listener reachability remain open |
| G12 rollback | Host/model contract improved | Target restore operation and independent target readback unproven |
| G13 Type111 crypto/security | Explicit UNKNOWN preserved | Requires separate evidence; not in R1 |
| G14 unknown security fails closed | Policy/model PASS | No Honda Type111 behavior |
| G15-G18 generation, stale cleanup, logs, rollback/disable | Host model and policy evidence | Real target interruption/cleanup remains unknown |
| G19 Honda prerequisites | NOT READY | API17 Bionic method, CFLite contract, attach permission and fault containment |
| G20 first live modification scope | Checklist bounded on paper | Atomicity/thread-rendezvous and failure recovery prerequisites fail |
| G21 latency | Structural/model only | No Honda timing claim |
| Restoration | Stronger offline verifier contract | Cannot prove a future target read or restoration operation |
| Listener network policy | Specific observed D4 policy input | No Honda listener or reachability evidence |

## ECC audit findings

ECC literature-review, security-review, safety-guard, coding-standard, and test guidance was applied as a manual review checklist. This is not an independent ECC service review or external sign-off. Findings:

1. Provenance is separated into Honda evidence, AOSP/ARM documentation, lab models and external references.
2. API-22+/23+ Android linker claims are excluded from the API-17 design baseline.
3. CoreFoundation principles are not assigned to Honda CFLite without direct evidence.
4. Restoration must be independently read back; installer/write return values are insufficient.
5. Unknown crash, host-loss, power and reboot states remain UNKNOWN; no automatic “volatile equals safe” claim.
6. Specific-address policy remains mandatory; wildcard bind is rejected.
7. Existing repository results such as PREP2_COMPLETE, CF_BRIDGE_OFFLINE_READY, and D4 network readiness remain bounded to their original scopes.

## Remaining unknowns

### Requires Honda-specific evidence

- Actual attach mechanism, process permissions, live mapping/load bias and process epoch.
- API-17 target page permission transitions and cache-flush result.
- Safe all-thread rendezvous and absence of execution through the patch span.
- Honda CFLite constructor callback identity, getter ownership, and nested Type111 object lifetime.
- In-target serializer/reentrancy behavior, listener bind/reachability, and target fault containment.
- Independent exact restoration readback and stock display/audio/cluster behavior after the experiment.

### Cannot be established by offline source review alone

- The target's actual runtime permissions, scheduling, phone behavior, socket reachability, or reaction to process failure.
- A specific powered target's physical post-restart/stock state.
- A future observation not yet collected. Offline models cannot turn any of these into proof.

### Further offline work is justified

Yes. The proposed checklist identifies a concrete contradiction: the expected four-byte Thumb callsite straddles a four-byte fetch group and no single atomic store or proven all-thread stop procedure exists. The stated two-write budget cannot yet be proven safe for all partial-write states. Continue offline with a compatible API-17 ARM/Bionic lab harness and static Honda CFLite constructor/getter audit; design an independently testable interruption model before any future experiment review.

## Verification

Focused PREP2, restoration-verifier, state-machine, and ownership suites: **143 passed**. Full configured offline suite: **652 passed, 3 skipped**, plus self-locator **3/3**, simulator checks passed, and `git diff --check` passed. Repository health: **446 Markdown files, 111 indexed reports, 0 curated broken links, 0 forbidden tracked file extensions**. Hosted CI is pending push of this scoped change set. No ADB binary or Honda command was invoked.

ECC review result: manual audit applied; no independent reviewer/service was available. Focused and full offline verification support the model contract only. Final review and ending HEAD will be recorded after hosted CI.

## Next milestone

**43T1-R2 — API-17 ARM/Bionic Harness and Honda CFLite Static Ownership Closure.** Offline only. Exit only when the harness environment and exact test scope are demonstrated reproducible, and Honda ownership callsites have been mapped or explicitly declared unresolved. Another ECC readiness decision is required afterward. Do not start a modifying Honda experiment automatically.
