# Display B interposer assessment

**Status: implementation blocked by request/schema and decoder/output binding.**

The Step 11 offline completion record narrows the primary blocker: the tracked artifact set lacks the accepted-fd first-read/parser edge and endpoint recovery. Therefore TCP role and framing remain unknown. See `screen-tcp-listener.md`, `screen-tcp-framing.md`, and `primary-screen-end-to-end.md`.

The control wake mystery is resolved at the primitive level: `+0x1418` contains a listening socket descriptor created by `ServerSocketOpen`; `_ScreenThread` uses `SocketAccept` (`select()` then `accept()`). The incoming TCP connection makes the wait complete. The transport above `AirPlayReceiverSessionSetup` and schema on that accepted connection are still unknown. Setup's `0x294598` lookup is a Honda CFL dictionary lookup/conversion, but its key and semantic value names remain unresolved.

The media callback receives a stream/context-like object, data, and length. Helper `0x8e70c` dispatches through a function pointer in an internal object; H.264/AVCC helpers and Android MediaCodec imports exist in the same ELF, but are not linked to this callback in the current evidence. No output Surface has been identified.

| Control point | Evidence | Display B gate |
|---|---|---|
| Session setup input | `AirPlayReceiverSessionSetup` -> `AirPlayReceiverSessionScreen_Setup`; CFL dictionary lookup; key meaning unknown | Resolve upstream dispatcher and exact request/config semantics |
| Connection/wake | per-session TCP listener at `+0x1418`; `_ScreenThread` accepts peer connection | Resolve listener port/address source and accepted connection's request framing |
| ScreenStream | main session starts generic `ScreenStream` after accept | establish a second independently owned stream and lifecycle |
| Callback | singleton Honda callback table, generic stream argument and per-stream context APIs | prove dispatch can distinguish streams without overwriting primary callback |
| Decoder/output | H.264 and MediaCodec APIs exist; no call/object edge from callback; Surface unknown | prove per-stream decoder and output target creation/binding |

- **Two screen-session objects:** UNKNOWN.
- **Two ScreenStream objects:** generic APIs are instance-shaped, but Honda's singleton callback path and observed single main screen do not prove two active sessions: UNKNOWN end-to-end.
- **Two decoder objects:** UNKNOWN.
- **Two output Surfaces:** UNKNOWN.
- **Callback dispatch can differentiate streams:** YES at generic ABI via stream argument; semantic screen/display identity remains UNKNOWN.
- **Second session structurally possible:** UNKNOWN.
- **Two TCP listeners:** UNKNOWN.
- **Ready to build Display-B code:** NO.

**Raw TCP capture: HELPFUL after local endpoint resolution.** A short peer-to-head-unit TCP startup window could identify application framing and role. Do not capture broad USB traffic. No packet construction or firmware modification is indicated.
