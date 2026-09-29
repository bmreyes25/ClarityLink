# ClarityLink Display B architecture decision

## Candidate flow

```text
iPhone main stream (likely type 110) -> unchanged Honda receiver -> center display
iPhone alternate stream (prior art type 111) -> ClarityLink listener -> H.264 decoder -> ExternalDisplay View -> cluster Navigation region
```

Apple documents the multiple-stream model. xcertplay and Harman provide independent implementation evidence for 110/111 and a receiver-owned Type-111 path. This supports architectural plausibility, not Honda interoperability.

## Honda negotiation boundary

Likely minimum interposer, subject to ABI/source confirmation:

| Hook | Purpose | Input/output | Preserve |
|---|---|---|---|
| `AirPlayReceiverSessionSetup` | call stock implementation; inspect/augment capability response if response includes relevant fields | existing request and response dictionary | all stock fields, errors, and primary session behavior |
| `AirPlayReceiverSessionScreen_Setup` or lower SETUP serializer | detect requested Type 111; provision listener and append only its response entry | request stream list / stock result | Type 110 response and stock security context |
| Start / teardown hooks | start/stop only secondary receiver lifecycle | session identity and teardown reason | original stock calls and ordering |

The Harman implementation uses native hooks around stock functions; it is not evidence the Honda ABI supports those hooks. Honda's `CopyDisplaysInfo` and Setup functions have been identified statically, but the exact dictionary returned at the phone-facing boundary remains unproven. A ClarityLink-owned decoder is practical in principle because existing firmware has MediaCodec/Stagefright and NVIDIA H.264 support; stream-to-decoder throughput and independent coexistence are unverified. Honda's unresolved `mc_dev_attach` is therefore not intrinsically required for a separate Type-111 path.

## Coexistence and risk

Distinct stream IDs and listeners allow the center to remain on Music while the cluster stream shows Maps. Apple explicitly describes parallel streams, but Honda's receiver may have a singleton proxy callback or old plug-in behavior that cannot safely express it. Interposing its negotiation/session code risks primary impact until a reversible acceptance experiment proves otherwise.

Apple Maps has direct official support as the example provider of map and maneuver content. Waze and other third-party nav apps may provide cluster content through their CarPlay integration, but automatic routing on this receiver is unproven. Treat Waze as later validation.

Authentication: prior-art extension appears inside the established AirPlay session; no separate MFi authentication is shown. Whether Honda's existing receiver identity/security and feature revision are accepted by current iOS is UNKNOWN. Honda generation alone cannot establish incompatibility.

## Recommendation

Recommended path: **HYBRID**. Pause ptrace and stop treating the primary registry winner as the Display-B prerequisite. Keep the existing main path untouched; investigate the phone-facing Honda descriptor/SETUP response and interposer ABI offline. Use a ClarityLink-owned Type-111 listener/decoder if that boundary can append an independent port without replacing Honda callbacks. Retain the registry route as a fallback if Honda's protocol layer cannot represent or dispatch a second stream.

**Ready for a structured Display-B descriptor fixture: YES. Ready for wire negotiation implementation: NO.** The first later vehicle experiment should only verify that a phone accepts a second display request/opens the advertised Type-111 port while the center stays usable; do not run it in this milestone. Success signals: a second independent accepted TCP connection associated with Type 111 plus stable center CarPlay. Failure signals: no request/connection, SETUP rejection, or center session disruption. Capture protocol logs and cleanly restore the stock library/config after the test.
