# Step 42I — real synthetic H.264 decode on Mac

Date: 2026-09-30
Scope: offline synthetic media validation
Base: `c4225ae`

## Host tooling

FFmpeg was already installed at `/opt/homebrew/bin/ffmpeg`; no Homebrew installation was needed. Version is 9.0.2. `ffprobe` 9.0.2 is also available. The build reports libx264 and VideoToolbox H.264 encoders, an H.264 decoder, and RGBA pixel format output. Python AV, OpenCV, imageio, imageio-ffmpeg, and Pillow remain absent and were not needed.

## Real encode, decode, and renderer result

Ran the exact unit test:

```sh
python3 -m unittest -v tests.sim.test_host_h264_decoder.HostH264DecoderTests.test_real_synthetic_encode_then_host_decode
```

It passed and actually generated an in-memory synthetic `testsrc2` 320×180 frame, encoded it with FFmpeg/libx264 to Annex-B H.264, decoded it through `FfmpegCliDecoder`, validated one RGBA frame with 230,400 bytes and the synthetic 1,000,000,000 ns timestamp, then submitted it to mock Display 1. Nothing was written as media to disk. The generated H.264 output was 7,877 bytes for the demo metadata run. No Honda/iPhone media, capture, key, or firmware was used.

The test executed these FFmpeg argument sequences (using `/opt/homebrew/bin/ffmpeg`):

```text
ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i testsrc2=size=320x180:rate=1 -frames:v 1 -an -c:v libx264 -profile:v baseline -preset ultrafast -tune zerolatency -pix_fmt yuv420p -f h264 pipe:1
ffmpeg -nostdin -hide_banner -loglevel error -threads 1 -max_pixels 2073600 -f h264 -i pipe:0 -frames:v 1 -vf scale=320:180 -f rawvideo -pix_fmt rgba pipe:1
```

The first command emits Annex-B to memory. The second consumes that in-memory byte string through stdin and emits exactly one raw RGBA frame to memory.

The existing ScreenStream-shaped replay fixture remains parser-only and is still not passed to FFmpeg. The synthetic media decode is a separate validation track, not proof of Honda Type111 payload compatibility. The visual demo metadata now records `HOST-DECODED SYNTHETIC H264`, labels the validation `SYNTHETIC_TEST_VALUE`, and keeps Honda/live gates closed. The illustration itself remains a schematic SVG; no raw decoded pixels or encoded media are committed.

## Decision gate

FFMPEG AVAILABLE: YES
FFPROBE AVAILABLE: YES
LIBX264 AVAILABLE: YES
H264 DECODER AVAILABLE: YES
RGBA OUTPUT AVAILABLE: YES
FFMPEG INSTALL: SKIPPED (already installed; no install attempted)
SYNTHETIC MEDIA: GENERATED (in memory only)
H264 ENCODE: PASS
DIGITAL TWIN VIDEO INPUT: ANNEXB
HOST DECODE: PASS
DECODED FRAME TO RENDERER: PASS (mock Display 1)
CENTER DISPLAY PRESERVATION: PASS
AUDIO INVARIANTS: PASS
VISUAL DEMO DECODE STATUS: HOST_DECODED_SYNTHETIC_H264
OFFLINE DIGITAL TWIN: READY
SYNTHETIC TYPE111 DEMO: READY
JMCS NO-OP TEST: NOT READY
EXTERNALDISPLAY LIVE RENDER TEST: NOT READY
TYPE111 LIVE WORK: NOT READY
LD_PRELOAD STATUS: PARKED

BIGGEST BLOCKER: Honda Type111 media/schema/security and the actual jmcs/ExternalDisplay integration seams remain unproven; this test only validates the host's synthetic H.264 path.

## Verification

Decoder/replay/demo suite: 19 passed. Full offline suites were rerun: negotiation 18, transport 29, display/session 12, integration 12, simulator Python 31 (6 optional skips), simulator JavaScript 11, Type111 failure twin passed, locator smoke 3, and interposer 14 via standard-library assertion shim. `git diff --check` passed.

## Next

Build a synthetic ScreenStream integration fixture from generated H.264 by deriving synthetic VideoConfig and AVCC length-prefix fields, then prove ScreenStream parsing → Annex-B extraction → FFmpeg decode → mock rendering. Keep those synthetic values separate from Honda facts and keep all live tests gated.
