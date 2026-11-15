#!/usr/bin/env bash
# CL-INT-02 API17 runtime runner (synthetic lab only; emulator serials only; never a phone or vehicle).
#
#   run_cl_int_02_api17_ci.sh continuity   Type110 parent session survives three Type111 View replacements
#   run_cl_int_02_api17_ci.sh workload     unchanged CL-R12 workload/performance/soak gates, required PASS
#
# Both modes run against the already-booted CI emulator in ANDROID_SERIAL. Every PASS marker below is
# printed only after the app's own markers were observed in the live logcat; nothing is synthesized.
set -euo pipefail

mode="${1:-}"
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sdk_root="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
receipt="${CL_INT_02_RECEIPT_DIR:-$repo/build/cl-int-02-api17-receipt}"
build_dir="${CL_IMP_03_BUILD_DIR:-$repo/build/cl-imp-03}"
package=org.claritylink.independentdisplay.lab
activity=org.claritylink.android.ClarityLinkDisplayActivity
app_tag=ClarityLinkCLIMP03
step_timeout="${CL_INT_02_STEP_TIMEOUT:-240}"
mkdir -p "$receipt"
trap 'rc=$?; echo "CL_INT_02_RUNNER_ABORTED mode=$mode exit=$rc line=$LINENO" | tee -a "$receipt/final-status.txt" >&2' ERR

[[ "$mode" == continuity || "$mode" == workload ]] || {
  echo "usage: $0 continuity|workload" >&2; exit 2
}
adb="$sdk_root/platform-tools/adb"
[[ -x "$adb" ]] || { echo "ADB missing: $adb" >&2; exit 2; }
serial="${ANDROID_SERIAL:-}"
[[ "$serial" =~ ^emulator-[0-9]+$ ]] || { echo 'ANDROID_SERIAL must identify an emulator.' >&2; exit 2; }
command -v timeout >/dev/null 2>&1 || timeout() { shift; "$@"; }
adbq() { timeout "${CL_INT_02_ADB_TIMEOUT:-180}" "$adb" -s "$serial" "$@"; }

