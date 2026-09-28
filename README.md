# ClarityLink

**Official project name: ClarityLink.** Make a genuine, independent second CarPlay display appear only in the factory Honda Clarity instrument-cluster Navigation region while normal CarPlay remains independently usable on the center screen. Preserve all other stock cluster UI. Apple Maps is first; Waze follows if supported.

## Current status — 2026-09-28

The HondaHack output path is traced to a normal Android View hosted in Honda's externaldisplay window hierarchy. Screen Casting captures Display 0 at 400×240 ARGB_8888, transfers frames through shared MemoryFile/PFD IPC, and places them in an ImageView. HondaHack's Xposed module inserts that view into Honda's InterfaceWindow main/interrupt root. Display 1 is the external HDMI output at 800×480 on layer stack 1.

An offline ClarityLink renderer prototype separates synthetic FrameSource, renderer, and output backend. Host tests cover 800×480 sizing, row stride, invalid frames, repeated submission, and backend clear/destroy lifecycle. The API 17 Android View backend is a skeleton: externaldisplay root acquisition and real viewport/hardware output remain unimplemented. No independent CarPlay second stream exists.

Exact physical Navigation bounds remain unknown. SurfaceFlinger reports full-frame Display 1 output without a smaller crop. HondaHack's 584×215 root and 584×191 local cast image region are not proven physical coordinates. The main protocol blocker is still the missing second-display Identification/session advertisement and descriptor.

Display B static work is documented in `research/carplay/`. The offline model in `src/carplay-session-model/` emits deterministic JSON research fixtures with explicit unknown fields; it does not synthesize protocol bytes.

## Roadmap

1. Evidence baseline — complete.
2. Honda/cluster output path — complete enough; HondaHack View path traced to Display 1.
3. Reusable ClarityLink renderer abstraction — partial and sufficient for protocol work.
4. Second-display Identification/session reconstruction — current; primary model recovered, Display B model partial.
5. Implement Display-B negotiation — blocked on descriptor/session evidence.
6. Receive second CarPlay H.264 stream — pending accepted Display B.
7. Connect decoder to ExternalDisplay renderer — pending.
8. Offline integration and failure handling — pending.
9. Minimal reversible parked-car test — pending reviewed design.
10. Apple Maps cluster display with independent center display — pending.
11. Waze validation — pending Apple Maps success.
12. Packaging, recovery, and persistent implementation — pending.

The current engineering focus is Display B negotiation. Do not spend time on exact physical crop, HondaHack capture, framebuffer access, renderer optimization, root acquisition, or zero-copy input unless a protocol finding directly requires it.

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
| Primary display/session trace | [research/carplay/primary-display-session.md](research/carplay/primary-display-session.md) |
| Display B candidate model | [research/carplay/second-display-session.md](research/carplay/second-display-session.md) |
| Descriptor schema evidence | [research/carplay/identification-schema.md](research/carplay/identification-schema.md) |
| Session-model tests | [tests/carplay-session-model/test_model.py](tests/carplay-session-model/test_model.py) |

Raw captures, APKs, firmware, forensic images, and sensitive data stay local and ignored. No direct framebuffer access or vehicle writes are part of current work.
