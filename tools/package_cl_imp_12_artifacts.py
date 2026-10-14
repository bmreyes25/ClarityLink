#!/usr/bin/env python3
"""Package and attest local CL-IMP-12 API17/ARMv7 build outputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ANDROID = "{http://schemas.android.com/apk/res/android}"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def manifest_permissions(path: Path) -> tuple[str, list[str], bool]:
    root = ET.parse(path).getroot()
    app = root.find("application")
    if app is None:
        raise ValueError("application_manifest_missing")
    permissions = sorted({node.get(ANDROID + "name", "") for node in root.findall("uses-permission")})
    if "" in permissions:
        raise ValueError("permission_name_missing")
    return root.get("package", ""), permissions, app.get(ANDROID + "enabled", "true") == "false"


def require_regular_output(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"refusing symbolic-link output: {path.name}")
    if path.exists() and not path.is_file():
        raise ValueError(f"refusing non-file output: {path.name}")


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: package_cl_imp_12_artifacts.py REPOSITORY_ROOT NDK_ROOT")
    root = Path(sys.argv[1]).resolve()
    ndk = Path(sys.argv[2]).resolve()
    api17_root = root / "build/r7c/android-armv7"
    inputs = {
        "libclaritylink_android.armv7.so": api17_root / "libclaritylink_android.so",
        "claritylink-android-api17.jar": root / "build/r7c/claritylink-android-api17.jar",
        "claritylink-display-lab.apk": root / "build/cl-imp-03/claritylink-display-lab.apk",
        "claritylink-disabled-candidate.apk": root / "build/cl-imp-03/claritylink-disabled-candidate.apk",
        "api17-symbol-audit.json": root / "build/cl-imp-12/api17-symbol-audit.json",
    }
    for path in inputs.values():
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"required build output missing: {path}")
    native = inputs["libclaritylink_android.armv7.so"]
    readelf = ndk / "toolchains/llvm/prebuilt/darwin-x86_64/bin/llvm-readelf"
    elf = subprocess.run([str(readelf), "-h", "-d", str(native)], check=True,
                         capture_output=True, text=True).stdout
    if "ELF32" not in elf or "Machine:" not in elf or "ARM" not in elf:
        raise SystemExit("native artifact is not a 32-bit ARM shared library")
    needed = sorted({line.split("[")[-1].split("]")[0] for line in elf.splitlines()
                     if "(NEEDED)" in line and "[" in line})
    lab_package, lab_permissions, lab_disabled = manifest_permissions(
        root / "android/cl-imp-03-app/AndroidManifest.lab.xml")
    candidate_package, candidate_permissions, candidate_disabled = manifest_permissions(
        root / "android/cl-imp-03-app/AndroidManifest.candidate.xml")
    if lab_permissions or candidate_permissions or not candidate_disabled:
        raise SystemExit("APK permission/disabled-candidate contract failed")
    with zipfile.ZipFile(inputs["claritylink-display-lab.apk"]) as apk:
        names = set(apk.namelist())
        if "classes.dex" not in names:
            raise SystemExit("lab APK does not contain compiled API17 classes")
        if not any(name.startswith("assets/") for name in names):
            raise SystemExit("lab APK does not contain synthetic fixtures")
    with zipfile.ZipFile(inputs["claritylink-disabled-candidate.apk"]) as apk:
        if any(name.startswith("assets/") for name in apk.namelist()):
            raise SystemExit("disabled candidate must not contain synthetic fixture assets")

    output = root / "build/cl-imp-12/artifacts"
    for directory in (root / "build", root / "build/cl-imp-12", output):
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise SystemExit(f"unsafe artifact output directory: {directory}")
    output.mkdir(parents=True, exist_ok=True)
    for name, source in inputs.items():
        destination = output / name
        require_regular_output(destination)
        shutil.copyfile(source, destination)
    artifacts = [
        {"file": name, "size_bytes": (output / name).stat().st_size,
         "sha256": digest(output / name)}
        for name in sorted(inputs)
    ]
    deps = {
        "android_sdk_platform": "android-17",
        "android_build_tools": "35.0.0",
        "android_ndk": "23.2.8568313",
        "ffmpeg": {"version": "6.1.6", "source_archive_sha256":
                   "d4fcb164028dd3beee5d92c0ac72e46aac6973c75ea12dc14de07bf8f407370a",
                   "linkage": "static; H.264 decoder enabled; network disabled"},
        "java_source_target": "7",
        "java_build_runtime": "pinned local JDK 17",
        "apk_signing": "local debug keystore persists under ignored build/cl-imp-03; repeat APK hashes require the same keystore",
        "native_shared_libraries": needed,
    }
    permissions = {
        "lab_apk": {"package": lab_package, "declared": lab_permissions},
        "disabled_candidate_apk": {"package": candidate_package, "declared": candidate_permissions,
                                   "application_disabled": candidate_disabled},
        "runtime_permissions": [],
    }
    compatibility = {
        "android_min_api": 17,
        "native_abi": "armeabi-v7a",
        "native_elf_class": "ELF32",
        "native_machine": "ARM",
        "java_source_target": 7,
        "candidate_installation_enabled": False,
        "lab_apk_install_scope": "isolated API17 emulator only",
        "api17_emulator_validation": "see CL-IMP-12 report; emulator validation is separate from artifact build",
        "physical_scanout": "UNPROVEN",
        "honda_production_integration": "DISABLED",
        "authentic_iphone_type111": "NOT_VALIDATED",
    }
    docs = {
        "build-manifest.json": {"milestone": "CL-IMP-12", "artifacts": artifacts,
                                "dependencies": deps, "compatibility": compatibility},
        "dependency-inventory.json": deps,
        "permission-inventory.json": permissions,
        "compatibility-report.json": compatibility,
    }
    for name, data in docs.items():
        destination = output / name
        require_regular_output(destination)
        destination.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    sums = output / "SHA256SUMS"
    require_regular_output(sums)
    sums.write_text(
        "".join(f"{item['sha256']}  {item['file']}\n" for item in artifacts), encoding="ascii")
    print(f"CL_IMP_12_PACKAGE_PASS artifacts={len(artifacts)} abi=armeabi-v7a api=17 permissions=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
