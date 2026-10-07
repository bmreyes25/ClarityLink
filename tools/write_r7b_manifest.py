#!/usr/bin/env python3
"""Write a sanitized machine-readable R7B build manifest."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
ndk = Path(os.environ["ANDROID_NDK_HOME"])
artifact = root / "build/r7b/android-armv7-r7b/libclaritylink_receiver.so"
compiler = ndk / "toolchains/llvm/prebuilt/darwin-x86_64/bin/armv7a-linux-androideabi17-clang"
linker = ndk / "toolchains/llvm/prebuilt/darwin-x86_64/bin/ld.lld"
def first_line(*args: str) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.splitlines()[0]

manifest = {
    "source_commit": subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                                     capture_output=True, text=True).stdout.strip(),
    "compiler": first_line(str(compiler), "--version"),
    "linker": first_line(str(linker), "--version"),
    "ndk_version": "23.2.8568313",
    "target_triple": "armv7a-linux-androideabi17",
    "api_level": 17,
    "abi": "armeabi-v7a",
    "build_type": "release_shared_library",
    "decoder_backend": "FFmpeg libavcodec/libswscale static; H.264 decoder only",
    "dependencies": {"ffmpeg": "6.1.6", "cxx_runtime": "NDK r23c libc++ static"},
    "dependency_source_sha256": {
        "ffmpeg-6.1.6.tar.xz": "d4fcb164028dd3beee5d92c0ac72e46aac6973c75ea12dc14de07bf8f407370a",
        "ffmpeg_signature": "verified with FFmpeg release signing key B4322F04D67658D8",
    },
    "ffmpeg_configure_flags": ["--target-os=android", "--arch=arm", "--cpu=armv7-a",
        "--enable-cross-compile", "--disable-shared", "--enable-static", "--enable-pic",
        "--disable-programs", "--disable-doc", "--disable-debug", "--disable-network",
        "--disable-autodetect", "--disable-everything", "--disable-avformat",
        "--disable-avdevice", "--disable-avfilter", "--disable-swresample",
        "--disable-postproc", "--enable-avcodec", "--enable-avutil", "--enable-swscale",
        "--enable-decoder=h264", "--disable-asm", "--disable-neon",
        "--disable-vfp", "--disable-gpl", "--disable-nonfree", "--disable-version3"],
    "compile_flags": ["-std=c++17", "-O2", "-fPIC", "-march=armv7-a",
                      "-mfloat-abi=softfp", "-mfpu=vfpv3-d16", "-fno-rtti",
                      "-fexceptions", "FFmpeg: --disable-asm --disable-neon --disable-vfp"],
    "link_flags": ["-shared", "-Wl,--no-undefined", "-Wl,--exclude-libs,ALL",
                    "-Wl,-soname,libclaritylink_receiver.so", "-static-libstdc++"],
    "artifact": {"name": artifact.name,
                 "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()},
}
(root / "research/runtime/r7b-build-manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n")
print(root / "research/runtime/r7b-build-manifest.json")
