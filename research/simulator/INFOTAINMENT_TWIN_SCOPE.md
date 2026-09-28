# Evidence-backed Clarity infotainment twin

**Scope:** offline models and captured display replay of the head unit, receiver seams, Android display-1 navigation area, Honda Hack casting, and audio/navigation state. The actual ARM receiver is not executed. Vehicle speed, gear, SOC, and range are **synthetic inputs** for display testing. This is not a full vehicle emulator or proof of native CarPlay support. The physical car remains the final compatibility test.

## Step 2 bounded checkpoint — September 28 UTC

**Complete and independently accepted for the assigned offline/model scope.** See [independent supervising Codex review](../verification/STEP_02_REVIEW.md). This is acceptance of a fixture-backed infotainment oracle with declared uncertainty; it does not accept a dependent vehicle, protocol, decoder, recovery or native-stream gate.

| Layer | Completed bounded implementation | Retained limits |
| --- | --- | --- |
| 1 Firmware/storage | Existing GPT fixture retained; [firmware catalog](firmware-catalog.json) hashes 14 allowlisted receiver/config/APK/ODEX members and eight activity/audio/display/services snapshot sets. [Service evidence](service-evidence.json) identifies four current APK service owners, matched manifest decoder inputs, observed binding edges and focus snapshots. Generators reproduce byte-identically. | Live archives non-atomic; not exhaustive filesystem extraction or service reverse engineering. No raw firmware or runtime bodies in Git. |
| 2 Android/application | [Pure mocked Binder, Navigation, ExternalDisplay, display and Audio interfaces](service-model.js), used by all three replay modes. Current activity snapshots show CarPlay service clients bound to Navigation and ExternalDisplay. Runtime observation attachment checks all shared source hashes. | No Android/Binder execution. Binding is not route metadata. AvApService focus on stream 12 persists even under disconnected labels; snapshot focus is not per-event CarPlay audio. Factory TBT/bus methods absent. |
| 3 Receiver ABI model | Explicit JS model of six 32-bit callback offsets in 24 bytes and singleton duplicate result `0x16`, matched to [static audit](../native/receiver-multidisplay-audit.md). Mock USB/MFi readiness, display/audio and replay of eight hashed runtime states; observed snapshot facts, inferred connection/app, synthetic callbacks/clock and unknown payload/continuity remain separate. | **Actual ARM receiver execution and a native binary harness remain unavailable.** The assigned scope permits this labeled model. No proprietary packets, authentication, decoding, second native callback or native CarPlay capability is implied. |
| 4 Dual display | Six hash-verified consecutive center/HDMI pairs; observed mirror and head-unit Waze route/background/end, visibly synthetic map/metadata. 800×480 outputs; Maps→Music, stop/end/disconnect/reconnect and stale setup/frame/guidance cleanup. Local browser compares the three modes and clips a synthetic proposed viewport. [Photo calibration](photo-calibration.json) locates inferred Maps/Music cast footprints and verifies all five source photo copies. | Photo poses differ; Maps right corners extrapolate. Physical Navigation safe rectangle/panel pixels and side clearances remain **unknown** (`rectangle: null`, `calibrated: false`). Source content region `[0,24,584,191]` is inferred from layout/padding; browser use is explicitly synthetic, not a physical safety guarantee. Replay time illustrative, not measured latency. |

Full reproduction uses the ignored OpenCV environment and local Chrome, as specified in [README](README.md). Independent results: **31 Python tests with zero skips/failures, 11 named model tests, six legacy JS assertion suites, three browser mode checks**; zero page errors/remote HTTP requests. Firmware/service/photo generators reproduce identical fixtures; all 14 JavaScript files pass syntax checks.

The reviewer found and verified fixes for compositor ownership, route-bearing captured pixel cleanup, pre-frame stream timeouts and runtime observation provenance. Saved references are separated from the modeled active HDMI owner. An active proposed map owns the model output across center Music; an observed mirror follows Music. Route-bearing reference pixels retire under declared model policies, while an explicit observed ended-compass frame remains. Audio continuity is a modeled invariant, not a measured proposed-stream result. Browser unplug cleanup is separately injected model behavior, not an added observed fixture. TTL advances on replay events/ticks. Full Tegra/QEMU boot is not a prerequisite.

## Current component model

