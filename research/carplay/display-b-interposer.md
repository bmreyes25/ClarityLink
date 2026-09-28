# Display B interposer assessment

**Status: plausible architecture, implementation blocked by missing control/identity schema and decoder/output consumer.**

The preferred receiver interposer concept remains a Honda receiver extension, but the newly bounded trace did not discover a small, proven protocol hook. `AirPlayReceiverSessionSetup` directly calls `AirPlayReceiverSessionScreen_Setup` at `0x28609c`; Setup uses helper `0x294598` and writes receiver fields at `+0x10/+0x14`. The external caller/input source and schema remain unknown. `_ScreenThread` waits using helper `0x2a0480` on `[r4 + 0x1418]`, and a successful return leads to `StartSession`; the helper primitive and signal producer remain unknown. `StartSession` creates and starts a generic `ScreenStream`. The transport, returned identity, and decoder output consumer remain outside recovered edges.

| Control point | Current evidence | Needed for B | Confidence / risk |
|---|---|---|---|
| Display descriptor | Honda creates one `gMainScreen`; `CopyDisplaysInfo` chooses registry index 0 | Evidence-backed second descriptor schema and supported enumeration/serialization | High confidence current main-only path; high protocol risk |
| Session setup producer | Setup direct caller is `AirPlayReceiverSessionSetup`; event wait object/helper identified by address/offset, signal producer unknown | Identify parser/transport/event and a supported second setup transaction | High confidence local calls; high unknown risk |
| Stream creation and identity | `StartSession` creates one generic stream object; no wire ID-to-screen key recovered | Distinct returned stream identity and binding | High confidence object creation; high identity risk |
| Callback dispatch | Honda proxy registers a singleton six-function callback table | Multi-stream dispatch with preserved A callback/context | High confidence singleton; high ABI risk |
| Decoder/output | `mc_ScreenStreamProcessData` receives structured input; concrete decoder and surface consumer not recovered | Per-stream decoder handoff and independent Honda ExternalDisplay target | Unknown; high integration risk |

The narrowest conceptually plausible intercepts are (1) the screen descriptor copy/advertisement path, (2) the receiver session setup/response mapping that creates each stream, and (3) proxy callback dispatch to per-stream consumers. Evidence does not establish that these are sufficient: a separate transport/parser hook and a decoder/output hook may also be required.

## Decision

- **Second session structurally possible:** UNKNOWN. Generic multiple `ScreenStream` objects are structurally represented; Honda's actual setup/advertisement and callback boundary are main-only/singleton.
- **Strategy B:** PLAUSIBLE as a future investigation architecture; BLOCKED for implementation by absent request/response schema, binding key, and concrete decoder consumer.
- **Raw capture:** HELPFUL only after identifying the control channel. Identification capture alone is not sufficient. The useful screen-session capture window is the setup request/response immediately before the event that wakes `_ScreenThread` and results in `ScreenStreamStart`; video capture should wait until its receiver endpoint is known.
- **Ready to build Display B negotiation code:** NO.

No wire fields, packet bytes, protocol patches, or deployment steps are proposed. See `screen-setup-input.md`, `screen-thread-event.md`, `video-callback-trace.md`, `carplay-decoder.md`, and `primary-screen-end-to-end.md` for the bounded findings.
