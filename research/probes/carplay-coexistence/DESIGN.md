# Active-CarPlay decoder probe — offline contract and candidate

Step 3 remains **in progress**. The historical approved APK and result are preserved under `research/probes/decoder-capacity/`: two simultaneous NVIDIA AVC decoders each produced 28/30 frames with CarPlay disconnected (93.33%), below the later 95% candidate threshold. Do not reinterpret that result.

The new candidate is a separate API-17 package, `org.claritylab.carplaycoexistence`, built from `src/org/claritylab/carplaycoexistence/DecoderCoexistenceService.java`. It is a foreground Android service with no Activity, no output `Surface`, no intent filter, and no requested permissions. A single explicit START action selects `OMX.Nvidia.h264.decode`, decodes one 800×480 H.264 stream at 15 fps for 900 submitted frames over 60 seconds, then queues EOS and drains for at most five more seconds. A persistent notification offers STOP. Its intended device writes are limited to temporary APK/app data and ordinary Android logcat; it does not open audio, network, Honda APIs, display APIs, root, or vehicle buses.

The historic 30-frame, two-second H.264 fixture is reused read-only and looped with monotonically increasing input PTS. Output is sent to codec output buffers, not a visible or hidden rendering surface. The service logs JSON events for actual codec identity, submitted and produced PTS plus monotonic arrival times, actual output format changes, input-buffer deadline misses, codec errors, EOS/drain, available/total memory snapshots, and thermal status (`unavailable` on this API level). Missing output PTS are calculated by the Mac scorer after trace extraction.

The numerical decoder-only gate is: all 900 planned inputs over at least 59.75 seconds; at least 95% outputs after drain (855/900); every actual reported output format remains 800×480; NVIDIA decoder identity; no output inter-frame gap above 250 ms after the first output; no codec error; and positively confirmed EOS. These are this project's engineering thresholds, not Apple requirements. CarPlay picture freeze and spoken guidance interruption are separate, mandatory human observations before, during, and after the run; the APK cannot measure them and the scorer always reports them as `UNOBSERVED`.

`evaluate_trace.py` validates event order and PTS provenance before scoring. `extract_logcat.py` extracts the service's JSON events from saved logcat text and applies the scorer without hand-editing the trace. It separates short-sample quality from the real decoder gate, so a synthetic 29/30 sample cannot pass: the full gate always requires all 900 inputs spanning at least 59.75 seconds. Tests cover 28/30 failure, the 29/30 sample-quality threshold, 855/900 over the full duration, short duration, long output gaps, unmatched or premature PTS, false EOS, wrong dimensions, software codec identity, errors, and log extraction.

## Current build evidence

The API-17 v1-signed APK is at the ignored local path `research/probes/carplay-coexistence/build/carplay-coexistence-probe-signed.apk`; do not commit or upload it. SHA-256: `59e7505e9b53fdb5bc6ee73ab10efcd9b377bc953a6e36dd9f6aaac42a5a7ea6`. The local ignored `build/BUILD-RECEIPT.json` records APK, source, manifest, and fixture hashes. Signature verification used the copied Google `apksig` tool. The source compiles against the repository's copied older Android API stub; the two deprecated notification APIs are retained because they exist on Android 4.2.2.

Rebuild and verify locally:

```sh
python3 research/probes/carplay-coexistence/build_probe.py
python3 -m unittest discover -s research/probes/carplay-coexistence -p 'test_*.py' -v
```

The current test result is 19 tests passed. Two consecutive same-machine builds with the same ignored local disposable key produced the same APK hash. A fresh checkout creates its own key, so its signed APK hash must be reviewed anew. These are host-side build/package/scorer tests, not an Android runtime test. No Android emulator/device run has validated this service's runtime, codec output-buffer behavior, service start, 60-second scheduling, or cleanup. Thus Step 3's artifact is **prepared for independent review**, not ready for on-car use until that review accepts the exact source/hash and run card. No ADB/device command was run while preparing it.
