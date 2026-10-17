#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sdk=${TEST3_SDK_ROOT:-"$HOME/Android/r7c2-sdk"}
java_home=${JAVA_HOME:-"$HOME/.local/toolchains/temurin-17.0.20.1+1-aarch64/jdk-17.0.20.1+1/Contents/Home"}
out=${TEST3_BUILD_DIR:-"$repo/build/test3-admission-probe"}
case "$out" in /*) ;; *) out="$repo/$out" ;; esac
adb="$sdk/platform-tools/adb"; emulator="$sdk/.emulator-intel/emulator/emulator"
avdmanager="$sdk/cmdline-tools/latest/bin/avdmanager"
apk="$out/claritylink-test3-admission-probe.apk"
package=org.claritylink.admissionprobe
component=org.claritylink.android.Test3DisplayAccessProbeActivity
expected_apk_sha256=${TEST3_EXPECTED_APK_SHA256:-}
[ -f "$apk" ] && [ -x "$adb" ] && [ -x "$emulator" ] && [ -x "$avdmanager" ] || {
  echo 'Build the probe and provide the pinned API17 emulator tools first.' >&2; exit 2;
}
[ -n "$expected_apk_sha256" ] || {
  echo 'Set TEST3_EXPECTED_APK_SHA256 from the reviewed probe build receipt.' >&2; exit 2;
}
apk_sha256=$(python3 - "$apk" "$expected_apk_sha256" <<'PY'
import hashlib, re, sys
from pathlib import Path
apk = Path(sys.argv[1])
expected = sys.argv[2]
if apk.is_symlink() or not apk.is_file() or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
    raise SystemExit("probe APK or expected SHA-256 is invalid")
actual = hashlib.sha256(apk.read_bytes()).hexdigest()
if actual != expected.lower():
    raise SystemExit("probe APK SHA-256 does not match the reviewed build receipt")
print(actual)
PY
) || exit 2
[ -x "$java_home/bin/java" ] || { echo 'Pinned local JDK 17 unavailable.' >&2; exit 2; }
export JAVA_HOME="$java_home" PATH="$java_home/bin:$PATH"
python3 - "$out" <<'PY'
from pathlib import Path
import os, sys
p = Path(sys.argv[1])
if not p.is_dir() or p.is_symlink() or p.resolve() != p.absolute():
    raise SystemExit("TEST3_BUILD_DIR must be an existing canonical directory, not a symlink")
for parent in (p, *p.parents):
    if parent.is_symlink():
        raise SystemExit("TEST3_BUILD_DIR has a symlink component")
PY
run_root=$(mktemp -d "$out/test3-run-XXXXXX")
avd_root="$run_root/avd"
avd_log="$run_root/emulator.log"
adb_log="$run_root/adb-server.log"
avd="test3probe_api17_$$"; avd_dir="$avd_root/$avd.avd"; avd_ini="$avd_root/$avd.ini"
port=; serial=; emulator_pid=; adb_server_pid=; adb_port=; created=0
cleanup() {
  result=$?; trap - EXIT INT TERM
  if [ -n "$emulator_pid" ] && kill -0 "$emulator_pid" 2>/dev/null; then
    kill "$emulator_pid" 2>/dev/null || true; wait "$emulator_pid" 2>/dev/null || true
  fi
  # `nodaemon server` runs in this invocation's child process. Recheck both
  # its command and current listener ownership immediately before signaling it.
  if [ -n "$adb_server_pid" ]; then
    server_command=$(ps -p "$adb_server_pid" -o command= 2>/dev/null || true)
    if [ -n "$adb_port" ]; then
      listener_pid=$(lsof -nP -t -iTCP:"$adb_port" -sTCP:LISTEN 2>/dev/null || true)
      case "$server_command:$listener_pid" in *"$adb"*"-P $adb_port nodaemon server"*:"$adb_server_pid")
        kill "$adb_server_pid" 2>/dev/null || true
        wait "$adb_server_pid" 2>/dev/null || true
        ;;
        *) echo 'ADB server exited or ownership changed; no cleanup signal sent.' >&2 ;;
      esac
    fi
  fi
  if [ "$created" -eq 1 ]; then
    python3 - "$out" "$run_root" "$avd_root" <<'PY'
from pathlib import Path
import shutil,sys
base, run, owned = map(Path, sys.argv[1:])
if (run.is_symlink() or run.parent.resolve() != base.resolve() or
        not run.name.startswith("test3-run-") or owned.is_symlink() or
        owned.parent.resolve() != run.resolve() or owned.name != "avd"):
    raise SystemExit("refusing to remove an AVD directory not owned by this invocation")
shutil.rmtree(owned)
PY
  fi
  exit "$result"
}
trap cleanup EXIT; trap 'exit 130' INT; trap 'exit 143' TERM
chmod 700 "$run_root"
mkdir -m 700 "$avd_root"
created=1
python3 - "$avd_log" <<'PY'
from pathlib import Path
import os, sys
p = Path(sys.argv[1])
fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
os.close(fd)
PY
python3 - "$adb_log" <<'PY'
from pathlib import Path
import os, sys
p = Path(sys.argv[1])
fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
os.close(fd)
PY
export ANDROID_HOME="$sdk" ANDROID_SDK_ROOT="$sdk" ANDROID_AVD_HOME="$avd_root"
adb_port=$(python3 - <<'PY'
import socket
s=socket.socket(); s.bind(('127.0.0.1',0)); print(s.getsockname()[1]); s.close()
PY
)
export ADB_SERVER_PORT="$adb_port" ANDROID_ADB_SERVER_PORT="$adb_port"
adb_local() { "$adb" -P "$adb_port" "$@"; }
remote_status_query() {
  query_kind=$1; query_command=$2; query_package=${3:-}
  remote_reply=$(adb_local -s "$serial" shell "$query_command; cl_remote_rc=\$?; echo CLARITYLINK_REMOTE_RC=\$cl_remote_rc" 2>&1) || return 1
  remote_output=$(printf '%s\n' "$remote_reply" | python3 "$repo/tools/test3_remote_query.py" "$query_kind" "$query_package") || return 1
}
read_process_table() {
  remote_status_query processes 'ps' || return 1
}
"$adb" -P "$adb_port" nodaemon server >> "$adb_log" 2>&1 &
adb_server_pid=$!
server_ready=0
for attempt in $(seq 1 20); do
  kill -0 "$adb_server_pid" 2>/dev/null || { echo 'Owned ADB server failed to bind its private port.' >&2; exit 3; }
  listener_pid=$(lsof -nP -t -iTCP:"$adb_port" -sTCP:LISTEN 2>/dev/null || true)
  if [ "$listener_pid" = "$adb_server_pid" ] && adb_local devices >/dev/null 2>&1; then
    server_ready=1; break
  fi
  sleep 0.1
done
[ "$server_ready" -eq 1 ] || { echo 'Owned ADB server did not become ready.' >&2; exit 3; }
inventory() { adb_local devices | awk 'NR>1 && NF {print $1" "$2}'; }
[ -z "$(inventory)" ] || { echo 'Unexpected target on private ADB server.' >&2; exit 3; }
for candidate in 5580 5582 5584; do
  if python3 - "$candidate" <<'PY'
import socket,sys
p=int(sys.argv[1]); ss=[]
try:
 for n in (p,p+1):
  s=socket.socket(); s.bind(('127.0.0.1',n)); ss.append(s)
except OSError: raise SystemExit(1)
finally:
 for s in ss: s.close()
PY
  then port=$candidate; break; fi
done
[ -n "$port" ] || { echo 'No free emulator port pair.' >&2; exit 4; }
serial="emulator-$port"
if [ -e "$avd_dir" ] || [ -e "$avd_ini" ] || [ -L "$avd_dir" ] || [ -L "$avd_ini" ]; then
  echo 'Refusing an existing AVD name collision.' >&2; exit 4
fi
printf 'no\n' | "$avdmanager" create avd --name "$avd" --package 'system-images;android-17;default;x86' >/dev/null
grep -q '^abi.type=x86$' "$avd_dir/config.ini" || exit 4
arch -x86_64 "$emulator" -avd "$avd" -port "$port" -no-window -no-audio -no-snapshot \
  -no-boot-anim -wipe-data -accel off -gpu swiftshader_indirect > "$avd_log" 2>&1 &
emulator_pid=$!
ready=0
for attempt in $(seq 1 300); do
  kill -0 "$emulator_pid" 2>/dev/null || { echo 'Owned emulator exited during boot.' >&2; exit 5; }
  devices=$(inventory)
  case "$devices" in ''|"$serial "*) :;; *) echo "Unexpected private ADB target: $devices" >&2; exit 5;; esac
  if [ "$devices" = "$serial device" ]; then
    bootanim=$(adb_local -s "$serial" shell getprop init.svc.bootanim | tr -d '\r')
    package_service=$(adb_local -s "$serial" shell service check package | tr -d '\r')
    display_service=$(adb_local -s "$serial" shell service check display | tr -d '\r')
    provisioned=$(adb_local -s "$serial" shell settings get global device_provisioned 2>/dev/null | tr -d '\r')
    case "$bootanim:$package_service:$display_service" in
      stopped:*found:*found*)
        case "$provisioned" in 0|1) ready=1; break;; esac
        ;;
    esac
  fi
  sleep 1
done
[ "$ready" -eq 1 ] || { echo 'API17 emulator boot timeout.' >&2; exit 5; }
api=$(adb_local -s "$serial" shell getprop ro.build.version.sdk | tr -d '\r')
release=$(adb_local -s "$serial" shell getprop ro.build.version.release | tr -d '\r')
[ "$api:$release" = '17:4.2.2' ] || { echo 'API17 guest identity mismatch.' >&2; exit 6; }
adb_local -s "$serial" shell settings put global overlay_display_devices '800x480/160'
overlay_ready=0
for attempt in $(seq 1 30); do
  overlay_value=$(adb_local -s "$serial" shell settings get global overlay_display_devices 2>/dev/null | tr -d '\r')
  if [ "$overlay_value" = '800x480/160' ]; then overlay_ready=1; break; fi
  sleep 1
done
[ "$overlay_ready" -eq 1 ] || { echo 'Synthetic display overlay setting was not established.' >&2; exit 7; }
adb_local -s "$serial" install "$apk" >/dev/null
case "$(adb_local -s "$serial" shell pm path "$package" | tr -d '\r')" in package:*) :;; *) exit 8;; esac
uid=$(adb_local -s "$serial" shell dumpsys package "$package" | sed -n 's/.*userId=\([0-9][0-9]*\).*/\1/p' | head -1 | tr -d '\r')
[ -n "$uid" ] || { echo 'Probe UID unavailable.' >&2; exit 8; }
adb_local -s "$serial" logcat -c
adb_local -s "$serial" shell am start -n "$package/$component" >/dev/null
logs=
for attempt in $(seq 1 30); do
logs=$(adb_local -s "$serial" logcat -d -v brief -s ClarityLinkTest3Probe:V '*:S' | tr -d '\r')
  printf '%s\n' "$logs" | grep -F 'PROBE_COMPLETE windows_created=0 surfaces_allocated=0' >/dev/null && break
  sleep 1
