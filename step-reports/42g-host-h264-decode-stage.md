# Step 42G — host H.264 decode stage

Date: 2026-09-30
Scope: offline host decoder adapter and synthetic-only twin
Base: `dbbacd1`

## Result

Added an optional FFmpeg CLI decoder adapter with bounded Annex-B input, SPS/PPS validation, explicit dimensions/timestamp, a short timeout, one-frame RGBA output, and validation through the existing renderer `DecodedFrame` model. Added an in-memory FFmpeg/libx264 synthetic test-pattern generator. No media file is stored by the generator.

The current environment has no `ffmpeg`, `ffprobe`, PyAV, OpenCV, imageio, or Pillow. The real encode/decode test was skipped with the explicit reason “ffmpeg absent; real synthetic encode/decode not run.” The Step 42E AVCC-like fixture is intentionally invalid as a decodable stream and is never passed to FFmpeg. Adapter wiring was tested with a fake process response; that is not counted as real decode.

The visual twin now exposes decode status and, here, labels the hypothetical picture `SYNTHETIC FRAME SOURCE — HOST DECODER UNAVAILABLE`. If FFmpeg is installed but this replay's non-decodable fixture remains in use, the UI reports that valid H.264 test media was not generated. The established pattern fallback continues to submit to the renderer mock. Strict mode remains Type111-skipped; hypothetical mode remains synthetic only.

## Verification

- Host decoder adapter + visual demo + replay focused tests: 16 passed, 1 skipped (FFmpeg absent).
- No synthetic H.264 media was generated in this environment.
- Host decoder mock-output path produced a validated synthetic RGBA frame and submitted it to mock Display 1.
- Existing suites: negotiation 18; transport 29; display/session 12; integration 11; simulator Python 31 with 6 optional skips; simulator JavaScript 11; interposer 14 via standard-library `pytest.raises` shim; locator smoke 3.
- Live Type111, jmcs no-op, and ExternalDisplay live rendering remain NOT READY.
- `git diff --check`: passed.

## Decision gate

HOST H264 DECODER: OPTIONAL
DECODER BACKEND: MOCK_ONLY on this host (FFmpeg CLI adapter implemented; executable unavailable)
SYNTHETIC H264 INPUT: NOT READY (generator available only when FFmpeg/libx264 exist)
AVCC TO ANNEXB: PASS (existing synthetic parser test)
HOST DECODE: SKIPPED (FFmpeg absent)
DECODED FRAME TO RENDERER: PASS for fake adapter output; actual decode path SKIPPED
CENTER DISPLAY PRESERVATION: PASS (existing replay invariant test)
AUDIO INVARIANTS: PASS (existing replay invariant test)
DECODE FAILURE ISOLATION: PASS (unavailable, invalid, timeout, and zero-frame results produce no frame; replay asserts Type110/audio state unchanged)
VISUAL DEMO UPDATED: YES
EVIDENCE LABELS: PASS
OFFLINE DIGITAL TWIN: READY
SYNTHETIC TYPE111 DEMO: READY with explicit pattern fallback
JMCS NO-OP TEST: NOT READY
EXTERNALDISPLAY LIVE RENDER TEST: NOT READY
TYPE111 LIVE WORK: NOT READY
LD_PRELOAD STATUS: PARKED

BIGGEST BLOCKER: this host has no FFmpeg executable, so there is no actual host H.264 decode result yet.

## Next

Run the optional synthetic encode/decode test in a host environment with FFmpeg and libx264 available, preserving all live integration gates. Then wire only successfully decoded synthetic frames into the twin renderer path.
