# Honda Setup stream-entry schema (recovered fields)

Evidence: static disassembly of local `jmcs`; stream entry built inside `AirPlayReceiverSessionSetup` and appended by `_AddResponseStream`.

| Key | CF value type | Value source | Phone-facing |
|---|---|---|---|
| `type` | CFNumber-like integer | constant `110` | **Confirmed**: response object reaches binary plist serializer |
| `dataPort` | CFNumber-like signed 64-bit integer | ephemeral TCP listener bound to port 0; assigned port | **Confirmed**: response object reaches binary plist serializer |
| Other keys in primary entry | unknown | not fully decoded | unknown |

The containing response has a `streams` CFArray. `_AddResponseStream` obtains or creates a mutable array, appends the entry, and sets it on the response. The Setup caller passes this same response to `CFPropertyListCreateData` via `_requestSendPlistResponse`; therefore the stock stream list reaches the phone-facing HTTP binary-plist body.

No Honda-side evidence in this trace establishes streamConnectionID, sessionID, UUID, timing, crypto/security, latency, or video-format fields inside the stream-entry dictionary. Setup separately initializes security state for the receiver session; whether another stream may reuse it is unknown. `type=111` remains prior-art only; the fixture's secondary entry is synthetic and not a recovered schema.
