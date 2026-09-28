# ClarityLink Step 5B — diagnostics-first plan

Session directory: `research/captures/step5b/20260928T130534Z/`.

This revised plan replaces the original analyzer-first ordering. The objective is to determine the cluster map rendering target and practical second-display requirements using existing read-only head-unit diagnostics before photo measurement or any hardware purchase.

## A. Read-only display inventory — completed

ADB connected to `192.168.86.102:5555`; root was confirmed. The vehicle was queried read-only. No settings, files, buses, or firmware were changed. Findings are summarized in `research/cluster-display-diagnostics.md`; raw outputs remain local/ignored under `research/captures/display-diagnostics/20260928T-adb-session/`.

## B. Read-only display inventory

The completed inventory covered bounded output for `/proc/fb`, `/dev/graphics`, `/sys/class/graphics`, `/sys/class/display`, `/sys/class/drm` if present, `fbset -i` if installed, `dumpsys display`, SurfaceFlinger, window, `wm size/density`, and relevant display properties. Store complete outputs locally under `research/captures/display-diagnostics/`; analyze selected lines only.

Inventory device path, display ID, width, height, pixel format, BPP, stride, layer stack, orientation/refresh when available, and likely role. Keep Android logical output dimensions, source video dimensions, full cluster dimensions, and Navigation destination rectangle separate.

Inspect only known Honda display components (`cluster`, `cluster_get.sh`, `cluster_set.sh`, `disp_com_meter`, ExternalDisplay services/libraries, Navigation interfaces) with targeted strings/symbols and bounded code slices. Do not invoke hidden calibration or write functions.

## C. Framebuffer gate and optional frame

Do not read any framebuffer until a probable cluster/display path is positively identified and width, height, BPP/format, stride, and exact byte count are established from diagnostics. Reads only; writes are forbidden.

Before one read-only frame capture, ask the user to display the normal factory Navigation map in the cluster and reply READY. Capture to the Mac, timestamp the frame, and pair it with a straight-on full-cluster photo of the same state only if required to validate diagnostics. If the identified HDMI frame does not contain the OEM page, stop and record the limitation.

## D. Existing iAP2/CarPlay observation options

Read-only checks found whether `/sys/kernel/debug/usb/usbmon` or `/dev/usbmon*` already exists, whether debugfs is already mounted, whether `CONFIG_USB_MON` is enabled in the available config, and whether `tcpdump`, `strace`, `usbmon`, and `logcat` are present. Do not mount debugfs, enable tracing, or attach strace.

Use short targeted logcat observations around a normal CarPlay connection only after the user confirms readiness. Preserve local logs, extract relevant lines, and determine whether existing diagnostics disclose display/session information. Do not alter USB traffic. Recommend analyzer purchase only after existing software options are exhausted and the remaining evidence need is documented.

## Integrity and scope

No firmware/settings/vehicle writes, framebuffer writes, CAN traffic, APK installation, binary patch, packet injection, or unnecessary reboot. Keep raw artifacts local and ignored. Do not stage raw captures or sensitive logs. Record only sanitized findings in tracked reports. Do not begin Step 6 until display/session identity, target rendering surface/map rectangle, and rollback/fail-clear behavior are sufficiently defined.
