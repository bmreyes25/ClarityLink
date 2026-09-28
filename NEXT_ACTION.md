# Next action

**Recover the missing offline native-analysis slice:** obtain the detailed `jmcs` disassembly or analysis project covering `ServerSocketOpen`, the post-accept reader/parser, and the assignments to the callback object's `+0x10` dispatch slot. Resolve the bind endpoint/advertisement and prove the accepted-fd-to-`mc_ScreenStreamProcessData` path first. In parallel within that same slice, follow the assigned media target toward the H.264/MediaCodec and Surface setup. Do not use the vehicle, reconnect ADB, modify firmware, construct packet bytes, or implement Display B. A short single-flow TCP capture becomes useful only after local endpoint recovery.

Steps 1–3 are complete enough for protocol work. HondaHack's output path is traced; the renderer abstraction exists, while root acquisition, physical crop, and zero-copy remain deferred. Static analysis confirms one Honda `gMainScreen`, main-only display-info copy, and a singleton proxy callback. The offline two-display model exists, but cannot establish a genuine Display B session.

Current reports:

- research/hondahack/hondahack-display-path.md
- research/hondahack/hondahack-static-analysis.md
- research/hondahack/CLARITYLINK_OUTPUT_INTERFACE.md
- src/claritylink-renderer/
- research/carplay/second-display-session.md
- research/carplay/screen-start-transport.md
- research/carplay/primary-screen-start-request.md
- research/carplay/video-stream-binding.md
- research/carplay/decoder-output-path.md
- research/carplay/display-b-interposer.md
- step-reports/08-screen-session-trace.md
- step-reports/09-control-and-decoder-trace.md
- research/carplay/control-plane-state-machine.md
- step-reports/10-control-media-breakthrough.md
- research/carplay/screen-setup-input.md
- research/carplay/screen-thread-event.md
- research/carplay/video-callback-trace.md
- research/carplay/carplay-decoder.md
- research/carplay/primary-screen-end-to-end.md
- research/carplay/identification-schema.md
- src/carplay-session-model/model.py

Keep raw captures/APKs local and ignored. No framebuffer access or vehicle write is part of the next step.
