#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sdk=${CL_IMP_03_SDK_ROOT:-"$HOME/Android/r7c2-sdk"}
out=${CL_IMP_03_BUILD_DIR:-"$repo/build/cl-imp-03"}
java_home=${JAVA_HOME:-"$HOME/.local/toolchains/temurin-17.0.20.1+1-aarch64/jdk-17.0.20.1+1/Contents/Home"}
export JAVA_HOME="$java_home" PATH="$java_home/bin:$PATH"
adb="$sdk/platform-tools/adb"
emulator="$sdk/.emulator-intel/emulator/emulator"
avdmanager="$sdk/cmdline-tools/latest/bin/avdmanager"
package=org.claritylink.independentdisplay.lab
attacker_package=org.claritylink.labattacker
attacker_component=org.claritylink.attacker.ExportBoundaryAttackActivity
component=org.claritylink.android.ClarityLinkDisplayActivity
decoder_only=0
type111_mode=0
type111_first=0
if [ "${1:-}" = "--cl-imp-08-decoder" ]; then
  decoder_only=1
  component=org.claritylink.android.Api17DecoderLabActivity
  shift
fi
if [ "${1:-}" = "--cl-r4-type111-first" ]; then
  type111_mode=1
  type111_first=1
  shift
elif [ "${1:-}" = "--cl-r4-type111" ]; then
  type111_mode=1
  shift
fi
[ "$#" -eq 0 ] || { echo 'Unexpected emulator harness arguments.' >&2; exit 2; }
guard="$repo/tools/api17_runner_guard.py"
out=$(python3 "$guard" resolve-build "$repo" "$out") || exit $?
apk="$out/claritylink-display-lab.apk"
attacker_apk="$out/cl-r4-boundary-attacker/cl-r4-boundary-attacker.apk"
[ -f "$apk" ] && [ -f "$attacker_apk" ] && [ -x "$adb" ] && [ -x "$emulator" ] && [ -x "$avdmanager" ] || {
  echo 'Build CL-IMP-03 lab and boundary-attacker APKs, and provide isolated API17 tools first.' >&2; exit 2;
}
run_root=$(python3 "$guard" create-run "$repo" "$out") || exit $?
run_label=$(basename -- "$run_root")
campaign_evidence="$run_root/evidence"
mkdir "$campaign_evidence" "$run_root/avd"
chmod 700 "$campaign_evidence" "$run_root/avd"
ui_test_source="$repo/android/cl-imp-03-app/test/org/claritylink/test/CrashDialogDismissTest.java"
ui_test_build="$run_root/ui-automator"
ui_test_classes="$ui_test_build/classes"
ui_test_dex="$ui_test_build/dex"
ui_test_jar="$ui_test_build/claritylink-crash-dialog-tests.jar"
mkdir -p "$ui_test_classes" "$ui_test_dex"
"$java_home/bin/javac" -source 7 -target 7 \
  -cp "$sdk/platforms/android-17/android.jar:$sdk/platforms/android-17/uiautomator.jar" \
  -d "$ui_test_classes" "$ui_test_source"
"$sdk/build-tools/35.0.0/d8" --min-api 17 \
  --lib "$sdk/platforms/android-17/android.jar" \
  --lib "$sdk/platforms/android-17/uiautomator.jar" \
  --output "$ui_test_dex" "$ui_test_classes/org/claritylink/test/CrashDialogDismissTest.class"
"$java_home/bin/jar" cf "$ui_test_jar" -C "$ui_test_classes" org/claritylink/test
"$java_home/bin/jar" uf "$ui_test_jar" -C "$ui_test_dex" classes.dex
ui_test_sha=$(shasum -a 256 "$ui_test_jar" | awk '{print $1}')
echo "API17_CRASH_DIALOG_TEST_JAR sha256=$ui_test_sha artifact=$run_label/ui-automator/claritylink-crash-dialog-tests.jar"
export ANDROID_HOME="$sdk" ANDROID_SDK_ROOT="$sdk" ANDROID_AVD_HOME="$run_root/avd"
adb_port=$(python3 - <<'PY'
import socket
s=socket.socket();s.bind(('127.0.0.1',0));print(s.getsockname()[1]);s.close()
PY
)
export ADB_SERVER_PORT="$adb_port" ANDROID_ADB_SERVER_PORT="$adb_port"
adb_local() { "$adb" -P "$adb_port" "$@"; }
serial= emulator_pid= adb_server_pid= adb_server_started=0 avd_created=0
avd="climp03_api17_$$"
avd_dir="$run_root/avd/$avd.avd"
avd_ini="$run_root/avd/$avd.ini"
adb_server_owned() {
  [ "$adb_server_started" -eq 1 ] && [ -n "$adb_server_pid" ] &&
    kill -0 "$adb_server_pid" 2>/dev/null || return 1
  parent=$(ps -p "$adb_server_pid" -o ppid= 2>/dev/null | tr -d ' ')
  executable=$(lsof -a -p "$adb_server_pid" -d txt -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)
  command=$(ps -p "$adb_server_pid" -o command= 2>/dev/null || true)
  python3 "$guard" check-adb-child "$adb_server_pid" "$$" \
    "$adb_server_pid" "$parent" "$executable" "$adb" "$command" "$adb_port" \
    >/dev/null 2>&1
}
cleanup() {
  result=$?
  trap - EXIT INT TERM
  if [ -n "$emulator_pid" ] && kill -0 "$emulator_pid" 2>/dev/null; then
    kill "$emulator_pid" 2>/dev/null || true
    wait "$emulator_pid" 2>/dev/null || true
  fi
  # Stop only the foreground ADB server this shell launched as a direct child.
  # If the child identity is ambiguous or changed, leave it untouched.
  if [ "$adb_server_started" -eq 1 ] && adb_server_owned; then
    kill "$adb_server_pid" 2>/dev/null || true
    wait "$adb_server_pid" 2>/dev/null || true
  fi
  if [ "$avd_created" -eq 1 ]; then
    python3 "$guard" cleanup-avd "$run_root" "$avd" ||
      echo 'AVD ownership could not be proven; preserving its files.' >&2
  fi
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

adb_server_log="$run_root/adb-server.log"
"$adb" -P "$adb_port" --one-device CL_IMP_03_NO_PHYSICAL_USB server nodaemon > "$adb_server_log" 2>&1 &
adb_server_pid=$!
adb_server_started=1
server_ready=0
for attempt in $(seq 1 30); do
  if adb_server_owned && adb_local devices >/dev/null 2>&1; then server_ready=1; break; fi
  kill -0 "$adb_server_pid" 2>/dev/null || break
  sleep 0.1
done
[ "$server_ready" -eq 1 ] || {
  echo 'Cannot prove dedicated ADB server ownership for this run; no target commands were sent.' >&2
  exit 3;
}
echo "ISOLATED_ADB_SERVER pid=$adb_server_pid port=$adb_port launch=foreground-child target=none"
source_receipt="$campaign_evidence/api17-source-manifest.sha256"
(
  cd "$repo"
  hash_file() {
    digest=$(shasum -a 256 "$1" | awk '{print $1}')
    printf '%s  %s\n' "$digest" "$2"
  }
  hash_file "$apk" 'build/claritylink-display-lab.apk'
  hash_file "$repo/tools/run_cl_imp_03_emulator.sh" 'tools/run_cl_imp_03_emulator.sh'
  hash_file "$repo/tools/build_cl_imp_03_apks.sh" 'tools/build_cl_imp_03_apks.sh'
  hash_file "$repo/tools/normalize_api17_png.py" 'tools/normalize_api17_png.py'
  hash_file "$guard" 'tools/api17_runner_guard.py'
  hash_file "$attacker_apk" 'build/cl-r4-boundary-attacker.apk'
  hash_file "$repo/android/cl-r4-boundary-attacker/AndroidManifest.xml" 'android/cl-r4-boundary-attacker/AndroidManifest.xml'
  hash_file "$repo/android/cl-r4-boundary-attacker/java/org/claritylink/attacker/ExportBoundaryAttackActivity.java" 'android/cl-r4-boundary-attacker/ExportBoundaryAttackActivity.java'
  hash_file "$repo/tools/verify_api17_pixel_content.swift" 'tools/verify_api17_pixel_content.swift'
  hash_file "$repo/tools/verify_api17_padded_crop_content.swift" 'tools/verify_api17_padded_crop_content.swift'
  hash_file "$repo/android/cl-imp-03-app/AndroidManifest.lab.xml" 'android/cl-imp-03-app/AndroidManifest.lab.xml'
  hash_file "$ui_test_source" 'android/cl-imp-03-app/test/CrashDialogDismissTest.java'
  hash_file "$ui_test_jar" 'artifacts/claritylink-crash-dialog-tests.jar'
  hash_file "$sdk/platforms/android-17/android.jar" 'toolchain/android-17/android.jar'
  hash_file "$sdk/platforms/android-17/uiautomator.jar" 'toolchain/android-17/uiautomator.jar'
  hash_file "$adb" 'toolchain/platform-tools/adb'
  hash_file "$emulator" 'toolchain/emulator/emulator'
  find "$repo/android/cl-imp-03-app/java/org/claritylink/android" \
    "$repo/android/src/main/java/org/claritylink/android" \
    "$repo/src/claritylink-renderer/android-api17" -type f -name '*.java' |
    while IFS= read -r file; do
      label=${file#"$repo"/}
      hash_file "$file" "$label"
    done
) | LC_ALL=C sort > "$source_receipt"
echo "API17_SOURCE_MANIFEST artifact=$run_label/evidence/api17-source-manifest.sha256"
# Ignore adb's `* daemon ...` startup banners; retain every actual serial/status row,
# including unauthorized/offline targets, so the unknown-device guard stays strict.
inventory() { adb_local devices | awk 'NF >= 2 && $1 != "List" && $1 !~ /^\*/ {print $1" "$2}'; }
[ -z "$(inventory)" ] || { echo 'Private ADB server unexpectedly has a target.' >&2; exit 3; }
port=$(python3 - <<'PY'
import socket
for p in (5580,5582,5584):
    held=[]
    try:
        for n in (p,p+1):
            s=socket.socket();s.bind(('127.0.0.1',n));held.append(s)
        print(p);break
    except OSError: pass
    finally:
        for s in held:s.close()
else: raise SystemExit('No free emulator port pair')
PY
)
serial="emulator-$port"
echo "API17_EMULATOR_TARGET avd=$avd serial=$serial port=$port api_expected=17 release_expected=4.2.2 dedicated_adb_port=$adb_port pid=$adb_server_pid"
owned() {
  [ -n "$emulator_pid" ] && kill -0 "$emulator_pid" 2>/dev/null &&
    [ "$(inventory)" = "$serial device" ]
}
python3 "$guard" check-avd "$run_root" "$avd"
printf 'no\n' | "$avdmanager" create avd --name "$avd" \
  --package 'system-images;android-17;default;x86' >/dev/null
python3 "$guard" mark-avd "$run_root" "$avd"
avd_created=1
grep -q '^abi.type=x86$' "$avd_dir/config.ini" || { echo 'AVD ABI mismatch.' >&2; exit 4; }
arch -x86_64 "$emulator" -avd "$avd" -port "$port" -no-window -no-audio \
  -no-snapshot -no-boot-anim -wipe-data -accel off -gpu swiftshader_indirect \
  > "$run_root/emulator.log" 2>&1 &
emulator_pid=$!
ready=0
for attempt in $(seq 1 300); do
  kill -0 "$emulator_pid" 2>/dev/null || { echo 'Owned emulator exited during boot.' >&2; exit 5; }
  devices=$(inventory)
  case "$devices" in ''|"$serial "*) :;; *) echo "Unexpected private ADB target: $devices" >&2; exit 5;; esac
  if owned && [ "$(adb_local -s "$serial" shell getprop sys.boot_completed | tr -d '\r')" = 1 ]; then ready=1; break; fi
  sleep 1
