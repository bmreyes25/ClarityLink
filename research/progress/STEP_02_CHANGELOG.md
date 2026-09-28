# Step 2 changelog — independently accepted bounded offline/model scope

Starting Git HEAD: `2cb93bd0dbaef29386c19e5b7d518a0670c3e5ed` on `main`.
Repository was clean; origin is the intended private `bmreyes25/clarity-carplay-cluster` repository.

## Milestone 1 — firmware/storage catalog (2026-09-28T01:09:05Z)

Inspected required brief/status/policy and only numbered plan section 2, simulator source and existing tests before editing. No applicable AGENTS.md found in repository/parent paths. Verified tmp, assets and captures exclusions with `git check-ignore`; all ignored. No firmware/configuration modification or extraction, no derivative image needed. Both pristine datasets untouched. No vehicle commands.

- `python3 -m unittest discover -s research/simulator -p 'test_*.py'`: baseline 12 tests passed, exit 0.
- `for test in research/simulator/test-*.js; do node "$test" || exit; done`: baseline six suites passed, exit 0.
- `git status --short`, `git diff --stat`, `git remote -v`, `git branch --show-current`: clean baseline, main, intended URL, exit 0.
- `git ls-remote origin refs/heads/main`: baseline equals starting HEAD, exit 0.
- `python3 research/simulator/catalog_firmware.py /Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_WORKING research/simulator/firmware-catalog.json`: 14 allowlisted archive members and eight runtime states hashed, exit 0. No raw bytes emitted or extracted. Catalog records source archive/member, size and SHA-256; runtime text stays opaque.
- Python discovery after catalog: 14 tests passed, exit 0.

Files: `catalog_firmware.py`, `firmware-catalog.json`, `test_firmware_catalog.py`; preserve existing nine-partition storage fixture. High confidence in catalog identities/hashes, unknown deeper app ownership/protocol semantics. Existing sanitized native reports support service seams, not maneuver transport. Runtime focus remains unknown from new summaries.

Rollback: revert explicitly changed source/docs/fixtures, never working/pristine datasets. Next: pure Android/Binder and receiver ABI models; native ARM execution remains unavailable. Acceptance and dependent gates pending independent review.

## Milestones 2–3 — mocked services and labeled receiver ABI (2026-09-28T01:15:53Z)

Added `service-model.js` and `test-service-model.js`. Pure Binder dispatcher exposes only mock Navigation, ExternalDisplay and Audio methods. Receiver model retains the documented 24-byte/six-offset singleton restriction; USB/MFi readiness and callbacks are synthetic. No actual ARM load/execute, no second native screen registration, no device/vehicle connector. Static references: `research/native/receiver-multidisplay-audit.md` receiver table and `research/native/live-session-topology-20260925.md` binding/audio table. No raw vendor code sent to remote services.

`node research/simulator/test-service-model.js`: initially seven, then eight named tests passed, exit 0. Added runtime replay from eight captured-label/hash records, with observed/inferred/synthetic/unknown fields explicitly separated. Audio focus is unknown for snapshot replay; mock continuity does not establish real playback. `digital-twin.js` now invalidates all stream setup on route end, reconnect and 15-second stale-frame boundary; explicit tick supports deterministic cleanup. Guidance expires at the same inclusive boundary. Tests cover Maps→Music mirror vs independent proposed map, lifecycle order, stop/end/disconnect, late frames, stale guidance, mock audio invariance, blocked unmodeled Binder/bus calls and mutation rejection.

Limits: method call order/readiness/audio state are modeled, not captured ABI traces; opaque snapshots and acquired state labels do not prove per-event receiver behavior. Next: provenance/profile and browser verification. Acceptance remains pending independent review.

## Milestone 4 — dual-display provenance and browser replay

