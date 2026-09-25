# Read-only inventory commands for the next parked connection

**Run only the inventory first. No `dd`, tar archive, install, mount, `force_ro` change, or vehicle-bus command belongs in this pass.** Save command outputs on the Mac under `research/acquisition/live-inventory/<UTC timestamp>/`; the head unit is a read-only source. If permission is denied, record it and stop that check.

Connect to Wirebug's current Wi-Fi ADB address, then run the commands below. Use the exact device serial returned by `adb devices -l`; the last known address was `192.168.86.102:5555`. `fdisk -l` may require existing root privileges; do not modify security settings to obtain it.

```sh
adb devices -l
adb -s SERIAL shell id
adb -s SERIAL shell cat /proc/partitions
adb -s SERIAL shell cat /proc/mtd
adb -s SERIAL shell cat /proc/mounts
adb -s SERIAL shell fdisk -l /dev/block/mmcblk0
adb -s SERIAL shell ls -l /dev/block/mmcblk0 /dev/block/mmcblk0p* /dev/block/mmcblk0boot* /dev/block/mmcblk0rpmb
adb -s SERIAL shell ls -l /dev/block/mtdblock*
adb -s SERIAL shell ls -l /dev/block/platform/sdhci-tegra.3/by-name
adb -s SERIAL shell ls -ld /init /init.rc /init.*.rc /default.prop /ueventd.* /sbin
adb -s SERIAL shell cat /sys/block/mmcblk0/size
adb -s SERIAL shell cat /sys/block/mmcblk0/queue/logical_block_size
adb -s SERIAL shell df -k /mnt/usbdrive1
adb -s SERIAL shell cat /sys/block/sda/size
adb -s SERIAL shell cat /sys/block/sda/device/serial
adb -s SERIAL shell busybox blkid /dev/block/sda1
adb -s SERIAL shell du -sk /system /data /mnt/data1 /mnt/data2 /mnt/media
adb -s SERIAL shell ls -ld /mnt/usbdrive1/CLARITY_BACKUP_20260918_0225
adb -s SERIAL shell ls -la /mnt/usbdrive1
adb -s SERIAL shell busybox --list
adb -s SERIAL shell which dd sha256sum wc tar df du awk mv mkdir sync
adb -s SERIAL shell 'test -r /dev/block/mmcblk0; echo __CLARITY_READ_EXIT__:$?'
adb -s SERIAL shell 'test -r /dev/block/mmcblk0boot0; echo __CLARITY_READ_EXIT__:$?'
adb -s SERIAL shell 'test -r /dev/block/mmcblk0boot1; echo __CLARITY_READ_EXIT__:$?'
# Repeat the marked read test only for mtdblock indices listed by the current /proc/mtd.
```

Use the printed `__CLARITY_READ_EXIT__` value for readability, rather than the Mac `adb` process status: older ADB versions may not propagate the remote command's exit code. A missing or malformed marker means the result is unknown and the acquisition generator must stop or omit that optional source.

Also inventory readable boot-area size and `force_ro` **without changing it** if the paths exist:

```sh
adb -s SERIAL shell cat /sys/block/mmcblk0boot0/size
adb -s SERIAL shell cat /sys/block/mmcblk0boot0/force_ro
adb -s SERIAL shell cat /sys/block/mmcblk0boot1/size
adb -s SERIAL shell cat /sys/block/mmcblk0boot1/force_ro
```

For a no-hand-typing run, `research/acquisition/read_only_inventory.py` performs only allowlisted reads and writes its transcript on the Mac. Review its source before use. Then update [STORAGE_MAP.md](STORAGE_MAP.md) with the fresh mapping, USB filesystem/free space, actual applets, and any unavailable results. **Only after that** generate the exact chunk manifest and seek review of the run card.

The later metadata pass may read `/proc/cpuinfo`, `/proc/meminfo`, `/proc/cmdline`, `/proc/version`, `/proc/modules`, `/proc/interrupts`, `/proc/devices`, `getprop`, and bounded existing sysfs names/properties. It must not recursively read arbitrary sysfs controls or access safety-related buses.
