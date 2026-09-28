# CarPlay decoder and output trace

**Verdict: decoder, cardinality, and output Surface remain unknown.**

The bounded `jmcs` trace reaches Honda's `mc_ScreenStreamProcessData` (`0xbee91`) and its structured input processing, but not a proven H.264 decoder call. The generic wrapper dispatches callbacks by stream object and supports a stream context pointer. Honda's proxy callback registration is singleton. Neither fact establishes the decoder ownership model.

| Item | Result |
|---|---|
| Frame/packet receiver | `mc_ScreenStreamProcessData`, but exact H.264 frame boundary is unknown |
| Payload type | Structured records are parsed; H.264-bearing payload not proven at a specific callback argument |
| Stream context available | Yes, structurally through generic per-stream context APIs; meaning unknown |
| Decoder creation/library/object | Unknown |
| Codec | H.264 helpers/strings exist elsewhere in native artifacts; linkage to this callback is unproven |
| Instance storage/cardinality | Unknown |
| Dimensions source | Unknown |
| Start/stop/destroy | Generic stream lifecycle callbacks exist; decoder lifecycle is unknown |
| Output object type/owner | Unknown; no proven Surface, ANativeWindow, SurfaceTexture, or renderer handoff |
| Two output objects | Unknown |
| Second stream structurally possible | Unknown for end-to-end Honda receiver; generic stream instances alone are insufficient evidence |

The exact evidence needed is the focused decoder call graph and target setup for the callback reached from `mc_ScreenStreamProcessData`, within the indexed binaries `jmcs`, `libcarplay_proxy.so`, or their proven receiver dependency. The existing report excerpts do not expose that edge. The separate two-decoder hardware probe is not evidence for the active CarPlay path.
