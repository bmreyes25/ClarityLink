# ClarityLink project state — 2026-09-28

## Goal

Render a genuine, independent second CarPlay display only in the existing Honda Clarity instrument-cluster Navigation region while normal CarPlay remains independently usable on the center display. Preserve all other stock cluster UI. Apple Maps is the first target; Waze follows if supported.

## Current milestone

The current focus is CarPlay Display B negotiation (Step 4). The renderer is sufficient to define a candidate Android output endpoint, but must not distract from the iPhone-facing second display/session model.

HondaHack's cluster output path is traced. It uses a normal Android View injected into Honda's existing externaldisplay main/interrupt window hierarchy, not direct framebuffer output or a DisplayManager Presentation. Screen Casting captures Display 0 at 400×240 ARGB_8888, passes frames through a MemoryFile/PFD Messenger path, and sets them on a HondaHack ImageView in that View. The externaldisplay process owns the Display 1 full-screen windows.

Display 1 is confirmed as HDMI/external, 800×480 at about 60 Hz, layer stack 1. SurfaceFlinger reports full-frame bounds and no smaller Android crop. HondaHack's 584×215 root and 584×191 cast ImageView region are local layout measurements, not proven physical cluster bounds. Photo and screenshot together support downstream composition but do not prove the exact cluster crop/mask.

An offline renderer prototype now exists in src/claritylink-renderer/. The Python synthetic frame source and mock lifecycle backend are tested. The API 17 Java view backend is a skeleton: obtaining the Honda externaldisplay root requires a privileged integration hook, physical viewport and hardware output are unverified, and Surface-backed/zero-copy decoder frames are not implemented.

## Evidence and blockers

- Confirmed: separate Android Displays 0 and 1 at 800×480; Display 1 / layer stack 1; HondaHack Screen Casting and Advanced Meter share the ExternalDisplay Xposed-injected View host path.
- Confirmed: HondaHack captures the center display at 400×240 ARGB_8888 and presents it in a fitXY ImageView. The source layout's local cast area is 584×191 within a 584×215 root.
- Unknown: exact physical Navigation region geometry and downstream crop/mask transform.
- Unknown: raw iAP2 Identification, second display descriptor/UUID/role, and second session negotiation.
- Unknown: a supported/maintainable ClarityLink mechanism to obtain Honda's externaldisplay root without HondaHack's private Xposed integration.
- Not implemented: second CarPlay session, second H.264 stream, hardware renderer, or on-car test.

## Roadmap

| Step | Work | Status |
|---|---|---|
| 1 | Evidence baseline | Complete |
| 2 | Prove cluster/HondaHack output path | Complete: HondaHack uses a regular View in Honda's ExternalDisplay window; exact physical crop remains non-blocking and unproven |
| 3 | Reusable ClarityLink renderer abstraction | Partial and sufficient for protocol work: synthetic host model/tests and API 17 View skeleton; root acquisition, crop, and zero-copy remain deferred |
| 4 | Second-display Identification/session reconstruction | Current: primary model traced; Display B/session and wire schema are partial/blocked |
| 5 | Implement Display-B negotiation | Not ready; requires accepted descriptor/session evidence and a reversible implementation design |
| 6 | Receive second CarPlay H.264 stream | Pending negotiated stream; existing decoder feasibility stands |
| 7 | Connect decoder to ExternalDisplay renderer | Pending stream-to-frame lifecycle and renderer integration |
| 8 | Offline integration and failure handling | Pending independent teardown, reconnect, display-loss, and fail-clear validation |
| 9 | Minimal reversible parked-car test | Pending Steps 4–8 and reviewed run/recovery plan |
| 10 | Apple Maps cluster display with independent center display | Pending real Display B stream |
| 11 | Waze validation | Pending Apple Maps success |
| 12 | Packaging, recovery, and persistent implementation | Pending stable validation and recovery plan |

The primary blocker is the iPhone-facing Display B descriptor/session/stream negotiation. Exact physical crop, externaldisplay root acquisition, and zero-copy input remain deferred unless protocol integration requires them. This milestone was offline; no vehicle is needed until a reviewed reversible test is ready.

## Repository and data safety

- Official project name: ClarityLink. GitHub repository: bmreyes25/ClarityLink, branch main.
- Raw captures, the copied HondaHack APK, forensic images, phone/location data, and vendor binaries stay local and ignored.
- Pristine and verified forensic originals remain immutable; offline analysis uses designated working copies.
- Vehicle was used only for parked, read-only display diagnostics. No vehicle writes, framebuffer reads/writes, flash, remount, packet injection, or bus actions were performed.
- Latest live capture set is local/ignored under research/captures/hondahack-display-path/20260928T152742Z/.

## Authoritative files

- NEXT_ACTION.md — single next action.
- EVIDENCE_INDEX.md — evidence and confidence map.
- research/hondahack/hondahack-display-path.md — traced Honda output path.
- research/hondahack/hondahack-static-analysis.md — APK call graph.
- research/hondahack/CLARITYLINK_OUTPUT_INTERFACE.md — renderer contract/limits.
- step-reports/05c-hondahack-display-path.md — live/static milestone result.
- research/iap2-identification.md — unresolved CarPlay session advertisement.
- research/carplay/primary-display-session.md — primary static trace.
- research/carplay/second-display-session.md — Display B boundaries and missing evidence.
- research/carplay/identification-schema.md — field-level schema confidence.
- step-reports/07-second-carplay-session-model.md — current protocol milestone.
- src/carplay-session-model/model.py — offline candidate model, not wire serialization.
