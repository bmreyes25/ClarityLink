#!/usr/bin/env python3
"""Build a local API-17 diagnostic APK; never connects to a device."""
import hashlib
import pathlib
import shutil
import subprocess
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
RESEARCH = HERE.parent.parent
JAVA = RESEARCH / "tools/java/jdk-17.0.20.1+1-jre/Contents/Home/bin/java"
KEYTOOL = RESEARCH / "tools/java/jdk-17.0.20.1+1-jre/Contents/Home/bin/keytool"
ECJ = RESEARCH / "tools/android/ecj-3.33.0.jar"
ANDROID = RESEARCH / "tools/android/android-4.1.1.4.jar"
R8 = RESEARCH / "tools/android/r8-8.13.24.jar"
APKSIG = RESEARCH / "tools/android/apksig-8.13.2.jar"
APKTOOL = RESEARCH / "tools/apktool_3.0.3.jar"
BUILD = HERE / "build"
SOURCE = HERE / "src/org/claritylab/decoderprobe/DecoderCapacityProbeActivity.java"
FIXTURE = HERE / "fixtures/avc-800x480-15fps.mp4"


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for name in ("classes", "dex", "apktool", "sign-tool", "inspected"):
        target = BUILD / name
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
    package_dir = BUILD / "apktool"
    (package_dir / "assets").mkdir()
    shutil.copyfile(HERE / "AndroidManifest.xml", package_dir / "AndroidManifest.xml")
    shutil.copyfile(HERE / "apktool.yml", package_dir / "apktool.yml")
    shutil.copyfile(FIXTURE, package_dir / "assets" / FIXTURE.name)
    run(JAVA, "-jar", ECJ, "-1.7", "-classpath", ANDROID, "-d", BUILD / "classes", SOURCE)
    classes = sorted((BUILD / "classes").rglob("*.class"))
    run(JAVA, "-cp", R8, "com.android.tools.r8.D8", "--min-api", "17",
        "--no-desugaring", "--lib", ANDROID, "--output", BUILD / "dex", *classes)
    unsigned = BUILD / "decoder-probe-unsigned.apk"
    run(JAVA, "-jar", APKTOOL, "b", package_dir, "-o", unsigned)
    with zipfile.ZipFile(unsigned, "a") as archive:
        archive.write(BUILD / "dex/classes.dex", "classes.dex", compress_type=zipfile.ZIP_STORED)
    with zipfile.ZipFile(unsigned) as archive:
        if archive.getinfo("assets/" + FIXTURE.name).compress_type != zipfile.ZIP_STORED:
            raise RuntimeError("Fixture was compressed; MediaExtractor cannot open its descriptor")
    run(JAVA, "-jar", ECJ, "-1.8", "-classpath", APKSIG,
        "-d", BUILD / "sign-tool", HERE / "tools/SignDiagnosticApk.java")
    keystore = BUILD / "diagnostic-debug.keystore"
    if not keystore.exists():
        run(KEYTOOL, "-genkeypair", "-keystore", keystore, "-storepass", "android",
            "-keypass", "android", "-alias", "clarity-diagnostic",
            "-dname", "CN=Clarity Diagnostic, O=ClarityLab, C=US",
            "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650")
    signed = BUILD / "decoder-probe-signed.apk"
    run(JAVA, "-cp", str(BUILD / "sign-tool") + ":" + str(APKSIG),
        "SignDiagnosticApk", unsigned, signed, keystore, "clarity-diagnostic")
    run(JAVA, "-jar", APKTOOL, "d", "-f", signed, "-o", BUILD / "inspected")
    print("APK:", signed)
    print("APK SHA-256:", digest(signed))
    print("Fixture SHA-256:", digest(FIXTURE))


if __name__ == "__main__":
    main()
