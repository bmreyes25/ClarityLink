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
type111_reattach=0
type110_failure=0
owner_death=0
reentrant_teardown=0
delayed_death_callback=0
if [ "${1:-}" = "--cl-r4b-reentrant-teardown-type111-first" ]; then
  type111_mode=1
  type111_first=1
  reentrant_teardown=1
  shift
elif [ "${1:-}" = "--cl-r4b-reentrant-teardown" ]; then
  type111_mode=1
  reentrant_teardown=1
  shift
elif [ "${1:-}" = "--cl-r4b-type110-failure" ]; then
  type110_failure=1
  shift
elif [ "${1:-}" = "--cl-r4b-parent-owner-death" ]; then
  type111_mode=1
  owner_death=1
  shift
elif [ "${1:-}" = "--cl-imp-08-decoder" ]; then
  decoder_only=1
  component=org.claritylink.android.Api17DecoderLabActivity
  shift
fi
if [ "${1:-}" = "--cl-r5-type111-first-reattach" ]; then
  type111_mode=1
  type111_first=1
  type111_reattach=1
  shift
elif [ "${1:-}" = "--cl-r4-type111-first" ]; then
  type111_mode=1
  type111_first=1
  shift
elif [ "${1:-}" = "--cl-r4-type111" ]; then
  type111_mode=1
  shift
elif [ "${1:-}" = "--cl-r4-type111-reattach" ]; then
  type111_mode=1
  type111_reattach=1
  shift
fi
if [ "${1:-}" = "--cl-r4b-delayed-callback" ]; then
  type111_mode=1
  type111_reattach=1
  delayed_death_callback=1
  shift
elif [ "${1:-}" = "--cl-r4b-delayed-callback-type111-first" ]; then
  type111_mode=1
  type111_first=1
  type111_reattach=1
  delayed_death_callback=1
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
    --el attack_last_frame "$3" --ei attack_sink_pid "$4" \
    --ei attack_compositor_pid "$5" >/dev/null
  wait_for 'CL_R4_CROSS_UID_ATTACKS_PASS'
  logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
  after_teardown=$(printf '%s\n' "$logs" | grep -F -c 'TYPE111_PARENT_TEARDOWN session_id=' || true)
  [ "$before_teardown" -eq "$after_teardown" ] || {
    echo 'Separate-UID attack changed parent-session teardown state.' >&2; exit 9;
  }
  [ "$(printf '%s\n' "$logs" | grep -F -c 'ATTACK_DENIED operation=probe' || true)" -eq 7 ] || {
    echo 'Separate-UID attacker did not have all seven probe-service launches denied.' >&2; exit 9;
  }
  [ "$(printf '%s\n' "$logs" | grep -F -c 'ATTACK_DENIED operation=service component=Type110SinkFailureTestService' || true)" -ge 1 ] || {
    echo 'Separate-UID start of the destructive Type110 failure helper was not denied.' >&2; exit 9;
  }
  [ "$(printf '%s\n' "$logs" | grep -F -c 'ATTACK_DENIED operation=bind_service component=Type110SinkFailureTestService' || true)" -ge 1 ] || {
    echo 'Separate-UID bind of the destructive Type110 failure helper was not explicitly denied.' >&2; exit 9;
  }
  [ "$(printf '%s\n' "$logs" | grep -F -c 'ATTACK_UNVERIFIED operation=bind_service component=Type110SinkFailureTestService' || true)" -eq 0 ] || {
    echo 'Separate-UID bind failure for the destructive Type110 helper was ambiguous.' >&2; exit 9;
  }
  [ "$(printf '%s\n' "$logs" | grep -F -c 'ATTACK_NOT_DENIED operation=bind_service component=Type110SinkFailureTestService' || true)" -eq 0 ] || {
    echo 'Separate-UID attacker bound the destructive Type110 failure helper.' >&2; exit 9;
  }
  [ "$(printf '%s\n' "$logs" | grep -F -c 'ATTACK_DENIED operation=service component=CompositorOwnerDeathTestService' || true)" -ge 1 ] || {
    echo 'Separate-UID start of the compositor owner-death helper was not denied.' >&2; exit 9;
  }
  [ "$(printf '%s\n' "$logs" | grep -F -c 'ATTACK_DENIED operation=bind_service component=CompositorOwnerDeathTestService' || true)" -ge 1 ] || {
    echo 'Separate-UID bind of the compositor owner-death helper was not explicitly denied.' >&2; exit 9;
  }
  [ "$(printf '%s\n' "$logs" | grep -F -c 'ATTACK_NOT_DENIED operation=bind_service component=CompositorOwnerDeathTestService' || true)" -eq 0 ] || {
    echo 'Separate-UID attacker bound the compositor owner-death helper.' >&2; exit 9;
  }
  printf '%s\n' "$logs" | grep -F "CL_R4_CROSS_UID_ATTACKS_PASS uid=$attacker_uid target_uid=$app_uid attempts=23 denied=23" >/dev/null || {
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
  reattach_session_arg=${2:-}
  case "$scenario" in
    presentation|type111|type111_owner_death|type111_reentrant_teardown|type111_first|type111_first_reentrant|type111_first_reattach|type111_reattach|type111_delayed_callback_first|type111_first_delayed_callback_first|type111_delayed_callback_replacement|controlled_exit|crash)
      component=org.claritylink.android.ClarityLinkDisplayActivity
      set -- --es mode EMULATOR_PRESENTATION --es emulator_only_confirmation CL_IMP_03_OFFLINE_EMULATOR_ONLY
      case "$scenario" in
        type111) set -- "$@" --ez type111_fixture_mode true ;;
        type111_owner_death) set -- "$@" --ez type111_fixture_mode true --ez owner_death_test true ;;
        type111_reentrant_teardown) set -- "$@" --ez type111_fixture_mode true --ez reentrant_teardown_test true ;;
        type111_first_reentrant) set -- "$@" --ez type111_fixture_mode true --ez type111_first_mode true --ez reentrant_teardown_test true ;;
        type111_first) set -- "$@" --ez type111_fixture_mode true --ez type111_first_mode true ;;
        type111_first_reattach)
          set -- "$@" --ez type111_fixture_mode true --ez type111_first_mode true --ez type111_reattach_test true
          ;;
        type111_delayed_callback_first)
          set -- "$@" --ez type111_fixture_mode true --ez type111_reattach_test true --ez delayed_death_callback_test true
          ;;
        type111_first_delayed_callback_first)
          set -- "$@" --ez type111_fixture_mode true --ez type111_first_mode true --ez type111_reattach_test true --ez delayed_death_callback_test true
          ;;
        type111_delayed_callback_replacement)
          set -- "$@" --ez type111_fixture_mode true --ez type111_reattach_test true --ez delayed_death_callback_test true
          if [ -n "$reattach_session_arg" ]; then
            set -- "$@" --el type111_reattach_session_id "$reattach_session_arg"
          fi
          ;;
        type111_reattach)
          set -- "$@" --ez type111_fixture_mode true --ez type111_reattach_test true
          if [ -n "$reattach_session_arg" ]; then
            set -- "$@" --el type111_reattach_session_id "$reattach_session_arg"
          fi
          ;;
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
  if [ "$reentrant_teardown" -eq 1 ]; then
    start_lab_activity_privileged type111_first_reentrant
  elif [ "$delayed_death_callback" -eq 1 ]; then
    start_lab_activity_privileged type111_first_delayed_callback_first
  elif [ "$type111_reattach" -eq 1 ]; then
    start_lab_activity_privileged type111_first_reattach
  else
    start_lab_activity_privileged type111_first
  fi