`build_simulator_assets.py`, `display-profile.json`, `test_profile.py`: six paired center/HDMI captures validated against saved sources, five Waze asset hashes added, complete-working `j_config.xml` hash equals existing profile hash. Physical Navigation rectangle explicitly null/uncalibrated. `index.html` uses the same service model and visibly labels observed mirror/Honda guidance vs synthetic second stream/metadata, with ARM-not-executed and unknown audio/physical bounds. `check_offline.py` provides repeatable Python/JS/browser checks; `browser-replay-check.js` uses local Chrome and exports assertions only. README/scope/status updated for limitations and independent-review handoff.

Actual commands/results:

- `python3 research/simulator/build_simulator_assets.py`: exit 0; all six pairs hash matched. Existing `samples.js` regenerated with no diff.
- Python discovery after provenance: 15 tests passed, exit 0.
- `npm install --prefix research/tmp/step-2/browser --no-audit --no-fund playwright`: exit 0, two packages in ignored tmp only; Chrome already installed.
- First `CLARITY_PLAYWRIGHT_MODULE="$PWD/research/tmp/step-2/browser/node_modules/playwright" CLARITY_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' python3 research/simulator/check_offline.py --browser`: Python/JS passed; browser failed exit 1 because its test incorrectly assumed the observed Music fixture ended with disconnect. Corrected the test to inject a separately modeled disconnect without altering observed fixtures. A preceding patch attempt failed on context matching and made no changes; corrected and reapplied.

High confidence in saved pixel provenance and deterministic model assertions. No photo calibration, native ARM execution, raw protocol decoding, measured second-stream audio/coexistence or full vehicle emulation. Exhaustive app/service ownership remains unimplemented. No dependent gate advanced; F-A/F-B unchanged. Independent supervising Codex must review the declared checks and unknowns before accepting Step 2. Detailed final results and Git checkpoint follow below.

## Final local verification — 2026-09-28T01:18:46Z

- `CLARITY_PLAYWRIGHT_MODULE="$PWD/research/tmp/step-2/browser/node_modules/playwright" CLARITY_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' python3 research/simulator/check_offline.py --browser`: all nine commands passed, exit 0. Counts: 15 Python unittest tests, six legacy JS assertion suites, eight named model tests, three browser replay mode checks plus zero page errors/remote HTTP requests. Local assertions-only log: ignored `research/tmp/step-2/check-results.txt`. No screenshots/traces exported.
- Re-ran catalog command with output `research/tmp/step-2/firmware-catalog-review.json`; `cmp research/simulator/firmware-catalog.json research/tmp/step-2/firmware-catalog-review.json`: exit 0, identical regeneration.
- Local Python SHA-256 comparison of complete-working catalog entries against existing static-analysis copies `extracted/system-vendor/system/bin/jmcs` and `extracted/system-vendor/system/lib/libcarplay_proxy.so`: both match. No copied binary changed or exposed.
- `gh repo view bmreyes25/clarity-carplay-cluster --json visibility,url`: exit 0, intended URL and `PRIVATE`.
- `git diff --check`: exit 0. Reviewed source/doc changes and generated catalog keys/hashes; only allowlisted artifact names, sizes and digests, no runtime contents.
- `git check-ignore research/tmp/step-2/browser/package-lock.json research/tmp/step-2/check-results.txt research/simulator/assets/center-20260925-music.png research/captures/20260925-waze-headunit-route/twin-survey/display-0.png`: exit 0, all excluded.

Sanitized fixture SHA-256:

- `firmware-catalog.json`: `f3bbd896b9b296af246813dc5110953127d6d8e67d7278b59918ff128c1c7427`.
- `display-profile.json`: `10ac7ae340ee05f67917f2299474fb1602052d043732954c4f2eec65a7716f0f`.

Git checkpoint procedure: explicitly stage the 16 reviewed Step 2 source/doc/test/JSON paths; inspect `git diff --cached --stat`, `--numstat`, `--check` and blob names/size/content for exclusions and credentials. Preserve the complete reversible source diff at ignored `research/tmp/step-2/source-review.patch` after staging; starting HEAD above preserves the baseline. Commit `Strengthen Step 2 offline twin models and replay provenance`, push `origin main` without force, then compare `git ls-remote origin refs/heads/main` to `git rev-parse HEAD`. The resulting SHA and actual remote outcome belong in the final handoff, not embedded in the commit itself. Stop on unexpected remote/credentials/divergence; do not mark acceptance from a push.

