# Step 28 — Honda display capability advertisement and AltScreen gating

**Date:** 2026-09-29  
**Starting commit:** `5331dc6`  
**Scope:** offline static review of local `jmcs`, generated disassembly/string map, and tracked prior-art/Step 27 reports. No vehicle, ADB, ptrace, firmware patch, live hook, or Type-111 implementation.

## Result

Recovered the local output of `AirPlayReceiverSessionScreen_CopyDisplaysInfo` (`jmcs` VA `0x287ae1`, file offset `0x287ae0`). The function creates a mutable dictionary, invokes `ScreenCopyMain` once, copies properties from that single main-screen object, and returns the dictionary through an output pointer. The string table provides literal keys `edid`, `features`, `maxFPS`, `widthPhysical`, `heightPhysical`, `widthPixels`, `heightPixels`, and `uuid`. Numeric properties are read through `CFObjectGetPropertyInt64Sync` and inserted with `CFDictionarySetInt64`; `edid` is copied and inserted with `CFDictionarySetValue`. The `features` property is transformed by bit masks before insertion. Its meaning and runtime value are unknown. The recovered `uuid` key also uses the numeric setter in this code path; representation and value require confirmation.

This function contains no screen enumeration loop or display-array construction. `ScreenCopyMain` selects registry index zero. A generated-disassembly search found the function definition but no direct call instruction to it. An indirect function-pointer/callback edge remains possible. Consequently the enclosing parent, call chain, serializer/send path, message/request type, and protocol timing are not established. It is not proven phone-facing, and it is not tied to iAP2 Identification, ReceiverInfo, Setup, or feature discovery.

## Findings by requested investigation

1. **Callers/xrefs:** no direct caller found in generated `jmcs` disassembly. Indirect use unresolved. Classification: UNKNOWN; no caller purpose/return-use can be assigned.
2. **Output:** one dictionary; fields listed above. No evidenced role, screen type/subtype, view area, input device, initial URL, or primary/secondary key. Exact units/runtime values unknown.
3. **Container:** local output dictionary; parent and wire collection unknown. No CFArray around displays found in this function.
4. **Phone-facing serializer:** unknown. Exact unresolved edge is from function return/out pointer to any caller; no direct caller recovered.
5. **Protocol phase:** unknown. Chronology relative to iAP2 Identification and AirPlay SETUP cannot be established.
6. **Identification/ReceiverInfo:** no wire payload/call edge found. Existing project evidence explicitly treats raw iAP2 Identification as unresolved and separate from this display builder.
7. **Enumeration:** singleton in this function; receiver-wide display enumeration model unknown. One configured `gMainScreen` is independently established.
8. **Secondary constants:** no contextual Honda evidence of `altScreen`, secondary role, cluster designation, second display UUID, or Type 111 in this builder. `features` is a candidate container, but semantics are unknown.
9. **Prior art:** Honda confirmed: local main descriptor keys and primary Type-110 Setup response. Honda analog: none yet for display list/alternate feature/second UUID. Absent: no claim (bounded function only). Unknown: phone-facing descriptor list, AltScreen field, second descriptor, stream correlation. xcertplay/Harman remain comparison evidence, not Honda proof.
10. **Phone gating:** Apple documents multi-stream cluster use at a high level; exact wire gate unknown. Prior art implements display identities and 110/111 paths. Honda capability advertisement, phone proposal, Type-111 setup request, and acceptance remain unknown.
11. **Feature field:** `features` numeric masked value in the local dictionary; AltScreen-like field present: UNKNOWN; extensible at phone-facing layer: UNKNOWN.
12. **Primary UUID:** `uuid` key sourced from the main screen property and inserted numerically. Format, lifetime, session scope, and advertisement to phone: unknown.
13. **Second descriptor feasibility:** unknown; this builder returns a dictionary and no collection. No insertion container or safe capability mutation point established.
14. **Type 111 alone:** likely insufficient as an architectural inference: no Honda descriptor/correlation evidence shows which display it would identify. Apple does not document this exact private schema.
15–16. **Type dispatch/parser:** incoming request `type` lookup, conversion, comparisons, known values, and default behavior are not recovered in the available evidence. Response-side type 110 is confirmed; Type 111 acceptance/dispatch is unknown.
17–18. **Hooks/ownership:** capability hook requirement unknown; likely needed if iPhone gating depends on advertisement. Setup response mutation point remains the Step 27 post-Setup/pre-serializer structural candidate. No capability response ownership/serializer/mutation point is known.
19. **Two-stage design:** Stage A cannot be designed against an unlocated phone-facing container. Stage B's mutation candidate exists but Type-111 dispatch, listener lifecycle, and correlation are unknown. No hook code written.
20. **Correlation:** descriptor UUID ↔ stream type/connection ID/data port/session is unknown.
21. **Experiment:** not authorized/performed. Earliest unambiguous future signal would be a second request carrying an identifiable alternate type/display identity; alternatively a second connection correlated to an advertised secondary identity. No decoder required to observe that.
22. **State machine:**

```text
PHONE -> Honda capability query: UNKNOWN
Honda -> PHONE main + hypothetical cluster descriptor: UNKNOWN
PHONE -> Honda primary SETUP (type 110): PRIOR-ART SUPPORTED; Honda phone-facing response path CONFIRMED
Honda -> PHONE type 110 + dataPort: CONFIRMED (Step 27)
PHONE -> Honda secondary SETUP (type 111 + display correlation): UNKNOWN
Honda/ClarityLink -> PHONE type 111 + independent port: UNKNOWN
PHONE -> secondary listener: UNKNOWN
```

## Decision gate

```text
DISPLAY CAPABILITY MESSAGE: unknown; local CopyDisplaysInfo output not linked to a message
COPYDISPLAYSINFO PHONE-FACING: UNKNOWN
DISPLAY CONTAINER: one local dictionary; parent/wire container unknown
MULTI-DISPLAY REPRESENTABLE: UNKNOWN at advertisement layer
PRIMARY DISPLAY UUID: local `uuid` property inserted as numeric value; format/lifetime/wire status unknown
ALTSCREEN FEATURE FIELD: `features` exists; AltScreen semantics unknown
TYPE111 REQUEST PARSER: unknown
HONDA ACCEPTS/ROUTES TYPE111: unknown
CAPABILITY HOOK REQUIRED: unknown (architecturally likely, Honda gate unproven)
SETUP HOOK REQUIRED: unknown for protocol; structurally available to modify stock response if a secondary port is independently accepted
CAPABILITY MUTATION POINT: unknown; caller and enclosing response unresolved
DISPLAY-TO-STREAM CORRELATION: unknown
READY FOR STRUCTURED DISPLAY-B NEGOTIATION IMPLEMENTATION: NO
READY FOR LIVE NEGOTIATION TEST: NO
BIGGEST BLOCKER: no recovered caller edge from CopyDisplaysInfo's returned dictionary to a phone-facing message/serializer
```

Detailed notes: `research/carplay/honda-display-capabilities.md`, `honda-copy-displays-info.md`, `honda-identification-receiver-info.md`, `honda-alt-screen-gating.md`, `honda-stream-type-dispatch.md`, `display-stream-correlation.md`, and `altscreen-control-plane.md`.
