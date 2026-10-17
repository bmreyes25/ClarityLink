# Current project status

**Updated:** 2026-10-17
**Campaign:** Repository recovery and public-safe synchronization
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
| CL-R4 dual-stream fixture isolation | `IN_PROGRESS`; Binder v3 identity, bounded dispatch, Type110 progress during Type111 saturation, fixture decoding, and Type111 producer-failure/recovery have laboratory evidence. Sink reconnection, Type110-only ownership, parent-authority process death, and reentrant teardown remain incomplete. | [Producer-process result](../../research/vehicle/test6a-t7-integration/30-cl-r4-producer-process-fault-result.md), [stream isolation results](../../research/vehicle/test6a-t7-integration/26-cl-r4-stream-isolation-results.md) |
| CL-R5 Type111 control plane | `IN_PROGRESS`; a synthetic lab-only Android Binder model covers capability/setup, navigation eligibility, presentation, geometry, and VideoConfig against Binder v3 identity. It is not CarPlay wire negotiation or an authenticated Honda session. | [Type111 integration results](../../research/vehicle/test6a-t7-integration/27-cl-type111-major-integration-results.md), [presentation model](../../research/vehicle/test6a-t7-integration/25-cl-r5-presentation-control-model.md) |
| CL-R6 Honda display output | `IN_PROGRESS`; an OEM-authorized output host is required. No supported arbitrary-frame interface has been established. | [Honda Type111 research plan](../research/honda-type111-research-plan.md) |
| CL-R7 / CL-R8 | `PLANNED`; no vehicle or live iPhone operation is authorized. | [Development roadmap](../roadmap/final-development-plan.md) |
| `safeForHonda()` | `false`. | [`DisplayPolicy.java`](../../android/src/main/java/org/claritylink/android/DisplayPolicy.java) |

## Review and publication

The publication candidate is a clean-history selection based on `origin/main`; it excludes raw/private emulator evidence and vehicle-specific local inventories. Separate read-only ECC-guided code and security reviewers covered the full candidate at `31cf50a`, verified the padded-crop correction at `3d6f8bf`, and confirmed final scope/status metadata at `4889118`. The runner ownership, artifact-path, padded-crop negative-control, and stale scope/status findings were corrected. The configured suite passes in a clean Git clone and in the local engineering environment (1,507 passed, 15 skipped), including the macOS Swift verifier regression. The API17 emulator runtime was not executed. AI review is not human vehicle-safety certification.

## Next action

Complete the API17 Type111 sink-reconnection and Type110-only failure ownership matrix, then validate parent-owner death and reentrant teardown. Honda authenticated Type111 and OEM output integration remain unproven and unauthorized.
