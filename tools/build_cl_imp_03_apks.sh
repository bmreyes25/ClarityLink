#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sdk=${CL_IMP_03_SDK_ROOT:-"$HOME/Android/r7c2-sdk"}
platform="$sdk/platforms/android-17"
build_tools="$sdk/build-tools/35.0.0"
java_home=${JAVA_HOME:-"$HOME/.local/toolchains/temurin-17.0.20.1+1-aarch64/jdk-17.0.20.1+1/Contents/Home"}
out=${CL_IMP_03_BUILD_DIR:-"$repo/build/cl-imp-03"}
# CL_IMP_03_BUILD_DIR is caller-controlled. Require a fresh, atomically created
# campaign directory; never recycle or recursively clean an existing path.
case "$out" in /*) ;; *) out="$repo/$out" ;; esac
out_parent=$(dirname -- "$out")
out_name=$(basename -- "$out")
if [ -L "$repo/build" ]; then
  echo 'Repository build root must not be a symlink.' >&2; exit 2
fi
mkdir -p "$repo/build"
parent_real=$(CDPATH= cd -- "$out_parent" 2>/dev/null && pwd -P) || {
  echo 'Build output parent must already exist.' >&2; exit 2;
}
repo_build_real=$(CDPATH= cd -- "$repo/build" && pwd -P)
case "$parent_real" in "$repo_build_real"|/tmp|/private/tmp) ;; *)
  echo 'Build output must be a direct child of repo/build or /tmp.' >&2; exit 2 ;;
esac
case "$out_name" in cl-imp-03|cl-imp-03-*|claritylink-cl-imp-03-*|cl-r[0-9]*-*) ;; *)
  echo 'Build output directory name is not a ClarityLink campaign directory.' >&2; exit 2 ;;
esac
[ ! -e "$out" ] && [ ! -L "$out" ] || {
  echo 'Build output must be a fresh path; existing paths are never cleaned or reused.' >&2; exit 2;
}
mkdir "$out" || { echo 'Could not atomically create build output directory.' >&2; exit 2; }
chmod 700 "$out"
marker="$out/.claritylink-build-root"
printf '%s\n' "$repo" > "$marker"
[ -f "$platform/android.jar" ] || { echo 'API17 android.jar unavailable.' >&2; exit 2; }
[ -x "$java_home/bin/javac" ] || { echo 'Pinned Java 17 toolchain unavailable.' >&2; exit 2; }
for tool in aapt d8 zipalign apksigner; do
  [ -x "$build_tools/$tool" ] || { echo "Missing Android build tool: $tool" >&2; exit 2; }
done
export JAVA_HOME="$java_home" PATH="$java_home/bin:$PATH"
mkdir -p "$out/classes" "$out/dex"
"${JAVAC:-javac}" -source 1.7 -target 1.7 -Xlint:all -bootclasspath "$platform/android.jar" \
  -d "$out/classes" \
  "$repo/android/src/main/java/org/claritylink/android/DisplayDiscovery.java" \
  "$repo/android/src/main/java/org/claritylink/android/DisplayPolicy.java" \
  "$repo/android/src/main/java/org/claritylink/android/SecondaryDisplayHost.java" \
  "$repo/android/src/main/java/org/claritylink/android/Api17SurfaceH264Decoder.java" \
  "$repo/android/src/main/java/org/claritylink/android/Api17BufferH264Decoder.java" \
  "$repo/android/src/main/java/org/claritylink/android/Yuv420FrameAdapter.java" \
  "$repo/android/src/main/java/org/claritylink/android/HostedContentLifecycle.java" \
  "$repo/android/src/main/java/org/claritylink/android/ProcessLifecycleAdapter.java" \
  "$repo/android/src/main/java/org/claritylink/android/HondaStyleHostModel.java" \
  "$repo/android/src/main/java/org/claritylink/android/HondaStyleDisplayHostSimulator.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/ClarityLinkDisplayApplication.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/ClarityLinkDisplayActivity.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/Type110ProgressProbeService.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/Type111ProducerService.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/Type110OwnerIsolationTestActivity.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/CompositorOwnerDeathTestService.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/SameUidRegistrationAttackTestService.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/Api17DecoderLabActivity.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/MessengerFrameHostService.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/MessengerFrameLabActivity.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/MessengerFramePerformanceActivity.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/MessengerFrameParcel.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/CompositorService.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/FrameLabSinkService.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/FrameLabSinkAdmission.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/Type110SinkFailureTestService.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/FrameIpcClient.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/FrameViewSink.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/FrameStreamIdentity.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/Type110LabProbeOwnership.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/FrameLabSink.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/FrameIpcProtocol.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/Type111ControlPlane.java" \
  "$repo/android/cl-imp-03-app/java/org/claritylink/android/Type111ControlClient.java" \
  "$repo/src/claritylink-renderer/android-api17/FrameDispatchGate.java" \
  "$repo/src/claritylink-renderer/android-api17/DecodedFrame.java" \
  "$repo/src/claritylink-renderer/android-api17/FrameSource.java" \
  "$repo/src/claritylink-renderer/android-api17/DiagnosticFrameSource.java" \
  "$repo/src/claritylink-renderer/android-api17/ClarityLinkContentView.java" \
  "$repo/src/claritylink-renderer/android-api17/RendererViewport.java" \
  "$repo/src/claritylink-renderer/android-api17/FrameBackpressureGate.java" \
  "$repo/src/claritylink-renderer/android-api17/SimulatedExternalDisplayCompositor.java" \
  "$repo/src/claritylink-renderer/android-api17/Display1OutputBackend.java" \
  "$repo/src/claritylink-renderer/android-api17/HondaStyleSimulatorRendererHost.java"
mkdir -p "$out/assets"
cp "$repo/tests/fixtures/cl-imp-08/type110-red-32x32.h264.b64" "$out/assets/type110-red-32x32.h264.b64"
cp "$repo/tests/fixtures/cl-imp-08/type111-blue-32x32.h264.b64" "$out/assets/type111-blue-32x32.h264.b64"
cp "$repo/tests/fixtures/cl-imp-08/type111-green-64x64.h264.b64" "$out/assets/type111-green-64x64.h264.b64"
"$build_tools/d8" --min-api 17 --lib "$platform/android.jar" --output "$out/dex" \
  $(find "$out/classes" -name '*.class' -print)
key=${CL_IMP_03_KEYSTORE:-"$out/cl-imp-03-debug.keystore"}
if [ ! -f "$key" ]; then
  "$java_home/bin/keytool" -genkeypair -keystore "$key" -storepass android -keypass android \
    -alias climp03lab -dname 'CN=ClarityLink CL-IMP-03 Offline Lab' -keyalg RSA -keysize 2048 \
    -validity 3650 >/dev/null 2>&1
fi
package_variant() {
  name=$1
  manifest=$2
  unsigned="$out/$name-unsigned.apk"
  aligned="$out/$name-aligned.apk"
  manifest_dir="$out/$name-manifest"
  mkdir -p "$manifest_dir"
  cp "$repo/android/cl-imp-03-app/$manifest" "$manifest_dir/AndroidManifest.xml"
  if [ "$name" = "claritylink-display-lab" ]; then
    "$build_tools/aapt" package -f -M "$manifest_dir/AndroidManifest.xml" \
      -I "$platform/android.jar" -A "$out/assets" -F "$unsigned"
  else
    "$build_tools/aapt" package -f -M "$manifest_dir/AndroidManifest.xml" \
      -I "$platform/android.jar" -F "$unsigned"
  fi
  (cd "$out/dex" && "$build_tools/aapt" add "$unsigned" classes.dex >/dev/null)
  "$build_tools/zipalign" -f 4 "$unsigned" "$aligned"
  "$build_tools/apksigner" sign --ks "$key" --ks-pass pass:android --key-pass pass:android \
    --ks-key-alias climp03lab --min-sdk-version 17 --v1-signing-enabled true \
    --v2-signing-enabled false --v3-signing-enabled false --out "$out/$name.apk" "$aligned"
  "$build_tools/apksigner" verify --min-sdk-version 17 "$out/$name.apk"
}
package_variant claritylink-display-lab AndroidManifest.lab.xml
package_variant claritylink-disabled-candidate AndroidManifest.candidate.xml

attacker_out="$out/cl-r4-boundary-attacker"
attacker_classes="$attacker_out/classes"
attacker_dex="$attacker_out/dex"
mkdir -p "$attacker_classes" "$attacker_dex"
"${JAVAC:-javac}" -source 1.7 -target 1.7 -Xlint:all -bootclasspath "$platform/android.jar" \
  -d "$attacker_classes" \
  "$repo/android/cl-r4-boundary-attacker/java/org/claritylink/attacker/ExportBoundaryAttackActivity.java" \
  "$repo/android/cl-r4-boundary-attacker/java/org/claritylink/attacker/ExportBoundaryAttackService.java"
"$build_tools/d8" --min-api 17 --lib "$platform/android.jar" --output "$attacker_dex" \
  $(find "$attacker_classes" -type f -name '*.class' -print)
attacker_unsigned="$attacker_out/cl-r4-boundary-attacker-unsigned.apk"
attacker_aligned="$attacker_out/cl-r4-boundary-attacker-aligned.apk"
"$build_tools/aapt" package -f \
  -M "$repo/android/cl-r4-boundary-attacker/AndroidManifest.xml" \
  -I "$platform/android.jar" -F "$attacker_unsigned"
(cd "$attacker_dex" && "$build_tools/aapt" add "$attacker_unsigned" classes.dex >/dev/null)
"$build_tools/zipalign" -f 4 "$attacker_unsigned" "$attacker_aligned"
"$build_tools/apksigner" sign --ks "$key" --ks-pass pass:android --key-pass pass:android \
  --ks-key-alias climp03lab --min-sdk-version 17 --v1-signing-enabled true \
  --v2-signing-enabled false --v3-signing-enabled false \
  --out "$attacker_out/cl-r4-boundary-attacker.apk" "$attacker_aligned"
"$build_tools/apksigner" verify --min-sdk-version 17 "$attacker_out/cl-r4-boundary-attacker.apk"
attacker_permissions=$("$build_tools/aapt" dump permissions "$attacker_out/cl-r4-boundary-attacker.apk")
printf '%s\n' "$attacker_permissions" | grep -E -q '^uses-permission:' && {
  echo "Boundary attacker must request no permissions: $attacker_permissions" >&2; exit 3;
}

permissions=$("$build_tools/aapt" dump permissions "$out/claritylink-display-lab.apk")
printf '%s\n' "$permissions" | grep -E -q '^uses-permission:' && {
  echo "Unexpected permission declaration in lab APK: $permissions" >&2; exit 3;
}
python3 - "$out/claritylink-display-lab.apk" "$out/claritylink-disabled-candidate.apk" <<'PY'
import sys
import zipfile
lab, candidate = map(zipfile.ZipFile, sys.argv[1:])
fixtures = {"assets/type110-red-32x32.h264.b64", "assets/type111-blue-32x32.h264.b64",
            "assets/type111-green-64x64.h264.b64"}
if not fixtures.issubset(set(lab.namelist())):
    raise SystemExit("lab APK is missing CL-IMP-08 synthetic fixtures")
if fixtures.intersection(candidate.namelist()):
    raise SystemExit("disabled candidate APK must not package synthetic lab fixtures")
PY
python3 - "$repo/android/cl-imp-03-app/AndroidManifest.candidate.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
android = "{http://schemas.android.com/apk/res/android}"
app = root.find("application")
activity = app.find("activity") if app is not None else None
if app is None or activity is None or app.get(android + "enabled") != "false" or activity.get(android + "enabled") != "false":
    raise SystemExit("candidate APK must remain disabled at application and activity level")
if root.findall("uses-permission"):
    raise SystemExit("candidate APK must declare no permissions")
PY
shasum -a 256 "$out/claritylink-display-lab.apk" "$out/claritylink-disabled-candidate.apk"
shasum -a 256 "$attacker_out/cl-r4-boundary-attacker.apk"
echo 'CL_IMP_03_APKS_BUILT lab=emulator-only candidate=disabled boundary_attacker=separate_uid instrumentation=none permissions=none'
