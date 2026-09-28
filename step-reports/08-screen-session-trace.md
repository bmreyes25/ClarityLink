# Step 8 — Primary screen-session trace

**Status: PARTIAL; transport, response schema, display-to-stream identity, and decoder/output consumer remain unresolved.** Work was offline against the focused saved `jmcs` and `libcarplay_proxy.so` static-analysis artifacts. No vehicle, ADB, firmware modification, protocol bytes, or Display B implementation was used.

## Findings

- `_ScreenThread` (`jmcs` VA `0x283dad`) waits on a semaphore in its screen-session context. On a successful wake, it invokes `AirPlayReceiverSessionScreen_StartSession` (`0x2883a9`) using the receiver screen-session object and a context pointer loaded from the surrounding session state. The upstream event/request that signals this semaphore is not identified.
- The worker-creation site is not identified in the bounded static artifacts. Its visible path calls `AirPlayReceiverSessionScreen_StopSession` (`0x288451`) during exit; a separate `_ScreenTearDown` helper exists, but its trigger/owner is unresolved.
- `StartSession` is receiver-side lifecycle setup. It initializes internal session fields, creates a generic `ScreenStream` (`0x28e209`), uses the main screen copy path, configures stream state/context, and starts it via `ScreenStreamStart` (`0x28e299`). It is not shown serializing or sending a protocol request.
- `AirPlayReceiverSessionScreen_Setup` (`0x287d5d`) reads values from a dictionary-like object using helper `0x294598`, but the upstream caller, keys, transport origin, and request/response semantics are not recovered.
- Generic stream APIs store a context pointer on each stream object and dispatch processing through function pointers. Honda's proxy still exposes a singleton callback table; stream-context presence does not prove the context identifies a screen or can route multiple streams.
- Honda `mc_ScreenStreamInitialize` increments a generic stream counter and creates callback context. This proves generic stream lifecycle support, not two accepted CarPlay display sessions.
- The concrete decoder creation and Android `Surface`/ExternalDisplay consumer are not recovered in this trace. Decoder cardinality is unknown.

## Decision gate

| Gate | Result |
|---|---|
| Screen start transport | UNKNOWN |
| Start request schema | UNKNOWN |
| Start response schema | UNKNOWN |
| Display-to-stream binding | UNKNOWN; local session-to-stream object association only |
| Callback dispatch | Generic stream/context dispatch exists; explicit screen/session ID unknown; Honda proxy registration singleton |
| Decoder cardinality | UNKNOWN |
| Output surface model | UNKNOWN in CarPlay native path |
| Second session structurally possible | UNKNOWN; generic object machinery exists, Honda integration remains single-screen/single-callback |
| Strategy B | PLAUSIBLE as investigation architecture; implementation BLOCKED |
| Raw capture | HELPFUL after the actual control channel is identified; Identification-only capture is insufficient |
| Ready to build Display B negotiation code | NO |

## Choke points

1. `gMainScreen` initialization and `CopyDisplaysInfo` selecting registry entry zero.
2. The unidentified setup/event producer and response mapping feeding the `_ScreenThread` lifecycle.
3. The singleton `libcarplay_proxy.so` callback table.
4. The unrecovered per-stream decoder and output-surface consumer.

The earlier output-path work for HondaHack confirms that Android Display 1 can host a normal View; it does not establish that the CarPlay receiver can provide a second decoded stream or route it there.

## Next evidence needed

Identify the exact caller and input path for `AirPlayReceiverSessionScreen_Setup`, then follow the event/response that wakes `_ScreenThread` into stream creation. For the downstream leg, resolve `mc_ScreenStreamProcessData` callback arguments and locate its concrete decoder/output consumer. Only after the transport endpoint is known should a narrowly scoped passive capture be designed.

## Artifacts

- [screen-start-transport.md](../research/carplay/screen-start-transport.md)
- [primary-screen-start-request.md](../research/carplay/primary-screen-start-request.md)
- [video-stream-binding.md](../research/carplay/video-stream-binding.md)
- [decoder-output-path.md](../research/carplay/decoder-output-path.md)
- [display-b-interposer.md](../research/carplay/display-b-interposer.md)

No new wire-model fields were added because request/response semantics and serialized values remain unsupported by evidence.