elif [ "$type111_mode" -eq 1 ]; then
  if [ "$owner_death" -eq 1 ]; then
    start_lab_activity_privileged type111_owner_death
  elif [ "$reentrant_teardown" -eq 1 ]; then
    start_lab_activity_privileged type111_reentrant_teardown
  elif [ "$delayed_death_callback" -eq 1 ]; then
    start_lab_activity_privileged type111_delayed_callback_first
  elif [ "$type111_reattach" -eq 1 ]; then
    start_lab_activity_privileged type111_reattach
  else
    start_lab_activity_privileged type111
  fi
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
initial_activity_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
initial_type111_pid=$(printf '%s\n' "$initial_activity_logs" | sed -n 's/.*ACTIVITY_READY .*pid=\([0-9][0-9]*\).*/\1/p' | head -1)
[ -n "$initial_type111_pid" ] || { echo 'Initial Type111 process identity was not captured.' >&2; exit 9; }
expected_setup_order=110_first
[ "$type111_first" -eq 1 ] && expected_setup_order=111_first
initial_setup_receipt=$(printf '%s\n' "$initial_activity_logs" | grep -F 'IPC_SESSION_STARTED generation=' | head -1)
printf '%s\n' "$initial_setup_receipt" | grep -F "setup_order=$expected_setup_order " >/dev/null || {
  echo "Initial API17 session did not prove setup_order=$expected_setup_order before process replacement." >&2
  exit 9
}
printf '%s\n' "$initial_setup_receipt" > "$campaign_evidence/api17-initial-setup-order-$adb_port.txt"
initial_compositor_pid=$(printf '%s\n' "$initial_setup_receipt" | sed -n 's/.*remote_pid=\([0-9][0-9]*\).*/\1/p')
initial_setup_type111_pid=$(printf '%s\n' "$initial_setup_receipt" | sed -n 's/.*type111_view_pid=\([0-9][0-9]*\).*/\1/p')
initial_session_generation=$(printf '%s\n' "$initial_setup_receipt" | sed -n 's/.*IPC_SESSION_STARTED generation=\([0-9][0-9]*\).*/\1/p')
initial_type110_sink_pid=$(printf '%s\n' "$initial_setup_receipt" | sed -n 's/.*type110_sink_pid=\([0-9][0-9]*\).*/\1/p')
[ -n "$initial_compositor_pid" ] && [ -n "$initial_setup_type111_pid" ] &&
  [ -n "$initial_session_generation" ] && [ -n "$initial_type110_sink_pid" ] || {
  echo 'Initial session receipt omitted compositor, Type111, Type110, or session identity.' >&2; exit 9;
}
[ "$initial_setup_type111_pid" = "$initial_type111_pid" ] || {
  echo 'Initial setup receipt Type111 PID did not match the observed Activity process.' >&2; exit 9;
}
proof="$campaign_evidence/api17-binder-view-proof-$adb_port.png"
proof_tmp="$proof.tmp"
owned || exit 7
# API17 adbd predates `exec-out`; non-interactive `shell` is the compatible path.
adb_local -s "$serial" shell run-as "$package" cat files/test6a-binder-view-proof.png > "$proof_tmp"
python3 "$repo/tools/normalize_api17_png.py" "$proof_tmp"
mv "$proof_tmp" "$proof"
echo "BINDER_VIEW_PROOF_SAVED artifact=$run_label/evidence/$(basename -- "$proof")"

