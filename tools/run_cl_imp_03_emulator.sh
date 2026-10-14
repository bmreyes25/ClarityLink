#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sdk=${CL_IMP_03_SDK_ROOT:-"$HOME/Android/r7c2-sdk"}
out="$repo/build/cl-imp-03"
adb="$sdk/platform-tools/adb"
emulator="$sdk/.emulator-intel/emulator/emulator"
avdmanager="$sdk/cmdline-tools/latest/bin/avdmanager"
apk="$out/claritylink-display-lab.apk"
package=org.claritylink.independentdisplay.lab
component=org.claritylink.android.ClarityLinkDisplayActivity
decoder_only=0
if [ "${1:-}" = "--cl-imp-08-decoder" ]; then
  decoder_only=1
  component=org.claritylink.android.Api17DecoderLabActivity
  shift
fi
[ "$#" -eq 0 ] || { echo 'Unexpected emulator harness arguments.' >&2; exit 2; }
[ -f "$apk" ] && [ -x "$adb" ] && [ -x "$emulator" ] && [ -x "$avdmanager" ] || {
  echo 'Build CL-IMP-03 APKs and provide the isolated API17 emulator tools first.' >&2; exit 2;
}
mkdir -p "$out/avd"
export ANDROID_HOME="$sdk" ANDROID_SDK_ROOT="$sdk" ANDROID_AVD_HOME="$out/avd"
adb_port=$(python3 - <<'PY'
import socket
s=socket.socket();s.bind(('127.0.0.1',0));print(s.getsockname()[1]);s.close()
PY
)
export ADB_SERVER_PORT="$adb_port" ANDROID_ADB_SERVER_PORT="$adb_port"
adb_local() { "$adb" -P "$adb_port" "$@"; }
serial= emulator_pid= avd_created=0
avd="climp03_api17_$$"
avd_dir="$out/avd/$avd.avd"
avd_ini="$out/avd/$avd.ini"
cleanup() {
  result=$?
  trap - EXIT INT TERM
  if [ -n "$emulator_pid" ] && kill -0 "$emulator_pid" 2>/dev/null; then
    kill "$emulator_pid" 2>/dev/null || true
    wait "$emulator_pid" 2>/dev/null || true
  fi
  adb_local kill-server >/dev/null 2>&1 || true
  if [ "$avd_created" -eq 1 ]; then
    python3 - "$avd_dir" "$avd_ini" <<'PY'
from pathlib import Path
import shutil,sys
avd,ini=map(Path,sys.argv[1:])
if avd.exists(): shutil.rmtree(avd)
if ini.exists(): ini.unlink()
PY
  fi
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

adb_local --one-device CL_IMP_03_NO_PHYSICAL_USB start-server >/dev/null
inventory() { adb_local devices | awk 'NR>1 && NF {print $1" "$2}'; }
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
owned() {
  [ -n "$emulator_pid" ] && kill -0 "$emulator_pid" 2>/dev/null &&
    [ "$(inventory)" = "$serial device" ]
}
printf 'no\n' | "$avdmanager" create avd --name "$avd" \
  --package 'system-images;android-17;default;x86' --force >/dev/null
avd_created=1
grep -q '^abi.type=x86$' "$avd_dir/config.ini" || { echo 'AVD ABI mismatch.' >&2; exit 4; }
arch -x86_64 "$emulator" -avd "$avd" -port "$port" -no-window -no-audio \
  -no-snapshot -no-boot-anim -wipe-data -accel off -gpu swiftshader_indirect \
  > "$out/emulator.log" 2>&1 &
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
installed=$(adb_local -s "$serial" shell pm path "$package" | tr -d '\r')
case "$installed" in package:*) :;; *) echo 'Lab APK installation not visible.' >&2; exit 8;; esac
app_uid=$(adb_local -s "$serial" shell dumpsys package "$package" | sed -n 's/.*userId=\([0-9][0-9]*\).*/\1/p' | head -1 | tr -d '\r')
[ -n "$app_uid" ] || { echo 'Could not identify installed lab app UID.' >&2; exit 8; }
adb_local -s "$serial" logcat -c
owned || exit 7
adb_local -s "$serial" shell am start -n "$package/$component" \
  --es mode EMULATOR_PRESENTATION --es emulator_only_confirmation CL_IMP_03_OFFLINE_EMULATOR_ONLY >/dev/null
