# 43T1-R3B — lifecycle cleanup static closure

**Scope:** repository-only static analysis. No model or runtime integration was added.

## Repository state and safety

- Starting branch: `main`.
- Starting HEAD: `febaf21e0760f564140ac7b92d93d53de961d89c` (the known 43T1-R3A final HEAD; verified at task start).
- R3B evidence closure HEAD: `e8c2c37ad26d331cf20f9de7ba91add5a40f9517` (substantive documentation/matrix commit). This report is a follow-up record commit; the final pushed HEAD is reported in the final response.
- Initial worktree was already dirty with R3 working files and prior updates in `EVIDENCE_INDEX.md`, `NEXT_ACTION.md`, `PROJECT_STATE.md`, `docs/safety/runtime-failure-matrix.md`, and `step-reports/README.md`. Those pre-existing changes were preserved; only this task's additions will be committed.
- Honda contacted: NO.
- ADB used: NO.
- Runtime writes: 0.
- Vehicle connected: NO; RAM attached: NO; listener created: NO; Type111 negotiated: NO.
- No firmware, capture, credential, key, token, or vehicle screenshot was added.

## Sources reviewed

- `step-reports/43l1-callout-safety-cleanup-reachability.md` and `step-reports/43l2-session-finalizer-extension-audit.md`.
- `research/carplay/honda-project-child-cleanup-reachability.md`, `honda-session-finalizer-dataflow.md`, and `honda-type110-ownership-ledger.md`.
- `research/runtime/honda-cflite-ownership-static-audit.md`.
- `research/runtime/43t1-r3a-non-inline-seam-evidence-inventory.md`, `43t1-r3a-setup-path-seam-map.md`, and `step-reports/43t1-r3a-non-inline-seam-evidence-inventory.md`.
- `step-reports/43t1-r2-api17-arm-bionic-cflite-readiness.md`, `43t1-r1-runtime-feasibility-review.md`, and `43t1-r0-post-d4-readiness-review.md`.
- Searched repository reports/research for `Finalize`, finalizer, cleanup, teardown, session cleanup, generation cleanup, retire/remove/release/close, listener cleanup, project child, Type111 child, and stale cleanup.
- All historical reports were treated as evidence, not authorization. Static Honda statements remain bounded to their cited hash-matched artifact; synthetic cleanup contracts remain `MODEL_ONLY`.

## Cleanup/finalizer findings

- **Honda finalizer exists:** CF `_Finalize` calls Honda `_AirPlayHandleSessionFinalized(session, context)`, then `AirPlayReceiverSessionPlatformFinalize(session)`. This is `HONDA_CONFIRMED` static control flow for the cited binary.
- **Session identity is incomplete for project ownership:** the Honda per-session callback sees an opaque session pointer/context. No stable Honda generation or non-reuse guarantee was recovered. The global `MC_DEV_CARPLAY_SESSION_DESTROYED` callback receives interface+event without session identity; project association remains `UNKNOWN`.
- **Type110:** the ordinary stock response graph has traced container retain/release edges and a recognized Type110 teardown path (`HONDA_CONFIRMED`). This does not prove runtime fault/re-entry safety or compatibility of arbitrary Type111 values.
- **Unknown Type111:** the recovered `tearDownStreams` parser skips unknown type 111; no enumeration of project child resources is evidenced (`HONDA_CONFIRMED` for this bounded parser path).
- **Callback ownership:** the session delegate is a Honda-owned fixed 11-word record; the interface event callback is a global fixed 24-byte single slot. Whole-record replacement, not append-only subscription, is evidenced. Replacement is rejected as unsafe.
- **Release/close paths:** response graph release follows synchronous serialization and precedes HTTP send. Connection close reaches session teardown only conditionally when its private context contains a session pointer. Neither edge supplies a project-child registry lookup.
- **Project behavior:** generation tokens, lease expiry, listener close, rollback, duplicate/stale cleanup, and fail-closed security retirement are `MODEL_ONLY`/host-test contracts. They are not Honda cleanup evidence.

## Coverage and ownership results

- Coverage matrix: [43T1-R3B cleanup coverage matrix](../research/runtime/43t1-r3b-cleanup-coverage-matrix.md). No project-child scenario is `COVERED_STATICALLY`; model-only scenarios are labeled as such.
- Ownership map: [43T1-R3B finalizer ownership map](../research/runtime/43t1-r3b-finalizer-ownership-map.md). Honda owns its session/context and stock Type110 path; the project would own a hypothetical Type111 child, listener, generation token, and stale/duplicate records. Their association is not evidenced.
- Is project-child cleanup statically bounded? **No.** Existing Honda cleanup cannot safely be treated as the owner of future project-created Type111 resources.

## Main static blockers

1. No non-destructive, session-addressable project subscription or project registry lookup is evidenced.
2. The only recovered callback registration paths are replacement slots; callback replacement and dispatch-table overwrite are rejected.
3. The known `tearDownStreams` path skips unknown Type111.
4. The app-facing finalizer event lacks session/generation identity; stable Honda pointer generation is unknown.
5. Connection-to-session teardown is conditional; success, disconnect, malformed Setup, serializer/body failure, listener failure, media non-arrival, crash/restart, and power-loss coverage is incomplete or model-only/unknown.
6. The static stock Type110 retain/release graph does not prove arbitrary Type111 field compatibility, partial mutation rollback, or project-resource reachability.
7. No cleanup model is justified: modeled generations cannot bridge the absent Honda registration/identity path.

## Decision

**R3B decision:** `LIFECYCLE_CLEANUP_NOT_SAFE_FOR_PROJECT_CHILDREN`

**Project recommendation:** `GO_FOR_R3C_STATIC_SEAM_CLOSURE`

R3C may continue offline only to search preserved repository artifacts for a genuinely non-replacement, session-addressable extension path or independent project-owned entry/cleanup design. This recommendation does not authorize runtime interposition, Setup mediation, Type111 work, or a car experiment.

## ECC review

Manual @ECC review covered cleanup ownership, session identity, failure coverage, Type110 preservation, hypothetical Type111 ownership, callback replacement, unknown-type handling, and authorization language. Findings: keep Honda static paths separate from project model cleanup; do not infer Type111 teardown from Type110 release; treat unknown-type skip as a blocker; do not describe the global event as session-addressable; do not infer cleanup on process/power loss; retain all runtime prohibitions. This is a manual review, not independent ECC sign-off.

## Verification

- Focused tests: none applicable; no code, checker, test, or model was added.
- Full `PYTHON=.venv/bin/python ./tools/run_tests.sh`: **674 passed, 3 skipped**; self-locator **3 passed**; all configured simulator checks passed. Capture-backed replay scripts were skipped because private fixtures are not CI inputs.
- `.venv/bin/python tools/check_repo_health.py`: **passed**, 464 Markdown files, 116 indexed milestone/support reports, 0 curated broken links, 0 forbidden tracked extensions.
- `git diff --check`: **passed**.
- Hosted Offline CI: started for the pushed R3B commit; final result is recorded in the final response. Earlier 43T1 runs do not verify this chunk.
- CodeQL: started for the pushed R3B commit; final result is recorded in the final response. Earlier 43T1 runs do not verify this chunk.
