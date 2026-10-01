# Step 42J — valid synthetic H.264 through ScreenStream fixture

## Result

Generated a 320×180 `testsrc2` frame in memory with FFmpeg 9.0.2 and libx264, then routed that valid synthetic media through the modeled ScreenStream pipeline:

`Annex-B H.264 → SPS/PPS/VCL extraction → synthetic avcC → AVCC frame → opcode 1/0 envelopes → HondaScreenReceiverCore → AVCC-to-Annex-B → FFmpeg decode → RGBA DecodedFrame → Display 1 mock`

The encoder output was 7,877 bytes. It contained NAL types 5 (IDR), 6 (SEI), 7 (SPS), and 8 (PPS): one SPS, one PPS, and three VCL NALs in the selected access unit. The generated avcC-style config is 39 bytes and sets a four-byte NAL length. The AVCC frame body is 7,237 bytes. Synthetic ScreenStream packet sizes are 167 bytes for opcode 1 and 7,365 bytes for opcode 0, each including a 128-byte modeled header.

The host decoder returned a 320×180 RGBA frame (230,400 bytes), which the mock accepted on Display 1. The fixture labels its payload `SYNTHETIC_TEST_VALUE` and its envelope `PLAINTEXT_SYNTHETIC`; it bypasses Honda crypto and does not claim that the modeled header or config is Honda Type111 wire evidence. Type110 and synthetic audio invariants remained unchanged.

## Failure coverage

Tests reject missing SPS/PPS, malformed config, unsupported three-byte NAL length size, malformed AVCC NAL length, invalid H.264 decode, and rejected renderer frames. The parser's incomplete declared body is buffered until the missing bytes arrive; unknown opcodes are surfaced as unknown events. Failure cases preserve synthetic Type110/audio snapshots.

## Demo and limits

`demo/type111/replay-data.json` now records the complete ScreenStream-fixture validation. The hypothetical mode reports `HOST-DECODED SYNTHETIC H264 VIA SCREENSTREAM FIXTURE` only after parse, config, extraction, decode, and mock rendering all succeed. The page still shows a schematic cluster illustration, not the decoded pixel frame. It explicitly says the bytes are synthetic, not Honda output or real CarPlay frames; ExternalDisplay handoff and Honda Type111 schema, crypto, and display correlation remain unknown. All live gates remain NOT READY and LD_PRELOAD remains PARKED.

No generated video or RGBA file was retained. All media was generated and consumed in memory.

## Verification

The ScreenStream fixture suite and visual-demo integration tests passed, including actual FFmpeg/libx264 encode/decode. Results: negotiation 18; transport 29; session model 12; integration 13; simulator Python 13; offline decoder 1; locator smoke 3; simulator JavaScript 11; failure twin passed; interposer standard-library runner 14; `git diff --check` passed. The test run briefly caught a demo rebuild assertion that omitted the new screenstream metadata; the assertion was corrected and the full integration suite passed afterward.
