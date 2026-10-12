#!/usr/bin/env python3
"""Run the Test A diagnostic lifecycle only on a dedicated API17 x86 AVD.

The ADB server is pinned to this run's emulator serial with --one-device and
uses a dedicated TCP port. It cannot select a USB/physical target. The runner
owns both foreground processes and removes only its unique AVD and artifacts.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone


REPO = Path(__file__).resolve().parents[1]
SDK = Path(os.environ.get("R7E6_SDK_ROOT", str(Path.home() / "Android/r7c2-sdk")))
JAVA_HOME = Path(os.environ.get(
    "R7E6_JAVA_HOME",
    str(Path.home() / ".local/toolchains/temurin-17.0.20.1+1-aarch64/jdk-17.0.20.1+1/Contents/Home"),
))
ADB = SDK / "platform-tools/adb"
EMULATOR = SDK / ".emulator-intel/emulator/emulator"
AVDMANAGER = SDK / "cmdline-tools/latest/bin/avdmanager"
IMAGE = SDK / "system-images/android-17/default/x86"
PRODUCTION_X86 = REPO / "build/r7e1/native-x86/claritylink-target-diag"
FAULT_X86 = REPO / "build/r7e6/native-x86-test/claritylink-target-diag-test"
AVD_ROOT = REPO / "build/r7e6/avd"
RUN_ROOT = REPO / "build/r7e6/runs"
HOST_COMMAND_TIMEOUT = 12.0
MAX_CAPTURE = 256 * 1024


class RuntimeFailure(RuntimeError):
    pass


class ProcOnlyComplete(Exception):
    """Stop after the focused procfs matrix, before diagnostic lifecycle runs."""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def free_port_pair(start: int, stop: int) -> int:
    for port in range(start, stop + 1, 2):
        sockets: list[socket.socket] = []
        try:
            for candidate in (port, port + 1):
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
                sock.bind(("127.0.0.1", candidate))
                sockets.append(sock)
            return port
        except OSError:
            pass
        finally:
            for sock in sockets:
                sock.close()
    raise RuntimeFailure(f"no free localhost port pair in {start}..{stop + 1}")


def free_port(start: int, stop: int) -> int:
    for port in range(start, stop + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
            sock.bind(("127.0.0.1", port))
            return port
        except OSError:
            pass
        finally:
            sock.close()
    raise RuntimeFailure(f"no free localhost port in {start}..{stop}")


def stop_owned(process: subprocess.Popen[bytes] | None, label: str,
               failures: list[str], timeout: float = 10.0) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            failures.append(f"owned {label} process group did not exit after SIGKILL")
    except ProcessLookupError:
        try:
            process.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            failures.append(f"owned {label} process did not exit")


def run_client(argv: list[str], env: dict[str, str], timeout: float,
               server: subprocess.Popen[bytes], label: str) -> subprocess.CompletedProcess[bytes]:
    if server.poll() is not None:
        raise RuntimeFailure("isolated, one-device ADB server exited; refusing implicit restart")
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=env, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate()
        raise RuntimeFailure(
            f"host command timeout ({label}); adb client was stopped; emulator cleanup required; "
            f"stdout={stdout[-4096:]!r} stderr={stderr[-4096:]!r}"
        ) from exc
    if len(stdout) + len(stderr) > MAX_CAPTURE:
        raise RuntimeFailure(f"{label} output exceeded {MAX_CAPTURE} byte cap")
    return subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)


def ensure_success(result: subprocess.CompletedProcess[bytes], label: str) -> str:
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeFailure(f"{label} failed rc={result.returncode}: {stderr[-3000:]} {stdout[-3000:]}")
    if stderr.strip():
        raise RuntimeFailure(f"{label} emitted stderr: {stderr[-3000:]}")
    return stdout.replace("\r", "")


def ensure_push_success(result: subprocess.CompletedProcess[bytes],
                        local_path: Path, label: str) -> str:
    """Accept this ADB version's stderr progress line only after exact shape validation."""
    stdout = result.stdout.decode("utf-8", errors="replace").replace("\r", "")
    stderr = result.stderr.decode("utf-8", errors="replace").replace("\r", "").strip()
    if result.returncode != 0 or stdout.strip():
        raise RuntimeFailure(
            f"{label} failed rc={result.returncode}: stdout={stdout[-1000:]!r} "
            f"stderr={stderr[-1000:]!r}"
        )
    path = re.escape(str(local_path))
    if not re.fullmatch(
        path + r": 1 file pushed, 0 skipped\. [0-9.]+ [KMG]?B/s "
        r"\([0-9]+ bytes in [0-9.]+s\)", stderr
    ):
        raise RuntimeFailure(f"{label} returned an unrecognized transfer result: {stderr!r}")
    return stdout


