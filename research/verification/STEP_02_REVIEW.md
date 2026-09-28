# Independent supervising Codex review — Step 2

Reviewed at **2026-09-28T01:31:18Z**. Starting checkpoint: `fc8c8d486c80dcedfa6cc81bcafb751c4874696b`; review includes the subsequent uncommitted Step 2 implementation. Commit/push verification remains the executor's checkpoint responsibility.

## Verdict

**Accepted for the user's bounded offline Step 2 scope.** All four required layers have useful, repeatable offline implementations. This acceptance explicitly permits the labeled receiver ABI **model** and uncertain physical Navigation safe bounds, as the user's assigned work does. The numbered plan's stronger actual native harness/physical rectangle interpretation has not been established and must not be claimed.

This is an infotainment oracle for declared fixtures and modeled lifecycle behavior. It is not a full vehicle emulator, native CarPlay implementation, decoder coexistence measurement, protocol capability verdict, or authorization for vehicle work. Actual ARM receiver execution, physical safe edge clearance, exhaustive service reverse engineering, and real proposed-stream audio remain unavailable. No dependent on-car gate is accepted by this review.

The reviewer independently inspected required brief/status/policy, numbered plan section 2 only, checkpoint/source/tests, sanitized static receiver/topology references and new generators. The reviewer did not change implementation, commit, push, inspect raw capture pixels in a remote tool, or contact a vehicle. Local feature algorithms processed private images without exporting them.

## Findings resolved during review

1. **P2, compositor ownership:** baseline `service-model.js` gave an older observed capture precedence over an active proposed stream, while browser state indicated the proposed map. Independently reproduced with a saved Music capture followed by cluster setup/activation/frame. Current `ExternalDisplay.compose` gives the proposed active frame ownership; historical reference capture remains separately labeled. Regression `proposed active stream owns HDMI over an earlier observed reference capture` passes.
2. **P2, stale guidance pixels:** baseline route-end cleared guidance state while an observed Waze route frame remained the compositor output. Current `digital-twin.js` retires identified route-bearing captures at modeled route end and the inclusive 15-second replay-clock boundary; observed ended-compass captures remain. This is explicitly modeled cleanup, not a newly captured end/unplug event. Regression tests pass.
3. **P2, incomplete stream timeout:** setup/activation without a first frame had no expiry. Current setup and activation start a modeled timeout, release stream state at its boundary, reject late activation/frame events, and preserve modeled audio. Regression passes.
4. **P2, runtime provenance:** new service facts were initially bound only to the matching audio hash. Current runtime replay requires all four shared snapshot hashes (activity, services, audio, display); altered activity/display/service digests are rejected. Independently regenerated both catalogs match their tracked fixtures byte for byte.

No remaining actionable blocking finding in the bounded implementation reviewed here.

## Four-layer evidence

| Layer | Independently verified | Limit retained |
| --- | --- | --- |
| Firmware/storage | Nine-partition existing sanitized GPT/mount fixture consistency test; 14 allowlisted firmware members, eight four-file runtime snapshots; complete-working catalog regeneration identical. Four APK manifest owner facts are tied to hashed current APK manifests and matching prior decoder input. | Prior GPT acquisition validation is reused, not re-acquired; live archives non-atomic, not exhaustive firmware extraction. |
| Android/application | Pure mock Binder allowlist, Navigation/ExternalDisplay/Audio model; service evidence regeneration identical. Tests distinguish activity-service bindings from service registry, allowlist output and snapshot focus from continuity. | No Android/Binder executes. Binding does not establish CarPlay route fields. |
| Receiver | Singleton six 32-bit callback slots/24 bytes and duplicate `0x16` agree with `research/native/receiver-multidisplay-audit.md:18`. Mock USB/MFi/display/audio lifecycle and hashed snapshot replay pass. | JS model only; no actual ARM loading, proprietary USB/MFi packets, authentication, second native callback, or video decoding. |
| Dual display | Six paired center/HDMI hashes verified by local tests; 800×480 surfaces; observed mirror, observed Honda Waze guidance, and visibly synthetic proposed stream browser replays pass. Music follows mirrored center while proposed map persists. Photo registrations regenerate identically. Synthetic map is clipped to a labeled proposed viewport. | Paired captures non-atomic; event clocks illustrative. Photo content quads inferred, safe bounds/panel coordinates unknown; no physical safety guarantee. |

