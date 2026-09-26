#!/usr/bin/env python3
"""Reconstruct a verified eMMC user-area image in a writable Mac working copy.

This never opens the USB or any block device for writing. The output must not
exist; source chunks and their manifest are checked before publication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reconstruct(folder: Path, output: Path) -> tuple[int, str]:
    folder = folder.resolve(strict=True)
    output = output.absolute()
    if not output.parent.is_dir() or output.parent.resolve() != folder:
        raise ValueError("output must be directly inside the working-copy root")
    if output.exists() or output.is_symlink() or output.with_suffix(output.suffix + ".partial").exists():
        raise FileExistsError("image or partial output already exists")
    manifest = json.loads((folder / "ACQUISITION_MANIFEST.json").read_text())
    hashes = {}
    for line in (folder / "SHA256SUMS").read_text().splitlines():
        want, relative = line.split("  ", 1)
        if relative in hashes or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError("unsafe checksum manifest")
        hashes[relative] = want
    chunks = manifest["chunks"]
    if not chunks or len({x["name"] for x in chunks}) != len(chunks):
        raise ValueError("missing or duplicate eMMC chunks")
    total = 0
    for chunk in chunks:
        relative = chunk["name"]
        source = folder / relative
        if not relative.startswith("emmc/mmcblk0.part") or source.is_symlink():
            raise ValueError(f"unsafe source: {relative}")
        if chunk["skip_mib"] * 1024 * 1024 != total or chunk["count_mib"] * 1024 * 1024 != chunk["expected_bytes"]:
            raise ValueError(f"eMMC chunks are not contiguous: {relative}")
        if source.stat().st_size != chunk["expected_bytes"] or digest_file(source) != hashes[relative]:
            raise ValueError(f"source length or hash mismatch: {relative}")
        total += chunk["expected_bytes"]
    if total != manifest["emmc_bytes"]:
        raise ValueError("chunks do not span the declared eMMC size")
    partial = output.with_suffix(output.suffix + ".partial")
    whole = hashlib.sha256()
    written = 0
    try:
        with partial.open("xb") as target:
            for chunk in chunks:
                with (folder / chunk["name"]).open("rb") as source:
                    for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
                        target.write(block)
                        whole.update(block)
                        written += len(block)
            target.flush()
            os.fsync(target.fileno())
        if written != total:
            raise ValueError("reconstructed length mismatch")
        partial.replace(output)
        output.with_suffix(output.suffix + ".sha256").write_text(f"{whole.hexdigest()}  {output.name}\n")
        return written, whole.hexdigest()
    except Exception:
        partial.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("working_copy", type=Path)
    args = parser.parse_args()
    size, digest = reconstruct(args.working_copy, args.working_copy / "mmcblk0-full.img")
    print(f"reconstructed bytes={size} sha256={digest}")
