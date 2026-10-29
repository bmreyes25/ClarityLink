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

## Composition model — main vs interrupt (central finding; G-02 mechanism confirmed)
The host composes content in **two layers**:
- a **main layout** for normal content (e.g. the turn-by-turn navigation module), and
- a separate **interrupt layout** for interrupts/warnings/popups.

The interrupt subsystem is substantial and typed: interrupts carry an id, a type, a priority, an enable/status
flag, a "currently shown" view id, and an interrupt-info list; there are explicit warning/emergency/popup paths.
Functionally, **warning/emergency content is rendered through the interrupt layer, which preempts main-layer
content**. This is the factory's warning-precedence mechanism.

**Composition ordering — now mechanism-confirmed (OBSERVED_STATIC, G-02).** At screen init the host attaches
three **separate windows** to the platform `WindowManager`, each with its own layout params, in a fixed order:
a **bottom** layer first, the **main** layer second, and the **interrupt** layer **last** — so the interrupt layer
is the top-most window, and it starts hidden. Main and interrupt are therefore **never the same view tree**, and
the interrupt window's visibility is toggled wholesale, independently of the main window. Within each layer, child
views are placed into a **static three-tier z-bucketing by view-id range** (fixed sub-containers), not a dynamic
bring-to-front; a same-id view is re-inserted at the front of its layer's list, otherwise appended. Consequence:
factory-originated interrupt/warning content composites **above** main content by window stacking, and the main
view tree is **preserved** while an interrupt is shown. This upgrades the previous claim from asserted to
mechanism-level — but it is static add-order evidence only, and it does **not** establish precedence under injected
third-party behavior (see report 08 / U-05).

## Relationship to HondaHack (clean-room comparison)
HondaHack (third-party) inserted its own View into the host's **main layout** at the lowest index — i.e. **below**
the factory interrupt/warning layer. So factory interrupt content would still composite above it. **However**, this
does not prove the interrupt layer is unaffected when third-party code runs inside the host process, nor that
main-layer injection cannot disturb the measure/layout/focus of the interrupt layer. HondaHack's mechanism is a
private in-process insertion, **not** a supported or safe extension interface, and it carries no caller
authorization. See report 08 for the safety limits.

## Display-host death / restart / restoration (OBSERVED_STATIC, G-03)
The render host registers a platform **display listener** on Display 1 and responds to its link going away and
coming back (the physical panel link / "LVDS" status is surfaced to the host). Observed sequence:
- **Display removed** — immediate, synchronous teardown: the host removes its whole window/layer stack, clears its
  window-manager reference, and notifies the content manager so every content module stands down. No delay.
- **Display added** — deferred, **validity-gated** rebuild: the host schedules a short-delay task that posts to the
  main thread, re-acquires the display, and checks it is **valid** before doing anything. If valid, it recreates
  the window, rebuilds the three-window layer stack, and resumes content. If **not** valid, it logs an error and
  does **not** rebuild (fail-closed — it will not attach to an invalid display).
- **Display changed** — no-op.

So the factory host is **self-healing against the display link dropping**: tear down on loss, validity-gated
rebuild + resume on return. This is the factory protecting its **own** content; it is not evidence about how any
third-party/injected content behaves across that gap, and the real-world timing is not established here (runtime
evidence required). This mirrors, at a role level, the `HOST_LOST → RECOVERING → restore` states in ClarityLink's
own `cluster_navigation_model.py` (G-04) — which is independently authored and uses no factory identifiers.

## Boundaries (producer → consumer)
| Boundary | Producer | Consumer | Representation | Owner | Evidence |
|---|---|---|---|---|---|
| intake → render | AP service | Out host | structured messages | in-platform | OBSERVED_STATIC |
| main content | Out host | main layout | Android Views | host process | OBSERVED_STATIC |
| interrupt content | Out host | interrupt layout | Android Views (preempting) | host process | OBSERVED_STATIC |
| composite → Display 1 | Out host | Android Display 1 | rendered frame | host process | OBSERVED_STATIC |

## Unknowns
- Static layer add-order is confirmed (G-02); what is still **unproven** is whether that window stacking holds as a
  precedence **guarantee** at runtime and under injected third-party behavior (report 08 / U-05).
- Display-host death/restart/restoration sequencing is now traced (G-03, above); the **real-world timing** and the
  behavior of any non-factory content across the teardown→rebuild gap remain runtime-only unknowns.
- Any native/downstream composition outside the Android host (possible; unresolved).
