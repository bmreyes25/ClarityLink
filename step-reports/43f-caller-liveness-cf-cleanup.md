# Step 43F — post-Setup caller liveness and CF cleanup guarantees

**Date:** 2026-09-30
**Starting commit:** `735c26663958457f9ca8972345785a72faa69bd1`
**Scope:** offline static audit of the hash-identified Honda `jmcs` ELF, CF-style wrappers, test environment, and existing CI. No vehicle, ADB, runtime, patch, Type111 implementation, or live render test.

## Result

LLVM disassembly of `_connectionHandleMessage` (`0x28a30c`) confirms that after `AirPlayReceiverSessionSetup` (`0x28af72`) returns, the handler stores OSStatus at `[sp+0x50]`, branches on it, and on success stages the same responseOut value from `[sp+0x54]` in `r2` immediately before `_requestSendPlistResponse` at `0x28afba`. The parsed Setup dictionary remains in `[sp+0x1c]`; HTTP request/message and connection are preserved in `r6` and `r4`; the receiver/session pointer can be reloaded from `[r10+0xf4]`. The stack frame remains live through the common release path. The serializer returns before the caller releases responseOut at `0x28b052`.

`_requestSendPlistResponse` receives the direct Setup response pointer, calls `CFPropertyListCreateData` synchronously, installs the resulting bytes as the HTTP body, releases temporary CFData, and returns. HTTP response queuing and `writev` occur afterward through the connection state machine. No response mutation or retained/asynchronous CF response handoff is observed in the serializer.

Setup constructs its response with `CFDictionaryCreateMutable` (`0x28557e`). `_AddResponseStream` creates streams with `CFArrayCreateMutable` (`0x284de2`), appends with `CFArrayAppendValue`, attaches with `CFDictionarySetValue`, and releases its local array reference. Existing arrays are appended to by the same helper. Thus **stock object mutability is confirmed**, while safe arbitrary caller-side mutation remains unknown. CF-style append/set implementations invoke their configured callbacks, but callback identities and exact retain/release accounting for the relevant constructor arguments were not fully resolved.

The conceptual insertion window exists between stock response setup and serializer call. A branch/call replacement would need a trampoline/shim preserving `r4-r11`, stack alignment, the exact `r0-r3` serializer arguments, and the serializer's returned status. No safe inline area, relocation, or runtime callout is proven. Cleanup after an augmented response later fails serialization/HTTP queuing is not connected to project-owned state.

## Test environment

`pytest` is an expected test dependency (`requirements-test.txt`, `pytest>=8.3,<9`). Both README and `docs/development/testing.md` already document venv creation, installation, and `./tools/run_tests.sh`; no docs change was needed. This host's Python 3.14 environment has no pytest, so the canonical runner is blocked locally. GitHub Actions **Offline CI** completed successfully for this exact starting HEAD `735c26663958457f9ca8972345785a72faa69bd1` (run [36813310742](https://github.com/bmreyes25/ClarityLink/actions/runs/36813310742)).

## Decision gate

CALLER LIVENESS: COMPLETE

SERIALIZER INPUT: DIRECT_SAME_OBJECT

SERIALIZATION SYNC: YES

RESPONSE MUTABILITY: CONFIRMED_MUTABLE

STREAMS ARRAY MUTABILITY: CONFIRMED_MUTABLE

CLEANUP CONTRACT: PARTIAL

INSERTION WINDOW: FOUND

CALLOUT FEASIBILITY: NEEDS_TRAMPOLINE

CANONICAL TEST ENV: BLOCKED

SEAM IMPLEMENTATION DESIGN: NEEDS_MORE_STATIC_PROOF

IMPLEMENTATION READY: NO

LIVE TEST READY: NO

JMCS INTEGRATION READY: NO

EXTERNALDISPLAY LIVE RENDER READY: NO

LD_PRELOAD: PARKED

NEXT STATIC QUESTION: Which exact callback functions are installed in Honda's response dictionary and streams array, and what existing handler/session edge cleans project state if serialization or response queuing fails?

## Evidence limits

All instruction and CF conclusions are `HONDA_CONFIRMED` only for the static path in the named ELF. Callback ownership, race exclusion, arbitrary mutation safety, and cleanup for hypothetical project resources are `HONDA_UNKNOWN` or `HONDA_INDIRECT_CANDIDATE`. Existing Python model results remain `SYNTHETIC_TEST_VALUE`; MHI2 remains `EXTERNAL_PRIOR_ART`; future append mechanics remain `HYPOTHESIS`. No readiness gate advanced.

Detailed instruction, ownership, and failure tables are in [Honda post-Setup caller liveness](../research/carplay/honda-post-setup-caller-liveness.md).
