# Honda `forceKeyFrame` semantics — Step 43C

**Evidence classification:** `HONDA_UNKNOWN` for overall semantics and Type111 relation. The recovered ScreenStream frame switch provides a narrower `HONDA_CONFIRMED` result: opcode 3 falls through to its unrecognized path there. This does not establish the behavior of other paths.

## Scope and input identity

Analysis was offline and read-only. The hash-matched ELF is `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; `extracted/system-vendor/system/bin/jmcs` is the same binary. The binary is 32-bit ARM EABI5 and contains debug information. The preserved analysis inputs are `research/native/jmcs/symbols.json`, `disassembly.txt`, `focused-annotated.txt`, and `strings.txt`, plus `nm` and Apple `dwarfdump` output gathered locally. No binary or decompiler database is included in this report.

The DWARF data names `AirPlayReceiverSessionForceKeyFrame` and gives an apparent source declaration at `AirPlayReceiverSession.c:2792–2806`, with formal names `inSession`, `inCompletion`, and `inContext`. Its range is recorded as low PC `0` and high PC `0x5c`; this is not a usable relocated code address. The local symbol map and disassembly contain no corresponding function body or symbol. Neither `nm -an` nor `nm -D` exposes the function. The local extracted-file inventory contains only the duplicate `jmcs` copies for this component, not a separately identified AirPlay implementation library.

**Result:** function name/prototype metadata found (`PARTIAL`); executable implementation not recovered (`FAILED` from the available artifacts). The source file named in DWARF is not present, and the metadata does not provide the function's runtime body.

## Function and caller trace

| Item | Evidence | Result |
|---|---|---|
| Function name | DWARF name and string literals at `0x8ba3cf`, `0xbbea1c` | Name exists; strings do not establish a code reference |
| Function body/address | `symbols.json`, preserved disassembly, `nm` | No usable body/address found |
| Callers/callees | Preserved function-level xrefs and symbol map | Not recoverable from the available inputs |
| Session/completion/context parameters | DWARF formal parameter names | Interface hint only; semantics unknown |
| Trigger (request/timer/error/UI/decoder) | No body or call sites available | Unknown |
| Display index, UUID, stream type, or connection ID | No function body or call sites available | Unknown |

The caller trace is **PARTIAL**: the named function has debug metadata, but there are no executable xrefs to enumerate. No caller is classified as Type110-only, generic, UI-driven, or decoder-driven.

## Property and string evidence

The string inventory contains `forceKeyFrameNeeded` at `0x337352` and `0x3379fb`, and `forceKeyFrame` at `0x33737b`. Nearby strings include screen/session-related names such as `sessionDied`, `status`, `streams`, `timelineOffset`, `type`, `timestampsUpdated`, `frameCount`, `edid`, `features`, `maxFPS`, dimensions, `uuid`, `latencyMs`, `avcc`, and `platformLayer`.

String-pool proximity alone cannot establish that these names share a dictionary, object, owner, or call path. The preserved disassembly has no resolved xrefs for either key. Therefore the consumer/property trace is **PARTIAL** and does not establish whether either string is a phone-facing dictionary key, internal field, request, response, or media control.

| Property/string | Readers | Writers | Object owner | Phone-facing? | Media-facing? | Display-specific? | Confidence |
|---|---|---|---|---|---|---|---|
| `forceKeyFrame` | Unknown; no resolved xrefs | Unknown; no resolved xrefs | Unknown | Unknown | Unknown | Unknown | `HONDA_UNKNOWN` |
| `forceKeyFrameNeeded` | Unknown; no resolved xrefs | Unknown; no resolved xrefs | Unknown | Unknown | Unknown | Unknown | `HONDA_UNKNOWN` |
| `AirPlayReceiverSessionForceKeyFrame` | No caller recovered | No implementation recovered | Session implied by name/parameter only | Unknown | Unknown | Unknown | `HONDA_UNKNOWN` |

## ScreenStream opcode relationship

Honda's recovered `AirPlayReceiverSessionScreen_ProcessFrames` path is documented in [Honda ScreenStream framing](honda-screen-framing.md). Its switch handles discriminators 0, 1, 2, 4, and 5. Discriminator 0 reaches the media callback; 1 reaches configuration handling; 2, 4, and 5 have their separately documented paths. Discriminator 3 falls through to the unrecognized/log path in this specific function.

Thus `opcode 3 = ForceKeyFrame` is **not supported** by this Honda switch. This finding does not prove there is no other keyframe-related control path. The frame callback's lack of an IDR/NAL type-5 test is also scoped only to the recovered callback/config path; see [Honda H.264 format](honda-h264-format.md).

**Opcode relation:** `NOT FOUND` in the recovered frame dispatch; **opcode:** `NONE` (no opcode is established as ForceKeyFrame). Do not promote opcode 3 based on external protocol descriptions.

## Control-plane and Type111 relationship

No recovered evidence ties these literals or the DWARF function name to `/info`, Setup request/response parsing, binary-plist serialization, HTTP handling, UI ownership commands, ViewArea changes, or a phone-facing command. Since the body and xrefs are missing, the overall control-plane relation remains **UNKNOWN**, and whether a key is phone-facing remains **UNKNOWN**.

Within the inspected Honda evidence, no reference links the name/keys to type 111, a second display, alternate display, cluster, display UUID selection, ViewArea, secondary listener/data port, or a second Screen object. This is **not found in inspected evidence**, not proof of semantic absence. Type111 relation is recorded as `NOT FOUND` at the current evidence boundary and remains an open Honda unknown.

External prior art is not used to classify Honda behavior. In particular, xcertplay or MHI2 command behavior cannot supply the missing Honda function body.

## Conservative classification and impact

Unknown register value: **`HONDA_UNKNOWN`**. Available evidence does not support `HONDA_CONFIRMED_TYPE110_REFRESH`, `HONDA_CONFIRMED_GENERIC_REFRESH`, or either UI/decoder candidate classification.

It is still possible that the API is a generic or Type110 refresh mechanism, but this is only a **`HYPOTHESIS`**, not a finding. No implementation or live test is justified from this evidence.

### Exact next static question

Trace Honda Setup response `type` and `streamConnectionID` dataflow against the advertised display `uuid` and Screen object identity in the hash-matched `jmcs`. Keep the correlation `UNKNOWN` unless a direct dataflow or comparison is recovered.

## Readiness

- Honda ForceKeyFrame implementation recovery: **incomplete**.
- Type111 implementation: **not ready**.
- Live test: **not ready**.
- jmcs integration: **not ready**.
- ExternalDisplay live render: **not ready**.
- LD_PRELOAD: **parked**.

See [Step 43C report](../../step-reports/43c-forcekeyframe-semantics.md) for the milestone decision gate.