done
[ "$ready" -eq 1 ] || { echo 'API17 emulator boot timeout.' >&2; exit 5; }
api=$(adb_local -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')
release=$(adb_local -s "$serial" shell getprop ro.build.version.release | tr -d '\r')
qemu=$(adb_local -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')
[ "$api:$release:$qemu" = "17:4.2.2:1" ] || { echo 'Guest identity mismatch.' >&2; exit 6; }

owned || exit 7
adb_local -s "$serial" shell settings put global overlay_display_devices '800x480/160'
owned || exit 7
adb_local -s "$serial" install "$apk" >/dev/null
adb_local -s "$serial" install "$attacker_apk" >/dev/null
ui_test_remote="/data/local/tmp/claritylink-crash-dialog-tests-$adb_port.jar"
adb_local -s "$serial" push "$ui_test_jar" "$ui_test_remote" >/dev/null
installed=
for attempt in $(seq 1 10); do
  owned || exit 7
  installed=$(adb_local -s "$serial" shell pm path "$package" | tr -d '\r')
  case "$installed" in package:*) break;; esac
  sleep 1
done
case "$installed" in package:*) :;; *) echo 'Lab APK installation not visible after bounded verification.' >&2; exit 8;; esac
attacker_installed=$(adb_local -s "$serial" shell pm path "$attacker_package" | tr -d '\r')
case "$attacker_installed" in package:*) :;; *) echo 'Separate-UID boundary attacker is not installed.' >&2; exit 8;; esac
app_uid=$(adb_local -s "$serial" shell dumpsys package "$package" | sed -n 's/.*userId=\([0-9][0-9]*\).*/\1/p' | head -1 | tr -d '\r')
[ -n "$app_uid" ] || { echo 'Could not identify installed lab app UID.' >&2; exit 8; }
probe_boundary_checked=0
attacker_uid=$(adb_local -s "$serial" shell dumpsys package "$attacker_package" | sed -n 's/.*userId=\([0-9][0-9]*\).*/\1/p' | head -1 | tr -d '\r')
[ -n "$attacker_uid" ] && [ "$attacker_uid" != "$app_uid" ] || {
  echo "Separate-UID attacker is not isolated: attacker=$attacker_uid app=$app_uid" >&2; exit 9;
}
owner_isolation_output=$(adb_local -s "$serial" shell am start \
  -n "$package/org.claritylink.android.Type110OwnerIsolationTestActivity" 2>&1 | tr -d '\r') || {
  printf '%s\n' "$owner_isolation_output" >&2
  echo 'Could not run same-UID two-session owner-isolation regression.' >&2; exit 9;
}
printf '%s\n' "$owner_isolation_output" | grep -F 'Starting: Intent' >/dev/null || {
  printf '%s\n' "$owner_isolation_output" >&2
  echo 'Two-session owner-isolation activity did not start under the app UID.' >&2; exit 9;
}
owner_isolation_logs=
for owner_attempt in $(seq 1 30); do
  owned || exit 7
  owner_isolation_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
  printf '%s\n' "$owner_isolation_logs" | grep -F 'TYPE110_OWNER_SESSION_ISOLATION_PASS ' >/dev/null && break
  sleep 1
