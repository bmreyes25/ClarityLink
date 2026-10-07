#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sdk_root=${R7C2_SDK_ROOT:-"$HOME/Android/r7c2-sdk"}
avd_root="$repo/build/r7c2/avd"
avd="r7c2_api17_$$"
port=5580
serial="emulator-$port"
package=com.claritylink.r7c2.test
apk="$repo/build/r7c2/apk/claritylink-r7c2-test.apk"
adb="$sdk_root/platform-tools/adb"
emulator="$sdk_root/.emulator-intel/emulator/emulator"
avdmanager="$sdk_root/cmdline-tools/latest/bin/avdmanager"
export ANDROID_HOME="$sdk_root" ANDROID_SDK_ROOT="$sdk_root" ANDROID_AVD_HOME="$avd_root"
mkdir -p "$avd_root"
for tool in "$adb" "$emulator" "$avdmanager"; do [ -x "$tool" ] || { echo "Missing SDK tool: $tool" >&2; exit 2; }; done
[ -f "$apk" ] || { echo 'Build the isolated R7C2 APK first.' >&2; exit 2; }

# Refuse to start if any existing ADB target could make a command ambiguous.
existing=$("$adb" devices | awk 'NR>1 && $1!="" {print $1}')
[ -z "$existing" ] || { echo "Refusing: pre-existing ADB target(s): $existing" >&2; exit 3; }

emulator_pid=
cleanup() {
  if [ -n "$emulator_pid" ]; then
    "$adb" -s "$serial" shell settings put global overlay_display_devices '' >/dev/null 2>&1 || true
    kill "$emulator_pid" 2>/dev/null || true
    wait "$emulator_pid" 2>/dev/null || true
    emulator_pid=
  fi
  if [ -d "$avd_root/$avd.avd" ]; then
    "$avdmanager" delete avd --name "$avd" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

"$avdmanager" create avd --name "$avd" --package 'system-images;android-17;default;x86' --device 'Nexus S' --force >/dev/null
arch -x86_64 "$emulator" -avd "$avd" -port "$port" -no-window -no-audio -no-snapshot -no-boot-anim \
  -wipe-data -accel off -gpu swiftshader_indirect >"$repo/build/r7c2/emulator.log" 2>&1 &
emulator_pid=$!

assert_owned_target() {
  devices=$("$adb" devices | awk 'NR>1 && $1!="" {print $1" "$2}')
  count=$(printf '%s\n' "$devices" | awk 'NF {n++} END {print n+0}')
  [ "$count" -eq 1 ] || { echo "Refusing: expected exactly one ADB target, found: $devices" >&2; return 1; }
  printf '%s\n' "$devices" | awk -v expected="$serial" '$1==expected && $2=="device" {ok=1} END {exit !ok}' || {
    echo "Refusing: sole ADB target is not the owned emulator $serial: $devices" >&2; return 1;
  }
}
assert_no_foreign_target() {
  devices=$("$adb" devices | awk 'NR>1 && $1!="" {print $1" "$2}')
  foreign=$(printf '%s\n' "$devices" | awk -v expected="$serial" 'NF && $1!=expected {print $1" "$2}')
  [ -z "$foreign" ] || { echo "Refusing: foreign or ambiguous ADB target appeared: $foreign" >&2; return 1; }
  [ -z "$devices" ] || printf '%s\n' "$devices" | awk -v expected="$serial" '$1==expected {ok=1} END {exit !ok}' || {
    echo "Refusing: unexpected ADB state: $devices" >&2; return 1;
  }
}

ready=0
for attempt in $(seq 1 180); do
  if ! kill -0 "$emulator_pid" 2>/dev/null; then
    tail -60 "$repo/build/r7c2/emulator.log" >&2
    echo 'Emulator process exited before boot.' >&2; exit 7
  fi
  assert_no_foreign_target || exit 4
  devices=$("$adb" devices | awk 'NR>1 && $1!="" {print $1" "$2}')
  [ -n "$devices" ] || { sleep 1; continue; }
  state=$(printf '%s\n' "$devices" | awk -v expected="$serial" '$1==expected {print $2}')
  [ "$state" = device ] || { sleep 1; continue; }
  assert_owned_target || exit 4
  boot=$("$adb" -s "$serial" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')
  if [ "$boot" = 1 ]; then ready=1; break; fi
  sleep 1
done
[ "$ready" -eq 1 ] || { echo 'API17 emulator boot timeout' >&2; exit 5; }
assert_owned_target
"$adb" -s "$serial" shell settings put global overlay_display_devices '800x480/160'
"$adb" -s "$serial" logcat -c
"$adb" -s "$serial" install "$apk"
assert_owned_target
"$adb" -s "$serial" shell am start -n "$package/org.claritylink.android.R7C2RuntimeActivity" >/dev/null

result=''
for attempt in $(seq 1 300); do
  assert_owned_target
  result=$("$adb" -s "$serial" logcat -d -s ClarityLinkR7C2:I '*:S' 2>/dev/null | tr -d '\r' | awk '/RESULT=PASS|RESULT=FAIL/ {line=$0} END {print line}')
  case "$result" in *'RESULT=PASS'*|*'RESULT=FAIL'*) break;; esac
  sleep 1
done
"$adb" -s "$serial" logcat -d -s ClarityLinkR7C2:I '*:S' > "$repo/build/r7c2/runtime-logcat.txt"
printf '%s\n' "$result"
case "$result" in *'RESULT=PASS'*) exit 0;; *) echo 'Android runtime harness failed or timed out.' >&2; exit 6;; esac
