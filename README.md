# ClarityLink

**Independent CarPlay navigation in the factory map region of the 2018 Honda Clarity instrument cluster, while the center CarPlay display remains independently usable.**

The target behavior is Apple Maps first and Waze if supported, confined to the existing factory/HondaHack map region. The speedometer, gauges, warnings, and other stock cluster UI must remain intact. No independent iPhone-rendered cluster stream is confirmed yet.

## Current status — 2026-09-28

Steps 1–5 offline are complete. Step 5B is active and has been narrowed to the practical questions needed for this target: cluster output geometry, Honda's existing render path, second-display CarPlay setup, and binding a second stream to the map region.

- Live read-only ADB diagnostics confirm Android display 0 (built-in) and display 1 (HDMI) are each 800×480 at about 60 Hz. Display 1 uses layer stack 1 and its current HWC source/destination is the full 800×480 frame.
- `/proc/fb` exposes two Tegra framebuffer nodes. Sysfs links `fb0` to `tegradc.0` and `fb1` to `tegradc.1`; both report virtual size 800×960, stride 3200, and `bits_per_pixel=0`. The direct framebuffer format and allocation size therefore remain unverified.
- The read-only `screencap` utility supports selecting display ID 1 and can stream to the Mac. No frame has been captured yet; waiting for the normal factory Navigation page and the user’s READY.
- Honda Hack reaches the cluster over HDMI, but the exact factory Navigation destination surface/rectangle is still not exposed.
- Built-in usbmon paths are absent and `CONFIG_USB_MON` is not listed. Filtered logs show iAP2 connection/authentication and screen-transfer policy, but no raw Identification bytes or display/session descriptor. Do not recommend analyzer purchase yet; the descriptor may use another transport.
- Exact navigation destination rectangle, second-display negotiation, and safe-clear behavior remain unknown. Step 6 has not started.

## Roadmap

1. Evidence baseline — complete.
2. Cluster navigation-region model — partial; production geometry unresolved.
3. Second decoder capability — sufficient offline evidence for now; do not repeat without a new reason.
4. Static CarPlay display/Identification model — complete for static evidence.
5. Resolve practical cluster geometry, Honda render path, and available CarPlay session evidence — current.
6. Build the two-display Identification/session model offline.
7. Build the second-display receiver/decoder offline.
8. Bind its video to the cluster navigation region.
9. Validate independent center and cluster displays offline.
10. Prepare a reversible on-car runtime experiment.
11. Obtain a real secondary CarPlay stream while parked.
12. Validate Apple Maps in the cluster map region with the center display independent; then assess Waze.

Step 6 may proceed when evidence is sufficient to define the second display, its session identity, the target rendering surface and map rectangle, and rollback/fail-clear behavior. Unneeded panel specifications alone are not blockers.

## Start here

| Purpose | File |
|---|---|
| Current state and safety boundary | [PROJECT_STATE.md](PROJECT_STATE.md) |
| One next action | [NEXT_ACTION.md](NEXT_ACTION.md) |
| Evidence map | [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md) |
| Current Step 5B diagnostic report | [step-reports/05b-display-diagnostics.md](step-reports/05b-display-diagnostics.md) |
| Existing protocol and geometry gaps | [step-reports/05-protocol-gaps.md](step-reports/05-protocol-gaps.md) |
| Safe-area evidence ledger | [research/navigation-safe-area.md](research/navigation-safe-area.md) |
| iAP2/display static analysis | [research/iap2-identification.md](research/iap2-identification.md) |
| New-session handoff | [research/handoff/new-chat/START_HERE.md](research/handoff/new-chat/START_HERE.md) |

Reports, source, sanitized fixtures, and plans are organized under `step-reports/`, `research/`, `simulator/`, and `tests/`. Raw firmware, forensic images, phone/location data, and raw captures remain local and are excluded from Git. Work is read-only until an independently reviewed reversible experiment is explicitly prepared.
