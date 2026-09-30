# Honda Thumb-2 call-site branch model — Step 40B

## Evidence identity and sites

The inspected ELF is the local `jmcs` ARM32 little-endian ET_DYN file, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` (13,406,720 bytes). `objdump` was run directly on that ELF:

| Site | Bytes | Instruction | Target | Continuation |
|---|---|---|---|---|
| `_requestProcessInfo` `0x28a158` | `f8 f7 bc fd` | 32-bit Thumb `BL` | `AirPlayCopyServerInfo` `0x282cd4` | `0x28a15c` |
| `_connectionHandleMessage` `0x28af72` | `fa f7 b5 fa` | 32-bit Thumb `BL` | `AirPlayReceiverSessionSetup` `0x2854e0` | `0x28af76` |

The independent decoder reproduces the targets and re-encodes the exact original byte strings. Caller ABI evidence is recorded in [honda-hook-abi.md](honda-hook-abi.md). The Setup call has r0=session, r1=request, r2=responseOut, no stack arguments, and an 8-byte-aligned SP. The server-info call has four register arguments; see the ABI note for the recovered values.

## Encoding

Thumb `BL` immediate is 25 signed bits including the implicit low zero bit. The instruction PC base is `call_address + 4`. For halfwords `h1,h2` read little-endian:

```text
S  = h1[10]
imm10 = h1[9:0]
J1 = h2[13]
J2 = h2[11]
imm11 = h2[10:0]
I1 = NOT(J1 XOR S)
I2 = NOT(J2 XOR S)
disp = sign_extend_25(S:I1:I2:imm10:imm11:0)
target = call_address + 4 + disp
```

The legal byte displacement is `-16,777,216` through `+16,777,214`, in two-byte increments. The encoder and decoder reject malformed opcodes, odd code addresses, out-of-range targets, and 32-bit PC overflow. Branch targets are even code addresses. Thumb function pointers are separately represented with bit 0 set; the literal veneer restores that bit explicitly.

## Veneer model

When the ClarityLink shim is not in direct `BL` range, the modeled 12-byte veneer is four-byte aligned and contains:

| Offset | Encoding | Operation | Purpose |
|---|---|---|---|
| `+0` | `f8 df 04 c0` | `ldr.w r12,[pc,#4]` | Load the tagged 32-bit shim pointer from `+8` |
| `+4` | `60 47` | `bx r12` | Transfer in Thumb state without changing LR |
| `+6` | `00 00` | alignment padding | Align the literal to four bytes |
| `+8` | 4-byte LE pointer | `shim_code_address | 1` | Full address, Thumb bit set |

The veneer leaves r0-r3, SP, and LR unchanged. r12 is caller-saved under AAPCS32. These exact bytes were emitted/checked with Clang's ARMv7 assembler and executed under Unicorn in a synthetic memory image. This proves the instruction sequence in the emulator, not allocation, mapping, permissions, cache visibility, or execution inside Honda.

## Test status

`tests/honda/test_thumb_call.py` verifies both Honda targets, round trips, inclusive branch limits and out-of-range edges, malformed alignment, explicit Thumb-pointer conversion, and veneer bytes. An optional Unicorn test executes the patched caller branch, veneer, representative shim, untouched synthetic callee, and return to the original continuation. Evidence class: **EMULATOR CONFIRMED (synthetic code)**. No Honda traffic or live process was used.

Reproduce the emulator case without adding a project dependency:

```sh
python3 -m pip install --target /tmp/claritylink-unicorn-deps unicorn==2.1.4
PYTHONPATH=/tmp/claritylink-unicorn-deps:/tmp/claritylink-pytest-deps python3 -m pytest -q tests/honda/test_thumb_call.py
```
