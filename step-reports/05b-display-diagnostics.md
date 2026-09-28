# Step 5B — Display diagnostics and practical evidence gate

**Status: live read-only diagnostics collected; one display-1 frame awaits normal Navigation state and READY.** ClarityLink targets an independent second CarPlay display only inside the cluster map region while the center display remains independently usable.

## Live diagnostics

- ADB connected to `192.168.86.102:5555`; `su -c id` confirmed root. No vehicle writes or configuration changes were made.
- `/proc/fb` reports two `tegra_fb` entries. `fb0` maps by sysfs to `tegradc.0`; `fb1` maps to `tegradc.1`. Android identifies Display 0 as Built-in Screen and Display 1 as HDMI Screen. Matching framebuffer and Android display indices is a strong inference, not a proven direct mapping.
- Both Android displays are 800×480 at about 59.995 Hz, with layer stacks 0 and 1. SurfaceFlinger/HWC reports full-frame 800×480 source and destination rectangles. It does not expose a smaller factory Navigation map viewport.
- Both fbdev nodes report virtual size 800×960, stride 3200, but `bits_per_pixel=0`. `fbset` is unavailable. A 3,072,000-byte `stride × virtual height` estimate is conditional and not a verified framebuffer length. No framebuffer read was performed.
- `screencap` supports `-d display-id`; it can stream a selected display image to the Mac. No frame was captured yet.
- Read-only process/service inventory confirms the Honda `jmcs`, `disp_com_meter`, ExternalDisplay, CarPlay AP, and Navigation AP components are running. The logs show Navigation/TBT calls and view ID 200, but no destination rectangle or exact render binding.
- USB monitor nodes are absent; debugfs was already mounted. `/proc/config.gz` reports debugfs but does not list USB_MON. `tcpdump`, `strace`, `usbmon`, `fbset`, and `wm` are unavailable.
- Existing filtered logs include iAP2-connected/authentication/startup events and screen-transfer policy values, but no raw Identification packet fields/bytes or display/session descriptor. Sensitive device serials remain in ignored local logs only.

Full outputs are local/ignored under `research/captures/display-diagnostics/20260928T-adb-session/`. No raw diagnostics or identifiers are committed.

## Current decision values

```text
CLUSTER FULL RESOLUTION: Android HDMI output 800x480; native instrument-cluster resolution UNKNOWN
CLUSTER NAV SOURCE RESOLUTION: UNKNOWN
CLUSTER NAV DESTINATION RECT: UNKNOWN
CLUSTER PIXEL FORMAT: fbdev UNKNOWN (bits_per_pixel reports 0); HWC format code alone is insufficient
CLUSTER FRAMEBUFFER: /dev/graphics/fb1 is the likely HDMI candidate via tegradc.1; direct display mapping is inferred
READ-ONLY CLUSTER CAPTURE POSSIBLE: YES via screencap -d 1 streamed to Mac; waiting for Navigation state and READY
HONDAHACK USES SAME DISPLAY PATH: HDMI reaches cluster; exact factory Navigation surface/rectangle UNKNOWN
CARPLAY IDENTIFICATION: logs show connection/authentication policy only; no packet bytes/descriptor
HARDWARE USB ANALYZER REQUIRED: LIKELY for raw USB iAP2 bytes because usbmon is unavailable; defer purchase decision
STEP 6 READY: NO
```

## Next action

ACTION REQUIRED: Display the normal factory Navigation map in the cluster, with Honda Hack casting off, and reply **READY**. Then capture one read-only display-1 frame to the Mac. Afterward, request a straight-on cluster photo of the same state if needed to relate the Android image to the physical map region.

Do not read the raw framebuffer until its exact format and allocation size are established. The practical Step 6 gate remains sufficient evidence for second-display/session identity, target render path and map rectangle, and rollback/fail-clear behavior.
