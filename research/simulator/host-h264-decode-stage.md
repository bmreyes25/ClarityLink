# Host H.264 decode stage (Step 42G)

The twin now has an optional host decode adapter in `src/claritylink-sim/host_h264_decoder.py`. It accepts a bounded Annex-B access unit plus explicit dimensions/timestamp and, when FFmpeg is installed, requests one RGBA frame on stdout. The output is validated against the existing `DecodedFrame` contract before it can reach the Display 1 renderer mock. It uses argument arrays (no shell), a timeout, bounded input/dimensions, and does not persist media.

`generate_synthetic_h264()` can create one synthetic `testsrc2` frame through FFmpeg/libx264 into memory. No generated media is committed. Generation and decode are optional because this host has neither FFmpeg nor a Python video decoder; the real encode/decode test is explicitly skipped with that reason.

The Step 42E replay's AVCC-like bytes are parser fixtures, not a valid H.264 access unit. They are deliberately not sent to a real decoder. Consequently the canonical visual twin still uses the synthetic pattern fallback, and reports `HOST_DECODER_UNAVAILABLE` here. If FFmpeg exists elsewhere, it reports that the backend is available while still stating that no valid H.264 test media was generated/decoded by this replay. A fake subprocess test verifies adapter-to-frame-to-renderer wiring, but is not counted as actual decoding.

The decoder requires SPS and PPS NALs in Annex-B, one access unit, dimensions supplied by the caller, and emits one frame. This is only an offline test boundary. It does not establish Honda VideoConfig geometry, Honda Type111 framing, crypto, timing, or decoder compatibility. Type110 and audio isolation remain covered by the replay tests. Live Type111, jmcs no-op load, and ExternalDisplay output remain NOT READY.
