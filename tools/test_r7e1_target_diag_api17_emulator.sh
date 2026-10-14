#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sdk_root=${R7C2_SDK_ROOT:-"$HOME/Android/r7c2-sdk"}
avd_root="$repo/build/r7e1/avd"
binary="$repo/build/r7e1/native-x86/claritylink-target-diag"
apk="$repo/build/r7e1/display-apk/claritylink-r7e1-display-diagnostic.apk"
adb="$sdk_root/platform-tools/adb"
emulator="$sdk_root/.emulator-intel/emulator/emulator"
avdmanager="$sdk_root/cmdline-tools/latest/bin/avdmanager"
java_home="$HOME/.local/toolchains/temurin-17.0.20.1+1-aarch64/jdk-17.0.20.1+1/Contents/Home"
remote=/data/local/tmp/claritylink-target-diag
[ -x "$binary" ] || { echo 'Build the API17 x86 runtime-test diagnostic first.' >&2; exit 2; }
[ -f "$apk" ] || { echo 'Build the separate offline API17 display diagnostic APK first.' >&2; exit 2; }
[ -x "$adb" ] && [ -x "$emulator" ] && [ -x "$avdmanager" ] || { echo 'Missing isolated API17 SDK runtime tools.' >&2; exit 2; }
[ -x "$java_home/bin/java" ] || { echo 'Pinned local Java 17 runtime is unavailable.' >&2; exit 2; }
mkdir -p "$avd_root" "$repo/build/r7e1"
export ANDROID_HOME="$sdk_root" ANDROID_SDK_ROOT="$sdk_root" ANDROID_AVD_HOME="$avd_root"
export JAVA_HOME="$java_home" PATH="$java_home/bin:$PATH"

inventory=$("$adb" devices | awk 'NR>1 && $1!="" {print $1" "$2}')
[ -z "$inventory" ] || { echo "Refusing emulator test; pre-existing ADB target: $inventory" >&2; exit 3; }

port=$(python3 - <<'PY'
import socket
for candidate in range(5580, 5681, 2):
    opened=[]
    try:
        for port in (candidate, candidate+1):
            sock=socket.socket()
            sock.bind(("127.0.0.1", port))
            opened.append(sock)
        print(candidate)
        break
    except OSError:
        pass
    finally:
        for sock in opened: sock.close()
else:
    raise SystemExit("No free isolated emulator port pair")
PY
)
serial="emulator-$port"
nonce="$$-$(date +%s)"
avd="r7e1_api17_$nonce"
avd_dir="$avd_root/$avd.avd"
avd_ini="$avd_root/$avd.ini"
emulator_pid=
created=0
remote_exists=0

