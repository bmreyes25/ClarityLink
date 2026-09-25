# CarPlay on the Clarity instrument cluster: execution plan

**Updated:** 2026-09-24  
**Target:** A stationary, active Apple Maps route remains visible as an independent iPhone-rendered cluster map or maneuver card while the center CarPlay display shows Music, and spoken guidance still uses the factory speakers. Waze route guidance is a separate compatibility test. The existing Honda Hack mirror is the fallback baseline, not evidence of native dual CarPlay video.

This plan is executable in stages. A Mac simulator passing proves the proposed interfaces and cleanup only. A real iPhone stream on the cluster requires a live receiver observation and an on-car test. The original verified backup remains immutable; experiments use working copies under `clarity-analysis`.

## Evidence available now

| Question | Current evidence | Status |
|---|---|---|
| Is there an Android display output to the cluster? | SurfaceFlinger shows an 800×480 HDMI output; Honda Hack casting reached the physical cluster. | Proven destination |
| Does the Honda receiver advertise a second CarPlay display? | `jmcs` car init registers one `gMainScreen`; display info reads the main screen. Ordinary reconnect logs name one screen. | No second display observed; full protocol reply missing |
| Can Honda's screen proxy dispatch two streams? | `libcarplay_proxy.so` registers one global callback table and rejects a second registration. | Current proxy is a blocker |
| Does the iPhone send usable Route Guidance metadata here? | Logs show `turns controller` ownership, not maneuver/road/distance payloads. | Unknown |
| Can two H.264 decoders run on this Tegra build? | September 25 probe measured two concurrent NVIDIA instances, each outputting 28/30 800×480 frames in 1973 ms with EOS. | Actual-frame concurrency observed for this fixture; strict all-30 gate and CarPlay coexistence open |
| Where is the safe physical cluster navigation region? | Cast-on photos show a central rectangle below speed and above Menu/trip; sides crowd power/charge scales. | Approximate placement observed; calibrated safe bounds unknown |
| Can a failed receiver patch be recovered? | Backups have verified hashes; an independent boot/reflash recovery path is not established. | Not ready for receiver patch |

Apple's [WWDC19 CarPlay systems session](https://developer.apple.com/videos/play/wwdc2019/252/) describes separate H.264 map and maneuver streams and says these iOS 13 features required R15 CarPlay Communication plug-in APIs. The same session distinguishes iAP2 Route Guidance metadata, which the vehicle must draw itself. These are protocol possibilities, not Honda capabilities.

## Stage 1 — Complete the Mac bench (complete for current evidence)

1. Replay the saved paired center and HDMI captures and Honda Hack's 584×215 layout. **Done.**
2. Feed the versioned receiver-to-renderer contract into the simulator, including setup, frames, stop, and disconnect. The center app changes to Music while a simulated cluster frame remains active. **Done.** The contract adapter is offline and does not decode video.
3. Add a separate semantic Route Guidance fixture path for turn, road, distance, and expiry. Label these fixtures synthetic until actual iAP2 fields are captured. **Done.** The metadata fixture is explicitly hypothetical.
4. Verify no stale frame or turn survives disconnect, stream stop, timeout, or center-OCR source loss. Do not tie audio control to display replay. **Done in unit replay.** A receiver error event and real-time scheduling are not implemented; the current contract fixture exercises stop and disconnect.

**Exit:** repeatable tests and a browser replay that clearly separates saved Honda pixels, synthetic metadata, and hypothetical second-stream frames. This stage cannot prove receiver compatibility.

## Stage 2 — Focused parked-car evidence session

Run the [car session checklist](CAR_SESSION_CHECKLIST.md) only when the car is parked and the Mac can reach Wi-Fi ADB. The September 18 session already captured a reconnect, Maps→Music, paired center/HDMI screenshots, and ordinary receiver logs. The next session should photograph the *physical* cluster Navigation page and collect the accessible `jmcs` process/socket inventory while guidance runs behind center Music. Do not repeat the reconnect unless a new, offline-validated method can observe additional negotiation data. Keep this stage read-only.

**Exit:** safe-area geometry and any new receiver libraries or endpoints that inform an actual iAP2 diagnostic. The existing log already shows one named screen but does not print the full capability reply. A missing log entry is only a bounded negative; ordinary logcat is not a complete iAP2 protocol trace.

## Stage 3 — Choose the implementation route from evidence

**Route A: semantic guidance.** If actual iAP2 Route Guidance fields are observed, decode them into a display-only Honda Hack navigation view with explicit expiry. Verify it keeps working while center Music is visible. Do not call factory `ITBTInformation` setters that can send B-CAN. If metadata is absent but center-screen OCR is used, clear guidance when Maps leaves the center; that cannot meet the independent-display target.

**Route B: genuine cluster video.** Require evidence that the iPhone can be asked for a second map/card display on this receiver or a compatible receiver replacement. On a Mac harness, implement distinct display identity, setup, H.264 channel, per-stream callback dispatch, decoder, navigation-only surface, and teardown. The existing singleton proxy cannot be extended by changing one XML flag. A positive decoder-allocation probe would be necessary but still insufficient for sustained video.

**Decision:** Route A can deliver turn text/arrows without a second H.264 stream if metadata exists. Route B is required for the Volvo-style independent Apple Maps image. Both must preserve the center CarPlay and spoken audio.

## Stage 4 — Prove recovery and hardware limits before receiver changes

Calibrate the safe navigation rectangle from the physical photos. Establish a boot-independent restore path for the exact original files; the partial eMMC backup alone is not a tested recovery method. The approved September 25 actual-frame decoder diagnostic is complete and the APK was removed. It showed concurrent output under one fixture, while its strict all-30-frame gate remained incomplete. A later background-safe test would be needed for coexistence with active CarPlay. See the [new implementation gates](NATIVE_CLUSTER_IMPLEMENTATION_GATES.md).

**Exit:** a bounded rendering region, a tested recovery procedure, and a hardware result sufficient to size a candidate stream. If recovery is not proven, stop before factory receiver replacement.

## Stage 5 — Candidate integration and acceptance test

Prepare a byte-level diff against the working backup, a manifest of changed files, and an exact rollback. Bench-test two display lifecycles and audio isolation. A later parked on-car test must show: (1) Maps route on cluster with center Music, (2) voice directions heard, (3) no covering of speed/warnings, (4) route end and disconnect clear the map, and (5) original center CarPlay remains usable. Record Apple Maps and Waze separately. Do not infer CarPlay Ultra from ordinary CarPlay multi-display support.

**Current completion state:** Stage 1 is repeatable on the Mac. Stages 2–5 need new observations, and Stage 5 may require a newer/replaceable CarPlay receiver if this 2018 stack cannot negotiate a second stream. No native map patch is ready to install.
