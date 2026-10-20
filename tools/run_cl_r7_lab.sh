#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
build_dir=${CL_R7_BUILD_DIR:-"$repo/build/cl-r7-lab-$(date +%Y%m%d-%H%M%S)-$$"}
export CL_IMP_03_BUILD_DIR="$build_dir"

fail() {
  echo "CL_R7_END_TO_END_LAB_FAIL reason=$1 build_dir=$build_dir" >&2
  exit 1
}

"$repo/tools/build_cl_imp_03_apks.sh" || fail build

run_order() {
  name=$1
  mode=$2
  log="$build_dir/cl-r7-$name.log"
  echo "CL_R7_RUN_START order=$name log=$log"
  if ! "$repo/tools/run_cl_imp_03_emulator.sh" "$mode" >"$log" 2>&1; then
    cat "$log" >&2
    fail "$name-emulator-run"
  fi
  cat "$log"
  grep -F 'CL_R4_TYPE111_BUFFER_TO_VIEW_RUNTIME_PASS api=17 release=4.2.2 actual_mediacodec=true binder_pfd=true view_draw=true' "$log" >/dev/null ||
    fail "$name-runtime-pixel-path"
  grep -F 'cleanup=pass' "$log" >/dev/null || fail "$name-cleanup"
  grep -F 'CL_R6_DECODED_TYPE111_WARNING_BLOCK_PASS ' "$log" | grep -F 'reattached=true' >/dev/null ||
    fail "$name-decoded-type111-warning-withdrawal"
  grep -F 'CL_R6_DECODED_TYPE111_WARNING_RECOVERY_PASS ' "$log" | grep -F 'reattached=true' >/dev/null ||
    fail "$name-decoded-type111-warning-recovery"
  grep -F 'CL_R4_TYPE111_CONSUMER_REATTACH_PASS' "$log" >/dev/null ||
    grep -F 'TYPE111_CONSUMER_DEATH_VERIFIED' "$log" >/dev/null || fail "$name-view-reattachment"
  echo "CL_R7_RUN_PASS order=$name api=17 pixel_validation=true reattachment=true cleanup=true log=$log"
}

# Each runner owns and tears down its isolated API17 emulator and ADB server.
run_order type110-first --cl-r4-type111-reattach
run_order type111-first --cl-r5-type111-first-reattach

echo "CL_R7_END_TO_END_LAB_PASS api=17 setup_orders=2 actual_mediacodec=true binder_pfd=true pixel_validation=true decoded_type111_warning_withdrawal=true decoded_type111_warning_recovery=true view_reattachment=true cleanup=true build_dir=$build_dir"
