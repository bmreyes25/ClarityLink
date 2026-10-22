#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
factory_receipt="${CL_INT_02_FACTORY_RECEIPT_DIR:-$repo/build/cl-int-02-api17-receipt/factory}"
r12_receipt="${CL_R12_RECEIPT_DIR:-$repo/build/cl-int-02-api17-receipt/r12}"
candidate_build="${CL_IMP_03_BUILD_DIR:?CL_IMP_03_BUILD_DIR must name the candidate APK build}"

test -n "${CL_R12_BASELINE_APK:-}" || { echo 'CL_R12_BASELINE_APK is required for the A/B acceptance run.' >&2; exit 2; }
test -n "${CL_R12_CANDIDATE_APK:-}" || { echo 'CL_R12_CANDIDATE_APK is required for the A/B acceptance run.' >&2; exit 2; }

export CL_FACTORY_03_RECEIPT_DIR="$factory_receipt"
"$repo/tools/run_cl_factory_03_api17_ci.sh"
grep -Fq 'CL_FACTORY_03_API17_RUNTIME_PASS' "$factory_receipt/runtime-result.txt"
grep -Fq 'cleanup=true' "$factory_receipt/runtime-result.txt"
grep -Fq 'type111_isolated=true' "$factory_receipt/runtime-result.txt"

export CL_R12_RECEIPT_DIR="$r12_receipt"
export CL_IMP_03_BUILD_DIR="$candidate_build"
"$repo/tools/run_cl_r12_api17_ci.sh"
grep -Fq 'CL_R12_MESSENGER_LAB_PASS' "$r12_receipt/test-result.txt"
grep -Fq 'stale_generation_rejected=true' "$r12_receipt/test-result.txt"
grep -Fq 'navigation_withdrawal=true' "$r12_receipt/test-result.txt"
grep -Fq 'producer_host_process_recovery=true' "$r12_receipt/test-result.txt"
grep -Fq 'type110_untouched=true' "$r12_receipt/test-result.txt"

for variant in baseline optimized optimized-profile-control optimized-profile; do
  test ! -f "$r12_receipt/perf-$variant-destroy-missing.txt"
  grep -Fq "R12B_DESTROY mode=short" "$r12_receipt/perf-$variant-logcat.txt"
done
if [[ -f "$r12_receipt/perf-optimized-soak-logcat.txt" ]]; then
  test ! -f "$r12_receipt/perf-optimized-soak-destroy-missing.txt"
  grep -Fq 'R12B_DESTROY mode=soak' "$r12_receipt/perf-optimized-soak-logcat.txt"
fi

adb="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}/platform-tools/adb"
serial="${ANDROID_SERIAL:?ANDROID_SERIAL must identify the isolated API17 emulator}"
"$adb" -s "$serial" shell am force-stop org.claritylink.clfactory03.navlab
"$adb" -s "$serial" shell am force-stop org.claritylink.independentdisplay.lab
echo "factory=$(cat "$factory_receipt/final-status.txt")" > "$repo/build/cl-int-02-api17-receipt/final-status.txt"
echo "runtime=$(cat "$r12_receipt/final-status.txt")" >> "$repo/build/cl-int-02-api17-receipt/final-status.txt"
echo 'CL_INT_02_API17_FUNCTIONAL_PASS' | tee -a "$repo/build/cl-int-02-api17-receipt/final-status.txt"
