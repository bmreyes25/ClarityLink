# Tasks: Genuine iPhone-origin Type111 on Display 1

**Input**: `spec.md`, `plan.md`

**Canonical acceptance**: `docs/roadmap/finish-line-definition.md`; goal precedence: `docs/project/primary-goal.md`

**Status**: Proposed. No task below is claimed complete. All F1–F13 remain NOT PASSED.

## Phase 1 — Prerequisite evidence and gate review (Gate G1)

- [ ] **T001 [F13]** Record exact base SHA, branch, worktree, dirty/untracked scope, fetched `origin/main`, and task-owned file scope. Preserve all pre-existing changes.
- [ ] **T002 [F13]** Cross-check every F-ID and its evidence requirement against the canonical finish-line table; confirm goal precedence and record source revisions.
- [ ] **T003 [F1,F13]** Verify offline-only authorization, `safeForHonda() == false`, and that no live-iPhone, Honda ADB, vehicle or CAN operation is in scope.
- [ ] **T004 [F13]** Inventory existing receiver, decoder, lease, host-withdrawal and Type110 regression code/tests; classify each result VS, SYN, HST, UNK, MGI or MPA without upgrading evidence.
- [ ] **T005 [F3,F13]** Review the existing provenance and evidence-labeling behavior; identify only a demonstrated missing validation requirement.
- [ ] **T006 [F3,F13]** Review fixture intake boundaries and ensure synthetic or provenance-free fixtures cannot be represented as genuine iPhone evidence.
- [ ] **T007 [F4,F8,F9,F13]** Map the existing synthetic failure/disconnect tests to SC-004 and identify uncovered cases that the existing model can safely represent.
- [ ] **T008 [F2,F5,F6,F7,F10,F11,F12,F13]** Record Gate G1: list offline-ready gaps, all external blockers, required checks and exact file scope. Do not begin implementation until this record exists.

## Phase 2 — Offline CL-T111-INGEST-01 integration and verification

- [ ] **T009 [F3,F4,F13]** Confirm existing `Receiver`, `type111_ingest`, decoded-frame, per-stream dispatcher and lease interfaces from source; do not invent Honda protocol fields or production authentication.
- [ ] **T010 [F3,F13]** Verify framing/configuration/decode behavior with locally generated lab input only; label fixtures and outputs SYN and preserve input provenance.
- [ ] **T011 [F4,F8,F9]** Verify stream-generation fencing, stale-frame rejection and Type111-only teardown; add a focused regression only for a reproduced gap.
- [ ] **T012 [F1,F3,F4]** Verify absent or unverifiable authenticated-session context fails closed; never derive, extract or fabricate credentials or a Honda security context.
- [ ] **T013 [F3,F13]** Verify malformed, stale and unprotected media is rejected before reaching the frame sink; add bounded regression coverage for any reproduced defect.
- [ ] **T014 [F3,F4,F13]** Verify stream identity, frame ordering, configuration and provenance remain associated end to end in the host lab; do not claim MGI.
- [ ] **T015 [F1,F4]** Verify independent Type111 ownership and cleanup paths do not mutate Type110-owned session state.
- [ ] **T016 [F4,F8,F9]** Run the supported synthetic disconnect/fault matrix and verify withdrawal, cleanup and restoration outcomes with declared bounds.
- [ ] **T017 [F5,F13]** Verify every Honda Display 1 enablement path fails closed without a reviewed host contract.
- [ ] **T018 [F6]** Verify unknown page ownership, geometry and transforms are not guessed; reject unsupported dimensions rather than scaling into an assumed safe area.
- [ ] **T019 [F5,F6]** Verify frames reach only the existing simulated, lease-gated sink in this task; no private Binder or Honda sink is enabled.
- [ ] **T020 [F2,F4,F8,F9,F13]** Run the relevant host tests and API17 lab checks on the exact claimed tree/SHA; report synthetic Type110 continuity separately from target evidence.

## Phase 3 — Explicit blockers; no execution under this offline task