if [ "$type110_failure" -eq 1 ]; then
  logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
  sink_ready=$(printf '%s\n' "$logs" | grep -F 'TYPE110_LAB_SINK_READY ' | tail -1)
  type110_identity=$(printf '%s\n' "$logs" | grep -F 'IPC_STREAM_REGISTERED ' |
    grep -F 'stream_type=110 ' | tail -1)
  type111_identity=$(printf '%s\n' "$logs" | grep -F 'IPC_STREAM_REGISTERED ' |
    grep -F 'stream_type=111 ' | tail -1)
  sink_pid=$(printf '%s\n' "$sink_ready" | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p')
  session_id=$(printf '%s\n' "$type110_identity" | sed -n 's/.*session_id=\([0-9][0-9]*\).*/\1/p')
  type110_generation=$(printf '%s\n' "$type110_identity" | sed -n 's/.*stream_generation=\([0-9][0-9]*\).*/\1/p')
  compositor_pid=$(printf '%s\n' "$logs" | sed -n 's/.*IPC_SESSION_STARTED .*remote_pid=\([0-9][0-9]*\).*/\1/p' | head -1)
  [ -n "$sink_pid" ] && [ -n "$session_id" ] && [ -n "$type110_generation" ] &&
    [ -n "$compositor_pid" ] &&
    printf '%s\n' "$sink_ready" | grep -F "session_id=$session_id" >/dev/null &&
    printf '%s\n' "$type111_identity" | grep -F "session_id=$session_id " >/dev/null || {
      echo 'Could not prove both stream identities before Type110-only sink failure.' >&2
      exit 9
    }
  echo "CL_R4B_TYPE110_FAILURE_PRECONDITION session_id=$session_id type110_generation=$type110_generation sink_pid=$sink_pid type111_registered=true"
  assert_type110_probe_cross_uid_denied "$session_id" "$type110_generation" 0 "$sink_pid" "$compositor_pid"
  adb_local -s "$serial" shell am startservice -n \
    "$package/org.claritylink.android.Type110SinkFailureTestService" \
    --ei target_pid "$sink_pid" --el target_session_id "$session_id" \
    --es confirmation CL_R4B_OFFLINE_EMULATOR_ONLY >/dev/null
  wait_for "CL_R4B_TYPE110_SINK_FAILURE_TARGET_VERIFIED pid=$sink_pid "
  wait_for "CL_R4B_TYPE110_SINK_FAILURE_REQUESTED pid=$sink_pid"
  sink_death_process_receipt="$campaign_evidence/api17-type110-sink-death-process-$adb_port.txt"
  sink_pid_exited=0
  for death_attempt in $(seq 1 30); do
    owned || exit 7
    death_ps=$(adb_local -s "$serial" shell ps | tr -d '\r')
    printf '%s\n' "$death_ps" > "$sink_death_process_receipt"
    if ! printf '%s\n' "$death_ps" | awk -v pid="$sink_pid" '$2==pid {found=1} END {exit !found}'; then
      sink_pid_exited=1
      break
    fi
    sleep 1
  done
  [ "$sink_pid_exited" -eq 1 ] || {
    adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r' \
      > "$campaign_evidence/api17-type110-sink-death-logcat-$adb_port.txt"
    adb_local -s "$serial" shell dumpsys activity services | tr -d '\r' \
      > "$campaign_evidence/api17-type110-sink-death-services-$adb_port.txt"
    echo "Type110 sink process $sink_pid did not exit after the guarded kill request." >&2
    echo "Process snapshot: $run_label/evidence/$(basename -- "$sink_death_process_receipt")" >&2
    echo "Logcat: $run_label/evidence/api17-type110-sink-death-logcat-$adb_port.txt" >&2
    echo "Services: $run_label/evidence/api17-type110-sink-death-services-$adb_port.txt" >&2
    exit 9
  }
  echo "TYPE110_SINK_PID_EXIT_OBSERVED pid=$sink_pid session_id=$session_id artifact=$run_label/evidence/$(basename -- "$sink_death_process_receipt")"
  callback_seen=0
  for callback_attempt in $(seq 1 30); do
    owned || exit 7
    callback_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
    if printf '%s\n' "$callback_logs" | grep -F "IPC_VIEW_SINK_DEATH_CALLBACK session_id=$session_id stream_type=110 " >/dev/null; then
      callback_seen=1
      break
    fi
    sleep 1
  done
  printf '%s\n' "$callback_logs" > "$campaign_evidence/api17-type110-sink-death-logcat-$adb_port.txt"
  if [ "$callback_seen" -ne 1 ]; then
    adb_local -s "$serial" shell dumpsys activity services | tr -d '\r' \
      > "$campaign_evidence/api17-type110-sink-death-services-$adb_port.txt"
    echo "Type110 sink PID $sink_pid exited but compositor death callback was not observed within 30s." >&2
    echo "Logcat: $run_label/evidence/api17-type110-sink-death-logcat-$adb_port.txt" >&2
    echo "Processes: $run_label/evidence/$(basename -- "$sink_death_process_receipt")" >&2
    echo "Services: $run_label/evidence/api17-type110-sink-death-services-$adb_port.txt" >&2
    exit 9
  fi
  teardown_observed=0
  for teardown_attempt in $(seq 1 30); do
    owned || exit 7
    teardown_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
    if printf '%s\n' "$teardown_logs" | grep -F "TYPE110_OWNER_SESSION_INVALIDATED session_id=$session_id cause=owner_sink_death streams_closed=2" >/dev/null ||
       printf '%s\n' "$teardown_logs" | grep -F "TYPE111_PARENT_TEARDOWN session_id=$session_id streams_closed=2 result=accepted" >/dev/null; then
      teardown_observed=1
      break
    fi
    sleep 1
  done
  [ "$teardown_observed" -eq 1 ] || { echo 'Neither sink death nor the owner END invalidated the Type110 session.' >&2; exit 9; }
  wait_for "IPC_STREAM_UNREGISTERED session_id=$session_id stream_type=110 "
  wait_for "IPC_STREAM_UNREGISTERED session_id=$session_id stream_type=111 "
  wait_for 'LIFECYCLE_STOP reason=type110-lab-sink-disconnected'
  wait_for 'IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true active_pfd_transfers=0 retained_frame_bytes=0'
  final_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
  printf '%s\n' "$final_logs" > "$campaign_evidence/api17-type110-owner-failure-logcat-$adb_port.txt"
  if ! printf '%s\n' "$final_logs" | grep -F "TYPE110_OWNER_SESSION_INVALIDATED session_id=$session_id cause=owner_sink_death streams_closed=2" >/dev/null &&
     ! printf '%s\n' "$final_logs" | grep -F "TYPE111_PARENT_TEARDOWN session_id=$session_id streams_closed=2 result=accepted" >/dev/null; then
    echo 'Type110 sink failure did not invalidate the parent session through either teardown actor.' >&2; exit 9
  fi
  final_cleanup=$(printf '%s\n' "$final_logs" | grep -F 'IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true' | tail -1)
  printf '%s\n' "$final_cleanup" | grep -F 'active_pfd_transfers=0 retained_frame_bytes=0' >/dev/null || {
    echo "Type110-only failure cleanup counters are not zero: $final_cleanup" >&2; exit 9;
  }
  ps_snapshot=$(adb_local -s "$serial" shell ps | tr -d '\r')
  printf '%s\n' "$ps_snapshot" | awk -v pid="$sink_pid" '$2==pid {found=1} END {exit !found}' && {
    echo "Type110 sink PID $sink_pid remains alive after the targeted failure." >&2; exit 9;
  }
  echo "CL_R4B_TYPE110_ONLY_FAILURE_PASS session_id=$session_id type110_generation=$type110_generation type111_invalidated=true streams_unregistered=2 active_pfd_transfers=0 retained_frame_bytes=0 cross_uid_denied=21/21 sink_pid_exited=true fixture_only=true"
  shasum -a 256 "$campaign_evidence/api17-type110-owner-failure-logcat-$adb_port.txt" \
    > "$campaign_evidence/api17-type110-owner-failure-artifact-hashes-$adb_port.sha256"
  owned || exit 7
  adb_local -s "$serial" shell am force-stop "$attacker_package"
  adb_local -s "$serial" uninstall "$attacker_package" >/dev/null
  adb_local -s "$serial" uninstall "$package" >/dev/null
  adb_local -s "$serial" shell 'settings put global overlay_display_devices ""'
  echo "CL_R4B_API17_TYPE110_FAILURE_EMULATOR_PASS session_id=$session_id dedicated_adb_port=$adb_port serial=$serial"
  exit 0
fi

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
  if [ "$owner_death" -eq 1 ]; then
    wait_for 'CL_R4B_OWNER_SESSION_READY '
    logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
    ready_line=$(printf '%s\n' "$logs" | grep -F 'CL_R4B_OWNER_SESSION_READY ' | tail -1)
    owner_pid=$(printf '%s\n' "$ready_line" | sed -n 's/.*parent_owner_pid=\([0-9][0-9]*\).*/\1/p')
    session_id=$(printf '%s\n' "$ready_line" | sed -n 's/.*session_id=\([0-9][0-9]*\).*/\1/p')
    type110_connection_id=$(printf '%s\n' "$ready_line" | sed -n 's/.*type110_connection_id=\([0-9][0-9]*\).*/\1/p')
    type110_generation=$(printf '%s\n' "$ready_line" | sed -n 's/.*type110_generation=\([0-9][0-9]*\).*/\1/p')
    type110_last_frame=$(printf '%s\n' "$ready_line" | sed -n 's/.*type110_last_frame_id=\([0-9][0-9]*\).*/\1/p')
    type111_connection_id=$(printf '%s\n' "$ready_line" | sed -n 's/.*type111_connection_id=\([0-9][0-9]*\).*/\1/p')
    type111_generation=$(printf '%s\n' "$ready_line" | sed -n 's/.*type111_generation=\([0-9][0-9]*\).*/\1/p')
    [ -n "$owner_pid" ] && [ -n "$session_id" ] && [ -n "$type110_connection_id" ] &&
      [ -n "$type110_generation" ] && [ -n "$type110_last_frame" ] &&
      [ -n "$type111_connection_id" ] && [ -n "$type111_generation" ] || {
        echo 'Parent-owner death precondition omitted process or stream identity.' >&2; exit 9;
      }
    printf '%s\n' "$ready_line" | grep -F 'valid_type110_and_type111_frames=true session_kept_open=true' >/dev/null || {
      echo 'Parent-owner death lacks valid dual-stream frame evidence.' >&2; exit 9;
    }
    adb_local -s "$serial" shell dumpsys window windows | tr -d '\r' \
      > "$campaign_evidence/api17-compositor-owner-death-window-before-$adb_port.txt"
    awk -v package="$package" '
      /Window #[0-9]+ Window/ {
        if (matched && on_secondary) found=1
        in_window=1; matched=($0 ~ package); on_secondary=0
      }
      in_window && matched && /mDisplayId=1/ {on_secondary=1}
      /^$/ {if (matched && on_secondary) found=1; in_window=0}
      END {if (matched && on_secondary) found=1; exit !found}
    ' "$campaign_evidence/api17-compositor-owner-death-window-before-$adb_port.txt" || {
      echo 'No app-owned secondary Presentation window was present before compositor death.' >&2; exit 9;
    }
    adb_local -s "$serial" shell am startservice \
      -n "$package/org.claritylink.android.CompositorOwnerDeathTestService" \
      --es confirmation CL_R4B_OFFLINE_EMULATOR_ONLY \
      --ei target_pid "$owner_pid" --el session_id "$session_id" \
      --el type110_connection_id "$type110_connection_id" \
      --el type110_generation "$type110_generation" \
      --el type110_last_frame_id "$type110_last_frame" \
      --el type111_connection_id "$type111_connection_id" \
      --el type111_generation "$type111_generation" >/dev/null
    wait_for_owner_death_marker() {
      marker=$1
      for owner_attempt in $(seq 1 180); do
        owned || { echo 'Owned emulator changed during parent-owner death check.' >&2; return 1; }
        owner_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
        if printf '%s\n' "$owner_logs" | grep -F 'CL_R4B_PARENT_OWNER_DEATH_FAIL ' >/dev/null; then
          printf '%s\n' "$owner_logs" | grep -F 'CL_R4B_PARENT_OWNER_DEATH_FAIL ' >&2
          return 1
        fi
        printf '%s\n' "$owner_logs" | grep -F "$marker" >/dev/null && return 0
        sleep 1
      done
      echo "Timed out waiting for parent-owner death evidence: $marker" >&2
      return 1
    }
    wait_for_owner_death_marker "CL_R4B_OWNER_DEATH_TARGET_VERIFIED pid=$owner_pid "
    wait_for_owner_death_marker "CL_R4B_PARENT_OWNER_DEATH_REQUESTED pid=$owner_pid "
    wait_for_owner_death_marker "CL_R4B_OWNER_DEATH_BINDER_DISCONNECTED old_pid=$owner_pid "
    wait_for 'CL_R4B_ACTIVITY_OWNER_INVALIDATED '
    wait_for 'CL_R4B_ACTIVITY_OWNER_CLEANUP_PASS '
    owner_death_early_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
    printf '%s\n' "$owner_death_early_logs" \
      > "$campaign_evidence/api17-compositor-owner-death-early-logcat-$adb_port.txt"
    wait_for_owner_death_marker "CL_R4B_OWNER_DEATH_FRESH_SESSION_RECOVERY_PASS "
    wait_for_owner_death_marker "CL_R4B_PARENT_OWNER_DEATH_PASS old_pid=$owner_pid "
    owner_logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
    owner_logs="$owner_death_early_logs