done
printf '%s\n' "$owner_isolation_logs" | grep -E 'TYPE110_OWNER_SESSION_ISOLATION_PASS session_a=([0-9]+) session_b=([0-9]+) sessions_distinct=true concurrent_issue=true reverse_consume=true records_remaining=0' >/dev/null || {
  echo 'Two-session owner records were not independently consumed.' >&2; exit 9;
}
printf '%s\n' "$owner_isolation_logs" | grep -E 'TYPE110_OWNER_CAP_RECOVERY_PASS pending_cap=32 cap_rejected=true expired_records_pruned=32 orphan_temp_pruned=true orphan_claim_pruned=true new_session_issued=true artifacts_remaining=0' >/dev/null || {
  echo 'Expired and orphan recovery-owner files were not safely reclaimed.' >&2; exit 9;
}
owner_isolation_receipt="$campaign_evidence/api17-owner-session-isolation-$adb_port.txt"
printf '%s\n' "$owner_isolation_logs" | grep 'TYPE110_OWNER_SESSION_ISOLATION_PASS ' > "$owner_isolation_receipt"
echo "TYPE110_OWNER_SESSION_ISOLATION_RUNTIME_PASS concurrent_issue=true reverse_consume=true records_remaining=0 artifact=$run_label/evidence/$(basename -- "$owner_isolation_receipt")"
owner_cap_receipt="$campaign_evidence/api17-owner-cap-recovery-$adb_port.txt"
printf '%s\n' "$owner_isolation_logs" | grep 'TYPE110_OWNER_CAP_RECOVERY_PASS ' > "$owner_cap_receipt"
echo "TYPE110_OWNER_CAP_RECOVERY_RUNTIME_PASS expired_records=32 orphan_temp=true orphan_claim=true new_issue=true artifacts_remaining=0 artifact=$run_label/evidence/$(basename -- "$owner_cap_receipt")"
assert_type110_probe_cross_uid_denied() {
  owned || exit 7
  before_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
  before_teardown=$(printf '%s\n' "$before_logs" | grep -F -c 'TYPE111_PARENT_TEARDOWN session_id=' || true)
  adb_local -s "$serial" shell am start -n "$attacker_package/$attacker_component" \
    --el attack_session_id "$1" --el attack_generation "$2" \
    --el attack_last_frame "$3" --ei attack_sink_pid "$4" >/dev/null
  wait_for 'CL_R4_CROSS_UID_ATTACKS_PASS'
  logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
  after_teardown=$(printf '%s\n' "$logs" | grep -F -c 'TYPE111_PARENT_TEARDOWN session_id=' || true)
  [ "$before_teardown" -eq "$after_teardown" ] || {
    echo 'Separate-UID attack changed parent-session teardown state.' >&2; exit 9;
  }
  [ "$(printf '%s\n' "$logs" | grep -F -c 'ATTACK_DENIED operation=probe' || true)" -eq 7 ] || {
    echo 'Separate-UID attacker did not have all seven probe-service launches denied.' >&2; exit 9;
  }
  printf '%s\n' "$logs" | grep -F "CL_R4_CROSS_UID_ATTACKS_PASS uid=$attacker_uid target_uid=$app_uid attempts=19 denied=19" >/dev/null || {
    echo 'Separate-UID attacker did not reject all probe/service operations.' >&2; exit 9;
  }
  echo "TYPE110_PROBE_CROSS_UID_DENIED attacker_uid=$attacker_uid app_uid=$app_uid sink_pid=$4 compositor_pid=$5"
}
invoke_type110_probe_privileged() {
  owned || exit 7
  wait_for 'TYPE110_POST_DEATH_PROBE_INTERNAL_START session_id='
  wait_for 'TYPE110_POST_DEATH_PROBE_READY '
  wait_for 'CL_R4_TYPE110_AFTER_TYPE111_SINK_DEATH_PASS '
  wait_for 'CL_R4_PARENT_SESSION_TEARDOWN_PASS '
  probe_line=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r' |
    grep -F "TYPE110_POST_DEATH_PROBE_READY " | grep -F "session_id=$1 " | tail -1)
  probe_pid=$(printf '%s\n' "$probe_line" | sed -n 's/.*TYPE110_POST_DEATH_PROBE_READY pid=\([0-9][0-9]*\).*/\1/p')
  view_pid=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r' |
    sed -n 's/.*ACTIVITY_READY .*pid=\([0-9][0-9]*\).*/\1/p' | head -1)
  [ -n "$probe_pid" ] && [ -n "$view_pid" ] && [ "$probe_pid" != "$view_pid" ] &&
    [ "$probe_pid" != "$4" ] && [ "$probe_pid" != "$5" ] || {
      echo "Recovery producer PID check failed (probe=$probe_pid view=$view_pid type110=$4 compositor=$5)." >&2; return 1;
    }
  echo "TYPE110_RECOVERY_PRODUCER_PROCESS_PASS session_id=$1 pid=$probe_pid view_pid=$view_pid type110_sink_pid=$4 compositor_pid=$5 manifest_process=:type110_probe"
  if [ "$probe_boundary_checked" -eq 0 ]; then
    assert_type110_probe_cross_uid_denied "$1" "$2" "$3" "$4" "$5"
    probe_boundary_checked=1
  fi
}
start_lab_activity_privileged() {
  owned || exit 7
  scenario=$1
  case "$scenario" in
    presentation|type111|type111_first|controlled_exit|crash)
      component=org.claritylink.android.ClarityLinkDisplayActivity
      set -- --es mode EMULATOR_PRESENTATION --es emulator_only_confirmation CL_IMP_03_OFFLINE_EMULATOR_ONLY
      case "$scenario" in
        type111) set -- "$@" --ez type111_fixture_mode true ;;
        type111_first) set -- "$@" --ez type111_fixture_mode true --ez type111_first_mode true ;;
        controlled_exit) set -- "$@" --ez controlled_exit_after_validation true ;;
        crash) set -- "$@" --ez crash_after_first_frame true ;;
      esac
      output=$(adb_local -s "$serial" shell am start -n "$package/$component" "$@" 2>&1) || {
        printf '%s\n' "$output" >&2; return 1;
      }
      ;;
    decoder)
      component=org.claritylink.android.Api17DecoderLabActivity
      output=$(adb_local -s "$serial" shell am start -n "$package/$component" 2>&1) || {
        printf '%s\n' "$output" >&2; return 1;
      }
      ;;
    status_only)
      component=org.claritylink.android.ClarityLinkDisplayActivity
      output=$(adb_local -s "$serial" shell am start -n "$package/$component" 2>&1) || {
        printf '%s\n' "$output" >&2; return 1;
      }
      ;;
    *) echo "Unsupported lab launch scenario: $scenario" >&2; return 1 ;;
  esac
  printf '%s\n' "$output" | grep -F 'Starting: Intent' >/dev/null || {
    echo "Privileged shell could not launch scenario $scenario." >&2
    printf '%s\n' "$output" >&2; return 1;
  }
}
complete_probe_session_and_stop_isolated_package() {
  wait_for 'CL_R4_TYPE110_AFTER_TYPE111_SINK_DEATH_PASS'
  wait_for 'CL_R4_PARENT_SESSION_TEARDOWN_PASS'
  # Parent teardown is a session event. Stop the two specifically owned services
  # gracefully so onDestroy receipts are lifecycle evidence, not force-stop guesses.
  owned || exit 7
  wait_for 'CL_R4_OWNED_SERVICES_STOP_REQUESTED'
  wait_for 'TYPE110_LAB_SINK_DESTROYED '
  wait_for 'IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true active_pfd_transfers=0 retained_frame_bytes=0'
}
assert_type110_progress_precedes_parent_teardown() {
  session=$1
  old_frame=$2
  sink_pid=$3
  source_logs=$4
  death_line=$(printf '%s\n' "$source_logs" | grep -nF "IPC_VIEW_SINK_DEATH_CALLBACK session_id=$session stream_type=111" | head -1 | cut -d: -f1)
  frame_line=$(printf '%s\n' "$source_logs" | grep -nF "TYPE110_LAB_SINK_FRAME_ACCEPTED pid=$sink_pid" |
    grep -E "frame_id=$((old_frame + 1))([[:space:]]|$)" | head -1 | cut -d: -f1)
  teardown_line=$(printf '%s\n' "$source_logs" | grep -nF "TYPE111_PARENT_TEARDOWN session_id=$session streams_closed=2 result=accepted" | tail -1 | cut -d: -f1)
  [ -n "$death_line" ] && [ -n "$frame_line" ] && [ -n "$teardown_line" ] &&
    [ "$death_line" -lt "$frame_line" ] && [ "$frame_line" -lt "$teardown_line" ] || {
      echo "Type110 did not progress after Type111 sink death and before parent teardown (session=$session)." >&2
      return 1
    }
}
adb_local -s "$serial" logcat -c
owned || exit 7
if [ "$decoder_only" -eq 1 ]; then
  :