Pre-commit staged review actually passed: 16 explicitly named text files, initial total blob size 105,426 bytes, 983 additions/26 deletions; no ignored data paths, binary content or credential signatures. `git diff --cached --check` exit 0; staged stat/numstat inspected. `git ls-remote origin refs/heads/main` still matched starting HEAD immediately before commit. Final changelog staging and source patch regeneration include this review record. Commit/push are pending at this document's commit boundary; final handoff reports their actual results.

### Supervising Codex evidence handoff

Review only Step 2: required numbered plan section, the scope report's four-layer table, this changelog and the source diff. Reproduce catalog hashes from COMPLETE_WORKING, compare six pairs against their source captures locally, and run `check_offline.py --browser` with README environment. Inspect test assertions for mirror following Music, proposed map persistence, Honda route end, stale cleanup, disconnect and modeled audio continuity. Captured runtime snapshot bodies remain opaque; ABI callbacks and replay clock remain synthetic. No ARM receiver execution or actual second CarPlay stream is proven.

Outstanding gates: independent supervising Codex acceptance; photo-calibrated physical Navigation bounds; deeper app/service ownership and any actual ARM harness. Real protocol, decoder coexistence and audio validation remain their separately assigned dependencies. Next action is independent offline review of this checkpoint, not advancing a dependent gate or vehicle work. Rollback is an inverse of this source-only checkpoint or its saved patch; no firmware restoration required because no firmware/configuration was modified. Originals and raw artifacts remain local and unchanged.

## Continuation — finish the assigned offline/model scope (2026-09-28T01:31:52Z)

Starting HEAD for this continuation: `fc8c8d486c80dcedfa6cc81bcafb751c4874696b`; clean `main`, same intended origin. The previous checkpoint is pushed and remote-verified. Re-read required brief/status/policy and only plan section 2; no applicable AGENTS.md in repository/parents. Exclusions rechecked. No firmware/configuration changes or extraction, no whole-image duplication or firmware derivative required. Pristine originals untouched. All raw data processed locally; no pixels, runtime bodies, vendor bytes, routes or credentials emitted to remote AI. Source and derived numeric/allowlisted fixtures only enter Git.

The user's assigned scope explicitly permits a labeled receiver ABI model and uncertain physical Navigation bounds. Actual ARM execution and exhaustive reverse engineering are therefore documented limitations, not new prerequisites for the bounded offline oracle. Photo content placement is now inferred from observed correspondences; physical safe edges remain unknown. No dependent vehicle/protocol/decoder gate advances from a model assertion.

### Service ownership/runtime milestone

Files: `catalog_services.py`, `service-evidence.json`, `test_service_evidence.py`; linked from `catalog_firmware.py` and expanded `firmware-catalog.json`. Four allowlisted APK manifest owners identify Navigation, CarPlay and ExternalDisplay services. Current APK binary manifests match the prior decoder input manifests before decoded declarations are used; archived APK/binary/decoded manifest hashes are recorded. Activity dumps supply actual binding edges separately from the service-manager registry. All eight states show CarPlayApService bound to NavigationApService and ExternalDisplayApService; AvApService holds audio focus on stream 12, including disconnected acquisition labels. That proves snapshot ownership, not active CarPlay audio or per-event continuity. Observed logical dimensions are 800×480, not physical safe bounds.

`catalog_firmware.py` now hashes activity/audio/display/services for all eight states. `replayRuntimeSnapshots` optionally attaches service observations only if all shared source hashes match; observed snapshot focus stays separate from the model's audio lifecycle. Misdated/unmatched provenance is rejected. Runtime labels still imply app/connection actions; synthetic ABI callback ordering and replay time remain labeled.

