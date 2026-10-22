#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sdk=${CL_FACTORY_03_SDK_ROOT:-"$HOME/Android/r7c2-sdk"}
platform="$sdk/platforms/android-17"
build_tools="$sdk/build-tools/35.0.0"
java_home=${JAVA_HOME:-"$HOME/.local/toolchains/temurin-17.0.20.1+1-aarch64/jdk-17.0.20.1+1/Contents/Home"}
out=${CL_FACTORY_03_BUILD_DIR:-"$repo/build/cl-r13-factory-03-navlab"}
case "$out" in /*) ;; *) out="$repo/$out" ;; esac
out_parent=$(dirname -- "$out")
out_name=$(basename -- "$out")
if [ -L "$repo/build" ]; then echo 'Repository build root must not be a symlink.' >&2; exit 2; fi
mkdir -p "$repo/build"
parent_real=$(CDPATH= cd -- "$out_parent" 2>/dev/null && pwd -P) || {
  echo 'Build output parent must already exist.' >&2; exit 2;
}
repo_build_real=$(CDPATH= cd -- "$repo/build" && pwd -P)
case "$parent_real" in "$repo_build_real"|/tmp|/private/tmp) ;; *)
  echo 'Build output must be a direct child of repo/build or /tmp.' >&2; exit 2;; esac
case "$out_name" in cl-r[0-9]*-*) ;; *) echo 'Build output name must identify a ClarityLink campaign.' >&2; exit 2;; esac
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo 'Build output must be fresh; existing paths are never cleaned.' >&2; exit 2; }
[ -f "$platform/android.jar" ] || { echo 'API17 android.jar unavailable.' >&2; exit 2; }
[ -x "$java_home/bin/javac" ] || { echo 'Pinned Java 17 unavailable.' >&2; exit 2; }
for tool in aapt d8 zipalign apksigner; do
  [ -x "$build_tools/$tool" ] || { echo "Missing Android build tool: $tool" >&2; exit 2; }
done
mkdir "$out"
chmod 700 "$out"
printf '%s\n' "$repo" > "$out/.claritylink-build-root"
mkdir -p "$out/classes" "$out/dex"
find "$repo/android/src/main/java" -name '*.java' -print > "$out/java-sources.txt"
find "$repo/src/claritylink-renderer/android-api17" -name '*.java' -print >> "$out/java-sources.txt"
printf '%s\n' "$repo/android/cl-imp-03-app/java/org/claritylink/android/StructuredNavigationLabActivity.java" \
  >> "$out/java-sources.txt"
export JAVA_HOME="$java_home" PATH="$java_home/bin:$PATH"
javac -source 1.7 -target 1.7 -Xlint:all -bootclasspath "$platform/android.jar" \
  -d "$out/classes" @"$out/java-sources.txt"
"$build_tools/d8" --min-api 17 --lib "$platform/android.jar" --output "$out/dex" \
  $(find "$out/classes" -name '*.class' -print)
unsigned="$out/cl-factory-03-navlab-unsigned.apk"
aligned="$out/cl-factory-03-navlab-aligned.apk"
"$build_tools/aapt" package -f -M "$repo/android/cl-factory-03-app/AndroidManifest.xml" \
  -I "$platform/android.jar" -F "$unsigned"
(cd "$out/dex" && "$build_tools/aapt" add "$unsigned" classes.dex >/dev/null)
"$build_tools/zipalign" -f 4 "$unsigned" "$aligned"
key="$out/cl-factory-03-debug.keystore"
"$java_home/bin/keytool" -genkeypair -keystore "$key" -storepass android -keypass android \
  -alias clfactory03lab -dname 'CN=ClarityLink CL-FACTORY-03 Synthetic Lab' -keyalg RSA -keysize 2048 \
  -validity 3650 >/dev/null 2>&1
"$build_tools/apksigner" sign --ks "$key" --ks-pass pass:android --key-pass pass:android \
  --ks-key-alias clfactory03lab --min-sdk-version 17 --v1-signing-enabled true \
  --v2-signing-enabled false --v3-signing-enabled false --out "$out/claritylink-display-lab.apk" "$aligned"
"$build_tools/apksigner" verify --min-sdk-version 17 "$out/claritylink-display-lab.apk"
permissions=$("$build_tools/aapt" dump permissions "$out/claritylink-display-lab.apk")
printf '%s\n' "$permissions" | grep -E -q '^uses-permission:' && {
  echo "Synthetic nav lab must request no permissions: $permissions" >&2; exit 3;
}
shasum -a 256 "$out/claritylink-display-lab.apk"
echo 'CL_FACTORY_03_API17_APK_BUILT min_sdk=17 target_sdk=17 permissions=none factory_output=disabled'
