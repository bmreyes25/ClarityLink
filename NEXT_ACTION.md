# Next action

**Continue Step 4 offline:** trace the focused `jmcs` display/session setup and screen-stream entry points to determine whether the main-only `CopyDisplaysInfo` path or singleton `libcarplay_proxy` callback can be extended without changing the primary session. Record the exact call boundary and any missing request/response fields. Do not invent a wire serializer or use the vehicle.

Steps 1–3 are complete enough for protocol work. HondaHack's output path is traced; the renderer abstraction exists, while root acquisition, physical crop, and zero-copy remain deferred. Static analysis confirms one Honda `gMainScreen`, main-only display-info copy, and a singleton proxy callback. The offline two-display model exists, but cannot establish a genuine Display B session.

Current reports:

- research/hondahack/hondahack-display-path.md
- research/hondahack/hondahack-static-analysis.md
- research/hondahack/CLARITYLINK_OUTPUT_INTERFACE.md
- src/claritylink-renderer/
- research/carplay/second-display-session.md
- research/carplay/identification-schema.md
- src/carplay-session-model/model.py

Keep raw captures/APKs local and ignored. No framebuffer access or vehicle write is part of the next step.
