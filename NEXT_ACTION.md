# Next action

**Prove the exact registry entry that wins for `"CarPlay Screen"`.** Continue from [Step 16](step-reports/16-carplay-registration-match.md): trace relevant `devmgr_app_register` callers and their interface initializers, identify comparator candidates and evaluate the exact key, then follow the proven interface slot +4 attach callback to sink construction and `process_data`. Continue toward H.264, MediaCodec, and Surface only from that callback.

Do not use the vehicle or ADB. Do not implement Display B or infer registration based on nearby strings. The generic lookup and current evidence limits are in [device-registration.md](research/carplay/device-registration.md), [mc-dev-attach.md](research/carplay/mc-dev-attach.md), and [primary-screen-end-to-end.md](research/carplay/primary-screen-end-to-end.md).

Raw captures, APKs, firmware, forensic images, vendor binaries, and decompiler databases stay local and ignored. No model implementation or vehicle work is part of the next offline slice.
