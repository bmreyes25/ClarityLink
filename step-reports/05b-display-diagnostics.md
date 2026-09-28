# Step 5B — Display diagnostics and practical evidence gate

**Status: waiting for parked vehicle access.** The scope is the independent secondary CarPlay display inside the existing cluster map region. This report supersedes the analyzer-first capture ordering in the earlier Step 5B session plan.

## Work completed

- Reviewed the existing saved evidence: Android built-in and HDMI display devices are each reported at 800×480. These are logical head-unit outputs, not proof of the cluster's native framebuffer or map rectangle.
- Existing Honda Hack observations establish that its cast reaches the cluster and mirrors the center display. The 584×191 image rectangle is local to Honda Hack's 584×215 layout; its mapping to factory Navigation coordinates is unknown.
- Ran read-only `adb devices -l` on 2026-09-28. It returned no attached devices. No `adb connect`, vehicle query, physical interaction, or capture was performed because parked/powered readiness was not confirmed.
- The user reports ADB over Wi-Fi is available and no USB protocol analyzer is owned.

## Diagnostics-first sequence

Once parked/powered readiness and the current ADB address are confirmed, inspect only read-only framebuffer/sysfs, Android display, and targeted Honda display-service information. Save raw diagnostic outputs locally and use short extracted summaries in tracked reports. Establish display IDs, dimensions, pixel format, stride, and role before identifying any probable cluster target. Check existing USB-monitor support and short targeted logs before considering analyzer purchase.

A framebuffer read is gated on positive identification and verified byte count. Before capturing a frame, ask the user to show the normal factory Navigation map and reply READY. Preserve stock UI and never write to a framebuffer.

## Current decision values

```text
CLUSTER FULL RESOLUTION: UNKNOWN (Android built-in and HDMI outputs: 800x480)
CLUSTER NAV SOURCE RESOLUTION: UNKNOWN
CLUSTER NAV DESTINATION RECT: UNKNOWN
CLUSTER PIXEL FORMAT: UNKNOWN
CLUSTER FRAMEBUFFER: UNKNOWN
READ-ONLY CLUSTER CAPTURE POSSIBLE: UNCERTAIN
HONDAHACK USES SAME DISPLAY PATH: UNCERTAIN (HDMI reaches cluster; exact surface not established)
CARPLAY IDENTIFICATION: static evidence only; exhaust existing read-only logging/USB-monitor options after ADB is available
HARDWARE USB ANALYZER REQUIRED: NOT YET
STEP 6 READY: NO
```

## Next action

Wait for confirmation that the car is parked and powered and ready for read-only ADB diagnostics. Do not connect or query the vehicle before confirmation. See `NEXT_ACTION.md` for the single action and `research/handoff/new-chat/START_HERE.md` for the bounded session instructions.
