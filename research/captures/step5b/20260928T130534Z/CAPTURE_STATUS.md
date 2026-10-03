# ClarityLink Step 5B status

- Scope: independent secondary CarPlay display in the existing cluster Navigation map region; center display remains independent.
- ADB: connected to `[REDACTED-PRIVATE-ENDPOINT]:5555`; root confirmed with `su -c id`.
- Live display inventory: built-in display 0 and HDMI display 1, each 800×480 at about 60 Hz; two Tegra framebuffer nodes, likely aligned by index.
- Framebuffer caution: both sysfs nodes report virtual size 800×960, stride 3200, but BPP 0. No raw framebuffer read was performed.
- `screencap -d display-id` is available. Actual display-1 frame: pending normal Navigation page and user READY.
- Honda runtime inventory: `jmcs`, `disp_com_meter`, ExternalDisplay, CarPlay AP, and Navigation AP processes/services present; exact map destination surface not exposed.
- USB monitor: usbmon paths absent; kernel config does not list CONFIG_USB_MON. Filtered logs show iAP2/authentication startup policy only, no raw packet or screen descriptor.
- USB analyzer: none owned; likely needed for raw USB bytes after remaining evidence options are reviewed.
- Raw diagnostic files/logs: local/ignored under `research/captures/display-diagnostics/20260928T-adb-session/`; no raw files committed.
- Next gate: ask user to display normal factory Navigation with casting off and reply READY; then capture one read-only display-1 frame to the Mac.
