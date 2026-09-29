# Stream type 111 evidence

| Type | Name | Source and evidence | Confidence |
|---|---|---|---|
| 110 | Main screen | xcertplay pinned source defines `STREAM_TYPE_MAIN_SCREEN=110` in `AirPlayInfoPlist.kt`, builds main display entry with that type, and accepts it in `AirPlaySession.handleStreams` / `CarPlayMediaEngine` | High for this implementation; not Apple-published numeric assignment |
| 111 | Alternate screen | Same source defines `STREAM_TYPE_ALT_SCREEN=111`, builds the cluster entry with that type, and dispatches it to `media.onScreen`; Harman `alt111_profile.c` configures type 111 and its native receiver handles the Type-111 path | High that independent implementations use it for AltScreen; reverse-engineered ecosystem detail |

Apple WWDC19 confirms multiple simultaneous cluster H.264 streams without publishing stream numbers. Accordingly, 110/111 is **open-source implementation / reverse-engineered protocol evidence**, not an Apple public guarantee. Honda's present Type-110 association is an inference only; its serialized stream type has not been recovered.

Sources: xcertplay commit `3753867f0dd0e5c03490b987fb9df49b8ac96472`, `shared/src/main/java/com/shilapi/xcertplay/airplay/AirPlayInfoPlist.kt`, `AirPlaySession.kt`, `CarPlayMediaEngine.kt`; Harman commit `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c`, `src/native/altscreen111-gen2/src/alt111_profile.c`, `libaltscreen111_gen2.c`.
