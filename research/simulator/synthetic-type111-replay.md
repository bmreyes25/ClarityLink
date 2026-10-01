# Synthetic Type111 cluster replay

Canonical scenario: synthetic_type111_cluster_replay. Entry point: src/claritylink-sim/synthetic_type111_replay.py. Integration tests: tests/integration/test_synthetic_type111_replay.py.

## Replay

1. Start a synthetic CarPlay session and preserve a stock-shaped Type110/audio response.
2. Run the existing Setup interposer, which calls its stock delegate first with the original request.
3. Strict Honda mode returns stock only. Hypothetical mode gates on session/Type110, advertised capability, descriptor, stream fields, synthetic security placeholder, renderer availability and explicit unknowns.
4. In hypothetical mode only, append a candidate Type111 response built with the existing prior-art clone profile. Its response strategy is tagged MHI2_DERIVED_HYPOTHESIS; IDs and ports are synthetic. The descriptor UUID is synthetic and uncorrelated.
5. A fake listener accepts a synthetic client. The receiver parses a synthetic 128-byte opcode-1 header and avcC-like config, then an opcode-0 body. This reuses the Type110-informed ScreenStream/config/H.264 model; Type111 compatibility is not asserted.
6. The existing extractor emits an Annex-B access unit. No H.264 decoder exists. A deterministic RGBA test-pattern frame is generated after successful extraction and submitted to the Display 1 mock. The frame is not decoded from the H.264 bytes.
7. Type111 teardown closes the mock listener, renderer and synthetic secret placeholders. A snapshot asserts the stock Type110 response/request, center state and audio remain unchanged.
8. Full-session teardown is represented separately and clears both stream states, renderer and audio.

## Output status

- VIDEO_HANDOFF_MODE: SYNTHETIC_FRAME_SOURCE
- Raw ScreenStream timestamp: retained from synthetic header; units are not promoted.
- Display frame PTS: generated from deterministic synthetic replay time.
- Display 1: mock target 800x480; no Android composition.
- Safety overlay: UNKNOWN_NOT_RENDERED_BY_MOCK.
- Crop/mask: UNKNOWN.
- Type111 keys: not derived; placeholder bytes are synthetic, held in SecretBytes by the existing offline interposer and cleared on teardown. Receiver runs with crypto disabled.

## Evidence separation

Honda-confirmed semantics are limited to stock Setup ownership/Type110 field shapes and stock unsupported Type111 behavior. The Setup response strategy is MHI2-derived hypothesis. IDs, ports, descriptor and bodies are generated synthetic test values. Honda Type111 schema, display correlation, key/IV derivation, opcode semantics, phone acceptance and real render handoff remain unknown.

The replay proves internal model composition and state invariants only.

Step 42F's static visual demo reads a generated summary of this replay in both modes. It presents a center placeholder, a strict-mode empty secondary view or hypothetical-mode SVG illustration, evidence ledger, unknown register, and the semantic timeline. The SVG is a synthetic schematic chosen when the replay reports renderer submission; it is not decoded H.264. See `research/simulator/visual-cluster-demo.md` and `demo/type111/README.md`.

Step 42G adds an optional FFmpeg CLI host decoder and synthetic in-memory H.264 generator. The replay fixture remains parser-only and is never presented to the decoder as valid media. This environment has no FFmpeg, so the real decode test skips; visual output explicitly reports the pattern fallback and decoder status. See `research/simulator/host-h264-decode-stage.md`.

Step 42H rechecked the host and added a capability probe. FFmpeg, libx264, H.264 decoder, and RGBA output are unavailable, so no valid H.264 media or decoded RGBA frame was generated. Annex-B parser tests still pass on synthetic parser values; this does not mean the replay contains decodable H.264.

Step 42I ran a separate synthetic FFmpeg validation: generated test pattern → libx264 Annex-B → host decoder → validated 320×180 RGBA frame → mock Display 1. The parser-shaped replay access unit remains untouched and is still not decoded. The separate success is recorded in `demo/type111/replay-data.json` and is labeled synthetic, not Honda/CarPlay.

Step 42J builds a separate valid media-backed transport fixture at test time: generated Annex-B is split into SPS/PPS and VCL NALs, converted to a synthetic avcC config plus four-byte AVCC frame, and wrapped in plaintext synthetic opcode-1/0 ScreenStream envelopes. The current Type110-informed parser emits config and Annex-B events; the actual Annex-B is then decoded by FFmpeg and submitted to mock Display 1. The visual JSON records `HOST-DECODED SYNTHETIC H264 VIA SCREENSTREAM FIXTURE` after full success. This validates the reusable parser/decoder composition with synthetic bytes only; the canonical hypothetical Type111 request/response remains MHI2-derived or synthetic and is not asserted to be a Honda wire implementation. Real Type111 crypto, framing, correlation, and ExternalDisplay integration remain unknown.

Step 42K extends the same path without introducing a parallel frame generator: the fixture's renderer-accepted `DecodedFrame` is SHA-256 recorded and encoded as an ephemeral PNG for the local demo. This presentation artifact is checked against the source RGBA pixels in tests. It remains `SYNTHETIC_TEST_VALUE`; strict Honda mode has no Type111 frame and all live integration gates remain closed.
