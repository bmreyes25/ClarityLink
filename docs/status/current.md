# Current project status

**Updated:** 2026-10-19
**Campaign:** CL-R4 reliability completion and public-source publication
**Repository main baseline:** `bf4802246fe6c7e3bbf2c21edee23430fe9bb92c`
**Reliability PR:** [#37](https://github.com/bmreyes25/ClarityLink/pull/37), open and awaiting an approving GitHub review
**Authoritative manifest:** [milestones.json](milestones.json)

## Verified state

| Area | State | Evidence and limits |
|---|---|---|
| CL-R0 repository foundation | Established | See [CL-R0 validation](cl-r0-validation.md). The repository has no selected license. |
| CL-R1 warning preemption | Lab PASS | Deterministic Binder/Handler/View race tests suppress stale drawing and restore fresh frames. This is not Honda warning-priority evidence. |
| CL-R2 API17 isolation and crash recovery | Lab PASS | Owned API17 emulator process checks and controlled crash-dialog handling have been exercised. Historical FinalizerWatchdog behavior remains unattributed and unreproduced. |
| CL-R3 Binder-to-View | Lab PASS | Malformed Binder input, generations, pixel checks, process death, crash recovery, and cleanup have prior API17 evidence. No physical scanout is claimed. |
| CL-R4 reliability | **PARTIAL** | The latest exact-source API17 run passed CL-R4-01 (in-flight producer death) on source fingerprint `8fbcec8f744b8228f973df1a693acda4343b63c6c2b2e2c9a8f2a218a2c2d2e8`, APK SHA-256 `04002a9fd20b72f86fc7c4f423dbbe7f2d981afa96b8ef4313c1226091e26faa`. It proved the ordered active-session preclaim was rejected with the authorized Type110 sink preserved, 23/23 cross-UID operations denied, producer restart, fresh H.264 frames, generation fencing, and zero PFD/retained bytes. Separate earlier candidate evidence includes CL-R4-04, P02, and P03, but does not combine into a single final-source matrix. P04/P05/P06/P08 and aggregate P12 remain unverified. See ignored local acceptance reports under `build/cl-r4-acceptance-*`. |
| CL-R5 Type111 control model | Synthetic lab model | Capability, setup, navigation eligibility, presentation, geometry, and VideoConfig are represented in the lab. Honda SETUP schema and authenticated receiver-session delegation are unknown. |
| CL-R6 secondary output host | Synthetic lab model | Lab output geometry, warnings, withdrawal, restoration, and lifecycle are exercised. No Honda-owned instrument-cluster frame-admission interface is established. |
| CL-R7 end-to-end laboratory demonstration | **API17 LAB PASS** | The current candidate passed Type110-first and Type111-first on API17 / Android 4.2.2. Both runs verified actual MediaCodec H.264 output, Binder/PFD delivery, decoded pixels, warning withdrawal and fresh-frame restoration, real View-process death and reattachment, Type110 continuity, and cleanup. APK SHA-256: `26a659e5433ea168fb157f2cbae150d792b5ce275c8381f4e883d30f239066fc`. Evidence is preserved locally under ignored `build/cl-r7-lab-20261019-124248-19895/`. |
| Honda hardware validation | Not started | Requires documented OEM contracts, separate authorization, and an independently reviewed parked-vehicle plan. |
| `safeForHonda()` | `false` | Production integration remains disabled. |

## Current CL-R4 candidate run

The canonical runner is `tools/run_cl_r4_acceptance.py` (also `tools/run_cl_r4_acceptance.sh`). The latest run at `build/cl-r4-acceptance-20261019-123156-10607` records CL-R4-01 PASS and all unselected cases as NOT_RUN; its overall result is PARTIAL. It includes the API17 cross-UID attack start response and receipt, plus application-side rejection evidence. CL-R4-04, P02, and P03 have separate prior candidate passes; their fingerprints differ from the latest run and they do not combine into a final-source matrix PASS.

The configured offline suite passed **1,287 tests, 18 skipped**, plus three self-locator smoke tests, simulator checks, and whitespace validation after the unauthorized-start lifecycle fix. Host results do not substitute for API17 acceptance.

## Publication and review

PR #37 is the current reliability branch. Its previously observed Offline CI failure occurred in `tools/check_repo_health.py`, before pytest, because pinned hashes in `docs/status/cl-r0-review-scope.json` were stale for changed tracked files. CodeQL and language-analysis jobs passed, but those checks do not replace Offline CI. The branch has no recorded approving GitHub review. Do not bypass protected-main requirements.

The worktree contains public-safe source and test changes that still need final-source acceptance, scope-hash refresh, PR checks, and publication. Generated emulator evidence remains local and ignored. Historical worktrees and private research are preserved.

## Honda integration status

No genuine Honda Type111 capability advertisement, SETUP handler, authorized stream delegation, or same-session transport contract has been established. No supported Honda Display 1 frame-admission interface, display ownership contract, geometry contract, warning precedence contract, or restoration contract has been established. No OEM API is inferred from the synthetic adapters.

## Next actions

1. Implement the missing API17 fault interleavings and aggregate resource assertions, then freeze and run the full CL-R4 matrix on one source/APK. The current candidate's CL-R7 two-order regression has passed.
2. Refresh the PR #37 stale review-scope hashes after exact-source review, rerun Offline CI and CodeQL, and publish only reviewed, public-safe source through protected GitHub review.
3. Keep Honda integration disabled until supported receiver and instrument-cluster contracts are established.
