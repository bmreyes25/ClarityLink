# Current project status

**Updated:** 2026-10-18
**Campaign:** Final offline integration campaign
**Current milestone:** CL-R4 — `IN_PROGRESS`; CL-R5 — `IN_PROGRESS`
**Authoritative manifest:** [milestones.json](milestones.json)
**Latest public-safe integration summaries:** [Type111 producer-process result](../../research/vehicle/test6a-t7-integration/30-cl-r4-producer-process-fault-result.md), [stream isolation](../../research/vehicle/test6a-t7-integration/26-cl-r4-stream-isolation-results.md), [presentation-control model](../../research/vehicle/test6a-t7-integration/25-cl-r5-presentation-control-model.md). Raw emulator receipts and private evidence are excluded from this publication candidate.

## Verified state

| Area | State | Evidence |
|---|---|---|
| CL-R0 repository foundation | `ECC_REVIEWED_STATIC`; separate read-only code and security reviews found no actionable issue through `fc5a70b80dc517c2a8fb81ceb84f4eb3be888279`. The post-fix API17 runtime remains unverified, and the project license decision remains unresolved. | [CL-R0 validation](cl-r0-validation.md) |
| CL-R1 warning-preemption race | `API17_EMULATOR_VERIFIED` for deterministic Binder/Handler/View race interleavings and final-draw epoch gating. This is laboratory evidence, not Honda warning-priority validation. | [CL-R3 acceptance summary](../../research/vehicle/test6a-t7-integration/22-cl-r3-final-acceptance.md) |
| CL-R2 API17 isolation and crash recovery | `API17_EMULATOR_VERIFIED`; system-owned crash-dialog handling was validated. A historical FinalizerWatchdog timeout did not recur; its original cause remains unknown. | [CL-R3 acceptance summary](../../research/vehicle/test6a-t7-integration/22-cl-r3-final-acceptance.md) |
| CL-R3 Binder-to-View | `API17_EMULATOR_VERIFIED`; acceptance summary covers malformed frames, generations, pixel classification, warning interleavings, process death, crash recovery, and cleanup. No physical scanout is claimed. | [Final acceptance](../../research/vehicle/test6a-t7-integration/22-cl-r3-final-acceptance.md) |
| CL-R4 dual-stream fixture isolation | `IN_PROGRESS`; producer failure/recovery, Type110-only sink failure, actual compositor-owner process death, concurrent/repeated parent teardown, and delayed old-sink callbacks have API17 evidence. Teardown and delayed-callback tests passed in both stream-registration orders. The real old callback paused before registry mutation, then returned after the fresh sink replacement without unregistering it; fresh H.264 frames rendered, Type110 generation stayed unchanged, and parent cleanup reached zero PFD/retained-byte counters. CL-R4B registration attacks and queue-failure combinations remain incomplete. | [Producer-process result](../../research/vehicle/test6a-t7-integration/30-cl-r4-producer-process-fault-result.md), [stream isolation results](../../research/vehicle/test6a-t7-integration/26-cl-r4-stream-isolation-results.md) |
| CL-R5 Type111 control plane | `IN_PROGRESS`; a synthetic lab-only Android Binder model covers capability/setup, navigation eligibility, presentation, geometry, and VideoConfig against Binder v3 identity. It is not CarPlay wire negotiation or an authenticated Honda session. | [Type111 integration results](../../research/vehicle/test6a-t7-integration/27-cl-type111-major-integration-results.md), [presentation model](../../research/vehicle/test6a-t7-integration/25-cl-r5-presentation-control-model.md) |
| CL-R6 Honda display output | `IN_PROGRESS`; an OEM-authorized output host is required. No supported arbitrary-frame interface has been established. | [Honda Type111 research plan](../research/honda-type111-research-plan.md) |
| CL-R7 / CL-R8 | `PLANNED`; no vehicle or live iPhone operation is authorized. | [Development roadmap](../roadmap/final-development-plan.md) |
| `safeForHonda()` | `false`. | [`DisplayPolicy.java`](../../android/src/main/java/org/claritylink/android/DisplayPolicy.java) |

## Review and publication

The publication candidate is a clean-history selection based on `origin/main`; it excludes raw/private emulator evidence and vehicle-specific local inventories. Separate read-only ECC-guided code and security reviewers covered the full candidate at `31cf50a`, verified the padded-crop correction at `3d6f8bf`, and confirmed final scope/status metadata at `4889118`. The runner ownership, artifact-path, padded-crop negative-control, and stale scope/status findings were corrected. The earlier 1,507/15 candidate count is not retained as clean-clone evidence because its environment receipt is missing and the candidate worktree was later found to contain ignored local tools. The prior 1,208/18 main count did not reproduce. Two runs in one fresh clone of merged `main` at `4c448cbd` each returned 1,197 passed, 29 skipped, and no failures; see the [clean-main test receipt](cl-r0-main-test-receipt.md). The API17 emulator runtime was not executed. AI review is not human vehicle-safety certification.

## Next action

Complete the untested CL-R4B registration-attack, queue-saturation/failure, and aggregate cleanup cases. Then finish the laboratory output-host integration. Honda authenticated Type111 and OEM output integration remain unproven and unauthorized.
