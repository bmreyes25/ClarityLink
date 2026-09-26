#!/usr/bin/env python3
"""Verify new USB forensic sibling and add runtime snapshots, then mark complete.

Mac-only and review-gated. Never touches the existing backup sibling. Does not
copy to the future immutable/working Mac forensic directories; that is later.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
from pathlib import Path

from runtime_snapshot import STATES


HASH_LINE = re.compile(r"([0-9a-f]{64})  ([^\n]+)\Z")
RUN_RE = re.compile(r"CLARITY_FORENSIC_([0-9]{8}_[0-9]{6})\Z")
ARCHIVES = {
    "filesystems/system.tar", "filesystems/system-vendor.tar", "filesystems/data-live.tar",
    "filesystems/mitsubishi-live.tar", "filesystems/data1-live.tar",
    "filesystems/data2-live.tar", "filesystems/media-live.tar", "filesystems/root-startup.tar",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_paths(manifest: dict[str, object]) -> set[str]:
    paths = {"ACQUISITION_MANIFEST.json"}
    paths.update(str(x["name"]) for x in manifest["chunks"])
    paths.update(f"mtd/mtdblock{x['index']}-{x['name']}.img" for x in manifest["mtd"])
    paths.update(f"boot-regions/{x['name']}.img" for x in manifest["boot_read_only_candidates"])
    paths.update(ARCHIVES)
    return paths


def read_hashes(folder: Path) -> dict[str, str]:
    results: dict[str, str] = {}
    for line in (folder / "SHA256SUMS").read_text().splitlines():
        found = HASH_LINE.fullmatch(line)
        if not found:
            raise ValueError(f"invalid SHA256SUMS line: {line[:80]!r}")
        digest, relative = found.groups()
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or relative in results:
            raise ValueError(f"unsafe or duplicate hash path: {relative}")
        results[relative] = digest
    return results


def verify_hashes(folder: Path, hashes: dict[str, str]) -> None:
    for relative, want in hashes.items():
        path = folder / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"hashed file missing/not regular: {relative}")
        if sha256(path) != want:
            raise ValueError(f"hash mismatch: {relative}")


def finalize(usb_root: Path, folder: Path, manifest_path: Path, runtime_source: Path) -> dict[str, int]:
    usb_root = usb_root.resolve(strict=True)
    folder = folder.resolve(strict=True)
    match = RUN_RE.fullmatch(folder.name)
    manifest = json.loads(manifest_path.read_text())
    if folder.parent != usb_root or not match or match.group(1) != manifest["run_id"]:
        raise ValueError("forensic folder is not the expected direct USB sibling")
    if not (usb_root / "CLARITY_BACKUP_20260918_0225").is_dir():
        raise ValueError("existing backup sibling missing")
    usb_manifest_path = folder / "ACQUISITION_MANIFEST.json"
    if not usb_manifest_path.is_file() or sha256(usb_manifest_path) != sha256(manifest_path):
        raise ValueError("USB manifest does not match the reviewed generated manifest")
    for name in ("README.txt", "device-map.txt", "acquisition.log", "STORAGE_DONE.txt", "SHA256SUMS"):
        if not (folder / name).is_file():
            raise ValueError(f"required acquisition file missing: {name}")
    if (folder / "FINISHED.txt").exists():
        raise ValueError("already finalized")
    partials = [str(x.relative_to(folder)) for x in folder.rglob("*.partial")]
    if partials:
        raise ValueError(f"partial outputs present: {partials[:8]}")
    hashes = read_hashes(folder)
    required = expected_paths(manifest)
    if missing := required - hashes.keys():
        raise ValueError(f"selected acquisition files missing from SHA256SUMS: {sorted(missing)}")
    for chunk in manifest["chunks"]:
        path = folder / chunk["name"]
        if path.stat().st_size != chunk["expected_bytes"]:
            raise ValueError(f"eMMC chunk size mismatch: {chunk['name']}")
    verify_hashes(folder, hashes)
    if runtime_source.is_symlink():
        raise ValueError("runtime source root is a symlink")
    runtime_source = runtime_source.resolve(strict=True)
    if not runtime_source.is_dir():
        raise ValueError("runtime source missing")
    if {x.name for x in runtime_source.iterdir()} != set(STATES):
        raise ValueError("runtime source has missing or unexpected state directories")
    capture_times = []
    optional_failures = 0
    for state in STATES:
        if (runtime_source / state).is_symlink() or (runtime_source / state).resolve(strict=True).parent != runtime_source:
            raise ValueError(f"runtime state is a symlink or escapes session root: {state}")
        state_manifest_path = runtime_source / state / "manifest.json"
        if not state_manifest_path.is_file():
            raise ValueError(f"runtime state missing: {state}")
        state_manifest = json.loads(state_manifest_path.read_text())
        if state_manifest.get("state") != state or state_manifest.get("serial") != manifest["serial"]:
            raise ValueError(f"runtime manifest state/serial mismatch: {state}")
        capture_times.append(dt.datetime.fromisoformat(state_manifest["utc"]))
        commands = state_manifest.get("commands", {})
        mandatory = {"ps", "services", "packages", "getprop", "display", "window", "surfaceflinger", "activity"}
        if not mandatory.issubset(commands):
            raise ValueError(f"runtime command manifest incomplete: {state}")
        for decisive in ("ps", "display", "window", "surfaceflinger", "activity"):
            if commands[decisive].get("exit") != 0 or commands[decisive].get("stdout_bytes_saved", 0) <= 0:
                raise ValueError(f"runtime decisive capture failed: {state}/{decisive}")
        optional_failures += sum(1 for info in commands.values() if info.get("exit") != 0)
    if max(capture_times) - min(capture_times) > dt.timedelta(hours=24):
        raise ValueError("runtime states span more than 24 hours; review stale state folders")
    destination = folder / "runtime"
    if any(destination.iterdir()):
        raise ValueError("USB runtime directory already contains files; inspect before finalizing")
    staging = folder / "runtime.__staging__"
    if staging.exists():
        raise ValueError("interrupted runtime staging exists; inspect before retry")
    source_hashes: dict[str, str] = {}
    for state in STATES:
        src = runtime_source / state
        if any(x.is_symlink() for x in src.rglob("*")):
            raise ValueError(f"runtime source contains symlink: {state}")
        for source_file in src.rglob("*"):
            if source_file.is_file():
                source_hashes[str(source_file.relative_to(runtime_source))] = sha256(source_file)
    shutil.copytree(runtime_source, staging)
    for relative, want in source_hashes.items():
        if sha256(staging / relative) != want:
            raise ValueError(f"runtime copy hash mismatch: {relative}")
    destination.rmdir()
    staging.rename(destination)
    retained: dict[str, str] = {}
    allowed_top = {
        "ACQUISITION_MANIFEST.json", "README.txt", "device-map.txt", "acquisition.log",
        "acquisition.log.original", "SHA256SUMS.original", "STORAGE_DONE.txt",
    }
    allowed_dirs = {"emmc", "mtd", "boot-regions", "filesystems", "metadata", "runtime"}
    for path in folder.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"symlink in forensic sibling: {path}")
        if not path.is_file() or path.name == "SHA256SUMS":
            continue
        relative = path.relative_to(folder)
        if len(relative.parts) == 1 and relative.name not in allowed_top:
            raise ValueError(f"unexpected top-level file: {relative}")
        if len(relative.parts) > 1 and relative.parts[0] not in allowed_dirs:
            raise ValueError(f"unexpected acquisition path: {relative}")
        retained[str(relative)] = sha256(path)
    if not required.issubset(retained):
        raise ValueError("selected acquisition output vanished during finalization")
    new_hashes_path = folder / "SHA256SUMS.rebuild"
    if new_hashes_path.exists():
        raise ValueError("interrupted checksum rebuild exists; inspect before retry")
    new_hashes_path.write_text("".join(f"{digest}  {relative}\n" for relative, digest in sorted(retained.items())))
    new_hashes_path.replace(folder / "SHA256SUMS")
    all_hashes = read_hashes(folder)
    verify_hashes(folder, all_hashes)
    error_sidecars = sum(1 for relative in retained if relative.endswith(".errors.txt") and (folder / relative).stat().st_size)
    unavailable = sum(1 for relative in retained if relative.endswith(".unavailable.txt"))
    (folder / "FINISHED.txt").write_text(
        f"Forensic acquisition verified on Mac. Retained files hashed: {len(all_hashes)}. Runtime states: {len(STATES)}.\n"
        f"Nonempty error sidecars: {error_sidecars}. Unavailable metadata results: {unavailable}. Runtime command failures: {optional_failures}.\n"
        "SHA256SUMS and this completion marker are intentionally not self-hashed. Live filesystem archives are not atomic snapshots.\n"
    )
    return {"hashed_files": len(all_hashes), "runtime_states": len(STATES), "runtime_command_failures": optional_failures}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--usb-root", required=True, type=Path)
    ap.add_argument("--forensic-dir", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--runtime-source", required=True, type=Path)
    args = ap.parse_args()
    print(json.dumps(finalize(args.usb_root, args.forensic_dir, args.manifest, args.runtime_source), indent=2))


if __name__ == "__main__":
    main()
