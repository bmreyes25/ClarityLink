# Next action

**Continue Step 4 offline:** extend the targeted `jmcs` xref/decompilation for the already identified caller `AirPlayReceiverSessionSetup` (VA `0x2854e1`), wait helper `0x2a0480` and object at screen-session `+0x1418`, plus the decoder/output call graph from Honda `mc_ScreenStreamProcessData`/helper `0x8e70c`. The saved focused excerpts omit those callers and consumer edges. If static analysis cannot expose them, identify the precise runtime endpoint needed for a narrowly scoped passive observation. Do not invent a wire serializer or use the vehicle.

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
- research/carplay/screen-setup-input.md
- research/carplay/screen-thread-event.md
- research/carplay/video-callback-trace.md
- research/carplay/carplay-decoder.md
- research/carplay/primary-screen-end-to-end.md
- research/carplay/identification-schema.md
- src/carplay-session-model/model.py

Keep raw captures/APKs local and ignored. No framebuffer access or vehicle write is part of the next step.
