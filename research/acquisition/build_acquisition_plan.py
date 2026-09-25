#!/usr/bin/env python3
"""Generate an exact, reviewable USB acquisition script from fresh ADB inventory.

Generation is Mac-only. This program never invokes ADB or copies vehicle bytes.
The generated script must be reviewed separately before it is run on the car.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import math
import re
import textwrap
from pathlib import Path


HERE = Path(__file__).resolve().parent
ANALYSIS = HERE.parent.parent
ONE_MIB = 2**20
ONE_GIB = 2**30
PRIOR_ARCHIVES = (
    "honda-config.tar",
    "system-vendor.tar",
    "userdata-live.tar",
    "media-config.tar",
    "root-startup.tar",
)
REQUIRED_APPLETS = {"awk", "base64", "cat", "date", "dd", "df", "du", "grep", "id", "ls", "mkdir", "mv", "printf", "sha256sum", "tar", "wc"}
ROOT_STARTUP_PATHS = (
    "/init", "/init.rc", "/init.goldfish.rc", "/init.nv_dev_board.usb.rc",
    "/init.recovery.vcm30t30.rc", "/init.tf.rc", "/init.trace.rc",
    "/init.usb.rc", "/init.vcm30t30.rc", "/default.prop",
    "/ueventd.goldfish.rc", "/ueventd.rc", "/ueventd.vcm30t30.rc", "/sbin",
)
RUN_ID_RE = re.compile(r"[0-9]{8}_[0-9]{6}\Z")
MTD_RE = re.compile(r'^mtd(\d+):\s+([0-9a-fA-F]+)\s+[0-9a-fA-F]+\s+"([^"]+)"$', re.M)


def read_result(folder: Path, name: str, *, required: bool = True) -> str | None:
    manifest = json.loads((folder / "manifest.json").read_text())
    info = manifest["commands"].get(name)
    if not info or info["exit"] != 0:
        if required:
            raise ValueError(f"fresh inventory result unavailable: {name}")
        return None
    return (folder / f"{name}.stdout.txt").read_text(errors="replace")


def positive_int(text: str | None, label: str) -> int:
    if text is None or not re.fullmatch(r"[0-9]+\s*", text):
        raise ValueError(f"invalid {label}: {text!r}")
    value = int(text.strip())
    if value <= 0:
        raise ValueError(f"nonpositive {label}")
    return value


def parse_free_kib(df_text: str) -> int:
    for line in reversed(df_text.splitlines()):
        parts = line.split()
        if parts and parts[-1] == "/mnt/usbdrive1" and len(parts) >= 6 and parts[3].isdigit():
            return int(parts[3])
    raise ValueError("cannot establish USB available KiB from df output")


def parse_du_bytes(text: str) -> int:
    expected = {"/system", "/data", "/mnt/data1", "/mnt/data2", "/mnt/media"}
    sizes: dict[str, int] = {}
    for line in text.splitlines():
        pieces = line.split()
        if len(pieces) == 2 and pieces[0].isdigit() and pieces[1] in expected:
            sizes[pieces[1]] = int(pieces[0]) * 1024
    if sizes.keys() != expected:
        raise ValueError(f"filesystem du incomplete: {sorted(expected - sizes.keys())}")
    return sum(sizes.values())


def chunks(total_bytes: int, chunk_bytes: int = ONE_GIB) -> list[dict[str, int | str]]:
    if total_bytes <= 0 or chunk_bytes != ONE_GIB:
        raise ValueError("invalid chunk parameters")
    result = []
    for index, start in enumerate(range(0, total_bytes, chunk_bytes)):
        size = min(chunk_bytes, total_bytes - start)
        result.append({
            "index": index,
            "name": f"emmc/mmcblk0.part{index:03d}",
            "skip_mib": start // ONE_MIB,
            "count_mib": math.ceil(size / ONE_MIB),
            "expected_bytes": size,
        })
    return result


def build(folder: Path, run_id: str) -> dict[str, object]:
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run ID must be YYYYMMDD_HHMMSS")
    manifest = json.loads((folder / "manifest.json").read_text())
    root_verified = manifest.get("root_verified") is True
    captured = manifest.get("captured_utc", "")
    if not re.match(r"\d{4}-\d{2}-\d{2}T", captured):
        raise ValueError("inventory has no UTC timestamp")
    age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(captured)
    if age.total_seconds() < -300 or age.total_seconds() > 24 * 3600:
        raise ValueError("inventory is not fresh (must be within 24 hours)")
    mounts = read_result(folder, "proc-mounts")
    usb_mounts = [line.split()[0] for line in mounts.splitlines() if len(line.split()) >= 3 and line.split()[1:3] == ["/mnt/usbdrive1", "vfat"]]
    if len(usb_mounts) != 1:
        raise ValueError("USB not uniquely shown as vfat at /mnt/usbdrive1")
    usb_source = usb_mounts[0]
    if not re.fullmatch(r"/dev/block/[A-Za-z0-9_./:-]+", usb_source):
        raise ValueError("unexpected USB mount source")
    backup_listing = read_result(folder, "backup-dir")
    if "CLARITY_BACKUP_20260918_0225" not in backup_listing:
        raise ValueError("existing backup sibling not confirmed")
    root_listing = read_result(folder, "root-startup-list")
    listed_roots = {line.split()[-1].lstrip("/") for line in root_listing.splitlines() if line.startswith(("-", "d")) and line.split()}
    missing_roots = [path for path in ROOT_STARTUP_PATHS if path.lstrip("/") not in listed_roots]
    if missing_roots:
        raise ValueError(f"root-startup paths missing in fresh inventory: {missing_roots}")
    sibling = f"CLARITY_FORENSIC_{run_id}"
    if sibling in read_result(folder, "usb-root"):
        raise ValueError(f"forensic sibling already exists on USB: {sibling}; choose a new run ID")
    applets = set(read_result(folder, "busybox-applets").split())
    missing = REQUIRED_APPLETS - applets
    if missing:
        raise ValueError(f"required BusyBox applets unavailable: {sorted(missing)}")
    sectors = positive_int(read_result(folder, "emmc-sectors"), "eMMC sectors")
    if manifest["commands"].get("readable-root-mmcblk0" if root_verified else "readable-mmcblk0", {}).get("exit") != 0:
        raise ValueError("eMMC user area not readable by current ADB shell")
    usb_sectors = positive_int(read_result(folder, "usb-sda-sectors"), "USB sda sectors")
    usb_serial = read_result(folder, "usb-serial", required=False)
    blkid = read_result(folder, "usb-blkid-root" if root_verified else "usb-blkid", required=False)
    if usb_serial and re.fullmatch(r"[A-Za-z0-9._:-]{4,128}", usb_serial.strip()):
        usb_identity = {"mode": "sysfs-serial", "value": usb_serial.strip()}
    else:
        found = re.search(r'\bUUID="?([A-Za-z0-9-]+)"?', blkid or "")
        if not found or "blkid" not in applets:
            raise ValueError("no verified USB serial or FAT volume UUID; cannot bind destination identity")
        usb_identity = {"mode": "fat-uuid", "value": found.group(1)}
    logical = positive_int(read_result(folder, "emmc-logical-block"), "logical block size")
    if logical not in {512, 4096}:
        raise ValueError(f"unexpected logical block size: {logical}")
    # Linux /sys/block/*/size is reported in 512-byte sectors, even if the
    # logical block size differs. Keep both facts in the generated manifest.
    emmc_bytes = sectors * 512
    if emmc_bytes > 2**40:
        raise ValueError("implausibly large eMMC; review manually")
    mtd_text = read_result(folder, "proc-mtd")
    mtd_all = [{"index": int(i), "bytes": int(size, 16), "name": name} for i, size, name in MTD_RE.findall(mtd_text)]
    if not mtd_all or len({x["index"] for x in mtd_all}) != len(mtd_all):
        raise ValueError("MTD inventory absent or ambiguous")
    if any(not re.fullmatch(r"[A-Za-z0-9_-]+", x["name"]) for x in mtd_all):
        raise ValueError("MTD name not safe for generated path")
    readable_prefix = "readable-root-" if root_verified else "readable-"
    mtd = [x for x in mtd_all if manifest["commands"].get(f"{readable_prefix}mtdblock{x['index']}", {}).get("exit") == 0]
    mtd_unavailable = [x for x in mtd_all if x not in mtd]
    boot: list[dict[str, int | str]] = []
    for side in (0, 1):
        size_text = read_result(folder, f"boot{side}-sectors", required=False)
        if size_text is not None and manifest["commands"].get(f"{readable_prefix}mmcblk0boot{side}", {}).get("exit") == 0:
            boot_sectors = positive_int(size_text, f"boot{side} sectors")
            boot.append({"name": f"mmcblk0boot{side}", "sectors": boot_sectors, "bytes": boot_sectors * 512})
    free_kib = parse_free_kib(read_result(folder, "usb-df"))
    fs_bytes = parse_du_bytes(read_result(folder, "filesystem-du-root" if root_verified else "filesystem-du"))
    prior_bytes = sum((ANALYSIS / name).stat().st_size for name in PRIOR_ARCHIVES)
    archive_budget = max(2 * fs_bytes, 2 * prior_bytes)
    required_bytes = max(20 * ONE_GIB, emmc_bytes + sum(x["bytes"] for x in mtd) + sum(x["bytes"] for x in boot) + archive_budget + 2 * ONE_GIB)
    required_kib = math.ceil(required_bytes / 1024)
    if free_kib < required_kib:
        raise ValueError(f"USB free {free_kib} KiB < required {required_kib} KiB; do not delete old data")
    return {
        "run_id": run_id,
        "inventory": str(folder),
        "inventory_utc": captured,
        "serial": manifest.get("serial"),
        "requires_existing_root": root_verified,
        "usb_mount_source": usb_source,
        "usb_sda_sectors_512b": usb_sectors,
        "usb_identity": usb_identity,
        "emmc_sectors_512b": sectors,
        "emmc_logical_block_bytes": logical,
        "emmc_bytes": emmc_bytes,
        "chunks": chunks(emmc_bytes),
        "mtd": mtd,
        "mtd_unavailable": mtd_unavailable,
        "boot_read_only_candidates": boot,
        "rpmb": "inventory-only; never read secure contents",
        "filesystem_du_bytes": fs_bytes,
        "archive_budget_bytes": archive_budget,
        "usb_free_kib_at_inventory": free_kib,
        "required_free_kib": required_kib,
        "caveats": ["live raw image, not atomic", "generated commands require separate human review", "boot areas acquired only if already readable without force_ro changes"],
    }


def manifest_text(plan: dict[str, object]) -> str:
    return json.dumps(plan, sort_keys=True, indent=2) + "\n"


def render_script(plan: dict[str, object]) -> str:
    template = (HERE / "acquire_headunit.sh.in").read_text()
    payload = manifest_text(plan)
    encoded = base64.b64encode(payload.encode()).decode()
    manifest_emitter = "\n".join(f"        \"$BB\" printf '%s' '{part}'" for part in textwrap.wrap(encoded, 76))
    commands = []
    for chunk in plan["chunks"]:
        commands.append(f'copy_exact /dev/block/mmcblk0 {chunk["name"]} {chunk["expected_bytes"]} 1048576 {chunk["skip_mib"]} {chunk["count_mib"]}')
    for item in plan["boot_read_only_candidates"]:
        commands.append(f'copy_exact /dev/block/{item["name"]} boot-regions/{item["name"]}.img {item["bytes"]} 512 0 {item["sectors"]}')
    for item in plan["mtd"]:
        block = 65536
        count = math.ceil(item["bytes"] / block)
        commands.append(f'copy_exact /dev/block/mtdblock{item["index"]} mtd/mtdblock{item["index"]}-{item["name"]}.img {item["bytes"]} {block} 0 {count}')
    archives = [
        ("/system", "system.tar"),
        ("/system/vendor", "system-vendor.tar"),
        ("/data", "data-live.tar"),
        ("/data/MitsubishiElectric", "mitsubishi-live.tar"),
        ("/mnt/data1", "data1-live.tar"),
        ("/mnt/data2", "data2-live.tar"),
        ("/mnt/media", "media-live.tar"),
    ]
    archive_lines = [f"archive_dir {source} filesystems/{name}" for source, name in archives]
    replacements = {
        "@RUN_ID@": str(plan["run_id"]),
        "@REQUIRES_ROOT@": "1" if plan["requires_existing_root"] else "0",
        "@EXPECTED_SECTORS@": str(plan["emmc_sectors_512b"]),
        "@EXPECTED_LOGICAL_BLOCK@": str(plan["emmc_logical_block_bytes"]),
        "@REQUIRED_FREE_KIB@": str(plan["required_free_kib"]),
        "@EXPECTED_USB_MOUNT_SOURCE@": str(plan["usb_mount_source"]),
        "@EXPECTED_USB_SECTORS@": str(plan["usb_sda_sectors_512b"]),
        "@USB_ID_MODE@": str(plan["usb_identity"]["mode"]),
        "@USB_ID_VALUE@": str(plan["usb_identity"]["value"]),
        "@MANIFEST_SHA256@": hashlib.sha256(payload.encode()).hexdigest(),
        "@MANIFEST_BYTES@": str(len(payload.encode())),
        "@MANIFEST_EMIT_COMMANDS@": manifest_emitter,
        "@BLOCK_COPY_COMMANDS@": "\n".join(commands),
        "@FILESYSTEM_ARCHIVE_COMMANDS@": "\n".join(archive_lines),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    if re.search(r"@[A-Z_]+@", template):
        raise ValueError("unreplaced template token")
    if re.search(r"\bdd\s+[^\n]*of=/dev/(?:block|mtd)", template):
        raise ValueError("dangerous device output in generated script")
    return template


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--inventory", type=Path, required=True, help="fresh output from read_only_inventory.py")
    ap.add_argument("--run-id", required=True, help="unique YYYYMMDD_HHMMSS for new USB sibling")
    args = ap.parse_args()
    inventory = args.inventory.resolve()
    live_base = (HERE / "live-inventory").resolve()
    if live_base not in inventory.parents:
        ap.error("inventory must come from research/acquisition/live-inventory")
    plan = build(inventory, args.run_id)
    output = HERE / "generated" / args.run_id
    if output.exists():
        ap.error(f"generated output already exists: {output}")
    output.mkdir(parents=True)
    (output / "ACQUISITION_MANIFEST.json").write_text(manifest_text(plan))
    (output / "acquire_headunit.sh").write_text(render_script(plan))
    print(f"Generated for review only: {output}")
    print(f"eMMC bytes: {plan['emmc_bytes']}; chunks: {len(plan['chunks'])}; required free KiB: {plan['required_free_kib']}")


if __name__ == "__main__":
    main()
