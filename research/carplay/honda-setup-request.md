# Honda SETUP request parsing — Step 29

## Confirmed outer path

The Step 27 static trace identifies `_connectionHandleMessage` (`0x28a30c`) as the HTTP request dispatcher. It obtains a request-body property-list dictionary and passes that dictionary as argument `r1` to `AirPlayReceiverSessionSetup` (`0x2854e0`) at call site `0x28af72`; `r0` is the session and `r2` is the response output slot. The response is subsequently serialized as a binary plist. This confirms the caller-side object handoff, not the body's exact parse helper, allocation/ownership details, HTTP method/path predicate, or route registration.

## Missing request-side details

The tracked checkout has no full `_connectionHandleMessage` or Setup request-read disassembly, no exact `jmcs` ELF, and no complete request parser excerpt. Therefore the following remain unknown:

| Item | Status |
|---|---|
| HTTP body parser function / binary-plist parse call | Unknown exact helper; outer parsed-dictionary handoff is documented |
| Request-object construction and body ownership | Unknown |
| Method and path identifying SETUP | Unknown |
| Incoming dictionary keys read by Setup | Not inventoried from primary disassembly |
| `streams` request array and its element schema | Unknown |
| Request key `type` | Not confirmed as read by Honda |
| IDs / UUID / connection identifiers | Unknown |

Do not infer request schema from the response-side `streams` array or its `type=110` entry. Recover the exact firmware ELF plus dispatcher and Setup disassembly before naming a request key or claiming a stream loop.
