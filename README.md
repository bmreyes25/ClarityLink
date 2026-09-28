# ClarityLink

**Official project name: ClarityLink.** Make a genuine, independent second CarPlay display appear only in the factory Honda Clarity instrument-cluster Navigation region while normal CarPlay remains independently usable on the center screen. Preserve all other stock cluster UI. Apple Maps is first; Waze follows if supported.

## Current status — 2026-09-28

The HondaHack output path is traced to a normal Android View hosted in Honda's externaldisplay window hierarchy. Screen Casting captures Display 0 at 400×240 ARGB_8888, transfers frames through shared MemoryFile/PFD IPC, and places them in an ImageView. HondaHack's Xposed module inserts that view into Honda's InterfaceWindow main/interrupt root. Display 1 is the external HDMI output at 800×480 on layer stack 1.

An offline ClarityLink renderer prototype separates synthetic FrameSource, renderer, and output backend. Host tests cover 800×480 sizing, row stride, invalid frames, repeated submission, and backend clear/destroy lifecycle. The API 17 Android View backend is a skeleton: externaldisplay root acquisition and real viewport/hardware output remain unimplemented. No independent CarPlay second stream exists.

Exact physical Navigation bounds remain unknown. SurfaceFlinger reports full-frame Display 1 output without a smaller crop. HondaHack's 584×215 root and 584×191 local cast image region are not proven physical coordinates. The main protocol blocker is still the missing second-display Identification/session advertisement and descriptor.

## Roadmap

1. Evidence baseline — complete.
2. Prove cluster/HondaHack output path — complete; HondaHack's Android View host path is traced. Exact physical crop is deferred unless rendering needs it.
3. Prove a reusable ClarityLink renderer — current; complete the offline prototype, then run one reversible parked-car renderer test.
4. Finalize the second-display CarPlay protocol model — major blocker after Step 3; resolve Identification/session, display role/UUID, dimensions, FPS, touch behavior, and capability.
5. Build the second CarPlay receiver/decoder — begin once Display B is accepted; prior decoder feasibility work is sufficient for now.
6. Connect the two halves — keep primary center CarPlay independent while routing the secondary decoded stream through ClarityLink to Display 1.
7. Offline integration and failure handling — validate session and decoder lifecycle, reconnect, display loss, and fail-clear behavior.
8. Parked-car second-display experiment — after Steps 2–7, with a minimal reversible test.
9. Apple Maps, independence, then Waze — prove Maps, independent center use, then Waze; package with recovery after stable validation.

Immediate order: finish the renderer proof, then focus the bulk of effort on the second-display CarPlay protocol/session model. The vehicle remains off during current offline work.

## Start here

| Purpose | File |
|---|---|
| Current state | [PROJECT_STATE.md](PROJECT_STATE.md) |
| One next action | [NEXT_ACTION.md](NEXT_ACTION.md) |
| Evidence index | [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md) |
| HondaHack path | [research/hondahack/hondahack-display-path.md](research/hondahack/hondahack-display-path.md) |
| Static trace | [research/hondahack/hondahack-static-analysis.md](research/hondahack/hondahack-static-analysis.md) |
| Renderer interface | [research/hondahack/CLARITYLINK_OUTPUT_INTERFACE.md](research/hondahack/CLARITYLINK_OUTPUT_INTERFACE.md) |
| Milestone report | [step-reports/05c-hondahack-display-path.md](step-reports/05c-hondahack-display-path.md) |
| CarPlay protocol | [research/iap2-identification.md](research/iap2-identification.md) |
| Physical safe-area evidence | [research/navigation-safe-area.md](research/navigation-safe-area.md) |

Raw captures, APKs, firmware, forensic images, and sensitive data stay local and ignored. No direct framebuffer access or vehicle writes are part of current work.
