#!/usr/bin/env bash
# Build the synthetic host-withdrawal instrumentation APK (CL-INT-04).
#
# Contains the API17 renderer, the lab host simulator, Display1HostExpiryTest and one non-exported
# synthetic producer service that runs in its own process (android:process=":producer"). It has no
# permissions and no Honda reference. It is separate from the PaneLease test APK on purpose: that
# APK is contractually component-free. Output: <dir>/claritylink-host-withdrawal-test.apk
#
# usage: build_cl_int_04_host_test_apk.sh <fresh_output_dir>
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
  "$repo/android/src/test/java/org/claritylink/renderer/Display1HostExpiryTest.java"
  "$repo/android/src/test/java/org/claritylink/renderer/ProducerDeathService.java"
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
"$tools/aapt" package -f -M "$repo/android/cl-int-04-host-withdrawal-test/AndroidManifest.xml" \
  -I "$platform/android.jar" -F "$out/unsigned.apk"
(cd "$out/dex" && "$tools/aapt" add "$out/unsigned.apk" classes.dex >/dev/null)
"$tools/zipalign" -f 4 "$out/unsigned.apk" "$out/aligned.apk"
key="$out/host-withdrawal-debug.keystore"
"${KEYTOOL:-keytool}" -genkeypair -keystore "$key" -storepass android -keypass android \
  -alias hostwithdrawal -dname 'CN=ClarityLink Host Withdrawal Offline Test' -keyalg RSA -keysize 2048 \
  -validity 3650 >/dev/null 2>&1
"$tools/apksigner" sign --ks "$key" --ks-pass pass:android --key-pass pass:android \
  --ks-key-alias hostwithdrawal --min-sdk-version 17 --v1-signing-enabled true \
  --v2-signing-enabled false --v3-signing-enabled false --out "$out/claritylink-host-withdrawal-test.apk" "$out/aligned.apk"
"$tools/apksigner" verify --min-sdk-version 17 "$out/claritylink-host-withdrawal-test.apk"
if "$tools/aapt" dump permissions "$out/claritylink-host-withdrawal-test.apk" | grep -q 'uses-permission'; then
  echo 'The host-withdrawal test APK must request no permissions.' >&2; exit 3
fi
sha256sum "$out/claritylink-host-withdrawal-test.apk" 2>/dev/null || shasum -a 256 "$out/claritylink-host-withdrawal-test.apk"
echo "CL_INT_04_HOST_TEST_APK_BUILT $out/claritylink-host-withdrawal-test.apk"
