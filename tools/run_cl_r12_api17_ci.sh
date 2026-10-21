#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sdk_root="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
receipt="${CL_R12_RECEIPT_DIR:-$repo/build/cl-r12-api17-receipt}"
mkdir -p "$receipt"

adb="$sdk_root/platform-tools/adb"
[[ -x "$adb" ]] || { echo "ADB missing: $adb" >&2; exit 2; }
serial="${ANDROID_SERIAL:-}"
[[ "$serial" =~ ^emulator-[0-9]+$ ]] || { echo 'ANDROID_SERIAL must identify an emulator.' >&2; exit 2; }

{
  echo "commit=$(git -C "$repo" rev-parse HEAD)"
  tree_fingerprint=$(git -C "$repo" rev-parse 'HEAD^{tree}')
  echo "tree=$tree_fingerprint"
  echo "branch=$(git -C "$repo" branch --show-current)"
  echo "serial=$serial"
  echo "sdk_root=$sdk_root"
  echo "emulator_version=$("$sdk_root/emulator/emulator" -version 2>&1 | head -n 1)"
  echo "emulator_sha256=$(sha256sum "$sdk_root/emulator/emulator" | awk '{print $1}')"
  echo "graphics_backend=swiftshader_indirect (headless)"
  echo "apk_sha256=$(sha256sum "$repo/build/cl-imp-03/claritylink-display-lab.apk" | awk '{print $1}')"
  echo "source_sha256=$(git -C "$repo" archive HEAD | sha256sum | awk '{print $1}')"
} > "$receipt/identity.txt"
sdkmanager=$(find "$sdk_root/cmdline-tools" -type f -name sdkmanager -print -quit 2>/dev/null || true)
if [[ -n "$sdkmanager" ]]; then "$sdkmanager" --list_installed > "$receipt/sdk-packages.txt" 2>&1 || true; fi
for fingerprint in \
  "$sdk_root/platforms/android-17/android.jar" \
  "$sdk_root/system-images/android-17/default/x86/source.properties" \
  "$sdk_root/system-images/android-17/default/x86/system.img" \
  "$sdk_root/build-tools/35.0.0/source.properties"; do
  if [[ -f "$fingerprint" ]]; then sha256sum "$fingerprint" >> "$receipt/sdk-fingerprints.txt"; fi
done

devices=$("$adb" devices | awk 'NR > 1 && $2 == "device" { print $1 }')
[[ "$devices" == "$serial" ]] || {
  printf 'Expected exactly %s; online ADB devices were:\n%s\n' "$serial" "$devices" >&2
  exit 3
}

boot_deadline=$((SECONDS + 360))
until [[ "$("$adb" -s "$serial" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]]; do
  if (( SECONDS >= boot_deadline )); then
    echo 'Android guest boot timed out after 360 seconds.' >&2
    "$adb" -s "$serial" logcat -d > "$receipt/boot-timeout-logcat.txt" || true
    exit 4
  fi
  sleep 2
done

api=$("$adb" -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')
release=$("$adb" -s "$serial" shell getprop ro.build.version.release | tr -d '\r')
abi=$("$adb" -s "$serial" shell getprop ro.product.cpu.abi | tr -d '\r')
{
  echo "api=$api"
  echo "release=$release"
  echo "abi=$abi"
  echo "fingerprint=$("$adb" -s "$serial" shell getprop ro.build.fingerprint | tr -d '\r')"
  echo "kernel=$("$adb" -s "$serial" shell uname -a | tr -d '\r')"
} >> "$receipt/identity.txt"
[[ "$api" == 17 && "$release" == 4.2.2 && "$abi" == x86 ]] || {
  echo "Expected Android 4.2.2/API 17/x86; got release=$release api=$api abi=$abi" >&2
  exit 5
}

apk="$repo/build/cl-imp-03/claritylink-display-lab.apk"
"$adb" -s "$serial" logcat -c
"$adb" -s "$serial" install "$apk" | tee "$receipt/install.txt"
"$adb" -s "$serial" shell am start -W \
  -n org.claritylink.independentdisplay.lab/org.claritylink.android.MessengerFrameLabActivity \
  --ez run_cl_r12_scenario true | tee "$receipt/activity-start.txt"

deadline=$((SECONDS + 180))
while (( SECONDS < deadline )); do
  "$adb" -s "$serial" logcat -d -s ClarityLinkMessengerLab > "$receipt/test-logcat.txt"
  if rg -q 'CL_R12_MESSENGER_LAB_PASS' "$receipt/test-logcat.txt"; then
    rg 'CL_R12_MESSENGER_LAB_PASS|SCENARIO_STALE_GENERATION_REJECTED|navigation_inactive|interrupt_preemption|LAB_ONLY_SYNTHETIC_HOST_PROCESS_CRASH|rendered Type111 fixture frames=' "$receipt/test-logcat.txt" \
      | tee "$receipt/test-result.txt"
    break
  fi
  sleep 1
done
rg -q 'CL_R12_MESSENGER_LAB_PASS' "$receipt/test-logcat.txt" || {
  "$adb" -s "$serial" logcat -d -s ClarityLinkMessengerLab AndroidRuntime > "$receipt/test-failure-logcat.txt" || true
  echo 'CL-R12 API17 runtime scenario did not produce its PASS marker.' >&2
  exit 6
}

"$adb" -s "$serial" shell am force-stop org.claritylink.independentdisplay.lab
echo 'CL_R12_API17_RUNTIME_PASS' | tee "$receipt/final-status.txt"
