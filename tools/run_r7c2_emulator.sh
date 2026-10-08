#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sdk_root=${R7C2_SDK_ROOT:-"$HOME/Android/r7c2-sdk"}
avd_root="$repo/build/r7c2/avd"
package=com.claritylink.r7c2.test
apk="$repo/build/r7c2/apk/claritylink-r7c2-test.apk"
adb="$sdk_root/platform-tools/adb"
emulator="$sdk_root/.emulator-intel/emulator/emulator"
avdmanager="$sdk_root/cmdline-tools/latest/bin/avdmanager"
smoke_only=0
[ "${1:-}" != "--smoke-only" ] || smoke_only=1
focused_case=
focused_repeats=1
if [ "${1:-}" = "--case" ]; then
  focused_case=${2:?case name required}
  case "$focused_case" in socket-read|socket-read-after-dismiss|primary-surface|activity-destroy) : ;; *) echo 'Unsupported focused case.' >&2; exit 2 ;; esac
  shift 2
  if [ "${1:-}" = "--repeat" ]; then focused_repeats=${2:?repeat count required}; shift 2; fi
fi
case "$focused_repeats" in ''|*[!0-9]*) echo 'Repeat count must be an integer.' >&2; exit 2;; esac
[ "$focused_repeats" -ge 1 ] && [ "$focused_repeats" -le 25 ] || { echo 'Repeat count must be between 1 and 25.' >&2; exit 2; }
[ "$focused_repeats" -eq 1 ] || [ "$focused_case" = activity-destroy ] || { echo 'Repeats are supported only for activity-destroy.' >&2; exit 2; }

export ANDROID_HOME="$sdk_root" ANDROID_SDK_ROOT="$sdk_root" ANDROID_AVD_HOME="$avd_root"
[ -x "$adb" ] && [ -x "$emulator" ] && [ -x "$avdmanager" ] || { echo 'Missing isolated SDK runtime tool.' >&2; exit 2; }
[ -f "$apk" ] || { echo 'Build the isolated R7C2 APK first.' >&2; exit 2; }
mkdir -p "$avd_root"

# Refuse every pre-existing ADB target. Inventory is the only ADB operation
# permitted before this run has launched and proven its emulator.
existing=$("$adb" devices | awk 'NR>1 && $1!="" {print $1" "$2}')
[ -z "$existing" ] || { echo "FOREIGN_OR_STALE_ADB_TARGET_PRESENT: $existing" >&2; exit 3; }

nonce="$$-$(date +%s)"
avd="r7c6_api17_$nonce"
avd_dir="$avd_root/$avd.avd"
avd_ini="$avd_root/$avd.ini"
avd_created=0
emulator_pid=
logcat_pid=
serial=
owned_ready=0

choose_port() {
  python3 - "$adb" <<'PY'
import socket, subprocess, sys
adb = sys.argv[1]
try:
    out = subprocess.check_output([adb, "devices"], text=True)
except Exception as exc:
    raise SystemExit("cannot inventory ADB before port selection: %s" % exc)
if any(line.split() for line in out.splitlines()[1:]):
    raise SystemExit("FOREIGN_OR_STALE_ADB_TARGET_PRESENT")
for port in range(5580, 5681, 2):
    sockets=[]
    try:
        for candidate in (port, port + 1):
            s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            s.bind(("127.0.0.1", candidate))
            sockets.append(s)
        print(port)
        break
    except OSError:
        pass
    finally:
        for s in sockets:
            s.close()
else:
    raise SystemExit("No free emulator console/ADB port pair in 5580-5681")
PY
}

device_inventory() {
  "$adb" devices | awk 'NR>1 && $1!="" {print $1" "$2}'
}

assert_owned_target() {
  if [ -z "$emulator_pid" ] || ! kill -0 "$emulator_pid" 2>/dev/null; then
    echo 'Owned emulator process is not alive.' >&2; return 1
  fi
  devices=$(device_inventory)
  count=$(printf '%s\n' "$devices" | awk 'NF {n++} END {print n+0}')
  [ "$count" -eq 1 ] || { echo "Refusing ADB operation; targets are: $devices" >&2; return 1; }
  printf '%s\n' "$devices" | awk -v expected="$serial" '$1==expected && $2=="device" {ok=1} END {exit !ok}' || {
    echo "Refusing ADB operation; sole target is not the owned serial $serial: $devices" >&2; return 1;
  }
}

