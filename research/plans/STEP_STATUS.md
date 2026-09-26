# Clarity second-display step status — 2026-09-25

This is a compact status index for the local model. The detailed exit criteria remain in [the 12-step plan](CARPLAY_SECOND_DISPLAY_REVIEW.plan.md). A passing simulator assertion does not prove a receiver feature.

| Step | Status | Evidence / remaining gate |
|---|---|---|
| 1 Git/evidence baseline | Complete | Private GitHub repo and sanitized research baseline exist. Raw firmware excluded from Git. |
| F-A Acquisition design | Complete | Read-only storage inventory, USB layout, chunk manifest, script guards, and run card documented. |
| F-B Forensic acquisition | Partial | Eight eMMC chunks, eight MTD images, `/system` tar and seven metadata files verified; remaining archives/metadata/runtime states absent. See [status](../acquisition/FORENSIC_STATUS_20260925.md). |
| 2 Infotainment twin | In progress | Existing tests replay observed Maps→Music mirroring, head-unit Waze arrow cleanup, and a separately labeled hypothetical independent stream. A sanitized, GPT-CRC-validated nine-partition storage fixture now seeds the firmware catalog; deeper app/service ownership fixtures remain. |
| 3 Decoder coexistence probe prep | In progress | Earlier CarPlay-disconnected probe measured 28/30 frames per decoder. A Mac-only trace scorer now encodes the 95%/250-ms/EOS gate; the background-safe APK and reviewed run card have not been built. |
| 4 Active-CarPlay decoder test | Pending car/review | No active-CarPlay coexistence measurement. |
| 5 Static Identification reconstruction | In progress | Main-screen registration and singleton proxy callback found; raw actual Identification bytes remain unavailable. |
| 6 Protocol capture | Conditional pending | Only if Step 5 leaves a material unknown and a bench-validated capture method exists. |
| 7 Branch/ABI design | Pending | Requires protocol and receiver evidence; `unknown` remains an allowed verdict. |
| 8 Boot-independent recovery | Pending | A complete raw image does not prove restoration without Android/ADB. |
| 9 Offline candidate | Pending | No verified iPhone second-stream candidate yet. |
| 10 Synthetic renderer on car | Pending separate approval | Only after exact artifact/run card. |
| 11 Receiver on car | Blocked by Step 8 and 9 gates | No receiver patch or interposer installed. |
| 12 Apple Maps/Waze acceptance | Pending | Native independent iPhone cluster display has not been achieved. |

Current offline work: inspect the verified working image, strengthen Step 2's forensic catalog and display ownership fixtures, prepare Step 3's bounded probe, and continue Step 5 copied-binary analysis. Next parked session can resume F-B from the [exact run card](../acquisition/RESUME_RUN_CARD_20260925.md) after review. The same USB contains the old backup, which remains immutable.
