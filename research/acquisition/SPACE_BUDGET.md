# Forensic USB space budget — provisional

The USB is not mounted on the Mac and ADB currently lists no device, so **free space is unknown**. The user's approximately 114 GB figure is an estimate, not a verified preflight result. The September 18 saved inventory gives the following *historical* inputs:

| Item | Bytes | GiB |
|---|---:|---:|
| Full `/dev/block/mmcblk0` user area | 7,549,747,200 | 7.03125 |
| Eight separate MTD block images (including 64 MiB whole-device) | 93,585,408 | 0.08715 |
| Five prior filesystem archives combined | 1,040,515,072 | 0.96905 |
| Boot0/boot1 | unknown | unknown |
| Metadata/runtime snapshots | unknown, expected small | unknown |

The eMMC chunk plan for the **historical size** is seven 1,073,741,824-byte chunks plus one 33,554,432-byte chunk. Every chunk is below FAT32's 4 GiB single-file limit. The generator must recompute this from fresh `/sys/block/mmcblk0/size` and logical block size; these counts are not authorization to acquire.

For advance planning, budget **at least 20 GiB free** before starting: full eMMC + all historical MTD images + twice the prior archive total as a live-data allowance + 2 GiB spare, rounded up. That calculation is approximately 11.06 GiB before rounding; the 20 GiB floor leaves roughly 8.9 GiB more for boot regions, duplicate live filesystem archives, metadata, vfat overhead, and growth. The generator uses the larger of this floor and a fresh calculation based on current block sizes plus twice the current `du` total plus 2 GiB spare. **Exact future tar output size is unknowable without copying a live changing filesystem**; this is a conservative preflight budget, not an exact output-size promise. Each archive also gets its own live free-space and FAT32-size guard. If a dependable filesystem estimate is unavailable, generation stops. **Abort if live `df` free space is below the required amount. Never delete existing USB data to make room.**

Disk speed is also unmeasured. A full read plus on-USB hashing can take longer than a short diagnostic session. The acquisition script must checkpoint at each completed chunk and permit a reviewed resume; do not promise a 10-minute car session before timing a harmless read-only benchmark or confirming the user's available time.
