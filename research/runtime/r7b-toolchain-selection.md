# R7B toolchain selection

## Decision

Use Android NDK **r23c / 23.2.8568313**, API 17, target triple
`armv7a-linux-androideabi17`, ABI `armeabi-v7a`. NDK r24 raised the minimum
OS to API 19 and stopped supporting Jelly Bean and non-NEON devices; r23 is
therefore the final practical NDK line for this target. The selected Darwin
toolchain contains universal x86_64/arm64 host executables and was executed on
this Apple Silicon Mac.

Observed compiler: Android clang 12.0.9, revision `8481493` based on LLVM
`r416183c2`. Observed linker: LLD 12.0.9. The API-specific wrapper reports
target `armv7a-unknown-linux-android17`. `tools/build_android_api17_armv7.sh`
checks the exact NDK revision and uses the NDK sysroot; it accepts the NDK
location only through `ANDROID_NDK_HOME`.

The shared library uses C++17 and statically links the NDK C++ runtime. Its
dynamic dependencies are only API17 Bionic `libc.so`, `libm.so`, and `libdl.so`.
No Honda executable, APK, or device install is produced. The NDK archive used
for local verification was `android-ndk-r23c-darwin.zip`, SHA-256
`baf793127741eda36f2eabe69cdec23a70c814deb3c75df8744af35aed21e59d`; the
official Android repository XML lists SHA-1
`1fc65d8f6083f3f5cd01e0cf97c6adc10f4f076f`, which matched the downloaded
archive. [Official Android NDK package metadata](https://dl.google.com/android/repository/repository2-1.xml).

R23 is no longer the latest NDK and is selected specifically for this legacy
minimum API/ABI. The official revision history documents API16–18 removal in
r24; the official build guide documents the API-suffixed Android target
triple and Darwin universal host support. [NDK revision history](https://developer.android.com/ndk/downloads/revision_history),
[NDK cross-compilation guide](https://developer.android.com/ndk/guides/other_build_systems).

## Reproduction

Install NDK r23c from Google's archived NDK distribution, verify the archive
against the hash above, then set `ANDROID_NDK_HOME` and run
`tools/build_android_api17_armv7.sh` from a clean checkout. FFmpeg 6.1.6 is
downloaded from the upstream release archive and SHA-256 checked by the script.
All build products are ignored under `build/r7b/`.

## Evidence

NDK provenance and wrapper identity: `ANDROID_ARMV7_BUILD_CONFIRMED` for the
local output. This establishes an API17/ARMv7 build, not execution on Honda.
The toolchain itself is an official Android NDK release, but this report does
not claim Honda compatibility.
