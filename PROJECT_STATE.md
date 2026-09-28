# ClarityLab project state — 2026-09-28

## Goal

Investigate an independent Apple Maps/Waze CarPlay map or guidance view in the 2018 Honda Clarity MY16ADA instrument cluster, while preserving center-display use and spoken guidance. No working independent CarPlay cluster stream or route-metadata bridge is confirmed.

## Repository and data safety

- Git branch: `main`; Step 5 work is based on `ae22f7a`.
- Raw firmware, images, phone/location data, APK/ODEX/shared libraries, and extracted binaries stay local and ignored; none belong in Git.
- Pristine backup: `/Users/bmreyes24/ClarityLab/backups/CLARITY_BACKUP_20260918_0225_ORIGINAL` is read-only and unchanged.
- Verified forensic original: `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_ORIGINAL` is immutable; analysis uses the separate `..._COMPLETE_WORKING` copy.
- No on-car write, flash, remount, bus action, or capture occurred in Step 5.

## Confirmed evidence

- Honda Hack casting mirrors the center CarPlay screen into the cluster; it follows Maps→Music. Spoken guidance remained audible during casting.
- Android Waze running on the head unit can show a Honda cluster arrow/distance independently; it clears on route end. This does not prove iPhone CarPlay metadata.
- Copied `jmcs` statically configures one main CarPlay screen (800×480, max 30 FPS, hifi touch). Its proxy screen callback is singleton. The raw iAP2 exchange was never captured.
- Two NVIDIA H.264 decoder objects each produced 28/30 frames in a short, disconnected-CarPlay test. Active CarPlay coexistence and second-Surface rendering remain untested.
- The verified raw forensic acquisition is local/outside Git. Steps 1–4 deliverables and prior evidence ledger are pushed.

## Step 5 result

- **Factory safe area:** unknown. The Honda Hack cast area is `(0,24,584,191)` in its own 584×215 layout. The primary display is 800×480. No transform between them or OEM Navigation safe bounds is established.
- **iAP2 Identification:** not reconstructed. Static `jmcs` identifies state routines, but the exact message bytes/IDs/order/UUID are unavailable. The CarPlay screen descriptor follows a separate AirPlay receiver display-info path.
- **Step 6 ready:** no. See `step-reports/05-protocol-gaps.md` for the exact missing captures.

## Current authoritative files

- `NEXT_ACTION.md` — one next action.
- `EVIDENCE_INDEX.md` — concise artifact/evidence map.
- `research/navigation-safe-area.md` — rectangle candidates and missing geometry observation.
- `research/iap2-identification.md` — static model and passive capture plan.
- `step-reports/05-protocol-gaps.md` — Step 5 gate outcome.
- `step-reports/RUN_STATUS.md` — concise session log.
