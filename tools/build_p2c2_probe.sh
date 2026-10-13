#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sdk=${P2C2_SDK_ROOT:-"$HOME/Android/r7c2-sdk"}
platform="$sdk/platforms/android-17"
build_tools="$sdk/build-tools/35.0.0"
out="$repo/build/p2c2"
[ -f "$platform/android.jar" ] || { echo 'API17 android.jar unavailable.' >&2; exit 2; }
for tool in aapt d8 zipalign apksigner; do
  [ -x "$build_tools/$tool" ] || { echo "Missing build tool: $tool" >&2; exit 2; }
done
export JAVA_HOME=${JAVA_HOME:-"$HOME/.local/toolchains/temurin-17.0.20.1+1-aarch64/jdk-17.0.20.1+1/Contents/Home"}
export PATH="$JAVA_HOME/bin:$PATH"
mkdir -p "$out/classes" "$out/dex"
"${JAVAC:-javac}" -source 1.7 -target 1.7 -Xlint:all -bootclasspath "$platform/android.jar" \
  -d "$out/classes" \
  "$repo/android/src/main/java/org/claritylink/android/DisplayDiscovery.java" \
  "$repo/android/src/main/java/org/claritylink/android/DisplayPolicy.java" \
  "$repo/android/src/main/java/org/claritylink/android/HondaStyleHostModel.java" \
  "$repo/android/src/main/java/org/claritylink/android/SecondaryDisplayHost.java" \
  "$repo/android/src/main/java/org/claritylink/android/HondaStyleDisplayHostSimulator.java" \
  "$repo/android/p2c2-probe/java/org/claritylink/android/P2C2AdmissionProbeActivity.java"
"$build_tools/aapt" package -f -M "$repo/android/p2c2-probe/AndroidManifest.xml" \
  -I "$platform/android.jar" -F "$out/unsigned.apk"
"$build_tools/d8" --min-api 17 --lib "$platform/android.jar" --output "$out/dex" \
  $(find "$out/classes" -name '*.class' -print)
(cd "$out/dex" && "$build_tools/aapt" add "$out/unsigned.apk" classes.dex)
"$build_tools/zipalign" -f 4 "$out/unsigned.apk" "$out/aligned.apk"
key="$out/p2c2-debug.keystore"
if [ ! -f "$key" ]; then
  "${KEYTOOL:-keytool}" -genkeypair -keystore "$key" -storepass android -keypass android \
    -alias p2c2probe -dname 'CN=P2C2 Emulator Only' -keyalg RSA -keysize 2048 \
    -validity 3650 >/dev/null 2>&1
fi
"$build_tools/apksigner" sign --ks "$key" --ks-pass pass:android \
  --key-pass pass:android --ks-key-alias p2c2probe --min-sdk-version 17 \
  --v1-signing-enabled true --v2-signing-enabled false --v3-signing-enabled false \
  --out "$out/p2c2-probe.apk" "$out/aligned.apk"
"$build_tools/apksigner" verify --min-sdk-version 17 "$out/p2c2-probe.apk"
shasum -a 256 "$out/p2c2-probe.apk"
