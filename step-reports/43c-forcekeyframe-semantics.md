# Step 43C — Honda ForceKeyFrame semantics

**Scope:** offline static analysis only. No vehicle, ADB, Honda runtime, binary modification, Type111 implementation, or live test was used.

## Result

The analysis did **not** recover an executable body for `AirPlayReceiverSessionForceKeyFrame`. The hash-matched `jmcs` contains DWARF metadata naming the function and an apparent source location/prototype, but its low PC is zero and there is no corresponding function symbol or body in the preserved symbol map/disassembly. The two extracted `jmcs` paths are duplicate copies. The recovered artifacts therefore do not answer whether the path refreshes Type110, controls a generic screen, requests an IDR, or participates in UI/control behavior.

One narrower transport fact is established: Honda's recovered `AirPlayReceiverSessionScreen_ProcessFrames` switch does not handle discriminator 3 as ForceKeyFrame; it falls through to the unrecognized/log path. This applies to that frame dispatch only and does not rule out a separate control path.

## Artifact identity and recovery limits

| Check | Finding |
|---|---|
| Honda ELF | `extracted/system/system/bin/jmcs` |
| SHA-256 | `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` |
| Duplicate | `extracted/system-vendor/system/bin/jmcs`, same hash |
| Format | 32-bit ARM EABI5 ELF with debug information |
| Symbols | Partial; ordinary symbols exist, ForceKeyFrame symbol/body does not |
| DWARF | Partial; function name, source line 2792–2806, parameter names, and unusable low-PC-zero range |
| Preserved inputs | `research/native/jmcs/{symbols.json,disassembly.txt,focused-annotated.txt,strings.txt}` |
| Alternate extracted implementation | Not found in the available extracted paths; no separate AirPlay implementation library identified |

No ELF, raw firmware, decompiler database, or generated proprietary dump was added.

## Function, callers, and consumers

The DWARF formal parameters are named `inSession`, `inCompletion`, and `inContext`; that reveals an interface shape, not behavior. No executable address, file offset, body, caller, callee, or xref can be tied to this entry in the local map. The function/caller trace is therefore partial.

The string inventory contains `forceKeyFrameNeeded` at `0x337352` and `0x3379fb`, and `forceKeyFrame` at `0x33737b`. No resolved code xrefs were present in the saved function-level disassembly. Nearby string-pool items are not sufficient to assign the keys to an object or message. Readers, writers, ownership, serialization, and media effects remain unknown. Consumer/property trace is partial.

| Caller / consumer question | Result |
|---|---|
| Caller functions and call-site addresses | Not recoverable from current inputs |
| Trigger type (request, timer, error, UI, decoder) | Unknown |
| Session state passed at call | Parameter names suggest a session argument; actual use unknown |
| Display index/UUID, stream type, streamConnectionID | No relation recovered |
| `forceKeyFrame` and `forceKeyFrameNeeded` readers/writers | No resolved xrefs; unknown |
| Phone-facing serialization or inbound request | Unknown |
| IDR request / decoder recovery | Unknown |

## ScreenStream and control-plane evidence

The Honda frame parser's switch handles 0, 1, 2, 4, and 5; 3 reaches its unrecognized path. See [Honda ScreenStream framing](../research/carplay/honda-screen-framing.md). The function body is unavailable, so this does not establish the full meaning of the separate named API or string keys.

No recovered function-level evidence connects the ForceKeyFrame name/keys with `/info`, Setup, plist serialization, HTTP, UI commands, ViewArea, or a Type111 stream. The conservative classifications are `OPCODE RELATION: NOT FOUND` in the recovered frame dispatch, `CONTROL PLANE RELATION: UNKNOWN`, `PHONE FACING KEY: UNKNOWN`, and `TYPE111 RELATION: NOT FOUND` within inspected evidence. None means global semantic absence.

## Decision and next action

The appropriate register classification is `HONDA_UNKNOWN`. Calling it Type110 refresh, generic screen refresh, UI control, or decoder recovery would overstate the evidence. No implementation or live readiness changes follow.

Next static task: trace Setup response `type` / `streamConnectionID` dataflow against display `uuid` and Screen object identity in the hash-matched Honda `jmcs`; preserve unknown where no direct binding is found.

## Decision gate

FUNCTION FOUND: PARTIAL

IMPLEMENTATION RECOVERED: FAILED

CALLER TRACE: PARTIAL

CONSUMER TRACE: PARTIAL

OPCODE RELATION: NOT FOUND

OPCODE: NONE

CONTROL PLANE RELATION: UNKNOWN

PHONE FACING KEY: UNKNOWN

TYPE111 RELATION: NOT FOUND

FORCEKEYFRAME CLASSIFICATION: HONDA_UNKNOWN

IMPLEMENTATION READY: NO

LIVE TEST READY: NO

JMCS INTEGRATION READY: NO

EXTERNALDISPLAY LIVE RENDER READY: NO

LD_PRELOAD: PARKED

NEXT STATIC QUESTION: Does Honda Setup response `type` or `streamConnectionID` dataflow reference, compare, or derive from the advertised display `uuid` or Screen object identity?