Photo registration reproduced **66 Maps inliers**, median residual **0.3016 photo px**, and **31 Music inliers**, median **0.3562 photo px**. Maps support covers only part of the source width; extrapolation, different camera poses, and algorithm-only resampling intervals remain visible. `physicalNavigationSafeBounds.rectangle` remains null and `calibrated` false. These are repeatable content-placement estimates, not physical Navigation calibration.

Observed facts, inferred label-derived app/session state, synthetic ABI calls/clock/map metadata, and unknown transport/audio are separate in fixtures and runtime checkpoints. Mock audio invariance tests do not imply measured voice continuity. Imported chronology retains an unverified-provenance label.

## Actual independent commands and results

All commands run locally in the analysis repository; each below exited **0**:

```sh
CLARITY_PLAYWRIGHT_MODULE="$PWD/research/tmp/step-2/browser/node_modules/playwright" \
CLARITY_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
research/tmp/step-2/vision-env/bin/python research/simulator/check_offline.py --browser

python3 research/simulator/catalog_firmware.py \
 /Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_WORKING \
 research/tmp/step-2/independent-catalog.json
python3 research/simulator/catalog_services.py \
 /Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_WORKING \
 research/tmp/step-2/independent-services.json
research/tmp/step-2/vision-env/bin/python research/simulator/calibrate_display.py \
 --output research/tmp/step-2/independent-calibration.json

cmp research/simulator/firmware-catalog.json research/tmp/step-2/independent-catalog.json
cmp research/simulator/service-evidence.json research/tmp/step-2/independent-services.json
cmp research/simulator/photo-calibration.json research/tmp/step-2/independent-calibration.json
git diff --check
```

- Full verification: **31 Python tests, zero skips/failures; 11 named model tests; six legacy JavaScript assertion suites; three browser modes**, zero page errors or remote HTTP requests. Nine check commands pass. Browser also asserts the synthetic 800×480 viewport clipping, active compositor owner, two inferred photo polygons and disconnect/reset cleanup.
- `node --check` run individually through a local Python loop over all **14 simulator JavaScript files**: all exit 0. Plain JS/Python has no configured package build/type/lint gate; no coverage percentage is claimed. Meaningful model/provenance/browser checks substitute for unrelated build commands.
- Baseline `build_simulator_assets.py` exited 0 and preserved baseline sample content. Final Python profile tests independently verify six paired sources/assets and configuration digests.
- `git check-ignore` for three independent generated review copies and `research/simulator/assets/physical-maps-20260925.jpg`: all excluded, exit 0. Reviewed new source has no production vehicle-bus connector, real Binder/USB/native execution or firmware writes.

Reviewed fixture SHA-256:

| Fixture | SHA-256 |
| --- | --- |
| firmware-catalog.json | `7a60209fa417b4aaf1ad6b4ad416a66f4b763d5339b97548e904d4c2d5840f20` |
| service-evidence.json | `197ba2d9eb9dc9e79f464406837bff9c70dc7315194dbe1486173fc4cb36ee6a` |
| photo-calibration.json | `fc48180a93779f9edbdcb2ffcbf2a6b2d2c53d22f0145af4f5206eebcfbfdb8a` |
| display-profile.json | `4934f8c306a590fbb8274f7c7d9de0a4c9cc8b92222ca95668cabf40db90e10b` |

## Checkpoint handoff

Executor should record this independent acceptance in the Step 2 scope/status/changelog, preserve the limitations, inspect staged sanitized content and size, commit/push without force, and verify `origin/main` equals the new commit. Report that resulting commit externally rather than embedding its own SHA in it. Raw firmware/captures/runtime bodies and local environments remain ignored. Rollback is source/docs/fixture reversion only; no firmware restoration is needed because no firmware/configuration was modified. Vehicle, protocol, recovery and coexistence gates remain separately pending.
