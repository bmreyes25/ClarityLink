# Next action

**ACTION REQUIRED:** Display the normal factory Navigation map in the instrument cluster with Honda Hack casting off, then reply **READY**. ADB is connected at `192.168.86.102:5555`, root is available, and the read-only diagnostics are saved locally under `research/captures/display-diagnostics/20260928T-adb-session/`.

After READY, capture one display-1 frame with the read-only `screencap -d 1` path, streamed to the Mac. Do not write a capture to vehicle storage. Then request a straight-on full-cluster photo of the same Navigation state if needed to match display pixels to the physical map area.

Do not read `/dev/graphics/fb*` yet: sysfs reports `bits_per_pixel=0`, so the raw framebuffer format/allocation size is unverified. Keep raw diagnostic logs local/ignored, analyze only copies, and do not recommend USB analyzer purchase yet. Existing USB-monitor support is absent and filtered logs do not contain raw iAP2 Identification or display/session descriptor data.
