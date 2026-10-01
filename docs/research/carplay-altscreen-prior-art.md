# CarPlay secondary-screen and AltScreen prior art

**Research snapshot:** 2026-09-30
**Purpose:** preserve source-pinned external research and turn it into Honda-specific questions.
**Scope:** the pre-CarPlay-Ultra independent secondary-screen / instrument-cluster architecture.

## Evidence classes

| Class | Meaning |
|---|---|
| `HONDA_CONFIRMED` | Supported by an identified Honda artifact or trace preserved in this repository. |
| `EXTERNAL_PRIOR_ART` | Behavior in an upstream project, Apple documentation, or another receiver; it does not establish Honda behavior. |
| `SYNTHETIC_TEST_VALUE` | Generated or modeled data used only by offline tests and the digital twin. |
| `HYPOTHESIS` | A proposed interpretation or design implication that still needs direct evidence. |
| `UNKNOWN` | Not established by the available evidence. |

Never promote a result from an external receiver to `HONDA_CONFIRMED`. Local Honda source notes linked below remain the authority for Honda-specific claims.

## Apple multi-display CarPlay architecture

Apple's WWDC 2019 CarPlay session describes the iOS 13-era vehicle-system path: earlier CarPlay systems used one H.264 stream; the newer vehicle communication interface can carry multiple independent H.264 streams and let the vehicle choose appropriate content for each display. Apple discusses map and maneuver-card content for an instrument cluster, while the main display continues independently. The session associates these vehicle-system APIs with CarPlay Communication plug-in R15. This verifies that ClarityLink's overall two-display concept is an Apple-supported architecture; it does **not** prove support in Honda MY16ADA, its receiver, or its iPhone negotiation path.

WWDC 2022 and Apple's CarPlay Simulator documentation show an app-development simulator with a cluster display alongside the primary display, including map/turn-card presentation. WWDC 2023 discusses vehicle-system view areas and additional displays. These are Apple platform material, not evidence that this Honda build implements the corresponding receiver behavior. This project does not target CarPlay Ultra.

