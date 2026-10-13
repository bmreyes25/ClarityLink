#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sdk=${P2C2_SDK_ROOT:-"$HOME/Android/r7c2-sdk"}
adb="$sdk/platform-tools/adb"
emulator="$sdk/.emulator-intel/emulator/emulator"
avdmanager="$sdk/cmdline-tools/latest/bin/avdmanager"
apk="$repo/build/p2c2/p2c2-probe.apk"
out="$repo/build/p2c2"
package=org.claritylink.p2c2.probe
component="$package/org.claritylink.android.P2C2AdmissionProbeActivity"
[ -x "$adb" ] && [ -x "$emulator" ] && [ -x "$avdmanager" ] && [ -f "$apk" ] || {
  echo 'Build the probe and provide the isolated API17 emulator tools.' >&2; exit 2;
}
mkdir -p "$out/avd"
export ANDROID_HOME="$sdk" ANDROID_SDK_ROOT="$sdk" ANDROID_AVD_HOME="$out/avd"
export JAVA_HOME=${JAVA_HOME:-"$HOME/.local/toolchains/temurin-17.0.20.1+1-aarch64/jdk-17.0.20.1+1/Contents/Home"}
export PATH="$JAVA_HOME/bin:$PATH"
export ADB_LOCAL_TRANSPORT_MAX_PORT=5585

server_port=$(python3 - <<'PY'
import socket
s=socket.socket();s.bind(('127.0.0.1',0));print(s.getsockname()[1]);s.close()
PY
)
export ADB_SERVER_PORT="$server_port" ANDROID_ADB_SERVER_PORT="$server_port"
adb_local() { "$adb" -P "$server_port" "$@"; }
serial= emulator_pid= avd_created=0 ready=0
avd="p2c2_api17_$$"
avd_dir="$out/avd/$avd.avd"
avd_ini="$out/avd/$avd.ini"
cleanup() {
  status=$?
  trap - EXIT INT TERM
  if [ "$ready" -eq 1 ] && owned_target >/dev/null 2>&1; then
    adb_local -s "$serial" shell 'settings put global overlay_display_devices ""' >/dev/null 2>&1 || true
  fi
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
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# A private server is restricted to a deliberately nonexistent USB serial.
# Emulator local transport remains available; no physical USB target can attach.
adb_local --one-device P2C2_NO_PHYSICAL_USB_DEVICE start-server >/dev/null
inventory() { adb_local devices | awk 'NR>1 && NF {print $1" "$2}'; }
[ -z "$(inventory)" ] || { echo 'Isolated server already has a target.' >&2; exit 3; }
port=$(python3 - <<'PY'
import socket
for port in (5580,5582,5584):
    sockets=[]
    try:
        for number in (port,port+1):
            s=socket.socket();s.bind(('127.0.0.1',number));sockets.append(s)
        print(port);break
    except OSError: pass
    finally:
        for s in sockets:s.close()
else: raise SystemExit('No free local emulator port pair')
PY
)
serial="emulator-$port"
owned_target() {
  [ -n "$emulator_pid" ] && kill -0 "$emulator_pid" 2>/dev/null || return 1
  [ "$(inventory)" = "$serial device" ] || return 1
}
printf 'no\n' | "$avdmanager" create avd --name "$avd" \
  --package 'system-images;android-17;default;x86' --force >/dev/null
avd_created=1
[ -f "$avd_dir/config.ini" ] && grep -q '^abi.type=x86$' "$avd_dir/config.ini" || exit 4
arch -x86_64 "$emulator" -avd "$avd" -port "$port" -no-window -no-audio \
  -no-snapshot -no-boot-anim -wipe-data -accel off -gpu swiftshader_indirect \
  >"$out/emulator.log" 2>&1 &
emulator_pid=$!
for attempt in $(seq 1 300); do
  kill -0 "$emulator_pid" 2>/dev/null || { echo 'Emulator exited before boot.' >&2; exit 5; }
  targets=$(inventory)
  case "$targets" in ''|"$serial "*) :;; *) echo "Unexpected isolated target: $targets" >&2; exit 5;; esac
  if owned_target && [ "$(adb_local -s "$serial" shell getprop sys.boot_completed | tr -d '\r')" = 1 ]; then
    ready=1; break
  fi
  sleep 1
