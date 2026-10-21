#!/usr/bin/env bash
# Read-only REA/JADX environment check. Never executes APK contents or installs tools.
set -u

expected_jadx_sha='6e5eacf500b64292bfb73c49797c1958f6ee44646e43e868039ae7feb573ff75'
smoke_apk=''
if [[ ${1:-} == '--smoke-apk' ]]; then
  if [[ $# -ne 2 ]]; then echo 'usage: doctor_re_toolchain.sh [--smoke-apk PATH]' >&2; exit 2; fi
  smoke_apk=$2
elif [[ $# -ne 0 ]]; then
  echo 'usage: doctor_re_toolchain.sh [--smoke-apk PATH]' >&2
  exit 2
fi

status=0
config_path=${CODEX_HOME:-$HOME/.codex}/config.toml
config_value() { sed -nE "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*\"([^\"]+)\".*/\\1/p" "$config_path" | head -n 1; }
check() { printf '%-30s %s\n' "$1" "$2"; }

arch=$(uname -m 2>/dev/null || printf unknown)
check 'Host architecture' "$arch"
[[ $arch == arm64 || $arch == aarch64 ]] || check 'Architecture note' 'OPTIONAL: verify provider compatibility for this host'

rea_cli=''
if command -v rea >/dev/null 2>&1; then
  rea_cli=$(command -v rea)
  check 'REA executable' "INSTALLED: $rea_cli"
  rea --version 2>&1 | head -n 1 | sed 's/^/  version: /'
else
  rea_cli=$(find "$HOME/.npm/_npx" -path '*/node_modules/rea-agents/scripts/rea.mjs' -type f -print -quit 2>/dev/null || true)
  if [[ -n $rea_cli ]]; then check 'REA executable' 'INSTALLED in npm cache'; node "$rea_cli" --version 2>&1 | head -n 1 | sed 's/^/  version: /'; else check 'REA executable' 'MISSING'; status=1; fi
fi

java_home=${JAVA_HOME:-$(config_value JAVA_HOME)}
java_bin=java; javac_bin=javac
if [[ -n $java_home && -x $java_home/bin/java ]]; then java_bin=$java_home/bin/java; javac_bin=$java_home/bin/javac; fi
if command -v "$java_bin" >/dev/null 2>&1 || [[ -x $java_bin ]]; then
  check 'Java' "RUNTIME VERIFIED: $("$java_bin" -version 2>&1 | head -n 1)"
else check 'Java' 'MISSING'; status=1; fi
if command -v "$javac_bin" >/dev/null 2>&1 || [[ -x $javac_bin ]]; then check 'Javac' "RUNTIME VERIFIED: $("$javac_bin" -version 2>&1)"; else check 'Javac' 'MISSING'; status=1; fi
if (command -v "$java_bin" >/dev/null 2>&1 || [[ -x $java_bin ]]) && "$java_bin" --list-modules 2>/dev/null | grep -q '^jdk.compiler@'; then
  check 'jdk.compiler' 'RUNTIME VERIFIED'
  tmp_java=$(mktemp -d 2>/dev/null || true)
  if [[ -n $tmp_java ]]; then
    printf '%s\n' 'public final class ToolchainSmoke { public static void main(String[] args) { System.out.print("jdk-compiler-ok"); } }' > "$tmp_java/ToolchainSmoke.java"
    if "$javac_bin" "$tmp_java/ToolchainSmoke.java" >/dev/null 2>&1 && [[ $("$java_bin" -cp "$tmp_java" ToolchainSmoke 2>/dev/null) == 'jdk-compiler-ok' ]]; then check 'JDK compile/run' 'RUNTIME VERIFIED'; else check 'JDK compile/run' 'FAILED'; status=1; fi
    rm -rf "$tmp_java"
  else check 'JDK compile/run' 'SKIPPED: temporary directory unavailable'; status=1; fi
else check 'jdk.compiler' 'MISSING'; status=1; fi

jar_path=${REA_JADX_MCP_JAR:-}
if [[ -z $jar_path && -r $config_path ]]; then jar_path=$(config_value REA_JADX_MCP_JAR); fi
if [[ -n $jar_path && -r $jar_path ]]; then
  check 'JADX provider file' 'INSTALLED and readable'
  if command -v shasum >/dev/null 2>&1; then
    actual_sha=$(shasum -a 256 "$jar_path" | awk '{print $1}')
    if [[ $actual_sha == "$expected_jadx_sha" ]]; then check 'JADX provider SHA-256' 'VERIFIED against documented pin'; else check 'JADX provider SHA-256' 'INCOMPATIBLE: digest mismatch'; status=1; fi
  else check 'JADX provider SHA-256' 'MISSING shasum'; status=1; fi
  if command -v unzip >/dev/null 2>&1 && unzip -tqq "$jar_path" >/dev/null 2>&1; then check 'JADX provider archive' 'RUNTIME INPUT VALIDATED'; else check 'JADX provider archive' 'INVALID or unzip unavailable'; status=1; fi
else check 'JADX provider file' 'MISSING or not configured'; status=1; fi

if [[ -r $config_path ]]; then
  check 'Codex REA config' 'CONFIGURED file found; running MCP inheritance still requires a live call'
else check 'Codex REA config' 'MISSING'; fi

for tool in apktool ghidraRun aapt aapt2 apksigner adb; do
  if command -v "$tool" >/dev/null 2>&1; then check "$tool" 'OPTIONAL: installed'; else check "$tool" 'OPTIONAL: unavailable'; fi
done

if [[ -n $smoke_apk ]]; then
  if [[ ! -r $smoke_apk ]]; then check 'Smoke APK' 'MISSING or unreadable'; status=1
  elif [[ -n $rea_cli ]]; then
    check 'Smoke APK' 'Running REA package inspection; APK contents are not executed'
    if [[ $rea_cli == */rea.mjs ]]; then JAVA_HOME="$java_home" REA_JADX_MCP_JAR="$jar_path" node "$rea_cli" inspect-android-package "$smoke_apk" --format json --full-output | python3 -c 'import json,sys; x=json.load(sys.stdin); d=x.get("data",x); n=d.get("normalized_result",{}); print(json.dumps({"ok":x.get("ok"),"evidence_id":d.get("evidence_id"),"package_name":n.get("package_name"),"min_sdk":n.get("min_sdk"),"target_sdk":n.get("target_sdk"),"provider":d.get("provider",{}).get("version")})); sys.exit(0 if x.get("ok") else 1)' || status=1; else "$rea_cli" inspect-android-package "$smoke_apk" --format json --full-output | python3 -c 'import json,sys; x=json.load(sys.stdin); print(json.dumps(x)); sys.exit(0 if x.get("ok") else 1)' || status=1; fi
  else check 'Smoke operation' 'BLOCKED: REA CLI unavailable'; status=1; fi
fi

check 'Codex MCP Android' 'NOT PROVEN by this doctor; restart desktop and perform a live Android tool call'
exit "$status"
