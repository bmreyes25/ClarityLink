# ClarityLink project state — 2026-09-28

## Goal

Render a genuine, independent second CarPlay display only in the existing Honda Clarity instrument-cluster Navigation region while normal CarPlay remains independently usable on the center display. Preserve all other stock cluster UI. Apple Maps is the first target; Waze follows if supported.

## Current milestone

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
| 2 | Prove cluster/HondaHack output path | Complete for Android view host path; physical safe-area crop unresolved |
| 3 | Build reusable ClarityLink Display 1 renderer | Partial: host mock/prototype complete; Android API 17 host backend skeleton only |
| 4 | Reconstruct second-display CarPlay Identification/session model | Next |
| 5 | Implement second-display negotiation | Pending Step 4 evidence |
| 6 | Receive/decode second CarPlay H.264 stream | Pending |
| 7 | Route decoder output to Display 1 | Pending root/lifecycle and viewport work |
| 8 | Offline integration and failure handling | Pending |
| 9 | Minimal reversible parked-car test | Pending separate reviewed run card |
| 10 | Apple Maps independent center/cluster validation | Pending |
| 11 | Waze validation | Pending Apple Maps path |
| 12 | Packaging and recovery/persistent implementation | Pending after validation |

The largest current blocker is reconstructing the second-display Identification/session advertisement. Physical viewport proof and a production-safe externaldisplay host adapter remain required before live rendering.

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
