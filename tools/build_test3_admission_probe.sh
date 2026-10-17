#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sdk=${TEST3_SDK_ROOT:-"$HOME/Android/r7c2-sdk"}
platform="$sdk/platforms/android-17"
tools="$sdk/build-tools/35.0.0"
java_home=${JAVA_HOME:-"$HOME/.local/toolchains/temurin-17.0.20.1+1-aarch64/jdk-17.0.20.1+1/Contents/Home"}
out=${TEST3_BUILD_DIR:-"$repo/build/test3-admission-probe"}
case "$out" in /*) ;; *) out="$repo/$out" ;; esac
out_parent=$(dirname -- "$out")
out_name=$(basename -- "$out")
[ ! -L "$repo/build" ] || { echo 'Repository build root must not be a symlink.' >&2; exit 2; }
mkdir -p "$repo/build"
parent_real=$(CDPATH= cd -- "$out_parent" 2>/dev/null && pwd -P) || {
  echo 'Build output parent must already exist.' >&2; exit 2;
}
repo_build_real=$(CDPATH= cd -- "$repo/build" && pwd -P)
case "$parent_real" in "$repo_build_real"|/tmp|/private/tmp) ;; *)
  echo 'Build output must be a direct child of repo/build or /tmp.' >&2; exit 2 ;;
esac
case "$out_name" in test3-admission-probe|test3-admission-probe-*) ;; *)
  echo 'Build output directory name is not a Test 3 campaign directory.' >&2; exit 2 ;;
esac
[ ! -e "$out" ] && [ ! -L "$out" ] || {
  echo 'Build output must be a fresh path; existing paths are never cleaned or reused.' >&2; exit 2;
}
mkdir "$out" || { echo 'Could not atomically create build output directory.' >&2; exit 2; }
chmod 700 "$out"
[ -f "$platform/android.jar" ] || { echo 'API17 android.jar unavailable.' >&2; exit 2; }
for tool in aapt d8 zipalign apksigner; do
  [ -x "$tools/$tool" ] || { echo "Missing build tool: $tool" >&2; exit 2; }
done
[ -x "$java_home/bin/javac" ] && [ -x "$java_home/bin/keytool" ] || {
  echo 'Pinned local JDK 17 unavailable.' >&2; exit 2;
}
export JAVA_HOME="$java_home" PATH="$java_home/bin:$PATH"
mkdir -p "$out/classes" "$out/dex"
"$JAVA_HOME/bin/javac" -source 1.7 -target 1.7 -Xlint:all -bootclasspath "$platform/android.jar" \
  -d "$out/classes" \
  "$repo/android/src/main/java/org/claritylink/android/DisplayDiscovery.java" \
  "$repo/android/test3-admission-probe/java/org/claritylink/android/Test3DisplayAccessProbeActivity.java"
"$tools/aapt" package -f -M "$repo/android/test3-admission-probe/AndroidManifest.xml" \
  -I "$platform/android.jar" -F "$out/unaligned.apk"
"$tools/d8" --min-api 17 --lib "$platform/android.jar" --output "$out/dex" \
  $(find "$out/classes" -name '*.class' -print)
(cd "$out/dex" && "$tools/aapt" add "$out/unaligned.apk" classes.dex >/dev/null)
"$tools/zipalign" -f 4 "$out/unaligned.apk" "$out/aligned.apk"
key="$out/test3-probe-debug.keystore"
if [ ! -f "$key" ]; then
  "$JAVA_HOME/bin/keytool" -genkeypair -keystore "$key" -storepass android -keypass android \
    -alias test3probe -dname 'CN=ClarityLink Test 3 Offline Probe' -keyalg RSA -keysize 2048 \
    -validity 3650 >/dev/null 2>&1
fi
"$tools/apksigner" sign --ks "$key" --ks-pass pass:android --key-pass pass:android \
  --ks-key-alias test3probe --min-sdk-version 17 --v1-signing-enabled true \
  --v2-signing-enabled false --v3-signing-enabled false --out "$out/claritylink-test3-admission-probe.apk" \
  "$out/aligned.apk"
"$tools/apksigner" verify --min-sdk-version 17 --verbose "$out/claritylink-test3-admission-probe.apk"
"$tools/aapt" dump badging "$out/claritylink-test3-admission-probe.apk" > "$out/apk-badging.txt"
"$tools/aapt" dump permissions "$out/claritylink-test3-admission-probe.apk" > "$out/apk-permissions.txt"
if rg -q '^uses-permission:' "$out/apk-permissions.txt"; then
  echo 'Probe APK unexpectedly declares permissions.' >&2; exit 3
fi
"$tools/aapt" dump xmltree "$out/claritylink-test3-admission-probe.apk" AndroidManifest.xml > "$out/apk-manifest-tree.txt"
rg -q 'Theme.NoDisplay' "$repo/android/test3-admission-probe/AndroidManifest.xml"
rg -q 'android:exported="true"' "$repo/android/test3-admission-probe/AndroidManifest.xml"
if rg -q 'Presentation|SurfaceView|SurfaceHolder|WindowManager|INTERNET|WRITE_EXTERNAL_STORAGE|READ_EXTERNAL_STORAGE|Runtime\.exec|ProcessBuilder|startService|bindService|BroadcastReceiver|ContentProvider' \
  "$repo/android/test3-admission-probe/java" "$repo/android/test3-admission-probe/AndroidManifest.xml"; then
  echo 'Probe source/manifest contains a disallowed surface, private integration, process, service, or storage capability.' >&2
  exit 4
fi
shasum -a 256 "$out/claritylink-test3-admission-probe.apk"
echo "TEST3_PROBE_BUILT package=org.claritylink.admissionprobe min_sdk=17 target_sdk=17 permissions=none window=Theme.NoDisplay"
