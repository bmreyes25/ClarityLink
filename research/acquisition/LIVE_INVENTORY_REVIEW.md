# September 25 head-unit inventory: acquisition review packet

The parked, read-only storage inventory is complete. Raw output is local and ignored by Git at `research/acquisition/live-inventory/20260925T210625Z/`. The exact generated files are local and ignored at `research/acquisition/generated/20260925_211500/`:

- `ACQUISITION_MANIFEST.json` — SHA-256 `062f663e68693eae6d110c4ded0816da1d25888f73264c30153d26befa1da0ce`; identifies every selected source and expected output length.
- `acquire_headunit.sh` — SHA-256 `e363beeef75a1e308f07bb9adf9f3173dcb0f7c46bc5c23bac209617b48a0a12`; generated for **review only**; no bulk copy has run.

## Confirmed device facts

| Fact | Live result |
|---|---:|
| eMMC user area `/dev/block/mmcblk0` | 7,549,747,200 bytes; 14,745,600 × 512-byte sectors |
| eMMC chunks | Seven × 1 GiB, then one × 32 MiB |
| Documented/readable MTD regions | Eight, totaling 93,585,408 bytes |
| boot0 / boot1 / RPMB device nodes | Absent; no acquisition commands generated |
| USB mount | `/mnt/usbdrive1`, vfat, `/dev/block/vold/8:1` |
| USB free at inventory | 119,880,800 KiB (about 114.3 GiB) |
| Generated minimum free requirement | 20,971,520 KiB (20 GiB) |
| Existing backup hashes checked on USB | `boot.img`, `recovery.img`, `nor-whole-device.img`: 3/3 matched |

The ordinary ADB shell cannot read the raw devices. The installed `su` facility returned `uid=0(root)` and fixed **read-only** tests passed for eMMC and all eight MTD blocks. The script requires that same existing root context; it does not change root configuration. The USB serial and FAT UUID are retained only in the ignored local manifest and transcript.

## Review before the long copy

1. Read the [run card](ON_CAR_FORENSIC_ACQUISITION_RUN_CARD.md), [storage map](STORAGE_MAP.md), and [space budget](SPACE_BUDGET.md).
2. Inspect the exact local generated manifest and shell script. Check the eight `mmcblk0.part*` expected lengths, eight documented `mtdblock*` sources, and every destination under the new `CLARITY_FORENSIC_20260925_211500` sibling. Confirm there is no block-device output path, remount, protection change, or safety-bus command.
3. Arrange a parked power window longer than the short diagnostics used earlier. The full eMMC read, USB write, and hashing time has not been measured; do not promise completion in ten minutes. The script checkpoints completed chunks and preserves interrupted partials for review.
4. Before execution, recheck that the same USB is mounted, the old backup exists and its three known hashes match, USB free space still exceeds the generated floor, and no sibling with the selected name exists. The generated script enforces those checks again.
5. Collect the eight labeled runtime states in the run card, then perform the separately reviewed copy. Keep raw output and phone/location data local.

**Status:** inventory and script generation complete; parked bulk acquisition and runtime-state capture pending review. A raw live image will not be an atomic filesystem snapshot. Recovery after a failed receiver start still requires separate boot-independent proof.
