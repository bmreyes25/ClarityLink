#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sdk_root="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
receipt="${CL_R12_RECEIPT_DIR:-$repo/build/cl-r12-api17-receipt}"
build_dir="${CL_IMP_03_BUILD_DIR:-$repo/build/cl-imp-03}"
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
  echo "apk_sha256=$(sha256sum "$build_dir/claritylink-display-lab.apk" | awk '{print $1}')"
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

apk="$build_dir/claritylink-display-lab.apk"
"$adb" -s "$serial" logcat -c
"$adb" -s "$serial" install "$apk" | tee "$receipt/install.txt"
"$adb" -s "$serial" shell am start -W \
  -n org.claritylink.independentdisplay.lab/org.claritylink.android.MessengerFrameLabActivity \
  --ez run_cl_r12_scenario true | tee "$receipt/activity-start.txt"

deadline=$((SECONDS + 180))
while (( SECONDS < deadline )); do
  "$adb" -s "$serial" logcat -d -s ClarityLinkMessengerLab > "$receipt/test-logcat.txt"
  if grep -q 'CL_R12_MESSENGER_LAB_PASS' "$receipt/test-logcat.txt"; then
    grep -E 'CL_R12_MESSENGER_LAB_PASS|SCENARIO_STALE_GENERATION_REJECTED|navigation_inactive|interrupt_preemption|LAB_ONLY_SYNTHETIC_HOST_PROCESS_CRASH|rendered Type111 fixture frames=' "$receipt/test-logcat.txt" \
      | tee "$receipt/test-result.txt"
    break
  fi
  sleep 1
done
grep -q 'CL_R12_MESSENGER_LAB_PASS' "$receipt/test-logcat.txt" || {
  "$adb" -s "$serial" logcat -d -s ClarityLinkMessengerLab AndroidRuntime > "$receipt/test-failure-logcat.txt" || true
  echo 'CL-R12 API17 runtime scenario did not produce its PASS marker.' >&2
  exit 6
}

run_performance() {
  local variant="$1" apk_path="$2" mode="${3:-short}" profile="${4:-false}" started="$receipt/perf-$1-start.txt"
  local result_seen=false
  [[ -f "$apk_path" ]] || { echo "Missing $variant APK: $apk_path" >&2; exit 7; }
  "$adb" -s "$serial" uninstall org.claritylink.independentdisplay.lab \
    > "$receipt/perf-$variant-uninstall.txt" 2>&1 || true
  "$adb" -s "$serial" install "$apk_path" | tee "$receipt/perf-$variant-install.txt"
  "$adb" -s "$serial" logcat -c
  "$adb" -s "$serial" shell am start -W \
    -n org.claritylink.independentdisplay.lab/org.claritylink.android.MessengerFramePerformanceActivity \
    --es cl_r12b_mode "$mode" --ez cl_r12b_profile "$profile" | tee "$started"
  local timeout=90
  [[ "$mode" == soak ]] && timeout=720
  local deadline=$((SECONDS + timeout))
  while (( SECONDS < deadline )); do
    "$adb" -s "$serial" logcat -d -s ClarityLinkR12B > "$receipt/perf-$variant-logcat.txt"
    if grep -q "R12B_RESULT mode=$mode" "$receipt/perf-$variant-logcat.txt"; then
      result_seen=true
    fi
    if [[ "$result_seen" == true ]] && grep -q "R12B_DESTROY mode=$mode" "$receipt/perf-$variant-logcat.txt"; then
      grep -E 'R12B_(START|RESULT|STAGE|VIEW_STAGE|VIEW_FRAME_IDS|DESTROY|SETUP_FAILED|FRAME_SEND_FAILED|DELIVERY_FAILED)' \
        "$receipt/perf-$variant-logcat.txt" | tee "$receipt/perf-$variant-result.txt"
      return 0
    fi
    sleep 1
  done
  echo "Timed out waiting for $variant performance/destruction result" >&2
  exit 8
}

baseline_apk="${CL_R12_BASELINE_APK:-}"
candidate_apk="${CL_R12_CANDIDATE_APK:-$apk}"
if [[ -n "$baseline_apk" ]]; then
  run_performance baseline "$baseline_apk"
  run_performance optimized "$candidate_apk"
  run_performance optimized-profile-control "$candidate_apk"
  run_performance optimized-profile "$candidate_apk" short true
  if python3 "$repo/tools/check_cl_r12_perf_gate.py" "$receipt/perf-baseline-logcat.txt" \
      > "$receipt/perf-baseline-gate.txt" 2>&1 &&
      python3 "$repo/tools/check_cl_r12_perf_gate.py" "$receipt/perf-optimized-logcat.txt" \
      > "$receipt/perf-optimized-gate.txt" 2>&1; then
    run_performance optimized-soak "$candidate_apk" soak
    python3 "$repo/tools/check_cl_r12_perf_gate.py" "$receipt/perf-optimized-soak-logcat.txt" \
      > "$receipt/perf-optimized-soak-gate.txt" 2>&1 || true
  else
    echo 'CL_R12_SOAK_SKIPPED short-run correctness/performance/resource gates did not pass.' \
      | tee "$receipt/perf-soak-skipped.txt"
  fi
fi

"$adb" -s "$serial" shell am force-stop org.claritylink.independentdisplay.lab
echo 'CL_R12_API17_RUNTIME_PASS' | tee "$receipt/final-status.txt"