```mermaid
flowchart LR
  phone[iPhone / wired CarPlay] --> receiver[jmcs receiver]
  receiver --> proxy[libcarplay_proxy.so]
  proxy --> service[CarPlay Java services]
  service --> center[Android center display / audio]
  center --> hack[Honda Hack screenshot/casting path]
  hack --> hdmi[Android display 1 / HDMI cluster region]
  factory[Honda Navigation APIs] --> hdmi
  receiver -. separate negotiated map stream unproven .-> candidate[Candidate cluster decoder/surface]
  candidate -. proposed .-> hdmi
```

The solid lines summarize inspected firmware and prior observations; they do not imply that CarPlay maneuver metadata flows into Honda Navigation. The dashed lines are the proposed native extension. Honda's factory navigation setters can emit B-CAN messages and are **excluded** as test interfaces.

## Evidence inventory and missing observations

| Boundary | Established evidence | Missing for a faithful twin |
| --- | --- | --- |
| iPhone to receiver | `jmcs` symbols, one configured main CarPlay screen, live iAP2/AirPlay threads and two IPv6 TCP flows | Raw iAP2 Identification fields; distinct CarPlay display identities and session setup. Built-in usbmon is absent on this kernel. |
| Video decoding | Approved API-17 probe produced 28/30 actual 800×480 frames from each of two simultaneous NVIDIA instances in 1973 ms | Explain two missing frames; sustained performance across profiles and coexistence with factory CarPlay |
| Center display | Saved 800×480 Maps/Music frames and SurfaceFlinger dump | Layer ownership and transitions with route active during a new controlled capture |
| Cluster output | Separate 800×480 Android HDMI display; Honda Hack 584×215 meter layout and 400×240 screenshot casting path; off/on SurfaceFlinger snapshots and physical Maps/Music photos | Calibrated safe boundary, side clearance near power/charge scales, and latency measurements |
| Route semantics | Honda native navigation types; CarPlay resource ownership strings; saved Apple Maps screenshot OCR | Decoded CarPlay route payloads, if present; maneuver/distance lifetimes; Waze-specific behavior |
| Audio | User verified spoken Apple Maps directions with casting on and after rollback; Android audio focus snapshot stayed on `AvApService` across casting states | Per-event audio trace and later voice validation with a proposed receiver/renderer change |
| Recovery | Simulator clears route/display on disconnect | On-car route end, unplug, receiver restart, and cast-off transitions, each observed without a write |

## Further fidelity work outside the completed offline scope

1. **Session timeline:** connection, receiver readiness, CarPlay primary display, route start/update/end, center app switch, cluster view ownership, casting enable/disable, and disconnect. Every event records observed vs synthetic provenance.
2. **Display compositor:** independently replay saved center and HDMI frames; place candidate map or guidance only inside the measured physical navigation safe area. Make clipping and occlusion visible. Never simulate speedometer/warning replacement.
3. **Audio observer:** record whether voice and music were heard and read-only Android route/focus state. Do not synthesize a claim that a candidate stream preserves voice; a later parked test must verify it.
4. **Receiver contract adapters:** accept parsed logcat, USB trace summaries, and (only if validated) decoded iAP2/CarPlay session events. Unknown or encrypted payloads remain opaque records, never fabricated fields.
5. **Deterministic replay:** events with monotonic timestamps, fixture hashes, source labels, and failure injection for dropped frames, stale guidance, disconnect, route end, center app switch, cast switch, and decoder failure.

The existing [`index.html`](index.html), [`digital-twin.js`](digital-twin.js), and JSONL samples now replay the measured September 25 casting transitions alongside hypothetical independent-stream/metadata behavior. They do not decode CarPlay traffic or emulate the Honda receiver. The [live topology](../native/live-session-topology-20260925.md) identifies additional event adapters the twin could model without pretending to reproduce proprietary transport bytes.

## Acceptance gates for the offline workaround

- Replaying an observed two-display timeline reproduces center and cluster frames with documented timing/provenance.
- Candidate map remains on the cluster when center switches Maps → Music, or a metadata card explicitly reports that its source is unavailable.
- Guidance and candidate frames clear on route end, CarPlay disconnect, stale update, or failed decoder, without covering the native non-navigation area.
- Apple Maps and Waze use separate fixtures and capability verdicts.
- Audio is treated as an invariant checked in later car validation, not inferred from the Mac replay.

After the parked survey and any conditional protocol/decoder measurements, choose the implementation branch from evidence: native metadata, independent map stream, or an interim display-only workaround. The final on-car change must have a reversible package/patch, exact affected components, recovery steps, and a separate review before use.