wait_for() {
  marker=$1
  for attempt in $(seq 1 60); do
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
  wait_for 'CLIMP08_API17_MEDIACODEC_PASS'
  logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
  printf '%s\n' "$logs" | grep -F 'resolutionReset=64x64 independentStreams=true surfaceSubmissionOnly=true physicalScanout=UNPROVEN' >/dev/null || {
    echo 'Decoder result did not report bounded API17 Surface submission and explicit scanout limitation.' >&2
    printf '%s\n' "$logs" >&2
    exit 9
  }
  owned || exit 7
  adb_local -s "$serial" shell am force-stop "$package"
  adb_local -s "$serial" uninstall "$package" >/dev/null
  adb_local -s "$serial" shell 'settings put global overlay_display_devices ""'
  echo 'CL_IMP_08_API17_MEDIACODEC_EMULATOR_PASS dual_stream=true resolution_reset=64x64 owned_surfaces=borrowed scanout=unproven install_scope=isolated_emulator'
  exit 0
fi
wait_for 'ADMISSION_STATE=PRESENTATION_SHOWN'
wait_for 'SURFACE_BORROWED_READY valid=true owner=Presentation_SurfaceHolder released_by_app=false'
wait_for 'SYNTHETIC_FRAME_DRAWN_ON_PRESENTATION_CANVAS'
wait_for 'IPC_SESSION_STARTED'
wait_for 'IPC_SYNTHETIC_FRAME_ACCEPTED'
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
wait_for 'ADMISSION_STATE=FAILED'
wait_for 'RENDERER_RELEASED'
wait_for 'IPC_REMOTE_END'
wait_for 'IPC_REMOTE_PROCESS_DESTROYED resources_cleared=true'
owned || exit 7
adb_local -s "$serial" shell am force-stop "$package"
owned || exit 7
adb_local -s "$serial" shell settings put global overlay_display_devices '800x480/160'
adb_local -s "$serial" logcat -c
owned || exit 7
adb_local -s "$serial" shell am start -n "$package/$component" \
  --es mode EMULATOR_PRESENTATION \
  --es emulator_only_confirmation CL_IMP_03_OFFLINE_EMULATOR_ONLY \
  --ez crash_after_first_frame true >/dev/null
wait_for 'SYNTHETIC_FRAME_DRAWN_ON_PRESENTATION_CANVAS'
wait_for 'IPC_SYNTHETIC_FRAME_ACCEPTED'
logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
crash_remote_pid=$(printf '%s\n' "$logs" | sed -n 's/.*IPC_SESSION_STARTED .*remote_pid=\([0-9][0-9]*\).*/\1/p' | head -1)
[ -n "$crash_remote_pid" ] || { echo 'Missing remote compositor PID in crash-recovery run.' >&2; exit 9; }
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
# Android 4.2.2 leaves a crashing app and its windows pending the system error
# dialog. Dismiss that state with force-stop, then verify exact app ownership is gone.
owned || exit 7
adb_local -s "$serial" shell am force-stop "$package"
crashed=0
for attempt in $(seq 1 30); do
  owned || exit 7
  ps=$(adb_local -s "$serial" shell ps | tr -d '\r')
  windows=$(adb_local -s "$serial" shell dumpsys window windows | tr -d '\r')
  crash_log=$(adb_local -s "$serial" logcat -d -s AndroidRuntime:E '*:S' | tr -d '\r')
  app_windows=$(printf '%s\n' "$windows" | grep -F "mOwnerUid=$app_uid" || true)
  compositor_process=$(printf '%s\n' "$ps" | awk -v pid="$crash_remote_pid" '$2==pid {print; found=1} END {if (!found) exit 1}' || true)
  if ! printf '%s\n' "$ps" | awk -v name="$package" '$NF==name {found=1} END {exit !found}' &&
     [ -z "$app_windows" ] && [ -z "$compositor_process" ]; then crashed=1; break; fi
  sleep 1
done
[ "$crashed" -eq 1 ] || {
  echo 'Crash recovery did not reclaim process and app-owned windows.' >&2
  printf '%s\n' "$ps" | grep -F "$package" >&2 || true
  printf '%s\n' "$compositor_process" >&2
  printf '%s\n' "$windows" | grep -F "mOwnerUid=$app_uid" >&2 || true
  printf '%s\n' "$crash_log" >&2
  exit 9
}
adb_local -s "$serial" logcat -c
owned || exit 7
adb_local -s "$serial" shell am start -n "$package/$component" >/dev/null
wait_for 'STATUS_ONLY feature_disabled=true recovered_state=discarded'
logs=$(adb_local -s "$serial" logcat -d -s ClarityLinkCLIMP03:I '*:S' | tr -d '\r')
if printf '%s\n' "$logs" | grep -E 'PRESENTATION_SHOWN|DISPLAY_ENUMERATION' >/dev/null; then
  echo 'Recovered activity automatically re-admitted a display.' >&2; exit 10
fi
owned || exit 7
adb_local -s "$serial" uninstall "$package" >/dev/null
remaining=$(adb_local -s "$serial" shell pm path "$package" | tr -d '\r')
[ -z "$remaining" ] || { echo 'Emulator app package remains after uninstall.' >&2; exit 11; }
adb_local -s "$serial" shell 'settings put global overlay_display_devices ""'
echo "CL_IMP_03_04_API17_EMULATOR_PASS api=$api release=$release install=pass admission=pass canvas_draw=pass separate_process_ipc=pass bounded_frame=pass crash_recovery=status_only uninstall=pass"
