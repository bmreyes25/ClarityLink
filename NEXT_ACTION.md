# Next action

**Continue Step 3 offline:** turn the existing renderer abstraction and API 17 View skeleton into the smallest executable ClarityLink output prototype supported by the HondaHack trace. Keep Honda's externaldisplay-root integration explicitly isolated behind an adapter, validate the API 17-compatible frame contract and lifecycle, and do not claim hardware output. After the offline prototype is reviewable, prepare one reversible parked-car renderer test. Do not use the vehicle during this offline task.

Step 2 is closed: HondaHack uses a regular View injected into Honda's ExternalDisplay window on Display 1 (800×480, layer stack 1). The host-side synthetic renderer and API 17 View skeleton already exist, but the latter does not yet acquire Honda's root or demonstrate device output. The exact physical Navigation viewport remains unknown and is deferred unless needed by the renderer.

Current reports:

- research/hondahack/hondahack-display-path.md
- research/hondahack/hondahack-static-analysis.md
- research/hondahack/CLARITYLINK_OUTPUT_INTERFACE.md
- src/claritylink-renderer/

Keep raw captures/APKs local and ignored. No framebuffer access or vehicle write is part of the next step.
