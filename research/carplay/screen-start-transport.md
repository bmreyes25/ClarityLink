# Screen start control transport trace

**Scope:** focused static review of the ignored MY16ADA build 1.F1A2.45 `jmcs` and `libcarplay_proxy.so` analysis artifacts. No live session, protocol capture, vehicle, or firmware change was used. This report records the furthest proven edges and the unresolved transport boundary.

## Result

`_ScreenThread` (`jmcs`, VA `0x283dad`) calls `AirPlayReceiverSessionScreen_StartSession` (VA `0x2883a9`) after its `SocketAccept` wait succeeds (the wait is a `select()` on a listening TCP socket, followed by `accept()`). In that path, `StartSession` creates and starts an internal generic `ScreenStream` using `ScreenStreamCreate`, property/context helpers, and `ScreenStreamStart`. This proves receiver-side lifecycle setup, not construction or transmission of a request to the phone.

The session API is in `jmcs`'s Apple/AirPlay receiver implementation. The saved disassembly does not show a socket send, HTTP/RTSP request, plist encoder, iAP2 message enqueue, USB channel write, or a named setup command in `StartSession`. `AirPlayReceiverSessionScreen_Setup` parses a dictionary-like object using helper `0x294598`, but the actual caller that supplies it, its keys, and any wire/IPC origin are not recovered in the bounded artifacts. It is therefore not justified to classify the screen-start exchange as iAP2, AirPlay control, RTSP/HTTP, plist, or proprietary serialized bytes.

| Question | Finding | Confidence |
|---|---|---|
| Function owner | `jmcs`, Apple/AirPlay receiver screen-session implementation | High (symbol and binary) |
| Thread owner | `_ScreenThread`, VA `0x283dad` | High |
| Screen-session input | Thread context at `r4`; it passes screen-session object at `[r4 + 0x1400 + 0x14]` and a context-derived pointer `[ *(r4+0x0c) + 0xb0 ]` to `StartSession` | High for register/memory flow; semantic type of second pointer unknown |
| Trigger | listening TCP socket fd at `[r4 + 0x1400 + 0x18]`; `SocketAccept` uses `select()` then `accept()` with a 10-second timeout | High; inbound peer connection makes the wait complete |
| `StartSession` arguments | `r0` receiver screen-session object; `r1` passed setup/context pointer from the thread | High for call ABI; pointee schema unknown |
| Request construction | Not present in the traced `StartSession` body; it creates/configures/starts `ScreenStream` | High for visible body, not a proof the broader stack lacks request construction |
| Transport/channel | Unknown | Unknown |
| Request/response names and serialized fields | Unknown | Unknown |
| Return | `StartSession` returns status from internal setup path and calls session cleanup helper on error; numeric status semantics not mapped | High for control flow, low for enum semantics |

## Internal stream lifecycle evidence

At VA `0x2883a9`, `StartSession` initializes session fields, invokes a helper on session storage near `+0x1e8`, calls `ScreenStreamCreate` (`0x28e209`) with the supplied context, obtains main screen data through `ScreenCopyMain` (`0x2a17fd`), configures stream properties/context through indirect helpers, and invokes `ScreenStreamStart` (`0x28e299`). The resulting stream operations dispatch through global function pointers. `ScreenStreamProcessData` forwards its stream pointer and data/timing arguments through a generic function pointer; it does not expose an explicit screen ID in the wrapper signature.

`AirPlayReceiverSessionScreen_Setup` (`0x287d5d`) reads properties from its second argument via helper `0x294598`, then stores the returned values in the receiver object. This establishes a structured internal setup API. It does not reveal whether the incoming object came from a network control protocol or internal IPC.

## Exact missing edge

The remaining control edge is upstream of `AirPlayReceiverSessionSetup`: identify its caller/dispatcher, the source and semantics of the CFL dictionary input, and the accepted TCP request parser. Socket creation and acceptance are now proven, but the request schema and downstream accepted-socket consumer are not. An Identification-only USB capture would not settle this without first proving the exchange traverses that link.

## Capture value

- **Raw Identification capture:** helpful only for iAP2 Identification fields; not sufficient evidence for this screen-session path.
- **Screen-session control capture:** helpful now that the listener and TCP accept path are proven. The needed window is only the inbound accepted TCP flow around `_ScreenThread`'s successful `accept()` and `ScreenStreamStart`; first resolve the listener port/address from local code/runtime evidence.
- **Video capture:** not yet specified; first establish whether `ScreenStreamProcessData` input arrives from a distinct endpoint/channel and how it is keyed.

No packet bytes or guessed message schema are supplied.
