# 43T1-R3A — non-inline seam evidence inventory

**Chunk:** first, bounded evidence-inventory portion of 43T1-R3. This report does not complete R3 or build a model.

## Scope and repository state

- Starting branch: `main`.
- Starting HEAD: `7dbc66152658a9d3b506efce777c9da0a84d9f12` (matches the supplied 43T1-R2 final HEAD).
- Final HEAD: recorded after the R3A documentation commit/push; no implementation or model is planned.
- Initial worktree: not clean. Existing user work was present before this task: modified `EVIDENCE_INDEX.md`, `NEXT_ACTION.md`, `PROJECT_STATE.md`, `docs/safety/runtime-failure-matrix.md`, and `step-reports/README.md`; untracked R3 materials included an inventory, setup map, wrapper analysis, callback audit, ADR, and R3 report. These were preserved and not treated as authorization or as R3A deliverables.
- Honda contacted: NO.
- ADB used: NO.
- Runtime writes: 0.
- Vehicle connected: NO; RAM attached: NO; live listener: NO; Type111 negotiated: NO.
- No code, parser, validator, or model added.

## Sources reviewed

- `EVIDENCE_INDEX.md`, `PROJECT_STATE.md`, `NEXT_ACTION.md`.
- `step-reports/43l-post-setup-transaction-seam.md`, `43l1-callout-safety-cleanup-reachability.md`, `43l2-session-finalizer-extension-audit.md`.
- `step-reports/43m-existing-call-wrapper-seam.md`, `43n-trampoline-and-type111-oracle.md`, `43r-type111-setup-listener-contract.md`, `43s-type111-runtime-readiness-review.md`, `43s1-executable-trampoline-listener-proof.md`, `43s2-native-helper-reentrancy-readiness.md`.
- `step-reports/43t1-prep2-offline-runtime-integration-readiness.md`, `43t1-r0-post-d4-readiness-review.md`, `43t1-r1-runtime-feasibility-review.md`, `43t1-r2-api17-arm-bionic-cflite-readiness.md`.
- Historical reports for 43L, 43L1, 43L2, 43M, 43N, 43R, 43S, 43S1, 43S2, and 43T1-PREP2; reports were treated as historical evidence, not authorization.
- `research/carplay/honda-post-setup-existing-call-map.md`, `honda-request-send-plist-wrapper-audit.md`, `honda-project-child-cleanup-reachability.md`, `honda-cf-callback-ownership.md`.
- `research/runtime/api17-arm-bionic-harness-analysis.md`, `honda-cflite-ownership-static-audit.md`, `honda-native-load-seams.md`, `jmcs-load-seam-audit.md`.
- Existing untracked R3 drafts were inspected as working-tree context and not treated as independent verification.

## Candidate seams found

- **Existing wrapper:** historical static reports establish a direct local Thumb call into `_requestSendPlistResponse`, with no existing Setup-specific wrapper route shown. The 43M transaction wrapper is `MODEL_ONLY`. Connecting it would require code redirection, which R2 leaves `NO_GO` under unproven thread-stop and restoration assumptions.
- **Serializer-adjacent:** response construction, `_AddResponseStream`, streams-array operations, and serializer/status handling form a static path. No existing non-inline registration or callable mediator is evidenced. Lower-level serialization/body functions lack the Setup context or are too late for typed response mutation.
- **Callback/dispatch:** recovered delegate and global callback records have replacement semantics in the cited static audits; no append-only observer chain is established. Replacing records risks Honda-owned control/media/Type110 behavior.
- **Lifecycle/finalizer:** a Honda finalization path exists. Static reports do not establish ClarityLink child subscription, complete failure coverage, or reliable session identity in the app-facing event. This is the one area worth additional bounded static closure as a prerequisite; it is not a Setup seam.
- **Loader/preload:** historical audits do not evidence a supported jmcs plugin or preload integration path. Generic AOSP API-17 linker references do not prove Honda behavior. Persistent startup/load changes are excluded.
- **External process/proxy:** no evidenced transparent supported route. Reject any approach that breaks CarPlay authentication, injects USB traffic, performs network MITM, manually manipulates phone traffic, or persistently changes Honda state.
- **Unsafe boundary:** inline patching, thread-stop assumptions, root/su, ptrace, `/proc/<pid>/mem`, APK install, startup persistence, block-device writes, CAN writes, USB injection, and HondaHack persistent mutation are rejected as `REJECT_UNSAFE`.

Detailed table and path map: [R3A seam evidence inventory](../research/runtime/43t1-r3a-non-inline-seam-evidence-inventory.md) and [Setup seam map](../research/runtime/43t1-r3a-setup-path-seam-map.md).

## Best candidate and decision

- Best candidate for deeper **static study**: lifecycle cleanup ownership and finalizer event coverage, especially any existing non-destructive, session-addressable subscription and failure-path coverage.
- Best runtime mediation seam: none found.
- R3B is justified only as a bounded static cleanup-ownership closure. It must not add runtime activity or infer that lifecycle cleanup creates a Setup entry point.

**R3A decision:** `R3A_FOUND_CANDIDATES_NEED_STATIC_CLOSURE`

**Recommended next chunk:** `43T1-R3B — Lifecycle Cleanup Static Closure`

## ECC findings

Manual @ecc-guided evidence/safety review: keep static Honda control-flow claims separate from `MODEL_ONLY`; do not call the local BL or model wrapper an existing wrapper; treat callback replacement as replacement rather than subscription; do not infer cleanup coverage from a finalizer edge; do not upgrade Apple CF, AOSP, ARM, synthetic, or host-loopback evidence into Honda proof; retain R2’s inline-patch rejection. This is not independent ECC sign-off.

## R3C follow-up (2026-10-03)

R3C closes the bounded lifecycle/extension question without rewriting the historical R3A result. Honda has a raw session pointer internally at Setup and finalization, but no supported additive observation of both endpoints and no stable generation/non-reuse contract. Session/server delegates are whole-record copies, the global interface event is a single slot without session identity, and serializer/response state is transaction-scoped. No append-only session registration or same-identity Setup/cleanup pair was found in reviewed evidence. See [R3C pairing](../../research/runtime/43t1-r3c-entry-cleanup-pairing.md), [registration audit](../../research/runtime/43t1-r3c-registration-and-observer-audit.md), and [R3C report](43t1-r3c-session-addressable-static-seam-closure.md). R3C decision: `RUNTIME_INTERPOSITION_ARCHITECTURE_EXHAUSTED`; project recommendation: `PIVOT_AWAY_FROM_HONDA_RUNTIME_INTERPOSITION`.

## Tests, repo health, and hosted status

- Focused tests: none applicable; no parser, validator, test, or model was added.
- Full `PYTHON=.venv/bin/python ./tools/run_tests.sh`: **674 passed, 3 skipped**; self-locator **3 passed**; all configured simulator checks passed. Capture-backed scripts were skipped because private fixtures are not CI inputs.
- `.venv/bin/python tools/check_repo_health.py`: **passed**, 460 Markdown files, 115 indexed milestone/support reports, 0 curated broken links, 0 forbidden tracked extensions.
- `git diff --check`: **passed**.
- Hosted Offline CI and CodeQL: pending dispatch/result lookup for the R3A commit. Earlier runs on R2 or pre-existing R3 drafts do not verify this chunk.
