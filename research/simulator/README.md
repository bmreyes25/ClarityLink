# Clarity offline simulator and guarded guidance bridge

The [infotainment twin evidence map](INFOTAINMENT_TWIN_SCOPE.md) defines the supported scope, measured versus synthetic inputs, and the missing runtime observations. The next parked session's `twin-survey` captures can be compared offline with [`twin_survey_compare.py`](../scripts/twin_survey_compare.py) before adding them as replay fixtures. A hash or layer difference alone is not a decoded CarPlay secondary stream.

**Load September 25 casting session** replays the new, observed sequence: Apple Maps with casting off (native compass on HDMI), Apple Maps with casting on (Maps mirrored), then center Music with casting on (Music mirrored). The user confirmed voice guidance during casting. New [physical Maps](assets/physical-maps-20260925.jpg), [CarPlay Home](assets/physical-carplay-home-20260925.jpg), [Music](assets/physical-music-20260925.jpg), and [Honda Home](assets/physical-honda-home-20260925.jpg) photos show the cast occupying a wide central region below speed and above the Menu/trip row. Speed and range remain visible, but edge clearance near the power/charge scales needs measurement. These images are copied from the saved captures; `display-profile.json` stores their hashes. This sequence proves the existing Honda Hack path follows the center screen; it is not a separate Apple Maps stream.

**Load head-unit Waze guidance** replays a second parked observation: Android Waze shows a route while HDMI and the physical cluster show a 300-foot arrow, the arrow remains when the center switches to Honda Home, and the cluster returns to compass after the route ends. The first two HDMI PNGs were byte-identical. This is an independently rendered Honda guidance view sourced from Waze *on the head unit*, not iPhone CarPlay. [Capture findings](../captures/20260925-WAZE_HEADUNIT_FINDINGS.md) identify the Honda Hack hook and 5601/5602/5603 handler route. The sample makes the renderer behavior replayable offline without claiming a CarPlay metadata source.

[`native_guidance_adapter.py`](native_guidance_adapter.py) is a pure Mac-side model of that live `enable_custom_meter=false` path. It maps a verified maneuver, road, and meter distance to handler 5601/5602/5603 events, with status 2 for route end. It has **no ADB or broadcast function**. The saved Apple Maps `Start on Example Rd` frame contains no next-maneuver distance, so this model deliberately refuses to produce a display update from that image alone. The factory's normal start/turn views omit the road name even when the handler receives it; `expected_factory_view` records that limitation. Tests cover the Waze 81-meter positive control, maneuver mapping, missing-distance rejection, layout selection, and route-end clearing. A full Goal 1 display needs a separate bounded custom view or a genuine second CarPlay map stream.

## Run the captured two-display simulator

Open [`index.html`](index.html) in a browser. **Load captured displays** and step through the events, or press **Play**. The center pane replays the saved Apple Maps and Music frames; the cluster pane shows the matching HDMI capture. The two cluster capture files in that session were byte-identical. The 584×215 Honda Hack meter preview is a *proposed, synthetic* navigation layer, not an iPhone-rendered second stream or a claim about exact physical placement. Its guidance clears before the center changes to Music because a center-screen OCR bridge would lose its Maps source. The final disconnect event removes both screenshots.

The three PNGs in `assets/` are local copies of read-only captures. `working-backup/j_config.xml` and `working-backup/meter_civic.xml` are copies of extracted backed-up files. `display-profile.json` records their measured 800×480 CarPlay screen and 584×215 meter layout dimensions, source hashes, and the unverified physical placement. The original backup under `~/ClarityLab/backups/CLARITY_BACKUP_20260918_0225_ORIGINAL` has not been changed. All sample buttons use generated `samples.js` and work when the page is opened directly; no network connection is required.

Regenerate derived assets after changing a working copy or sample log:

```sh
cd /Users/bmreyes24/ClarityLab/clarity-analysis
python3 research/simulator/build_simulator_assets.py
node research/simulator/test-capture-replay.js
python3 -m unittest discover -s research/simulator -p 'test_*.py'
```

The captured frame pairs were taken consecutively, not atomically. The proposed preview's `Example Road` turn is synthetic and does not mean the receiver supplied route guidance. Physical cluster elements outside the HDMI capture are absent from the simulator. The OCR subprocess has a 45-second timeout; a timeout is reported as a stopped bridge rather than hanging indefinitely.

