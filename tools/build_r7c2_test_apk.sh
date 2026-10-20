#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sdk_root=${R7C2_SDK_ROOT:-"$HOME/Android/r7c2-sdk"}
platform="$sdk_root/platforms/android-17"
tools="$sdk_root/build-tools/35.0.0"
out="$repo/build/r7c2/apk"
[ -f "$platform/android.jar" ] || { echo "API17 platform missing: $platform" >&2; exit 2; }
[ -x "$tools/aapt" ] && [ -x "$tools/d8" ] && [ -x "$tools/apksigner" ] || { echo 'Build-tools 35.0.0 required.' >&2; exit 2; }
[ -f "$repo/build/r7c/android-x86/libclaritylink_android.so" ] || {
  echo 'Build the API17 x86 runtime-test JNI library first.' >&2; exit 2;
}
mkdir -p "$out/classes" "$out/gen" "$out/assets" "$out/dex" "$out/package/lib/x86"
ANDROID_HOME="$sdk_root" "$repo/tools/compile_android_api17_java.sh"
main="$repo/build/r7c/java-api17"
find "$repo/android/r7c2-test/java" -name '*.java' -print > "$out/test-sources.txt"
"${JAVAC:-javac}" -source 1.7 -target 1.7 -Xlint:all -bootclasspath "$platform/android.jar" \
  -classpath "$main" -d "$out/classes" @"$out/test-sources.txt"
cp "$repo/tests/fixtures/r7b/type110-red.h264.b64" "$out/assets/type110-red.h264.b64"
cp "$repo/tests/fixtures/r7b/type111-blue.h264.b64" "$out/assets/type111-blue.h264.b64"
"$tools/aapt" package -f -M "$repo/android/r7c2-test/AndroidManifest.xml" -I "$platform/android.jar" \
  -A "$out/assets" -F "$out/unaligned.apk"
"$tools/d8" --min-api 17 --lib "$platform/android.jar" --output "$out/dex" \
  $(find "$main" "$out/classes" -name '*.class' -print)
(cd "$out/dex" && "$tools/aapt" add "$out/unaligned.apk" classes.dex)
cp "$repo/build/r7c/android-x86/libclaritylink_android.so" "$out/package/lib/x86/libclaritylink_android.so"
(cd "$out/package" && "$tools/aapt" add "$out/unaligned.apk" lib/x86/libclaritylink_android.so)
"$tools/zipalign" -f 4 "$out/unaligned.apk" "$out/aligned.apk"
key="$out/r7c2-debug.keystore"
if [ ! -f "$key" ]; then
  "${KEYTOOL:-keytool}" -genkeypair -keystore "$key" -storepass android -keypass android \
    -alias r7c2test -dname 'CN=R7C2 Offline Test' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1
fi
"$tools/apksigner" sign --ks "$key" --ks-pass pass:android --key-pass pass:android --ks-key-alias r7c2test \
  --min-sdk-version 17 --v1-signing-enabled true --v2-signing-enabled false --v3-signing-enabled false \
  --out "$out/claritylink-r7c2-test.apk" "$out/aligned.apk"
"$tools/apksigner" verify --min-sdk-version 17 --verbose "$out/claritylink-r7c2-test.apk"
shasum -a 256 "$out/claritylink-r7c2-test.apk"
