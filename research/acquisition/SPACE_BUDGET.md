# Forensic USB space budget — current inventory

The parked September 25 read-only inventory measured **119,880,800 KiB free** on `/mnt/usbdrive1` (about 114.3 GiB). The exact generated manifest is `research/acquisition/generated/20260925_211500/ACQUISITION_MANIFEST.json`; it must be reviewed before copying. The current inputs are:

| Item | Bytes | GiB |
|---|---:|---:|
| Full `/dev/block/mmcblk0` user area | 7,549,747,200 | 7.03125 |
| Eight separate MTD block images (including 64 MiB whole-device) | 93,585,408 | 0.08715 |
| Five prior filesystem archives combined | 1,040,515,072 | 0.96905 |
| Boot0/boot1 | 0 selected; device nodes absent | 0 |
| Current top-level filesystem `du` total | 1,062,993,920 | 0.98999 |
| Metadata/runtime snapshots | unknown, expected small | unknown |

The freshly generated eMMC chunk plan is seven 1,073,741,824-byte chunks plus one 33,554,432-byte chunk. Every chunk is below FAT32's 4 GiB single-file limit. These counts are **not authorization to acquire**.

The generator requires **at least 20 GiB free**: the larger of that floor and raw eMMC + selected MTD/boot bytes + twice the current `du` total or prior archive total + 2 GiB spare. The current arithmetic is about 11.1 GiB, so the 20 GiB floor governs. The current USB free space exceeds the floor by about 94.3 GiB. **Exact future tar output size is unknowable without copying a live changing filesystem**; this is a preflight budget, not an exact output-size promise. Each archive also gets its own live free-space and FAT32-size guard. Recheck `df` immediately before any approved acquisition. Abort if the requirement is not met; never delete existing USB data to make room.

Disk speed is also unmeasured. A full read plus on-USB hashing can take longer than a short diagnostic session. The acquisition script must checkpoint at each completed chunk and permit a reviewed resume; do not promise a 10-minute car session before timing a harmless read-only benchmark or confirming the user's available time.
