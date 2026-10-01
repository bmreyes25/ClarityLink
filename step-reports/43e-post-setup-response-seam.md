# Step 43E — Honda post-Setup / pre-serialization seam audit

**Date:** 2026-09-30
**Starting commit:** `6ccdae455b26ad99ad0aa260e57cbbb9183cb82c`
**Scope:** offline static Honda `jmcs` analysis and synthetic rollback model. No vehicle, ADB, runtime, patching, Type111 implementation, or live render test.

## Result

The ordinary `_connectionHandleMessage` path (`0x28a30c`) calls `AirPlayReceiverSessionSetup` at `0x28af72` with receiver/session in `r0`, parsed request in `r1`, and `&response` at caller `sp+0x54` in `r2`. On zero status, that exact output is passed at `0x28afba` to `_requestSendPlistResponse` (`0x289f60`). The serializer synchronously creates binary-plist `CFData` and installs its bytes in the HTTP message; the caller releases the response at `0x28b052` after the helper returns. The request and session arguments remain in the caller context across the call.

Setup creates a mutable response dictionary (`0x28557e`); `_AddResponseStream` (`0x284db8`) obtains/creates a mutable `streams` array and appends stock entries. Setup publishes the response at `0x286260` on success. This establishes a structural caller-side append candidate but only indirect evidence of post-return mutability. No runtime CF call, race, reentrancy, or hook ABI is proven. Setup's own error path releases its local response and does not enter the serializer path.

Honda's original request remains available for type inspection. Honda logs/skips unsupported Type111 and continues the stream loop; recognized Type110 processing and final PlatformControl still determine Setup success. Therefore the future detection model is `ORIGINAL_REQUEST_AFTER_STOCK`, subject to caller-liveness proof before any implementation. A split request is not indicated by the static behavior.

The existing offline model/tests already represent stock-first cloning/appending and rollback. They are useful only as `SYNTHETIC_TEST_VALUE`: they cannot establish CF retain/release correctness or Honda's Type111 schema. No Type111 code or live gate was changed.

## Decision gate

SETUP RESPONSE LIFETIME: COMPLETE

RESPONSE MUTABILITY: INDIRECT_CANDIDATE

STREAMS ARRAY MUTABILITY: INDIRECT_CANDIDATE

REQUEST AVAILABLE AT SEAM: YES

SESSION AVAILABLE AT SEAM: YES

FUTURE DETECTION MODEL: ORIGINAL_REQUEST_AFTER_STOCK

ROLLBACK CONTRACT: WRITTEN

STOCK RESPONSE PRESERVATION MODEL: PASS

TYPE110 PRESERVATION: PASS

PRIOR ART COMPARISON: WRITTEN

SEAM CLASSIFICATION: SAFE_STATIC_CANDIDATE

IMPLEMENTATION DESIGN READY: NO

LIVE TEST READY: NO

JMCS INTEGRATION READY: NO

EXTERNALDISPLAY LIVE RENDER READY: NO

LD_PRELOAD: PARKED

NEXT STATIC QUESTION: What exact caller instructions and CF/runtime guarantees establish safe response/request/session liveness and failure cleanup from Setup return through serialization?

## Evidence classes and limitations

- `HONDA_CONFIRMED`: caller passes the exact Setup response to synchronous serializer; +1 response ownership is released after serialization; Setup builds mutable dictionary/array and appends stock entries; request/session remain available in caller context; stock unsupported Type111 is skipped.
- `HONDA_INDIRECT_CANDIDATE`: caller-side post-return mutation of the response and nested array. The observed constructors/helpers are mutable, but no caller-side mutation occurred in stock code.
- `HONDA_UNKNOWN`: safe third-party CF mutation, exact hook liveness/ABI/reentrancy, serializer-failure cleanup for hypothetical project resources, Type111 fields/acceptance, capability prerequisite, UUID relation, crypto, and renderer.
- `EXTERNAL_PRIOR_ART`: MHI2 stock-first clone/append and fail-closed hook policy; no Honda design inheritance claimed.
- `SYNTHETIC_TEST_VALUE`: offline model preservation and failure injection only.
- `HYPOTHESIS`: a future project-owned optional append can be made fail-soft while preserving stock response.

Detailed lifetime/failure tables: [Honda seam analysis](../research/carplay/honda-post-setup-response-seam.md). Existing offline model: `src/claritylink-negotiation/` and `tests/negotiation/test_setup_contract.py`.