cleanup() {
  status=$?
  trap - EXIT INT TERM
  if [ "$owned_ready" -eq 1 ] && assert_owned_target >/dev/null 2>&1; then
    "$adb" -s "$serial" shell settings put global overlay_display_devices '' >/dev/null 2>&1 || true
  fi
  if [ -n "$emulator_pid" ] && kill -0 "$emulator_pid" 2>/dev/null; then
    kill "$emulator_pid" 2>/dev/null || true
    wait "$emulator_pid" 2>/dev/null || true
  fi
  if [ -n "$logcat_pid" ] && kill -0 "$logcat_pid" 2>/dev/null; then
    kill "$logcat_pid" 2>/dev/null || true
    wait "$logcat_pid" 2>/dev/null || true
  fi
  if [ "$avd_created" -eq 1 ]; then
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

port=$(choose_port)
serial="emulator-$port"

# The API17 image itself is intact, but its optional per-image device catalog
# is absent. A generic AVD is therefore created without --device; this avoids
# the catalog lookup while retaining the pinned API17/x86 system image.
export JAVA_HOME=${JAVA_HOME:-"$HOME/.local/toolchains/temurin-17.0.20.1+1-aarch64/jdk-17.0.20.1+1/Contents/Home"}
export PATH="$JAVA_HOME/bin:$PATH"
printf 'no\n' | "$avdmanager" create avd --name "$avd" \
  --package 'system-images;android-17;default;x86' --force >/dev/null
avd_created=1
[ -f "$avd_dir/config.ini" ] && [ -f "$avd_ini" ] || { echo 'AVD manager did not create the unique generic AVD.' >&2; exit 4; }
grep -q '^abi.type=x86$' "$avd_dir/config.ini" || { echo 'Created AVD is not x86.' >&2; exit 4; }
grep -q '^image.sysdir.1=system-images/android-17/default/x86/' "$avd_dir/config.ini" || { echo 'AVD does not reference the pinned API17 x86 image.' >&2; exit 4; }

arch -x86_64 "$emulator" -avd "$avd" -port "$port" -no-window -no-audio \
  -no-snapshot -no-boot-anim -wipe-data -accel off -gpu swiftshader_indirect \
  >"$repo/build/r7c2/emulator-$port.log" 2>&1 &
emulator_pid=$!
printf 'R7C6_AVD_START avd=%s pid=%s port=%s serial=%s\n' "$avd" "$emulator_pid" "$port" "$serial"

ready=0
for attempt in $(seq 1 300); do
  kill -0 "$emulator_pid" 2>/dev/null || { tail -60 "$repo/build/r7c2/emulator-$port.log" >&2; echo 'Owned emulator process exited before boot.' >&2; exit 5; }
  devices=$(device_inventory)
  count=$(printf '%s\n' "$devices" | awk 'NF {n++} END {print n+0}')
  if [ "$count" -gt 1 ]; then echo "Refusing; foreign/ambiguous ADB targets appeared: $devices" >&2; exit 6; fi
  state=$(printf '%s\n' "$devices" | awk -v expected="$serial" '$1==expected {print $2}')
  if [ "$state" = device ]; then
    assert_owned_target || exit 6
    boot=$("$adb" -s "$serial" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')
    if [ "$boot" = 1 ]; then ready=1; owned_ready=1; break; fi
  elif [ -n "$devices" ] && [ "$count" -eq 1 ]; then
    case "$devices" in "$serial"\ *) : ;; *) echo "Refusing; unexpected ADB target appeared: $devices" >&2; exit 6;; esac
  fi
  sleep 1
done
[ "$ready" -eq 1 ] || { echo 'Owned API17 emulator boot timeout.' >&2; exit 7; }

# Prove all target identity properties before installing or launching the APK.
assert_owned_target
qemu=$("$adb" -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')
api=$("$adb" -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')
release=$("$adb" -s "$serial" shell getprop ro.build.version.release | tr -d '\r')
abi=$("$adb" -s "$serial" shell getprop ro.product.cpu.abi | tr -d '\r')
avd_response=$("$adb" -s "$serial" emu avd name | tr -d '\r')
actual_avd=$(printf '%s\n' "$avd_response" | awk 'NF && $1!="OK" {print; exit}')
[ "$qemu" = 1 ] && [ "$api" = 17 ] && [ "$release" = 4.2.2 ] && [ "$abi" = x86 ] && [ "$actual_avd" = "$avd" ] || {
  echo "Guest identity mismatch: qemu=$qemu api=$api release=$release abi=$abi avd=$actual_avd expected=$avd" >&2; exit 8;
}
printf 'R7C6_AVD_IDENTITY api=%s release=%s abi=%s vm=verified-by-smoke-activity avd=%s pid=%s serial=%s\n' \
  "$api" "$release" "$abi" "$avd" "$emulator_pid" "$serial"

assert_owned_target
"$adb" -s "$serial" shell settings put global overlay_display_devices '800x480/160'
assert_owned_target
"$adb" -s "$serial" logcat -c
assert_owned_target
"$adb" -s "$serial" install "$apk"
assert_owned_target
"$adb" -s "$serial" shell am start -n "$package/org.claritylink.android.R7C6SmokeActivity" >/dev/null

smoke=''
for attempt in $(seq 1 30); do
  assert_owned_target
  smoke=$("$adb" -s "$serial" logcat -d -s ClarityLinkR7C6:I '*:S' 2>/dev/null | tr -d '\r' | awk '/R7C6_SMOKE_PASS/ {line=$0} END {print line}')
  [ -n "$smoke" ] && break
  sleep 1
done
case "$smoke" in *'R7C6_SMOKE_PASS'*'runtime=Dalvik'*) : ;; *) echo "API17 Dalvik smoke failed: $smoke" >&2; exit 9;; esac
case "$smoke" in *'api=17'*'release=4.2.2'*'abi=x86'*) : ;; *) echo "API17 Dalvik guest identity mismatch: $smoke" >&2; exit 9;; esac
echo 'R7C6_API17_OWNED_AVD_PASS'
echo "$smoke"
[ "$smoke_only" -eq 0 ] || exit 0

