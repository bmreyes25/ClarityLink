# Step 5B — Live evidence status (superseded capture ordering)

**Status: waiting for parked ADB diagnostics.** This report preserves the fact that the earlier USB/photo capture session was not performed. The diagnostics-first scope and current next step are documented in `05b-display-diagnostics.md`.

- The 2026-09-28 read-only `adb devices -l` returned no attached device.
- No ADB connection attempt, vehicle query, USB trace, framebuffer read, cluster photo, or display-frame capture was performed in that check.
- The user reports ADB over Wi-Fi is available; no hardware USB analyzer is owned.
- Parked/powered readiness has not been confirmed. Do not connect or query the vehicle before confirmation.
- The older analyzer-first sequence is superseded. Check existing display diagnostics, USB-monitor availability, and targeted logs before recommending analyzer purchase.
- Geometry and iAP2 evidence remain unresolved; Step 6 has not started.

The practical Step 6 gate is sufficient evidence for the second display/session identity, target Honda rendering surface and cluster map rectangle, and rollback/fail-clear behavior. See `research/cluster-display-diagnostics.md`, `research/navigation-safe-area.md`, and `research/iap2-identification.md` for the evidence ledgers.
