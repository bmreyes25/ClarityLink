# ClarityLink project state — 2026-09-28

## Goal

Render a real, independent secondary CarPlay display only inside the existing factory/HondaHack navigation map region of the 2018 Honda Clarity MY16ADA instrument cluster. Keep the center CarPlay display independently usable. Preserve every other stock cluster element. Apple Maps is the first target; Waze follows if supported.

No independent CarPlay cluster stream or route-metadata bridge is confirmed.

## Repository and data safety

- GitHub repository: `ClarityLink`; branch `main`.
- Latest evidence baseline before the ClarityLink scope refresh: `68742466a02cdf2975b61c31ffcf829414ff915d`; this update publishes the revised Step 5B scope and handoff.
- Raw firmware, images, phone/location data, APK/ODEX/shared libraries, and extracted binaries stay local and ignored.
- Pristine backup `/Users/bmreyes24/ClarityLab/backups/CLARITY_BACKUP_20260918_0225_ORIGINAL` is read-only.
- Verified forensic original `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_ORIGINAL` is immutable; analysis uses its separate working copy.
- No vehicle writes, flash, remount, bus action, or capture occurred in the current diagnostics check.

## Confirmed evidence

- Honda Hack mirrors the center CarPlay screen into the cluster navigation area and follows center Maps → Music. Spoken guidance remained audible during casting.
- Saved Android diagnostics show separate built-in and HDMI display devices at 800×480. This does not establish the cluster's native framebuffer or the map destination rectangle.
- Android Waze can show a Honda cluster arrow/distance independently and clears on route end. This does not prove iPhone CarPlay metadata.
- Static `jmcs` analysis configures one main CarPlay screen (800×480, max 30 FPS, hifi touch); its proxy screen callback is singleton. Exact iAP2 Identification bytes and the live display/session descriptor remain unknown.
- Two NVIDIA H.264 decoder objects each produced 28/30 frames in a short test with CarPlay disconnected. Active coexistence and second-Surface rendering remain untested.
- Read-only `adb devices -l` on 2026-09-28 returned no attached devices. No connection attempt or vehicle query followed. The user reports ADB over Wi-Fi is available; parked/powered readiness is still required before vehicle access.

## Current work — Step 5B

Step 5B is diagnostics-first. Inspect read-only framebuffer/sysfs, Android display services, and narrowly scoped Honda display components before relying on photo geometry or recommending a USB analyzer. No USB analyzer is currently owned. Exhaust existing software/logging options before recommending one. Do not capture framebuffer data until a probable cluster/display framebuffer is positively identified, dimensions and byte size are known, and the user has displayed the normal factory Navigation map and replied READY.

- **Cluster full resolution:** saved Android built-in/HDMI surfaces are 800×480; native cluster resolution unknown.
- **Navigation source resolution:** unknown.
- **Navigation destination rectangle:** unknown. Honda Hack layout-local cast area is `(0,24,584,191)` in a 584×215 layout; mapping to cluster coordinates is unproven.
- **Framebuffer path/format:** unknown.
- **HondaHack target path:** HDMI output reaches the cluster; whether its composition surface is the exact factory Navigation surface is not proven.
- **CarPlay Identification:** static model only; no raw transaction captured. Built-in `CONFIG_USB_MON` was recorded unset. Existing ADB/logging and USB monitor availability checks remain to be performed once connected and parked.
- **Step 6 ready:** no. The practical gate is enough evidence to define second-display size/session identity, cluster rendering surface and target map rectangle, plus rollback/fail-clear behavior.

## Authoritative files

- `NEXT_ACTION.md` — one next action.
- `EVIDENCE_INDEX.md` — evidence and confidence map.
- `step-reports/05b-display-diagnostics.md` — current diagnostic-first status.
- `research/navigation-safe-area.md` — navigation geometry candidates and proof gaps.
- `research/iap2-identification.md` — static protocol model and evidence options.
- `step-reports/05-protocol-gaps.md` — current Step 5/6 evidence gate.
- `step-reports/RUN_STATUS.md` — dated work log.