assert_owned_target
"$adb" -s "$serial" logcat -c
runtime_log="$repo/build/r7c2/runtime-$port-logcat.txt"
"$adb" -s "$serial" logcat -v time -s ClarityLinkR7C2:I ClarityLinkR7C7:I libc:E DEBUG:E AndroidRuntime:E ActivityManager:W ActivityManager:E '*:S' > "$runtime_log" 2>&1 &
logcat_pid=$!
assert_owned_target
if [ -n "$focused_case" ] && [ "$focused_repeats" -gt 1 ]; then
  repeat=1
  while [ "$repeat" -le "$focused_repeats" ]; do
    assert_owned_target
    if [ "$repeat" -eq 1 ]; then component=R7C7LifecycleGuardActivity; else component=R7C2RuntimeActivity; fi
    "$adb" -s "$serial" shell am start -n "$package/org.claritylink.android.$component" \
      --es r7c6Case "$focused_case" --ei r7c7Repeat "$repeat" >/dev/null
    case_result=''
    for attempt in $(seq 1 90); do
      assert_owned_target
      if tr -d '\r' < "$runtime_log" | grep -F "event=ACTIVITY_DESTROY_DUAL_STREAM_RACE=PASS repeat=$repeat" >/dev/null; then
        case_result=PASS; break
      fi
      if tr -d '\r' < "$runtime_log" | grep -F 'RESULT=FAIL' >/dev/null; then
        case_result=FAIL; break
      fi
      sleep 1
    done
    [ "$case_result" = PASS ] || { result="RESULT=FAIL ACTIVITY_DESTROY_REPEAT=$repeat"; break; }
    printf 'ACTIVITY_DESTROY_REPEAT=%s PASS\n' "$repeat"
    repeat=$((repeat + 1))
    if [ "$repeat" -le "$focused_repeats" ]; then
      guard_ready=0
      for attempt in $(seq 1 60); do
        assert_owned_target
        top=$("$adb" -s "$serial" shell dumpsys activity activities 2>/dev/null | tr -d '\r' | awk '/mResumedActivity/ {print; exit}')
        case "$top" in *R7C7LifecycleGuardActivity*) guard_ready=1; break;; esac
        sleep 1
      done
      [ "$guard_ready" -eq 1 ] || { result="RESULT=FAIL GUARD_NOT_RESUMED_AFTER_REPEAT=$((repeat - 1))"; break; }
    fi
  done
  [ "$repeat" -gt "$focused_repeats" ] && result="RESULT=PASS ACTIVITY_DESTROY_REPEATS=$focused_repeats"
else
  if [ -n "$focused_case" ]; then
    "$adb" -s "$serial" shell am start -n "$package/org.claritylink.android.R7C7LifecycleGuardActivity" \
      --es r7c6Case "$focused_case" --ei r7c7Repeat 1 >/dev/null
  else
    "$adb" -s "$serial" shell am start -n "$package/org.claritylink.android.R7C7LifecycleGuardActivity" >/dev/null
  fi
  result=''
  for attempt in $(seq 1 1800); do
    assert_owned_target
    result=$(tr -d '\r' < "$runtime_log" | awk '/RESULT=PASS|RESULT=FAIL/ {line=$0} END {print line}')
    case "$result" in *'RESULT=PASS'*|*'RESULT=FAIL'*) break;; esac
    sleep 1
  done
fi
assert_owned_target
if [ -n "$logcat_pid" ] && kill -0 "$logcat_pid" 2>/dev/null; then
  kill "$logcat_pid" 2>/dev/null || true
  wait "$logcat_pid" 2>/dev/null || true
  logcat_pid=
fi
printf '%s\n' "$result"
case "$result" in *'RESULT=PASS'*) exit 0 ;; *) echo 'API17 runtime harness failed or timed out.' >&2; exit 10;; esac
