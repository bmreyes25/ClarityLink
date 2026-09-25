# Clarity cluster integration construction plan

**Date:** 2026-09-24  
**Mode:** direct local workspace; `clarity-analysis` is not a Git repository.  
**Objective:** show useful Apple Maps and Waze guidance in the factory cluster with normal CarPlay voice, then investigate an independent iPhone-rendered cluster map. All work is reversible and limited to the navigation display area.

## Evidence and invariants

- Verified backup: `/Users/bmreyes24/ClarityLab/backups/CLARITY_BACKUP_20260918_0225_ORIGINAL` remains read-only. Work from copies inside `clarity-analysis`.
- Honda Hack already mirrored the CarPlay center screen into the cluster while voice guidance worked. The September 18 capture shows center Music with an active Maps route and a compass-only cluster HDMI output.
- `jmcs` registers one CarPlay main screen; `libcarplay_proxy.so` holds one screen callback table. Native Apple Maps cluster video therefore needs more than a flag or XML change.
- The factory navigation setters can send B-CAN. Keep experiments on Honda Hack's visual layer; do not call those setters or change vehicle buses or critical indications.
- Apple's [WWDC19 session](https://developer.apple.com/videos/play/wwdc2019/252/) describes separate H.264 map and maneuver streams and R15 communication plug-in APIs. It does not establish their presence on MY16ADA.

## Dependency graph

```text
1 captured two-display twin
  ├── 2 display-only guidance bridge → optional parked visual test
  └── 3 read-only receiver/metadata evidence → 4 optional decoder diagnostic
                                            → 5 native multi-display decision
```

## Step 1 — Captured two-display twin (implemented)

**Context:** The existing simulator replayed abstract states. Three copied PNGs from the read-only session and working copies of `j_config.xml` and Honda Hack `meter_civic.xml` now supply real pixels and dimensions. The two cluster screenshots have the same SHA-256.

**Work:** Replay named captured center and cluster frames; show a separate 584×215 proposed Honda Hack guidance layer; preserve source and simulation labels; clear state on disconnect. Keep image assets local. Regenerate `display-profile.json` and `samples.js` from the copied evidence.

**Verify:** `node research/simulator/test-capture-replay.js`; `python3 -m unittest discover -s research/simulator -p 'test_*.py'`; click through `research/simulator/index.html` in a browser. **Exit:** real paired frames display, synthetic guidance is distinct, disconnect clears all. **Rollback:** remove only Step 1's copied images, derived profile, samples, and replay UI changes; preserve the preexisting simulator and bridge. No car state changes.

## Step 2 — Display-only guidance bridge

**Context:** `clarity_guidance_bridge.py` already OCRs one saved Apple Maps frame and plans a Honda Hack `UPDATE_NAVI_WAZE` visual broadcast. Maneuver parsing is narrow, and no active-distance OCR is verified. The backed-up layout has `turn_icon`, `next_road`, and `seg_dist` fields.

**Work:** Add Apple Maps/Waze fixtures for turn, distance, road changes, route end, and center app switching. Require confidence and bounded staleness; prove `STOP_NAVI` after disconnect, unrecognized OCR, timeout, or exception. When the center leaves Maps, screenshot OCR loses its source: clear the card and mark guidance unavailable until Maps returns or an independently verified metadata/secondary-stream source exists. Keep voice as observed state only. Avoid factory `ITBTInformation` setters. Run the bridge against replay fixtures before an optional stationary runtime test.

**Verify:** Python unit tests with mocked OCR/ADB plus replay acceptance cases. **Exit:** each sent visual update is traceable to a fixture, stale text always clears, center Music shows guidance unavailable for OCR, and rollback is observed in tests. **Rollback:** stop the Mac process; a future approved runtime test sends `STOP_NAVI` and installs no system patch.

## Step 3 — Read-only receiver and metadata evidence

**Context:** The copied Honda receiver has one configured main screen and a singleton proxy. The ordinary live log did not expose full iAP2 negotiation. Route Guidance metadata is a separate possible source for semantic turn information.

**Work:** Identify a read-only way to observe iAP2 display capability, stream setup, and Route Guidance payloads; compare Maps route changes with center app changes. If metadata is actually observed, add a metadata-to-visual adapter in the Mac harness. Record display identities, geometry, lifecycle, and gaps in the offline contract. Do not infer an API from feature strings alone.

**Verify:** source inspection, captured receiver trace, and reproducible observations across route and reconnect scenarios. **Exit:** a positive observation if a second setup or route payload is seen, or a bounded negative statement limited to the exact captured scenarios. **Rollback:** stop read-only capture; no vehicle file or setting changes.

## Step 4 — Optional decoder diagnostic

**Context:** This was the pre-September-25 gate. The completed [actual-frame probe](../captures/20260925T150706Z-SESSION_FINDINGS.md) observed two concurrent NVIDIA decoder instances producing 28/30 800×480 frames each in 1973 ms, then was removed. The all-30 criterion and coexistence with active factory CarPlay remain open.

**Work:** The signed API-17 APK, manifest/hash, parked run, and uninstall have been completed. Explain the two missing output frames offline; design a separate background-safe coexistence probe only if the receiver path warrants it. Treat the measured frames as one throughput observation, not a CarPlay protocol result.

**Verify:** offline source/build review first; later, if installed, stage-by-stage logs and a successful uninstall/reinstall rollback check. **Exit:** a bounded decoder allocation result and clean removal. **Rollback:** uninstall the exact diagnostic package. Do not run if its removal path or resource impact is not understood.

## Step 5 — Native multi-display decision

**Context:** Native Apple Maps map video needs an R15-compatible capability exchange, separate stream routing, a decoder and a cluster navigation-only surface. The existing receiver/proxy path does not currently establish these pieces.

**Work:** If Step 3 positively demonstrates compatibility or a licensed update path, implement a complete receiver-to-renderer contract in a Mac harness. First measure the cluster navigation safe area and prove an independent recovery path for this partial eMMC backup. Only then prepare a reversible vehicle candidate with exact binary diffs. If repeated observations show no second setup, record the bounded limitation and continue investigating the receiver; do not infer impossibility from one trace. Do not claim CarPlay Ultra support from ordinary multi-display support.

**Verify:** offline contract lifecycle and teardown tests establish only harness behavior. A separate parked-car gate must observe actual iAP2 setup, two received video channels, cluster rendering, and unchanged audio, with physical safe-area inspection. **Exit:** either a real iPhone-rendered cluster stream survives center app changes on the car, or a documented bounded blocker. **Rollback:** restore exact original files using a proven recovery method; do not install a receiver candidate if recovery or safe-area geometry is unproven.

## Plan changes

Record new evidence and changes to this plan in an ADR before altering the receiver. A failed gate may split a step or change its order; the report must distinguish observed vehicle behavior, copied-file evidence, and simulation.
