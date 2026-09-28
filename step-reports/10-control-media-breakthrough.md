# Step 10 — Control and media black-box breakthrough

**Status: PARTIAL, with a confirmed TCP wake endpoint and dictionary helper.** Offline-only. No vehicle, ADB, firmware patch, packet construction, or protocol implementation.

## Control findings

- `AirPlayReceiverSessionSetup` (`0x2854e1`) directly calls `AirPlayReceiverSessionScreen_Setup` (`0x287d5d`) at `0x28609c`.
- `AirPlayReceiverSessionScreen_Setup` calls `0x294598`, stores its returned words at screen-object `+0x10/+0x14`, and defaults to `0x46/0` if its status slot is set.
- `0x294598` uses Honda `CFLDictionaryGetValue` (`0x28f37c`) plus typed conversion (`0x293d40`). Input is CFL dictionary-compatible, but the key/value semantics remain unknown.
- `AirPlayReceiverSessionSetup` calls `ServerSocketOpen` (`0x2a0a34`) and stores its descriptor at outer receiver/session `+0x1418`.
- `ServerSocketOpen` uses `socket`, nonblocking mode, `bind`, and `listen`; call arguments at Setup supply stream socket/protocol values (SOCK_STREAM/TCP). `_ScreenThread` calls `SocketAccept` (`0x2a0480`) with a 10-second timeout. That helper uses `select()` and `accept()`. The incoming TCP peer connection is the event that completes the wait; no condition variable or semaphore signal was found in this path.
- A successful accept leads to `AirPlayReceiverSessionScreen_StartSession` (`0x2883a8`). The external caller/parser above `AirPlayReceiverSessionSetup` and accepted-connection request schema remain unresolved.

## Media findings

- Generic `ScreenStreamProcessData` invokes a global callback with the stream and process-data arguments.
- Honda `mc_ScreenStreamProcessData` (`0xbee91`) receives stream/context-like pointer, data pointer, and length; parses structured length-prefixed records and transforms framing.
- Helper `0x8e70c` validates and dispatches through an internal object function pointer at `+0x10`; it is not a proven decoder. Callback also calls `0x8ea18` twice.
- `jmcs` contains H.264/AVCC/Annex-B functions/strings and imported Android MediaCodec methods (including configure and output-buffer render APIs). The callback-to-pipeline xref and actual Surface construction/binding remain absent.
- Generic stream context APIs exist. The context assignment/recovery and link to a screen/session identity were not recovered.

## Decision gate

| Item | Result |
|---|---|
| Control transport class at wait endpoint | TCP listening socket / accepted TCP connection, confirmed |
| Request schema above Setup | Unknown |
| Setup lookup type | Honda CFL dictionary lookup + conversion, high confidence |
| Wake object | listening socket descriptor at outer receiver/session `+0x1418` |
| Wake producer | inbound peer connection, via `select()` readiness and `accept()` |
| Media parser | `mc_ScreenStreamProcessData` + custom callback dispatch at `0x8e70c` |
| H.264 boundary | H.264 capability strongly indicated in binary; callback linkage unresolved |
| Decoder / Surface | unknown for this stream path |
| Second session possible | UNKNOWN |
| Raw capture | HELPFUL, narrowly scoped to accepted TCP flow during setup/start |
| Ready for Display-B code | NO |

The precise implementation blocker is the absent evidence chain from accepted-session request through stream identity to a per-stream decoder and independent output target. See updated trace artifacts for address-level details.
