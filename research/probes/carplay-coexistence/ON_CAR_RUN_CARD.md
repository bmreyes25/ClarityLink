# Step 3 candidate — parked active-CarPlay decoder coexistence run card

**Review state: prepared, not approved for execution.** This is the candidate handoff for GPT-6 Sol Codex to inspect. Do not run it until the exact package/source/hash and this card have been reviewed and the user separately authorizes the new temporary APK install. No car or ADB device was contacted to prepare this card.

## Exact candidate and intended effect

- Package: `org.claritylab.carplaycoexistence`
- Local APK: `research/probes/carplay-coexistence/build/carplay-coexistence-probe-signed.apk`
- SHA-256: `59e7505e9b53fdb5bc6ee73ab10efcd9b377bc953a6e36dd9f6aaac42a5a7ea6`
- Signature: API-17 v1 signature verified by the local Google `apksig` verifier.
- Android manifest: no permissions, no Activity, one explicit exported service, and no intent filter. The service is explicitly addressable by ADB shell; while installed, another local app that knows the component could also start it. It performs only AVC decoding and logcat output.
- Install effect: temporary APK and ordinary private app data under Android `/data`; no system/config/firmware edits. Runtime: one NVIDIA 800×480 AVC decoder, 900 frames at 15 fps for 60 seconds, then a five-second maximum EOS drain (plus up to one second to queue EOS); persistent foreground notification includes STOP.
- Explicitly excluded: surfaces/overlays, center-display rendering, audio APIs, network, root, Honda Binder APIs, cluster, vehicle bus, CAN/B-CAN/F-CAN, filesystem writes by the app.

The APK consumes one hardware decoder while CarPlay is active. Decoder pressure can still affect CarPlay even though the app cannot touch its picture or audio paths. Keep the vehicle parked. Stop immediately on CarPlay freeze, spoken-guidance interruption, warnings, unusual lag, or unexpected screen changes.

## Mac preflight

Rebuild and run the host checks:

```sh
python3 research/probes/carplay-coexistence/build_probe.py
python3 -m unittest discover -s research/probes/carplay-coexistence -p 'test_*.py' -v
shasum -a 256 research/probes/carplay-coexistence/build/carplay-coexistence-probe-signed.apk
```

The APK hash must exactly match the value above. Use a fresh, ignored local directory under `research/captures/` for raw logcat and JSONL; do not commit, email, or upload those captures.

## Parked setup and baseline

1. Park safely and keep the vehicle stationary for the entire test. Keep the current head-unit configuration unchanged; Honda Hack casting must be off.
2. Connect CarPlay and start an Apple Maps route. Put Music on the center display while leaving the route active. Confirm spoken guidance is audible. Set the factory cluster to its Navigation page if that was the reviewed baseline.
3. Record the center picture, cluster view, voice status, and any existing warning before installation. Do not continue if CarPlay or voice is already unstable.
4. On the Mac, select the current ADB serial and confirm the package is absent:

```sh
adb devices -l
adb -s <serial> shell pm path org.claritylab.carplaycoexistence
```

Expected `pm path`: no package path. If it is installed already, stop and investigate; do not overwrite it.

## Install and run

Save the capture only on the Mac:

```sh
CAPTURE="research/captures/decoder-coexistence-YYYYMMDDTHHMMSS"
mkdir -p "$CAPTURE"
RAW="$CAPTURE/logcat.txt"
adb -s <serial> install research/probes/carplay-coexistence/build/carplay-coexistence-probe-signed.apk
adb -s <serial> logcat -v time -s ClarityCoexistence:I '*:S' > "$RAW" &
LOGCAT_PID=$!
adb -s <serial> shell am startservice -n org.claritylab.carplaycoexistence/.DecoderCoexistenceService --es action START
```

Observe center CarPlay picture and spoken guidance before, during, and after the maximum 66-second run. Stay ready to abort. After up to 70 seconds, stop the Mac logcat client and score the unedited log:

```sh
kill "$LOGCAT_PID"
wait "$LOGCAT_PID" 2>/dev/null || true
python3 research/probes/carplay-coexistence/extract_logcat.py "$RAW" "$CAPTURE/trace.jsonl"
```

Keep the original logcat unchanged. If extraction says there is no trace, malformed JSON, or an invalid trace, treat the run as incomplete; do not repair the log manually or rerun without review.

## Abort and rollback

If any abort condition occurs, issue STOP immediately:

```sh
adb -s <serial> shell am startservice -n org.claritylab.carplaycoexistence/.DecoderCoexistenceService --es action STOP
```

If the service does not finish promptly or ADB reports failure, force-stop only this package:

```sh
adb -s <serial> shell am force-stop org.claritylab.carplaycoexistence
```

Then uninstall and verify removal:

```sh
adb -s <serial> uninstall org.claritylab.carplaycoexistence
adb -s <serial> shell pm path org.claritylab.carplaycoexistence
```

Expected uninstall success and no package path. Reconnect/reopen normal CarPlay if needed; confirm center picture, spoken guidance, and normal cluster view return. Preserve the sanitized event counts/score and human observation separately from raw private logcat. If package removal or baseline restoration is uncertain, stop; do not proceed to receiver work.

## Acceptance gate and limitations

The *decoder-only* candidate passes only with all 900 inputs spanning at least 59.75 seconds, at least 855 matched outputs after confirmed EOS drain, actual output format staying 800×480, actual codec `OMX.Nvidia.h264.decode`, no output gap above 250 ms after the first output, and no codec errors. Missing outputs, input deadline misses, a false/missing EOS, or incomplete duration fail. The separately observed center picture and spoken guidance must remain normal before/during/after. A passing result applies only to this fixture, codec, 800×480, 15 fps and tested state; it does not prove iAP2 guidance or a second CarPlay display.

The current host tests validate build packaging, signature, manifest, trace logic, and synthetic fixtures only. The service has not been launched on Android 4.2.2 or an emulator. Acceptance by the supervising Codex and a separate user authorization for the temporary install are still required before execution.
