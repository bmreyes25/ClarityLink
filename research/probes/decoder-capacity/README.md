# API-17 AVC decoder diagnostic — built and run once, then removed

The signed diagnostic APK is `build/decoder-probe-signed.apk` (current SHA-256 `162cae47046ad144946c3fc889297c9f6f62c037ece6c3e45b35d5229db3aac7`). It was temporarily installed on the Clarity during the approved September 25 parked test, then removed. The decoded final manifest has package `org.claritylab.decoderprobe`, `minSdkVersion=17`, `targetSdkVersion=17`, and **no requested permissions**. Its bundled MP4 is stored uncompressed, so Android's `MediaExtractor` can open the asset without copying it to vehicle storage. Google `apksig` verified its v1 signature for Android API 17.

The fixed fixture is a two-second, 30-frame, 800×480, 15 fps H.264 Constrained Baseline clip at approximately 519 kb/s, generated from FFmpeg's `testsrc2`; its SHA-256 is `1a1f70418ad0df9210822ee03a44c313049879699ea75d9df3517dbcc42c04cc`. The app offers one-stream and two-stream buttons. Both `MediaCodec` instances are started concurrently and fed the same clip at its nominal frame times. It logs codec name, elapsed time, output format, decoded output-frame counts, EOS state, result, and resource-release messages under `ClarityDecoderProbe`. It prefers `OMX.Nvidia.h264.decode`; a software fallback is clearly reported and does not pass the NVIDIA hardware gate. The run has a seven-second upper bound and releases every created codec, extractor, and Surface in a `finally` path.

This measures actual decoded output buffers under a controlled fixture. The [parked result](../../captures/20260925T150706Z-SESSION_FINDINGS.md) was 28/30 800×480 output frames and EOS from each of two simultaneous `OMX.Nvidia.h264.decode` instances in 1973 ms. Its strict result was `INCOMPLETE`; nevertheless, both instances demonstrably decoded frames concurrently. The initial build hit an Android 4.2 `ByteBuffer.clear` linkage error; the current APK calls `Buffer.clear` and produced these outputs. This test does **not** prove that the factory receiver can negotiate two CarPlay streams, nor that full-screen CarPlay stays visible while this foreground Activity runs. A later separate background probe would be needed for a clean CarPlay-coexistence measurement. The tiny 32×32 center-screen Surface views receive an 800×480 configured decoder output; the test checks the decoder's reported output dimensions, not the displayed widget size.

Build reproducibly from inside `clarity-analysis`:

```sh
python3 research/probes/decoder-capacity/build_probe.py
python3 -m unittest discover -s research/probes/decoder-capacity -p 'test_*.py'
```

The build uses the copied Android API 17 compile stub, ECJ, Google's D8 and `apksig` jars, Apktool's AAPT2 packaging, and a local disposable diagnostic signing key. All inputs, tools, and outputs stay under `clarity-analysis`. The 17.4 MB D8 jar and 496 KB apksig jar came from Google's Android Maven repository. The MP4 generator is the `imageio-ffmpeg` 0.6.0 package under `research/tools/python`. Source, manifest, asset, and APK hashes are in `PROBE-MANIFEST.json`.

Installing this APK writes `/data/app` and app data on the car, and briefly reserves video decoder resources. It was uninstalled after the approved test; package and app-data absence plus normal CarPlay/voice were verified. Review the exact [parked run and rollback card](ON_CAR_RUN_CARD.md) before any repeat install. The measured two-stream output is only a decoder-capacity prerequisite for native multi-display CarPlay.