elif [ "$type111_first" -eq 1 ]; then
  start_lab_activity_privileged type111_first
elif [ "$type111_mode" -eq 1 ]; then
  start_lab_activity_privileged type111
else
  start_lab_activity_privileged presentation
fi
wait_for() {
  marker=$1
  for attempt in $(seq 1 180); do
    owned || { echo 'Owned emulator changed during validation.' >&2; return 1; }
    logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
    printf '%s\n' "$logs" | grep -F "$marker" >/dev/null && return 0
    sleep 1
  done
  echo "Timed out waiting for app evidence: $marker" >&2
  printf '%s\n' "$logs" >&2
  return 1
}
if [ "$decoder_only" -eq 1 ]; then
  start_lab_activity_privileged decoder
  wait_for 'CLIMP08_API17_MEDIACODEC_PASS'
  logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
  expected_order=110_first
  [ "$type111_first" -eq 1 ] && expected_order=111_first
  printf '%s\n' "$logs" | grep -F "IPC_SESSION_STARTED generation=" | grep -F "setup_order=$expected_order" >/dev/null || {
    echo "API17 stream setup order did not match $expected_order." >&2; exit 9;
  }
  printf '%s\n' "$logs" | grep -F 'resolutionReset=64x64 independentStreams=true surfaceSubmissionOnly=true physicalScanout=UNPROVEN' >/dev/null || {
    echo 'Decoder result did not report bounded API17 Surface submission and explicit scanout limitation.' >&2
    printf '%s\n' "$logs" >&2
    exit 9
  }
  owned || exit 7
  adb_local -s "$serial" shell am force-stop "$package"
  adb_local -s "$serial" shell am force-stop "$attacker_package"
  adb_local -s "$serial" uninstall "$attacker_package" >/dev/null
    adb_local -s "$serial" uninstall "$package" >/dev/null
  adb_local -s "$serial" shell 'settings put global overlay_display_devices ""'
  echo 'CL_IMP_08_API17_MEDIACODEC_EMULATOR_PASS dual_stream=true resolution_reset=64x64 owned_surfaces=borrowed scanout=unproven install_scope=isolated_emulator'
  exit 0
fi
wait_for 'ADMISSION_STATE=WINDOW_ADMITTED_LAB'
wait_for 'SURFACE_BORROWED_READY valid=true owner=Presentation_SurfaceHolder released_by_app=false'
wait_for 'BINDER_FRAME_DRAWN_ON_PRESENTATION_VIEW'
wait_for 'SYNTHETIC_FRAME_DRAWN_ON_PRESENTATION_CANVAS'
wait_for 'BINDER_VIEW_PROOF_SAVED'
proof="$campaign_evidence/api17-binder-view-proof-$adb_port.png"
proof_tmp="$proof.tmp"
owned || exit 7
# API17 adbd predates `exec-out`; non-interactive `shell` is the compatible path.
adb_local -s "$serial" shell run-as "$package" cat files/test6a-binder-view-proof.png > "$proof_tmp"
python3 "$repo/tools/normalize_api17_png.py" "$proof_tmp"
mv "$proof_tmp" "$proof"
echo "BINDER_VIEW_PROOF_SAVED artifact=$run_label/evidence/$(basename -- "$proof")"