Actual commands: `python3 -m unittest discover -s research/simulator -p test_service_evidence.py` initially exit 1 before implementation, then an overstrict test was corrected; final seven tests passed exit 0. `python3 research/simulator/catalog_services.py <COMPLETE_WORKING> research/simulator/service-evidence.json`, repeat to ignored `research/tmp/step-2/service-evidence-repeat.json`, and `cmp`: exit 0, four owners/eight snapshots, byte-identical. `python3 -m py_compile research/simulator/catalog_services.py research/simulator/test_service_evidence.py`: exit 0.

### Photo placement/geometry milestone

Files: `calibrate_display.py`, `photo-calibration.json`, `test_display_geometry.py`; integration in `build_simulator_assets.py`, `display-profile.json`, `display-geometry.js`, `test_profile.py`, `index.html` and `browser-replay-check.js`. Installed OpenCV/numpy only in ignored `research/tmp/step-2/vision-env`; no images uploaded. All five physical JPEG asset copies hash-match saved sources. Copied meter layout lines 2, 74–75 provide 584×215 layout and top padding 24: inferred cast content rectangle `[0,24,584,191]`, with config hash recorded. No configuration was changed.

Local SIFT/RANSAC projects that region into separate 1280×960 Maps/Music photo poses. Maps: 66 inliers, median residual 0.3016 photo px, 95th percentile 0.8301; Music: 31, 0.3562, 0.8817. Maps right corners extrapolate outside matched support. Deterministic 100-fit resampling reports algorithm sensitivity, not physical-boundary confidence. Camera poses cannot define a shared panel-native rectangle; physical safe edges/power-scale clearance remain unknown. Home has no corresponding HDMI frame and stays unknown. Browser photo polygons are inferred; proposed map viewport and pixels are visibly synthetic and clipped on an 800×480 schematic. No safe-boundary, native CarPlay or ABI capability claim derives from these fits.

Actual commands: `python3 -m venv research/tmp/step-2/vision-env`, `research/tmp/step-2/vision-env/bin/pip install --disable-pip-version-check opencv-python-headless`: exit 0, OpenCV wheel 5.0.0.93 and numpy 2.5.3. `research/tmp/step-2/vision-env/bin/python research/simulator/calibrate_display.py`: exit 0, numeric summary only. Geometry unittest discovery in this venv: eight passed, zero skips; system Python discovers eight with six optional dependency skips, so full acceptance uses the venv. Compilation and deterministic in-memory JSON regeneration/hash compare passed. No image artifacts produced. `python3 research/simulator/build_simulator_assets.py`: exit 0, source hashes checked and numeric browser bundle regenerated.

### Independent review findings corrected

An independent Codex reviewer reproduced stale capture ownership: a historical observed frame masked an active proposed stream, and route-bearing Waze pixels survived modeled route end. Added regression tests first: `node research/simulator/test-service-model.js` exited 1 with three failures (compositor ownership, route-bearing capture cleanup, pre-frame setup/activation TTL). Fixed precedence, route-end/TTL retirement of route-bearing capture IDs, and setup/activation timeout. An explicit observed ended-compass frame remains available. Observed source images and event fixtures are preserved; these cleanup rules are labeled model policies. Final named model tests: 11 passed, exit 0. Reviewer also requested shared observation provenance checks; altered activity/display/services hashes now reject in tests.

### Integrated verification and handoff

`CLARITY_PLAYWRIGHT_MODULE="$PWD/research/tmp/step-2/browser/node_modules/playwright" CLARITY_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' research/tmp/step-2/vision-env/bin/python research/simulator/check_offline.py --browser`: nine commands passed, exit 0; **31 Python tests (zero skips), 11 named model tests, six legacy JS suites, three browser modes**, zero page errors/remote HTTP requests. Browser checks active-owner agreement, observed Music mirroring, Waze background/end, proposed map persistence, synthetic SVG clipping and disconnect cleanup. `node --check` for every simulator JS and `git diff --check`: exit 0. Updated README contains exact full-check and regeneration commands. No configured package build/type/lint gate exists for these plain JS/Python models; no coverage percentage claimed.

Sanitized fixture hashes after integration:

