# Next action

**Continue Step 4 offline:** use the exact local `jmcs` ELF and validated address map to resolve the linked media-object table created for the CarPlay ScreenStream. Trace `mc_stream_push_data` vtable slot `+0x14` back through `mc_stream_link`/media-framework construction, then follow its concrete target toward `android_mediacodec_process_data`, H.264 conversion, decoder configure, and Surface binding. Also resolve the `CFDictionarySetInt64` key and whether that dictionary value is externally advertised. Do not use the vehicle or start a runtime trace yet: static analysis recovered the accepted-fd `recv` path.

See `step-reports/12-jmcs-deep-slice.md`, `research/carplay/jmcs-address-map.md`, and `research/carplay/accepted-fd-dataflow.md`.

Raw captures, APKs, firmware, forensic images, and vendor binaries stay local and ignored. No model implementation or vehicle work is part of the next offline slice.
