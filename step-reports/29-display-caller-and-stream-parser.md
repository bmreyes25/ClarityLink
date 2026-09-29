# Step 29 — display caller and SETUP stream parser

**Date:** 2026-09-29  
**Starting commit:** `09ee0bf`  
**Scope:** offline-only review of tracked Honda `jmcs` artifacts and Steps 26–28. No vehicle, ADB, ptrace, firmware patch, hooks, Type-111 implementation, or return to the `mc_dev_attach` registry.

## Outcome

This pass did not close either requested unknown. The tracked checkout has symbol metadata, generated disassembly and function excerpts, but not the matching `jmcs` ELF or the raw relocation/data/DWARF material needed to search pointer storage and callback tables. The saved request-side disassembly slice also does not include `_connectionHandleMessage` or the request reads/control flow within `AirPlayReceiverSessionSetup`. The documented Step 27 caller/send and Step 28 descriptor findings remain valid, but cannot be extended into the missing caller/parser edges from the available primary artifacts.

The material outcomes are negative in a bounded, useful sense: no evidence currently supports treating `CopyDisplaysInfo` as phone-facing; no Honda evidence currently supports generic Type-111 acceptance or explicit rejection. Those are still unknown, not unreachable/unsupported conclusions.

## A. Display capability path

```text
AirPlayReceiverSessionScreen_CopyDisplaysInfo (0x287ae0)
  -> ScreenCopyMain() once
  -> one local mutable dictionary (edid/features/maxFPS/dimensions/uuid)
  -> caller / parent / protocol message / serializer / send: UNKNOWN
```

The available artifacts do not expose function-pointer relocations, `.data` initializers, callback table entries, constructor writes, interface type/slot, or indirect callers. The numeric `features` masking and numeric-setter `uuid` insertion remain as recorded in Step 28; bit meanings, runtime type/value, lifetime, and wire status are unknown. No display list or second descriptor is proven. The SETUP send path remains a separate confirmed response path.

## B. SETUP request path

```text
HTTP request -> _connectionHandleMessage (0x28a30c)
  -> parsed request-body property-list dictionary (outer handoff confirmed)
  -> AirPlayReceiverSessionSetup (0x2854e0), call 0x28af72
  -> request keys / stream loop / type dispatch: UNKNOWN
```

Step 27 confirms the same Setup response output is passed to `_requestSendPlistResponse` (`0x289f60`) at `0x28afba`, then sent as a binary-plist HTTP response. That does not expose which request keys Setup reads. Incoming `type`, value conversion, request stream multiplicity, type-110 request routing, and Type-111 default/rejection/generic handling remain unknown.

## Cross-correlation and prior-art comparison

| Field / concept | Prior art | Honda evidence | Match |
|---|---|---|---|
| `type` | xcertplay uses 110/111; Harman has a Type-111 route | Honda response writes type 110; request parser unavailable | Response-side analog only |
| UUID | Prior art has display identities | Honda local main dictionary inserts `uuid` numerically | Partial local concept; representation and wire use unknown |
| `dataPort` | Prior art returns a per-stream port | Honda response stream entry has dynamic `dataPort` | Honda response-side match |
| `streamConnectionID` | Present in prior-art protocol structures | No Honda Setup read/write correlation recovered | Unknown |
| Display role/list | Prior art has alternate display signaling | Honda builder returns one main-screen dictionary | No Honda secondary role/list proof |

Do not transfer prior-art acceptance, key names, or semantics onto Honda.

## Decision gate

```text
COPYDISPLAYSINFO INDIRECT CALLER: UNKNOWN; no stored pointer/table/caller recovered from tracked evidence
PHONE-FACING DISPLAY MESSAGE: UNKNOWN
DISPLAY SERIALIZER: UNKNOWN for CopyDisplaysInfo output; Setup response serializer is _requestSendPlistResponse (0x289f60)
DISPLAY UUID FLOW: ScreenCopyMain result property -> local `uuid` numeric-setter insertion; onward flow UNKNOWN
FEATURES MEANING: numeric masked property; bit meanings/value UNKNOWN
SETUP REQUEST STREAM KEY: UNKNOWN
STREAM TYPE PARSER: UNKNOWN
TYPE110 PATH: PARTIAL; stock response type=110/dataPort and phone-facing send confirmed; request-side path unknown
TYPE111 BEHAVIOR: UNKNOWN
REQUEST STREAM MODEL: UNKNOWN
DISPLAY-TO-STREAM BINDING: UNKNOWN
SECOND DISPLAY ADVERTISEMENT REQUIRED: UNKNOWN
CAPABILITY HOOK: none identified
SETUP HOOK: structural candidate at _connectionHandleMessage after Setup (0x28af72) and before serializer (0x28afba); not protocol-validated or implemented
READY FOR NEGOTIATION IMPLEMENTATION: NO
READY FOR FIRST LIVE NEGOTIATION EXPERIMENT: NO
BIGGEST BLOCKER: missing matching jmcs ELF plus complete caller/request-parser disassembly, preventing both indirect-reference recovery and incoming type dispatch analysis
```

### Hook assessment

No capability hook can be specified because the phone-facing capability boundary is unknown. A post-Setup/pre-serializer response mutation window exists as a structural Setup candidate, preserving stock Setup execution, but no request acceptance or Display-B correlation is established. No code or hooks were written.

## Artifacts and verification

Added the eight focused notes named in the milestone: `copy-displays-indirect-calls.md`, `honda-display-capabilities.md`, `honda-display-uuid-flow.md`, `honda-setup-request.md`, `honda-stream-type-parser.md`, `display-stream-correlation.md`, `honda-alt-screen-gating.md`, and `claritylink-display-b-architecture.md`. Updated `PROJECT_STATE.md`, `EVIDENCE_INDEX.md`, and `NEXT_ACTION.md`.

No tests were run because no code/model changed. `git diff --check` is required and will be run before commit. No `jmcs` binary was modified or accessed live.

**Next concrete task:** acquire/locate the exact offline `jmcs` ELF matching the saved VA map, then generate a complete ARM/Thumb xref/disassembly slice for CopyDisplaysInfo references and `_connectionHandleMessage` through Setup request reads. Until then, negotiation remains gated.
