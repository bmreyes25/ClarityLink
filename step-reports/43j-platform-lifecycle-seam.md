# Step 43J — Honda platform lifecycle seam (offline)

**Base:** `39ba911e6655f93d23d1a9fb65bfe1a81d6720c4`  
**Artifact:** `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` (MATCH).  
**Scope:** static binary analysis plus synthetic project-only lifecycle model. No car connection, deployment, patch, interposer, or Type111 implementation.

## Results

The recovered Honda delegate is 44 bytes / 11 words. Its population pattern by offset exactly matches the pinned R11B 11-slot layout: context at +0; null +4/+8; populated +0xc/+0x10/+0x14; null +0x18; populated +0x1c/+0x20/+0x24/+0x28. `HONDA_R11B_DELEGATE_FINGERPRINT: STRONG` as a structural fingerprint only; no Honda source ABI names are inferred from it.

`AirPlayReceiverSessionPlatformControl` compares `tearDownStreams`, extracts `streams`, gets each dictionary's `type`, and routes 100/101 into separate state slots and 110 through the platform stream path. Unknown types log and continue. The stream branch proceeds through `_UpdateStreams` / `_TearDownStreams`; it never loads or calls `session+0x24`. The indirect call through `session+0x24` is in the separate unmatched-command path (`0x28d2c2–0x28d2d6`). Type111 therefore currently takes the ignored/unsupported unknown-type path; it is not delivered to application control.

`_AirPlayHandleSessionControl` is populated in the delegate and is reachable from PlatformControl's other-command fallback, with the platform's command/qualifier/params/output passed as callback arguments. It is not reachable for recognized `tearDownStreams` or `setUpStreams` branches. This rejects it as the project stream lifecycle attachment. No separate application delegate delivery for teardown is shown. Honda application behavior for arbitrary unrelated controls is outside this lifecycle conclusion.

`_Finalize` (`0x284d24`) calls `AirPlayReceiverSessionPlatformFinalize` (`0x28cd60`) once at a single direct call site per CF runtime finalizer invocation. PlatformFinalize tolerates `session+0x10 == NULL`; otherwise it stops HID, calls `_TearDownStreams(session, NULL)`, frees platform state, clears the pointer, and returns. The session pointer is still the active finalizer argument. All recovered PlatformFinalize calls reduce to this direct caller; no outside caller was found. The cleanup is independent of HTTP state and prior `tearDownStreams`. Exact-once is proven at the static finalizer call-site model, not as a claim about impossible runtime reentrancy.

PlatformControl and PlatformFinalize are `.symtab` globals and absent from `.dynsym` in this artifact, so they are not dynamically exported symbols. Observed calls are internal direct ARM/Thumb branches, not PLT calls. PlatformFinalize has the single finalizer call site. PlatformControl has setup and teardown callers previously recorded in Steps 43I/38 plus its internal callback-table fallback; this step did not claim symbol visibility implies a safe extension mechanism.

## Lifecycle decision

The exact death reason is `DIAGNOSTIC_ONLY` for child cleanup correctness if a project child is keyed by session identity and cleanup is unconditionally tied to PlatformFinalize. The semantic two-signal platform lifecycle is proven, but safe extension/interposition and the post-Setup child creation seam are not. The external registry and idempotent cleanup contract are ready for an offline prototype. No claim is made that the adapter can yet be installed in Honda.

## Synthetic model and verification

Added `src/carplay-session-model/project_lifecycle.py` and focused tests covering type-specific teardown, duplicates, finalization, concurrent teardown/finalization, malformed/unknown inputs, UI/unknown commands, cleanup exceptions, stock errors, stopped children, and pointer-generation reuse. The model invokes stock once with the original request and leaves Honda Type110/audio state outside project state.

Results: focused lifecycle tests: 10 passed. `PYTHON="$PWD/.venv/bin/python" ./tools/run_tests.sh`: 251 passed, 4 skipped; locator smoke (3) and simulator JavaScript checks passed. Capture-backed replay remains skipped because private fixtures are unavailable; it is not claimed as passed.

## Decision gate

| Gate | Result |
|---|---|
| `HONDA_R11B_DELEGATE_FINGERPRINT` | STRONG |
| `TEARDOWNSTREAMS_TO_DELEGATE_CONTROL` | NO |
| `HONDA_APPLICATION_CONTROL_CAN_SEE_TEARDOWNSTREAMS` | NO |
| `TYPE111_CURRENT_PLATFORMCONTROL_RESULT` | IGNORED |
| `PLATFORMCONTROL_REQUEST_AWARE_SIGNAL` | PROVEN |
| `PLATFORMFINALIZE_FULL_SESSION_SIGNAL` | PROVEN |
| `PLATFORMFINALIZE_CALL_COUNT_MODEL` | ONCE_PER_FINALIZATION |
| `SESSIONDIED_FOR_CLEANUP_CORRECTNESS` | DIAGNOSTIC_ONLY |
| `DELEGATE REPLACEMENT REQUIRED` | NO |
| `PROJECT SESSION REGISTRY MODEL` | READY |
| `PROJECT CHILD LIFECYCLE` | READY_FOR_OFFLINE_PROTOTYPE |
| `POST-SETUP SEAM` | NEEDS_MORE_STATIC_PROOF |
| `JMCS INTEGRATION DESIGN` | NOT READY |
| Live test / Type111 live / ExternalDisplay live | NOT READY |
| `LD_PRELOAD` | PARKED |

**Biggest blocker:** proving a safe, supported way to observe PlatformControl/PlatformFinalize and create the registry child after successful Setup without mutating Honda state.  
**Next action:** prototype and exercise the external registry/stock-delegating adapter offline, then finish static proof of the post-Setup creation seam.