def adb_command(adb_port: int, serial: str, *args: str) -> list[str]:
    # Every operation names both the dedicated server and its exact emulator.
    return [str(ADB), "-P", str(adb_port), "-s", serial, *args]


def target_command(adb_port: int, serial: str, server: subprocess.Popen[bytes],
                   env: dict[str, str], command: str, label: str,
                   timeout: float = HOST_COMMAND_TIMEOUT) -> str:
    result = run_client(adb_command(adb_port, serial, "shell", command), env,
                        timeout, server, label)
    return ensure_success(result, label)


def assert_inventory(adb_port: int, serial: str, server: subprocess.Popen[bytes],
                     env: dict[str, str]) -> str:
    result = run_client([str(ADB), "-P", str(adb_port), "devices"], env, 5.0,
                        server, "isolated emulator inventory")
    output = ensure_success(result, "isolated emulator inventory")
    rows = [line.split() for line in output.splitlines()[1:] if line.strip()]
    if rows != [[serial, "device"]]:
        raise RuntimeFailure(f"isolated ADB target inventory is not the exact owned emulator: {rows!r}")
    return output


def assert_owned_emulator_transport(console_port: int, serial: str,
                                    emulator: subprocess.Popen[bytes],
                                    server: subprocess.Popen[bytes],
                                    env: dict[str, str],
                                    evidence: dict[str, object]) -> None:
    """Refuse guest commands if another host ADB process attached to this AVD."""
    adb_port = console_port + 1
    result = subprocess.run(
        ["/usr/sbin/lsof", "-nP", "-t", f"-iTCP:{adb_port}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env=env, timeout=5.0, check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeFailure("could not verify exclusive emulator transport ownership")
    pids = {int(line) for line in result.stdout.splitlines() if line.strip().isdigit()}
    allowed = {emulator.pid, server.pid}
    foreign = sorted(pids - allowed)
    observation = {
        "label": "host loopback transport ownership",
        "serial": serial,
        "port": adb_port,
        "pids": sorted(pids),
        "allowed_owned_pids": sorted(allowed),
    }
    records = evidence["host_checks"]
    assert isinstance(records, list)
    records.append(observation)
    if foreign:
        raise RuntimeFailure(
            f"emulator loopback transport has foreign ADB owner(s) {foreign}; "
            "refusing every guest command"
        )


def invoke_diag(adb_port: int, serial: str, server: subprocess.Popen[bytes],
                env: dict[str, str], remote: str, mode: str, label: str,
                timeout: float = HOST_COMMAND_TIMEOUT) -> tuple[int, str, float, int, int, bool]:
    if not re.fullmatch(r"/data/local/tmp/claritylink_r7e6_[0-9a-f]{12}(?:_fault)?", remote):
        raise RuntimeFailure("remote diagnostic path did not match the frozen test grammar")
    if mode not in {"--version", "--self-test", "--test-child-loop", "--test-child-sleep",
                    "--test-child-crash", "--test-parent-timeout", "--test-sigchld-ignored",
                    "--test-fork-failure", "--test-waitpid-error"}:
        raise RuntimeFailure(f"unsupported test mode: {mode}")
    # Path and mode are strict constants/validated tokens; the shell suffix
    # captures the guest status even on older adbd shell protocol versions.
    command = f"{remote} {mode}; echo __R7E6_STATUS:$?"
    started = time.monotonic()
    output = target_command(adb_port, serial, server, env, command, label, timeout)
    elapsed = time.monotonic() - started
    match = re.search(r"(?:^|\n)__R7E6_STATUS:(\d+)\s*$", output)
    if not match:
        raise RuntimeFailure(f"{label} returned without guest status trailer: {output[-2000:]!r}")
    status = int(match.group(1))
    start_record = re.search(r"SUPERVISOR_CHILD_STARTED parent_pid=(\d+) child_pid=(\d+)", output)
    reaped_record = re.search(r"SUPERVISOR_CHILD_REAPED parent_pid=(\d+) child_pid=(\d+)(?: recovery=(\w+))?", output)
    supervisor = reaped_record or start_record
    parent_pid = int(supervisor.group(1)) if supervisor else -1
    child_pid = int(supervisor.group(2)) if supervisor else -1
    return status, output, elapsed, parent_pid, child_pid, reaped_record is not None


def verify_pid_absent(adb_port: int, serial: str, server: subprocess.Popen[bytes],
                      env: dict[str, str], pid: int, label: str) -> None:
    if pid <= 1 or pid > 4_194_304:
        raise RuntimeFailure(f"invalid reported PID for {label}: {pid}")
    output = target_command(adb_port, serial, server, env,
                            f"test ! -e /proc/{pid} && echo R7E6_PID_ABSENT:{pid}",
                            f"{label} exact /proc check", timeout=5.0)
    if output.strip() != f"R7E6_PID_ABSENT:{pid}":
        raise RuntimeFailure(f"process state uncertain for PID {pid}: {output!r}")


def main() -> int:
    if platform.system() != "Darwin":
        raise RuntimeFailure("this pinned x86 emulator runner is supported only on macOS")
    required = [ADB, EMULATOR, AVDMANAGER, IMAGE / "system.img", PRODUCTION_X86,
                FAULT_X86, JAVA_HOME / "bin/java"]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeFailure("missing runtime input(s): " + ", ".join(missing))

    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    AVD_ROOT.mkdir(parents=True, exist_ok=True)
    run_id = f"{os.getpid():x}{int(time.time()):08x}"[-12:]
    avd = f"r7e6_api17_{run_id}"
    avd_dir = AVD_ROOT / f"{avd}.avd"
    avd_ini = AVD_ROOT / f"{avd}.ini"
    host_home = RUN_ROOT / f"host-home-{run_id}"
    evidence_path = RUN_ROOT / f"api17-runtime-{run_id}.json"
    # Use a legal even emulator port, point the emulator at the private server,
    # and let the host socket-ownership guard catch any competing server.
    console_port = free_port_pair(5580, 5680)
    serial = f"emulator-{console_port}"
    adb_port = free_port(5038, 5138)
    remote_prod = f"/data/local/tmp/claritylink_r7e6_{run_id}"
    remote_fault = remote_prod + "_fault"
    remote_fault_marker = f"/data/local/tmp/claritylink_r7e6_{run_id}_fault" # strict test-only name

    host_home.mkdir(parents=True, mode=0o700)
    (host_home / ".android").mkdir(mode=0o700)
    env = os.environ.copy()
    env.update({"HOME": str(host_home), "ANDROID_HOME": str(SDK),
                "ANDROID_SDK_ROOT": str(SDK), "ANDROID_AVD_HOME": str(AVD_ROOT),
                "ANDROID_USER_HOME": str(host_home / ".android"),
                "JAVA_HOME": str(JAVA_HOME),
                "PATH": str(JAVA_HOME / "bin") + os.pathsep + env.get("PATH", "")})
    env.pop("ANDROID_SERIAL", None)
    env.pop("ADB_SERVER_SOCKET", None)
    env.pop("ADB_SERVER_PORT", None)
    # ADB_USB=0 prevents this dedicated server from enumerating or opening any
    # host USB interface. Emulator discovery remains enabled (ADB_EMU unset).
    env["ADB_USB"] = "0"
    env["ADB_LOCAL_TRANSPORT_MAX_PORT"] = str(console_port + 5)
    env["ANDROID_ADB_SERVER_PORT"] = str(adb_port)

    evidence: dict[str, object] = {
        "run_id": run_id, "started_utc": now(), "host": platform.platform(),
        "sdk_root": str(SDK), "adb_version": "", "emulator_version": "",
        "avd": avd, "serial": serial, "adb_server_port": adb_port,
        "emulator_console_port": console_port, "emulator_pid": None,
        "isolated_adb_one_device_filter": serial, "physical_targets_allowed": False,
        "host_command_timeout_seconds": HOST_COMMAND_TIMEOUT,
        "production_x86_sha256": sha256(PRODUCTION_X86),
        "fault_test_x86_sha256": sha256(FAULT_X86),
        "host_commands": [], "host_checks": [], "runtime_results": [], "cleanup": {},
    }
    adb_log = open(RUN_ROOT / f"adb-server-{run_id}.log", "wb")
    emulator_log = open(RUN_ROOT / f"emulator-{run_id}.log", "wb")
    adb_server: subprocess.Popen[bytes] | None = None
    emulator: subprocess.Popen[bytes] | None = None
    avd_created = False
    failures: list[str] = []

    def local(argv: list[str], label: str, timeout: float = 30.0,
              stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
        process = subprocess.run(argv, input=stdin, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, env=env, timeout=timeout,
                                 check=False)
        if len(process.stdout) + len(process.stderr) > MAX_CAPTURE:
            raise RuntimeFailure(f"{label} local output exceeded cap")
        cast = evidence["host_commands"]
        assert isinstance(cast, list)
        cast.append({"label": label, "argv": argv, "returncode": process.returncode,
                     "stdout": process.stdout.decode("utf-8", "replace")[-8192:],
                     "stderr": process.stderr.decode("utf-8", "replace")[-8192:]})
        if process.returncode != 0:
            raise RuntimeFailure(f"{label} failed: {process.stderr.decode('utf-8', 'replace')[-2000:]}")
        return process

    try:
        evidence["adb_version"] = local([str(ADB), "version"], "ADB version", 5.0).stdout.decode().strip()
        evidence["emulator_version"] = local(["arch", "-x86_64", str(EMULATOR), "-version"],
                                             "x86 emulator version", 10.0).stdout.decode().strip()
        evidence["java_version"] = local([str(JAVA_HOME / "bin/java"), "-version"],
                                          "pinned Temurin JDK version", 5.0).stderr.decode().strip()
        if avd_dir.exists() or avd_ini.exists():
            raise RuntimeFailure("run-unique AVD name already exists; refusing to replace it")
        avd_created = True
        local([str(AVDMANAGER), "create", "avd", "--name", avd,
                         "--package", "system-images;android-17;default;x86", "--force"],
                        "create unique project AVD", 60.0, stdin=b"no\n")
        if not avd_dir.is_dir() or not avd_ini.is_file():
            raise RuntimeFailure("AVD manager did not create the unique AVD in the isolated directory")
        config = (avd_dir / "config.ini").read_text(errors="replace")
        if "abi.type=x86" not in config or "system-images/android-17/default/x86" not in config:
            raise RuntimeFailure("created AVD did not bind to the pinned API17 x86 system image")
        if not (avd_dir / "userdata.img").exists():
            raise RuntimeFailure("unique AVD user data image is missing")

        # USB discovery is disabled for this dedicated server. Its emulator
        # scan range is extended to include this run's unique local port;
        # the shared default server remains on its smaller default range.
        adb_server = subprocess.Popen(
            [str(ADB), "--one-device", serial, "-P", str(adb_port), "server", "nodaemon"],
            stdout=adb_log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
        evidence["adb_server_pid"] = adb_server.pid
        time.sleep(0.25)
        if adb_server.poll() is not None:
            raise RuntimeFailure("isolated ADB server with --one-device did not stay alive")

        emulator_argv = ["arch", "-x86_64", str(EMULATOR), "-avd", avd,
                         "-ports", f"{console_port},{console_port + 1}",
                         "-no-window", "-no-audio", "-no-snapshot", "-no-boot-anim",
                         "-wipe-data", "-accel", "off", "-gpu", "swiftshader_indirect",
                         "-no-metrics", "-crash-report-mode", "disabled"]
        emulator = subprocess.Popen(emulator_argv, stdout=emulator_log,
                                    stderr=subprocess.STDOUT, env=env,
                                    start_new_session=True)
        evidence["emulator_pid"] = emulator.pid
        evidence["emulator_started_utc"] = now()

        boot_deadline = time.monotonic() + 300.0
        booted = False
        while time.monotonic() < boot_deadline:
            if adb_server.poll() is not None:
                raise RuntimeFailure("isolated ADB server exited during emulator boot")
            if emulator.poll() is not None:
                raise RuntimeFailure(f"owned emulator exited during boot (rc={emulator.returncode})")
            assert_owned_emulator_transport(console_port, serial, emulator,
                                            adb_server, env, evidence)
            result = run_client([str(ADB), "-P", str(adb_port), "devices"], env, 5.0,
                                adb_server, "owned-emulator boot inventory")
            inventory = ensure_success(result, "owned-emulator boot inventory")
            rows = [line.split() for line in inventory.splitlines()[1:] if line.strip()]
            if len(rows) > 1 or any(row[0] != serial for row in rows):
                raise RuntimeFailure(f"unexpected device visible to filtered ADB server: {rows!r}")
            if rows == [[serial, "device"]]:
                boot = target_command(adb_port, serial, adb_server, env,
                                      "getprop sys.boot_completed", "emulator boot-complete", 8.0).strip()
                if boot == "1":
                    booted = True
                    break
            time.sleep(1.0)
        if not booted:
            raise RuntimeFailure("owned API17 emulator did not boot within 300 seconds")

        assert_inventory(adb_port, serial, adb_server, env)
        avd_console = run_client(
            adb_command(adb_port, serial, "emu", "avd", "name"), env, 5.0,
            adb_server, "exact emulator console AVD identity",
        )
        avd_console_output = ensure_success(avd_console, "exact emulator console AVD identity")
        avd_names = [line.strip() for line in avd_console_output.splitlines()
                     if line.strip() and line.strip() not in {"OK", "KO"}]
        if len(avd_names) != 1:
            raise RuntimeFailure(f"emulator console returned ambiguous AVD name: {avd_console_output!r}")
        identity = {
            "qemu": target_command(adb_port, serial, adb_server, env, "getprop ro.kernel.qemu", "qemu identity").strip(),
            "release": target_command(adb_port, serial, adb_server, env, "getprop ro.build.version.release", "release identity").strip(),
            "api": target_command(adb_port, serial, adb_server, env, "getprop ro.build.version.sdk", "API identity").strip(),
            "abi": target_command(adb_port, serial, adb_server, env, "getprop ro.product.cpu.abi", "ABI identity").strip(),
            "avd": avd_names[0],
        }
        if identity["qemu"] != "1" or identity["release"] != "4.2.2" or identity["api"] != "17" or identity["abi"] != "x86" or avd not in identity["avd"]:
            raise RuntimeFailure(f"guest identity verification failed: {identity!r}")
        dalvik = target_command(adb_port, serial, adb_server, env,
                                "dalvikvm -version 2>&1", "Dalvik runtime identity", 8.0)
        if "Dalvik VM version" not in dalvik and "Dalvik" not in dalvik:
            raise RuntimeFailure(f"guest did not report Dalvik runtime: {dalvik!r}")
        evidence["guest_identity"] = identity
        evidence["dalvikvm_version"] = dalvik

        if os.environ.get("R7E7A_PROC_ONLY") == "1":
            proc_results: list[dict[str, object]] = evidence["runtime_results"]  # type: ignore[assignment]

            def proc_case(label: str, script: str, expected: str | None) -> str:
                output = target_command(adb_port, serial, adb_server, env,
                                        "sh -c '" + script + "'", label, 5.0)
                if expected is not None and output.strip() != expected:
                    raise RuntimeFailure(f"{label}: expected {expected!r}, got {output!r}")
                if expected is None and output.strip():
                    raise RuntimeFailure(f"{label}: unexpected sentinel/output {output!r}")
                proc_results.append({"label": label, "stdout": output})
                return output

            live = "test -d /proc/$$ && test -r /proc/$$/stat && test -r /proc/self/stat"
            proc_case("same-shell procfs positive control", live + " && echo PROC_SELF_OK", "PROC_SELF_OK")
            proc_case("visible live PID blocks absence sentinel",
                      live + " && test ! -e /proc/$$ && echo R7E6_PIDS_ABSENT:1:2", None)
            proc_case("inaccessible positive control blocks absence sentinel",
                      "test -d /proc/$$ && test -r /proc/$$/stat && "
                      "test -r /proc/r7e7a_missing_control/stat && "
                      "test ! -e /proc/4194302 && test ! -e /proc/4194303 && "
                      "echo R7E6_PIDS_ABSENT:4194302:4194303", None)
            proc_case("reaped child PID absence after wait",
                      "sleep 1 & p=$!; wait $p; "
                      "test -d /proc/$$ && test -r /proc/$$/stat && test -r /proc/self/stat && "
                      "test ! -e /proc/$p && echo REAPED_PID_ABSENT", "REAPED_PID_ABSENT")
            evidence["procfs_matrix"] = "API17_PROCFS_POSITIVE_CONTROL_PASS"
            evidence["emulator_runtime_result"] = "API17_PROCFS_REVIEW_ONLY"
            return_code = 0
            raise ProcOnlyComplete()

        # A unique 0555 local staging copy is used; canonical artifacts are
        # not chmod'ed or rewritten. The fault binary is test-only.
        stage_dir = RUN_ROOT / f"staging-{run_id}"
        stage_dir.mkdir(mode=0o700)
        prod_stage = stage_dir / "claritylink-target-diag"
        fault_stage = stage_dir / "claritylink-target-diag-fault"
        shutil.copyfile(PRODUCTION_X86, prod_stage)
        shutil.copyfile(FAULT_X86, fault_stage)
        prod_stage.chmod(0o555)
        fault_stage.chmod(0o555)
        if sha256(prod_stage) != sha256(PRODUCTION_X86) or sha256(fault_stage) != sha256(FAULT_X86):
            raise RuntimeFailure("local staging bytes differ from their build artifacts")

        for local_path, remote_path in ((prod_stage, remote_prod), (fault_stage, remote_fault_marker)):
            assert_inventory(adb_port, serial, adb_server, env)
            absent = target_command(adb_port, serial, adb_server, env,
                                    f"test ! -e {remote_path} && echo R7E6_ABSENT", "remote exact path precheck")
            if absent.strip() != "R7E6_ABSENT":
                raise RuntimeFailure(f"remote test path already exists: {remote_path}")
            push = run_client(adb_command(adb_port, serial, "push", str(local_path), remote_path),
                              env, 30.0, adb_server, f"push {local_path.name}")
            ensure_push_success(push, local_path, f"push {local_path.name}")
            metadata = target_command(adb_port, serial, adb_server, env,
                                      f"ls -l {remote_path}", f"remote metadata {local_path.name}")
            md5_output = target_command(adb_port, serial, adb_server, env,
                                        f"/system/bin/md5 {remote_path}", f"remote md5 {local_path.name}")
            stat = re.search(
                r"(?m)^(-[rwx-]{9})\s+(\w+)\s+(\w+)\s+(\d+)\s+.*\s+"
                r"([^\s]+)\s*$", metadata
            )
            md5_match = re.search(r"\b([0-9a-fA-F]{32})\b", md5_output)
            expected_md5 = md5(local_path)
            if (not stat or stat.group(1) != "-r-xr-xr-x"
                    or stat.group(2, 3) != ("root", "root")
                    or int(stat.group(4)) != local_path.stat().st_size
                    or stat.group(5) != Path(remote_path).name):
                raise RuntimeFailure(f"remote mode/owner/size/type mismatch: {metadata!r}")
            if not md5_match or md5_match.group(1).lower() != expected_md5:
                raise RuntimeFailure(f"remote MD5 mismatch for {local_path.name}: {md5_output!r}")

        results: list[dict[str, object]] = evidence["runtime_results"]  # type: ignore[assignment]

        def run_case(remote: str, mode: str, label: str, expected_status: int,
                     expected_text: str | None = None, timeout: float = HOST_COMMAND_TIMEOUT,
                     require_reap: bool = True) -> dict[str, object]:
            assert_inventory(adb_port, serial, adb_server, env)
            status, output, elapsed, parent_pid, child_pid, reaped = invoke_diag(
                adb_port, serial, adb_server, env, remote, mode, label, timeout)
            record: dict[str, object] = {"label": label, "mode": mode, "status": status,
                                         "elapsed_seconds": round(elapsed, 4),
                                         "stdout": output[-8192:], "parent_pid": parent_pid,
                                         "child_pid": child_pid,
                                         "exact_child_reaped_record": reaped}
            if status != expected_status:
                raise RuntimeFailure(f"{label}: guest status {status}, expected {expected_status}; {output[-2000:]!r}")
            if expected_text and expected_text not in output:
                raise RuntimeFailure(f"{label}: missing expected output {expected_text!r}")
            if require_reap:
                if not reaped or parent_pid < 2 or child_pid < 2:
                    raise RuntimeFailure(f"{label}: no exact child-reaped record: {output[-2000:]!r}")
            if parent_pid >= 2 and child_pid >= 2:
                verify_pid_absent(adb_port, serial, adb_server, env, child_pid, label + " child")
                verify_pid_absent(adb_port, serial, adb_server, env, parent_pid, label + " parent")
            results.append(record)
            return record

        version_samples: list[float] = []
        for index in range(5):
            record = run_case(remote_prod, "--version", f"production version {index + 1}", 0,
                              "CLARITYLINK_DIAG_VERSION=1.0.0")
            version_samples.append(float(record["elapsed_seconds"]))
            if "ABI=x86" not in str(record["stdout"]):
                raise RuntimeFailure("x86 emulator diagnostic reports a different ABI")
        self_test_record = run_case(remote_prod, "--self-test", "production self-test", 0,
                                    "SELF_TEST_PASS")
        if "RESOURCE_COUNTS final=0" not in str(self_test_record["stdout"]):
            raise RuntimeFailure("self-test did not report zero modeled resources")

        # Faults run only in the compile-time test variant.
        run_case(remote_fault, "--test-child-loop", "child busy-loop watchdog", 124,
                 require_reap=True, timeout=8.0)
        run_case(remote_fault, "--test-child-sleep", "child blocked-sleep watchdog", 124,
                 require_reap=True, timeout=8.0)
        run_case(remote_fault, "--test-child-crash", "child crash mapping", 126,
                 require_reap=True, timeout=8.0)
        run_case(remote_fault, "--test-sigchld-ignored", "SIGCHLD ignore reset", 0,
                 "SUPERVISOR_CHILD_REAPED", timeout=8.0)
        run_case(remote_fault, "--test-fork-failure", "fork failure fail-closed", 127,
                 require_reap=False, timeout=8.0)
        run_case(remote_fault, "--test-waitpid-error", "waitpid error exact recovery", 127,
                 "recovery=kill_waitpid", timeout=8.0)
        run_case(remote_fault, "--test-parent-timeout", "parent watchdog exact kill/reap", 125,
                 require_reap=False, timeout=8.0)

        # The production child/parent deadlines are 2 s/4 s. Keep the
        # historical 100-pair default; R7E7G can request a smaller focused
        # transport rehearsal without repeating the established stress run.
        requested_cycles = int(os.environ.get("R7E7G_API17_CYCLES", "100"))
        if not 1 <= requested_cycles <= 100:
            raise RuntimeFailure("R7E7G_API17_CYCLES must be in [1, 100]")
        cycle_max: list[float] = []
        for index in range(requested_cycles):
            v = run_case(remote_prod, "--version", f"repeat {index + 1} version", 0,
                         "CLARITYLINK_DIAG_VERSION=1.0.0")
            s = run_case(remote_prod, "--self-test", f"repeat {index + 1} self-test", 0,
                         "SELF_TEST_PASS")
            cycle_max.append(max(float(v["elapsed_seconds"]), float(s["elapsed_seconds"])))
        evidence["repeat_cycles"] = {"requested": requested_cycles, "completed": len(cycle_max),
                                      "version_and_self_test_each_cycle": True,
                                      "max_pair_seconds": max(cycle_max),
                                      "version_timing_seconds": {"min": min(version_samples),
                                                                  "median": sorted(version_samples)[len(version_samples)//2],
                                                                  "max": max(version_samples)},
                                      "self_test_seconds": self_test_record["elapsed_seconds"]}

        # Remove only the two exact temporary paths, then prove both absent.
        for remote in (remote_prod, remote_fault_marker):
            rm_output = target_command(adb_port, serial, adb_server, env,
                                       f"/system/bin/rm {remote} && echo R7E6_RM_OK", "exact emulator cleanup")
            if rm_output.strip() != "R7E6_RM_OK":
                raise RuntimeFailure(f"exact emulator cleanup failed for {remote}: {rm_output!r}")
            absent = target_command(adb_port, serial, adb_server, env,
                                    f"test ! -e {remote} && echo R7E6_ABSENT", "emulator final exact absence")
            if absent.strip() != "R7E6_ABSENT":
                raise RuntimeFailure(f"emulator path remains after exact rm: {remote}")
        evidence["emulator_runtime_result"] = "ANDROID_API17_X86_RUNTIME_WATCHDOG_PROVEN_X86"
        evidence["normal_execution_result"] = "PASS"
        evidence["host_timeout_failure_policy"] = "abort; stop only owned emulator; preserve local evidence; no retry"
        return_code = 0
    except ProcOnlyComplete:
        pass
    except Exception as exc:  # evidence and owned-process cleanup are mandatory on every failure
        evidence["failure"] = f"{type(exc).__name__}: {exc}"
        return_code = 1
    except KeyboardInterrupt:
        evidence["failure"] = "KeyboardInterrupt: runner cancelled; only owned emulator/server were stopped"
        return_code = 130
    finally:
        evidence["shutdown_started_utc"] = now()
        stop_owned(emulator, "emulator", failures)
        evidence["emulator_shutdown_utc"] = now()
        stop_owned(adb_server, "isolated ADB server", failures)
        evidence["isolated_adb_shutdown_utc"] = now()
        if avd_created:
            try:
                if avd_dir.parent.resolve() != AVD_ROOT.resolve() or avd_dir.name != f"{avd}.avd":
                    raise RuntimeFailure("refusing cleanup outside the exact run-owned AVD path")
                shutil.rmtree(avd_dir, ignore_errors=False)
                avd_ini.unlink(missing_ok=True)
                evidence["avd_removed"] = not avd_dir.exists() and not avd_ini.exists()
            except Exception as exc:
                failures.append(f"owned AVD cleanup failed: {exc}")
        shutil.rmtree(host_home, ignore_errors=True)
        evidence["cleanup"] = {"emulator_process_exit": emulator.poll() if emulator else None,
                               "adb_server_process_exit": adb_server.poll() if adb_server else None,
                               "avd_removed": evidence.get("avd_removed", not avd_created),
                               "failures": failures}
        evidence["finished_utc"] = now()
        with evidence_path.open("w", encoding="utf-8") as handle:
            json.dump(evidence, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.chmod(evidence_path, 0o600)
        adb_log.close()
        emulator_log.close()
        print(f"R7E6_EVIDENCE={evidence_path}")
        print(f"R7E6_AVD={avd} PID={evidence.get('emulator_pid')} SERIAL={serial} ADB_SERVER_PORT={adb_port}")
        if failures:
            print("R7E6_CLEANUP_FAILURE=" + "; ".join(failures), file=sys.stderr)
            return_code = 1
    if return_code == 0:
        if os.environ.get("R7E7A_PROC_ONLY") == "1":
            print("ANDROID_API17_X86_PROCFS_REVIEW_PASS")
        else:
            print("ANDROID_API17_X86_RUNTIME_WATCHDOG_PROVEN_X86")
    return return_code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeFailure as exc:
        print(f"R7E6_RUNTIME_BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(2)
