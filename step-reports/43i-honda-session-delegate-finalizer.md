# Step 43I — Honda session delegate and finalizer audit

## 1. Scope and starting state

Offline reverse-engineering only. No vehicle, ADB, live CarPlay, Honda execution, jmcs patching, or Type111 implementation. Starting HEAD was `9dd53a75a5c162b3a7f6605bc7b167fc35d2b311`, clean, with the earlier Step 43G/43H commits preserved. The jmcs reference hash matched exactly: `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`.

## 2. Tools and address method

Used the existing `tools/elf_va_map.py` PT_LOAD mapper to map VAs to file data and decode literal/table words. Thumb pointers retain bit 0 in stored values and are normalized for disassembly. Used Xcode `llvm-objdump`, `strings`, and preserved `research/native/jmcs/symbols.json`/`strings.txt`. Compared external sources only as `EXTERNAL_PRIOR_ART`; no external ABI assumption was used to label Honda slots.

## 3. Honda session class, finalizer, and delegate

The class table at `0x3427d4` names `AirPlayReceiverSession` and points to `_Finalize` (`0x284d24`). `AirPlayReceiverSessionGetTypeID` (`0x284e28`) registers the table; `AirPlayReceiverSessionCreate` (`0x284e58`) calls `_CFRuntimeCreateInstance` with object size `0x1420`.

`_Finalize` loads session field `+0x20` as a callback and `+0x14` as its context, calls the callback first (`0x284d30–0x284d36`), then performs platform, screen, stream, control, timing, clock, dispatch-source, AES-CBC, screen-object, server, and dispatch cleanup. `AirPlayReceiverSessionSetDelegate` (`0x285040`) copies 44 bytes / 11 words to session `+0x14`.

`_AirPlayThread` constructs and installs a 28-byte server delegate. Its `sessionCreated` slot at server delegate `+0x14` points to `_AirPlayHandleSessionCreated` (`0xaf04c`); `sessionFailed` at `+0x18` points to `_AirPlayHandleSessionFailed` (`0xa6144`). `AirPlayReceiverSessionCreate` calls the session-created function from server offset `+0x24`, confirming the callback path.

`_AirPlayHandleSessionCreated` allocates an application context, populates the 44-byte session delegate, and calls SetDelegate at `0xaf252`. Delegate offset `+0x0c` contains `_AirPlayHandleSessionFinalized` (`0xae654`, stored Thumb pointer `0xae655`). It is non-null. Other recovered callbacks include `_AirPlayHandleSessionControl`, `_AirPlayHandleSessionCopyProperty`, `_AirPlayHandleModesChanged`, `_AirPlayHandleRequestUI`, `_AirPlayHandleSessionDuckAudio`, and `_AirPlayHandleSessionUnduckAudio`. The complete table and offsets are in [the Honda lifecycle research note](../research/carplay/honda-session-delegate-lifecycle.md).

## 4. Stream teardown and three lifecycle layers

`AirPlayReceiverSessionTearDown` (`0x2852ec`) passes its request through `AirPlayReceiverSessionPlatformControl` (`0x28cd88`) with the `tearDownStreams` CFString (object VA `0x3373d7`, text VA `0x3373e7`). PlatformControl inspects an array of stream dictionaries and branches on types 100, 101, and 110. This is request-aware stream handling; it does not establish a Type111 callback or Type111 semantics.

The CF object finalizer is a distinct later lifetime signal. Its application callback runs before `AirPlayReceiverSessionPlatformFinalize`, screen teardown, two stream teardowns, control/timing/clock cleanup, AES finalization, and remaining object releases. Step 43H's HTTP connection-finalizer-to-session-TearDown edge remains conditional on the per-connection session pointer. Session object destruction and session teardown must not be collapsed into one event.

## 5. External prior art

Pinned WirelessCarPlay, R11B, Hyundai 2018, and MHI2 references and their distinctions are recorded in [the prior-art note](../docs/research/airplay-session-lifecycle-prior-art.md). All are `EXTERNAL_PRIOR_ART`; the source lineages show similar delegate/finalizer and separate stream-teardown concepts, but do not establish Honda ABI or implementation behavior.

## 6. Project-child lifecycle and limits

The existing Honda `_AirPlayHandleSessionFinalized` is a proven full session-object finalization callback and a plausible future application-level cleanup point. The current delegate is copied wholesale; replacing it with a project-only delegate would wipe Honda callbacks. A future integration must preserve the callback table, context, and required ordering.

The request-aware stream path is Honda-confirmed, but a project child notification/subscription is not. The binary's recognized stream types do not prove Type111 support. Therefore `PROJECT_CHILD_ATTACHMENT_POINT` is a **candidate** for finalization; request-aware project stream attachment is **unknown**; the two-signal child lifecycle is `NEEDS_MORE_STATIC_PROOF`. Keep Type110, its crypto, center-screen state, and audio outside project-only cleanup.

## 7. Tests and readiness

No model behavior changed. `PYTHON="$PWD/.venv/bin/python" ./tools/run_tests.sh` passed: 241 passed, 4 skipped; locator standard-library smoke tests 3 passed; simulator JavaScript checks and the Type111 failure-twin check passed. Capture-backed replay scripts were skipped because their ignored/private capture fixtures are not CI inputs. `git diff --check` passed. No test executes Honda code.

```text
HONDA SESSION DELEGATE API: PROVEN
HONDA SESSION DELEGATE LAYOUT: PROVEN (44-byte table; all written slots resolved)
HONDA SESSION CREATED CALLBACK: PROVEN
SESSION CFRUNTIME CLASS: PROVEN
SESSION CFRUNTIME FINALIZER: PROVEN
FINALIZE CALLBACK SLOT: PROVEN
HONDA EXISTING FINALIZE CALLBACK: PROVEN (_AirPlayHandleSessionFinalized)
TEARDOWNSTREAMS PLATFORMCONTROL: PROVEN
TYPE110-ONLY TEARDOWN DISTINGUISHABLE: YES (in request-aware type parser; this does not imply Type111 support)
SESSIONDIED PATH: PARTIAL (literals present; full semantic path not traced)
FULL SESSION CLEANUP SIGNAL: BOTH (TearDown path and object finalizer exist; only finalizer is object-finalization callback)
PROJECT CHILD LIFECYCLE MODEL: NEEDS_MORE_STATIC_PROOF
POST-SETUP SEAM: NEEDS_MORE_STATIC_PROOF
JMCS INTEGRATION DESIGN: NOT READY
JMCS NO-OP TEST: NOT READY
TYPE111 LIVE: NOT READY
EXTERNALDISPLAY LIVE RENDER: NOT READY
LD_PRELOAD: PARKED
BIGGEST BLOCKER: Honda has a proven session finalizer callback but no proven request-aware project-child callback or supported way to chain new child behavior while preserving the existing delegate.
```

## 8. Next action

Trace the application-owned `tearDownStreams` request path into the existing Honda session control/platform callbacks and establish whether a project stream child can receive Type111-specific teardown while Type110 remains untouched. Until then, retain the finalizer only as a candidate cleanup safety net and keep implementation gates closed.