- Firmware catalog: `7a60209fa417b4aaf1ad6b4ad416a66f4b763d5339b97548e904d4c2d5840f20`.
- Service evidence: `197ba2d9eb9dc9e79f464406837bff9c70dc7315194dbe1486173fc4cb36ee6a`.
- Photo calibration: `fc48180a93779f9edbdcb2ffcbf2a6b2d2c53d22f0145af4f5206eebcfbfdb8a`.
- Display profile: `4934f8c306a590fbb8274f7c7d9de0a4c9cc8b92222ca95668cabf40db90e10b`.

Independent supervising Codex review is being reproduced separately in `research/verification/STEP_02_REVIEW.md`; acceptance is not claimed until its verdict is recorded. Reviewer receives all four-layer source/fixture/report paths and full reproduction commands. Rollback: revert only this continuation's explicitly reviewed source/doc/test/JSON/JS paths to starting HEAD, or apply inverse of saved ignored `research/tmp/step-2/finish-source-review.patch`; never restore/change datasets. Remaining real-world limitations: physical Navigation safe edges, actual ARM execution, actual CarPlay second-stream negotiation and measured audio/decoder coexistence. These require separate evidence before their dependent gates. Final review verdict and Git checkpoint follow below.

## Independent acceptance and final checkpoint

Independent supervising Codex review now completed: `research/verification/STEP_02_REVIEW.md` accepts the user's bounded offline/model Step 2 scope after inspecting all four layers and independently reproducing full tests and three generator comparisons. No remaining blocking implementation finding. Status/scope/README now record that acceptance. All four assigned offline/model layers are complete; actual ARM execution, physical Navigation safe edges and native second-stream/audio capability remain explicitly unproven and do not pass a dependent gate. F-A/F-B unchanged.

Reviewer independently ran the full vision-env/browser command: 31 Python tests with zero skips/failures, 11 named model tests, six legacy JS suites, three browser modes; zero page errors or remote HTTP requests. All 14 simulator JS files passed syntax. Firmware/service/photo generators to ignored `independent-catalog.json`, `independent-services.json`, `independent-calibration.json` reproduced tracked JSON byte for byte with `cmp` exit 0. Report contains commands, hashes, four resolved findings and limitations.

Final files changed/purpose: catalogs/service evidence and tests add allowlisted ownership/bindings/focus provenance; calibration script/fixture/tests add deterministic inferred content placement and uncertainty; numeric geometry JS, profile/builder, UI/browser tests integrate clipped synthetic viewport and inferred photo overlays; twin/service model/tests fix ownership/end/stale/startup/provenance behavior; README/scope/status/changelog/review record reproducible acceptance and limitations. No firmware/config/source dataset change; source rollback only.

Next action: use this reviewed fixture/model oracle for separately assigned offline work. No car patch, new acquisition, protocol verdict or decoder/audio compatibility result is authorized by this completion. Stage only explicitly reviewed source/docs/tests/derived sanitized fixtures, inspect staged names/content/size, preserve ignored `finish-source-review.patch`, commit a descriptive checkpoint and push `origin main` without force. Verify with `git ls-remote origin refs/heads/main` against resulting `git rev-parse HEAD`. Commit/push results and final SHA will be reported in the external handoff, not embedded into the commit itself.

Final pre-commit review, **2026-09-28T01:35:31Z**: 22 explicitly named changed text files staged; initial staged blob size **209,467 bytes**, 2,016 additions/36 deletions. Inspected staged stat/numstat/names and source/fixture contents; no private captures/resources/tmp paths, raw binary content or credential signatures. `git diff --cached --check` exited 0. Generated numeric browser bundle exactly equals reviewed calibration JSON. `gh repo view ... --json visibility,url` confirms intended private remote; `git ls-remote origin refs/heads/main` still equals continuation starting HEAD. Ignore checks pass for venv, review patch, private photo and copied config. Saved full reversible source diff at ignored `research/tmp/step-2/finish-source-review.patch`; regenerating it after this changelog update preserves the final staged change. Commit/push verification will be performed next; acceptance is the independent offline scope verdict above, separate from publication success.
