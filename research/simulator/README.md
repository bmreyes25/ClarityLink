# Clarity offline simulator and guarded guidance bridge

## Step 2 repeatable checkpoint

The four-layer implementation and remaining gaps are in [the scope report](INFOTAINMENT_TWIN_SCOPE.md#step-2-bounded-checkpoint--september-28-utc). **Step 2 is complete and independently accepted for the assigned offline/model scope.** The [review](../verification/STEP_02_REVIEW.md) records reproduced checks and retained limits. The receiver is an explicitly labeled ABI **model**, not execution of `jmcs` or its ARM proxy. Photo registration now estimates cast footprints for Maps and Music in each camera view. Physical Navigation safe edges and panel-native coordinates remain unknown. All new interfaces are offline mocks; no production vehicle-bus connector is present.

Run the baseline offline checks, including existing private-capture checks (six OpenCV geometry tests skip on system Python; use the full acceptance command below):

```sh
python3 research/simulator/check_offline.py
```

The full acceptance command also runs the local photo-geometry tests. Install the small analysis environment in ignored scratch space; no private images are uploaded. The actual browser check uses locally installed Chrome and Playwright in ignored scratch space. It reads private images locally and exports no screenshots, video, trace or raw pixels; it blocks HTTP/HTTPS requests. On this Mac:

```sh
python3 -m venv research/tmp/step-2/vision-env
research/tmp/step-2/vision-env/bin/pip install opencv-python-headless==5.0.0.93 numpy==2.5.3
npm install --prefix research/tmp/step-2/browser --no-audit --no-fund playwright
CLARITY_PLAYWRIGHT_MODULE="$PWD/research/tmp/step-2/browser/node_modules/playwright" \
CLARITY_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
research/tmp/step-2/vision-env/bin/python research/simulator/check_offline.py --browser
```

Open `research/simulator/index.html` locally and select **Load September 25 casting session** (observed mirror), **Load head-unit Waze guidance** (observed Honda guidance), or **Load independent-screen model** (synthetic proposed second stream). The replay badge names the evidence category. Modeled audio focus remains unknown unless explicitly set; observed runtime focus snapshots are documented separately; continuity tests are explicitly modeled. Capture pairs and hashes are recorded in `display-profile.json`. The active compositor owner is shown separately from saved observed reference captures. The proposed 800×480 display-1 schematic clips its synthetic map to an explicitly synthetic viewport based on the inferred cast configuration; two photo overlays show inferred placement with uncertainty. Synthetic map/metadata fixtures do not contain captured iPhone streams.

Regenerate the allowlisted firmware catalog from the complete working dataset without extracting files:

```sh
python3 research/simulator/catalog_firmware.py \
  /Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_WORKING \
  research/tmp/step-2/firmware-catalog-review.json
cmp research/simulator/firmware-catalog.json research/tmp/step-2/firmware-catalog-review.json
```

The catalog stores only archive/member names, byte counts and hashes. Raw runtime snapshots stay local. `catalog_services.py` extracts only allowlisted current APK ownership, activity-service binding edges, logical dimensions and audio focus snapshot facts into `service-evidence.json`. Four current APK binary manifests match the prior decoder inputs. All eight saved states show CarPlay service binding to Navigation and ExternalDisplay, plus AvApService focus on stream 12, including disconnected acquisition labels; that is not continuous CarPlay audio evidence. Eight state labels drive inferred app/connection transitions through `replayRuntimeSnapshots`, which labels its callback sequence and clock synthetic and its protocol and per-event audio unknown. Passing service evidence into the replay exposes snapshot observations separately from modeled audio; all shared activity/audio/display/services hashes must match before those facts are attached. The callback offsets and singleton restriction are static evidence; method ordering, transport readiness and audio updates are modeled behavior. Stale guidance/stream TTL is a 15-second model policy, evaluated on each event or explicit `tick`. Route end, failed stream, disconnect, reconnect and setup/activation stalls invalidate stream setup and reject late frames. Captured route-bearing Waze/Maps pixels retire on modeled end/TTL while the explicit observed ended-compass fixture remains. A proposed active stream owns the modeled output over an older reference capture. Audio music/voice state is preserved through app switches, route end and stream stop, then released on disconnect in the model. Full Android/Tegra/QEMU boot is not a prerequisite.

Reproduce service and photo evidence without changing raw inputs:

```sh
python3 research/simulator/catalog_services.py \
  /Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_WORKING \
  research/tmp/step-2/service-evidence-review.json
cmp research/simulator/service-evidence.json research/tmp/step-2/service-evidence-review.json
research/tmp/step-2/vision-env/bin/python research/simulator/calibrate_display.py \
  --output research/tmp/step-2/photo-calibration-review.json
cmp research/simulator/photo-calibration.json research/tmp/step-2/photo-calibration-review.json
```

`photo-calibration.json` records observed source hashes and inferred photo quadrilaterals, residuals, support and deterministic resampling sensitivity. Maps has 66 inliers and 0.302 photo-pixel median residual; Music has 31 and 0.356. Maps right corners extrapolate beyond its matched feature support. The camera poses differ, and resampling does not establish safe edge clearance. Home correspondence is unavailable. No photo coordinate is advertised as a CarPlay capability or a physically safe vehicle rendering rectangle. `build_simulator_assets.py` validates calibration source hashes and regenerates numeric-only `display-geometry.js` for file-based replay.

The [sanitized forensic storage fixture](forensic-storage-map.json) is generated from the verified working eMMC image and live mount inventory by `research/acquisition/catalog_storage.py`. Its nine GPT partitions, ext4 signatures, and mount/read-only states seed the firmware-catalog layer of the twin. It contains no filesystem contents and says nothing about display pixel bounds; those still come from display captures and physical photos. The image was read live, so writable filesystem contents are not an atomic snapshot. Run `python3 -m unittest discover -s research/simulator -p 'test_*.py'` to check the fixture's partition ordering and mount relationships.

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
