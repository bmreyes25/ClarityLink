# Honda call-site interposition model — Step 40B

## Call-site evidence

The exact local `jmcs` ELF (`cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`) was re-disassembled:

| Call site | Caller | Original target | Register contract | Stack / continuation |
|---|---|---|---|---|
| `0x28a158`, `f8 f7 bc fd` | `_requestProcessInfo` | `AirPlayCopyServerInfo` `0x282cd4` | Four AAPCS32 register args; r0-r3 | no stack args; next instruction `0x28a15c` |
| `0x28af72`, `fa f7 b5 fa` | `_connectionHandleMessage` | `AirPlayReceiverSessionSetup` `0x2854e0` | r0=session, r1=request, r2=responseOut; r0 returns OSStatus | no stack args, SP 8-byte aligned; next instruction `0x28af76` |

Both are 32-bit Thumb direct `BL`, not function prologues or indirect calls. The disassembly verifies the instruction/target/continuation; live register values and runtime call behavior remain static-analysis evidence, not runtime confirmation.

## Selected shape

1. Replace only the selected four-byte `BL` in the mock patch plan.
2. If the actual shim is in signed Thumb `BL` range, target it directly. Otherwise target a four-byte-aligned nearby ClarityLink-owned literal veneer; the veneer transfers to a full 32-bit Thumb function pointer.
3. The ordinary shim calls the untouched Honda function at its original target using the normal ABI, preserves its own caller's LR, and returns the exact stock r0 result. No stolen-prologue trampoline is required because the Honda callee entry is not patched.
4. NOOP semantics return the same object/OSStatus and, for Setup, leave the response-out object exactly as Honda produced it. OBSERVE semantics retain only bounded event categories/counts, never request contents or identifiers.

This leaves **zero additional Honda bytes** modified beyond each selected call instruction. A near executable allocation for the veneer and a valid shim address are not yet available or proven; the current patch plan does not allocate or write executable pages. The alternative of an unverified code cave is rejected because none has been identified in Honda evidence.

## ABI and scope

The Unicorn fixture executes a representative Thumb wrapper using `push {r4,lr}`, keeps LR across a call to a synthetic callee, restores r4/LR via `pop {r4,pc}`, and verifies the argument/result, callee-saved register, stack pointer, and caller continuation. It does not execute Honda functions, call real CoreFoundation, or prove native wrapper ownership/error details. Reentrancy and the worker-thread set remain unknown. No stolen-prologue relocation is performed.

## Current status

The branch/veneer instruction path is emulator-confirmed with synthetic addresses. Original-call delegation is architecturally valid for a call-site wrapper and host semantics are tested, but a compiled ClarityLink shim, runtime allocation, page permissions, cache synchronization, concurrent-thread coordination, and live install/restore are **NOT READY**. This model does not authorize Step 41.
