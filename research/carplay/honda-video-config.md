# Honda ScreenStream VideoConfig — Step 37

## Honda-confirmed call chain

```text
AirPlayReceiverSessionScreen_ProcessFrames (0x287d8d)
  opcode byte header+4 == 1
  -> CFObjectSetPropertyData (0x2929e8), on ScreenStream [session+0x1ec]
  -> generic ScreenStream property callback
  -> mc_ScreenStreamSetProperty (0xbe6fc; Thumb symbol 0xbe6fd)
  -> CFDataGetBytePtr / CFDataGetLength
  -> H264ConvertAVCCtoAnnexBHeader (0x29f28c)
  -> converted SPS/PPS buffer + derived NAL width stored in stream context
```

This closes the type-1 consumer path. The helper name and field traversal are direct Honda evidence: it reads byte 4 for `(byte & 3) + 1`, byte 5 for `& 0x1f` SPS count, BE16 SPS lengths and bytes, then a PPS count and BE16 PPS lengths and bytes. It converts the parameter sets into `00 00 00 01`-prefixed output. It does **not** validate `configurationVersion`, profile, compatibility, or level; those first four bytes are retained by ClarityLink as raw fields only.

`mc_ScreenStreamSetProperty` first invokes the helper in sizing/metadata mode, allocates the output, then invokes it again to write the converted parameter sets. It stores the Annex-B bytes at callback context `+0x08`, size at `+0x0c`, and derived NAL length width at `+0x14`; it resets context flag `+0x10` to zero. The type-0 callback reads the same `+0x14` selector and, when `+0x10` is zero, prefixes the next produced video media buffer with the stored parameter-set bytes and sets the flag. Thus the opcode-1 config is not passed through `ScreenStreamProcessData` as an opaque config message; Honda converts/stores its parameter sets and prepends them to the next video output.

## Format classification and edges

**HONDA CONFIG FORMAT: AVCC-LIKE, high confidence.** The exact helper is named `H264ConvertAVCCtoAnnexBHeader` and implements the AVCDecoderConfigurationRecord array layout. Honda does not validate the version/profile bytes, so the parser intentionally does not claim full spec validation or SPS semantic parsing. Bytes after parsed PPS data are ignored by Honda's conversion output; ClarityLink preserves them as opaque trailing bytes.

The helper accepts a body ending immediately after its SPS list as a successful no-PPS case. This is an observed edge in Honda's function, even though a conventional avcC record includes a PPS-count byte. SPS/PPS contents are copied as opaque NAL data; Honda does not inspect NAL types in this helper. A subsequent config replaces the stored converted parameter-set buffer and selector and resets the one-time prepend flag. No explicit decoder flush or generation counter was found in this setter path.

The two header float32 values at offsets `+16` and `+20` are converted separately to CF double property updates before the body data-property update. Their destination property names and meanings are not resolved; do not label them width, height, or frame rate.

## Offline model

`src/claritylink-transport/video_config.py` parses only the proven avcC-like prefix and SPS/PPS length lists, records raw version/profile fields without validating them, derives the width, and preserves trailing bytes. `receiver_core.py` replaces config state on each non-empty opcode 1 and arranges for converted SPS/PPS to prefix the next successful type-0 media buffer. No real or captured configuration bytes are included.