if [ "$type111_mode" -eq 1 ]; then
  wait_for 'CL_R4_TYPE111_BUFFER_DECODE_BINDER_VIEW_PASS'
  wait_for 'TYPE111_PRODUCER_WAIT_BOUNDS_PASS'
  wait_for 'CL_R4_TYPE111_INFLIGHT_PRODUCER_DEATH_CLEANUP_PASS'
  wait_for 'CL_R4_TYPE111_PRODUCER_DEATH_RESTART_PASS'
  wait_for 'CL_R4_TYPE111_DECODER_FAULT_RECOVERY_PASS'
  wait_for 'CL_R5_API17_CONTROL_VALIDATION_PASS'
  wait_for 'CL_R5_API17_PRESENTATION_LIFETIME_PASS'
  wait_for 'CL_R4_API17_DUAL_STREAM_SATURATION_PASS'
  wait_for 'CL_R4_TYPE111_LIVE_GENERATION_PASS'
  wait_for 'CL_R4_STREAM_GENERATION_ISOLATION_PASS'
  wait_for 'CL_R4_TYPE110_ISOLATION_PASS type111_decoder_reset=true type110_decoder_generation=970001 type110_frame_before_after=true binder_session_preserved=true fixture_only=true'
  wait_for 'CL_R4_PADDED_CROP_VIEW_PASS adapter=YUV420-planar source_stride=40 source_slice_height=40 crop=8,8,24,24 binder_pfd=true view_draw=true decoded_h264_output=false'
  wait_for 'CL_R4_TYPE111_SINK_PROCESS_EXIT_REQUESTED'
  wait_for 'IPC_VIEW_SINK_DEATH_CALLBACK session_id='
  logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
  app_pid=$(printf '%s\n' "$logs" | sed -n 's/.*ACTIVITY_READY .*pid=\([0-9][0-9]*\).*/\1/p' | head -1)
  [ -n "$app_pid" ] || { echo 'Type111 process identity was not captured.' >&2; exit 9; }
  death_line=$(printf '%s\n' "$logs" | grep -F 'CL_R4_TYPE111_SINK_PROCESS_EXIT_REQUESTED ' | tail -1)
  printf '%s\n' "$death_line" | grep -F "pid=$app_pid " >/dev/null || {
    echo 'The Type111 sink process exit was not the identified Activity process.' >&2; exit 9;
  }
  session_id=$(printf '%s\n' "$death_line" | sed -n 's/.*session_id=\([0-9][0-9]*\).*/\1/p')
  type110_generation=$(printf '%s\n' "$death_line" | sed -n 's/.*type110_generation=\([0-9][0-9]*\).*/\1/p')
  type110_last_frame=$(printf '%s\n' "$death_line" | sed -n 's/.*type110_last_frame_id=\([0-9][0-9]*\).*/\1/p')
  type110_sink_pid=$(printf '%s\n' "$death_line" | sed -n 's/.*type110_sink_pid=\([0-9][0-9]*\).*/\1/p')
  compositor_pid=$(printf '%s\n' "$logs" | sed -n 's/.*IPC_REMOTE_PROCESS_READY pid=\([0-9][0-9]*\).*/\1/p' | head -1)
  [ -n "$session_id" ] && [ -n "$type110_generation" ] && [ -n "$type110_last_frame" ] &&
    [ -n "$type110_sink_pid" ] && [ -n "$compositor_pid" ] || {
    echo 'Missing process or stream identity from the pre-death receipt.' >&2; exit 9;
  }
  [ "$app_pid" != "$type110_sink_pid" ] && [ "$app_pid" != "$compositor_pid" ] &&
    [ "$type110_sink_pid" != "$compositor_pid" ] || {
    echo 'Type111 view, Type110 sink, and compositor were not separate processes.' >&2; exit 9;
  }
  printf '%s\n' "$logs" | grep -F "IPC_STREAM_REGISTERED session_id=$session_id stream_type=110" >/dev/null || {
    echo 'Type110 Binder stream was not registered before Type111 process death.' >&2; exit 9;
  }
  printf '%s\n' "$logs" | grep -F "IPC_STREAM_REGISTERED session_id=$session_id stream_type=111" >/dev/null || {
    echo 'Type111 Binder stream was not registered before its process death.' >&2; exit 9;
  }
  ps_snapshot=$(adb_local -s "$serial" shell ps | tr -d '\r')
  printf '%s\n' "$ps_snapshot" | awk -v pid="$app_pid" '$2==pid {found=1} END {exit !found}' && {
    echo "Type111 View process $app_pid remains alive after its self-termination request." >&2; exit 9;
  }
  printf '%s\n' "$logs" | grep -F "IPC_VIEW_SINK_DEATH_CALLBACK session_id=$session_id stream_type=111" >/dev/null || {
    echo 'Compositor did not observe Type111 Binder sink death.' >&2; exit 9;
  }
  if printf '%s\n' "$logs" | grep -F "IPC_VIEW_SINK_DEATH_CALLBACK session_id=$session_id stream_type=110" >/dev/null; then
    echo 'Type110 sink died when only the Type111 View process died.' >&2; exit 9;
  fi
  process_state=$(printf '%s\n' "$ps_snapshot" | awk -v pid="$app_pid" '$2 == pid {print}')
  [ -z "$process_state" ] || { echo "Type111 sink process still exists: $process_state" >&2; exit 9; }
  window_state=$(adb_local -s "$serial" shell dumpsys window windows | tr -d '\r' | grep -F "mOwnerUid=$app_uid" || true)
  [ -z "$window_state" ] || { echo "ClarityLink window remains after Type111 sink death: $window_state" >&2; exit 9; }
  echo "TYPE111_SINK_DEATH_VERIFIED pid=$app_pid type110_sink_pid=$type110_sink_pid compositor_pid=$compositor_pid type110_death_callback=false"
  invoke_type110_probe_privileged "$session_id" "$type110_generation" "$type110_last_frame" "$type110_sink_pid" "$compositor_pid"
  complete_probe_session_and_stop_isolated_package
  logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
  printf '%s\n' "$logs" > "$campaign_evidence/api17-type111-logcat-$adb_port.txt"
  assert_type110_progress_precedes_parent_teardown "$session_id" "$type110_last_frame" "$type110_sink_pid" "$logs"
  printf '%s\n' "$logs" | grep -F "CL_R4_TYPE110_AFTER_TYPE111_SINK_DEATH_PASS session_id=$session_id stream_generation=$type110_generation old_last_frame_id=$type110_last_frame" >/dev/null || {
    echo 'Type110 did not report post-death progress on the original stream identity.' >&2; exit 9;
  }
  printf '%s\n' "$logs" | grep -F "TYPE110_LAB_SINK_FRAME_ACCEPTED pid=$type110_sink_pid" | grep -E "frame_id=$((type110_last_frame + 1))([[:space:]]|$)" >/dev/null || {
    echo 'The independent Type110 sink did not record the next frame after Type111 sink death.' >&2; exit 9;
  }
  printf '%s\n' "$logs" | grep -F "TYPE111_PARENT_TEARDOWN session_id=$session_id streams_closed=2 result=accepted" >/dev/null || {
    echo 'Parent teardown did not close the remaining Type110 child stream.' >&2; exit 9;
  }
  for stream_type in 110 111; do
    printf '%s\n' "$logs" | grep -F "IPC_STREAM_REGISTERED session_id=" | grep -F "stream_type=$stream_type" >/dev/null || {
      echo "Missing actual Binder registration for stream type $stream_type." >&2; exit 9;
    }
    printf '%s\n' "$logs" | grep -F 'IPC_REMOTE_FRAME ' | grep -F 'accepted=true' | grep -F "stream_type=$stream_type" >/dev/null || {
      echo "No accepted Binder/PFD frame for stream type $stream_type." >&2; exit 9;
    }
    printf '%s\n' "$logs" | grep -F "IPC_STREAM_UNREGISTERED session_id=" | grep -F "stream_type=$stream_type" >/dev/null || {
      echo "Stream type $stream_type was not independently cleaned up." >&2; exit 9;
    }
  done
  printf '%s\n' "$logs" | grep -F 'CL_R4_API17_DUAL_STREAM_SATURATION_PASS' | grep -F 'type111_queue_full_rejected=true' | grep -F 'type110_progress_before_release=true' | grep -F 'cross_route=false' >/dev/null || {
    echo 'API17 dual-stream saturation proof is incomplete.' >&2; exit 9;
  }
  printf '%s\n' "$logs" | grep -F 'CL_R5_API17_CONTROL_VALIDATION_PASS' | grep -F 'duplicate_capability=true' | grep -F 'unsupported_context=true' | grep -F 'out_of_bounds_geometry=true' >/dev/null || {
    echo 'API17 Type111 capability/control validation evidence is incomplete.' >&2; exit 9;
  }
  printf '%s\n' "$logs" | grep -F 'CL_R5_API17_PRESENTATION_LIFETIME_PASS' | grep -F 'maps_to_waze=true' | grep -F 'transport_identity_preserved=true' >/dev/null || {
    echo 'API17 Type111 presentation/transport lifetime evidence is incomplete.' >&2; exit 9;
  }
  printf '%s\n' "$logs" | grep -F 'CL_R4_STREAM_GENERATION_ISOLATION_PASS' | grep -F 'stream_type=110' | grep -F 'stream_type_111_generation=' | grep -F 'stale_rejected=true' >/dev/null || {
    echo 'Per-stream live generation isolation was not proven.' >&2; exit 9;
  }
  printf '%s\n' "$logs" | grep -F 'IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true active_pfd_transfers=0 retained_frame_bytes=0' >/dev/null || {
    echo 'Remote process cleanup counters are nonzero or unavailable.' >&2; exit 9;
  }
  process_state=$(adb_local -s "$serial" shell ps | tr -d '\r' | awk -v pid="$app_pid" '$2 == pid {print}')
  [ -z "$process_state" ] || { echo "Consumer process still exists: $process_state" >&2; exit 9; }
  window_state=$(adb_local -s "$serial" shell dumpsys window windows | tr -d '\r' | grep -F "mOwnerUid=$app_uid" || true)
  [ -z "$window_state" ] || { echo "ClarityLink window remains after consumer death: $window_state" >&2; exit 9; }
  echo "TYPE111_CONSUMER_DEATH_VERIFIED pid=$app_pid process_absent=true app_window_absent=true"
  printf '%s\n' "$logs" | grep -F 'IPC_REMOTE_FRAME ' | grep -F 'accepted=true' >/dev/null || {
    echo 'No decoded frame crossed the receiver Binder/PFD boundary.' >&2; exit 9;
  }
  for proof_name in type111-blue-frame-1.png type111-blue-frame-4.png type111-green-frame-1.png type111-green-frame-3.png type111-padded-crop-frame.png type111-independent-producer-frame.png type111-restarted-producer-frame.png; do
    proof_path="$campaign_evidence/api17-$proof_name-$adb_port.png"
    proof_tmp="$proof_path.tmp"
    owned || exit 7
    adb_local -s "$serial" shell run-as "$package" cat "files/$proof_name" > "$proof_tmp"
    python3 "$repo/tools/normalize_api17_png.py" "$proof_tmp"
    mv "$proof_tmp" "$proof_path"
  done
  crop_proof="$campaign_evidence/api17-type111-padded-crop-frame.png-$adb_port.png"
  green_control="$campaign_evidence/api17-type111-green-frame-1.png-$adb_port.png"
  crop_receipt="$campaign_evidence/api17-type111-padded-crop-content-$adb_port.json"
  swift "$repo/tools/verify_api17_padded_crop_content.swift" \
    "$crop_proof" "$green_control" "$apk" "$crop_receipt"
  shasum -a 256 "$apk" "$campaign_evidence/api17-type111-logcat-$adb_port.txt" \
    "$campaign_evidence/api17-type111-blue-frame-1.png-$adb_port.png" \
    "$campaign_evidence/api17-type111-independent-producer-frame.png-$adb_port.png" \
    "$campaign_evidence/api17-type111-restarted-producer-frame.png-$adb_port.png" \
    "$campaign_evidence/api17-type111-green-frame-1.png-$adb_port.png" \
    "$campaign_evidence/api17-type111-padded-crop-frame.png-$adb_port.png" \
    "$crop_receipt" \
    "$repo/tools/verify_api17_padded_crop_content.swift" \
    > "$campaign_evidence/api17-type111-artifact-hashes-$adb_port.sha256"
  adb_local -s "$serial" shell am force-stop "$package"
  adb_local -s "$serial" uninstall "$package" >/dev/null
  adb_local -s "$serial" shell 'settings put global overlay_display_devices ""'
  echo "CL_R4_TYPE111_BUFFER_TO_VIEW_RUNTIME_PASS api=$api release=$release actual_mediacodec=true binder_pfd=true view_draw=true screenshots=7 cleanup=pass padded_crop_adapter_ipc=true isolated_producer_death_restart=pass"
  exit 0
