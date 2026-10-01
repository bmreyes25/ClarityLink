# Synthetic Type111 visual demo

This static page visualizes the Step 42E digital-twin replay. It uses only Python's standard library to produce the JSON summary and a local browser to display it. It makes no network requests beyond the local HTTP server and contains no Honda captures, keys, or firmware assets.

From the repository root, generate the data and start the local server:

```sh
python3 src/claritylink-sim/export_visual_demo.py
python3 -m http.server 8000 --bind 127.0.0.1 --directory demo/type111
```

Open `http://localhost:8000` in a browser. Choose **Strict Honda** to see Type110 active with no secondary frame, or **Hypothetical Type111** to see a schematic synthetic cluster pattern, replay status, and event timeline. Press Control-C in the terminal to stop the local server.

The data file is generated from `synthetic_type111_cluster_replay()` in both modes. It summarizes the existing replay events and state; it does not include media bytes, key/IV material, or captured protocol payloads. The map-like pattern is an inline SVG illustration shown only when the replay records a mock renderer submission. It is not an H.264 decode or Honda image.

Evidence labels mean:

- `HONDA_CONFIRMED`: recovered stock Type110 behavior and Honda's unsupported Type111 branch.
- `MHI2_DERIVED_HYPOTHESIS`: prior-art candidate response profile, not a Honda wire contract.
- `SYNTHETIC_TEST_VALUE`: generated ports, identifiers, state, timestamps, and illustration.
- `UNKNOWN`: Honda response/security/correlation details and live integration surfaces that remain unproven.

The page intentionally keeps unknowns visible. Live Type111, jmcs no-op loading, and real ExternalDisplay rendering remain not ready.

## Optional host H.264 decode

Step 42G adds an optional FFmpeg CLI decoder and in-memory synthetic test-pattern generator. Run `python3 -m unittest tests.sim.test_host_h264_decoder.HostH264DecoderTests.test_real_synthetic_encode_then_host_decode` to encode and decode one synthetic frame without writing media files. The local Mac passed this test with FFmpeg 9.0.2/libx264. To record the current local result into the static demo metadata, run `python3 src/claritylink-sim/export_visual_demo.py --decode-synthetic-h264`; without FFmpeg the unit test skips explicitly and the default page reports `SYNTHETIC FRAME SOURCE — HOST DECODER UNAVAILABLE`.

The canonical replay's H.264-like bytes are parser fixtures, not valid H.264, and are never passed to FFmpeg. The successful FFmpeg validation uses an independent generated `testsrc2` pattern, outputs Annex-B H.264, decodes it to RGBA, and submits it to the mock renderer. The visual SVG remains a schematic; the status documents the separate decoded-frame test. This is not Honda/CarPlay output. Honda Type111 media format and real ExternalDisplay handoff remain unproven; all live gates remain NOT READY.

## Optional ScreenStream fixture validation

Step 42J connects generated H.264 to the modeled transport path. Run `python3 src/claritylink-sim/export_visual_demo.py --screenstream-h264` to generate a test pattern in memory, extract its SPS/PPS and IDR NAL, build a synthetic avcC config and AVCC frame, wrap them as opcode 1 and opcode 0 ScreenStream messages, parse/extract/decode them, and submit the decoded RGBA frame to mock Display 1. No media bytes are written. The JSON reports `HOST-DECODED SYNTHETIC H264 VIA SCREENSTREAM FIXTURE` only when every stage passes. This plaintext synthetic envelope is a test model, not Honda protocol evidence; Honda Type111 crypto, response schema, stream correlation, and ExternalDisplay handoff remain unknown.
