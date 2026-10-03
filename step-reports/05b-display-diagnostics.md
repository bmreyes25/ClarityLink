# Step 5B — Display diagnostics and practical evidence gate

**Status: live read-only display diagnostics and factory/Advanced Meter/Screen Casting frames collected.** ClarityLink targets an independent second CarPlay display only inside the cluster map region while the center display remains independently usable.

## Live diagnostics

- ADB connected to `[REDACTED-PRIVATE-ENDPOINT]:5555`; `su -c id` confirmed root. No vehicle writes or configuration changes were made.
- `/proc/fb` reports two `tegra_fb` entries. `fb0` maps by sysfs to `tegradc.0`; `fb1` maps to `tegradc.1`. Android identifies Display 0 as Built-in Screen and Display 1 as HDMI Screen. Matching framebuffer and Android display indices is a strong inference, not a proven direct mapping.
- Both Android displays are 800×480 at about 59.995 Hz, with layer stacks 0 and 1. SurfaceFlinger/HWC reports full-frame 800×480 source and destination rectangles. It does not expose a smaller factory Navigation map viewport.
- Both fbdev nodes report virtual size 800×960, stride 3200, but `bits_per_pixel=0`. `fbset` is unavailable. A 3,072,000-byte `stride × virtual height` estimate is conditional and not a verified framebuffer length. No framebuffer read was performed.
- `screencap -d 1` produced valid 800×480 frames for factory Navigation, Advanced Meter, and Screen Casting. The factory screenshot compass/grid and Menu match the photo; speedometer, power/charge, range, and indicators in the photo do not appear in the Android capture.
- SurfaceFlinger reports full-frame Display 1 source/destination bounds in all three states; no smaller nav rectangle appears. HondaHack's static path is now traced: its Xposed module inserts a normal View into Honda `InterfaceWindow` main/interrupt layout; Display 1's externaldisplay process owns full-screen windows. The named HondaHack `MeterActivity` is on Display 0, not the external output.
- Read-only process/service inventory confirms the Honda `jmcs`, `disp_com_meter`, ExternalDisplay, CarPlay AP, and Navigation AP components are running. The logs show Navigation/TBT calls and view ID 200, but no destination rectangle or exact render binding.
- USB monitor nodes are absent; debugfs was already mounted. `/proc/config.gz` reports debugfs but does not list USB_MON. `tcpdump`, `strace`, `usbmon`, `fbset`, and `wm` are unavailable.
- Existing filtered logs include iAP2-connected/authentication/startup events and screen-transfer policy values, but no raw Identification packet fields/bytes or display/session descriptor. Sensitive device serials remain in ignored local logs only.

Full outputs and screenshots are local/ignored under `research/captures/`. No raw diagnostics or identifiers are committed. The HondaHack 7.7.7 APK was copied read-only to the local ignored artifacts directory for offline analysis.

## Current decision values

```text
CLUSTER FULL RESOLUTION: Android HDMI output 800x480; full native cluster resolution UNKNOWN
CLUSTER NAV SOURCE RESOLUTION: UNKNOWN
CLUSTER NAV DESTINATION RECT: UNKNOWN
CLUSTER PIXEL FORMAT: fbdev UNKNOWN (bits_per_pixel reports 0); HWC format code alone is insufficient
CLUSTER FRAMEBUFFER: /dev/graphics/fb1 is the likely HDMI candidate via tegradc.1; direct display mapping is inferred
READ-ONLY DISPLAY-1 CAPTURE POSSIBLE: YES via screencap -d 1 streamed to Mac; three states captured
HONDAHACK DISPLAY-1 OUTPUT: Xposed-injected Android View in Honda ExternalDisplay window hierarchy
CLUSTER HARDWARE MASK/COMPOSITOR: PLAUSIBLE from photo/capture difference; implementation and coordinates unresolved
CARPLAY IDENTIFICATION: logs show connection/authentication policy only; no packet bytes/descriptor
HARDWARE USB ANALYZER REQUIRED: LIKELY for raw USB iAP2 bytes because usbmon is unavailable; defer purchase decision
SECOND DISPLAY NEGOTIATION READY: NO — Identification/session descriptor still unknown
```

## Next action

Proceed offline with second-display CarPlay Identification/session reconstruction. Keep physical safe-area coordinates, supported externaldisplay root acquisition, second-display descriptor, and fail-clear behavior open; the on-car renderer is not ready. No further vehicle capture is currently required. Do not read raw framebuffer devices.