fi
wait_for 'CLIMP09_RENDER_GEOMETRY_PASS'
wait_for 'CLIMP09_WARNING_RESUME_PASS'
wait_for 'DIAGNOSTIC_FRAME_PIPELINE_PASS static=1 synthetic=3 canvas_frames=4'
wait_for 'CL_R1_BINDER_HANDLER_VIEW_RACE_PASS'
wait_for 'CL_R3_MALFORMED_BINDER_SUITE_PASS cases=11 same_session=true post_rejection_frame_drawn=true'
wait_for 'CL_R3_GENERATION_TRANSITION_PASS transitions=2 rapid=true'
malformed_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
for malformed_case in negative_dimensions zero_dimensions oversized_dimensions integer_overflow_dimensions unsupported_pixel_format invalid_stride short_payload long_payload missing_pfd invalid_crop stale_generation; do
  printf '%s\n' "$malformed_logs" | grep -F "CL_R3_MALFORMED_BINDER_REJECT case=$malformed_case" >/dev/null || {
    echo "Missing actual Binder rejection receipt for $malformed_case." >&2; exit 9;
  }
done
[ "$(printf '%s\n' "$malformed_logs" | grep -c 'IPC_REMOTE_FRAME_REJECT .*active_pfd_transfers=0')" -ge 10 ] || {
  echo 'Malformed Binder requests did not all produce zero-active-PFD rejection receipts.' >&2; exit 9;
}
[ "$(printf '%s\n' "$malformed_logs" | grep -c 'IPC_REMOTE_GENERATION_REPLACED .*accepted=true binder_session_preserved=true')" -eq 2 ] || {
  echo 'Expected two successful live generation transitions on one Binder session.' >&2; exit 9;
}
if printf '%s\n' "$malformed_logs" | grep -F 'IPC_REMOTE_DISCONNECTED' >/dev/null; then
  echo 'Binder session disconnected during generation transition.' >&2; exit 9;
fi
adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r' \
  > "$campaign_evidence/api17-normal-logcat-$adb_port.txt"
for frame_index in 1 2 3 4; do
  frame_name="api17-diagnostic-frame-$frame_index.png"
  frame_path="$campaign_evidence/api17-diagnostic-frame-$frame_index-$adb_port.png"
  frame_tmp="$frame_path.tmp"
  owned || exit 7
  adb_local -s "$serial" shell run-as "$package" cat "files/$frame_name" > "$frame_tmp"
  python3 "$repo/tools/normalize_api17_png.py" "$frame_tmp"
  mv "$frame_tmp" "$frame_path"
done
pixel_receipt="$campaign_evidence/api17-pixel-content-$adb_port.json"
swift "$repo/tools/verify_api17_pixel_content.swift" \
  "$campaign_evidence/api17-diagnostic-frame-1-$adb_port.png" \
  "$campaign_evidence/api17-diagnostic-frame-2-$adb_port.png" \
  "$campaign_evidence/api17-diagnostic-frame-3-$adb_port.png" \
  "$campaign_evidence/api17-diagnostic-frame-4-$adb_port.png" \
  "$apk" "$pixel_receipt"
wait_for 'IPC_SESSION_STARTED'
wait_for 'IPC_SYNTHETIC_FRAME_ACCEPTED'
wait_for 'IPC_REMOTE_FRAME generation='
logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
remote_pid=$(printf '%s\n' "$logs" | sed -n 's/.*IPC_SESSION_STARTED .*remote_pid=\([0-9][0-9]*\).*/\1/p' | head -1)
app_pid=$(printf '%s\n' "$logs" | sed -n 's/.*ACTIVITY_READY .*pid=\([0-9][0-9]*\).*/\1/p' | head -1)
[ -n "$remote_pid" ] && [ -n "$app_pid" ] && [ "$remote_pid" != "$app_pid" ] || {
  echo "IPC endpoint did not run in a separate project-owned process (app=$app_pid remote=$remote_pid)." >&2
  printf '%s\n' "$logs" >&2
  adb_local -s "$serial" shell ps >&2
  exit 9
}
active_windows=$(adb_local -s "$serial" shell dumpsys window windows | tr -d '\r')
printf '%s\n' "$active_windows" | grep -F "mOwnerUid=$app_uid" >/dev/null || {
  echo 'Cannot prove an app-owned window existed before display removal.' >&2; exit 9;
}
owned || exit 7
adb_local -s "$serial" shell 'settings put global overlay_display_devices ""'
wait_for 'SURFACE_BORROWED_LOST owner=Presentation_SurfaceHolder released_by_app=false'
wait_for 'ADMISSION_STATE=FAULTED'
wait_for 'RENDERER_RELEASED'
wait_for 'IPC_REMOTE_END'
wait_for 'IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true'
owned || exit 7
adb_local -s "$serial" shell am force-stop "$package"
owned || exit 7
adb_local -s "$serial" shell settings put global overlay_display_devices '800x480/160'
adb_local -s "$serial" logcat -c
owned || exit 7
# Controlled termination is a separate lifecycle experiment. The process is
# killed by its own emulator-only Activity after its Binder/PFD race suite.
start_lab_activity_privileged controlled_exit
wait_for 'CL_R2_CONTROLLED_PROCESS_EXIT_REQUESTED'
controlled_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
printf '%s\n' "$controlled_logs" > "$campaign_evidence/api17-controlled-death-logcat-$adb_port.txt"
controlled_pid=$(printf '%s\n' "$controlled_logs" | sed -n 's/.*CL_R2_CONTROLLED_PROCESS_EXIT_REQUESTED pid=\([0-9][0-9]*\).*/\1/p' | tail -1)
[ -n "$controlled_pid" ] || { echo 'Missing controlled process identity.' >&2; exit 9; }
controlled_line=$(printf '%s\n' "$controlled_logs" | grep -F 'CL_R2_CONTROLLED_PROCESS_EXIT_REQUESTED ' | tail -1)
controlled_session=$(printf '%s\n' "$controlled_line" | sed -n 's/.*session_id=\([0-9][0-9]*\).*/\1/p')
controlled_generation=$(printf '%s\n' "$controlled_line" | sed -n 's/.*type110_generation=\([0-9][0-9]*\).*/\1/p')
controlled_last_frame=$(printf '%s\n' "$controlled_line" | sed -n 's/.*type110_last_frame_id=\([0-9][0-9]*\).*/\1/p')
controlled_sink_pid=$(printf '%s\n' "$controlled_line" | sed -n 's/.*type110_sink_pid=\([0-9][0-9]*\).*/\1/p')
controlled_compositor_pid=$(printf '%s\n' "$controlled_line" | sed -n 's/.*compositor_pid=\([0-9][0-9]*\).*/\1/p')
[ -n "$controlled_session" ] && [ -n "$controlled_generation" ] &&
  [ -n "$controlled_last_frame" ] && [ -n "$controlled_sink_pid" ] &&
  [ -n "$controlled_compositor_pid" ] || { echo 'Missing parent or Type110 identities for controlled process-death recovery.' >&2; exit 9; }
