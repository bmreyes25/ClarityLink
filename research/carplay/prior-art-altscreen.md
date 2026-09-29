# CarPlay AltScreen prior art — Step 34 refresh

**Reviewed 2026-09-29. Offline source review; no Honda changes or vehicle test.**

## Source pins

| Project | Pin / status | Relevant source |
|---|---|---|
| harman-f/mhi2_altscreen_carplay ([repository](https://github.com/harman-f/mhi2_altscreen_carplay)) | `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c` | `src/native/altscreen111-gen2/libaltscreen111_gen2.c`, `src/native/altscreen111-gen2/src/alt111_profile.c`, `src/native/altscreen111-gen2/src/alt111_video.c`, deployment and vehicle test records |
| arctus/mib2-carplay-rgi-altscreen ([repository](https://github.com/arctus/mib2-carplay-rgi-altscreen)) | URL was unavailable/incomplete from the supplied repository during clone; no commit/source claims made | Not used as evidence |
| shilapi/xcertplay ([repository](https://github.com/shilapi/xcertplay)) | `3753867f0dd0e5c03490b987fb9df49b8ac96472` | `AirPlayInfoPlist.kt`, `AirPlaySession.kt`, `CarPlayMediaEngine.kt` |
| Apple WWDC19 | [Advances in CarPlay Systems](https://developer.apple.com/videos/play/wwdc2019/252/) | Official Apple session transcript |

## What is supported

Apple documents that iOS 13 added multiple independent H.264 streams for cluster content, including map and maneuver-card streams in parallel, and says the vehicle selects what type of content each instrument-cluster stream displays. The talk says the described new system features require Communication Plug-in R15. This is official architecture evidence, not proof Honda's receiver implements R15.

In xcertplay, `AirPlayInfoPlist.build` constructs a `displays` array with separate main and cluster entries and UUIDs. `STREAM_TYPE_MAIN_SCREEN=110` and `STREAM_TYPE_ALT_SCREEN=111` are source constants, used again by SETUP stream dispatch in `AirPlaySession.handleStreams`. That is direct implementation evidence for this receiver's mapping, not an Apple-published numeric definition. The same source conditionally adds `altScreen` to session `enabledFeatures` when a cluster config exists.

The Harman MHI2 repository contains native Type-111 receiver code and vehicle-test artifacts. `alt111_profile.c` assigns type 111 and an instrument-cluster URL. The generation-2 implementation hooks stock session functions and owns Type-111 state/transport while retaining delegates to stock functions. The implementation is a platform-specific interposer; it demonstrates feasibility on that MHI2 build, not binary/API compatibility with Honda.

## Important limitations

The supplied Audi/VW project URL could not be resolved to a checked-out repository at this review. The Harman repository itself has source for a receiver on its target build; xcertplay is a standalone Android receiver, not a Honda-compatible drop-in. Neither establishes that Honda's old receiver can accept an appended display without changing its singleton proxy callback table or setup serialization.

## Step 34 source inspection: separation, crypto, and descriptors

The MHI2 repository was checked out and inspected at pinned current commit `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c` (HEAD on 2026-09-29), including `src/native/altscreen111-gen2/libaltscreen111_gen2.c`, `docs/research/MU1440_GEN2_HOOK_MAP.md`, `docs/research/STREAM111_PROTOCOL.md`, `docs/research/IOS27_SENDER_LIFECYCLE.md`, and control-plane architecture notes.

Source details:

- It resolves stock `AirPlayReceiverSessionSetSecurityInfo`, `AES_CBCFrame_Init`, and `AirPlay_DeriveAESKeySHA512ForScreen`.
- Its narrow AES-CBC observation path captures stock session AES material only around the known stock security-setter caller range; it does not persist/log live keys.
- For its Type-111 ID, it calls the stock screen derivation with the captured 16-byte session material and `streamConnectionID`, then initializes its Type-111 AES-CTR receiver state.
- It clones the root request before replacing only its `streams` array for stock delegation, filtering Type 111 from the stock clone while preserving other root fields and non-111 entries.
- It clones the requested Type-111 descriptor for the response and changes `dataPort` and `streamID=111`; unknown descriptor fields survive. Existing response stream entries remain.
- It maintains a separate Type-111 listener/session generation. Its source/docs treat `streamConnectionID`/session-generation changes as transport boundaries and UI candidate, show/stop, and ViewArea changes as presentation operations that can occur while the stream remains alive.

This confirms the user's architecture split as MHI2's current approach. It does not make MHI2 response fields Honda schema: Honda Type 110 writes `type=110`; MHI2's Type-111 response writes `streamID=111` on a cloned descriptor. Nor does it prove Type-111 request or crypto behavior on Honda.

## Feature-token version boundary

Apple's WWDC19 CarPlay update says the described iOS 13 display features, including second screens and ViewArea, require Communication Plug-in R15. MHI2/xcertplay document modern feature tokens such as `altScreen` and `viewAreas`; Honda's inspected binary has no matching string literals. This supports a **version-dependent** requirement for the modern token set and R15-era capability behavior. It does not prove whether Type-111 itself existed before those tokens or whether an older iOS/head-unit pair negotiated an auxiliary stream through another capability path. Record `ALTSCREEN_TOKEN_REQUIREMENT=VERSION-DEPENDENT` and `TYPE111_PRE_TOKEN_HISTORY=UNKNOWN`.

## Transport before UI

MHI2's source establishes/starts its separate Type-111 receiver as transport state and handles PlatformControl/SessionControl UI operations separately. Its docs say Type-111 may remain established across provider/UI changes, and `suggestUI` is a candidate-list transaction distinct from `showUI`. Thus `TYPE111_TRANSPORT_BEFORE_UI_SELECTION=YES` for MHI2's implementation model. Honda ordering remains UNKNOWN.

## Conclusion

The AltScreen approach is a credible architecture candidate, and `mc_dev_attach("CarPlay Screen")` is not a conceptual dependency if ClarityLink receives a separate negotiated stream and owns its decoder. The missing display UUID↔`streamConnectionID` mapping is no longer the primary transport blocker: the ID participates in per-screen crypto, while UUID/capability belongs to display/presentation signaling in current evidence. Honda still needs Type-111 schema/security compatibility, accepted socket/framing ownership, and a safe stock delegation design recovered. No live test is ready.
