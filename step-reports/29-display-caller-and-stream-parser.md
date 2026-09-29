# Step 29 — display caller and SETUP stream parser

**Date:** 2026-09-29  
**Starting commit:** `09ee0bf`  
**Scope:** offline-only analysis. No vehicle, ADB, ptrace, firmware patch, hooks, or Type-111 implementation.

## Acquisition identity gate

Located `/system/bin/jmcs` in the immutable complete acquisition archive, without changing the source. The archive and extracted analysis copy are documented in `research/carplay/jmcs-acquisition-identity.md`. The copied ELF SHA-256 matches the previously analyzed image; ELF class/endian/type/machine, load layout, symbols, and VA-to-file-offset mapping match saved static/runtime address evidence. The user’s identity gate therefore passed before continuing Step 29.

## Findings

### Display path

`AirPlayReceiverSessionScreen_CopyDisplaysInfo` (`0x287ae0`) has a direct caller: `AirPlayReceiverSessionPlatformCopyProperty` (`0x28d328`), call at `0x28d370`. For property `displays`, the caller makes a mutable array, invokes the builder once, appends its dictionary, and returns a one-element CFArray. The dictionary describes `ScreenCopyMain()` and includes EDID, features, maxFPS, dimensions, and numeric-setter `uuid`. `AirPlayCopyServerInfo` (`0x282cd4`) calls the platform property-copy routine, but the exact displays property argument/key and the serializer/send edge are not proven. The phone-facing capability message remains unknown.

### SETUP request/type path

`_connectionHandleMessage` decodes the body through `CFCreateWithPlistBytes` (`0x29354c`), which wraps the bytes as CFData and calls `CFPropertyListCreateWithData`. It passes the parsed request dictionary to `AirPlayReceiverSessionSetup` (`0x2854e0`) at `0x28af72`. Top-level reads include `osBuildVersion`, `modelCode`, `udid`, and `streams`. Setup iterates the `streams` CFArray and reads each entry’s integer `type` via `CFDictionaryGetInt64` at `0x28590e`. Exact HTTP method/path routing and body ownership are unresolved.

The dispatcher routes type 100/101 to audio setup and type 110 to screen setup. Other values, including 111, reach the invalid-type path at `0x2861f6`; Type 111 is not generically accepted. Type 110 calls `AirPlayReceiverSessionScreen_Setup` at `0x28609c`, opens the dynamic listener, and appends a response entry with `type=110` and its `dataPort`. This confirms request type 110 through the established response serializer/send path.

Setup handles a stream array with per-element processing and appends response entries. It is structurally multi-entry; duplicate and combination constraints remain unknown. The recovered Setup path does not read or emit the display UUID, stream ID, or `streamConnectionID`. No display-to-stream identity binding is established.

## Decision gate

```text
COPYDISPLAYSINFO INDIRECT CALLER: AirPlayReceiverSessionPlatformCopyProperty, direct call at 0x28d370
PHONE-FACING DISPLAY MESSAGE: UNKNOWN; local `displays` property array is proven, wire path is not
DISPLAY SERIALIZER: UNKNOWN for displays; Setup response serializer is _requestSendPlistResponse
DISPLAY UUID FLOW: ScreenCopyMain property -> local dictionary -> one-item displays array; further flow unknown
FEATURES MEANING: integer/masked value; meaning and bits unknown
SETUP REQUEST STREAM KEY: streams[] element key `type`
STREAM TYPE PARSER: CFDictionaryGetInt64 in AirPlayReceiverSessionSetup at 0x28590e
TYPE110 PATH: CONFIRMED; screen setup -> dynamic listener -> response type=110/dataPort -> existing HTTP binary-plist send path
TYPE111 BEHAVIOR: REJECTED by invalid-type dispatch
REQUEST STREAM MODEL: ARRAY; per-element loop; multi-entry mechanics present
DISPLAY-TO-STREAM BINDING: type 110 selects screen setup, but no display UUID/ID correlation found
SECOND DISPLAY ADVERTISEMENT REQUIRED: UNKNOWN
CAPABILITY HOOK: unknown; phone-facing serializer boundary not recovered
SETUP HOOK: structural candidate in _connectionHandleMessage after Setup and before response serialization (0x28af72–0x28afba); insufficient to make Type 111 accepted
READY FOR NEGOTIATION IMPLEMENTATION: NO
READY FOR FIRST LIVE NEGOTIATION EXPERIMENT: NO
BIGGEST BLOCKER: exact phone-facing serialization of the `displays` property and its relationship to a second screen
```

## Evidence files and verification

Updated the eight focused research notes, plus `PROJECT_STATE.md`, `EVIDENCE_INDEX.md`, and `NEXT_ACTION.md`. Added the acquisition identity record. No tests were run because no code/model changed. `git diff --check` was run before commit. The extracted analysis binary is ignored and was not staged; the immutable acquisition source was not modified.

**Next concrete task:** trace `AirPlayCopyServerInfo` argument values to identify the `displays` property key and follow that returned value to its serializer/send consumer.
