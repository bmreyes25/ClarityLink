# Next action

**Resolve the matching `CarPlay Screen` device registration.** The active call is now confirmed at `mc_ScreenStreamStart` (`0xBDC06`) with exact name `"CarPlay Screen"`; `mc_dev_attach` enters `devmgr_dev_attach` -> `devmgr_dev_alloc` -> `dev_attach`. Decode the lookup in `dev_attach` (`0x81FF4`) and the narrowly relevant registry population/registration path, then follow the matched callback to concrete sink construction and its +0x14 `process_data` target. Continue from that target toward H.264, MediaCodec, and Surface.

Do not use the vehicle yet. The precise static gap and current evidence are in `step-reports/15-carplay-device-attach.md`, `research/carplay/device-manager.md`, and `research/carplay/active-carplay-sink.md`.

Raw captures, APKs, firmware, forensic images, and vendor binaries stay local and ignored. No model implementation or vehicle work is part of the next offline slice.
