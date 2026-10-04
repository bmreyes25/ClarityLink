# 43T1-R3C — Setup entry and cleanup pairing

This table is the architecture gate. A path qualifies only when the same session identity is available at an additive Setup entry and a cleanup event, without displacing Honda state or requiring a rejected runtime redirect.

| Entry candidate | Cleanup candidate | Same identity? | Setup mutation possible? | Additive? | Runtime redirect needed? | Result |
|---|---|---|---|---|---|---|
| Direct `AirPlayReceiverSessionSetup(session, request, responseOut)` | Session `_Finalize(session, context)` → Honda finalizer/platform cleanup | Raw pointer appears at both internal endpoints, but no generation/non-reuse promise; project cannot observe either through supported API | Internally response is mutable; external project cannot safely enter | No demonstrated project subscription; delegate is a whole-record replacement | Yes for project entry into direct call; rejected inline redirect would violate R2 | `REJECT_REPLACEMENT` |
| Server delegate `sessionCreated(session)` before Setup | Session delegate finalizer or `sessionFailed` | Session pointer passed at creation; failed/destroy path does not prove same session cleanup to additive consumer | No Setup response access is provided by create callback | No; server delegate record copied wholesale | Would require replacing callback or unsupported dispatch | `REJECT_REPLACEMENT` |
| Session delegate Setup/control/property callback | Same delegate finalizer callback | One session object | No callback identified as additive Setup-response observer; control delegate does not see the Setup response | No; 44-byte Honda delegate is occupied and copied wholesale | Yes to replace/redirect | `REJECT_REPLACEMENT` |
| Global Setup HTTP response serializer `_requestSendPlistResponse` | Global destroy event callback | No; serializer has session in caller context, event supplies only interface+event | Response can be changed before serialization internally | No observer chain on serializer; global event is a single slot | Yes to intercept serializer call; local BL patch prohibited | `REJECT_UNSAFE` |
| `_AddResponseStream` / response CFArray append | `tearDownStreams` parser or `_Finalize` | No project identity relation in records; response lifetime ends before cleanup | Structural append exists, but external safe caller absent; Type111 compatibility unknown | Data array append is not additive callback registration | Yes to reach internal helper from outside | `REJECT_NO_CLEANUP` |
| Setup success event inferred from global interface callback | `MC_DEV_CARPLAY_SESSION_DESTROYED` | No: destroy callback carries interface/event, no session pointer or generation | No Setup event/response mutation path shown | No; one global callback slot | Would require replacing global callback | `REJECT_NO_IDENTITY` |
| Type110 `streamConnectionID` observation | Session finalizer / disconnect | No mapping recovered from ID to session cleanup; ID reuse semantics unknown | Value participates in stock Type110 setup only; no Type111 extension contract | Not a registration mechanism | Requires unsupported interception to observe/act on both ends | `REJECT_NO_IDENTITY` |
| Hypothetical project-owned sidecar keyed by session pointer + local generation | Honda finalizer/project watchdog | Project identity could be paired only after project observes both events; finalizer is not additively observable and global event lacks session | Model can represent a response mutation, but no supported Setup entry | No demonstrated additive entry or cleanup observer | A new runtime entry/redirect required; no such supported route evidenced | `REJECT_NO_SETUP` |
| Supported plugin/provider/observer path | Matching session cleanup registration | None recovered | None recovered | No append-only mechanism found | Unknown plugin route cannot justify runtime use | `UNKNOWN` mechanism does not meet gate | `REJECT_NO_SETUP` |

## Pairing result

**No qualifying Setup + cleanup pair was found.** Honda has a useful internal Setup transaction and a real session finalizer, but these are not a paired extension interface. The available callback routes are replacement-only or single-slot, and the global destroy event omits session identity. The response graph is transaction-scoped and released before later cleanup. An external project map would be an unconnected model, not a statically supported architecture.

## Gate status

| Requirement | Evidence status |
|---|---|
| Additive/non-replacement entry | No |
| Stable session identity | No; raw pointer only, generation/reuse unknown |
| Setup visibility | Honda internal only; no project-supported additive visibility |
| Cleanup visibility | Honda internal; no project-supported same-session subscription |
| No rejected mutation | No route evidenced without callback replacement or prohibited redirect |
| Preserve Type110 | Cannot be established for an inserted project record; stock Type110 path remains Honda-owned |

Decision: `RUNTIME_INTERPOSITION_ARCHITECTURE_EXHAUSTED`.
