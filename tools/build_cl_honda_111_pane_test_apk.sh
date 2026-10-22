#!/usr/bin/env bash
# Build the synthetic PaneLease instrumentation APK (CL-HONDA-111-02).
#
# Contains the API17 renderer, the lab host simulator and the PaneLease test classes only.
# It has no permissions, no components and no Honda reference; it exists so the pane-lease
# lifecycle acceptance matrix can run on a real Android 4.2.2 UI thread, which a host JVM
# cannot provide (PaneLease binds to the main Looper).
#
# usage: build_cl_honda_111_pane_test_apk.sh <fresh_output_dir>
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="${1:?fresh output directory required}"
case "$out" in /*) ;; *) out="$repo/$out" ;; esac
[[ ! -e "$out" ]] || { echo "Output directory must not exist: $out" >&2; exit 2; }
sdk="${CL_IMP_03_SDK_ROOT:-$HOME/Android/r7c2-sdk}"
platform="$sdk/platforms/android-17"
tools="$sdk/build-tools/35.0.0"
[[ -f "$platform/android.jar" ]] || { echo "API17 android.jar unavailable: $platform" >&2; exit 2; }
for t in aapt d8 zipalign apksigner; do [[ -x "$tools/$t" ]] || { echo "Missing build tool: $t" >&2; exit 2; }; done

mkdir -p "$out/classes" "$out/dex"
sources=(
  "$repo/android/src/test/java/org/claritylink/renderer/PaneLeaseTest.java"
  "$repo/android/src/test/java/org/claritylink/renderer/Display1PaneLeaseLifecycleTest.java"
  "$repo/android/src/test/java/org/claritylink/renderer/Display1RendererViewportInPlaceTest.java"
)
{
  find "$repo/android/src/main/java" -name '*.java' -print
  find "$repo/src/claritylink-renderer/android-api17" -name '*.java' -print
  printf '%s\n' "${sources[@]}"
} > "$out/sources.txt"
"${JAVAC:-javac}" -source 1.7 -target 1.7 -Xlint:all -bootclasspath "$platform/android.jar" \
  -d "$out/classes" @"$out/sources.txt"
"$tools/d8" --min-api 17 --lib "$platform/android.jar" --output "$out/dex" \
  $(find "$out/classes" -name '*.class' -print)
"$tools/aapt" package -f -M "$repo/android/cl-honda-111-pane-test/AndroidManifest.xml" \
  -I "$platform/android.jar" -F "$out/unsigned.apk"
(cd "$out/dex" && "$tools/aapt" add "$out/unsigned.apk" classes.dex >/dev/null)
"$tools/zipalign" -f 4 "$out/unsigned.apk" "$out/aligned.apk"
key="$out/pane-test-debug.keystore"
"${KEYTOOL:-keytool}" -genkeypair -keystore "$key" -storepass android -keypass android \
  -alias panetest -dname 'CN=ClarityLink PaneLease Offline Test' -keyalg RSA -keysize 2048 \
  -validity 3650 >/dev/null 2>&1
"$tools/apksigner" sign --ks "$key" --ks-pass pass:android --key-pass pass:android \
  --ks-key-alias panetest --min-sdk-version 17 --v1-signing-enabled true \
  --v2-signing-enabled false --v3-signing-enabled false --out "$out/claritylink-pane-lease-test.apk" "$out/aligned.apk"
"$tools/apksigner" verify --min-sdk-version 17 "$out/claritylink-pane-lease-test.apk"
if "$tools/aapt" dump permissions "$out/claritylink-pane-lease-test.apk" | grep -q 'uses-permission'; then
  echo 'The PaneLease test APK must request no permissions.' >&2; exit 3
fi
sha256sum "$out/claritylink-pane-lease-test.apk" 2>/dev/null || shasum -a 256 "$out/claritylink-pane-lease-test.apk"
echo "CL_HONDA_111_PANE_TEST_APK_BUILT $out/claritylink-pane-lease-test.apk"
