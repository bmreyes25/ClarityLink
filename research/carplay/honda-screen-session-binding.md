# Honda Type-110 screen-session binding — Step 33

The stock Type-110 SETUP path performs the following sequence within `AirPlayReceiverSessionSetup` (`0x2854e0`): it reads the request stream's 64-bit `streamConnectionID`, rejects zero, derives a screen AES key/IV using that ID and the receiver session master key, installs the derived material through `AirPlayReceiverSessionScreen_SetSecurityInfo`, opens a TCP listener on an ephemeral port, and appends a response entry containing `type=110` and `dataPort`.

This is enough to confirm that the stream connection identifier participates in per-screen security context and that a port is allocated in the same per-entry flow. It does not prove the accepted socket later stores or looks up that ID, or that the ID chooses a display. The mapping is implicit at setup time through branch-local key derivation/listener/response construction; the accepted-connection object association remains unproven.

`AirPlayReceiverSessionScreen_Setup` (`0x287d5c`) is called immediately before the inlined `_ScreenSetup` work, with screen-session object, request stream dictionary, and a `uint32_t` session ID. It reads a separate dictionary value and writes a 64-bit pair at object offsets `+0x10/+0x14`; the semantic key has not been established as `streamConnectionID`. Therefore the persistent layout question remains open.

| Claim | Status |
|---|---|
| SETUP stream ID read as uint64 | Confirmed |
| ID influences screen AES key/IV | Confirmed |
| Derived crypto installed on screen session | Confirmed |
| Same branch creates TCP listener and returns its port | Confirmed |
| ID stored persistently in a named screen-session field | Unknown |
| accepted TCP socket mapped back to ID | Unknown |
| ID selects `/info` display UUID / display role | No evidence found |

No Type-111 behavior is implemented or inferred from this Type-110 path. A ClarityLink Type-111 path would need the correct stream-ID-based cryptographic context if Honda/iPhone protocol parity requires it; schema and parity remain unknown.
