# Step 40 — Honda hook integration boundary

**Base:** 0855d31 (Step 39)
**Scope:** exact offline jmcs identity/ABI analysis plus host-only hook safety models. No vehicle or live process work.

## Evidence recovered

The local target matches ELF32 little-endian ARM ET_DYN, size 13,406,720 bytes, SHA-256 cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232, .text SHA-256 ca4abfd2f2c1f5f7fe88b4b0bde9e920d22b454f2a699b7de1f4984c901278eb. It has Android ID notes and no GNU build-id.

The Setup ABI is OSStatus AirPlayReceiverSessionSetup(session, request, responseOut): r0, r1, r2; r0 returns status. _connectionHandleMessage calls it at 0x28af72, passes responseOut at caller sp+0x54, checks status, sends the successful same response at 0x28afba, and releases it after synchronous serialization. The caller's stack is 8-byte aligned at the call.

_requestProcessInfo calls AirPlayCopyServerInfo at 0x28a158; its r0 result is the serverInfo dictionary used for /info serialization and later released. Its DWARF signature maps four parameters to r0-r3. Candidate function/call-site bytes, prologues, and hazards are listed in research/carplay/honda-hook-fingerprints.md.

## Implemented

- Read-only ELF32 identity and .text hashing with PT_LOAD extraction and GNU build-id parsing.
- Exact all-invariants build gate plus exact instruction fingerprint checks.
- Synthetic /proc/maps parsing, PT_LOAD load-bias calculation, executable/path/ambiguity/range checks, and Thumb pointer-bit handling.
- Mock address-space transaction that preflights every candidate before activation, applies all or none, restores original bytes, verifies restoration, and supports retry after an injected restore failure.
- Host OFF, NOOP, OBSERVE, and gated AUGMENT semantics. NOOP/OBSERVE delegate the exact request to stock, return the exact stock object/result, avoid listener/KDF/Type111 work, and store bounded secret-free diagnostics.

## Decision

The selected call-site candidates are the serverInfo builder call at 0x28a158 and Setup call at 0x28af72. Persistent augmentation also requires lifecycle coordination at session start/teardown. These are control-plane points; no media hook is justified.

**The actual Honda hook harness is NOT READY.** There is no ARMv7 Thumb-2 call-site shim/original-call veneer, branch-range validation, executable memory/page/cache handling, thread synchronization, live restore path, or independently validated original-call bridge. Function-entry trampolines are also not ready: several entries begin with PC-relative literal loads or ADR/LDRD. A successful mock transaction is not live-safety evidence.

Type111 trigger, response acceptance, KDF compatibility, secondary TCP, and secondary H.264 remain unproven. Step 41 is drafted but not ready/executed.

## Verification

- Focused affected suite (Honda, transport, negotiation, interposer, integration, renderer): 91 passed, 31 subtests passed.
- Step 40 Honda tests: 21 passed.
- Maintained suite under tests/ plus src/claritylink-renderer/tests: 104 passed, 31 subtests passed.
- git diff --check: passed.
- Repository-root pytest collection still fails on unrelated research import-path and duplicate-module issues; no unrelated test infrastructure was changed.
