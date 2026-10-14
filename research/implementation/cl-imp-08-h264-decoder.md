# CL-IMP-08 — H.264 secondary decoder

## Implementation

- Added `Api17SurfaceH264Decoder`, an Android API16+ `MediaCodec` AVC decoder that targets a borrowed `Surface`. It validates even 2..4096 dimensions, positive session generations, increasing timestamps, Annex-B framing, a 2 MiB access-unit limit, a 64 KiB SPS/PPS limit, and 1..5000 ms synchronous decode deadlines.
- Codec configuration is submitted separately with the API17 codec-config buffer flag. The adapter submits one compressed access unit at a time, waits for and submits at most the first decoded output to its Surface, permits the codec's observed one-access-unit output delay, validates output timestamp ordering and dimensions, rejects stale generations, and recreates the codec on an explicitly newer generation/resolution reset.
- The adapter does not own or release its Surface. It clears codec and configuration state deterministically on close. Unknown/authenticated Type111 security is not implemented here; the adapter accepts clear lab fixture bytes only.
- Added an emulator-only Activity that creates separate Type110 and Type111 decoder instances and Surface owners, decodes independently colored synthetic fixtures, exercises a 32×32 to 64×64 reset, and verifies stale-generation rejection. The test reports Surface submission only and explicitly marks physical scanout unproven.
- The candidate APK remains disabled. The laboratory APK is only installed and removed inside the isolated API17 emulator harness.

## Validation evidence

- Synthetic H.264 fixtures decode with host FFmpeg and their PNG dimensions and SHA-256 values are recorded in `tests/fixtures/cl-imp-08/README.md`.
- `tools/compile_android_api17_java.sh`: passed against Android API17.
- `tools/run_cl_imp_03_emulator.sh --cl-imp-08-decoder`: passed on the isolated Android 4.2.2/API17 x86 emulator. Both independent decoders submitted one output frame each; the secondary decoder reset successfully from 32×32 to 64×64; emulator-only APK install/removal and overlay cleanup passed.
- `tests/offline-decoder/test_offline_decoder.py`: 1 passed, 1 skipped (optional ignored local FFmpeg capacity artifacts are absent).
- Full offline suite: 1,409 passed, 14 skipped. Repository health and `git diff --check` passed.

## Limits and follow-up

- Fixtures are generated synthetic color frames, not CarPlay or iPhone captures. No Apple authentication, Type111 transport, Honda delegation, Honda display admission, ARMv7 JNI/native decoder, or physical cluster scanout was exercised.
- The API17 emulator codec reports macroblock-padded output dimensions for cropped H.264 sizes. CL-IMP-08 fixtures therefore use exact macroblock-aligned dimensions; CL-IMP-09 must define a tested crop/viewport path before relying on arbitrary production resolutions.
- The static fixture extractor is not a complete production H.264 access-unit parser or RTP/transport depacketizer. Those remain explicit integration work.
- No Honda integration was enabled or contacted.
