# ClarityLink Display B architecture — Step 29 update

## State of evidence

The lower response path remains confirmed: `_connectionHandleMessage` calls `AirPlayReceiverSessionSetup`, whose response contains a `streams` array with stock `type=110` and dynamic `dataPort`; the caller passes that same response to the binary-plist HTTP serializer. The caller's post-Setup/pre-serializer interval remains a structural response mutation candidate.

The display capability builder is separate in current evidence. `AirPlayReceiverSessionScreen_CopyDisplaysInfo` returns one dictionary from one main-screen object, with `edid`, `features`, `maxFPS`, physical/pixel dimensions, and numeric-setter `uuid`. Its indirect caller, interface slot, parent, serializer, and protocol phase remain unlocated. The request-side stream parser remains unknown; therefore Type-111 generic acceptance is not established.

## Correlation and design gate

No evidence joins display UUID, stream type, stream ID, connection ID, session ID, or `dataPort`. Do not implement display negotiation or infer that type 111 is accepted. A future hook plan requires (1) the actual capability boundary and message schema, and (2) request parser/type handling plus the relation between request identity and response stream/listener.

| Potential hook | Current candidate | Status |
|---|---|---|
| Capability advertisement | None identified | Unknown |
| SETUP response | `_connectionHandleMessage`, after Setup returns and before `_requestSendPlistResponse` (`0x28af72`–`0x28afba`) | Structural candidate only; no implementation |

**Negotiation implementation ready:** no. **Live negotiation experiment ready:** no. Offline evidence acquisition is the next action; no vehicle, ADB, ptrace, patch, hooks, or Type-111 implementation in Step 29.
