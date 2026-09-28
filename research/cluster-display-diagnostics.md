# ClarityLink cluster display diagnostics

**Status: partial; live head-unit inventory pending parked ADB access.** This ledger separates Android source/output dimensions from the factory cluster map destination.

| Display | Device path | Width | Height | BPP | Stride | Format | Android display ID | Likely role | Evidence / confidence |
|---|---|---:|---:|---|---|---|---|---|---|
| Built-in | Unknown | 800 | 480 | Unknown | Unknown | Unknown | Not restated in current summary | Center display | Existing SurfaceFlinger evidence summarized in `research/native/receiver-multidisplay-audit.md`; high confidence for saved logical mode, not physical framebuffer |
| HDMI | Unknown | 800 | 480 | Unknown | Unknown | Unknown | Not restated in current summary | External display path that reaches the cluster | Existing SurfaceFlinger evidence and Honda Hack cast observation; high confidence for logical mode/path, exact cluster surface uncertain |
| Cluster factory Navigation target | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | Map/navigation destination region | No native dimensions or rectangle established; unknown |

## Interpretation

The saved 800×480 values describe Android logical display devices and must not be copied into the native cluster rectangle field. Honda Hack's `(0,24,584,191)` cast image is local to its 584×215 meter layout. Whether it targets the exact factory Navigation composition surface remains uncertain.

## Latest live check

On 2026-09-28, `adb devices -l` returned an empty list. No ADB connection attempt or vehicle query was made because parked/powered readiness was not confirmed. No live sysfs, `/proc/fb`, `dumpsys`, or framebuffer output was collected.

## Next evidence

After the user confirms the vehicle is parked and powered and provides the current ADB address, collect read-only `/proc/fb`, `/sys/class/graphics`, available display sysfs, `dumpsys display`, SurfaceFlinger, window and property outputs. Store full diagnostic logs locally in `research/captures/display-diagnostics/`; put only selected sanitized lines and conclusions in this tracked file. Identify the target path and exact format/stride/byte count before any framebuffer read.
