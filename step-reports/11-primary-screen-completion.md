# Step 11 — primary screen completion

**Outcome: PARTIAL; offline static trace only.** Starting commit `5bdab19`. No vehicle use, ADB reconnection, firmware modification, or generated packet bytes.

## Findings

- Listener: `AirPlayReceiverSessionSetup` calls `ServerSocketOpen`; descriptor stored at outer session `+0x1418`; `_ScreenThread` calls `SocketAccept` (`select()` then `accept()`). Address and port cannot be recovered from the tracked excerpt. No port advertisement edge is proven.
- Accepted TCP reader/parser: no accepted-fd first read is present in the tracked evidence. TCP framing and CONTROL/MEDIA/MIXED role remain UNKNOWN.
- Callback: `ScreenStreamProcessData` dispatches into Honda `mc_ScreenStreamProcessData`. Its callback-level framed records reach helper `0x8e70c`, which invokes a function pointer at an internal object `+0x10`. Containing object assignment sites and concrete targets are not recovered.
- Codec/output: H.264/AVCC helpers and MediaCodec imports are in `jmcs`; the stream callback-to-H.264 call path, decoder owner/cardinality, and actual output Surface are unproven.
- Context: generic stream context get/set operations and Honda per-stream initialization/counting exist. Unique semantic identity and display A/B binding remain UNKNOWN.
- Second screen: generic registry/stream machinery is present, but Honda initializes one main screen, advertises from `ScreenCopyMain`, and has singleton proxy callbacks. Narrow audit gives **PARTIAL** latent capability, not proven R15 support.

## Decision gate

| Question | Result |
|---|---|
| Primary screen path | PARTIAL |
| Listener port / TCP role | UNKNOWN / UNKNOWN |
| H.264 / decoder / Surface | UNKNOWN / UNKNOWN / UNKNOWN |
| Stream identity | PARTIAL; per-stream context mechanism, display identity unknown |
| Second session structurally possible | UNKNOWN |
| Ready for Display B | NO |
| Raw capture | HELPFUL, once endpoint is known; one short peer-to-head-unit TCP startup flow |

**Single biggest blocker:** there is no evidence-backed accepted-fd first-read/parser edge connecting the listener to the screen stream callback; the same missing source slice also prevents endpoint and TCP-role recovery.

No tests were run: this milestone changes only research documentation and adds no executable code. `git diff --check` is requested as a documentation-integrity check.
