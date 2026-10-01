# CarPlay display capability and SETUP stream identity prior art

**Purpose:** guide Honda static analysis. These sources are `APPLE_PUBLIC_ARCHITECTURE` or `EXTERNAL_PRIOR_ART`; none establishes Honda behavior. Revisions below are pinned or are an immutable Apple session URL. Reviewed 2026-09-30.

## Apple: multiple displays and streams

[Apple WWDC 2019 session 252, “Advances in CarPlay Systems”](https://developer.apple.com/videos/play/wwdc2019/252/) describes the iOS 13-era vehicle-system architecture. Apple says the vehicle declares display physical size/resolution and the iPhone creates an H.264 stream of that size. It then describes multiple H.264 streams for instrument-cluster content, including parallel map and maneuver-card streams; the vehicle selects the content type shown in each stream. Apple also discusses display view areas and safe areas.

Classification: `APPLE_PUBLIC_ARCHITECTURE`. This confirms the general independent-secondary-stream concept as Apple-supported vehicle architecture. It does **not** establish Honda MY16ADA capability, exact Honda fields, or a particular Type 110/111 mapping.

## carlink_linux: capability and stream layers

Repository: [`lvalen91/carlink_linux`](https://github.com/lvalen91/carlink_linux), pinned `fbbfa59400dac4704f34a5d76e745080ce7d6338` (remote `main` observed at this revision on 2026-09-30). Primary document: [`docs/CARPLAY_CAPABILITIES.md`](https://github.com/lvalen91/carlink_linux/blob/fbbfa59400dac4704f34a5d76e745080ce7d6338/docs/CARPLAY_CAPABILITIES.md).

The document distinguishes the `/info` capability dictionary and its display/HID/features fields from a newer Setup-response FeatureKey token list. It explicitly scopes that token-list mechanism and tokens such as `viewAreas` and `altScreen` to iOS 27 / newer reverse-engineered evidence, contrasting them with its public 2017 SDK baseline. Separately, it identifies `type: 110` as the screen **stream** type and says its display UUID corresponds to the HID touchscreen `displayUUID` in that implementation's model.

Classification: `EXTERNAL_PRIOR_ART`, with mixed source confidence as labeled by that repository (`[SDK]`, `[iOS27]`, `[INFER]`). This is a useful warning to keep display/HID identity, advertised capabilities, and media stream identity as separate questions. Its UUID-to-HID relationship and modern FeatureKey mechanism are not Honda findings and must not be generalized to Honda's older Android receiver.

## MHI2: stock-first Type 111 SETUP handling

Repository: [`harman-f/mhi2_altscreen_carplay`](https://github.com/harman-f/mhi2_altscreen_carplay), pinned `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c`. Inspected files: [`MU1440_GEN2_HOOK_MAP.md`](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/research/MU1440_GEN2_HOOK_MAP.md) and [`libaltscreen111_gen2.c`](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/src/native/altscreen111-gen2/libaltscreen111_gen2.c).

The source describes calling stock Setup with the original request first, preserving the stock response, then selecting a requested type-111 descriptor, cloning that descriptor, and appending project-owned response fields including a data port and its implementation's `streamID`. It states that the main type-110 stream stays stock-owned. The code also demonstrates use of the stock per-screen derivation behavior for its own Type-111 stream. The repository cautions that the hooks and ABI assumptions are specific to the audited MU1440 target.

Classification: `EXTERNAL_PRIOR_ART`. It supports a stock-first integration pattern for that target only. It does not prove Honda's accepted keys, Type-111 response schema, field names, crypto lifecycle, hook safety, or availability of a comparable Honda seam.

### Legacy AES evidence addendum (Step 43O planning)

The pinned [`STREAM111_PROTOCOL.md`](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/research/STREAM111_PROTOCOL.md) makes the older-generation crypto chain explicit: MHI2's Type111 path uses its established session AES material plus the secondary stream's `streamConnectionID` with `AirPlay_DeriveAESKeySHA512ForScreen`, then maintains an AES-CTR context through screen setup, frames, and stop. The pinned [`45clouds/WirelessCarPlay` source](https://github.com/45clouds/WirelessCarPlay/blob/51145ef55f8dd9f1cbadd58353cacb5e0ca215e9/source/Sources/AirPlayReceiverSession.c) independently reads the screen descriptor's `streamConnectionID` and passes it with session AES material into that derivation on its legacy non-PairVerify screen path. This raises the cross-platform legacy per-screen KDF model to strong external prior art. Honda Type111 remains `HONDA_UNKNOWN`; use these only to guide the offline isolation model, not to claim Honda crypto compatibility. Full boundary: [legacy AES Type111 cross-reference](legacy-aes-type111-cross-reference.md).

## CPC200: documented Type-111 ordering

Repository: [`lvalen91/CPC200-CCPA_resources`](https://github.com/lvalen91/CPC200-CCPA_resources), pinned `e3e5d005552d3fa6f264634b377d30b0794dd1eb`. Inspected [`video_protocol.md`](https://github.com/lvalen91/CPC200-CCPA_resources/blob/e3e5d005552d3fa6f264634b377d30b0794dd1eb/documentation/02_Protocol_Reference/video_protocol.md), especially its “TTY Log Correlation: Video Stream Setup” section.

That community protocol document presents a logged sequence in which setup type 111 appears before the navigation screen dimensions/configuration and first navigation H.264 frame; type 110 setup and its first frame follow in the quoted sequence. The document attributes the sequence to its adapter TTY log/capture analysis. This gives a useful ordering example for that receiver, but it is not an Apple normative requirement or a Honda transaction.

Classification: `EXTERNAL_PRIOR_ART`. It suggests a bounded first negotiation observation target: normal center stream remains functional while a second stream is requested/opened. It does not prove a Honda phone will request type 111, nor that `/info` advertisement alone triggers it.

## Search-model consequence

### Step 43E seam boundary

Honda's exact Setup out object reaches a synchronous pre-serialization caller window, with mutable CF response/array construction already present in stock. This is `HONDA_CONFIRMED` for dataflow and stock construction, but only `HONDA_INDIRECT_CANDIDATE` for caller-side mutation. The MHI2 stock-first append remains `EXTERNAL_PRIOR_ART`; it does not prove Honda hook safety, CF ownership semantics for new entries, schema, or cleanup. See [the full Step 43E lifetime and rollback audit](honda-post-setup-response-seam.md).

The sources support asking two separate Honda questions in order:

1. What display/input/capability identity is advertised through `/info`?
2. What stream entries does SETUP request, and how does Honda parse and answer each one?

Only after tracing the Honda stream path should researchers compare any explicit UUID, display index, Screen object, or HID identity. A direct `display uuid → streamConnectionID` join is not a required assumption. The working hypothesis is that capability/display identity and per-stream transport/security identity may be separate layers; for Honda this remains `HYPOTHESIS` until a direct dataflow or phone-side observation establishes more.

The smallest future live negotiation proof, after all safety and implementation gates are separately reviewed, could be limited to observing a Type-111 request/second listener while stock Type 110 remains normal. It need not claim successful video decode or renderer handoff. This is a test-planning inference from external prior art, not a readiness decision.
