# Step 40B — reversible ARMv7 Thumb-2 call-site model

**Date:** 2026-09-29
**Starting commit:** `61865f2764befcd23ff8b26bfa7cb73dcce2fa07`
**Scope:** offline static verification, host models, and synthetic ARM emulation only.

## Result

The selected Honda call sites are both direct four-byte Thumb `BL` instructions. A checked encoder/decoder exactly round-trips the pinned instructions and an optional Unicorn fixture executes a synthetic caller → veneer → representative wrapper → stand-in original function → original continuation chain. Synthetic transaction tests verify exact byte restoration and inject write, partial-write, read, corruption, and stale-process failures.

The design does not need a stolen-prologue trampoline: interception occurs at a call instruction, so the wrapper can make a normal call to the untouched original target and return the stock result. The veneer and mock transaction are **not a live patch engine**. No Honda process memory is read or written.

## Revalidated Honda evidence

The inspected `extracted/system/system/bin/jmcs` and `extracted/system-vendor/system/bin/jmcs` are byte-identical, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`.

| Candidate | Static callsite bytes | Disassembly | Return address |
|---|---|---|---|
| INFO | `0x28a158`: `f8 f7 bc fd` | Thumb `BL 0x282cd4` (`AirPlayCopyServerInfo`) | `0x28a15c` |
| Setup | `0x28af72`: `fa f7 b5 fa` | Thumb `BL 0x2854e0` (`AirPlayReceiverSessionSetup`) | `0x28af76` |

`objdump` was run against the local ELF for each range. The Python decoder recovers displacements `-0x7488` and `-0x5a96` respectively, and re-encodes the original instruction bytes exactly. Setup’s r0/r1/r2 contract and aligned stack are recorded in `research/carplay/honda-hook-abi.md`; the INFO site supplies four register arguments as described there. The actual Honda target functions were not executed.

## Implementation and verification

- `src/claritylink-honda/thumb_call.py` implements strict little-endian Thumb `BL` decoding/encoding, range validation, and explicit code-address/function-pointer conversions.
- `encode_thumb_veneer()` returns a 12-byte, four-byte-aligned literal veneer (`ldr.w r12,[pc,#4]`, `bx r12`, padding, tagged 32-bit pointer). Clang’s ARMv7 assembler confirmed the opcode words.
- `src/claritylink-honda/callsite.py` creates a four-byte mock patch only after checking that the recorded instruction decodes to the stock target. The strategy changes no other Honda instruction bytes.
- `tests/honda/test_thumb_call.py` tests exact callsite encodings, round trips, branch endpoints, alignment, Thumb pointer bit handling, malformed ranges, and the veneer bytes. Unicorn 2.1.4 was installed under `/tmp` only; one fixture connects the mock patch transaction to emulation: it installs a synthetic `BL`, executes the Thumb caller/veneer/wrapper/stand-in callee path, verifies r0, preserved r1-r3 and r4-r11, SP, and continuation, then restores and byte-verifies the original `BL`. This is **EMULATOR CONFIRMED for the synthetic fixture**, not Honda runtime evidence.
- `mock_hooks.py` now models transaction preflight, exact restoration, a loud `CRITICAL_EXECUTABLE_RESTORE_FAILURE`, and process-epoch invalidation. Injected failure coverage includes partial write, second-site failure, failed restore, verification corruption, read failure, and changed process/load-bias identity.
- `modes.py` models INFO and Setup NOOP/OBSERVE with exact stock-result identity. INFO observations are capped at 32 displays and retain counts/classes only; no dictionary values, UUIDs, tokens, or keys enter diagnostics.

Maintained suites were run separately to avoid the repository’s existing duplicate test-module name collision:

| Suite | Result |
|---|---:|
| Honda + integration | 41 passed |
| Transport + negotiation + interposer | 61 passed, 31 subtests passed |
| Renderer | 8 passed |
| Session model + offline decoder | 13 passed |
| **Total** | **123 passed, 31 subtests passed** |

Combining all test directories into one pytest collection still fails because both `tests/carplay-session-model/test_model.py` and `src/claritylink-renderer/tests/test_model.py` import as `test_model`. The suites pass when run separately. Repository-wide research collection was not used as a passing claim.

## ECC review

The installed ECC agentic-engineering and security-review guidance was applied before implementation and again against the actual diff. Pre-review checks covered Thumb/ARM ABI and state-bit separation, branch and address overflow, alignment/endian behavior, exact-build binding, partial install/rollback, stale process state, diagnostics, and synthetic inputs. The post-review found and resolved two implementation issues: partial-write recovery now records a patch before issuing its write, and unknown/corrupted bytes remain in a loud critical state rather than being overwritten on a guessed retry. Address/hash/name bounds and branch-range rejection are covered by code or tests.

No dedicated ECC code-review agent/tool endpoint is exposed in this environment; this is a documented self-review against the installed ECC workflow, not an independent external review. **ECC REVIEW: FINDINGS RESOLVED; independent reviewer unavailable.** No open code finding blocks the synthetic model; target executable-memory behavior remains an explicit open blocker.

## Limits and gate

The fixture does not prove a ClarityLink binary can be allocated near the Honda text, that an executable page can be safely protected/unprotected, that instruction-cache synchronization is correct on Honda’s API-17 ARM target, or that all concurrent callers are coordinated. It also does not call the actual Honda functions or CoreFoundation APIs. Those items remain unknown/not ready. See `research/carplay/honda-executable-memory.md`.

```text
INFO CALL SITE VERIFIED: YES
SETUP CALL SITE VERIFIED: YES
CALL INSTRUCTION TYPE: 32-bit Thumb BL immediate
THUMB ENCODER: READY (host-confirmed)
THUMB DECODER: READY (host-confirmed)
BRANCH RANGE CHECK: READY (inclusive limits tested)
REDIRECTION STRATEGY: BL to direct shim if in range; otherwise BL to nearby ClarityLink literal veneer
VENEER: READY (synthetic ARMv7 instruction sequence emulator-confirmed)
STOLEN-PROLOGUE TRAMPOLINE REQUIRED: NO
ORIGINAL HONDA DELEGATION: READY AS CALL-SITE DESIGN; actual Honda target not executed
ABI PRESERVATION: PARTIAL (representative wrapper executed; production C shim/CoreFoundation ABI not tested)
SYNTHETIC EXECUTION: PASS
PATCH TRANSACTION: READY (host mock only)
EXACT BYTE RESTORATION: READY (host bytearray only)
RESTORE VERIFICATION: READY (host bytearray only)
ICACHE SYNC MODEL: UNKNOWN
MEMORY PROTECTION MODEL: NOT READY
NO-OP SHIM: READY (host semantics; representative wrapper emulator fixture)
OBSERVE SHIM: READY (bounded host semantics; representative wrapper emulator fixture)
@ECC REVIEW: FINDINGS RESOLVED; independent reviewer unavailable
OFFLINE REVERSIBLE HOOK HARNESS: READY (synthetic emulator + mock patch/restore only)
READY FOR STEP 41 PARKED NO-OP TEST: NO
READY FOR TYPE111 LIVE REQUEST: NO
BIGGEST BLOCKER: no verified target executable-page allocation/protection, cache-sync, and thread-coordination lifecycle
```

No vehicle, ADB, ptrace, live process access/write, listener, phone connection, Type111 request, firmware modification, or CAN operation occurred. Suggested commit: `ClarityLink: prove reversible Thumb-2 call interposition`.
