# Next action

**Resolve the indirect device/factory registration used by the CarPlay screen source.** `mc_stream_link` is confirmed as a generic endpoint linker; all its direct callers are PBS pipeline builders/helpers, and none is yet proven to construct the active screen sink. Trace the CarPlay screen's `mc_dev_attach` device identity through the relevant device-manager registration and attach callbacks until the sink argument/ops table is visible. Then follow its `process_data` method toward H.264, MediaCodec, and Surface.

Do not use the vehicle yet. The precise static gap and current evidence are in `step-reports/14-active-media-sink.md`, `research/carplay/mc-stream-link.md`, and `research/carplay/active-carplay-sink.md`.

Raw captures, APKs, firmware, forensic images, and vendor binaries stay local and ignored. No model implementation or vehicle work is part of the next offline slice.