done
[ "$ready" -eq 1 ] || { echo 'API17 emulator boot timeout.' >&2; exit 5; }
owned_target || exit 6
qemu=$(adb_local -s "$serial" shell getprop ro.kernel.qemu | tr -d '\r')
api=$(adb_local -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')
release=$(adb_local -s "$serial" shell getprop ro.build.version.release | tr -d '\r')
abi=$(adb_local -s "$serial" shell getprop ro.product.cpu.abi | tr -d '\r')
avd_name=$(adb_local -s "$serial" emu avd name | tr -d '\r' | awk '$1!="OK" && NF {print;exit}')
[ "$qemu:$api:$release:$abi:$avd_name" = "1:17:4.2.2:x86:$avd" ] || {
  echo 'Owned emulator identity mismatch.' >&2; exit 6;
}
echo "P2C2_ISOLATED_API17_READY serial=$serial server_port=$server_port"

log_text() { owned_target || exit 7; adb_local -s "$serial" logcat -d -s ClarityLinkP2C2:I '*:S' | tr -d '\r'; }
await_marker() {
  wanted=$1
  for attempt in $(seq 1 60); do
    log=$(log_text)
    case "$log" in *P2C2_FAIL*) echo "$log" | tail -25 >&2; exit 8;; esac
    printf '%s\n' "$log" | grep -F "$wanted" >/dev/null && return 0
    sleep 1
  done
  echo "Timed out waiting for $wanted" >&2; exit 8
}
owned_target
adb_local -s "$serial" shell settings put global overlay_display_devices '800x480/160'
owned_target
adb_local -s "$serial" install "$apk" >/dev/null
owned_target
adb_local -s "$serial" logcat -c
owned_target
adb_local -s "$serial" shell am start -n "$component" >/dev/null
await_marker 'P2C2_HOST_SIMULATOR_PASS layers=bottom,navigation,warning stale_generation=reject navigation_exit=clear close=idempotent evidence=synthetic'
await_marker 'P2C2_CONTENT_VIEW_PASS frames=2 session=immutable clear=before_install warning=clears resize=fit generation=77 evidence=synthetic'
await_marker 'P2C2_INVALID_DISPLAY_PASS'
await_marker 'P2C2_PERMISSION_DENIED_PASS'
await_marker 'P2C2_PRESENTATION_PASS cycles=3 activeSurface=1'
log_text > "$out/first-run.log"
owned_target
adb_local -s "$serial" shell 'settings put global overlay_display_devices ""'
await_marker 'P2C2_DISPLAY_REMOVED_PASS created=4 destroyed=4'
log_text > "$out/first-run.log"
echo 'P2C2_LIFECYCLE_AND_REMOVAL_PASS'

# Recreate an active Presentation, then terminate its process. WMS must lose
# that app window; this verifies emulator framework reclamation, not Honda.
owned_target
adb_local -s "$serial" shell am force-stop "$package"
owned_target
adb_local -s "$serial" shell settings put global overlay_display_devices '800x480/160'
owned_target
adb_local -s "$serial" logcat -c
owned_target
adb_local -s "$serial" shell am start -n "$component" >/dev/null
await_marker 'P2C2_PRESENTATION_PASS cycles=3 activeSurface=1'
owned_target
before=$(adb_local -s "$serial" shell dumpsys window windows | tr -d '\r')
printf '%s\n' "$before" | grep -F "$package" >/dev/null || {
  echo 'Cannot prove app window existed before process death.' >&2; exit 9;
}
owned_target
adb_local -s "$serial" shell am force-stop "$package"
for attempt in $(seq 1 15); do
  owned_target
  processes=$(adb_local -s "$serial" shell ps | tr -d '\r')
  windows=$(adb_local -s "$serial" shell dumpsys window windows | tr -d '\r')
  if ! printf '%s\n' "$processes" | awk -v name="$package" '$NF==name {found=1} END {exit !found}' &&
     ! printf '%s\n' "$windows" | grep -F "$package" >/dev/null; then
    log_text > "$out/second-run.log"
    echo 'P2C2_PROCESS_DEATH_RECLAIM_PASS'
    shasum -a 256 "$apk" "$out/first-run.log" "$out/second-run.log"
    echo 'API17_EMULATOR_PASS'
    exit 0
  fi
  sleep 1
done
echo 'Process/window remained after force-stop.' >&2
exit 9
