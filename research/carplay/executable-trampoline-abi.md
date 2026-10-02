# 43S1 executable Thumb trampoline ABI proof (offline)

**Classification:** `LAB_EXECUTABLE_CONFIRMED` for the standalone synthetic Thumb image and Unicorn run; Honda caller facts remain `HONDA_CONFIRMED` static ELF evidence. This image is not linked to or installed in `jmcs` and cannot patch the Honda artifact.

## Exact target revalidation

The preserved `extracted/system/system/bin/jmcs` SHA-256 was rechecked as `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. Existing planner validates ELF32 little endian, `EM_ARM`, `ET_DYN`, EABI5, the entire pinned hash, Thumb BL bytes `fe f7 d1 ff` at `0x28afba`, decoded target `0x289f60`, continuation `0x28afbe`, surrounding callsite fingerprint, and `_connectionHandleMessage` prologue fingerprint. A separate test implementation decodes the Thumb BL immediate from S/J1/J2/I1/I2/imm fields and independently obtains `0x289f60`. The original return state is Thumb-tagged `0x28afbf`.

At the serializer call, original `SP` is the live `_connectionHandleMessage` frame. The synthetic shim snapshots entry SP into `r12` before its first stack operation, pushes `r4-r11,lr`, inserts an alignment word, then reserves a 48-byte local context. It reads request from original SP+`0x1c`, response from original SP+`0x54`, statusOut pointer from original `r3` and checks that it equals original SP+`0x50`, and session from `[r10+0xf4]` after a null-base guard. No caller offset uses the adjusted shim SP.

## Context and register contract

| Context offset | Value |
|---:|---|
| `0x00` | original/callsite SP |
| `0x04` | request pointer from `[original_sp+0x1c]` |
| `0x08` | response pointer from `[original_sp+0x54]` |
| `0x0c` | stock serializer statusOut pointer (entry r3), expected to equal `original_sp+0x50` |
| `0x10` | session pointer from `[r10+0xf4]`; zero when r10 is null |
| `0x14..0x20` | saved serializer r0-r3 |
| `0x24` | project prepare result |
| `0x28` | stock serializer r0 |
| `0x2c` | expected statusOut stack address |

The shim preserves `r4-r11` and SP by its machine code. It restores r0-r3 immediately before the stock serializer call. The serializer is called at one static site, once. Its r0 is retained in r4 across project completion and restored to r0 before the original continuation. Commit eligibility is exactly prepare-result `1`, non-null status pointer matching the exact caller local, serializer r0 `0xc8`, and `*statusOut == 0`; every other expected result passes `commit=false` to the exact-generation finish helper. The helper must implement commit/rollback as non-throwing result-returning operations. The shim does not catch arbitrary native faults.

The local helper stubs include push/sub/add/pop sequences that exercise nested stack use while preserving the AAPCS callee-saved contract. Unicorn hooks stand in for the prepare/serializer/finish function bodies; these hooks intentionally do not claim compiled native transaction logic or Honda execution.

## Toolchain and executable evidence

- Toolchain: Apple Clang 21, `--target=armv7-none-eabi -mthumb`; emits ELF32 little-endian ARM EABI5 relocatable object.
- `llvm-objdump -d -r` from the Xcode toolchain disassembled the shim and showed exactly three local `R_ARM_THM_CALL` relocations to `project_prepare`, `stock_serializer`, and `project_finish`.
- Text is 162 bytes, has execute/read but not write permission, and is below the 512-byte check bound. The in-memory builder locally applies only those three same-text ARM Thumb call relocations and rejects undefined imports. It writes no binary artifact.
- Emulator: Unicorn 2.1.4, ARM AArch32 in Thumb mode. It executes the compiled instructions in the shim and helper stack stubs. Unicorn is an instruction-level architecture/ABI test, not an Android Bionic or Honda runtime emulator.
- Tests verify exact context addresses, 8-byte call-boundary SP, exactly one serializer call, result/statusOut gating, caller r4-r11, original SP, and branch to a Thumb continuation sentinel. They exercise prepare bypass/failure, serializer failure, nonzero statusOut, finish-helper failure, null request/response, null status pointer mismatch, and null r10. A nested synthetic invocation and two concurrent independent Unicorn sessions execute without shim-global state; the nested invocation still uses a separate emulator instance and does not prove native transaction-helper reentrancy.

## Limits

The prepare/finish/serializer bodies are harness callbacks, not compiled project code. Project transaction reentrancy, same-session concurrent SETUP serialization, C/ARM exception behavior, asynchronous listener errors after activation, a Honda adapter's runtime mapping, and callout safety in Honda remain unproven. A bad non-null r10 or corrupted stack that points outside mapped memory can fault; no in-process signal-handler recovery is claimed. These limits make 43S1 G19 `PARTIAL`, not a Honda attachment approval.

## Reproduction

```sh
clang --target=armv7-none-eabi -mthumb -c src/claritylink-negotiation/thumb_setup_shim.S -o /tmp/claritylink-thumb-shim.o
/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/llvm-objdump -d -r /tmp/claritylink-thumb-shim.o
PYTHON=.venv/bin/python .venv/bin/pytest -q tests/negotiation/test_thumb_setup_shim.py
```