controlled_dead=0
for attempt in $(seq 1 30); do
  owned || exit 7
  ps=$(adb_local -s "$serial" shell ps | tr -d '\r')
  if ! printf '%s\n' "$ps" | awk -v pid="$controlled_pid" '$2==pid {found=1} END {exit !found}'; then
    controlled_dead=1; break
  fi
  sleep 1
done
[ "$controlled_dead" -eq 1 ] || { echo "Controlled app PID $controlled_pid did not exit." >&2; exit 9; }
wait_for "IPC_VIEW_SINK_DEATH_CALLBACK session_id=$controlled_session stream_type=111"
controlled_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
printf '%s\n' "$controlled_logs" | grep -F "IPC_STREAM_UNREGISTERED session_id=$controlled_session stream_type=111" >/dev/null || {
  echo 'Controlled process death did not unregister the Type111 child.' >&2; exit 9;
}
if printf '%s\n' "$controlled_logs" | grep -F "IPC_VIEW_SINK_DEATH_CALLBACK session_id=$controlled_session stream_type=110" >/dev/null; then
  echo 'Type110 sink itself died when only the Type111 View process died.' >&2; exit 9;
fi
controlled_windows=$(adb_local -s "$serial" shell dumpsys window windows | tr -d '\r')
if printf '%s\n' "$controlled_windows" | grep -F "mOwnerUid=$app_uid" >/dev/null; then
  echo 'App-owned window remained after controlled process termination.' >&2; exit 9
fi
owned || exit 7
invoke_type110_probe_privileged "$controlled_session" "$controlled_generation" "$controlled_last_frame" "$controlled_sink_pid" "$controlled_compositor_pid"
complete_probe_session_and_stop_isolated_package
controlled_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
printf '%s\n' "$controlled_logs" | grep -F "TYPE110_LAB_SINK_FRAME_ACCEPTED pid=$controlled_sink_pid" | grep -E "frame_id=$((controlled_last_frame + 1))([[:space:]]|$)" >/dev/null || {
  echo 'Type110 did not accept the next frame on its existing stream after Type111 process death.' >&2; exit 9;
}
printf '%s\n' "$controlled_logs" | grep -F 'IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true active_pfd_transfers=0 retained_frame_bytes=0' >/dev/null || {
  echo 'Parent teardown left compositor transfers or retained bytes.' >&2; exit 9;
}
assert_type110_progress_precedes_parent_teardown "$controlled_session" "$controlled_last_frame" "$controlled_sink_pid" "$controlled_logs"
owned || exit 7
adb_local -s "$serial" logcat -c
start_lab_activity_privileged status_only
wait_for 'STATUS_ONLY feature_disabled=true recovered_state=discarded'
recovery_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
if printf '%s\n' "$recovery_logs" | grep -E 'PRESENTATION_SHOWN|DISPLAY_ENUMERATION' >/dev/null; then
  echo 'Controlled-death recovery automatically re-admitted a display.' >&2; exit 10
fi
echo "CL_R2_CONTROLLED_PROCESS_DEATH_PASS app_pid=$controlled_pid type111_death=observed type110_survived=true post_death_frame=true parent_teardown=true pfd_transfers=0 retained_bytes=0 app_windows=none restart=status_only"
owned || exit 7
adb_local -s "$serial" shell am force-stop "$package"
adb_local -s "$serial" logcat -c
owned || exit 7
start_lab_activity_privileged crash
wait_for 'BINDER_FRAME_DRAWN_ON_PRESENTATION_VIEW'
wait_for 'SYNTHETIC_FRAME_DRAWN_ON_PRESENTATION_CANVAS'
wait_for 'CLIMP09_RENDER_GEOMETRY_PASS'
wait_for 'CLIMP09_WARNING_RESUME_PASS'
wait_for 'DIAGNOSTIC_FRAME_PIPELINE_PASS static=1 synthetic=3 canvas_frames=4'
wait_for 'CL_R1_BINDER_HANDLER_VIEW_RACE_PASS'
wait_for 'IPC_SYNTHETIC_FRAME_ACCEPTED'
wait_for 'CL_R2_UNCAUGHT_CRASH_REQUESTED'
logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
crash_remote_pid=$(printf '%s\n' "$logs" | sed -n 's/.*IPC_SESSION_STARTED .*remote_pid=\([0-9][0-9]*\).*/\1/p' | head -1)
[ -n "$crash_remote_pid" ] || { echo 'Missing remote compositor PID in crash-recovery run.' >&2; exit 9; }
crash_owner_line=$(printf '%s\n' "$logs" | grep -F 'CL_R2_UNCAUGHT_CRASH_REQUESTED ' | tail -1)
crash_owner_session=$(printf '%s\n' "$crash_owner_line" | sed -n 's/.*session_id=\([0-9][0-9]*\).*/\1/p')
crash_type110_generation=$(printf '%s\n' "$crash_owner_line" | sed -n 's/.*type110_generation=\([0-9][0-9]*\).*/\1/p')
crash_type110_last_frame=$(printf '%s\n' "$crash_owner_line" | sed -n 's/.*type110_last_frame_id=\([0-9][0-9]*\).*/\1/p')
crash_type110_sink_pid=$(printf '%s\n' "$crash_owner_line" | sed -n 's/.*type110_sink_pid=\([0-9][0-9]*\).*/\1/p')
crash_compositor_pid=$(printf '%s\n' "$crash_owner_line" | sed -n 's/.*compositor_pid=\([0-9][0-9]*\).*/\1/p')
[ -n "$crash_owner_session" ] && [ -n "$crash_type110_generation" ] &&
  [ -n "$crash_type110_last_frame" ] && [ -n "$crash_type110_sink_pid" ] &&
  [ -n "$crash_compositor_pid" ] || { echo 'Missing Type110 and parent receipts for uncaught-crash recovery.' >&2; exit 9; }
crash_logged=0
for attempt in $(seq 1 30); do
  crash_log=$(adb_local -s "$serial" logcat -d -s AndroidRuntime:E '*:S' | tr -d '\r')
  if printf '%s\n' "$crash_log" | grep -F 'CL-IMP-03 emulator-only crash recovery probe' >/dev/null; then
    crash_logged=1
    break
  fi
  sleep 1
done
 [ "$crash_logged" -eq 1 ] || { echo 'Expected emulator-only crash was not recorded.' >&2; exit 9; }
