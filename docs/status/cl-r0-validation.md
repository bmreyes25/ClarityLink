# CL-R0 repository validation

**Date:** 2026-10-17
**Scope:** public-safe publication-candidate assembly from `origin/main`; no Honda, live iPhone, or vehicle operation.

| Check | Result |
|---|---|
| Candidate base | Clean-history candidate starts at the current `origin/main` commit. It does not include the old unpublished branch history. |
| Publication selection | Selected source, tests, build tools, current status/roadmap, and concise synthetic lab summaries. Raw emulator captures, private firmware, local inventories, and vehicle-specific runner variants are excluded. |
| Focused regression | 25 tests passed for Binder generation ownership, probe export/guard contracts, and existing production-admission boundaries. |
| P2C2 API17 build | Compiled and packaged using API17 `android.jar`; build output now uses a fresh temporary class/dex workspace. The exact latest APK SHA-256 is recorded in the local runtime receipt. |
| P2C2 API17 runtime | One isolated run verified the private instrumentation launch, synthetic content, invalid-display rejection, overlay-permission denial, and Presentation cycles. It then timed out on overlay-display removal because the probe lacked display-removal observation. The listener/poll cleanup fix is implemented and host-compiled; a subsequent run aborted before guest commands because the isolated ADB server discovered a pre-existing emulator target. Full post-fix runtime acceptance remains unverified. |
| API17 build/runtime environment | The ADB runner positively identified its own API17 emulator before guest commands. On the latest attempt, its preflight found an already-connected emulator on the fresh private server and stopped before sending commands to that target. No unidentified target was used. |
| Repository health | Index-snapshot repository health passed before the final probe-listener correction; rerun after committing the current candidate. |
| Privacy and licensing | Candidate reports were sanitized and staged content scanned for secrets, local paths, and private evidence. No private firmware or captures are included. The project license decision remains unresolved; no license is added by this campaign. |
| Emulator / vehicle | No emulator run, Honda operation, or live iPhone operation was performed in this publication-preparation phase. |
| Independent review | Separate ECC-guided reviews of candidate `408292e73e38bfd9d6fbba19efe131d21a1e2421` found one P2 stale-generation teardown defect and one P1 exported display-probe issue (plus a P2 exported Test 4 probe). Fixes are implemented; the exact corrected commit still requires targeted review before publication. |

This file records candidate-preparation checks, not publication approval. See [current status](current.md) and the [authoritative milestone manifest](milestones.json).
