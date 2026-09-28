# CarPlay decoder and output trace

**Verdict: native H.264/MediaCodec machinery is present in `jmcs`; its ownership and connection to the screen callback/output target remain unproven.**

The offline callback trace now establishes framed-data handling and a callback dispatch from helper `0x8e70c`. Two calls from `mc_ScreenStreamProcessData` to `0x8ea18` are also visible. Neither call can yet be joined to the H.264 pipeline through an evidence-backed callback or object pointer.

The `jmcs` ELF contains H.264 strings/helpers (`h264AVCC`, `h264AnnexB`, `H264ConvertAVCCtoAnnexBHeader`, `H264GetNextNALUnit`, `create_h264_pipeline`, `handle_h264_stream_source`) and imported Android `MediaCodec` methods including `CreateByType`, `configure`, `start`, input/output-buffer operations, and `renderOutputBufferAndRelease`. These imports and helper names establish a plausible codec path in the binary, not that it is the CarPlay ScreenStream consumer traced here. The imported configure signature accepts a `SurfaceTextureClient` smart pointer, but no particular CarPlay output object or target binding is established.

| Item | Result |
|---|---|
| Screen callback | `mc_ScreenStreamProcessData` at `0xbee91` |
| Framing/helper boundary | helper `0x8e70c`, then custom indirect callback through object `+0x10`; callback also calls `0x8ea18` twice |
| H.264 handling | H.264/AVCC/Annex-B code exists in same ELF; callback linkage remains unknown |
| Decoder creation API | Android `MediaCodec` APIs imported; CarPlay decoder constructor/object assignment not recovered |
| Decoder owner/storage/cardinality | Unknown |
| Codec config and dimensions | Unknown for this callback path |
| Start/stop/destroy | MediaCodec imports present, but per-session calls not linked to callback |
| Output target | MediaCodec `configure` type signature mentions `SurfaceTextureClient`; actual CarPlay instance/Surface creation/binding unknown |
| Two decoder/output objects | Unknown |

**First confirmed video function:** none yet at the traced CarPlay callback edge. **Format:** H.264 is high-confidence as a local native capability, not yet proven at this particular callback. **Output Surface:** unknown. The precise blocker is a callback/object xref that joins `mc_ScreenStreamProcessData` or its indirect dispatch target to `create_h264_pipeline`/MediaCodec configure and its output-target construction.