The saved Apple Maps frame is `fixture-carplay-main.png`; the simultaneously captured cluster frame is `fixture-cluster-cast.png`. `GuidanceOCR.swift` uses macOS Vision to read the main screen. `GuidanceCard.swift` produces `fixture-guidance-card.png` by cropping the actual guidance card, proving an image-based interim display is possible. This image is **not** a second iPhone-rendered stream.

Build the two Mac tools using the included Xcode command-line compiler:

```sh
cd /Users/bmreyes24/ClarityLab/clarity-analysis
xcrun swiftc -O research/simulator/GuidanceOCR.swift -o research/simulator/guidance-ocr
xcrun swiftc -O research/simulator/GuidanceCard.swift -o research/simulator/guidance-card
```

Inspect the saved frame and the proposed Honda Hack display commands without connecting to a car:

```sh
python3 research/simulator/clarity_guidance_bridge.py
```

The local `index.html` visualizes the extracted guidance image and replays a JSONL event log. Choose the bundled log with its file picker, or run a local HTTP server from this directory and use **Load bundled example**. `digital-twin.js` never opens a network or device connection. Vehicle values in the example are synthetic; the navigation phrase and voice observation come from the saved capture/user verification.

## Independent-screen receiver model

Use **Load independent-screen example** or open `sample-dual-screen.jsonl` to inspect the proposed Volvo-style lifecycle: connected receiver → cluster display advertised → separate cluster setup → map channel active → center changes from Maps to Music while the cluster frame persists → route ends → stream stops → disconnect clears state. The map-like background is a schematic drawn in CSS; no iPhone video is decoded or copied. This model establishes a testable interface boundary and failure behavior, not CarPlay compatibility.

Run `node research/simulator/test-dual-screen.js` from the analysis root. Its checks verify that the cluster remains active across a center-app change, rejects setup when the receiver did not advertise a cluster display, and clears stale frames at route end/disconnect. The earlier `sample-replay.jsonl` format still works.

**Load proposed stream contract** replays a versioned, hypothetical receiver-to-renderer event contract through `contract-adapter.js`. Its second cluster frame persists while the center is Music, then clears on stop/disconnect. **Load hypothetical route metadata** shows a separate semantic guidance path: a synthetic turn remains through the center-app change and expires after 15 seconds without refresh. Center-screen OCR guidance instead clears immediately when Maps leaves the center. Neither example represents captured iAP2 payloads or a functioning native dual-display receiver.

Run `node research/simulator/test-contract-adapter.js` and `node research/simulator/test-guidance-expiry.js` to verify these behaviors. The adapter and digital twin only read local sample files; they cannot write to the car.

## Proposed reversible on-car display test — not yet run

`clarity_guidance_bridge.py` contains an optional, bounded `--live` mode for a later *explicitly approved* parked-car test. It reads an 800×480 center screenshot over ADB, recognizes a small set of English Apple Maps banner phrases, and proposes the Honda Hack `UPDATE_NAVI_WAZE` broadcast with `icon` and `street` extras. This branch requires `nav_in_dashboard=true`, `enable_custom_meter=true`, and `enable_screen_cast=false`; a read-only live-preference check refuses execution otherwise. **The September 25 car had `enable_custom_meter=false` and `enable_screen_cast=true`, so this script will refuse that observed state.** The successful Android Waze display used the other `UPDATE_NAVI`/5601–5603 route, which needs its own offline mapping and validation. Do not use this script as evidence that Apple Maps is already bridged to the cluster.

The exact reversible state change is **temporary Honda Hack navigation view visibility and text/icon**. No APK, system file, firmware image, or persistent preference would be changed. Stopping the test sends `STOP_NAVI`, restoring the prior native view; the Python process also sends it in a `finally` block. The current script is a prototype and has only been tested against saved frames, not on the car. The user must explicitly authorize any first live run. Keep the car parked for this test and visually verify that no warnings or other cluster content are obscured. If the cluster presentation is unsuitable, stop immediately; the center CarPlay screen and its spoken directions remain the baseline.

Limitations: OCR has only been checked on one Apple Maps image (`Start on Example Rd`). It cannot decode the roundabout-arrow image, multilingual directions, or all distance formats yet. A second live screenshot may change the CarPlay layout. If the screenshot text is uncertain, the bridge does not send a direction. The current intermediate renderer is an image/semantic overlay, not dedicated CarPlay secondary-display negotiation. A firmware patch would be a separate project with a boot recovery plan.
