# Synthetic Type111 visual demo

The static local page contrasts stock-shaped center Display 0 with a hypothetical Type111 Display 1. It uses no remote services. The visible secondary image, when generated, is the exact RGBA frame accepted by the mock renderer after the synthetic ScreenStream parser and FFmpeg decoder; it is not Honda output, CarPlay content, or a map.

From the repository root, regenerate the synthetic frame and metadata, then serve the page:

```sh
python3 src/claritylink-sim/export_visual_demo.py --screenstream-h264
python3 -m http.server 8000 --bind 127.0.0.1 --directory demo/type111
```

Open `http://localhost:8000` and select **Hypothetical Type111**. The page displays `demo/type111/runtime/type111-frame.png` inside the Display 1 mock only after the image loads at the recorded dimensions. It preserves aspect ratio with letterboxing. The metadata in `replay-data.json` records width, height, RGBA byte count, pixel SHA-256, and `SYNTHETIC_TEST_VALUE`. The runtime PNG and sidecar metadata are ignored by Git and are generated on demand; no frame bytes or base64 are stored in tracked JSON.

The command removes any prior runtime image before starting. A missing decoder, failed decode, renderer rejection, or artifact-write failure leaves no old success image behind and records a schematic fallback reason. Running the exporter without `--screenstream-h264` also clears the generated image, so the page cannot silently show a stale frame.

**Strict Honda** continues to show Type110 active and no secondary frame. The evidence ledger, timeline, unknown register, and all live readiness gates remain visible in both modes. `HONDA_CONFIRMED` refers only to recovered Honda Type110/unsupported-Type111 behavior; `MHI2_DERIVED_HYPOTHESIS` is external prior art; generated pixels/values are `SYNTHETIC_TEST_VALUE`; unproven Honda behavior remains `UNKNOWN`.

The synthetic fixture is generated in memory as `testsrc2` H.264, packed into the modeled plaintext ScreenStream test envelope, parsed as VideoConfig and AVCC, normalized to Annex-B, decoded to 320×180 RGBA, and submitted to mock Display 1. No H.264 or decoded media is retained in Git. This validates only the offline test pipeline; Honda Type111 framing/security, jmcs integration, and real ExternalDisplay output remain unproven. If FFmpeg is unavailable, the command reports failure and the page uses the explicit schematic fallback.
