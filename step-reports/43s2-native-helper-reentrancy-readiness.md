# Step 43S2 — native helper / reentrancy proof (2026-10-02)

## Decision

**`43S2_PASS`** for the offline objectives. **`GO_FOR_READ_ONLY_HONDA_PREFLIGHT`** is a recommendation for a separately scoped next milestone only. No Honda connection, ADB, patch, or deployment occurred in 43S2. Honda runtime/deployment remains disabled. This is not authorization for Type111 negotiation.

## Starting state and boundary

Starting HEAD: `6df9998cd69838400d22e8e072af4d3c3eeed77b` on `main`, initially clean. This milestone was offline only. The preserved Honda `jmcs` remains read-only. The exact 43S1 facts were retained: SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; ARM32 little-endian EABI5; Thumb BL bytes `fe f7 d1 ff` at `0x28afba`; target `0x289f60`; continuation `0x28afbe`; Thumb LR `0x28afbf`; caller context request `[SP+0x1c]`, statusOut `[SP+0x50]`, response `[SP+0x54]`, session `[r10+0xf4]`. The existing exact-artifact tests and callsite planner remain the independent validation path.

## Work completed

- Replaced synthetic project helper stubs with compiled native `native_setup_txn.c` in the same ARMv7 Thumb ELF object as the executable shim. The builder checks ARM EABI5, Thumb entry, expected helper symbols and call relocations, no undefined imports, read-only executable text, and the 4096-byte bound. The current generated text is 1346 bytes; it is produced in memory/temp storage only.
- The shim snapshots caller SP before allocating its own frame, loads request/response from the preserved frame offsets, compares statusOut against original `SP+0x50` before dereferencing, obtains session from `[r10+0xf4]` with a null-base guard, restores serializer arguments, calls the stock boundary exactly once, preserves serializer `r0`, gates completion on the local success predicate, then restores SP/registers and returns to the continuation sentinel.
- The C core performs bounded request validation, process-wide nonblocking transaction admission, generation/listener preparation, narrowly scoped `{type:111,dataPort}` append, and exact-generation commit/rollback. Borrowed pointers are synchronous-only and no pointers are retained in the 44-byte transaction object. Fixed wire sizes/offsets have compile-time assertions. Cleanup errors are returned through a shim-context diagnostic field without changing the stock serializer result.
- The same native C source was compiled and executed both as ARM code under Unicorn and as a host shared library. The host shared-library callbacks prepare the existing real loopback listener before the serializer boundary, prove immediate connection, and roll back listener/generation after serializer failure.
- The concurrency harness exercises same-emulator nested/reentrant service and serializer calls, competing Type111 calls, separate concurrent sessions, repeated IDs, contention/BUSY behavior, and a deterministic 10,000-case malformed request sweep. This is a bounded property sweep, not a coverage-guided fuzzer. A process-wide try-lock gives overlapping project mutations stock-only behavior; it does not assume Honda itself is reentrant.
- Failure-injection and listener tests cover socket setup, worker readiness, serializer and commit failures, stale generation cleanup, parent teardown, timeout/no-connect, client drop, explicit disable, FD closure, and worker joining. Existing tests use real host sockets and OS descriptor accounting.

## ECC review

ECC was requested and applied manually in this session: native ABI, ARM call boundaries, stack alignment, register preservation, borrowed-pointer lifetime, callback failure atomicity, lock ownership, listener/accepted-socket ownership, rollback, failure injection, evidence labels, and unsafe deployment boundaries were reviewed. A dedicated automated ECC reviewer was not available. High-confidence findings fixed during review: the C response validator had unused stream-ID parameters, which were removed; wire-layout static assertions and explicit synchronous/failure-atomic service callback requirements were added. Arbitrary native memory faults are not claimed recoverable.

## Evidence classification and remaining boundaries

`LAB_EXECUTABLE_CONFIRMED`: compiled project helper code executes in the same Unicorn process/address space as the Thumb shim. `LAB_HOST_RUNTIME_CONFIRMED`: compiled C transaction code uses actual host loopback sockets and its generation-owned worker/FD cleanup. `HONDA_CONFIRMED`: only the existing preserved ELF/callsite facts above. Honda interface reachability, Honda Type111 acceptance/security, actual CF response ownership/retain semantics, and Honda runtime cleanup remain unconfirmed. The clean-room C request/response structs are not Honda CoreFoundation objects. No external platform evidence is promoted into Honda evidence.

Recoverable expected project failures return status values and retain the stock serializer path. Invalid nonnull memory, invalid instructions, or stack corruption can fault the process; no signal handler or crash-recovery claim is made. The listener's production interface policy remains unresolved. An accepted Type111 socket with unknown framing must be closed and its exact generation retired; no AES/ChaCha parser is selected.

## Gate reassessment

| Gate | Result | Evidence / boundary |
|---|---|---|
| G5 executable trampoline ABI | **PASS** | Compiled ARMv7 Thumb shim and native helpers execute under Unicorn; register/SP/serializer/continuation matrix passes. Emulator evidence only. |
| G11 listener runtime contract | **PARTIAL** | Real host socket and worker work, bind/listen-before-advertise, immediate loopback connection, and explicit policy variants pass. Honda address/family/interface reachability remains an observation prerequisite. |
| G12 listener rollback / ownership | **PASS** | Actual host sockets, accepted sockets, joinable workers, exact-generation cleanup, failure injection, and descriptor accounting pass; target process mapping remains unproven. |
| G19 caller context / callout / reentrancy | **PASS for the offline seam** | Context capture is executable; native helpers use no shared transaction globals; same-emulator service/serializer nesting and host overlapping mutation return BUSY without corrupting the outer transaction; serializer is opaque/synchronous/exactly once. Honda CF response translation and Honda callback/runtime behavior are explicit later prerequisites, not guessed facts in this code. |
| G21 synchronous latency shape | **PASS structurally; not benchmarked** | Native parsing loops are bounded to at most 8 entries and do no media work. The future service adapter must keep accept/media work off this call. Host timings are not used as Honda real-time evidence. |

## Verification

- Focused ARM/helper/real-listener tests: **26 passed**.
- Configured full offline suite (`PYTHON=.venv/bin/python tools/run_tests.sh`): **400 passed, 3 skipped**.
- Host native core ran plain, ASan/UBSan, and TSan variants.
- A deterministic 10,000-case malformed-input sweep passed; this is not coverage-guided fuzzing.
- Shim build/disassembly: ARM EABI5 ELF; 1346-byte text; 5 required internal Thumb call relocations; no undefined imports; entry has Thumb state. Xcode `llvm-objdump` confirms SP snapshot precedes prologue and caller offsets use saved `r12`.
- Self-locator smoke: 3 passed.
- Simulator checks: passed.
- `git diff --check`: passed.

## Authorization recommendation and next milestone

The implementation-contract gaps are closed strongly enough to recommend a **read-only Honda network/runtime preflight** as the smallest separately reviewed activity to observe interface/address-family and target runtime facts. That preflight must not negotiate Type111, modify files/process memory, or deploy code. It was not performed here. A new readiness review must independently assess the preflight evidence and the Honda CF response bridge before any negotiation-only test. Honda runtime/deployment remains mechanically disabled.

Next action: **43T0 — read-only Honda network/runtime preflight**. The report does not authorize a controlled Type111 negotiation test.