$owner_logs"
    printf '%s\n' "$owner_logs" > "$campaign_evidence/api17-compositor-owner-death-logcat-$adb_port.txt"
    new_owner_pid=$(printf '%s\n' "$owner_logs" | sed -n \
      's/.*CL_R4B_PARENT_OWNER_DEATH_PASS old_pid=[0-9][0-9]* new_pid=\([0-9][0-9]*\).*/\1/p' | tail -1)
    [ -n "$new_owner_pid" ] && [ "$new_owner_pid" != "$owner_pid" ] || {
      echo 'Surviving observer did not identify a fresh compositor process.' >&2; exit 9;
    }
    ps_snapshot=$(adb_local -s "$serial" shell ps | tr -d '\r')
    printf '%s\n' "$ps_snapshot" > "$campaign_evidence/api17-compositor-owner-death-processes-$adb_port.txt"
    printf '%s\n' "$ps_snapshot" | awk -v pid="$owner_pid" '$2==pid {found=1} END {exit !found}' && {
      echo "Dead compositor PID $owner_pid remains in the OS process list." >&2; exit 9;
    }
    printf '%s\n' "$owner_logs" | grep -E 'PRESENTATION_DISMISS_REQUESTED reason=parent-owner-(died|replaced)' >/dev/null || {
      echo 'Surviving Activity did not request secondary Presentation dismissal after owner loss.' >&2; exit 9;
    }
    adb_local -s "$serial" shell dumpsys window windows | tr -d '\r' \
      > "$campaign_evidence/api17-compositor-owner-death-window-state-$adb_port.txt"
    adb_local -s "$serial" shell dumpsys activity services | tr -d '\r' \
      > "$campaign_evidence/api17-compositor-owner-death-services-$adb_port.txt"
    if grep -E 'ServiceRecord.*(FrameLabSinkService|Type111ProducerService)' \
      "$campaign_evidence/api17-compositor-owner-death-services-$adb_port.txt" >/dev/null; then
      echo 'Type110 sink or Type111 producer service remained registered after owner loss.' >&2; exit 9;
    fi
    printf '%s\n' "$owner_logs" | grep -F 'TYPE110_LAB_SINK_DESTROYED ' >/dev/null || {
      echo 'Independent Type110 sink process did not report service destruction.' >&2; exit 9;
    }
    printf '%s\n' "$owner_logs" | grep -F 'TYPE111_PRODUCER_RUN_PASS ' | grep -F 'resources_released=true' >/dev/null || {
      echo 'Type111 producer did not report decoder/worker completion before owner death.' >&2; exit 9;
    }
    if printf '%s\n' "$owner_logs" | grep -F 'PRESENTATION_CLOSE_FAILED' >/dev/null; then
      echo 'Activity reported a failed Presentation close after parent-owner death.' >&2; exit 9;
    fi
    if awk -v package="$package" '
      /Window #[0-9]+ Window/ {
        if (matched && on_secondary) found=1
        in_window=1; matched=($0 ~ package); on_secondary=0
      }
      in_window && matched && /mDisplayId=1/ {on_secondary=1}
      /^$/ {if (matched && on_secondary) found=1; in_window=0}
      END {if (matched && on_secondary) found=1; exit !found}
    ' "$campaign_evidence/api17-compositor-owner-death-window-state-$adb_port.txt"; then
      echo 'App-owned secondary Presentation window remained after parent-owner death.' >&2; exit 9;
    fi
    shasum -a 256 "$apk" "$campaign_evidence/api17-compositor-owner-death-logcat-$adb_port.txt" \
      "$campaign_evidence/api17-compositor-owner-death-processes-$adb_port.txt" \
      "$campaign_evidence/api17-compositor-owner-death-services-$adb_port.txt" \
      > "$campaign_evidence/api17-compositor-owner-death-artifact-hashes-$adb_port.sha256"
    echo "CL_R4B_PARENT_OWNER_DEATH_API17_PASS old_compositor_pid=$owner_pid new_compositor_pid=$new_owner_pid session_id=$session_id old_pid_absent=true owner_valid=false child_present=false stale_type110_frame=rejected stale_type111_frame=rejected registrations=0 pfd_transfers=0 retained_bytes=0 presentation=dismiss_requested evidence=$run_label/evidence"
    owned || exit 7
    adb_local -s "$serial" shell am force-stop "$package"
    adb_local -s "$serial" shell am force-stop "$attacker_package"
    adb_local -s "$serial" uninstall "$attacker_package" >/dev/null
    adb_local -s "$serial" uninstall "$package" >/dev/null
    adb_local -s "$serial" shell 'settings put global overlay_display_devices ""'
    exit 0
  fi
  if [ "$reentrant_teardown" -eq 1 ]; then
    wait_for 'CL_R4B_REENTRANT_PARENT_TEARDOWN_PASS'
    wait_for 'IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true active_pfd_transfers=0 retained_frame_bytes=0'
    logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
    printf '%s\n' "$logs" > "$campaign_evidence/api17-reentrant-teardown-logcat-$adb_port.txt"
    pass_line=$(printf '%s\n' "$logs" | grep -F 'CL_R4B_REENTRANT_PARENT_TEARDOWN_PASS ' | tail -1)
    if printf '%s\n' "$logs" | grep -F 'CL_R4_TYPE111_BUFFER_DECODE_BINDER_VIEW_FAIL' >/dev/null; then
      echo 'Fixture worker reported a failure during the reentrant teardown scenario.' >&2; exit 9;
    fi
    printf '%s\n' "$pass_line" | grep -F "session_id=$initial_session_generation " \
      | grep -F 'concurrent_calls=2 accepted_calls=1 rejected_calls=1' \
      | grep -F 'overlap_barrier=first_paused_contender_rejected' \
      | grep -F 'repeated_close_rejected=true' \
      | grep -F 'pending_pfd_rejected=true registration_during_shutdown_rejected=true' \
      | grep -F 'replacement_during_shutdown_rejected=true type110_died_during_shutdown=true' \
      | grep -F 'owner_valid=false child_present=false pfd_transfers=0 retained_bytes=0' >/dev/null || {
      printf '%s\n' "$pass_line" >&2
      printf '%s\n' "$logs" | grep -E 'PARENT_TEARDOWN_BARRIER|TYPE111_PARENT_TEARDOWN|CL_R4B_REENTRANT|IPC_REMOTE_PROCESS_DESTROYED' >&2 || true
      echo 'Concurrent/repeated teardown receipt did not match the initial session and zero-resource state.' >&2; exit 9;
    }
    printf '%s\n' "$logs" | grep -F "CL_R4B_TEARDOWN_PENDING_PFD_PASS session_id=$initial_session_generation " \
      | grep -F 'transfer_active=true' >/dev/null || {
      echo 'Teardown test did not hold a real pending Type111 PFD transfer.' >&2; exit 9;
    }
    printf '%s\n' "$logs" | grep -F "CL_R4B_TEARDOWN_PENDING_PFD_REJECTED session_id=$initial_session_generation " \
      | grep -F 'result=session_closing active_pfd=0 retained_bytes=0 transfer_active=false' >/dev/null || {
      echo 'Pending PFD transfer was not rejected and released while parent teardown admission was closed.' >&2; exit 9;
    }
    printf '%s\n' "$logs" | grep -F "CL_R4B_TEARDOWN_REPLACEMENT_REJECTED session_id=$initial_session_generation " \
      | grep -F 'replacement_unchanged=true' >/dev/null || {
      echo 'Type111 replacement was not rejected during parent teardown.' >&2; exit 9;
    }
    printf '%s\n' "$logs" | grep -F "CL_R4B_TEARDOWN_TYPE110_DEATH_PASS session_id=$initial_session_generation " \
      | grep -F 'binder_death_observed=true admission_already_closed=true' >/dev/null || {
      echo 'Actual Type110 sink process death was not observed during parent teardown.' >&2; exit 9;
    }
    printf '%s\n' "$logs" | grep -F "CL_R4B_TEARDOWN_REGISTRATION_REJECTED session_id=$initial_session_generation " \
      | grep -F 'current_registration_preserved=true active_pfd=1' >/dev/null || {
      echo 'Type111 stream registration race was not rejected without changing the in-flight registration.' >&2; exit 9;
    }
    # The Activity's linked death recipient proves the process death. Depending on
    # ordering, CompositorService may already have unregistered the stream and
    # unlinked its recipient; exact-once unregister and zero-resource checks below
    # validate that teardown won safely in that interleaving.
    printf '%s\n' "$logs" | grep -F 'IPC_LAB_TRANSFER_BARRIER_ENTERED ' \
      | grep -F "session_id=$initial_session_generation " | grep -F 'active_pfd=1' >/dev/null || {
      echo 'No actual in-flight PFD entered the transfer barrier.' >&2; exit 9;
    }
    printf '%s\n' "$logs" | grep -F "IPC_REMOTE_FRAME_REJECT " \
      | grep -F 'reason=session_closing' | grep -F 'active_pfd_transfers=0' >/dev/null || {
      echo 'Compositor did not reject the pending frame after teardown admission closed.' >&2; exit 9;
    }
    teardown_count=$(printf '%s\n' "$logs" | grep -F "TYPE111_PARENT_TEARDOWN session_id=$initial_session_generation " \
      | grep -F 'result=accepted' | wc -l | tr -d ' ')
    [ "$teardown_count" -eq 1 ] || { echo "Expected one parent teardown commit; observed $teardown_count." >&2; exit 9; }
    for stream_type in 110 111; do
      unregister_count=$(printf '%s\n' "$logs" | grep -F "IPC_STREAM_UNREGISTERED session_id=$initial_session_generation " \
        | grep -F "stream_type=$stream_type " | wc -l | tr -d ' ')
      [ "$unregister_count" -eq 1 ] || { echo "Stream $stream_type unregister count was $unregister_count." >&2; exit 9; }
      printf '%s\n' "$logs" | grep -F 'IPC_REMOTE_FRAME ' | grep -F "session_id=$initial_session_generation " \
        | grep -F "stream_type=$stream_type " | grep -F 'accepted=true' >/dev/null || {
        echo "No valid pre-teardown frame for stream $stream_type." >&2; exit 9;
      }
    done
    printf '%s\n' "$logs" | grep -F 'IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true active_pfd_transfers=0 retained_frame_bytes=0' >/dev/null || {
      echo 'Compositor owner did not report zero-resource shutdown after reentrant teardown.' >&2; exit 9;
    }
    shasum -a 256 "$apk" "$campaign_evidence/api17-reentrant-teardown-logcat-$adb_port.txt" \
      > "$campaign_evidence/api17-reentrant-teardown-artifact-hashes-$adb_port.sha256"
    owned || exit 7
    adb_local -s "$serial" shell am force-stop "$package"
    adb_local -s "$serial" shell am force-stop "$attacker_package"
    adb_local -s "$serial" uninstall "$attacker_package" >/dev/null
    adb_local -s "$serial" uninstall "$package" >/dev/null
    adb_local -s "$serial" shell 'settings put global overlay_display_devices ""'
    echo "CL_R4B_REENTRANT_TEARDOWN_API17_PASS session_id=$initial_session_generation concurrent_calls=2 accepted_calls=1 repeat_close_inert=true streams_unregistered=2 active_pfd_transfers=0 retained_bytes=0 fixture_only=true evidence=$run_label/evidence"
    exit 0
  fi
  wait_for 'CL_R4_TYPE111_SINK_PROCESS_EXIT_REQUESTED'
  if [ "$delayed_death_callback" -eq 1 ]; then
    wait_for "IPC_LAB_DELAYED_DEATH_CALLBACK_ENTERED session_id=$initial_session_generation "
    logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
    printf '%s\n' "$logs" > "$campaign_evidence/api17-delayed-callback-before-replacement-$adb_port.txt"
    entered_line=$(printf '%s\n' "$logs" | grep -nF "IPC_LAB_DELAYED_DEATH_CALLBACK_ENTERED session_id=$initial_session_generation " | tail -1 | cut -d: -f1)
    [ -n "$entered_line" ] || { echo 'Delayed callback entry receipt disappeared before replacement.' >&2; exit 9; }
    post_entry_detach=$(printf '%s\n' "$logs" | awk -v entered="$entered_line" -v session="$initial_session_generation" '
      NR > entered && index($0, "IPC_TYPE111_SINK_DETACHED session_id=" session " ") {print; found=1}
      END {if (!found) exit 1}
    ' || true)
    [ -z "$post_entry_detach" ] || {
      echo 'Delayed callback detached the old sink after entering its pre-mutation barrier but before replacement.' >&2
      printf '%s\n' "$post_entry_detach" >&2
      exit 9;
    }
    start_lab_activity_privileged type111_delayed_callback_replacement "$initial_session_generation"
    wait_for "IPC_LAB_DELAYED_DEATH_CALLBACK_RELEASED session_id=$initial_session_generation "
  else
    wait_for 'IPC_VIEW_SINK_DEATH_CALLBACK session_id='
  fi
  logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
  app_pid=$initial_type111_pid
  [ -n "$app_pid" ] || { echo 'Type111 process identity was not captured.' >&2; exit 9; }
  death_line=$(printf '%s\n' "$logs" | grep -F 'CL_R4_TYPE111_SINK_PROCESS_EXIT_REQUESTED ' | grep -F "pid=$app_pid " | tail -1)
  printf '%s\n' "$death_line" | grep -F "session_id=$initial_session_generation " >/dev/null || {
    echo 'The Type111 sink process exit was not the identified Activity process.' >&2; exit 9;
  }
  session_id=$(printf '%s\n' "$death_line" | sed -n 's/.*session_id=\([0-9][0-9]*\).*/\1/p')
  type110_generation=$(printf '%s\n' "$death_line" | sed -n 's/.*type110_generation=\([0-9][0-9]*\).*/\1/p')
  type110_last_frame=$(printf '%s\n' "$death_line" | sed -n 's/.*type110_last_frame_id=\([0-9][0-9]*\).*/\1/p')
  type110_sink_pid=$(printf '%s\n' "$death_line" | sed -n 's/.*type110_sink_pid=\([0-9][0-9]*\).*/\1/p')
  compositor_pid=$initial_compositor_pid
  [ "$session_id" = "$initial_session_generation" ] || {
    echo 'Pre-death session identity did not match the initial setup receipt generation.' >&2; exit 9;
  }
  [ -n "$session_id" ] && [ -n "$type110_generation" ] && [ -n "$type110_last_frame" ] &&
    [ -n "$type110_sink_pid" ] && [ -n "$compositor_pid" ] || {
    echo "Missing process or stream identity from the pre-death receipt: session=$([ -n "$session_id" ] && echo yes || echo no) type110_generation=$([ -n "$type110_generation" ] && echo yes || echo no) last_frame=$([ -n "$type110_last_frame" ] && echo yes || echo no) type110_sink=$([ -n "$type110_sink_pid" ] && echo yes || echo no) compositor=$([ -n "$compositor_pid" ] && echo yes || echo no)." >&2
    exit 9;
  }
  [ "$type110_sink_pid" = "$initial_type110_sink_pid" ] || {
    echo 'Type110 sink PID changed between initial session receipt and owner-death precondition.' >&2; exit 9;
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
  if [ "$delayed_death_callback" -eq 1 ]; then
    printf '%s\n' "$logs" | grep -F "CL_R4B_DELAYED_CALLBACK_NEGATIVE_IDENTITY_PASS wrong_session=true wrong_generation=true replacement_unchanged=true" >/dev/null || {
      echo 'Delayed callback wrong-identity releases were not rejected without changing the replacement.' >&2; exit 9;
    }
    printf '%s\n' "$logs" | grep -F "IPC_LAB_DELAYED_DEATH_CALLBACK_RELEASED session_id=$session_id " \
      | grep -F 'entered_before_replacement=true completed_after_replacement=true current_sink_preserved=true' >/dev/null || {
      printf '%s\n' "$logs" | grep -F 'IPC_LAB_DELAYED_DEATH_CALLBACK_' >&2 || true
      echo 'Paused old Binder callback did not complete after replacement while preserving the current sink.' >&2; exit 9;
    }
  else
    printf '%s\n' "$logs" | grep -F "IPC_VIEW_SINK_DEATH_CALLBACK session_id=$session_id stream_type=111" >/dev/null || {
      echo 'Compositor did not observe Type111 Binder sink death.' >&2; exit 9;
    }
  fi
  if printf '%s\n' "$logs" | grep -F "IPC_VIEW_SINK_DEATH_CALLBACK session_id=$session_id stream_type=110" >/dev/null; then
    echo 'Type110 sink died when only the Type111 View process died.' >&2; exit 9;
  fi
  process_state=$(printf '%s\n' "$ps_snapshot" | awk -v pid="$app_pid" '$2 == pid {print}')
  [ -z "$process_state" ] || { echo "Type111 sink process still exists: $process_state" >&2; exit 9; }
  if [ "$delayed_death_callback" -eq 1 ]; then
    replacement_activity_pid=$(printf '%s\n' "$logs" | sed -n \
      's/.*ACTIVITY_READY .*pid=\([0-9][0-9]*\).*/\1/p' | tail -1)
    [ -n "$replacement_activity_pid" ] && [ "$replacement_activity_pid" != "$app_pid" ] || {
      echo 'Delayed callback replacement did not start a fresh View Activity process.' >&2; exit 9;
    }
  else
    window_state=$(adb_local -s "$serial" shell dumpsys window windows | tr -d '\r' | grep -F "mOwnerUid=$app_uid" || true)
    [ -z "$window_state" ] || { echo "ClarityLink window remains after Type111 sink death: $window_state" >&2; exit 9; }
  fi
  echo "TYPE111_SINK_DEATH_VERIFIED pid=$app_pid type110_sink_pid=$type110_sink_pid compositor_pid=$compositor_pid type110_death_callback=false"
  if [ "$type111_reattach" -eq 1 ]; then
    if [ "$delayed_death_callback" -eq 0 ]; then
      start_lab_activity_privileged type111_reattach "$session_id"
    fi
    if [ "$delayed_death_callback" -eq 1 ]; then
      wait_for "CL_R4B_DELAYED_SINK_CALLBACK_PASS session_id=$session_id "
      wait_for "IPC_LAB_DELAYED_DEATH_CALLBACK_RELEASED session_id=$session_id "
    fi
    for attempt in $(seq 1 180); do
      owned || { echo 'Owned emulator changed while waiting for Type111 reattachment.' >&2; exit 7; }
      logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
      printf '%s\n' "$logs" | grep -F 'CL_R4A_TYPE111_SINK_REPLACED ' | grep -F "session_id=$session_id " >/dev/null && break
      sleep 1
    done
    logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
    replacement_line=$(printf '%s\n' "$logs" | grep -F 'CL_R4A_TYPE111_SINK_REPLACED ' | tail -1)
    printf '%s\n' "$replacement_line" | grep -F "session_id=$session_id " | grep -F "type110_generation=$type110_generation" | grep -F 'stale_frame_rejected=true' >/dev/null || {
      echo 'API17 Binder reattachment did not preserve Type110 identity or reject a stale Type111 frame.' >&2; exit 9;
    }
    replacement_pid=$(printf '%s\n' "$logs" | sed -n 's/.*ACTIVITY_READY .*pid=\([0-9][0-9]*\).*/\1/p' | tail -1)
    [ -n "$replacement_pid" ] && [ "$replacement_pid" != "$app_pid" ] || {
      echo 'Restarted Type111 View process did not receive a fresh PID.' >&2; exit 9;
    }
    wait_for 'CL_R4A_VIEW_REATTACH_PASS'
    if [ "$delayed_death_callback" -eq 1 ]; then
      wait_for 'CL_R4B_DELAYED_CALLBACK_POST_TEARDOWN_PASS stale_release_rejected=true session_not_resurrected=true'
    fi
    logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
    printf '%s\n' "$logs" > "$campaign_evidence/api17-type111-reattach-logcat-$adb_port.txt"
    printf '%s\n' "$logs" | grep -F "CL_R4A_VIEW_REATTACH_PASS session_id=$session_id " | grep -F "type110_generation=$type110_generation" | grep -F 'parent_teardown=accepted' >/dev/null || {
      echo 'Reattached Activity receipt did not match the expected owner-authorized teardown.' >&2
      printf '%s\n' "$logs" | grep -F 'CL_R4A_VIEW_REATTACH_PASS ' >&2 || true
      echo "expected_session_id=$session_id expected_type110_generation=$type110_generation" >&2
      exit 9;
    }
    wait_for 'TYPE110_LAB_SINK_DESTROYED '
    wait_for 'IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true active_pfd_transfers=0 retained_frame_bytes=0'
    proof_path="$campaign_evidence/api17-type111-reattached-frame-$adb_port.png"
    proof_tmp="$proof_path.tmp"
    owned || exit 7
    adb_local -s "$serial" shell run-as "$package" cat files/type111-reattached-frame.png > "$proof_tmp"
    python3 "$repo/tools/normalize_api17_png.py" "$proof_tmp"
    mv "$proof_tmp" "$proof_path"
    shasum -a 256 "$proof_path" "$campaign_evidence/api17-type111-reattach-logcat-$adb_port.txt" \
      > "$campaign_evidence/api17-type111-reattach-artifact-hashes-$adb_port.sha256"
  else
    invoke_type110_probe_privileged "$session_id" "$type110_generation" "$type110_last_frame" "$type110_sink_pid" "$compositor_pid"
  fi
  if [ "$type111_reattach" -eq 0 ]; then
    complete_probe_session_and_stop_isolated_package
  fi
  logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
  printf '%s\n' "$logs" > "$campaign_evidence/api17-type111-logcat-$adb_port.txt"
  if [ "$type111_reattach" -eq 0 ]; then
    assert_type110_progress_precedes_parent_teardown "$session_id" "$type110_last_frame" "$type110_sink_pid" "$logs"
    printf '%s\n' "$logs" | grep -F "CL_R4_TYPE110_AFTER_TYPE111_SINK_DEATH_PASS session_id=$session_id stream_generation=$type110_generation old_last_frame_id=$type110_last_frame" >/dev/null || {
      echo 'Type110 did not report post-death progress on the original stream identity.' >&2; exit 9;
    }
    printf '%s\n' "$logs" | grep -F "TYPE110_LAB_SINK_FRAME_ACCEPTED pid=$type110_sink_pid" | grep -E "frame_id=$((type110_last_frame + 1))([[:space:]]|$)" >/dev/null || {
      echo 'The independent Type110 sink did not record the next frame after Type111 sink death.' >&2; exit 9;
    }
  else
    progress_line=$(printf '%s\n' "$logs" | grep -F "CL_R4A_VIEW_REATTACH_PASS session_id=$session_id " | tail -1)
    progress_frame=$(printf '%s\n' "$progress_line" | sed -n 's/.*type110_last_frame_id=\([0-9][0-9]*\).*/\1/p')
    [ -n "$progress_frame" ] && [ "$progress_frame" -gt "$type110_last_frame" ] || {
      echo 'Type110 did not accept a later frame on the unchanged generation after View death.' >&2; exit 9;
    }
    printf '%s\n' "$logs" | grep -F 'IPC_REMOTE_FRAME ' | grep -F "session_id=$session_id " | grep -F 'stream_type=110' | grep -F 'accepted=true' >/dev/null || {
      echo 'No post-death Type110 frame was accepted over Binder.' >&2; exit 9;
    }
  fi
  printf '%s\n' "$logs" | grep -F "TYPE111_PARENT_TEARDOWN session_id=$session_id streams_closed=2 result=accepted" >/dev/null || {
    echo 'Parent teardown did not close the remaining Type110 child stream.' >&2; exit 9;
  }
  for stream_type in 110 111; do
    if [ "$type111_reattach" -eq 1 ] && [ "$stream_type" -eq 111 ]; then
      printf '%s\n' "$logs" | grep -F "IPC_TYPE111_SINK_REPLACED session_id=$session_id " >/dev/null || {
        echo 'Missing actual Binder Type111 sink replacement receipt.' >&2; exit 9;
      }
    elif [ "$type111_reattach" -eq 1 ] && [ "$stream_type" -eq 110 ]; then
      printf '%s\n' "$logs" | grep -F "IPC_SESSION_STARTED generation=$session_id " | grep -F 'streams=110:primary_lab,111:secondary_view' >/dev/null || {
        echo 'Missing actual Binder receipt for the existing Type110 stream.' >&2; exit 9;
      }
    else
      printf '%s\n' "$logs" | grep -F "IPC_STREAM_REGISTERED session_id=" | grep -F "stream_type=$stream_type" >/dev/null || {
        echo "Missing actual Binder registration for stream type $stream_type." >&2; exit 9;
      }
    fi
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
  if [ "$type111_reattach" -eq 0 ]; then
    window_state=$(adb_local -s "$serial" shell dumpsys window windows | tr -d '\r' | grep -F "mOwnerUid=$app_uid" || true)
    [ -z "$window_state" ] || { echo "ClarityLink window remains after consumer death: $window_state" >&2; exit 9; }
    echo "TYPE111_CONSUMER_DEATH_VERIFIED pid=$app_pid process_absent=true app_window_absent=true"
  else
    echo "TYPE111_CONSUMER_DEATH_VERIFIED pid=$app_pid process_absent=true replacement_pid=$replacement_pid parent_session_reused=true"
  fi
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
    "$campaign_evidence/api17-initial-setup-order-$adb_port.txt" \
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
