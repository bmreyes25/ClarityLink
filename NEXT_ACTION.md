# Next action

**Continue Step 4 offline:** locate the caller/input producer for `AirPlayReceiverSessionScreen_Setup` and the event/response that wakes `_ScreenThread`; trace those edges to the transport parser and identify the concrete `mc_ScreenStreamProcessData` decoder/output consumer. Current focused artifacts stop before transport and after generic stream dispatch. If those static edges are absent, first identify the runtime endpoint needed for a narrowly scoped passive observation. Do not invent a wire serializer or use the vehicle.

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
- research/carplay/identification-schema.md
- src/carplay-session-model/model.py

Keep raw captures/APKs local and ignored. No framebuffer access or vehicle write is part of the next step.
