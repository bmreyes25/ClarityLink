# Next action

**Continue Step 4 offline:** the local `jmcs` ELF now confirms `AirPlayReceiverSessionSetup` creates a TCP listening socket at outer `+0x1418`; `_ScreenThread` waits with `select()`/`accept()` through `SocketAccept` (`0x2a0480`). Setup input is a CFL dictionary lookup through `0x294598`, though key semantics remain unknown. The media callback reaches framed-data helper `0x8e70c`, but no decoder/output edge is yet proven. Next, trace the caller/parser above `AirPlayReceiverSessionSetup`, determine the listener port/address and accepted request framing, and follow callback indirect targets to the H.264/MediaCodec setup and output Surface. A single-flow passive capture is helpful after the endpoint/port is known; do not use broad USB capture or invent fields.

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
