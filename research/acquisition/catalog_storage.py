#!/usr/bin/env python3
"""Build a sanitized storage fixture from a verified working eMMC image."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import uuid
import zlib
from pathlib import Path

SECTOR = 512


def read_header(source, lba: int) -> tuple[bytes, dict[str, int]]:
    source.seek(lba * SECTOR)
    raw = source.read(SECTOR)
    if raw[:8] != b"EFI PART":
        raise ValueError(f"missing GPT header at LBA {lba}")
    size, stored_crc = struct.unpack_from("<II", raw, 12)
    if not 92 <= size <= SECTOR:
        raise ValueError("invalid GPT header size")
    checked = bytearray(raw[:size])
    checked[16:20] = b"\0" * 4
    if zlib.crc32(checked) != stored_crc:
        raise ValueError(f"GPT header CRC mismatch at LBA {lba}")
    current, backup, first, last = struct.unpack_from("<QQQQ", raw, 24)
    entries_lba = struct.unpack_from("<Q", raw, 72)[0]
    count, entry_size, entries_crc = struct.unpack_from("<III", raw, 80)
    if current != lba or not 128 <= entry_size <= 4096 or not 1 <= count <= 1024:
        raise ValueError("unsupported GPT header fields")
    return raw, {
        "crc": stored_crc, "backup": backup, "first": first, "last": last,
        "entries_lba": entries_lba, "count": count, "entry_size": entry_size,
        "entries_crc": entries_crc,
    }


def mount_index(path: Path) -> dict[str, dict[str, object]]:
    result = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) < 4 or "/by-name/" not in fields[0]:
            continue
        name = fields[0].rsplit("/", 1)[-1]
        if name in result:
            raise ValueError(f"duplicate mount: {name}")
        result[name] = {"path": fields[1], "filesystem": fields[2], "read_only": "ro" in fields[3].split(",")}
    return result


def catalog(image: Path, mounts: Path) -> dict[str, object]:
    if image.is_symlink():
        raise ValueError("image symlink is not allowed")
    image = image.resolve(strict=True)
    if not image.is_file() or image.stat().st_size % SECTOR:
        raise ValueError("image missing, symlink, or not sector-aligned")
    sidecar = image.with_suffix(image.suffix + ".sha256")
    expected, filename = sidecar.read_text().strip().split("  ", 1)
    if filename != image.name or len(expected) != 64:
        raise ValueError("invalid reconstructed-image checksum sidecar")
    digest = hashlib.sha256()
    with image.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected:
        raise ValueError("reconstructed image checksum mismatch")
    sectors = image.stat().st_size // SECTOR
    mounted = mount_index(mounts)
    partitions = []
    with image.open("rb") as source:
        _, primary = read_header(source, 1)
        _, backup = read_header(source, sectors - 1)
        if primary["backup"] != sectors - 1 or backup["backup"] != 1 or primary["entries_crc"] != backup["entries_crc"]:
            raise ValueError("primary/backup GPT disagree")
        source.seek(primary["entries_lba"] * SECTOR)
        entries = source.read(primary["count"] * primary["entry_size"])
        if len(entries) != primary["count"] * primary["entry_size"] or zlib.crc32(entries) != primary["entries_crc"]:
            raise ValueError("GPT entry-array CRC mismatch")
        source.seek(backup["entries_lba"] * SECTOR)
        backup_entries = source.read(backup["count"] * backup["entry_size"])
        if backup["count"] != primary["count"] or backup["entry_size"] != primary["entry_size"] or backup_entries != entries:
            raise ValueError("primary/backup GPT entry arrays disagree")
        for index in range(primary["count"]):
            entry = entries[index * primary["entry_size"]:(index + 1) * primary["entry_size"]]
            if entry[:16] == b"\0" * 16:
                continue
            start, end = struct.unpack_from("<QQ", entry, 32)
            if not primary["first"] <= start <= end <= primary["last"]:
                raise ValueError(f"partition {index + 1} outside GPT usable region")
            name = entry[56:min(128, len(entry))].decode("utf-16le", "replace").rstrip("\0")
            source.seek(start * SECTOR + 1080)
            ext4 = source.read(2) == b"\x53\xef"
            partitions.append({
                "index": index + 1,
                "name": name,
                "start_lba": start,
                "end_lba": end,
                "size_bytes": (end - start + 1) * SECTOR,
                "ext4_superblock_signature": ext4,
                "mount": mounted.get(name),
            })
    if len({p["name"] for p in partitions}) != len(partitions):
        raise ValueError("duplicate GPT partition name")
    return {
        "source": "verified partial forensic eMMC user-area image; live, non-atomic",
        "image_bytes": image.stat().st_size,
        "gpt_primary_header_crc32": f"{primary['crc']:08x}",
        "gpt_backup_header_crc32": f"{backup['crc']:08x}",
        "gpt_entry_array_crc32": f"{primary['entries_crc']:08x}",
        "partitions": partitions,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("mounts", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = catalog(args.image, args.mounts)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"cataloged {len(result['partitions'])} partitions to {args.output}")
