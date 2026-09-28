# ClarityLink cluster display diagnostics

**Status: live ADB inventory collected; factory Navigation rectangle still unknown.** Vehicle access was read-only. ADB connected to `192.168.86.102:5555`; `su -c id` returned root. Full command outputs are local and ignored under `research/captures/display-diagnostics/20260928T-adb-session/`.

## Display inventory

| Display | Device path | Width | Height | BPP / stride | Format | Android display ID / layer stack | Likely role | Evidence / confidence |
|---|---|---:|---:|---|---|---|---|---|
| Built-in Screen | `/dev/graphics/fb0`; sysfs device link to `tegradc.0` | 800 | 480 mode; virtual 800×960 | BPP reports `0`; stride 3200 bytes/line | fbdev format unknown; HWC layer format field `0x1` is not proof of fbdev format | Display 0 / stack 0 | Center display | `dumpsys display`, SurfaceFlinger, `/proc/fb`, and sysfs; high confidence logical role and mode. fbdev alignment to Android ID is inferred by matching device index. |
| HDMI Screen | `/dev/graphics/fb1`; sysfs device link to `tegradc.1` | 800 | 480 mode; virtual 800×960 | BPP reports `0`; stride 3200 bytes/line | fbdev format unknown; HWC layer format field `0x1` is not proof of fbdev format | Display 1 / stack 1 | External HDMI path observed to reach cluster | `dumpsys display` says HDMI, 800×480 at 59.995 fps; SurfaceFlinger reports display 1 external. Honda Hack cast reaches cluster. High confidence logical role/mode; exact native cluster composition path remains uncertain. |
| Factory Navigation map destination | Unknown | Unknown | Unknown | Unknown | Unknown | Unknown | Map region inside instrument cluster | No diagnostic exposes the OEM destination rectangle. Unknown. |

`/proc/fb` reports two `tegra_fb` entries. `/sys/class/graphics/fb0/device` links to `tegradc.0`; `fb1` links to `tegradc.1`. `fb0` reports modes `U:800x480p-0` and `U:800x480p-59`; `fb1` reports `D:800x480p-59`. `/sys/class/display` and `/sys/class/drm` are absent. `fbset` and `wm` are not installed.

Both framebuffer nodes report `virtual_size=800,960`, `stride=3200`, and `bits_per_pixel=0`. If stride is bytes per line, `3200 × 960 = 3,072,000` bytes is a conditional virtual-buffer estimate. Since BPP is reported as zero and no framebuffer length/format ioctl is available, this is **not** a verified allocation size and does not authorize a raw framebuffer read. The 4 bytes/pixel ratio implied by `stride / width` is an inference only.

## SurfaceFlinger and capture path

Android display 0 is Built-in Screen; display 1 is HDMI Screen, both 800×480 at about 60 Hz. Display 0 uses layer stack 0 and display 1 uses layer stack 1. SurfaceFlinger/HWC reports full-frame 800×480 source/destination rectangles on both displays. HDMI layers are unnamed in the dump; no separate smaller factory Navigation map rectangle is exposed.

The installed `screencap` binary advertises `-d display-id` and writes to stdout when no filename is supplied. A display-1 frame can therefore be streamed to the Mac with a read-only ADB capture command, without writing to the vehicle. No frame has been captured yet. **Before one frame capture, the user must display the normal factory Navigation map in the cluster with Honda Hack casting off and reply READY.**

## Honda runtime components

Read-only process/service inventory found `jmcs`, `disp_com_meter`, ExternalDisplayOutService, ExternalDisplayApService, the CarPlay AP service, and Navigation AP service running. Existing ExternalDisplayOutService logs show calls to Navigation route and TBT interfaces and a view-control add for ID 200, but no map rectangle, source/destination crop, or native framebuffer binding. These findings do not prove Honda Hack uses the exact factory Navigation surface.

## USB monitor and logs

- `/sys/kernel/debug` was already mounted. `/sys/kernel/debug/usb/usbmon` and `/dev/usbmon*` are absent. `/proc/config.gz` lists `CONFIG_DEBUG_FS=y` but no `CONFIG_USB_MON` entry.
- `tcpdump`, `strace`, `usbmon`, `fbset`, and `wm` are unavailable. `dumpsys`, `screencap`, `logcat`, and BusyBox are available.
- Filtered existing logcat includes iAP2-connected and CarPlay authentication/startup events plus screen-transfer policy values (Take, user-initiated priority, Take constraint Never, Borrow constraint Anytime). It does not show raw Identification bytes, serialized display dimensions, UUID, or a second-display descriptor. Device serial values are kept only in ignored local logs.
- The built-in USB-monitor route is unavailable on this kernel. A hardware analyzer is likely required to capture raw USB iAP2 bytes, but no purchase is recommended yet; the display descriptor may use another transport and must be identified separately.

## Evidence files and next gate

Raw diagnostics are local/ignored in `research/captures/display-diagnostics/20260928T-adb-session/`. Do not commit them. Keep only sanitized conclusions in this file and `step-reports/05b-display-diagnostics.md`.

The exact factory map rectangle is still unknown. Next, ask the user to show the normal factory Navigation page with casting off and reply READY; then capture one read-only display-1 frame to the Mac and ask for a timestamp-matched straight-on cluster photo if needed. Do not read `/dev/graphics/fb*` until the framebuffer format, size, and byte count are established.
