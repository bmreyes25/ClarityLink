#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sdk_root="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
build_dir="${CL_IMP_03_BUILD_DIR:-$repo/build/cl-r13-factory-03-api17}"
receipt="${CL_FACTORY_03_RECEIPT_DIR:-$repo/build/cl-factory-03-api17-receipt}"
mkdir -p "$receipt"
adb="$sdk_root/platform-tools/adb"
[[ -x "$adb" ]] || { echo "ADB missing under SDK: $sdk_root" >&2; exit 2; }
serial="${ANDROID_SERIAL:-}"
[[ "$serial" =~ ^emulator-[0-9]+$ ]] || { echo 'ANDROID_SERIAL must identify an emulator.' >&2; exit 2; }
apk="$build_dir/claritylink-display-lab.apk"
[[ -f "$apk" ]] || { echo "Missing synthetic lab APK: $apk" >&2; exit 2; }

devices=$("$adb" devices | awk 'NR > 1 && $2 == "device" { print $1 }')
[[ "$devices" == "$serial" ]] || { echo "Expected only $serial, found: $devices" >&2; exit 3; }
deadline=$((SECONDS + 360))
until [[ "$("$adb" -s "$serial" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]]; do
  if (( SECONDS >= deadline )); then echo 'API17 emulator boot timed out.' >&2; exit 4; fi
  sleep 2
done
api=$("$adb" -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')
release=$("$adb" -s "$serial" shell getprop ro.build.version.release | tr -d '\r')
abi=$("$adb" -s "$serial" shell getprop ro.product.cpu.abi | tr -d '\r')
[[ "$api" == 17 && "$release" == 4.2.2 ]] || {
  echo "Expected Android 4.2.2/API 17; got release=$release api=$api" >&2; exit 5;
}
{
  echo "commit=$(git -C "$repo" rev-parse HEAD)"
  echo "branch=$(git -C "$repo" branch --show-current)"
  echo "serial=$serial api=$api release=$release abi=$abi"
  sha256sum "$apk"
} > "$receipt/identity.txt"

"$adb" -s "$serial" logcat -c
"$adb" -s "$serial" install "$apk" | tee "$receipt/install.txt"
"$adb" -s "$serial" shell am start -W \
  -n org.claritylink.independentdisplay.lab/org.claritylink.android.StructuredNavigationLabActivity \
  | tee "$receipt/activity-start.txt"
deadline=$((SECONDS + 90))
while (( SECONDS < deadline )); do
  "$adb" -s "$serial" logcat -d -s ClarityLinkNavLab AndroidRuntime > "$receipt/runtime-logcat.txt"
  if grep -q 'CL_FACTORY_03_API17_RUNTIME_PASS' "$receipt/runtime-logcat.txt"; then
    grep -E 'CL_FACTORY_03_API17_RUNTIME_(PASS|FAIL)' "$receipt/runtime-logcat.txt" \
      | tee "$receipt/runtime-result.txt"
    echo 'API17_RUNTIME_PASS' | tee "$receipt/final-status.txt"
    exit 0
  fi
  if grep -q 'CL_FACTORY_03_API17_RUNTIME_FAIL' "$receipt/runtime-logcat.txt"; then
    cat "$receipt/runtime-logcat.txt" >&2
    exit 6
  fi
  sleep 1
done
cat "$receipt/runtime-logcat.txt" >&2
echo 'No structured-navigation API17 runtime PASS marker was observed.' >&2
exit 7
