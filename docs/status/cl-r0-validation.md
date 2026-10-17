# CL-R0 repository validation

**Date:** 2026-10-17
**Scope:** public-safe publication-candidate assembly from `origin/main`; no Honda, live iPhone, or vehicle operation.

| Check | Result |
|---|---|
| Candidate base | Clean-history candidate starts at the current `origin/main` commit. It does not include the old unpublished branch history. |
| Publication selection | Selected source, tests, build tools, current status/roadmap, and concise synthetic lab summaries. Raw emulator captures, private firmware, local inventories, and vehicle-specific runner variants are excluded. |
| Focused regression | 22 tests passed in `tests/display/test_cl_imp_04_ipc_contract.py`, including full-identity Binder END rejection and explicit source-order checks that API/emulator guards precede simulator construction, display-service lookup, display-context creation, and Presentation construction. |
| Configured offline suite | 1,496 passed, 15 skipped, 0 failed. The canonical runner also passed its 3 self-locator smoke tests, all simulator JavaScript checks, and `git diff --check`. |
| P2C2 API17 build | Compiled and packaged using API17 `android.jar`; build output now uses a fresh temporary class/dex workspace. The exact latest APK SHA-256 is recorded in the local runtime receipt. |
| P2C2 API17 runtime | One isolated run verified the private instrumentation launch, synthetic content, invalid-display rejection, overlay-permission denial, and Presentation cycles. It then timed out on overlay-display removal because the probe lacked display-removal observation. The listener/poll cleanup fix is implemented and host-compiled; a subsequent run aborted before guest commands because the isolated ADB server discovered a pre-existing emulator target. Full post-fix runtime acceptance remains unverified. |
| API17 build/runtime environment | The ADB runner positively identified its own API17 emulator before guest commands. On the latest attempt, its preflight found an already-connected emulator on the fresh private server and stopped before sending commands to that target. No unidentified target was used. |
| Repository health | Index-snapshot repository health passed after the probe-listener correction: 774 Markdown files, 150 indexed reports, 0 broken curated links, 0 unindexed local paths, 0 forbidden tracked extensions. |
| Privacy and licensing | Candidate reports were sanitized and staged content scanned for secrets, local paths, and private evidence. No private firmware or captures are included. The project license decision remains unresolved; no license is added by this campaign. |
| Emulator / vehicle | No emulator run, Honda operation, or live iPhone operation was performed in this publication-preparation phase. |
| Independent review | Separate read-only ECC-guided code and security reviewers examined candidate `c398b2762bb5dbc505e527728bbdcbafa94d5d3f`; both found no new actionable issue and confirmed the stale-END and exported-probe corrections. This follow-up test/documentation commit is awaiting targeted review. Their reports are static assessments, not human safety certification. |

This file records candidate-preparation checks, not publication approval. The post-fix API17 runtime remains unverified because the isolated runner safely stopped at preflight after finding an already-connected emulator on its private ADB server. The stale-END Binder runtime sequence and post-fix P2C2 display-removal flow therefore remain outstanding. See [current status](current.md) and the [authoritative milestone manifest](milestones.json).
