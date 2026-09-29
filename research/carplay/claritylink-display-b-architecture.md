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

## Step 26 — Honda Setup ABI recovery (offline, 2026-09-29)

The exact local `jmcs` ELF disassembly adds a concrete Honda structure: `AirPlayReceiverSessionSetup` builds a mutable response dictionary, creates a per-stream dictionary with `type=110` and dynamic `dataPort`, then `_AddResponseStream` appends it to a `streams` CFArray. This is Honda-confirmed response construction and means multiple stream response entries are structurally representable. It does **not** prove a multiple-display descriptor array, Type-111 acceptance, or a phone-facing serializer edge. `AirPlayReceiverSessionScreen_CopyDisplaysInfo` separately returns one main-screen property dictionary after one `ScreenCopyMain` call.

The response dictionary is published through an output pointer. The separate completion callback receives status/context, not the response dictionary. The output-pointer caller, serializer, network write, formal C signature, and ownership contract remain unknown. `_requestSendPlistResponse` (`0x289f60`) serializes a generic plist to CFData for an HTTP response but has no proven call edge from CarPlay Setup. The response-augmentation shape is plausible but not established as safe. No hook or live negotiation is implemented.

## Step 27 — Setup response send path (offline, 2026-09-29)

Step 27 closes the central dataflow gap. `_connectionHandleMessage` (`0x28a30c`, `AirTunesServer.c`) calls `AirPlayReceiverSessionSetup` at `0x28af72` with `(session, requestDictionary, &response)` in `(r0, r1, r2)`. On success, the same response pointer is passed to `_requestSendPlistResponse` (`0x289f60`) at `0x28afba`. That helper creates a binary plist (`CFPropertyListCreateData`, format `0xc8`), installs its bytes/length as the body of an HTTP 200 response (`application/x-apple-binary-plist`), and the dispatcher calls `HTTPConnectionSendResponse` (`0x29dbe4`). It then releases the response object after synchronous serialization. The stock `streams` array and type-110/dataPort entry are therefore confirmed to reach the phone-facing response serialization/send path.

The immediate post-Setup/pre-serializer caller window is now the smallest structural augmentation candidate, and caller ownership is evidenced by the cleanup. That does not prove live-hook safety or iPhone support for Type 111. Display capability signaling remains unresolved: `CopyDisplaysInfo` still returns one main-screen dictionary, and no relation to this Setup response is established. Do not implement negotiation yet. See `step-reports/27-honda-setup-send-path.md` and `research/carplay/honda-setup-response.md`.

See `honda-setup-response.md`, `honda-display-descriptor.md`, `honda-dataport-field.md`, `honda-response-serializer.md`, `honda-hook-abi.md`, and `display-b-fixture.md`.

## Step 28 capability-gating update (2026-09-29)

`CopyDisplaysInfo` now has recovered literal keys: `edid`, `features`, `maxFPS`, `widthPhysical`, `heightPhysical`, `widthPixels`, `heightPixels`, and `uuid`. It builds one mutable dictionary from one `ScreenCopyMain()` result; the `uuid` property is inserted through the numeric setter in this function. A generated-disassembly search found no direct call site. Its parent, serializer, and phone-facing phase remain unknown. No second display descriptor array or AltScreen-like field is evidenced.

The Type-110 SETUP response remains confirmed phone-facing (Step 27), but incoming type parsing, Type-111 acceptance, display-to-stream correlation, and feature bit semantics are unknown. The current evidence does not support negotiation implementation or a live test. See `honda-display-capabilities.md`, `honda-copy-displays-info.md`, `honda-identification-receiver-info.md`, `honda-alt-screen-gating.md`, `honda-stream-type-dispatch.md`, and `display-stream-correlation.md`.
