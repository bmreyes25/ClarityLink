# Step 42K — actual decoded frame in the offline visual twin

**Classification:** Offline implementation; all generated media and frame values are `SYNTHETIC_TEST_VALUE`.

## Result

The hypothetical Display 1 panel now shows the pixels from the exact `DecodedFrame` accepted by the modeled ScreenStream pipeline's renderer mock:

`synthetic testsrc2 → H.264 → synthetic ScreenStream opcode 1/0 → parser → VideoConfig → AVCC-to-Annex-B → FFmpeg decode → RGBA → Display 1 mock → ephemeral PNG → browser`

The PNG encoder uses Python standard-library `struct` and `zlib`. Its runtime output is ignored at `demo/type111/runtime/type111-frame.png`; tracked `replay-data.json` stores only metadata. The metadata identifies `screenstream_synthetic_decode`, 320×180 RGBA8888, 230,400 source bytes, SHA-256 of the raw RGBA, and `SYNTHETIC_TEST_VALUE`. The HTML loads the asset only in Hypothetical Type111 mode, checks natural dimensions, preserves aspect ratio, and labels it “ACTUAL DECODED SYNTHETIC FRAME” with “Not Honda output · Not CarPlay content · Offline test fixture.”

Strict Honda mode remains unchanged: stock Type110 is active, Type111 is skipped, and no secondary frame is shown. If the PNG is absent or fails to load, the schematic is explicitly labeled as fallback. The exporter clears prior runtime artifacts before every run, so a failed generation cannot expose an old success image.

## Verification

- Real local command `python3 src/claritylink-sim/export_visual_demo.py --screenstream-h264`: passed with FFmpeg 9.0.2/libx264; wrote 320×180 PNG from the renderer-accepted RGBA frame.
- Provenance tests unpack PNG IDAT and compare decoded RGBA bytes and SHA-256 with the source frame.
- Failure checks cover invalid RGBA size, artifact write failure, missing artifact fallback, and cleanup of prior successful files before a failed generation.
- Existing ScreenStream tests retain Type110 and synthetic audio snapshots; strict-mode tests keep the secondary frame absent.
- `demo/type111/runtime/` is Git-ignored; no generated PNG/H.264/RGBA data is staged.
- Canonical local suite: 224 passed, 4 skipped; self-locator smoke: 3 passed; contract-only JavaScript checks and Type111 failure twin passed; inline demo JavaScript syntax check passed; `git diff --check` passed.

## Decision gate

| Gate | Result |
|---|---|
| ScreenStream fixture and host H.264 decode | PASS |
| Decoded RGBA to Display 1 mock | PASS |
| Actual decoded pixels in local visual demo | PASS |
| Pixel provenance | PASS |
| Strict Honda mode / Type110 / audio preservation | PASS |
| Stale artifact protection | PASS |
| Generated media committed | NO |
| Offline digital twin | READY |
| Live Type111 / jmcs integration / ExternalDisplay live render | NOT READY |
| LD_PRELOAD | PARKED |

The test uses synthetic media and a mock renderer only. It does not establish Honda Type111 wire compatibility, jmcs loadability, or a real ExternalDisplay handoff. The next offline Honda-specific task is the `/info` differential audit against the source-pinned display descriptor prior art.
