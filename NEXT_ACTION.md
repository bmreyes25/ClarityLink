# Next action

**Continue Step 4 offline:** resolve which concrete `mc_stream_sink_ifc` table is linked to the CarPlay ScreenStream. DWARF confirms slot +0x14 is `process_data`, but the active constructor/registration and backend target remain unknown. Trace that assignment through `mc_stream_link`/media-framework construction; only then follow its real callees toward H.264, MediaCodec configuration, and the output Surface. In parallel, recover the port dictionary key/destination and reconcile Setup +0x2b4 with `_ScreenThread` context +0x1418.

Do not use the vehicle or start a runtime trace yet. See `step-reports/13-media-vtable-decoder.md`, `research/carplay/media-vtable.md`, and `research/carplay/primary-object-ownership.md`.

Raw captures, APKs, firmware, forensic images, and vendor binaries stay local and ignored. No model implementation or vehicle work is part of the next offline slice.
