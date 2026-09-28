# Step 3 — Second H.264 decode/render path

**Status: offline decode plausibility demonstrated; render-Surface ownership and receiver coexistence remain unresolved.**

## Existing path evidence

- `extracted/system-vendor/system/vendor/media/mcs/j_config.xml:165–168` configures one CarPlay screen at 800×480 with a 30 FPS ceiling. This is the main-screen configuration; it does not advertise or bound a second display.
- The inspected `jmcs` ARM binary contains Stagefright `MediaCodec` references, including `CreateByType`, `configure`, `start`, `dequeueOutputBuffer`, `renderOutputBufferAndRelease`, and a Surface/SurfaceTextureClient configure signature. These prove the native image contains Android decode and render API references. The evidence currently available does **not** tie an exact `Surface` object or creation call site to the primary CarPlay display, nor show a second sink. Do not infer an independent cluster Surface from linked API names alone.
- `libcarplay_proxy.so` exports/contains the `ScreenStreamInitialize`, `ScreenStreamStart`, `ScreenStreamProcessData`, `ScreenStreamStop` callback family. Its Honda registration storage is a singleton (focused static disassembly in `research/native/receiver-multidisplay-audit.md`, function VA `0x1b7d`). This is a separate receiver/proxy concern from Android decoder capacity.
- The existing approved, temporary car-side capacity test (already completed and removed) ran two `OMX.Nvidia.h264.decode` instances concurrently at 800×480. Each delivered 28 of 30 output frames and EOS in the reported 1,973 ms; the run was marked `INCOMPLETE` against the later 30/30 threshold. The output was drained from decoder buffers; this was with CarPlay disconnected and did not test a display Surface, a CarPlay session, video stream negotiation, or audio coexistence. Evidence is in `research/probes/decoder-capacity/README.md` and `research/captures/20260925T150706Z-SESSION_FINDINGS.md`.

## Offline host replay

`tests/offline-decoder/run_dual_decode.py` launches two separate FFmpeg processes against the existing synthetic 800×480, 15 FPS, 30-frame H.264 fixture and verifies full frame counts/EOS. The fixture and FFmpeg binary are local ignored artifacts, not Git content. The test can be repeated with:

```sh
python3 -m unittest discover -s tests/offline-decoder -p 'test_*.py' -v
python3 tests/offline-decoder/run_dual_decode.py --json research/tmp/step-3/dual-decode.json
```

This is explicitly a macOS host/software replay test. It checks that the twin harness can process two independent streams and is **not** evidence about the car's NVIDIA hardware, Android SurfaceFlinger, a second Surface, or CarPlay integration.

## Finding and next evidence

The unit has demonstrated that its NVIDIA decoder can instantiate two concurrent decoder objects and produce most frames for a short controlled sample. That makes an additional decode path technically plausible, but is not enough to claim stable real-time rendering: the one missing frame per stream, short duration, disconnected CarPlay state, and output-buffer rather than Surface rendering leave the actual requirement open. The generic receiver appears to use a main 800×480 screen; a second H.264 stream would need separate negotiated setup, callback dispatch, decoder lifetime, and bounded cluster output. The next decisive test is the already-prepared, reviewed active-CarPlay coexistence probe; its car use remains a separate review/authorization checkpoint. The exact primary CarPlay `Surface` creation/bind call site also remains a targeted static-analysis question.
