# Display B interposer assessment

**Status: implementation blocked by request/schema and decoder/output binding.**

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
- **Ready to build Display-B code:** NO.

**Raw control capture: HELPFUL.** Now that a TCP listening/accept path is proven, a narrowly scoped passive capture can resolve only the accepted connection's application protocol and request/event schema. Capture the single peer-to-`jmcs` TCP flow during one screen-session setup/accept/start window. Exact listener port/address and request framing are still unknown; resolve them from local runtime metadata or a narrowly filtered endpoint observation. Do not capture broad USB traffic. No packet construction or firmware modification is indicated.
