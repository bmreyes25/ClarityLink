# MY16ADA storage map — historical, pending fresh read-only inventory

**Status:** provisional. Values below come from the saved September 18, 2026 `partitions.txt`, `emmc-layout.txt`, `partition-names.txt`, `mounts.txt`, and `mtd.txt` at the analysis root. On September 25, `adb devices -l` listed no device and `/Volumes/CLARITY` was absent, so no current device size, USB free-space value, boot-area accessibility, or applet list has been verified. **Do not run a bulk acquisition from this map alone.** The first connected step is the command set in [READ_ONLY_INVENTORY.md](READ_ONLY_INVENTORY.md); reconcile its output with this file and then generate/review the exact acquisition manifest.

## Historical block topology

`/proc/partitions` reports Linux 1 KiB blocks. The raw eMMC user area was **7,372,800 KiB = 7,549,747,200 bytes = 7.03125 GiB**, 14,745,600 logical 512-byte sectors. `fdisk -l` reported a protective MBR/GPT entry; it did not fully enumerate GPT contents. The by-name symlinks and mounts establish the following mapping:

| Device | Historical size | Name | Mount | FS / mount state | Proposed acquisition |
|---|---:|---|---|---|---|
| `/dev/block/mmcblk0` | 7,549,747,200 B | eMMC user area | multiple | mixed/live | numbered ~1 GiB raw chunks; includes partition table, all listed and unknown partitions, and slack |
| `mmcblk0p1` | 1,048,576 KiB | CAC | `/cache` | ext4, rw | included in raw eMMC; filesystem archive only if separately justified |
| `mmcblk0p2` | 786,432 KiB | CAP | `/system/vendor` | ext4, ro | included in raw; prior `system-vendor.tar` exists |
| `mmcblk0p3` | 524,288 KiB | APP | `/system` | ext4, ro | included in raw; prior `system-vendor.tar` exists |
| `mmcblk0p4` | 131,072 KiB | LOG | `/log` | ext4, rw | included in raw; inventory bounded logs only |
| `mmcblk0p5` | 1,048,576 KiB | MITSU | `/data/MitsubishiElectric` | ext4, rw | included in raw; filesystem archive in separate phase |
| `mmcblk0p6` | 131,072 KiB | SDA | `/mnt/data1` | ext4, rw | included in raw; filesystem archive in separate phase |
| `mmcblk0p7` | 131,072 KiB | SDA2 | `/mnt/data2` | ext4, rw | included in raw; filesystem archive in separate phase |
| `mmcblk0p8` | 1,048,576 KiB | SDC | `/mnt/media` | ext4, rw | included in raw; filesystem archive in separate phase |
| `mmcblk0p9` | 2,490,368 KiB | UDA | `/data` | ext4, rw | included in raw; live filesystem archive may have transient errors |

`mmcblk0boot0`, `mmcblk0boot1`, and `mmcblk0rpmb` were **not recorded** in the saved `/proc/partitions`. Fresh inventory must determine whether they exist. Boot0/boot1 are optional *read-only* sources only if exposed and readable without changing `force_ro` or protection state. RPMB is inventory-only.

The saved `mmcblk1` (15,826,944 KiB) with a vfat partition mounted at `/storage/sdcard1` is removable/storage media, **not** part of the raw head-unit eMMC request. The saved `sda` (121,020,416 KiB) and `sda1` mounted at `/mnt/usbdrive1` are the USB destination, **never** image sources or device-level output targets.

## Historical NOR/MTD topology

These names and sizes come from `/proc/mtd`. Recheck the live device names and readability before choosing sources. The prior verified `nor-whole-device.img` is 67,108,864 bytes and remains untouched.

| Device | Size | Name | Proposed method |
|---|---:|---|---|
| `mtdblock0` | 2,097,152 B | USP | separate read-only image if exposed |
| `mtdblock1` | 8,388,608 B | recovery | separate read-only image if exposed |
| `mtdblock2` | 8,388,608 B | boot | separate read-only image if exposed |
| `mtdblock3` | 2,097,152 B | app_datas | separate read-only image if exposed |
| `mtdblock4` | 262,144 B | app_datas_ex | separate read-only image if exposed |
| `mtdblock5` | 2,097,152 B | misc | separate read-only image if exposed |
| `mtdblock6` | 3,145,728 B | kpanic | separate read-only image if exposed |
| `mtdblock7` | 67,108,864 B | whole_device | separate read-only image; compare hash/size to old verified NOR image after Mac copy |

Only documented storage devices listed by `/proc/mtd` and corresponding `/dev/block/mtdblock*` may be read. Do not probe arbitrary `/dev` character devices, erase MTD, or write any block device.

## Consistency and scope

The raw `/dev/block/mmcblk0` image is a **live** acquisition. Writable ext4 filesystems can change while chunks are read, so reconstructed filesystem state may not be atomic. Never unmount live partitions to improve consistency. The separate archives and runtime snapshots provide context but do not turn the raw image into a snapshot.

This is a head-unit acquisition, not a dump of unrelated vehicle ECUs or safety systems. A fuller disk image strengthens offline analysis and recovery evidence, but does not replace the plan's boot-independent restoration gate.
