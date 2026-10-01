# Step 43G — Honda CF callbacks and failure cleanup edges

**Date:** 2026-09-30
**Starting commit:** `0e35b2b4ed9823e920cc0416da6221fae5f6a2b4`
**Scope:** offline static evidence review only. No vehicle, ADB, Honda runtime, binary patch, Type111 implementation, live hook, or render test.

## Result

The recorded ELF symbol/data references identify the CFL callback tables and their wrapper functions. Array callbacks map to retain/release/equality wrappers that delegate to `CFLRetain`, `CFLRelease`, and `CFLEqual`; dictionary key/value tables contain the corresponding wrappers and key hash. However, the Setup dictionary constructor arguments at `0x28557e` have not been mapped unambiguously to those named tables, and the Type110 entry dictionary's callback arguments and local release sites are not completely recovered. Table presence is not constructor-use proof. Exact callback and ownership ledgers therefore remain partial.

The caller synchronously serializes the Setup response to separate `CFData` and releases the original response after the serializer returns. Property-list creation failure returns an HTTP 500 path before body installation. Body installation failure can occur after body storage/length state has been changed, so the HTTP message may be partially mutated. The handler then attempts its error response path. `HTTPConnectionSendResponse` commits/queues serialized HTTP state after the CF graph has been released; later `writev` failure stops the connection and may invoke a connection callback. The callback target and its relationship to session/project state are not established. Queue/write failure cannot affect the released CF graph, but could leave hypothetical project-owned resources without a cleanup edge.

The inspected caller path does not statically show the response escaping before serialization, but does not establish dispatch/thread exclusivity or runtime race freedom. Readiness remains `NEEDS_MORE_STATIC_PROOF`.

## Decision gate

DICTIONARY CALLBACKS: PARTIAL

ARRAY CALLBACKS: PARTIAL

STOCK OWNERSHIP LEDGER: PARTIAL

PROJECT OWNERSHIP CONTRACT: PARTIAL

SERIALIZATION FAILURE CLEANUP: PARTIAL

HTTP QUEUE CLEANUP: PARTIAL

CALLER SIDE MUTATION RACE: NO_STATIC_EVIDENCE

CANONICAL TEST ENV: NOT_CHANGED

SEAM IMPLEMENTATION DESIGN: NEEDS_MORE_STATIC_PROOF

IMPLEMENTATION READY: NO

LIVE TEST READY: NO

JMCS INTEGRATION READY: NO

EXTERNALDISPLAY LIVE RENDER READY: NO

LD_PRELOAD: PARKED

NEXT STATIC QUESTION: Can the exact Setup dictionary callback arguments and Type110 entry construction/release sites be recovered from the identity-verified `jmcs` ELF, while also identifying the connection failure callback's target and any session teardown edge?

Detailed callback, ownership, failure, and rollback tables: [Honda CF callback ownership](../research/carplay/honda-cf-callback-ownership.md).

## Test environment and validation

The existing testing guide documents venv setup and `requirements-test.txt`; pytest remains unavailable in the current local Python environment, so the canonical runner was not run here. Existing dependency instructions were left unchanged. Focused negotiation tests, changed-document link checks, and `git diff --check` are reported in the commit summary after execution.
