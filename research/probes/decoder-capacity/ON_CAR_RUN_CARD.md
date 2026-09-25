# Parked decoder probe: exact change and rollback

**Executed once on 2026-09-25 with user approval; APK removed.** This card remains the exact procedure for any future repeat. The car must be parked. Do not run while driving or while any warning needs attention. The signed APK and its [source/fixture/manifest](README.md) are reviewable on the Mac first.

## Exact temporary vehicle change

`adb install` adds one package, `org.claritylab.decoderprobe`, under Android `/data/app` and may create its normal private app-data directory. Launching it opens a center-screen Activity. Tapping its one- or two-stream button allocates codec instances, decodes the bundled test clip for at most seven seconds, and writes ordinary `ClarityDecoderProbe` logcat lines. It has no permissions and makes no call to Honda, cluster, audio, network, root, or vehicle bus APIs. The Activity does temporarily take the center-screen foreground, so this card tests decoder capacity **with CarPlay disconnected**, not simultaneous visible CarPlay.

## Preflight on the Mac

1. Build and verify as documented in [README.md](README.md).
2. Confirm the final APK SHA-256 matches `PROBE-MANIFEST.json`. If the APK was rebuilt, update that manifest and review the new hash before installing.
3. Confirm the car's Wi-Fi ADB address and `adb devices` status. Confirm this package is not already installed with `adb shell pm path org.claritylab.decoderprobe` (expected: no path).
4. Disconnect the iPhone from CarPlay for the first test. Leave Honda Hack casting off.

## Run, once authorized for the vehicle write

Use the current ADB serial in place of `<serial>` and a dated capture directory under `research/captures/`:

```sh
adb -s <serial> install research/probes/decoder-capacity/build/decoder-probe-signed.apk
adb -s <serial> shell am start -n org.claritylab.decoderprobe/.DecoderCapacityProbeActivity
```

On the center screen, tap **Decode one stream** and wait for `RESULT`; then tap **Decode two streams** and wait for `RESULT`. Each run is bounded to seven seconds. Capture logs without clearing them:

```sh
adb -s <serial> logcat -v threadtime -d ClarityDecoderProbe:I '*:S'
```

Record both codec names, 800×480 output formats, 30 output frames per stream, elapsed times, EOS, and resource-release messages. A `PASS` from a software codec is not evidence about NVIDIA's hardware decoder. A failed run is evidence about this fixture and state only.

## Stop and rollback

```sh
adb -s <serial> shell am force-stop org.claritylab.decoderprobe
adb -s <serial> uninstall org.claritylab.decoderprobe
adb -s <serial> shell pm path org.claritylab.decoderprobe
```

The last command should return no package path. Android's normal uninstall removes package data; a direct app-data filesystem check may be permission-denied and should be reported as such. Reconnect the iPhone normally and confirm center CarPlay picture and spoken Apple Maps guidance are back to the prior baseline. If the app stalls, force-stop it, then uninstall. If ADB is unavailable, stop testing and perform the car's ordinary parked power cycle before reconnecting CarPlay; do not try a firmware flash or remount. Do not proceed to any receiver patch based on this probe alone.
