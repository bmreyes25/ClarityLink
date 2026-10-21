# CL-FACTORY-01 / M3 — ExternalDisplay host architecture (sanitized)

Status: IN PROGRESS. Evidence OBSERVED_STATIC (deodexed Java). Offline only. `safeForHonda() == false`.
Proprietary identifiers kept private; role-level description only.

## Two services
- **ExternalDisplay AP service** (intake/windowing side, small): receives navigation and vehicle/unit-info data
  over AIDL, assembles packetized messages (multi-packet + feedback/retry timers), and drives windowing control.
- **ExternalDisplay Out service** (render host, large — ~900 deodexed classes): **owns the cluster composition**
  and renders content onto Android Display 1. Content is organized into modules (turn-by-turn, audio, phone, mail,
  voice-recognition, a heads-up module, and a customize module).

## Display ownership
The render host **observes an existing external display** (Android Display 1) via the platform display manager
(`getDisplays` / display listeners); it does **not** create a virtual display. Historically the Android external
output was 800×480 — a logical size, **not** the physical cluster aperture.

## Composition model — main vs interrupt (central finding)
The host composes content in **two layers**:
- a **main layout** for normal content (e.g. the turn-by-turn navigation module), and
- a separate **interrupt layout** for interrupts/warnings/popups.

The interrupt subsystem is substantial and typed: interrupts carry an id, a type, a priority, an enable/status
flag, a "currently shown" view id, and an interrupt-info list; there are explicit warning/emergency/popup paths.
Functionally, **warning/emergency content is rendered through the interrupt layer, which preempts main-layer
content**. This is the factory's warning-precedence mechanism.

## Relationship to HondaHack (clean-room comparison)
HondaHack (third-party) inserted its own View into the host's **main layout** at the lowest index — i.e. **below**
the factory interrupt/warning layer. So factory interrupt content would still composite above it. **However**, this
does not prove the interrupt layer is unaffected when third-party code runs inside the host process, nor that
main-layer injection cannot disturb the measure/layout/focus of the interrupt layer. HondaHack's mechanism is a
private in-process insertion, **not** a supported or safe extension interface, and it carries no caller
authorization. See report 08 for the safety limits.

## Boundaries (producer → consumer)
| Boundary | Producer | Consumer | Representation | Owner | Evidence |
|---|---|---|---|---|---|
| intake → render | AP service | Out host | structured messages | in-platform | OBSERVED_STATIC |
| main content | Out host | main layout | Android Views | host process | OBSERVED_STATIC |
| interrupt content | Out host | interrupt layout | Android Views (preempting) | host process | OBSERVED_STATIC |
| composite → Display 1 | Out host | Android Display 1 | rendered frame | host process | OBSERVED_STATIC |

## Unknowns
- Exact compositing-order guarantees of the interrupt layer vs. arbitrary main-layer manipulation (method-level +
  runtime evidence required; tracked in report 08 / U-05).
- Host-process death/restart and factory-restoration sequencing (partial; being traced).
- Any native/downstream composition outside the Android host (possible; unresolved).
