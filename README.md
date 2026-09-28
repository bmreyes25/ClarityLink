# ClarityLink

**Independent CarPlay navigation in the factory map region of the 2018 Honda Clarity instrument cluster, while the center CarPlay display remains independently usable.**

The target behavior is Apple Maps first and Waze if supported, confined to the existing factory/HondaHack map region. The speedometer, gauges, warnings, and other stock cluster UI must remain intact. No independent iPhone-rendered cluster stream is confirmed yet.

## Current status — 2026-09-28

Steps 1–5 offline are complete. Step 5B is active and has been narrowed to the practical questions needed for this target: cluster output geometry, Honda's existing render path, second-display CarPlay setup, and binding a second stream to the map region.

- Saved evidence shows separate Android built-in and HDMI display devices at 800×480. That is the head-unit output size, not proof of the cluster map rectangle or its native framebuffer.
- Honda Hack mirrors the center CarPlay image into the cluster navigation area; it follows the center app. This establishes a usable existing output path, not the exact factory map bounds or a second CarPlay stream.
- A read-only `adb devices -l` check on 2026-09-28 returned no attached device. No vehicle diagnostics or capture were started in that check.
- The user reports ADB over Wi-Fi is available and no USB protocol analyzer is owned. The next investigation is read-only head-unit display diagnostics and targeted Honda component inspection. Do not recommend analyzer purchase until existing software options are exhausted.
- Exact navigation destination rectangle, actual iAP2 Identification bytes, second-display negotiation, and safe-clear behavior remain unknown. Step 6 has not started.

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
