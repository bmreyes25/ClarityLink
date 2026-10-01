# xcertplay Type111 reference — pinned external prior art

## Pin and limits

Inspected [`shilapi/xcertplay`](https://github.com/shilapi/xcertplay/tree/17c92439413638dfd1d7f91d7e1c2e7358398762) at exact commit `17c92439413638dfd1d7f91d7e1c2e7358398762` (`fix(audio): add missing MainMediaAudioBuffer sources`). Relevant files inspected: `AirPlayConfig.kt`, `AirPlayInfoPlist.kt`, `AirPlaySession.kt`, `CarPlayMediaEngine.kt`, `ScreenStream.kt`, `AirPlayInfoPlistTest.kt`, and `CarPlayMediaEngineTest.kt`. The checkout was temporary. No source is copied or vendored; xcertplay is GPL-licensed and is used here only as behavioral reference. All claims in this report are `EXTERNAL_PRIOR_ART`, not Honda facts.

## Source-confirmed behavior at this pin

| Area | Observation | Boundary |
|---|---|---|
| Configuration | `AirPlayConfig.cluster` is optional `AirPlayDisplayConfig?`; display configuration carries pixel size, optional physical size, FPS, primary input device, view/safe-area insets, and optional `initialUrl`. | This is xcertplay's configuration API. |
| `/info` displays | Builder always emits configured main as type 110 and, when `cluster != null`, emits type 111 with a distinct fixed UUID. Each descriptor includes UUID, type, maxFPS, pixel/physical dimensions, features, primaryInputDevice, one `viewAreas` entry and `initialViewArea=0`; `initialURL` is conditional. `safeArea` is nested in each view area. | The specific numeric UUIDs, dimensions and flags are implementation configuration, not portable Honda values. |
| SETUP feature response | Adds `viewAreas`; adds `altScreen` only when a cluster is configured. | xcertplay's emitted `enabledFeatures` behavior; not proof either token is required by current iOS or accepted by Honda. |
| Incoming screen streams | SETUP dispatch accepts 110 and 111, calls `media.onScreen(session, type, stream)`, and returns `{type, dataPort}` for an accepted screen. | Separate control-plane branch; the stream map itself retains request fields. |
| Stream identity | `CarPlayMediaEngine.StreamKey` is `(session, type)`, so screen state is distinct by session and screen type. | The code does not collapse 110 and 111 into one screen stream. |
| Recovery/control | The pinned engine installs a `forceKeyFrame` callback only for Type110; its command has empty params and is documented as targeting the primary display. No UUID-scoped Type111 keyframe, `showUI`, or `stopUI` implementation was found in the inspected source. | UUID-scoped alternate controls are not an xcertplay-at-this-pin finding; DiPlay adds related behavior. |
| Screen transport | `ScreenStream` describes a 128-byte header, opcode 0 VideoFrame and opcode 1 VideoConfig, length-prefixed H.264/H.265 NAL data, clear codec configuration, and ChaCha20-Poly1305 sealed frame bodies. The key is the DataStream output key; each frame uses a counter nonce. The engine derives the DataStream key from the session shared secret with a salt containing `streamConnectionID`. | Modern xcertplay security implementation; do not port to Honda. |

The pinned tests cover display/view-area plist construction and screen engine behavior, but are upstream unit tests, not physical iPhone or vehicle validation. This source does not itself establish an `altScreenURLs` reader or a current-phone request trace.

## Differential conclusion

xcertplay supports the external protocol model of optional display 111, separate listener/dataPort, and per-session/per-type media state. DiPlay's pinned source adds cluster URL selection and UUID-scoped alternate-screen controls, plus maintainer-reported physical validation; those additions must not be attributed to xcertplay. PlayPort carries similar protocol plumbing but currently configures only its main display by default and has one browser canvas. The source lineages overlap, so agreement among the three codebases is useful multi-implementation prior art, not three statistically independent protocol specifications.

Honda Type110's 128-byte framing and legacy AES-CTR path are separately `HONDA_CONFIRMED`. Honda Type111 remains `HONDA_UNKNOWN`, especially its key derivation, cipher, nonce/counter, and whether Type111 can use the same per-stream security model.

## Pinned source links

- [`AirPlayConfig.kt`](https://github.com/shilapi/xcertplay/blob/17c92439413638dfd1d7f91d7e1c2e7358398762/shared/src/main/java/com/shilapi/xcertplay/airplay/AirPlayConfig.kt)
- [`AirPlayInfoPlist.kt`](https://github.com/shilapi/xcertplay/blob/17c92439413638dfd1d7f91d7e1c2e7358398762/shared/src/main/java/com/shilapi/xcertplay/airplay/AirPlayInfoPlist.kt)
- [`AirPlaySession.kt`](https://github.com/shilapi/xcertplay/blob/17c92439413638dfd1d7f91d7e1c2e7358398762/shared/src/main/java/com/shilapi/xcertplay/airplay/AirPlaySession.kt)
- [`CarPlayMediaEngine.kt`](https://github.com/shilapi/xcertplay/blob/17c92439413638dfd1d7f91d7e1c2e7358398762/shared/src/main/java/com/shilapi/xcertplay/airplay/CarPlayMediaEngine.kt)
- [`ScreenStream.kt`](https://github.com/shilapi/xcertplay/blob/17c92439413638dfd1d7f91d7e1c2e7358398762/shared/src/main/java/com/shilapi/xcertplay/airplay/ScreenStream.kt)
- [`AirPlayInfoPlistTest.kt`](https://github.com/shilapi/xcertplay/blob/17c92439413638dfd1d7f91d7e1c2e7358398762/shared/src/test/java/com/shilapi/xcertplay/airplay/AirPlayInfoPlistTest.kt)
- [`CarPlayMediaEngineTest.kt`](https://github.com/shilapi/xcertplay/blob/17c92439413638dfd1d7f91d7e1c2e7358398762/shared/src/test/java/com/shilapi/xcertplay/airplay/CarPlayMediaEngineTest.kt)