done
printf '%s\n' "$logs" > "$run_root/probe-log.txt"
read_process_table || { echo 'Process query failed or returned malformed output.' >&2; exit 9; }
processes=$remote_output
probe_pid=$(printf '%s\n' "$processes" | awk -v package="$package" \
  '$NF == package { if (count++ == 0) pid=$2 } END { if (count == 1 && pid ~ /^[0-9]+$/) print pid; else exit 1 }') || {
  echo 'Could not bind the probe log to one live package process.' >&2; exit 9;
}
python3 "$repo/tools/test3_output_validation_v2.py" --expected-uid "$uid" --expected-pid "$probe_pid" --require-public-inventory \
  < "$run_root/probe-log.txt" > "$run_root/probe-validation.json" || {
  echo 'Strict probe log validation failed.' >&2
  cat "$run_root/probe-log.txt" >&2
  exit 9
}
remote_status_query windows 'dumpsys window windows' || { echo 'Window query failed or returned malformed output.' >&2; exit 10; }
windows=$remote_output
if printf '%s\n' "$windows" | grep -F "$package" >/dev/null; then echo 'Probe owns a window.' >&2; exit 10; fi
printf '%s\n' "$logs"
adb_local -s "$serial" shell am force-stop "$package"
read_process_table || { echo 'Post-stop process query failed or returned malformed output.' >&2; exit 11; }
processes=$remote_output
if printf '%s\n' "$processes" | awk -v package="$package" '$NF == package { found=1 } END { exit !found }'; then
  echo 'Probe process remains after force-stop.' >&2; exit 11
