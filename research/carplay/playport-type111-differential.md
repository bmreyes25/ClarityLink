# PlayPort Type111 differential — Step 43N

## Pin and evidence boundary

**EXTERNAL_PRIOR_ART:** [`youcci/playport`](https://github.com/youcci/playport/tree/9a0882dd0ffe48e467b59d58b12d81391df55ade), exact commit `9a0882dd0ffe48e467b59d58b12d81391df55ade`, “Refresh README screenshots with live CarPlay” (2026-10-01 14:30:27 +02:00). Inspected protocol session/info/media code, server configuration/bridge/hub, and web wire/UI code from a filtered temporary checkout. Nothing was copied into ClarityLink.

Pinned entry points: [`AirPlayInfoPlist.kt`](https://github.com/youcci/playport/blob/9a0882dd0ffe48e467b59d58b12d81391df55ade/protocol/src/main/java/com/shilapi/xcertplay/airplay/AirPlayInfoPlist.kt), [`AirPlaySession.kt`](https://github.com/youcci/playport/blob/9a0882dd0ffe48e467b59d58b12d81391df55ade/protocol/src/main/java/com/shilapi/xcertplay/airplay/AirPlaySession.kt), [`CarPlayMediaEngine.kt`](https://github.com/youcci/playport/blob/9a0882dd0ffe48e467b59d58b12d81391df55ade/protocol/src/main/java/com/shilapi/xcertplay/airplay/CarPlayMediaEngine.kt), [`CarPlayServer.kt`](https://github.com/youcci/playport/blob/9a0882dd0ffe48e467b59d58b12d81391df55ade/server/src/main/kotlin/com/playport/server/CarPlayServer.kt), [`WebBridge.kt`](https://github.com/youcci/playport/blob/9a0882dd0ffe48e467b59d58b12d81391df55ade/server/src/main/kotlin/com/playport/server/WebBridge.kt), [`WebHub.kt`](https://github.com/youcci/playport/blob/9a0882dd0ffe48e467b59d58b12d81391df55ade/server/src/main/kotlin/com/playport/server/WebHub.kt), and [`web/src/protocol.ts`](https://github.com/youcci/playport/blob/9a0882dd0ffe48e467b59d58b12d81391df55ade/web/src/protocol.ts).

## What the pinned code establishes

| Question | Finding |
|---|---|
| Type111 protocol constant | `STREAM_TYPE_ALT_SCREEN = 111`, alongside main screen 110. |
| Second display configuration | `AirPlayConfig` has optional `cluster`; `AirPlayInfoPlist` emits the second display when non-null. |
| SETUP dispatch | 110 and 111 are both routed to `media.onScreen(session, type, stream)` and accepted responses contain the matching `type` and returned `dataPort`. |
| Per-stream isolation | `CarPlayMediaEngine` uses a key of session plus type; recovery for 111 requests the AltScreen UUID keyframe. |
| Browser wire identity | `Wire` includes streamType in video config/frame packets; `WebBridge` forwards type and `WebHub` stores codecs/config by type. |
| Current server configuration | `CarPlayServer.airPlayConfig` sets `main` but does not populate optional `cluster`, so normal startup advertises main only. |
| Current web renderer | Wire data retains type, but `web/src/main.ts` currently routes video messages to one `VideoPlayer` and one canvas. It is not already a dual-canvas oracle. |

Thus PlayPort has useful Type111 protocol/media plumbing, but a lab branch still needs an opt-in cluster profile and frontend stream-specific canvases/decoders. The current Type111 capability is not enabled by default.

## ClarityLink use

Treat this as an out-of-car iOS behavior oracle only. Its receiver stack is derived from DiPlay/xcertplay and does not establish Honda compatibility. It can help record the current phone's `/info altScreenURLs`, SETUP features/stream dictionaries, Type111 endpoint, media arrival, and control commands. Any observed values must retain the phone/iOS/build and PlayPort configuration context.
