# CarPlay AltScreen prior art

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

## Conclusion

The AltScreen approach is a credible architecture candidate, and `mc_dev_attach("CarPlay Screen")` is not a conceptual dependency if ClarityLink receives a separate negotiated stream and owns its decoder. It is not yet proven bypassable on Honda: we have not found a supported hook that can augment the phone-facing advertisement and SETUP response while leaving Honda's primary callbacks intact. The remaining critical gate is Honda's actual serialized capability/session boundary and a compatible interposition mechanism.
