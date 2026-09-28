# Step 5 — Protocol and cluster map-region evidence

**Status: offline review complete; practical live evidence remains open.** ClarityLink targets a separate CarPlay map display inside the existing instrument-cluster navigation region while the center display remains independently usable.

## Cluster geometry and Honda render path

The exact factory Navigation destination rectangle remains unknown. Saved evidence establishes Android built-in and HDMI logical displays at 800×480. HondaHack's output path is traced to an Xposed-injected Android View hosted in Honda ExternalDisplay's main/interrupt window hierarchy; its `(0,24,584,191)` coordinates are local to a 584×215 layout and do not establish the physical cluster bounds. See `step-reports/05c-hondahack-display-path.md`.

Parked, read-only ADB diagnostics and factory/Advanced Meter/Screen Casting Display 1 captures are complete. Android display 1 is the 800×480 HDMI output; `fb1`/`tegradc.1` is the likely matching framebuffer. Its BPP reports zero, so its raw format/size remain unverified. SurfaceFlinger exposes no subrectangle. HondaHack's output view path is understood, but physical map bounds and a standalone host adapter remain unresolved. No raw framebuffer access is required.

## CarPlay second-display/session evidence

Static `jmcs` evidence configures one main CarPlay screen and has a separate AirPlay receiver display-info path. The raw iAP2 Identification bytes, display/session descriptor, UUID, and second-display negotiation are unknown. Read-only USB-monitor and log checks are complete: usbmon is not available, and the filtered live logs expose connection/authentication policy but no payload bytes or screen descriptor. A hardware analyzer is likely needed for raw USB traffic, but no purchase is recommended while the separate descriptor transport is still unknown.

## Practical Step 6 gate

The old exploratory Step 6 gate is superseded by the focused ClarityLink roadmap in `PROJECT_STATE.md`. The next milestone is offline second-display Identification/session reconstruction. Live rendering remains gated on:

1. The second CarPlay display size and session identity.
2. The Honda rendering surface/path and cluster Navigation destination rectangle.
3. A reversible binding with rollback and fail-clear behavior that preserves all stock cluster UI and center CarPlay use.

Perfect knowledge of unrelated panel specifications is not required. See `step-reports/05b-display-diagnostics.md` for the current parked-access gate.
