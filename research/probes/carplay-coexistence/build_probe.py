#!/usr/bin/env python3
"""Build and v1-verify the API-17 background-safe probe locally; never contacts a device."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
RESEARCH = HERE.parent.parent
OLD_PROBE = RESEARCH / "probes/decoder-capacity"
JAVA_HOME = RESEARCH / "tools/java/jdk-17.0.20.1+1-jre/Contents/Home"
JAVA = JAVA_HOME / "bin/java"
KEYTOOL = JAVA_HOME / "bin/keytool"
ECJ = RESEARCH / "tools/android/ecj-3.33.0.jar"
ANDROID = RESEARCH / "tools/android/android-4.1.1.4.jar"
R8 = RESEARCH / "tools/android/r8-8.13.24.jar"
APKSIG = RESEARCH / "tools/android/apksig-8.13.2.jar"
APKTOOL = RESEARCH / "tools/apktool_3.0.3.jar"
BUILD = HERE / "build"
SOURCE = HERE / "src/org/claritylab/carplaycoexistence/DecoderCoexistenceService.java"
FIXTURE = OLD_PROBE / "fixtures/avc-800x480-15fps.mp4"
APKTOOL_YML = """version: 3.0.3
apkFileName: carplay-coexistence-probe.apk
usesFramework:
  ids:
  - 1
sdkInfo:
  minSdkVersion: 17
  targetSdkVersion: 17
versionInfo:
  versionCode: 1
  versionName: 1.0
resourcesInfo:
  packageId: 127
doNotCompress:
- mp4
"""


def run(*args: object) -> None:
    subprocess.run([str(arg) for arg in args], check=True)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_zip_timestamps(path: pathlib.Path) -> None:
    """Remove wall-clock ZIP metadata so a local same-key rebuild is stable."""
    normalized = path.with_name(path.stem + ".normalized.apk")
    with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(normalized, "w") as target:
        target.comment = source.comment
        for entry in source.infolist():
            fixed = zipfile.ZipInfo(entry.filename, date_time=(2020, 1, 1, 0, 0, 0))
            fixed.compress_type = entry.compress_type
            fixed.comment = entry.comment
            fixed.extra = b""
            fixed.create_system = entry.create_system
            fixed.create_version = entry.create_version
            fixed.extract_version = entry.extract_version
            fixed.flag_bits = entry.flag_bits
            fixed.internal_attr = entry.internal_attr
            fixed.external_attr = entry.external_attr
            target.writestr(fixed, source.read(entry.filename), compress_type=entry.compress_type)
    os.replace(normalized, path)


def main() -> None:
    required = [JAVA, KEYTOOL, ECJ, ANDROID, R8, APKSIG, APKTOOL, SOURCE, FIXTURE]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("missing local build inputs: " + ", ".join(missing))
    BUILD.mkdir(exist_ok=True)
    keystore = BUILD / "coexistence-debug.keystore"
    for path in BUILD.iterdir():
        if path == keystore:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    for name in ("classes", "dex", "apktool", "sign-tool", "inspected"):
        (BUILD / name).mkdir(parents=True)
    package_dir = BUILD / "apktool"
    (package_dir / "assets").mkdir()
    shutil.copyfile(HERE / "AndroidManifest.xml", package_dir / "AndroidManifest.xml")
    (package_dir / "apktool.yml").write_text(APKTOOL_YML)
    shutil.copyfile(FIXTURE, package_dir / "assets" / FIXTURE.name)
    run(JAVA, "-jar", ECJ, "-1.7", "-classpath", ANDROID, "-d", BUILD / "classes", SOURCE)
    classes = sorted((BUILD / "classes").rglob("*.class"))
    if not classes:
        raise SystemExit("compiler emitted no class files")
    run(JAVA, "-cp", R8, "com.android.tools.r8.D8", "--min-api", "17",
        "--no-desugaring", "--lib", ANDROID, "--output", BUILD / "dex", *classes)
    unsigned = BUILD / "coexistence-probe-unsigned.apk"
    run(JAVA, "-jar", APKTOOL, "b", package_dir, "-o", unsigned)
    with zipfile.ZipFile(unsigned, "a") as archive:
        archive.write(BUILD / "dex/classes.dex", "classes.dex", compress_type=zipfile.ZIP_STORED)
    normalize_zip_timestamps(unsigned)
    with zipfile.ZipFile(unsigned) as archive:
        asset_name = "assets/" + FIXTURE.name
        if archive.getinfo(asset_name).compress_type != zipfile.ZIP_STORED:
            raise SystemExit("fixture is compressed; MediaExtractor cannot open its APK descriptor")
        if archive.read(asset_name) != FIXTURE.read_bytes():
            raise SystemExit("packaged fixture differs from preserved historical fixture")
    run(JAVA, "-jar", ECJ, "-1.8", "-classpath", APKSIG, "-d", BUILD / "sign-tool",
        HERE / "tools/SignDiagnosticApk.java")
    if not keystore.exists():
        run(KEYTOOL, "-genkeypair", "-keystore", keystore, "-storepass", "android",
            "-keypass", "android", "-alias", "clarity-coexistence",
            "-dname", "CN=Clarity Coexistence Diagnostic, O=ClarityLab, C=US",
            "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650")
    signed = BUILD / "carplay-coexistence-probe-signed.apk"
    run(JAVA, "-cp", str(BUILD / "sign-tool") + ":" + str(APKSIG), "SignDiagnosticApk",
        unsigned, signed, keystore, "clarity-coexistence")
    run(JAVA, "-jar", APKTOOL, "d", "-f", signed, "-o", BUILD / "inspected")
    receipt = {
        "package": "org.claritylab.carplaycoexistence",
        "apk": signed.name,
        "apk_sha256": digest(signed),
        "manifest_sha256": digest(HERE / "AndroidManifest.xml"),
        "service_source_sha256": digest(SOURCE),
        "fixture_sha256": digest(FIXTURE),
        "signing": "local disposable debug key; API-17 v1 signature verified by apksig",
        "apk_is_ignored_local_build_output": True,
        "device_contacted": False,
    }
    (BUILD / "BUILD-RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
