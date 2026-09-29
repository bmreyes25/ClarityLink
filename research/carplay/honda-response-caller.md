# Honda Setup response caller

Binary: local `jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`.

| Field | Recovery |
|---|---|
| Direct callers found | one: `_connectionHandleMessage` (no other direct call instruction in this `jmcs` ELF) |
| Caller | `_connectionHandleMessage` |
| Address/module | `0x28a30c`, `AirTunesServer.c` |
| Classification | Phone-facing HTTP request handler (static path; live phone transaction not captured) |
| Request source | Incoming HTTP connection/message; body decoded to a CF-style property-list dictionary |
| Call site | `0x28af6a–0x28af72` |
| Setup arguments | `r0 = receiver session` (`[r10+0xf4]`), `r1 = parsed request dictionary`, `r2 = &response` (`sp+0x54`) |
| Status handling | `r0` is saved/checked; nonzero follows error response path; zero continues to response setup |
| Post-call use | `sp+0x54` passed unchanged in `r2` to `_requestSendPlistResponse` at `0x28afba` |
| Cleanup | Same response pointer conditionally `CFRelease`d at `0x28b04e–0x28b054` |

The dispatcher later calls `HTTPConnectionSendResponse` at `0x28b790`. The HTTP server registration/callback edge into `_connectionHandleMessage` and exact URI route are not recovered here. See `honda-setup-response.md` for the complete response dataflow.