# On API17 AMS keeps the crashing Activity pending its system-owned error
# dialog. Capture that framework state before dismissing only its verified OK.
crash_evidence="$campaign_evidence/api17-crash-$adb_port"
mkdir -p "$crash_evidence"
crash_log=$(adb_local -s "$serial" logcat -d -s AndroidRuntime:E '*:S' | tr -d '\r')
printf '%s\n' "$crash_log" > "$crash_evidence/logcat.txt"
windows=$(adb_local -s "$serial" shell dumpsys window windows | tr -d '\r')
printf '%s\n' "$windows" > "$crash_evidence/windows-before-dismissal.txt"
adb_local -s "$serial" shell uiautomator dump /data/local/tmp/claritylink-crash-hierarchy.xml >/dev/null
adb_local -s "$serial" pull /data/local/tmp/claritylink-crash-hierarchy.xml "$crash_evidence/hierarchy-before-dismissal.xml" >/dev/null
grep -F 'Unfortunately, ClarityLink Display Lab has stopped.' "$crash_evidence/hierarchy-before-dismissal.xml" >/dev/null || {
  echo 'Expected ClarityLink crash dialog was not identified in UI hierarchy.' >&2; exit 9;
}
printf '%s\n' "$windows" | grep -F 'Application Error' >/dev/null || {
  echo 'Window Manager did not report the system Application Error window.' >&2; exit 9;
}
printf '%s\n' "$windows" | grep -F 'mOwnerUid=1000' >/dev/null || {
  echo 'Crash dialog is not positively identified as a system-owned window.' >&2; exit 9;
}
ps=$(adb_local -s "$serial" shell ps | tr -d '\r')
printf '%s\n' "$ps" > "$crash_evidence/processes-before-dismissal.txt"
crash_app_pid=$(printf '%s\n' "$ps" | awk -v name="$package" '$NF==name || index($NF,name ":")==1 {print $2; exit}')
[ -n "$crash_app_pid" ] || { echo 'Expected framework-waiting crash process absent before dialog action.' >&2; exit 9; }
owned || exit 7
dialog_test_output=$(adb_local -s "$serial" shell uiautomator runtest "$ui_test_remote" -c org.claritylink.test.CrashDialogDismissTest 2>&1 | tr -d '\r') || {
  printf '%s\n' "$dialog_test_output" >&2; exit 9;
}
printf '%s\n' "$dialog_test_output" > "$crash_evidence/uiautomator-dismissal.txt"
printf '%s\n' "$dialog_test_output" | grep -E 'OK \(1 test\)' >/dev/null || {
  echo 'UiAutomator did not report a successful exact-dialog dismissal.' >&2
  printf '%s\n' "$dialog_test_output" >&2; exit 9;
}
crash_clean=0
for attempt in $(seq 1 30); do
  owned || exit 7
  ps=$(adb_local -s "$serial" shell ps | tr -d '\r')
  windows=$(adb_local -s "$serial" shell dumpsys window windows | tr -d '\r')
  adb_local -s "$serial" shell uiautomator dump /data/local/tmp/claritylink-post-crash.xml >/dev/null 2>&1 || true
  adb_local -s "$serial" pull /data/local/tmp/claritylink-post-crash.xml "$crash_evidence/hierarchy-after-dismissal.xml" >/dev/null 2>&1 || true
  app_windows=$(printf '%s\n' "$windows" | grep -F "mOwnerUid=$app_uid" || true)
  if ! printf '%s\n' "$ps" | awk -v pid="$crash_app_pid" '$2==pid {found=1} END {exit !found}' &&
     [ -z "$app_windows" ] && ! printf '%s\n' "$windows" | grep -F 'Application Error' >/dev/null; then
    crash_clean=1; break
  fi
  sleep 1
done
[ "$crash_clean" -eq 1 ] || {
  echo 'Dismissed crash dialog but app process/window state did not clear.' >&2
  printf '%s\n' "$ps" >&2; printf '%s\n' "$windows" >&2; exit 9;
}
crash_cleanup_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
printf '%s\n' "$crash_cleanup_logs" > "$crash_evidence/claritylink-logcat-after-dismissal.txt"
printf '%s\n' "$crash_cleanup_logs" | grep -F "IPC_VIEW_SINK_DEATH_CALLBACK session_id=$crash_owner_session stream_type=111" >/dev/null || {
  echo 'Actual crash did not notify the Type111 sink death recipient.' >&2; exit 9;
}
printf '%s\n' "$crash_cleanup_logs" | grep -F "IPC_STREAM_UNREGISTERED session_id=$crash_owner_session stream_type=111" >/dev/null || {
  echo 'Actual crash did not unregister Type111.' >&2; exit 9;
}
if printf '%s\n' "$crash_cleanup_logs" | grep -F "IPC_VIEW_SINK_DEATH_CALLBACK session_id=$crash_owner_session stream_type=110" >/dev/null; then
  echo 'Type110 sink itself died when only the Type111 application process crashed.' >&2; exit 9;
fi
printf '%s\n' "$windows" > "$crash_evidence/windows-after-dismissal.txt"
printf '%s\n' "$ps" > "$crash_evidence/processes-after-dismissal.txt"
owned || exit 7
invoke_type110_probe_privileged "$crash_owner_session" "$crash_type110_generation" "$crash_type110_last_frame" "$crash_type110_sink_pid" "$crash_compositor_pid"
complete_probe_session_and_stop_isolated_package
crash_cleanup_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
printf '%s\n' "$crash_cleanup_logs" > "$crash_evidence/claritylink-logcat-after-parent-teardown.txt"
printf '%s\n' "$crash_cleanup_logs" | grep -F "TYPE110_LAB_SINK_FRAME_ACCEPTED pid=$crash_type110_sink_pid" | grep -E "frame_id=$((crash_type110_last_frame + 1))([[:space:]]|$)" >/dev/null || {
  echo 'Type110 did not progress after the Type111 application crash.' >&2; exit 9;
}
printf '%s\n' "$crash_cleanup_logs" | grep -F 'IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true active_pfd_transfers=0 retained_frame_bytes=0' >/dev/null || {
  echo 'Parent teardown after app-error dismissal left resources.' >&2; exit 9;
}
assert_type110_progress_precedes_parent_teardown "$crash_owner_session" "$crash_type110_last_frame" "$crash_type110_sink_pid" "$crash_cleanup_logs"
echo "CL_R2_UNCAUGHT_CRASH_FRAMEWORK_DIALOG_HANDLED app_pid=$crash_app_pid dialog_owner_uid=1000 dialog=identified_and_dismissed type111_death=observed type110_survived=true post_crash_frame=true parent_teardown=true pfd_transfers=0 retained_bytes=0 app_windows=none"
adb_local -s "$serial" logcat -c
owned || exit 7
start_lab_activity_privileged status_only
wait_for 'STATUS_ONLY feature_disabled=true recovered_state=discarded'
logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
if printf '%s\n' "$logs" | grep -E 'PRESENTATION_SHOWN|DISPLAY_ENUMERATION' >/dev/null; then
  echo 'Recovered activity automatically re-admitted a display.' >&2; exit 10
fi
owned || exit 7
adb_local -s "$serial" shell am force-stop "$attacker_package"
adb_local -s "$serial" uninstall "$attacker_package" >/dev/null
adb_local -s "$serial" uninstall "$package" >/dev/null
remaining=unknown
for attempt in $(seq 1 10); do
  owned || exit 7
  remaining=$(adb_local -s "$serial" shell pm path "$package" | tr -d '\r')
  [ -z "$remaining" ] && break
  sleep 1
done
[ -z "$remaining" ] || { echo 'Emulator app package remains after bounded uninstall verification.' >&2; exit 11; }
adb_local -s "$serial" shell 'settings put global overlay_display_devices ""'
echo "CL_IMP_03_LAB_RUNTIME_STAGES_PASS api=$api release=$release install=pass cross_uid_probe_denied=pass admission=pass canvas_draw=pass separate_process_ipc=pass crash_recovery=pass uninstall=pass cl_r3_acceptance=PASS malformed_binder=pass generation_transition=pass pixel_content=pass"