| Source | Revision/date | Classification | What it establishes | What it does not establish |
|---|---|---|---|---|
| [WWDC 2019: CarPlay](https://developer.apple.com/videos/play/wwdc2019/252/) | Apple session 252, 2019 | `EXTERNAL_PRIOR_ART` | Multiple independent H.264 vehicle-display streams; map/maneuver cluster content; vehicle selection of content; R15-era API context. | Honda receiver support, Honda's response schema, or phone behavior with this unit. |
| [WWDC 2022: Get more mileage out of your app with CarPlay](https://developer.apple.com/videos/play/wwdc2022/10016/) | Apple session 10016, 2022 | `EXTERNAL_PRIOR_ART` | Simulator/app workflow shows primary and instrument-cluster displays together. | Honda wire protocol or MY16ADA capability. |
| [Using the CarPlay Simulator](https://developer.apple.com/documentation/carplay/using-the-carplay-simulator) | Current Apple documentation, accessed 2026-09-30 | `EXTERNAL_PRIOR_ART` | CarPlay app developers can inspect a second cluster-display window in the simulator. | In-car receiver implementation or Honda compatibility. |
| [WWDC 2023: Optimize CarPlay for vehicle systems](https://developer.apple.com/videos/play/wwdc2023/10150/) | Apple session 10150, 2023 | `EXTERNAL_PRIOR_ART` | Vehicle-side display/view-area concepts continue in the documented CarPlay platform. | That Honda exposes those fields or uses a matching protocol generation. |

## xcertplay display-descriptor prior art

Repository: [shilapi/xcertplay](https://github.com/shilapi/xcertplay)
Pinned commit: [`de9647f4bdfb1be356bed4cac0519400473712a6`](https://github.com/shilapi/xcertplay/commit/de9647f4bdfb1be356bed4cac0519400473712a6), authored 2026-09-30 19:58:57 UTC.
Inspected source: [`AirPlayInfoPlist.kt`](https://github.com/shilapi/xcertplay/blob/de9647f4bdfb1be356bed4cac0519400473712a6/shared/src/main/java/com/shilapi/xcertplay/airplay/AirPlayInfoPlist.kt).

The builder emits a main display entry and conditionally emits an additional cluster entry. The source defines main type 110 and alternate type 111 and distinct configured UUID constants. Each generated entry uses its display configuration for dimensions and other display values. It includes a `viewAreas` array and `initialViewArea`; a view-area dictionary can include `safeArea`; `initialURL` is emitted conditionally when configuration supplies one. These are xcertplay implementation details, not universal protocol requirements. In particular, source support for an optional URL does not prove that a given runtime configuration emits it.

| Field | xcertplay main | xcertplay cluster | Honda status | ClarityLink implication |
|---|---|---|---|---|
| `type` | Main constant 110 | Alternate constant 111 | `HONDA_INDIRECT_CANDIDATE`; Honda has `type` in Setup stream dictionaries, not confirmed in its display descriptor | Trace any implicit role property or alternate descriptor source; do not infer from xcertplay. |
| `uuid` | Configured main UUID | Distinct configured alternate UUID | `HONDA_CONFIRMED`; inserted as a numeric CF value, semantics unresolved | Recover source property stability and consumers; no stream-identity relation is shown. |
| `maxFPS` | Per-display config | Per-display config | `CONFIRMED` | Compare actual main descriptor value with any future second descriptor. |
| `widthPixels` | Per-display config | Per-display config | `CONFIRMED` | Existing Honda main dimensions are a baseline, not proof of a second region. |
| `heightPixels` | Per-display config | Per-display config | `CONFIRMED` | Same. |
| `widthPhysical` | Per-display config | Per-display config | `CONFIRMED` | Preserve units and conversion uncertainty in any differential. |
| `heightPhysical` | Per-display config | Per-display config | `CONFIRMED` | Same. |
| `features` | Per-display config | Per-display config | `CONFIRMED`; bit meanings unknown | Record exact encoded value and avoid assigning undocumented bit meanings. |
| `primaryInputDevice` | Emitted from per-display config | Emitted from per-display config | `HONDA_ABSENT_LITERAL` | Search generic input/HID descriptor path; literal absence is not semantic absence. |
| `viewAreas` | One configured view-area entry | One configured view-area entry | `HONDA_ABSENT_LITERAL` | Do not infer support from an array-shaped `displays` property. |
| `initialViewArea` | Emitted as index 0 | Emitted as index 0 | `HONDA_ABSENT_LITERAL` | Determine whether Honda has implicit/numeric view-area selection. |
| `initialURL` | Optional when configuration provides it | Optional when configuration provides it | `HONDA_ABSENT_LITERAL` | Search URL constants/config and generic UI/control paths. |
| `safeArea` | Nested in the view-area entry | Nested in the view-area entry | `HONDA_ABSENT_LITERAL` | Search inset/geometry structures and generic serialization paths. |

Honda statuses are scoped to the recovered `/info` descriptor builder and exact-string checks on the matching jmcs ELF. The detailed evidence and confidence for every field are in the [Step 43A differential](../../research/carplay/honda-info-type111-differential.md). `HONDA_ABSENT_LITERAL` means the named literal was not found in that inspected scope; it does not prove that no indirect or generated implementation exists elsewhere.

## MHI2 AltScreen implementation

Repository: [harman-f/mhi2_altscreen_carplay](https://github.com/harman-f/mhi2_altscreen_carplay)
Pinned commit: [`c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c`](https://github.com/harman-f/mhi2_altscreen_carplay/commit/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c), authored 2026-09-29 11:19:50 UTC.
Inspected files: [README](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/README.md), [`MU1440_GEN2_HOOK_MAP.md`](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/research/MU1440_GEN2_HOOK_MAP.md), [`STREAM111_PROTOCOL.md`](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/research/STREAM111_PROTOCOL.md), [`IOS27_SENDER_LIFECYCLE.md`](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/research/IOS27_SENDER_LIFECYCLE.md), [`SCREENALT_CONTROL_PLANE.md`](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/architecture/SCREENALT_CONTROL_PLANE.md), [`VC_VIEWAREA_STATE.md`](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/research/VC_VIEWAREA_STATE.md), and [`libaltscreen111_gen2.c`](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/src/native/altscreen111-gen2/libaltscreen111_gen2.c).

That project reports a vehicle proof of concept on its MHI2/MU1440 target. Its hook map describes stock SessionSetup running first, preserving the normal response, then handling a separate Type111 path. It clones peer descriptors to retain opaque request fields, owns a separate listener/data port and lifecycle, and uses the existing authenticated session/security seam plus per-stream connection identity for its secondary-screen crypto. Its implementation also distinguishes UI ownership/control from video transport and uses exact-build/prologue checks with fail-closed behavior where needed.

Classification for all details in the preceding paragraph: `EXTERNAL_PRIOR_ART`. They are evidence about the specified MHI2 target and its authors' analysis. Honda's stock code currently skips unsupported Type111 without a response; no Honda Type111 schema, crypto, listener, or successful negotiation is established here. Do not copy MHI2 offsets, ABI assumptions, object layouts, or deployment details into Honda code.

### UI ownership and geometry are separate state

The MHI2 sender-lifecycle research for a specific iOS 27.2 beta build records distinct `suggestUI`, `showUI`, and `stopUI` call paths, `SecondDisplayMode`, and `forceKeyFrame`. The pinned MHI2 control-plane and ViewArea research separately describe requesting/selecting/reporting ViewArea on an existing screen. The exact token `ViewAreaChanged` does not appear in these inspected files, so this report does not claim it as a verified command literal. The inspected sender source lists these instrument-cluster URL strings: `maps:/car/instrumentcluster`, `maps:/car/instrumentcluster/map`, and `maps:/car/instrumentcluster/instructioncard`. These are source-pinned MHI2/iOS-analysis artifacts; they are not Honda-confirmed or Apple public API guarantees.

`HYPOTHESIS` for ClarityLink: model these independently because secondary video transport lifetime, selected UI context/ownership, and cluster ViewArea geometry may change at different times. This remains a design hypothesis until Honda behavior is observed.

## Security and crypto comparison

| System | Evidence-backed statement | Classification |
|---|---|---|
| Honda Type110 | Existing Honda analysis identifies 16-byte receiver-session master material plus a uint64 `streamConnectionID` as inputs to the Type110 screen AES key/IV derivation. Type110 derivation does not currently show stream type as an input. See [Honda screen crypto](../../research/carplay/honda-screen-crypto.md). | `HONDA_CONFIRMED` for the recovered Type110 path. |
| MHI2 Type111 | The pinned MHI2 hook/protocol notes report reuse of its authenticated session security material with a distinct stream connection identity and independent secondary stream state. | `EXTERNAL_PRIOR_ART`, MHI2 only. |
| Honda Type111 | Stock setup skips unsupported Type111; no Honda Type111 KDF, response schema, or security-state behavior is confirmed. | `UNKNOWN`. |

The next Honda crypto question is narrow: can Honda's recovered per-screen derivation primitive safely be used for a second screen state and a distinct streamConnectionID while keeping the Type110 crypto/CTR state independent? The Type110 observation alone does not answer this.

## CPC200 and other receiver prior art

Repository: [lvalen91/CPC200-CCPA_resources](https://github.com/lvalen91/CPC200-CCPA_resources)
Pinned commit: [`e3e5d005552d3fa6f264634b377d30b0794dd1eb`](https://github.com/lvalen91/CPC200-CCPA_resources/commit/e3e5d005552d3fa6f264634b377d30b0794dd1eb), authored 2026-09-28 10:35:10 UTC.
Inspected source: [`video_protocol.md`](https://github.com/lvalen91/CPC200-CCPA_resources/blob/e3e5d005552d3fa6f264634b377d30b0794dd1eb/documentation/02_Protocol_Reference/video_protocol.md) and related protocol notes in the same revision.

The CPC200 materials describe navigation screen geometry (`naviScreenInfo`), a navigation video path, and focus commands that start/stop video in the documented wired adapter flow. This is external evidence for that receiver and transport. It does not show that Honda uses the same protocol or that a display capability advertisement alone causes iOS to open Type111. Whether that advertisement is sufficient is `HYPOTHESIS` / `UNKNOWN` for Honda.

A useful future first negotiation criterion can be smaller than a rendered map: stock center Type110 remains functional and observation shows that the iPhone requests Type111 or opens a second stream endpoint. That criterion is a proposed test design, not proof the phone will do so.

## Honda-specific work this research enables

See the ordered [Honda Type111 research plan](honda-type111-research-plan.md). In brief, compare Honda `/info` first, inspect UI-control command handling, trace the Type110-to-possible-Type111 crypto primitive, revisit only a safe stock-first integration seam, prove synthetic ExternalDisplay rendering, capture an observation-only baseline, and design a minimal live negotiation test only after those gates.

## Sources and limits

Apple sources are official platform documentation. The three GitHub sources are pinned to the exact repository commits above so that the reviewed implementation can be revisited. Each external source demonstrates its own platform/build only. No external source in this document changes the current Honda readiness gates: jmcs integration seam unresolved; Honda Type111 schema/security/display correlation unknown; real ExternalDisplay handoff unproven; live negotiation NOT READY.
