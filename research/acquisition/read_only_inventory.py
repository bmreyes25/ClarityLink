#!/usr/bin/env python3
"""Collect allowlisted storage facts over ADB, writing only to the Mac.

This does not connect ADB, install packages, or write to Android/USB. The
optional existing-root pass uses only read commands through the already
installed su facility. Every failure is preserved as an unavailable result.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
COMMANDS: dict[str, tuple[str, ...]] = {
    "id": ("id",),
    "proc-partitions": ("cat", "/proc/partitions"),
    "proc-mtd": ("cat", "/proc/mtd"),
    "proc-mounts": ("cat", "/proc/mounts"),
    "fdisk-mmcblk0": ("fdisk", "-l", "/dev/block/mmcblk0"),
    "dev-mmc": ("ls", "-l", "/dev/block/mmcblk0", "/dev/block/mmcblk0p*", "/dev/block/mmcblk0boot*", "/dev/block/mmcblk0rpmb"),
    "dev-mtdblock": ("ls", "-l", "/dev/block/mtdblock*"),
    "by-name": ("ls", "-l", "/dev/block/platform/sdhci-tegra.3/by-name"),
    "root-startup-list": ("ls", "-ld", "/init", "/init.rc", "/init.*.rc", "/default.prop", "/ueventd.*", "/sbin"),
    "emmc-sectors": ("cat", "/sys/block/mmcblk0/size"),
    "emmc-logical-block": ("cat", "/sys/block/mmcblk0/queue/logical_block_size"),
    "boot0-sectors": ("cat", "/sys/block/mmcblk0boot0/size"),
    "boot0-force-ro": ("cat", "/sys/block/mmcblk0boot0/force_ro"),
    "boot1-sectors": ("cat", "/sys/block/mmcblk0boot1/size"),
    "boot1-force-ro": ("cat", "/sys/block/mmcblk0boot1/force_ro"),
    "usb-df": ("busybox", "df", "-k", "/mnt/usbdrive1"),
    "usb-sda-sectors": ("cat", "/sys/block/sda/size"),
    "usb-serial": ("cat", "/sys/block/sda/device/../../../../serial"),
    "usb-blkid": ("busybox", "blkid", "/dev/block/sda1"),
    "filesystem-du": ("du", "-sk", "/system", "/data", "/mnt/data1", "/mnt/data2", "/mnt/media"),
    "usb-root": ("ls", "-la", "/mnt/usbdrive1"),
    "backup-dir": ("ls", "-ld", "/mnt/usbdrive1/CLARITY_BACKUP_20260918_0225"),
    "busybox-applets": ("busybox", "--list"),
    "available-tools": ("which", "dd", "sha256sum", "wc", "tar", "df", "du", "awk", "mv", "mkdir", "sync"),
}
ROOT_COMMANDS: dict[str, str] = {
    "fdisk-mmcblk0-root": "busybox fdisk -l /dev/block/mmcblk0",
    "filesystem-du-root": "busybox du -sk /system /data /mnt/data1 /mnt/data2 /mnt/media",
    "extra-filesystem-du-root": "busybox du -sk /system/vendor /data/MitsubishiElectric /sbin",
    "usb-blkid-root": "busybox blkid /dev/block/sda1",
    "boot-regions-root": "busybox ls -l /dev/block/mmcblk0boot0 /dev/block/mmcblk0boot1 /dev/block/mmcblk0rpmb",
}


def inventory(serial: str, output: Path, timeout: int = 20, existing_root: bool = False) -> dict[str, object]:
    if not serial or any(c.isspace() for c in serial):
        raise ValueError("ADB serial must be a nonempty token")
    if output.exists():
        raise FileExistsError(f"refusing to reuse output directory: {output}")
    output.mkdir(parents=True)
    manifest: dict[str, object] = {"serial": serial, "captured_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "commands": {}}
    for name, remote in COMMANDS.items():
        command = ["adb", "-s", serial, "shell", *remote]
        try:
            proc = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
            stdout = proc.stdout[:512_000]
            stderr = proc.stderr[:64_000]
            code: int | str = proc.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = (exc.stdout or b"")[:512_000]
            stderr = (exc.stderr or b"")[:64_000] + b"\nTIMEOUT\n"
            code = "timeout"
        (output / f"{name}.stdout.txt").write_bytes(stdout)
        (output / f"{name}.stderr.txt").write_bytes(stderr)
        manifest["commands"][name] = {"argv": command, "exit": code, "stdout_bytes_saved": len(stdout), "stderr_bytes_saved": len(stderr)}
    mtd_text = (output / "proc-mtd.stdout.txt").read_text(errors="replace")
    source_paths = ["/dev/block/mmcblk0", "/dev/block/mmcblk0boot0", "/dev/block/mmcblk0boot1"]
    source_paths.extend(f"/dev/block/mtdblock{index}" for index in re.findall(r"^mtd(\d+):", mtd_text, re.M))
    for source in source_paths:
        name = "readable-" + source.rsplit("/", 1)[-1]
        # Pre-shell-v2 ADB can report adb's exit code rather than the remote
        # test's. Require an explicit remote status marker to avoid treating
        # unreadable block devices as readable.
        command = ["adb", "-s", serial, "shell", f"test -r {source}; echo __CLARITY_READ_EXIT__:$?"]
        try:
            proc = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
            stdout = proc.stdout[:64_000]
            match = re.search(rb"__CLARITY_READ_EXIT__:([0-9]+)\s*\Z", stdout)
            code = int(match.group(1)) if proc.returncode == 0 and match else "unknown"
            stderr = proc.stderr[:64_000]
        except subprocess.TimeoutExpired as exc:
            code = "timeout"
            stdout = (exc.stdout or b"")[:64_000]
            stderr = (exc.stderr or b"")[:64_000] + b"\nTIMEOUT\n"
        (output / f"{name}.stdout.txt").write_bytes(stdout)
        (output / f"{name}.stderr.txt").write_bytes(stderr)
        manifest["commands"][name] = {"argv": command, "exit": code, "stdout_bytes_saved": len(stdout), "stderr_bytes_saved": len(stderr)}
    if existing_root:
        root_commands = {"root-id": "id", **ROOT_COMMANDS}
        root_commands.update({
            "readable-root-" + source.rsplit("/", 1)[-1]: f"test -r {source}; echo __CLARITY_READ_EXIT__:$?"
            for source in source_paths
        })
        for name, remote in root_commands.items():
            command = ["adb", "-s", serial, "shell", "su", "-c", remote]
            try:
                proc = subprocess.run(command, capture_output=True, timeout=timeout, check=False)
                stdout = proc.stdout[:512_000]
                stderr = proc.stderr[:64_000]
                if name.startswith("readable-root-"):
                    match = re.search(rb"__CLARITY_READ_EXIT__:([0-9]+)\s*\Z", stdout)
                    code = int(match.group(1)) if proc.returncode == 0 and match else "unknown"
                else:
                    code = proc.returncode
            except subprocess.TimeoutExpired as exc:
                stdout = (exc.stdout or b"")[:512_000]
                stderr = (exc.stderr or b"")[:64_000] + b"\nTIMEOUT\n"
                code = "timeout"
            (output / f"{name}.stdout.txt").write_bytes(stdout)
            (output / f"{name}.stderr.txt").write_bytes(stderr)
            manifest["commands"][name] = {"argv": command, "exit": code, "stdout_bytes_saved": len(stdout), "stderr_bytes_saved": len(stderr)}
        root_id = (output / "root-id.stdout.txt").read_text(errors="replace")
        if "uid=0(root)" not in root_id:
            manifest["root_verified"] = False
        else:
            manifest["root_verified"] = True
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="serial from adb devices -l")
    parser.add_argument("--output", type=Path, help="new Mac output directory under research/acquisition/live-inventory")
    parser.add_argument("--existing-root-readonly", action="store_true", help="also use existing su for fixed read-only storage facts")
    args = parser.parse_args()
    base = (ROOT / "live-inventory").resolve()
    output = args.output or base / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    resolved = output.resolve()
    if resolved == base or base not in resolved.parents:
        parser.error(f"output must be a new directory beneath {base}")
    result = inventory(args.serial, resolved, existing_root=args.existing_root_readonly)
    failures = [name for name, info in result["commands"].items() if info["exit"] != 0]
    print(json.dumps({"output": str(resolved), "commands": len(COMMANDS), "unavailable": failures}, indent=2))


if __name__ == "__main__":
    main()
