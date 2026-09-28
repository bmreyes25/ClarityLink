# Next action

**ACTION REQUIRED:** Confirm the vehicle is parked and powered and ready for read-only ADB diagnostics over Wi-Fi. If its address differs from `192.168.86.102`, provide the current address. The latest `adb devices -l` returned no attached devices; do not connect or query the vehicle before this confirmation.

After confirmation, reconnect ADB only if needed and collect the bounded read-only display inventory described in the revised Step 5B handoff. Start with `/proc/fb`, graphics sysfs, `dumpsys display`, SurfaceFlinger, window diagnostics, and display properties. Save full outputs locally under `research/captures/display-diagnostics/`; extract only relevant lines into `research/cluster-display-diagnostics.md` and `step-reports/05b-display-diagnostics.md`.

Do not capture a framebuffer until its identity, dimensions, format, stride, and exact byte count are known. Then ask the user to display the normal factory Navigation map and reply READY before one read-only frame capture. Do not require a USB analyzer before the existing diagnostics and logging options have been exhausted. Keep the iPhone disconnected until any required capture setup is ready.
