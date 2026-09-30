# Step 42H — FFmpeg synthetic H.264 validation

Date: 2026-09-30
Scope: offline synthetic media only
Base: `0f3f2cd`

## Environment

- `ffmpeg`: unavailable (`command -v ffmpeg` found no executable)
- `ffprobe`: unavailable
- Python `av`, `cv2`, `imageio`, `imageio_ffmpeg`, and `PIL`: unavailable
- Capability probe result: FFmpeg, libx264, H.264 decoder, and RGBA output all unavailable
- No package was installed.

Because FFmpeg is absent, encoder/decoder tables could not be queried, no synthetic media was generated, and no external FFmpeg command ran. The test-time encode/decode test skipped with the reason `ffmpeg absent; real synthetic encode/decode not run`. Generated media is in-memory only when enabled; this run created none.

## Pipeline status

- Existing ScreenStream parser fixture -> Annex-B extraction: pass in the offline replay. The fixture is deliberately not valid H.264 and is not passed to FFmpeg.
- Valid synthetic source -> libx264 encode: skipped (FFmpeg/libx264 absent).
- Host decoder adapter: capability detection reports unavailable; mock-process adapter tests continue to verify bounded RGBA frame handoff, but do not count as real decoding.
- Decoded frame -> Display 1 renderer mock: skipped as an actual decoded frame; adapter wiring with mock RGBA output passes.
- Type110/audio preservation: pass in replay tests; the decode adapter does not own or mutate either state.
- Visual output remains `SYNTHETIC FRAME SOURCE — HOST DECODER UNAVAILABLE`.

## Decision gate

FFMPEG AVAILABLE: NO
LIBX264 AVAILABLE: NO
H264 DECODER AVAILABLE: NO
SYNTHETIC MEDIA: SKIPPED
H264 ENCODE: SKIPPED
DIGITAL TWIN VIDEO INPUT: SYNTHETIC_FRAME_ONLY
HOST DECODE: SKIPPED
DECODED FRAME TO RENDERER: SKIPPED (actual decode); mock adapter wiring PASS
CENTER DISPLAY PRESERVATION: PASS
AUDIO INVARIANTS: PASS
SKIP/FAILURE ISOLATION: PASS
VISUAL DEMO DECODE STATUS: SYNTHETIC_FRAME_SOURCE
OFFLINE DIGITAL TWIN: READY
SYNTHETIC TYPE111 DEMO: READY
JMCS NO-OP TEST: NOT READY
EXTERNALDISPLAY LIVE RENDER TEST: NOT READY
TYPE111 LIVE WORK: NOT READY
LD_PRELOAD STATUS: PARKED

BIGGEST BLOCKER: FFmpeg/libx264 is unavailable on this host, so no actual synthetic H.264 encode/decode could be run.

## Verification

The decoder/replay/demo tests passed with one explicit real-media skip. The full offline suites were rerun: negotiation 18, transport 29, display/session 12, integration 11, simulator Python 31 (6 optional skips), simulator JavaScript 11, failure twin, locator smoke, and interposer 14 via the standard-library assertion shim. `git diff --check` passed.

## Next action

Run `tests.sim.test_host_h264_decoder.HostH264DecoderTests.test_real_synthetic_encode_then_host_decode` on an offline host with FFmpeg, libx264, H.264 decode, and RGBA output. Do not change live readiness gates based on synthetic media success.
