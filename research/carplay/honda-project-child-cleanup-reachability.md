# Honda project-child cleanup reachability — Step 43L.1

**Classification:** Honda cleanup reachability PARTIAL; project child cleanup via Honda NOT_PROVEN. Evidence is offline static disassembly of the hash-matched Honda binary. The project registry is `SYNTHETIC_TEST_VALUE` and is not wired into Honda.

## Reachability chain and limits

After successful plist/body preparation, `_connectionHandleMessage` continues to HTTP send at `0x28b790`. `HTTPConnectionSendResponse` commits headers and places the connection into write state. `_HTTPConnectionRunStateMachine` (`0x29d698`) runs `SocketWriteData` (`0x2a01c0`) and `writev`; complete writes return to the state machine, partial/EAGAIN writes resume, and terminal errors stop the connection and call its close callback. `_connectionFinalize` (`0x289d90`) calls `AirPlayReceiverSessionTearDown` (`0x2852ec`) only when the connection context's session pointer at `+0xf4` is non-null. This is a conditional connection-to-session edge, not proof that every HTTP transaction or write failure owns a unique session.

`AirPlayReceiverSessionTearDown` reaches PlatformControl with `tearDownStreams`; the parser handles types 100/101/110 and skips unknown 111. Normal tearDown then performs screen/stream/control/timing cleanup. Separately, the CF runtime `_Finalize` invokes installed Honda `_AirPlayHandleSessionFinalized`, then PlatformFinalize and object teardown. The callback table is Honda-owned and `AirPlayReceiverSessionSetDelegate` replaces the whole 44-byte table. Step 43L.2 found an additional app-facing `MC_DEV_CARPLAY_SESSION_DESTROYED` interface event, but its global 24-byte callback record is also replaced wholesale and its `(interface,event)` callback omits the AirPlay session pointer. It is not a non-destructive, session-addressable subscriber mechanism. PlatformFinalize remains a Honda session-object cleanup point but has no proven project lookup/subscription path. Treat Honda finalization as optional; project cleanup must be generation-owned.

The response dictionary is released by `_connectionHandleMessage` after synchronous serialization. It does not survive to HTTP write or parent teardown and cannot own/reach project resources for those later events. A failed Setup returns before successful response delivery; that handler branch itself does not establish later session finalization. Parent session teardown is not guaranteed merely because response delivery failed; connection finalization's session pointer is conditional and session/object lifetime may continue elsewhere.

| FAILURE / FINALIZATION EVENT | Honda function | Session pointer available? | Project child reachable? | Cleanup attachable without new hook? | Confidence |
|---|---|---|---|---|---|
| Setup nonzero before response | Setup caller; stock Setup cleanup | Caller has session pointer | no project child should exist if prepare is gated on success | n/a | HONDA_CONFIRMED stock path; project rule SYNTHETIC_TEST_VALUE |
| Plist/body helper failure | `_requestSendPlistResponse` then handler cleanup | caller session remains in frame; response is released | not via response graph; project registry could reach by opaque key only if integration installed | no supported callback proven | HONDA_CONFIRMED for lifetime; cleanup edge HONDA_UNKNOWN |
| HTTP header commit failure | `HTTPConnectionSendResponse` → state machine close | connection context session only if non-null | no automatic project registry lookup | no | HONDA_CONFIRMED conditional session edge |
| Terminal socket write failure | `SocketWriteData` → stop/close → `_connectionFinalize` | conditional context `+0xf4` | no direct child pointer | no | HONDA_CONFIRMED path; parent tearDown conditional |
| Normal `tearDownStreams` | `AirPlayReceiverSessionTearDown` → PlatformControl | session argument available | parser ignores Type111; app delegate not called on stream branch | no project callback | HONDA_CONFIRMED |
| Session object finalization | `_Finalize` → `_AirPlayHandleSessionFinalized` / PlatformFinalize | session argument available in Honda path | app event gets interface+event only | no non-destructive project subscription/chaining | HONDA_CONFIRMED finalizer; project edge NOT_PROVEN |
| Session/connection reuse or pointer reuse | lifecycle across requests | raw pointer may recur; stable identifier not recovered here | generation registry can disambiguate only when project observes registration | no stable Honda generation field proven | HONDA_UNKNOWN |

Honda gives a raw session pointer in Setup and finalization paths, but no stable session-generation value was recovered. Project `ProjectSessionKey(identity,generation)` is a synthetic stale-pointer guard, not Honda state. A project-owned generation can be minted when it first safely observes a session and must be checked on every later operation.

```text
HONDA CLEANUP REACHABILITY: PARTIAL
PROJECT CHILD CLEANUP VIA HONDA: NOT_PROVEN
```
