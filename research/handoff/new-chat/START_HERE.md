# ClarityLink — new-session starter

Continue the 2018 Honda Clarity MY16ADA project in:

`/Users/bmreyes24/ClarityLab/clarity-analysis`

## Goal

Expose a real second, independent CarPlay display and render it only inside the existing factory/HondaHack map region of the instrument cluster. Keep the center CarPlay display independently usable. Preserve the speedometer, gauges, warnings, and all other stock cluster UI. Target Apple Maps first and Waze later if supported.

The practical questions are: cluster target resolution/rectangle, Honda's existing render path, how CarPlay advertises/creates a second display, and how to bind its video to the map region.

## Read first

Read only these state/evidence files before further investigation:

- `PROJECT_STATE.md`
- `NEXT_ACTION.md`
- `EVIDENCE_INDEX.md`
- `step-reports/05-protocol-gaps.md`
- `research/navigation-safe-area.md`
- `research/iap2-identification.md`
- `step-reports/05b-display-diagnostics.md`

Avoid recursive repository scans, raw forensic images, whole-binary dumps, and giant logs. Use targeted commands and write durable findings to reports.

## Current state

- Offline Steps 1–5 are complete; latest committed baseline was `68742466a02cdf2975b61c31ffcf829414ff915d`.
- Saved evidence reports Android built-in and HDMI outputs at 800×480. These do not establish native cluster resolution or the map destination rectangle.
- Honda Hack casts into the cluster map area but follows the center display; its layout-local rectangle is not factory geometry.
- Static receiver evidence configures one 800×480 CarPlay main screen. Exact iAP2 Identification bytes and display/session descriptor remain unknown.
- Read-only ADB diagnostics connected to `[REDACTED-PRIVATE-ENDPOINT]:5555`; root confirmed.
- Android displays 0/1 are Built-in/HDMI, each 800×480 at ~60 Hz. fb0/fb1 link to tegradc.0/.1; likely aligned to display IDs, but BPP reports 0 and framebuffer format/size remain unverified.
- `screencap -d 1` is available. No frame yet; next gate is the user displaying normal factory Navigation with casting off and replying READY.
- usbmon, tcpdump and strace are unavailable. Filtered logs show iAP2/authentication and screen-transfer policy only, no raw Identification or descriptor. The user owns no USB analyzer; defer purchase until descriptor transport and remaining options are reviewed.
- The native Navigation rectangle remains unknown. Step 6 is not ready.

## Next action and safety

Wait for the user to confirm the car is parked and powered and ready for read-only ADB diagnostics over Wi-Fi. Use the supplied current ADB address; ask for an updated one if needed. Do not access the vehicle before confirmation.

Then perform bounded, read-only inventory of `/proc/fb`, framebuffer sysfs, Android display services, and only the known Honda display components. Save diagnostic outputs locally under `research/captures/display-diagnostics/` and publish concise evidence summaries only. Never write to framebuffers, partitions, buses, settings, or firmware.

Do not capture a framebuffer until its identity, dimensions, format, stride, and byte count are known. Before the one read-only frame capture, ask the user to display normal factory Navigation and reply READY. Check existing USB monitor and targeted logging options before considering an analyzer. Keep the iPhone disconnected until capture setup is ready.

Step 6 may proceed only when evidence is sufficient to define the second display/session identity, the target cluster rendering surface and map rectangle, and rollback/fail-clear behavior. Unknown unused panel specifications alone are not blockers.