devices=$("$adb" devices | awk 'NR > 1 && $2 == "device" { print $1 }')
[[ "$devices" == "$serial" ]] || {
  printf 'Expected exactly %s; online ADB devices were:\n%s\n' "$serial" "$devices" >&2; exit 3
}
until [[ "$(adbq shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]]; do sleep 2; done
api=$(adbq shell getprop ro.build.version.sdk | tr -d '\r')
release=$(adbq shell getprop ro.build.version.release | tr -d '\r')
abi=$(adbq shell getprop ro.product.cpu.abi | tr -d '\r')
[[ "$api" == 17 && "$release" == 4.2.2 && "$abi" == x86 ]] || {
  echo "Expected Android 4.2.2/API 17/x86; got release=$release api=$api abi=$abi" >&2; exit 5
}
qemu=$(adbq shell getprop ro.kernel.qemu | tr -d '\r')
hardware=$(adbq shell getprop ro.hardware | tr -d '\r')
[[ "$qemu" == 1 && "$hardware" =~ ^(goldfish|ranchu|ranchu64)$ ]] || {
  echo "Refusing target without positive emulator identity: qemu=$qemu hardware=$hardware" >&2; exit 5
}
{
  echo "mode=$mode"
  echo "commit=$(git -C "$repo" rev-parse HEAD)"
  echo "tree=$(git -C "$repo" rev-parse 'HEAD^{tree}')"
  echo "branch=$(git -C "$repo" branch --show-current)"
  echo "baseline_sha=${CL_INT_02_BASELINE_SHA:-unset}"
  echo "serial=$serial api=$api release=$release abi=$abi"
  echo "emulator_identity=verified ro.kernel.qemu=$qemu ro.hardware=$hardware"
  echo "safeForHonda=false VEHICLE_DEPLOYMENT_NOT_AUTHORIZED synthetic_lab_only=true"
} > "$receipt/identity-$mode.txt"

if [[ "$mode" == workload ]]; then
  # The offered workload and its acceptance gates are the unchanged CL-R12 ones: >=27 delivered fps,
  # p95 <=50 ms, p99 <=100 ms, <=10% valid-frame drops, zero pixel mismatches / transport errors /
  # host rejections, producer FD delta <=2, and the 10-minute soak. This mode only refuses to accept a
  # run in which any of those verdicts was skipped.
  export CL_R12_RECEIPT_DIR="$receipt/r12"
  [[ -n "${CL_R12_BASELINE_APK:-}" ]] || { echo 'CL_R12_BASELINE_APK is required.' >&2; exit 2; }
  "$repo/tools/run_cl_r12_api17_ci.sh"
  status="$CL_R12_RECEIPT_DIR/final-status.txt"
  for verdict in CL_R12_API17_RUNTIME_SCENARIO=PASS CL_R12_GATE_CANDIDATE=PASS CL_R12_GATE_SOAK=PASS \
      CL_PANE_LEASE_INSTRUMENTATION=PASS CL_INT_04_HOST_WITHDRAWAL_INSTRUMENTATION=PASS \
      CL_R12_API17_RUNTIME_PASS CL_R12_DESTROY_EVIDENCE_MISSING_COUNT=0; do
    grep -qxF "$verdict" "$status" || {
      echo "CL_INT_02_WORKLOAD_REQUIRED_VERDICT_MISSING $verdict" | tee -a "$receipt/final-status.txt" >&2
      exit 21
    }
  done
  echo 'CL_INT_02_WORKLOAD_API17_PASS gates=r12_unchanged soak=pass' | tee "$receipt/final-status.txt"
  exit 0
fi

# ---------------------------------------------------------------- continuity
apk="$build_dir/claritylink-display-lab.apk"
[[ -f "$apk" ]] || { echo "Missing synthetic lab APK: $apk" >&2; exit 2; }
live_log="$receipt/continuity-logcat.txt"
logcat_pid=
cleanup() {
  [[ -z "$logcat_pid" ]] || kill "$logcat_pid" 2>/dev/null || true
  adbq shell am force-stop "$package" >/dev/null 2>&1 || true
  adbq shell settings put global overlay_display_devices '' >/dev/null 2>&1 || true
}
trap cleanup EXIT

fail() {
  echo "CL_INT_02_CONTINUITY_FAIL $*" | tee -a "$receipt/final-status.txt" >&2
  grep -E 'RENDERER_|SURFACE_BORROWED|ADMISSION_|CL_R4|IPC_' "$live_log" | tail -n 60 >&2 || true
  exit 9
}
logs() { tr -d '\r' < "$live_log"; }
wait_for_any() {  # wait_for_any <fixed marker>...; bounded; an attach failure ends the wait immediately
  local deadline=$((SECONDS + step_timeout)) marker
  while (( SECONDS < deadline )); do
    logs | grep -qF "RENDERER_ATTACH_FAILED" && fail "RENDERER_ATTACH_FAILED observed while waiting for: $1"
    for marker in "$@"; do logs | grep -qF "$marker" && return 0; done
    sleep 1
  done
  fail "timed out after ${step_timeout}s waiting for: $*"
}
wait_for() { wait_for_any "$1"; }
field() { sed -n "s/.*[ ]$1=\([0-9][0-9]*\).*/\1/p" <<<"$2" | tail -1; }
process_alive() {  # exact package process row; a recycled PID of another process does not count
  adbq shell ps | tr -d '\r' | awk -v pid="$1" -v package="$package" \
    '$2==pid && ($NF==package || index($NF, package ":")==1) {found=1} END {exit !found}'
}
launch() {  # launch <session_id|""> <ordinal>
  local args=(--es mode EMULATOR_PRESENTATION --es emulator_only_confirmation CL_IMP_03_OFFLINE_EMULATOR_ONLY
    --ez type111_fixture_mode true --ez type111_reattach_test true
    --ez multiple_view_replacement_test true --ei view_replacement_ordinal "$2"
    --ez hold_after_same_uid_attack true)
  [[ -z "$1" ]] || args+=(--el type111_reattach_session_id "$1")
  adbq shell am start -n "$package/$activity" "${args[@]}" | tee -a "$receipt/activity-start.txt" |
    grep -qF 'Starting: Intent' || fail "activity launch was not accepted (session=${1:-new} ordinal=$2)"
}

adbq uninstall "$package" > "$receipt/uninstall.txt" 2>&1 || true
adbq install "$apk" | tee "$receipt/install.txt"
adbq shell settings put global overlay_display_devices '800x480/160'
adbq logcat -c
: > "$live_log"
# API17's small log ring is overwritten by EGL chatter; keep a live app-tag-only receipt instead.
"$adb" -s "$serial" logcat -v time -s "$app_tag:I" '*:S' >> "$live_log" 2>&1 &
logcat_pid=$!

launch "" 0
wait_for 'ADMISSION_STATE=WINDOW_ADMITTED_LAB'
wait_for 'SURFACE_BORROWED_READY valid=true owner=Presentation_SurfaceHolder released_by_app=false'
wait_for 'BINDER_FRAME_DRAWN_ON_PRESENTATION_VIEW'
wait_for 'IPC_SESSION_STARTED generation='
setup=$(logs | grep -F 'IPC_SESSION_STARTED generation=' | head -1)
session_id=$(field generation "$setup")
initial_view_pid=$(field type111_view_pid "$setup")
type110_sink_pid=$(field type110_sink_pid "$setup")
compositor_pid=$(field remote_pid "$setup")
[[ -n "$session_id" && -n "$initial_view_pid" && -n "$type110_sink_pid" && -n "$compositor_pid" ]] ||
  fail 'initial session receipt omitted session, View, Type110, or compositor identity'

# Test-only gate: the lab holds the fixture until the runner releases it for this exact session.
wait_for "CL_R4B_CROSS_UID_GATE_WAIT session_id=$session_id "
adbq shell run-as "$package" touch "files/cl-r4b-cross-uid-release-$session_id"
wait_for 'CL_R4_TYPE111_SINK_PROCESS_EXIT_REQUESTED'
death=$(logs | grep -F 'CL_R4_TYPE111_SINK_PROCESS_EXIT_REQUESTED ' | grep -F "pid=$initial_view_pid " | tail -1)
[[ -n "$death" ]] || fail 'View exit was not the identified initial Activity process'
type110_generation=$(field type110_generation "$death")
last_type110_frame=$(field type110_last_frame_id "$death")
[[ "$(field session_id "$death")" == "$session_id" && -n "$type110_generation" &&
   -n "$last_type110_frame" ]] || fail 'pre-death receipt omitted the exact session or Type110 identity'
wait_for 'IPC_VIEW_SINK_DEATH_CALLBACK session_id='
if logs | grep -qF "IPC_VIEW_SINK_DEATH_CALLBACK session_id=$session_id stream_type=110"; then
  fail 'Type110 sink died when only the Type111 View process died'
fi
[[ "$initial_view_pid" != "$type110_sink_pid" && "$initial_view_pid" != "$compositor_pid" &&
   "$type110_sink_pid" != "$compositor_pid" ]] || fail 'View, Type110 sink, and compositor were not separate processes'

replacement_pids=,
replacement_generations=,
last_generation=0
for ordinal in 1 2 3; do
  launch "$session_id" "$ordinal"
  wait_for "CL_R4B_MULTI_VIEW_REPLACEMENT_PASS ordinal=$ordinal session_id=$session_id "
  pass=$(logs | grep -F "CL_R4B_MULTI_VIEW_REPLACEMENT_PASS ordinal=$ordinal session_id=$session_id " | tail -1)
  pid=$(field view_pid "$pass")
  generation=$(field type111_generation "$pass")
  frame=$(field type110_last_frame_id "$pass")
  grep -qF "type110_generation=$type110_generation" <<<"$pass" && grep -qF 'fresh_frame=true pixels_verified=true' <<<"$pass" &&
    [[ -n "$pid" && -n "$generation" && -n "$frame" ]] &&
    (( generation > last_generation && frame > last_type110_frame )) ||
    fail "replacement $ordinal omitted process, generation, Type110 progress, or fresh-frame proof: $pass"
  [[ "$pid" != "$initial_view_pid" ]] || fail 'a replacement reused the initial View PID'
  case "$replacement_pids" in *",$pid,"*) fail 'a View PID was reused across replacements' ;; esac
  case "$replacement_generations" in *",$generation,"*) fail 'a Type111 generation was reused' ;; esac
  replacement_pids="$replacement_pids$pid,"
  replacement_generations="$replacement_generations$generation,"
  last_generation=$generation
  last_type110_frame=$frame
  if (( ordinal < 3 )); then
    wait_for "CL_R4B_MULTI_VIEW_REPLACEMENT_EXIT_REQUESTED ordinal=$ordinal view_pid=$pid "
    for _ in $(seq 1 30); do process_alive "$pid" || break; sleep 1; done
    if process_alive "$pid"; then fail "replacement View process $pid survived its exit request"; fi
    wait_for "IPC_VIEW_SINK_DEATH_CALLBACK session_id=$session_id stream_type=111 "
    logs | grep -F "IPC_VIEW_SINK_DEATH_CALLBACK session_id=$session_id stream_type=111 " |
      grep -qF "stream_generation=$generation" || fail "generation $generation lacks its exact Binder death callback"
  else
    wait_for "CL_R4A_VIEW_REATTACH_PASS session_id=$session_id "
  fi
done

wait_for_any "TYPE111_PARENT_TEARDOWN session_id=$session_id streams_closed=2 result=accepted" \
  "TYPE111_PARENT_TEARDOWN_COMPLETED session_id=$session_id result=accepted late_close_resolution=true"
wait_for 'IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true active_pfd_transfers=0 retained_frame_bytes=0'
for stream_type in 110 111; do
  logs | grep -F "IPC_STREAM_UNREGISTERED session_id=$session_id " | grep -F "stream_type=$stream_type " |
    grep -qF 'active_pfd_transfers=0' || fail "stream $stream_type was not unregistered with zero PFD transfers"
done
if logs | grep -qF "RENDERER_ATTACH_FAILED"; then fail 'RENDERER_ATTACH_FAILED present in the final log'; fi

echo "CL_INT_02_TYPE110_CONTINUITY_API17_PASS session_id=$session_id replacement_pids=$replacement_pids replacement_generations=$replacement_generations replacements=3 unique_pids=true increasing_generations=true parent_session_preserved=true type110_frames_increased=true final_streams_unregistered=true pfd_transfers=0 retained_frame_bytes=0 renderer_attach_failed=false" |
  tee "$receipt/final-status.txt"