- [ ] **T021 [F6]** Record missing Honda Navigation-page ownership, physical safe area and transform contract (BLK-03); remain disabled.
- [ ] **T022 [F2,F7]** Record target evidence needed for Type110 continuity and factory warning precedence (BLK-03/05/06); do not induce a warning.
- [ ] **T023 [F7,F11]** Record the independent, qualified safety review required for warning and vehicle hazards (BLK-05); an AI review is not approval.
- [ ] **T024 [F2,F4,F8,F9]** Record target-only Type110 coexistence, revocation, failure and restoration evidence needed by F2/F4/F8/F9; do not connect to a vehicle.
- [ ] **T025 [F10]** Record that target performance/resource thresholds and measurements remain undefined and blocked; do not claim lab metrics satisfy F10.
- [ ] **T026 [F1,F2,F3,F4]** Record missing supported Honda receiver/session/SETUP/security/ownership/revocation contract (BLK-02); fail closed and do not infer fields from Type110 or third-party prior art.
- [ ] **T027 [F12]** Specify rollback evidence and independent recovery prerequisites only; no target change or rollback rehearsal is authorized.
- [ ] **T028 [F11]** Record the independent safety-review deliverable and reviewer qualification required before any target-facing work.
- [ ] **T029 [F1,F5,F6,F7,F11,F12]** Keep bench, phone and vehicle execution gated on separate explicit owner authorization; offline permission is not that authorization.
- [ ] **T030 [F3,F13]** Record the missing sanitized, genuine iPhone-origin Type111 fixture and its provenance/redaction requirements (BLK-04); obtaining it requires separate owner authorization and a legitimately authenticated bench session, neither of which is authorized here. Do not connect an iPhone or relabel synthetic data.

## Phase 4 — Public-safe history and specification maintenance

- [ ] **T031 [F13]** Review every task-scoped file for private evidence, credentials, derived Honda material, and ignored-file exposure before any public checkpoint.
- [ ] **T032 [F13]** For a verified public-safe development unit, use the repository publication tooling and verify remote SHA, PR checks and review status; never publish private evidence or merge safety-sensitive changes automatically.
- [ ] **T033 [F1-F13]** When the canonical finish-line or primary-goal documents change, update this traceability map in the same reviewed change; never infer F-item completion from synthetic evidence.

## Phase 5 — Bounded offline ephemeral cleanup/recovery harness (CL-T111-EPHEMERAL-HARNESS-01)

Evidence label SYN only. Contract: `docs/architecture/ephemeral-harness-contract.md`. These tasks add host-model evidence and do not move any F-item toward PASSED.

Review state: T034–T037 are implemented and covered by offline tests; the corrected candidate received independent read-only review and PR #106 was merged by the owner on 2026-10-29 at `2ce2c699b94f77fda867f278199c550e12acfa71`. Retry attempt labels are execution labels only, never the milestone identity. T034–T037 checkmarks record implementation of a synthetic host model only, not Honda compatibility or target recovery evidence.

- [x] **T034 [F4,F8,F9,F13]** Machine-readable resource manifest (`ephemeral_harness_manifest.json`) covering files/storage classes, processes, sockets, services, mounts, Display 1 leases and cleanup obligations; every Honda-dependent property UNKNOWN; `/data/local/tmp` not established as reboot-volatile.
- [x] **T035 [F4,F8,F9]** Deterministic cleanup/recovery state machine (`ephemeral_harness.py`) reusing the CL-INT-04 lease, teardown and host-withdrawal code; no second lease system; missing or unreachable resources are UNKNOWN, never clean.
- [x] **T036 [F4,F8,F9,F13]** Failure-injection tests: normal termination, process crash, lost producer, lost control connection, interrupted cleanup, host restart (epoch fence), simulated reboot, missing cleanup resource; Type110 independence through the CL-INT-04 pipeline.
- [x] **T037 [F13]** Negative assertions: a simulated reboot cannot establish Honda cleanup, RAM-backed target storage, restoration or reboot recovery; `safeForHonda()` false.
- [x] **T038 [F13]** Published through `tools/publish_checkpoint.sh`; remote SHA verified and exact candidate independently reviewed read-only. PR #106 merged by the owner at `2ce2c699b94f77fda867f278199c550e12acfa71`; required CI and CodeQL checks passed. This records publication only and does not change any Honda acceptance status or constitute safety approval.

## Gate rule

T021–T030 are records of missing evidence or authorization, not permission to perform the activity. No task permits vehicle access, Honda ADB, a connected iPhone, authentication bypass, secret extraction, warning suppression or a change to `safeForHonda()`. Any newly discovered interface remains UNK until its evidence is reviewed and the plan is revised.