assert_owned() {
  [ -n "$emulator_pid" ] && kill -0 "$emulator_pid" 2>/dev/null || { echo 'Owned emulator process is absent.' >&2; return 1; }
  devices=$("$adb" devices | awk 'NR>1 && $1!="" {print $1" "$2}')
  [ "$devices" = "$serial device" ] || { echo "Refusing ADB action; target inventory changed: $devices" >&2; return 1; }
}
cleanup() {
  status=$?
  trap - EXIT INT TERM
  if [ "$remote_exists" -eq 1 ] && [ -n "$emulator_pid" ] && kill -0 "$emulator_pid" 2>/dev/null; then
    if assert_owned >/dev/null 2>&1; then "$adb" -s "$serial" shell rm -f "$remote" >/dev/null 2>&1 || true; fi
  fi
  if [ -n "$emulator_pid" ] && kill -0 "$emulator_pid" 2>/dev/null; then
    kill "$emulator_pid" 2>/dev/null || true
    wait "$emulator_pid" 2>/dev/null || true
  fi
  if [ "$created" -eq 1 ]; then
    python3 - "$avd_dir" "$avd_ini" <<'PY'
from pathlib import Path
import shutil, sys
avd, ini = map(Path, sys.argv[1:])
if avd.exists(): shutil.rmtree(avd)
if ini.exists(): ini.unlink()
PY
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf 'no\n' | "$avdmanager" create avd --name "$avd" --package 'system-images;android-17;default;x86' --force >/dev/null
created=1
[ -f "$avd_dir/config.ini" ] && [ -f "$avd_ini" ] || { echo 'Isolated AVD was not created.' >&2; exit 4; }
grep -q '^abi.type=x86$' "$avd_dir/config.ini" || { echo 'Isolated AVD ABI is not x86.' >&2; exit 4; }
arch -x86_64 "$emulator" -avd "$avd" -port "$port" -no-window -no-audio -no-boot-anim -no-snapshot -wipe-data -accel off -gpu swiftshader_indirect \
  > "$repo/build/r7e1/emulator.log" 2>&1 &
emulator_pid=$!

ready=0
attempt=0
while [ "$attempt" -lt 120 ]; do
  if ! kill -0 "$emulator_pid" 2>/dev/null; then echo 'Owned emulator exited during boot.' >&2; exit 5; fi
  devices=$("$adb" devices | awk 'NR>1 && $1!="" {print $1" "$2}')
  if [ -n "$devices" ]; then
    case "$devices" in "$serial offline"|"$serial device") : ;; *) echo "Unexpected ADB target during boot: $devices" >&2; exit 5 ;; esac
    state=$(printf '%s\n' "$devices" | awk '{print $2}')
    if [ "$state" = device ]; then
      api=$("$adb" -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')
      boot=$("$adb" -s "$serial" shell getprop sys.boot_completed | tr -d '\r')
      if [ "$api" = 17 ] && [ "$boot" = 1 ]; then ready=1; break; fi
    fi
  fi
  attempt=$((attempt+1)); sleep 1
done
[ "$ready" -eq 1 ] || { echo 'Owned API17 emulator boot timeout.' >&2; exit 6; }
assert_owned
qemu=$("$adb" -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')
release=$("$adb" -s "$serial" shell getprop ro.build.version.release | tr -d '\r')
abi=$("$adb" -s "$serial" shell getprop ro.product.cpu.abi | tr -d '\r')
[ "$qemu" = 1 ] && [ "$release" = 4.2.2 ] && [ "$abi" = x86 ] || { echo "Guest identity mismatch: qemu=$qemu api=$api release=$release abi=$abi" >&2; exit 7; }

assert_owned
"$adb" -s "$serial" push "$binary" "$remote" >/dev/null
remote_exists=1
assert_owned
"$adb" -s "$serial" shell chmod 700 "$remote"
assert_owned
"$adb" -s "$serial" shell "$remote" --help | grep -q 'Usage:'
assert_owned
"$adb" -s "$serial" shell "$remote" --version | grep -q 'ABI=armeabi-v7a'
assert_owned
"$adb" -s "$serial" shell "$remote" --status | grep -q 'PERSISTENCE=NONE LISTENERS=0 DISPLAY=NONE RECEIVER=NONE'
assert_owned
"$adb" -s "$serial" shell "$remote" --self-test | grep -q 'SELF_TEST_PASS'
for mode in --carplay --type110 --type111 --display --usb --iap2 --mfi --listen --daemon; do
  assert_owned
  output=$("$adb" -s "$serial" shell "$remote" "$mode" | tr -d '\r')
  [ "$output" = UNSUPPORTED_MODE ] || { echo "Forbidden mode did not fail closed: $mode output=$output" >&2; exit 8; }
done
cycle=1
while [ "$cycle" -le 100 ]; do
  assert_owned
  output=$("$adb" -s "$serial" shell "$remote" --self-test | tr -d '\r')
  printf '%s\n' "$output" | grep -q 'RESOURCE_COUNTS final=0'
  printf '%s\n' "$output" | grep -q 'SELF_TEST_PASS'
  cycle=$((cycle+1))
done
assert_owned
"$adb" -s "$serial" shell rm -f "$remote"
remote_exists=0
assert_owned
absent=$("$adb" -s "$serial" shell test ! -e "$remote" && echo absent)
[ "$absent" = absent ] || { echo 'Diagnostic remained in emulator temporary storage.' >&2; exit 9; }

package=org.claritylink.r7e1.displaydiag
component=org.claritylink.android.R7E1DisplayDiagnosticActivity
wait_for_log() {
  wanted=$1
  attempt=0
  while [ "$attempt" -lt 30 ]; do
    assert_owned
    logs=$("$adb" -s "$serial" logcat -d -s ClarityLinkR7E1:I '*:S' 2>/dev/null | tr -d '\r')
    if printf '%s\n' "$logs" | grep -F "$wanted" >/dev/null; then return 0; fi
    attempt=$((attempt+1)); sleep 1
  done
  echo "Expected diagnostic log not observed: $wanted" >&2
  printf '%s\n' "$logs" >&2
  "$adb" -s "$serial" logcat -d -t 120 -s AndroidRuntime:E ActivityManager:I ActivityTaskManager:I PackageManager:I '*:S' >&2 || true
  return 1
}
assert_owned
"$adb" -s "$serial" install "$apk" >/dev/null
assert_owned
"$adb" -s "$serial" logcat -c
"$adb" -s "$serial" shell am start -n "$package/$component" >/dev/null
wait_for_log 'STATUS_ONLY no_display_action=true'
logs=$("$adb" -s "$serial" logcat -d -s ClarityLinkR7E1:I '*:S' 2>/dev/null | tr -d '\r')
if printf '%s\n' "$logs" | grep -E 'DISPLAY_ENUMERATION|ADMISSION_STATE|FRAME_POSTED' >/dev/null; then
  echo 'Default APK launch performed a display action.' >&2; exit 10
fi
assert_owned
"$adb" -s "$serial" shell am force-stop "$package"
assert_owned
"$adb" -s "$serial" shell settings put global overlay_display_devices '800x480/160'
assert_owned
"$adb" -s "$serial" logcat -c
"$adb" -s "$serial" shell am start -n "$package/$component" --es mode DISPLAY_ENUMERATION >/dev/null
wait_for_log 'DISPLAY_ENUMERATION count='
assert_owned
"$adb" -s "$serial" shell am force-stop "$package"
assert_owned
"$adb" -s "$serial" logcat -c
"$adb" -s "$serial" shell am start -n "$package/$component" --es mode PRESENTATION_PREFLIGHT \
  --es offline_emulator_confirmation R7E1_OFFLINE_EMULATOR_ONLY >/dev/null
wait_for_log 'ADMISSION_STATE=PRESENTATION_SHOWN'
wait_for_log 'ADMISSION_STATE=SURFACE_CREATED'
logs=$("$adb" -s "$serial" logcat -d -s ClarityLinkR7E1:I '*:S' 2>/dev/null | tr -d '\r')
if printf '%s\n' "$logs" | grep 'FRAME_POSTED' >/dev/null; then echo 'Presentation preflight posted visible frame content.' >&2; exit 11; fi
assert_owned
"$adb" -s "$serial" shell am force-stop "$package"
assert_owned
"$adb" -s "$serial" logcat -c
"$adb" -s "$serial" shell am start -n "$package/$component" --es mode SINGLE_FRAME_DIAGNOSTIC \
  --es offline_emulator_confirmation R7E1_OFFLINE_EMULATOR_ONLY >/dev/null
wait_for_log 'ADMISSION_STATE=SURFACE_CREATED'
wait_for_log 'FRAME_POSTED count=1'
wait_for_log 'FRAME_CLEARED_AND_RELEASED'
assert_owned
"$adb" -s "$serial" shell am force-stop "$package"
assert_owned
"$adb" -s "$serial" shell settings delete global overlay_display_devices >/dev/null
echo "R7E1_API17_X86_RUNTIME_PASS cycles=100 api=$api release=$release abi=$abi"
echo 'R7E1_API17_DISPLAY_APK_PASS default=no-output enumeration=pass presentation=emulator-only single-frame=one-shot'
