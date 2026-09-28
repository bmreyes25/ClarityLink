# Step 9 — Control and decoder trace

**Status: PARTIAL.** Offline-only review of the evidence-indexed `jmcs` and `libcarplay_proxy.so` artifacts. The vehicle remained unused; no ADB, firmware changes, packet construction, or broad repository/firmware scan was performed.

## Results

- **Setup caller:** `AirPlayReceiverSessionSetup` (`jmcs` VA `0x2854e1`) directly calls `AirPlayReceiverSessionScreen_Setup` at `0x28609c`. Setup takes a receiver screen-session pointer and a lookup-object pointer. Helper `0x294598` produces two values stored at offsets `+0x10/+0x14`; the key bytes, object type, and semantic field names remain unresolved.
- **Wake event:** `_ScreenThread` waits on `[r4 + 0x1418]` through helper `0x2a0480`. A zero return takes the path that calls `AirPlayReceiverSessionScreen_StartSession` at `0x283eb6`. The helper primitive, its initializer, and signal/post callers are absent from the focused excerpts.
- **Control transport/parser:** Unknown. The complete xref/caller chain above `AirPlayReceiverSessionSetup` is not in the indexed focused disassembly. No socket/HTTP/RTSP/iAP2/plist classification is supported.
- **Media callback:** Generic `ScreenStreamProcessData` dispatches a stream pointer plus data and metadata arguments through a function pointer. Honda `mc_ScreenStreamProcessData` (`0xbee91`) parses structured data and reaches helper `0x8e70c`; no proven H.264 frame-to-decoder edge is present.
- **Decoder/output:** Decoder creation/library/cardinality and Android output Surface remain unknown. The separate hardware decoder probe does not establish the CarPlay consumer.
- **Identity/routing:** Generic per-stream context exists; screen/session identity semantics remain unknown. Honda's callback table is singleton.

## Decision gate

| Item | Result |
|---|---|
| Setup caller | `AirPlayReceiverSessionSetup`, confirmed direct caller |
| Thread wake | helper `0x2a0480`, object at session `+0x1418`; primitive and producer unknown |
| Control transport | Unknown |
| Setup schema | Partial; helper-derived fields only, no key/type/value recovered |
| Stream callback | Generic stream dispatch -> Honda `mc_ScreenStreamProcessData` |
| Decoder/output Surface | Unknown |
| Primary display-stream binding | Unknown |
| Second session possible | Unknown |
| Display-B interposer | Plausible for investigation; blocked for implementation |
| Raw capture | Helpful after endpoint identification; not a broad USB capture |
| Ready for Display-B code | No |

## Exact missing artifacts

1. `jmcs` cross-references and caller body above `AirPlayReceiverSessionSetup`, including its input origin and the source of the object passed into Setup.
2. `jmcs` xrefs for helper `0x2a0480` and the wait object at screen-session `+0x1418`, including initialization and every signal path.
3. Focused decoder/output call graph from Honda `mc_ScreenStreamProcessData` and helper `0x8e70c` into the concrete decoder and output target in the indexed receiver binaries/dependencies.

The local ignored binary exists (`extracted/system-vendor/system/bin/jmcs`), but the available saved focus artifact omits the needed caller/event/decoder xrefs. The native reverse-engineering environment is also missing the `capstone` Python package on the active interpreter, so deeper disassembly was not available through the checked local script path. No package installation was attempted.

## Artifacts

- `research/carplay/screen-setup-input.md`
- `research/carplay/screen-thread-event.md`
- `research/carplay/video-callback-trace.md`
- `research/carplay/carplay-decoder.md`
- `research/carplay/primary-screen-end-to-end.md`
- `research/carplay/display-b-interposer.md`

The offline session model was not changed: no new semantic setup fields, event types, stream identity, decoder binding, or output binding are supported by this evidence.
