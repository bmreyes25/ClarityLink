#!/usr/bin/env python3
"""Reproduce the frozen ADB nested-shell bug on an isolated API17 x86 AVD."""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import r7e6_test_a_collector as collector
from tools import run_r7e6_api17_runtime as runtime


def main() -> int:
    if platform.system() != "Darwin":
        raise runtime.RuntimeFailure("the pinned API17 emulator workflow requires macOS")
    required = [runtime.ADB, runtime.EMULATOR, runtime.AVDMANAGER,
                runtime.IMAGE / "system.img", runtime.JAVA_HOME / "bin/java"]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise runtime.RuntimeFailure("missing runtime input(s): " + ", ".join(missing))

    runtime.RUN_ROOT.mkdir(parents=True, exist_ok=True)
    runtime.AVD_ROOT.mkdir(parents=True, exist_ok=True)
    run_id = f"{os.getpid():x}{int(time.time()):08x}"[-12:]
    avd = f"r7e7f_shell_{run_id}"
    avd_dir = runtime.AVD_ROOT / f"{avd}.avd"
    avd_ini = runtime.AVD_ROOT / f"{avd}.ini"
    host_home = runtime.RUN_ROOT / f"host-home-shell-{run_id}"
    evidence_path = runtime.RUN_ROOT / f"api17-shell-construction-{run_id}.json"
    console_port = runtime.free_port_pair(5580, 5680)
    serial = f"emulator-{console_port}"
    adb_port = runtime.free_port(5038, 5138)

    host_home.mkdir(parents=True, mode=0o700)
    (host_home / ".android").mkdir(mode=0o700)
    env = os.environ.copy()
    env.update({"HOME": str(host_home), "ANDROID_HOME": str(runtime.SDK),
                "ANDROID_SDK_ROOT": str(runtime.SDK), "ANDROID_AVD_HOME": str(runtime.AVD_ROOT),
                "ANDROID_USER_HOME": str(host_home / ".android"), "JAVA_HOME": str(runtime.JAVA_HOME),
                "PATH": str(runtime.JAVA_HOME / "bin") + os.pathsep + env.get("PATH", ""),
                "ADB_USB": "0", "ADB_LOCAL_TRANSPORT_MAX_PORT": str(console_port + 5),
                "ANDROID_ADB_SERVER_PORT": str(adb_port)})
    env.pop("ANDROID_SERIAL", None)
    env.pop("ADB_SERVER_SOCKET", None)
    env.pop("ADB_SERVER_PORT", None)
    log = open(runtime.RUN_ROOT / f"api17-shell-construction-{run_id}.log", "wb")
    evidence: dict[str, object] = {
        "probe": "R7E7F_API17_ADB_SHELL_ARGUMENT_CONSTRUCTION",
        "run_id": run_id, "serial": "REDACTED", "avd": avd,
        "adb_server_port": adb_port, "physical_targets_allowed": False,
        "guest_identity": {}, "host_checks": [], "commands": [], "cleanup_failures": [],
    }
    server = None
    emulator = None
    avd_created = False
    status = 1

    def run_exact(label: str, *remote_argv: str) -> subprocess.CompletedProcess[bytes]:
        if server is None:
            raise runtime.RuntimeFailure("isolated ADB server is not running")
        argv = runtime.adb_command(adb_port, serial, "shell", *remote_argv)
        result = runtime.run_client(argv, env, 8.0, server, label)
        safe_argv = list(argv)
        if "-s" in safe_argv:
            safe_argv[safe_argv.index("-s") + 1] = "<REDACTED_SERIAL>"
        stdout = result.stdout.decode("utf-8", "replace").replace("\r", "")
        stderr = result.stderr.decode("utf-8", "replace").replace("\r", "")
        evidence["commands"].append({"label": label, "argv_redacted": safe_argv,
                                     "host_returncode": result.returncode,
                                     "stdout": stdout[:8192], "stderr": stderr[:8192],
                                     "stdout_truncated": len(stdout) > 8192,
                                     "stderr_truncated": len(stderr) > 8192})
        return result

    try:
        if avd_dir.exists() or avd_ini.exists():
            raise runtime.RuntimeFailure("run-unique AVD name already exists; refusing reuse")
        created = subprocess.run(
            [str(runtime.AVDMANAGER), "create", "avd", "--name", avd,
             "--package", "system-images;android-17;default;x86", "--force"],
            input=b"no\n", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, timeout=60, check=False)
        if created.returncode != 0 or not avd_dir.is_dir() or not avd_ini.is_file():
            raise runtime.RuntimeFailure("could not create unique API17 x86 AVD")
        avd_created = True
        config = (avd_dir / "config.ini").read_text(errors="replace")
        if "abi.type=x86" not in config or "system-images/android-17/default/x86" not in config:
            raise runtime.RuntimeFailure("AVD does not use the pinned API17 x86 image")

        server = subprocess.Popen(
            [str(runtime.ADB), "--one-device", serial, "-P", str(adb_port), "server", "nodaemon"],
            stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        time.sleep(0.25)
        if server.poll() is not None:
            raise runtime.RuntimeFailure("isolated one-device ADB server exited")
        emulator = subprocess.Popen(
            ["arch", "-x86_64", str(runtime.EMULATOR), "-avd", avd,
             "-ports", f"{console_port},{console_port + 1}", "-no-window", "-no-audio",
             "-no-snapshot", "-no-boot-anim", "-wipe-data", "-accel", "off",
             "-gpu", "swiftshader_indirect", "-no-metrics", "-crash-report-mode", "disabled"],
            stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)

        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            runtime.assert_owned_emulator_transport(console_port, serial, emulator, server, env, evidence)
            inv = runtime.run_client([str(runtime.ADB), "-P", str(adb_port), "devices"],
                                     env, 5.0, server, "emulator inventory")
            rows = [line.split() for line in inv.stdout.decode("utf-8", "replace").splitlines()[1:]
                    if line.strip()]
            if len(rows) > 1 or any(row[0] != serial for row in rows):
                raise runtime.RuntimeFailure("private ADB server saw an unexpected target")
            if rows == [[serial, "device"]]:
                boot = runtime.target_command(adb_port, serial, server, env,
                                              "getprop sys.boot_completed", "emulator boot-complete", 8.0)
                if boot.strip() == "1":
                    break
            if emulator.poll() is not None or server.poll() is not None:
                raise runtime.RuntimeFailure("isolated emulator or ADB server exited during boot")
            time.sleep(1)
        else:
            raise runtime.RuntimeFailure("owned API17 emulator boot timed out")

        runtime.assert_inventory(adb_port, serial, server, env)
        identity = [runtime.target_command(adb_port, serial, server, env, f"getprop {prop}", prop).strip()
                    for prop in ("ro.build.version.release", "ro.build.version.sdk", "ro.product.cpu.abi")]
        if identity != ["4.2.2", "17", "x86"]:
            raise runtime.RuntimeFailure(f"unexpected emulator identity: {identity!r}")
        evidence["guest_identity"] = {"release": identity[0], "api": identity[1], "abi": identity[2]}

        child, parent = 2_000_000_001, 2_000_000_002
        fixed = collector.process_absence_command(child, parent)
        malformed = run_exact("original collector nested sh -c argv", "sh", "-c", fixed)
        malformed_stdout = malformed.stdout.decode("utf-8", "replace")
        malformed_stderr = malformed.stderr.decode("utf-8", "replace")
        if malformed.returncode != 0 or malformed_stdout or malformed_stderr:
            raise runtime.RuntimeFailure(
                "original nested-shell behavior differed from expected empty transport-success result")

        corrected = run_exact("corrected one-argument adb shell expression", fixed)
        marker = f"R7E6_PIDS_ABSENT:{child}:{parent}\n"
        corrected_stdout = corrected.stdout.decode("utf-8", "replace").replace("\r", "")
        corrected_stderr = corrected.stderr.decode("utf-8", "replace").replace("\r", "")
        if corrected.returncode != 0 or corrected_stdout != marker or corrected_stderr:
            raise runtime.RuntimeFailure("corrected single-expression command did not emit the exact sentinel")

        remote_pid = run_exact("remote $$ expansion positive control", "echo R7E7F_REMOTE_PID:$$")
        pid_out = remote_pid.stdout.decode("utf-8", "replace").strip()
        if remote_pid.returncode != 0 or not re.fullmatch(r"R7E7F_REMOTE_PID:[1-9][0-9]*", pid_out):
            raise runtime.RuntimeFailure("remote $$ did not expand to one decimal shell PID")

        live = ("test -d /proc/$$ && test -r /proc/$$/stat && test -r /proc/self/stat && "
                "test ! -e /proc/$$ && echo R7E6_PIDS_ABSENT:1:2")
        live_result = run_exact("live exact PID blocks sentinel", live)
        if live_result.returncode != 0 or live_result.stdout or live_result.stderr:
            raise runtime.RuntimeFailure("live shell PID failed to block process-absence sentinel")

        no_control = ("test -d /proc/$$ && test -r /proc/$$/stat && "
                      "test -r /proc/r7e7f_missing_control/stat && "
                      "test ! -e /proc/2000000001 && test ! -e /proc/2000000002 && "
                      "echo R7E6_PIDS_ABSENT:2000000001:2000000002")
        no_control_result = run_exact("missing procfs positive control blocks sentinel", no_control)
        if no_control_result.returncode != 0 or no_control_result.stdout or no_control_result.stderr:
            raise runtime.RuntimeFailure("missing procfs positive control failed to block sentinel")

        evidence["decision"] = "R7E7F_API17_ADB_SHELL_CONSTRUCTION_REPRODUCED_AND_FIXED"
        evidence["original_expected"] = {"stdout": "", "stderr": "", "host_returncode": 0}
        evidence["corrected_expected_sentinel"] = marker.rstrip("\n")
        status = 0
    finally:
        failures: list[str] = []
        runtime.stop_owned(emulator, "owned emulator", failures)
        runtime.stop_owned(server, "private ADB server", failures)
        if avd_created:
            try:
                shutil.rmtree(avd_dir)
                avd_ini.unlink(missing_ok=True)
            except Exception as exc:
                failures.append(f"owned AVD cleanup failed: {exc}")
        shutil.rmtree(host_home, ignore_errors=True)
        evidence["cleanup_failures"] = failures
        evidence["finished_utc"] = runtime.now()
        evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        evidence_path.chmod(0o600)
        log.close()
        print(f"R7E7F_API17_SHELL_EVIDENCE={evidence_path}")
        if failures:
            status = 1
    if status == 0:
        print("R7E7F_API17_ADB_SHELL_CONSTRUCTION_PROVEN")
    return status


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except runtime.RuntimeFailure as exc:
        print(f"R7E7F_API17_SHELL_PROBE_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(2)
