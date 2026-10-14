#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sdk=${CL_IMP_03_SDK_ROOT:-"$HOME/Android/r7c2-sdk"}
ndk=${ANDROID_NDK_HOME:-"$sdk/ndk/23.2.8568313"}
java_home=${JAVA_HOME:-"$HOME/.local/toolchains/temurin-17.0.20.1+1-aarch64/jdk-17.0.20.1+1/Contents/Home"}
[ -x "$java_home/bin/javac" ] || { echo 'Pinned local JDK 17 unavailable.' >&2; exit 2; }
[ -f "$sdk/platforms/android-17/android.jar" ] || { echo 'Android API17 SDK platform unavailable.' >&2; exit 2; }
[ -f "$ndk/source.properties" ] || { echo 'Pinned Android NDK unavailable.' >&2; exit 2; }
export ANDROID_NDK_HOME="$ndk" ANDROID_HOME="$sdk" JAVA_HOME="$java_home"
export PATH="$java_home/bin:$PATH"
mkdir -p "$repo/build/cl-imp-12"
"$repo/tools/build_r7c_android_api17_armv7.sh"
"$repo/.venv/bin/python" "$repo/tools/audit_r7c_api17_symbols.py" \
  "$repo/build/r7c/android-armv7/libclaritylink_android.so" --ndk "$ndk" \
  > "$repo/build/cl-imp-12/api17-symbol-audit.json"
"$repo/tools/compile_android_api17_java.sh"
"$repo/tools/build_cl_imp_03_apks.sh"
"$repo/.venv/bin/python" "$repo/tools/package_cl_imp_12_artifacts.py" "$repo" "$ndk"
