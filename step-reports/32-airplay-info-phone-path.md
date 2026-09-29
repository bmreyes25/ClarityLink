# Step 32 — recover the AirPlay `/info` phone-facing path

**Date:** 2026-09-29  
**Starting commit:** `cc21ca3`  
**Scope:** offline static analysis plus focused public-source verification. No vehicle, ADB, ptrace, firmware change, or live hook. No Type-111 implementation.

## Result

The primary gap from Steps 30–31 is closed. `AirPlayCopyServerInfo` is called by `_requestProcessInfo`, whose address is `0x28a018`. The response dictionary is sent to the plist serializer, and the request dispatcher sends the resulting HTTP response. The exact dataflow is:

```text
_connectionHandleMessage (0x28a30c)
  -> /info suffix dispatch (strnicmp_suffix; comparison at 0x28b678–0x28b680)
  -> _requestProcessInfo (0x28a018), call at 0x28b68e
  -> parse plist request / qualifier array
  -> AirPlayCopyServerInfo (0x282cd4), call at 0x28a156
  -> serverInfo CFDictionaryRef returned in r0, preserved in r5
  -> _requestSendPlistResponse (0x289f60), call at 0x28a19c with r2=r5
  -> CFPropertyListCreateData(format=0xc8), binary plist body
  -> return to _connectionHandleMessage; release serverInfo at 0x28a1da
  -> HTTPConnectionSendResponse (0x29dbe4), call at 0x28b790
  -> _HTTPConnectionRunStateMachine (0x29d698)
  -> SocketWriteData (0x2a01c0)
  -> writev@plt
```

The `/info` route comparison uses the path suffix. Its literal is `/info` (rodata file offset `0x333bca`; ELF VA `0x334bca` under the established segment mapping). The matched branch calls `_requestProcessInfo`; this and the helper name/call sequence identify the phone-facing GET-info response. The request parser reads a binary plist and obtains the `qualifier` array. The independently observed AirPlay qualifier value `txtAirPlay` is present in the same binary, but the complete qualifier-to-builder selector semantics were not needed to establish the returned server-info object path.

`AirPlayCopyServerInfo`'s result is the exact `CFDictionaryRef` passed as the plist object argument. The displays array inserted under `displays` by the builder is part of this same object. Thus `DISPLAYS_PHONE_FACING=CONFIRMED` at the static dataflow level. This proves the phone-facing response path in code; it does not constitute a packet capture or prove a particular run-time iPhone transaction.

## Mutation and ownership

`_requestProcessInfo` keeps the returned server-info object in `r5`. The call at `0x28a19c` passes the same pointer in `r2` to `_requestSendPlistResponse`. The serializer is synchronous and copies serialized bytes into the HTTP message body; `_requestProcessInfo` releases the server-info object at `0x28a1da`, after serialization returns. Therefore the narrow static mutation interval is after `AirPlayCopyServerInfo` returns at `0x28a156` and before `_requestSendPlistResponse` begins at `0x28a19c`. The outer dictionary and nested `displays` array are mutable per the established builder/property-copy path. This is a structural candidate window, not approval or validation of an executable hook.

## Setup feature-key search

The Honda ELF string scan contains no literal `FeatureKey`, `altScreen`, `viewAreas`, `initialViewArea`, or `enabledFeatures`. The SETUP response construction slice also provides no evidence of a string-token feature array. For this exact binary, classify the requested modern FeatureKey token array as **ABSENT from the recovered/static string and response-construction evidence**; this does not assert that the tokens are universally required or that every capability is represented by string keys. The existing numeric `features` values are separate and their bit meanings remain unresolved.

External prior art is supporting context only. xcertplay explicitly describes its `/info` response as read before media streams, and constructs a `displays` array with type 110 and an optional type-111 descriptor. Its source also adds an `altScreen` string to session `enabledFeatures` conditionally. The MHI2 hook-map describes stock-first SETUP augmentation for AltScreen/ViewArea and Type-111 response insertion. These are different receiver implementations and do not establish Honda requirements. Sources: [xcertplay AirPlayInfoPlist.kt](https://github.com/shilapi/xcertplay/blob/master/shared/src/main/java/com/shilapi/xcertplay/airplay/AirPlayInfoPlist.kt), [MHI2 GEN2 hook map](https://github.com/harman-f/mhi2_altscreen_carplay/blob/main/docs/research/MU1440_GEN2_HOOK_MAP.md), and [UxPlay protocol notes](https://github.com/FDH2/UxPlay/wiki/AirPlay2).

## `streamConnectionID`

The literal `streamConnectionID` and Honda internal `inScreenStreamConnectionID` occur in the ELF. The name's presence alone does not establish which request field is read, what object carries the value, or whether it binds an advertised display to a Setup stream. No such binding is claimed here; a dedicated xref/dataflow trace is still needed.

## Revised decision gate

```text
AIRPLAYCOPY_SERVERINFO SYMBOL: GLOBAL in .symtab; not dynsym-exported
EXTERNAL CONSUMER: none; internal consumer recovered in jmcs
PHONE_REQUEST_HANDLER: _requestProcessInfo (0x28a018), selected by /info suffix dispatch
SERVER_INFO_SERIALIZER: _requestSendPlistResponse (0x289f60), binary plist format 0xc8
SERVER_INFO_SEND_PATH: _connectionHandleMessage -> HTTPConnectionSendResponse -> SocketWriteData -> writev
DISPLAYS_PHONE_FACING: CONFIRMED (static object dataflow)
SERVER_INFO_MUTATION_POINT: _requestProcessInfo, 0x28a156 return through 0x28a19c serializer entry
DISPLAY_ARRAY: MUTABLE; outer dictionary mutable
HONDA FEATURE TOKEN ARRAY: no literal/construction evidence in this binary (ABSENT from evidence)
TYPE111_REJECTION_STATUS: invalid-type branch 0x2861f6; external status unknown
TYPE111_INTERCEPT_ABI: not validated
PARTIAL_SETUP_DELEGATION: UNKNOWN
DISPLAY_STREAM_BINDING: UNKNOWN; streamConnectionID xref pending
TWO_HOOKS_SUFFICIENT: UNKNOWN; SETUP feature advertisement may be a separate logical requirement
OFFLINE IMPLEMENTATION READY: NO (Type-111 and feature schema/ABI remain unresolved)
LIVE CONNECTION TEST READY: NO
BIGGEST BLOCKER: Honda display-to-Type-111 request binding and accepted SETUP response/capability schema
```

The practical model is now: Hook A can target the `/info` response object; Hook B must account for SETUP capability augmentation and Type-111 handling. These may be logically distinct mutations in one interception window, but Honda's required capability token schema and Type-111 acceptance behavior are not proven. Do not collapse the control-plane unknowns into a claim that two hooks suffice.

## Verification and next action

Updated the Step 31 conclusion and capability/send-path, correlation, architecture, and project-state notes. No code/data model changed; tests were not run. `git diff --check` is required before commit.

**Next action:** trace the existing `streamConnectionID` / `inScreenStreamConnectionID` xrefs through Setup and screen-session creation, then determine whether Honda has a preexisting stream-to-display association. Keep changes offline and descriptive.
