# 43T1 R7C7 final framework race and software closure

**Date:** 2026-10-08  
**Decision:** `R7C_SOFTWARE_PASS_PENDING_EXACT_HEAD_GATES`

## Lifecycle root cause

The test controller requests `finish()` on the main handler and awaits lifecycle completion off-main. The main looper remains responsive. The combined run exposed process reclamation because the tested Activity was the only foreground component; ActivityManager reclaimed the empty process before normal lifecycle callbacks. A test-only guard Activity keeps the process alive, and the repeat runner waits for it to resume before relaunching. This preserves the production lifecycle path and avoids extending timeouts.

One fresh 25-repeat run initially logged an `IllegalStateException` when the teardown test hook found no active socket because both diagnostic operations had already completed. The hook was made idempotent for the no-active-operation state. The rerun recorded 25/25 lifecycle passes and no close error.

## Acceptance evidence

- Final combined API17/Dalvik run: production socket fault matrix PASS; both H.264 streams decode/post; cumulative Type111 Surface, Presentation, peer-close, and Activity destroy cases PASS; 100/100 socket-inclusive cycles; owner/FD counts zero; stale JNI handle rejected; `RESULT=PASS`, `ERROR=NONE`.
- Independent Activity destroy stress: 25/25 PASS after the final test-hook change.
- Host repository suite: 902 passed, 14 skipped; locator checks 3 passed; simulator JS checks and whitespace checks passed.
- ASan/UBSan and TSan socket and integrated runs passed.
- NDK r23c ARMv7 build passed; API17 symbol audit reported no unknown imports. Artifact SHA256: `ddfa2efc2ace3667f1889032770a1011a28c42648907d8632a30a4dbe31d9e37`.
- Repository health and `git diff --check` passed before final evidence refresh; rerun after docs.

## Scope and gate

This closes R7C software evidence only. Honda, physical device, vehicle, real iPhone negotiation, and MFi evidence remain unresolved and outside the scope. Commit/push, exact-head Offline CI and CodeQL, and PR #17 merge are still required. R7D starts from the resulting merge head.

See [lifecycle diagnosis](../research/runtime/r7c7-activity-lifecycle-root-cause.md), [socket matrix](../research/runtime/r7c7-native-socket-fault-matrix.md), [combined run](../research/runtime/r7c7-combined-acceptance-run.md), and [R7D entry decision](../research/runtime/r7c7-r7d-entry-decision.md).

## Hosted verification and merge closure

R7C implementation commit `f24255c58ea000255c37d1dea28e5b26a569745b` received exact-head Offline CI PASS and CodeQL PASS. PR #17 merged into `main` at `f9ef5fa3f24ed89b32d0eddf62b1065fbef66562`. R7D began from that merge head in a separate worktree. Final R7C decision: `R7C_HONDA_ADAPTER_LAYER_OFFLINE_PASS`; R7D entry opened for offline simulation only.
