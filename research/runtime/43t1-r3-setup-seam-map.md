# 43T1-R3 — Setup path and seam map

**Evidence boundary:** static control/data-flow facts below are `HONDA_CONFIRMED` only for the hash-matched `jmcs` ELF described in 43L/43M/43N. Project transaction behavior is `MODEL_ONLY`. Generic Apple CF, AOSP, ARM and external prior art do not prove Honda runtime behavior.

```text
HTTP message enters _connectionHandleMessage (0x28a30c)
  request parse / Setup request dictionary [sp+0x1c]
    [possible message-handler seam — before response construction; no safe registration shown]
  AirPlayReceiverSessionSetup (direct BL 0x28af72)
    stream extraction: reads request streams[] and dispatches supported types
    [possible Setup seam — before response construction; direct call only]
    creates mutable response and stock stream entry
    _AddResponseStream (0x284db8)
      obtains response['streams']; if absent creates mutable CFArray
      appends stock entry; stores array on response; releases local array reference
      [possible array-construction seam — during response construction; direct helper, no extension]
    response streams array receives stock entry/entries
      [possible response mutation seam — during response construction]
  _connectionHandleMessage success branch adds Honda metadata / CFObjectSetProperty (0x28afae)
    response remains live at [sp+0x54]
    [possible exact property-call seam — during response construction]
  stage connection=r4, message=r6, response=[sp+0x54], statusOut=&[sp+0x50]
  direct local Thumb BL _requestSendPlistResponse (0x28afba)
    [possible transaction wrapper — before serializer; requires rejected redirection]
    CFPropertyListCreateData(format 0xc8)
      [possible serializer seam — during serializer; no supported mediation found]
    HTTPMessageSetBody(serialized bytes)
      [possible body seam — after serialization; too late to change response graph]
    releases temporary CFData; returns HTTP status/statusOut
  caller tests return==0xc8 && statusOut==0
    [possible result/commit seam — after serializer; no natural callback shown]
  common cleanup releases request (0x28b048) and response (0x28b052)
    [response release — graph lifetime ends]
  later HTTPConnectionSendResponse (0x28b790)
    [network send seam — after serializer and response release]
  session teardown / CF object _Finalize (0x284d24)
    AirPlayReceiverSessionPlatformFinalize (0x28cd60)
    [cleanup/finalizer seam — existing Honda cleanup; no project-child subscription]
```

## Seam placement table

| Candidate | Position | Existing mediation? | Static assessment |
|---|---|---|---|
| HTTP message dispatch / Setup parser | before response construction | `UNKNOWN`; recovered call is internal | Would need a natural dispatch extension not found; handler parser is broad. |
| `AirPlayReceiverSessionSetup` | before response construction | direct BL caller only | Runs before caller's post-success metadata and serializer result. |
| `CFObjectSetProperty` at `0x28afae` | during response construction | no; direct internal BL | Exact callsite is narrow but code replacement needed, result not yet known. |
| `_requestSendPlistResponse` at `0x28afba` | before serializer | no; direct internal BL to local function | Best transaction context in caller frame, but only callable through rejected callsite redirection. |
| `CFPropertyListCreateData` | during serializer | no supported mediation found | Too low-level and shared; no request/session identity in its interface. |
| `HTTPMessageSetBody` | after serializer | no supported mediation found | Sees bytes; too late to mutate response graph. |
| serializer return/status check | after serializer | no standalone hook/API | Result is locally observable in caller; reaching it requires callsite replacement. |
| `HTTPConnectionSendResponse` | after serializer, after graph release | direct call in common handler | Too late for Type111 response mutation. |
| `AirPlayReceiverSessionPlatformControl` callback | unknown command dispatch/lifecycle | Honda-owned delegate; replacement semantics | Teardown ignores Type111; other command callback is not Setup response path. |
| session `_Finalize` / PlatformFinalize | cleanup/finalizer | Honda-owned direct lifecycle call | Actual cleanup boundary, but no child subscription and incomplete event coverage. |
| `libcarplay_proxy` callback record | callback/media dispatch | singleton replacement table | Not connected to Setup response construction; overwrite displaces stock consumer. |
| jmcs loader/preload | outside Setup path | no supported load/extension point found | API-17 primitives alone do not establish Honda integration. |
| external host/process | outside jmcs | no supported transparent path | Reject due authentication/transport and persistence risks. |

## Type110 and Type111 boundary

`HONDA_CONFIRMED` static evidence shows the recovered stream teardown parser recognizes 100/101/110 and skips unknown types; it does not establish Type111 support. `HONDA_CONFIRMED` response path evidence provides a place where an added entry could be serialized, but that is only a structural opportunity, not proof of schema, acceptance, security, or safe integration. `MODEL_ONLY` response mutation and Type110-preservation invariants remain offline contracts.

The exact non-inline seam question therefore has a negative result on current artifacts: every response-capable candidate requires code redirection or lacks an existing supported callback; every lifecycle candidate is destructive or lacks session-addressable subscription semantics.