fi
if uninstall_output=$(adb_local -s "$serial" uninstall "$package" 2>&1); then :; else
  echo 'Probe uninstall command failed.' >&2; exit 12;
fi
uninstall_output=$(printf '%s' "$uninstall_output" | tr -d '\r')
[ "$uninstall_output" = 'Success' ] || { echo 'Probe uninstall did not return exact Success.' >&2; exit 12; }
remote_status_query packages "pm list packages \"$package\"" "$package" || { echo 'Package absence query failed or returned malformed output.' >&2; exit 12; }
remaining=$remote_output
[ -z "$remaining" ] || { echo 'Package remains after uninstall.' >&2; exit 12; }
read_process_table || { echo 'Post-uninstall process query failed or returned malformed output.' >&2; exit 12; }
processes=$remote_output
if printf '%s\n' "$processes" | awk -v package="$package" '$NF == package { found=1 } END { exit !found }'; then
  echo 'Probe process remains after uninstall.' >&2; exit 12
fi
adb_local -s "$serial" shell 'settings put global overlay_display_devices ""'
echo "TEST3_API17_EMULATOR_PASS api=$api release=$release uid=$uid apk_sha256=$apk_sha256 display1_enumerated=true display_context_created=true presentation_created=false app_window=false process_stopped=true package_uninstalled=true physical_scanout=unproven"
