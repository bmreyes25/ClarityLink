#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sdk_root=${R7C2_SDK_ROOT:-"$HOME/Android/r7c2-sdk"}
java_home=${JAVA_HOME:-"$HOME/.local/toolchains/temurin-17.0.20.1+1-aarch64/jdk-17.0.20.1+1/Contents/Home"}
platform="$sdk_root/platforms/android-17"
tools="$sdk_root/build-tools/35.0.0"
out="$repo/build/r7e1/display-apk"
[ -f "$platform/android.jar" ] || { echo 'Android API17 platform is missing.' >&2; exit 2; }
[ -x "$tools/aapt" ] && [ -x "$tools/d8" ] && [ -x "$tools/apksigner" ] && [ -x "$tools/zipalign" ] || { echo 'Android build-tools 35.0.0 are required.' >&2; exit 2; }
[ -x "$java_home/bin/javac" ] && [ -x "$java_home/bin/keytool" ] || { echo 'Pinned local JDK 17 is unavailable.' >&2; exit 2; }
mkdir -p "$out/classes" "$out/dex" "$out/assets"
export JAVA_HOME="$java_home" PATH="$java_home/bin:$PATH"
python3 "$repo/tools/generate_r7e1_diagnostic_frame.py"
cp "$repo/android/r7e1-display/assets/r7e1-diagnostic-frame.png" "$out/assets/"
"$JAVA_HOME/bin/javac" -source 1.7 -target 1.7 -Xlint:all -bootclasspath "$platform/android.jar" \
  -d "$out/classes" \
  "$repo/android/src/main/java/org/claritylink/android/DisplayPolicy.java" \
  "$repo/android/src/main/java/org/claritylink/android/DisplayDiscovery.java" \
  "$repo/android/src/main/java/org/claritylink/android/SecondaryDisplayHost.java" \
  "$repo/android/r7e1-display/java/org/claritylink/android/R7E1DisplayDiagnosticActivity.java"
"$tools/aapt" package -f -M "$repo/android/r7e1-display/AndroidManifest.xml" -I "$platform/android.jar" \
  -A "$out/assets" -F "$out/unaligned.apk"
"$tools/d8" --min-api 17 --lib "$platform/android.jar" --output "$out/dex" \
  $(find "$out/classes" -name '*.class' -print)
(cd "$out/dex" && "$tools/aapt" add "$out/unaligned.apk" classes.dex)
(cd "$out/assets" && "$tools/aapt" add "$out/unaligned.apk" r7e1-diagnostic-frame.png)
"$tools/zipalign" -f 4 "$out/unaligned.apk" "$out/aligned.apk"
key="$out/r7e1-debug-only.keystore"
if [ ! -f "$key" ]; then
  "$JAVA_HOME/bin/keytool" -genkeypair -keystore "$key" -storepass android -keypass android \
    -alias r7e1debug -dname 'CN=R7E1 Offline Diagnostic' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1
fi
"$tools/apksigner" sign --ks "$key" --ks-pass pass:android --key-pass pass:android --ks-key-alias r7e1debug \
  --min-sdk-version 17 --v1-signing-enabled true --v2-signing-enabled false --v3-signing-enabled false \
  --out "$out/claritylink-r7e1-display-diagnostic.apk" "$out/aligned.apk"
"$tools/apksigner" verify --min-sdk-version 17 --verbose "$out/claritylink-r7e1-display-diagnostic.apk"
"$tools/aapt" dump badging "$out/claritylink-r7e1-display-diagnostic.apk" > "$out/apk-badging.txt"
"$tools/aapt" dump permissions "$out/claritylink-r7e1-display-diagnostic.apk" > "$out/apk-permissions.txt"
shasum -a 256 "$out/claritylink-r7e1-display-diagnostic.apk" "$out/assets/r7e1-diagnostic-frame.png"
echo "Built offline diagnostic APK $out/claritylink-r7e1-display-diagnostic.apk"
