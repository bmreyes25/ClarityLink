#!/usr/bin/env python3
"""Fixed-operation, host-side-only read-only Honda runtime collector.

This script has no arbitrary remote-command option. It never uploads a file,
uses adb root, touches /proc/PID/mem, signals/suspends a target, or executes a
target-side custom helper. Real collection requires explicit parked/disconnect
attestations and either one existing authorized ADB target or an explicit serial.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import shutil
import subprocess
import sys
import time
from enum import StrEnum
from typing import Any

from parsers import parse_proc_stat_start_time, parse_status, parse_task_listing


COMMAND_TIMEOUT = 20
MAX_COMMAND_OUTPUT = 32 * 1024 * 1024
THREAD_SNAPSHOTS = 5
THREAD_INTERVAL_SECONDS = 2.0
JMCS_STATIC_PATH = "/system/bin/jmcs"
REPO_ROOT = Path(__file__).resolve().parents[2]
SAFE_PROPERTIES = (
    "ro.build.fingerprint", "ro.build.id", "ro.build.display.id",
    "ro.build.version.release", "ro.build.version.sdk", "ro.product.board",
    "ro.product.device", "ro.product.model", "ro.hardware", "ro.bootloader",
    "ro.secure", "ro.debuggable",
)
SAFE_DUMPSYS = ("display", "SurfaceFlinger", "window")
EXPECTED_PRODUCT_DEVICE = "vcm30t30a"
EXPECTED_ANDROID_RELEASE = "4.2.2"
EXPECTED_ANDROID_SDK = "17"
EXPECTED_PRODUCT_BOARD = "Andromeda"
EXPECTED_HARDWARE = "vcm30t30"
STATIC_READ_PATHS = frozenset({
    "/proc/version", "/proc/sys/kernel/osrelease", "/proc/sys/kernel/ostype",
    "/proc/cpuinfo", "/proc/meminfo", "/proc/cmdline", "/proc/cpu/alignment",
    "/proc/config.gz", "/proc/modules", "/proc/devices", "/proc/filesystems",
    "/proc/interrupts", "/proc/mounts", "/proc/self/mounts",
    "/proc/net/tcp", "/proc/net/tcp6", "/proc/net/udp", "/proc/net/udp6",
    "/proc/net/unix", "/proc/partitions", "/proc/sys/kernel/randomize_va_space",
    "/proc/sys/vm/mmap_min_addr", "/proc/sys/kernel/yama/ptrace_scope",
    "/sys/fs/selinux/enforce", "/proc/self/status",
    "/sys/devices/system/cpu/online", "/sys/devices/system/cpu/possible",
    "/sys/devices/system/cpu/present",
})


class SafetyStop(RuntimeError):
    pass


class CommandResult(StrEnum):
    SUCCESS = "success"
    COMMAND_UNAVAILABLE = "command_unavailable"
    PERMISSION_DENIED = "permission_denied"
    TRANSPORT_FAILURE = "transport_failure"
    PROCESS_IDENTITY_CHANGE = "process_identity_change"
    TIMEOUT = "timeout"
    OUTPUT_LIMIT = "output_limit"
    NOT_EXPOSED = "not_exposed"
    OTHER_COMMAND_FAILURE = "other_command_failure"


def classify_command_result(exit_code: int, stdout: bytes, stderr: bytes,
                            *, timed_out: bool = False,
                            output_limited: bool = False,
                            operation: str = "") -> CommandResult:
    """Classify command outcomes without treating missing tools as transport loss."""
    if timed_out:
        return CommandResult.TIMEOUT
    if output_limited:
        return CommandResult.OUTPUT_LIMIT
    if operation == "readlink" and exit_code == 0 and not parse_ls_symlink_target(stdout):
        return CommandResult.NOT_EXPOSED
    diagnostic = (stderr + b"\n" + stdout).decode("utf-8", "replace").lower()
    if re.search(r"(?:^|\n)(?:/system/bin/)?(?:sh|mksh):\s*[^\n]*:\s*not found(?:\s|$)", diagnostic):
        return CommandResult.COMMAND_UNAVAILABLE
    if "permission denied" in diagnostic or "operation not permitted" in diagnostic:
        return CommandResult.PERMISSION_DENIED
    if any(marker in diagnostic for marker in (
            "error: closed", "device offline", "device unauthorized", "unauthorized",
            "no devices/emulators found", "device not found", "failed to read from device")):
        return CommandResult.TRANSPORT_FAILURE
    if exit_code == 0:
        return CommandResult.SUCCESS
    return CommandResult.OTHER_COMMAND_FAILURE


def classify_stop_reason(message: str) -> CommandResult:
    if "instance changed" in message.lower() or "pid changed" in message.lower():
        return CommandResult.PROCESS_IDENTITY_CHANGE
    if "timed out" in message.lower():
        return CommandResult.TIMEOUT
    return CommandResult.OTHER_COMMAND_FAILURE


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    start_time_ticks: int
    executable: str
    cmdline: str
    uid: str
    gid: str
    ppid: str


class FixedAdb:
    """ADB wrapper exposing only reviewed read operations."""

    def __init__(self, serial: str, *, resolve_auto: bool = True):
        adb = shutil.which("adb")
        if not adb:
            raise SafetyStop("adb executable not found in PATH")
        self.adb = adb
        self.records: list[dict[str, Any]] = []
        self.device_selection_count = None
        if serial == "auto" and resolve_auto:
            try:
                listing = subprocess.run((adb, "devices", "-l"), capture_output=True,
                                         timeout=5, check=False, text=True)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise SafetyStop("existing ADB device listing failed; refusing selection") from exc
            rows = [line.split() for line in listing.stdout.splitlines()[1:] if line.split()]
            self.records.append({"operation": "host_adb_devices_preflight",
                                 "result": "ok" if listing.returncode == 0 and len(rows) == 1 and len(rows[0]) > 1 and rows[0][1] == "device" else "refused",
                                 "exit_code": listing.returncode, "candidate_count": len(rows),
                                 "states": [row[1] for row in rows if len(row) > 1],
                                 "stdout_sha256": hashlib.sha256(listing.stdout.encode()).hexdigest(),
                                 "stderr_sha256": hashlib.sha256(listing.stderr.encode()).hexdigest()})
            if listing.returncode != 0 or len(rows) != 1 or len(rows[0]) < 2 or rows[0][1] != "device":
                states = [row[1] if len(row) > 1 else "MALFORMED" for row in rows]
                raise SafetyStop(f"expected exactly one authorized ADB device; found {len(rows)} entries, states={states}")
            serial = rows[0][0]
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", serial):
            raise ValueError("invalid ADB serial syntax")
        self.serial = serial

    def plan(self, operation: str, args: tuple[str, ...]) -> tuple[str, ...]:
        if operation in {"id", "uname", "ps", "service-list", "hash-jmcs", "ls-jmcs",
                         "hash-su", "ls-su"}:
            if args:
                raise SafetyStop("fixed command does not accept extra arguments")
            remote = {"id": ("id",), "uname": ("uname", "-a"), "ps": ("ps",),
                      "service-list": ("service", "list"),
                      "hash-jmcs": ("sha256sum", JMCS_STATIC_PATH),
                      "ls-jmcs": ("ls", "-l", JMCS_STATIC_PATH),
                      "hash-su": ("sha256sum", "/system/xbin/su"),
                      "ls-su": ("ls", "-l", "/system/xbin/su")}[operation]
        elif operation == "read":
            if len(args) != 1:
                raise SafetyStop("read requires exactly one allowlisted path")
            path = args[0]
            if path not in STATIC_READ_PATHS and not re.fullmatch(
                    r"/proc/[0-9]+/(?:cmdline|stat|statm|status|limits|maps|smaps|wchan|mounts|mountinfo|task/[0-9]+/(?:comm|status|stat|wchan|stack))"
                    r"|/sys/devices/system/cpu/cpu[0-9]+/(?:topology/(?:core_id|physical_package_id|thread_siblings_list)|cache/index[0-9]+/(?:level|type|size|coherency_line_size|number_of_sets|ways_of_associativity|shared_cpu_list|shared_cpu_map))",
                    path):
                raise SafetyStop(f"read path outside fixed allowlist: {path}")
            remote = ("cat", path)
        elif operation == "list":
            if len(args) != 1:
                raise SafetyStop("list requires exactly one allowlisted directory")
            path = args[0]
            if path not in ("/proc", "/sys/devices/system/cpu", "/proc/net") and not re.fullmatch(
                    r"/proc/[0-9]+/(?:task|fd)|/sys/devices/system/cpu/cpu[0-9]+/cache", path):
                raise SafetyStop(f"directory outside fixed allowlist: {path}")
            # API-17 toolbox `ls` rejects the newer `-1` option; whitespace
            # tokenization in the host parsers handles its default columns.
            remote = ("ls", path)
        elif operation == "readlink":
            if len(args) != 1:
                raise SafetyStop("readlink requires exactly one allowlisted path")
            path = args[0]
            if not re.fullmatch(r"/proc/[0-9]+/(?:exe|cwd|root|fd/[0-9]+)", path):
                raise SafetyStop(f"readlink path outside fixed allowlist: {path}")
            # Android toolbox images may not ship the standalone readlink applet.
            remote = ("ls", "-l", path)
        elif operation == "property":
            if len(args) != 1 or args[0] not in SAFE_PROPERTIES:
                raise SafetyStop("property outside fixed allowlist")
            remote = ("getprop", args[0])
        elif operation == "dumpsys":
            if len(args) != 1 or args[0] not in SAFE_DUMPSYS:
                raise SafetyStop("dumpsys service outside fixed allowlist")
            remote = ("dumpsys", args[0])
        elif operation == "logcat":
            if args:
                raise SafetyStop("logcat is fixed to the bounded read-only form")
            remote = ("logcat", "-d", "-t", "500")
        else:
            raise SafetyStop(f"operation not allowlisted: {operation}")
        # Use the legacy `shell` service, which was verified on the API-17 target.
        return (self.adb, "-s", self.serial, "shell", *remote)

    def run(self, operation: str, *args: str, timeout: int = COMMAND_TIMEOUT,
            max_bytes: int = MAX_COMMAND_OUTPUT) -> tuple[int, bytes, bytes]:
        command = self.plan(operation, tuple(args))
        return self._run_planned(command, operation, tuple(args), timeout=timeout,
                                 max_bytes=max_bytes)

    def _run_planned(self, command: tuple[str, ...], operation: str,
                     args: tuple[str, ...], *, timeout: int = COMMAND_TIMEOUT,
                     max_bytes: int = MAX_COMMAND_OUTPUT) -> tuple[int, bytes, bytes]:
        """Execute a command built by a reviewed fixed-operation planner."""
        started = datetime.now(timezone.utc).isoformat()
        record: dict[str, Any] = {
            "operation": operation, "arguments": list(args),
            "command": list(command), "started_utc": started,
            "timeout_seconds": timeout, "max_output_bytes": max_bytes,
        }
        timed_out = truncated = False
        try:
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            assert proc.stdout is not None and proc.stderr is not None
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
            selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
            chunks = {"stdout": bytearray(), "stderr": bytearray()}
            deadline = time.monotonic() + timeout
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    proc.kill()
                    break
                events = selector.select(min(remaining, 0.25))
                for key, _ in events:
                    try:
                        data = os.read(key.fileobj.fileno(), 65536)
                    except OSError:
                        data = b""
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    total = len(chunks["stdout"]) + len(chunks["stderr"])
                    allowance = max(0, max_bytes - total)
                    chunks[key.data].extend(data[:allowance])
                    if len(data) > allowance:
                        truncated = True
                        proc.kill()
                        break
                if timed_out or truncated:
                    break
            selector.close()
            try:
                code = proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                code = proc.wait(timeout=2)
            out, err = bytes(chunks["stdout"]), bytes(chunks["stderr"])
            proc.stdout.close()
            proc.stderr.close()
            if timed_out:
                err += b"\ncollector: command timed out\n"
                code = 124
            elif truncated:
                err += b"\ncollector: combined output limit reached; process stopped\n"
                code = 125
            record["truncated"] = truncated
        except OSError as exc:
            out, err, code = b"", str(exc).encode(), 127
            record["host_execution_error"] = True
        record.update({"finished_utc": datetime.now(timezone.utc).isoformat(),
                       "exit_code": code})
        record["result"] = classify_command_result(
            code, out, err, timed_out=timed_out,
            output_limited=record.get("truncated", False), operation=operation).value
        self.records.append(record)
        return code, out, err

    def dry_run_command(self, operation: str, *args: str) -> str:
        return shlex.join(self.plan(operation, tuple(args)))


def _decode_cmdline(raw: bytes) -> str:
    return raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()


def parse_ls_symlink_target(raw: bytes) -> str:
    lines = [line.strip() for line in raw.decode("utf-8", "replace").splitlines() if line.strip()]
    if len(lines) != 1 or " -> " not in lines[0]:
        return ""
    return lines[0].rsplit(" -> ", 1)[1].strip()


def parse_ps_jmcs(text: str) -> tuple[int, ...]:
    lines = [line.split() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return ()
    header = [column.upper() for column in lines[0]]
    try:
        pid_idx = header.index("PID")
    except ValueError:
        return ()
    name_idx = next((header.index(col) for col in ("NAME", "CMD", "COMMAND") if col in header), None)
    matches = []
    for fields in lines[1:]:
        if pid_idx >= len(fields):
            continue
        name_fields = fields[name_idx:] if name_idx is not None and name_idx < len(fields) else fields[-1:]
        name = " ".join(name_fields)
        if name == "jmcs" or name.endswith("/jmcs") or name.split(":")[-1] == "jmcs":
            try:
                matches.append(int(fields[pid_idx]))
            except ValueError:
                continue
    return tuple(sorted(set(matches)))


def read_process_identity(reader: FixedAdb, pid: int, *, capture: "Capture | None" = None,
                          phase: str = "baseline", label: str = "identity") -> ProcessIdentity:
    if pid <= 0:
        raise SafetyStop("invalid jmcs PID")
    raw_results = []
    for op, arg, max_bytes in (("read", f"/proc/{pid}/stat", 64 * 1024),
                               ("read", f"/proc/{pid}/status", 256 * 1024),
                               ("read", f"/proc/{pid}/cmdline", 64 * 1024)):
        code, out, err = reader.run(op, arg, max_bytes=max_bytes)
        raw_results.append((op, arg, code, out, err))
    stat_raw, status_raw, cmd_raw = (item[3] for item in raw_results)
    if capture:
        for index, (op, arg, code, out, err) in enumerate(raw_results):
            capture.record_result(phase, "identity", f"{label}_{pid}_{index}_{Path(arg).name}",
                                  op, arg, code, out, err, pid=pid)
    if any(item[2] != 0 for item in raw_results):
        raise SafetyStop(f"identity read failed for PID {pid}")
    status = parse_status(status_raw.decode("utf-8", "replace"))
    status_name = status.get("Name", "").strip()
    cmdline = _decode_cmdline(cmd_raw)
    argv0 = cmd_raw.split(b"\x00", 1)[0].decode("utf-8", "replace").strip()
    if status_name != "jmcs" or Path(argv0.removesuffix(" (deleted)")).name != "jmcs":
        raise SafetyStop(f"PID {pid} comm/cmdline identity is not jmcs")
    # This API-17 build does not expose /proc/PID/exe through toolbox ls.
    # Preserve that result as NOT_EXPOSED and use independent status+cmdline
    # identity fields, plus PID/start time consistency checks, for discovery.
    exe = argv0
    try:
        uid = status["Uid"].split()[0]
        gid = status["Gid"].split()[0]
        status_pid = int(status["Pid"])
        ppid = status.get("PPid", "")
        start = parse_proc_stat_start_time(stat_raw.decode("utf-8", "replace"))
    except (KeyError, ValueError, IndexError) as exc:
        raise SafetyStop("jmcs identity fields are incomplete") from exc
    if status_pid != pid:
        raise SafetyStop("PID changed during identity read")
    return ProcessIdentity(pid, start, exe, cmdline, uid, gid, ppid)


def discover_process(reader: FixedAdb, *, capture: "Capture | None" = None,
                     phase: str = "baseline", label: str = "discover") -> ProcessIdentity:
    code, ps_raw, ps_err = reader.run("ps", max_bytes=2 * 1024 * 1024)
    if capture:
        capture.record_result(phase, "identity", f"{label}_ps", "ps", (), code, ps_raw, ps_err)
    if code != 0:
        raise SafetyStop("ps command failed while locating jmcs")
    pids = parse_ps_jmcs(ps_raw.decode("utf-8", "replace"))
    if len(pids) != 1:
        raise SafetyStop(f"expected exactly one jmcs process in ps, found {len(pids)}")
    before = read_process_identity(reader, pids[0], capture=capture, phase=phase, label=f"{label}_first")
    after = read_process_identity(reader, pids[0], capture=capture, phase=phase, label=f"{label}_confirm")
    if before != after:
        raise SafetyStop("jmcs process instance changed while establishing identity")
    return before


class Capture:
    def __init__(self, reader: FixedAdb, output: Path):
        self.reader = reader
        self.output = output
        self.started_utc = datetime.now(timezone.utc).isoformat()
        self.files: list[dict[str, Any]] = []
        self.phase_identities: dict[str, ProcessIdentity] = {}
        self.phase_times: dict[str, dict[str, str]] = {}
        self.stop_result: str | None = None

    def store(self, phase: str, category: str, name: str, operation: str,
              *args: str, timeout: int = COMMAND_TIMEOUT,
              max_bytes: int = MAX_COMMAND_OUTPUT, pid: int | None = None) -> tuple[int, bytes]:
        code, out, err = self.reader.run(operation, *args, timeout=timeout, max_bytes=max_bytes)
        self.record_result(phase, category, name, operation, args, code, out, err, pid=pid)
        return code, out

    def record_result(self, phase: str, category: str, name: str, operation: str,
                      args: Any, code: int, out: bytes, err: bytes,
                      *, pid: int | None = None) -> None:
        relative = Path(phase) / category / f"{name}.raw"
        target = self.output / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.write_bytes(out)
        target.chmod(0o600)
        err_name = None
        if err:
            err_path = target.with_suffix(".stderr.raw")
            err_path.write_bytes(err)
            err_path.chmod(0o600)
            err_name = str(err_path.relative_to(self.output))
            self.files.append({"path": err_name, "size": len(err),
                               "sha256": hashlib.sha256(err).hexdigest(),
                               "kind": "stderr", "pid": pid})
        self.files.append({"path": str(relative), "size": len(out),
                           "sha256": hashlib.sha256(out).hexdigest(),
                           "kind": "stdout", "pid": pid, "exit_code": code,
                           "operation": operation,
                           "arguments": [args] if isinstance(args, str) else list(args)})

    def assert_same_instance(self, expected: ProcessIdentity) -> None:
        current = discover_process(self.reader, capture=self, phase="identity-check",
                                   label=f"check_{expected.pid}_{datetime.now().strftime('%H%M%S%f')}")
        if current != expected:
            raise SafetyStop(f"jmcs instance changed during critical snapshot: {expected} -> {current}")

    def collect_identity_environment(self, phase: str) -> None:
        for operation, args, name, timeout, maximum in (
                ("id", (), "effective-shell-identity", 5, 64 * 1024),
                ("uname", (), "uname", 5, 64 * 1024),
                ("service-list", (), "service-list", 10, 1024 * 1024)):
            self.store(phase, "platform", name, operation, *args, timeout=timeout, max_bytes=maximum)
        self.store(phase, "platform", "jmcs_file_sha256", "hash-jmcs", timeout=10, max_bytes=64 * 1024)
        self.store(phase, "platform", "jmcs_file_metadata", "ls-jmcs", timeout=5, max_bytes=64 * 1024)
        for path in sorted(STATIC_READ_PATHS):
            safe_name = path.strip("/").replace("/", "_")
            self.store(phase, "platform", safe_name, "read", path,
                       timeout=10, max_bytes=8 * 1024 * 1024)
        for prop in SAFE_PROPERTIES:
            self.store(phase, "properties", prop.replace(".", "_"), "property", prop,
                       timeout=5, max_bytes=64 * 1024)
        self._capture_cpu_topology(phase)
        for service in SAFE_DUMPSYS:
            self.store(phase, "display", f"dumpsys_{service.replace('/', '_')}", "dumpsys", service,
                       timeout=15, max_bytes=4 * 1024 * 1024)
        self.store(phase, "logs", "logcat_tail", "logcat", timeout=15, max_bytes=4 * 1024 * 1024)

    def verify_target_identity(self) -> dict[str, str]:
        sources = (
            ("kernel_version", "read", "/proc/version", "3.1.10+"),
            ("android_release", "property", "ro.build.version.release", EXPECTED_ANDROID_RELEASE),
            ("android_sdk", "property", "ro.build.version.sdk", EXPECTED_ANDROID_SDK),
            ("device", "property", "ro.product.device", EXPECTED_PRODUCT_DEVICE),
            ("board", "property", "ro.product.board", EXPECTED_PRODUCT_BOARD),
            ("hardware", "property", "ro.hardware", EXPECTED_HARDWARE),
        )
        values: dict[str, str] = {}
        for name, operation, argument, expected in sources:
            code, raw = (self.store("preflight", "identity", name, operation, argument,
                                    timeout=5, max_bytes=64 * 1024))
            value = raw.decode("utf-8", "replace").strip()
            values[name] = value
            if code != 0:
                raise SafetyStop(f"required target identity source unavailable: {name}")
            matches = "3.1.10+" in value if name == "kernel_version" else value == expected
            if not matches:
                raise SafetyStop(f"target identity mismatch for {name}: expected {expected!r}, got {value!r}")
        if not values["kernel_version"].startswith("Linux version 3.1.10+"):
            raise SafetyStop("target kernel release does not match the known 3.1.10+ platform")
        return values

    def _capture_cpu_topology(self, phase: str) -> None:
        _, listing = self.store(phase, "cpu", "cpu_directory_listing", "list",
                                "/sys/devices/system/cpu", timeout=5, max_bytes=256 * 1024)
        cpu_names = sorted(set(re.findall(r"\bcpu[0-9]+\b", listing.decode("utf-8", "replace"))))
        for cpu in cpu_names:
            _, cache_listing = self.store(phase, "cpu", f"{cpu}_cache_listing", "list",
                                          f"/sys/devices/system/cpu/{cpu}/cache", timeout=5,
                                          max_bytes=256 * 1024)
            indexes = sorted(set(re.findall(r"\bindex[0-9]+\b", cache_listing.decode("utf-8", "replace"))))
            leaves = ["topology/core_id", "topology/physical_package_id",
                      "topology/thread_siblings_list"]
            for index in indexes:
                leaves.extend((f"cache/{index}/level", f"cache/{index}/type", f"cache/{index}/size",
                               f"cache/{index}/coherency_line_size", f"cache/{index}/number_of_sets",
                               f"cache/{index}/ways_of_associativity", f"cache/{index}/shared_cpu_list",
                               f"cache/{index}/shared_cpu_map"))
            for leaf in leaves:
                path = f"/sys/devices/system/cpu/{cpu}/{leaf}"
                self.store(phase, "cpu", f"{cpu}_{leaf.replace('/', '_')}", "read", path,
                           timeout=5, max_bytes=64 * 1024)

    def collect_connected_diagnostics(self) -> None:
        for service in SAFE_DUMPSYS:
            self.store("connected", "display", f"dumpsys_{service.replace('/', '_')}",
                       "dumpsys", service, timeout=15, max_bytes=4 * 1024 * 1024)
        self.store("connected", "logs", "logcat_tail", "logcat", timeout=15,
                   max_bytes=4 * 1024 * 1024)

    def _capture_thread_snapshot(self, phase: str, identity: ProcessIdentity, index: int) -> None:
        pid = identity.pid
        self.assert_same_instance(identity)
        _, listing = self.store(phase, "threads", f"snapshot_{index:02d}_task_listing", "list",
                                f"/proc/{pid}/task", timeout=5, max_bytes=256 * 1024, pid=pid)
        tids = parse_task_listing(listing.decode("utf-8", "replace"))
        for tid in tids:
            for leaf in ("comm", "status", "stat", "wchan"):
                path = f"/proc/{pid}/task/{tid}/{leaf}"
                self.store(phase, "threads", f"snapshot_{index:02d}_tid_{tid}_{leaf}",
                           "read", path, timeout=5, max_bytes=256 * 1024, pid=pid)
        self.assert_same_instance(identity)

    def collect_process_phase(self, phase: str, full: bool) -> ProcessIdentity:
        self.phase_times[phase] = {"started_utc": datetime.now(timezone.utc).isoformat()}
        identity = discover_process(self.reader, capture=self, phase=phase, label="initial")
        self.phase_identities[phase] = identity
        pid = identity.pid
        if full:
            self.collect_identity_environment(phase)
        paths = ("cmdline", "stat", "statm", "status", "limits", "maps", "smaps",
                 "wchan", "mounts", "mountinfo")
        self.assert_same_instance(identity)
        for leaf in paths:
            self.store(phase, "process", leaf, "read", f"/proc/{pid}/{leaf}",
                       timeout=20 if leaf == "smaps" else 10,
                       max_bytes=16 * 1024 * 1024 if leaf == "smaps" else 4 * 1024 * 1024,
                       pid=pid)
        for leaf in ("exe", "cwd", "root"):
            self.store(phase, "process", f"readlink_{leaf}", "readlink", f"/proc/{pid}/{leaf}",
                       timeout=5, max_bytes=64 * 1024, pid=pid)
        for directory in ("fd",):
            self.store(phase, "process", f"{directory}_links", "list", f"/proc/{pid}/{directory}",
                       timeout=10, max_bytes=2 * 1024 * 1024, pid=pid)
        fd_listing = next((entry for entry in reversed(self.files)
                           if entry["path"].endswith("fd_links.raw")), None)
        if fd_listing:
            try:
                raw = (self.output / fd_listing["path"]).read_text(errors="replace")
                fds = sorted(set(int(item) for item in raw.split() if item.isdecimal()))
            except OSError:
                fds = []
            for fd in fds:
                self.store(phase, "process", f"fd_{fd}_target", "readlink", f"/proc/{pid}/fd/{fd}",
                           timeout=5, max_bytes=64 * 1024, pid=pid)
        _, task_listing = self.store(phase, "threads", "task_listing", "list",
                                     f"/proc/{pid}/task", timeout=5, max_bytes=256 * 1024, pid=pid)
        try:
            tids = parse_task_listing(task_listing.decode("utf-8", "replace"))
        except ValueError:
            tids = ()
        for tid in tids:
            for leaf in ("comm", "status", "stat", "wchan"):
                self.store(phase, "threads", f"tid_{tid}_{leaf}", "read",
                           f"/proc/{pid}/task/{tid}/{leaf}", timeout=5,
                           max_bytes=256 * 1024, pid=pid)
        self.store(phase, "network", "unix", "read", "/proc/net/unix", timeout=10,
                   max_bytes=2 * 1024 * 1024, pid=pid)
        for filename, path in (("tcp4", "/proc/net/tcp"), ("tcp6", "/proc/net/tcp6"),
                               ("udp4", "/proc/net/udp"), ("udp6", "/proc/net/udp6")):
            self.store(phase, "network", filename, "read", path, timeout=10,
                       max_bytes=2 * 1024 * 1024, pid=pid)
        self.assert_same_instance(identity)
        for index in range(THREAD_SNAPSHOTS):
            self._capture_thread_snapshot(phase, identity, index)
            if index + 1 < THREAD_SNAPSHOTS:
                time.sleep(THREAD_INTERVAL_SECONDS)
        self.assert_same_instance(identity)
        self.phase_times[phase]["finished_utc"] = datetime.now(timezone.utc).isoformat()
        return identity

    def finalize(self, phase_order: list[str]) -> None:
        manifest = {
            "capture_id": self.output.name,
            "capture_started_utc": self.started_utc,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "adb_serial": self.reader.serial,
            "phase_order": phase_order,
            "phase_times": self.phase_times,
            "process_identities": {name: asdict(identity) for name, identity in self.phase_identities.items()},
            "target_identity": getattr(self, "target_identity", None),
            "privileged_mode": bool(getattr(self, "privileged_mode", False)),
            "artifacts": self.files,
            "commands": self.reader.records,
            "stop_result": self.stop_result,
            "guarantees": ["fixed allowlist only", "no target file writes", "no helper upload/execution",
                           "no ptrace", "no /proc/PID/mem", "no signals or thread suspension"],
        }
        manifest_path = self.output / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        manifest_path.chmod(0o600)
        entries = []
        for path in sorted(self.output.rglob("*")):
            if path.is_file() and path.name != "sha256.txt":
                entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(self.output)}")
        hash_path = self.output / "sha256.txt"
        hash_path.write_text("\n".join(entries) + "\n")
        hash_path.chmod(0o600)
        self.output.chmod(0o700)


def dry_run(reader: FixedAdb) -> None:
    fixed = [("id", ()), ("uname", ()), ("ps", ()), ("service-list", ()),
             ("hash-jmcs", ()), ("ls-jmcs", ())]
    fixed.extend(("read", (path,)) for path in sorted(STATIC_READ_PATHS))
    fixed.extend(("property", (prop,)) for prop in SAFE_PROPERTIES)
    fixed.extend(("dumpsys", (service,)) for service in SAFE_DUMPSYS)
    fixed.append(("logcat", ()))
    for op, args in fixed:
        print(reader.dry_run_command(op, *args))
    pid = "1234"
    process_leaves = ("cmdline", "stat", "statm", "status", "limits", "maps", "smaps",
                      "wchan", "mounts", "mountinfo", "task", "fd")
    for leaf in process_leaves:
        op = "list" if leaf in ("task", "fd") else "read"
        print("# PID template")
        print(reader.dry_run_command(op, f"/proc/{pid}/{leaf}"))
    for leaf in ("exe", "cwd", "root"):
        print(reader.dry_run_command("readlink", f"/proc/{pid}/{leaf}"))
    for fd in ("0",):
        print("# FD template")
        print(reader.dry_run_command("readlink", f"/proc/{pid}/fd/{fd}"))
    print(reader.dry_run_command("list", f"/proc/{pid}/task"))
    for leaf in ("comm", "status", "stat", "wchan"):
        print("# TID template")
        print(reader.dry_run_command("read", f"/proc/{pid}/task/{pid}/{leaf}"))
    print(reader.dry_run_command("list", "/sys/devices/system/cpu"))
    print(reader.dry_run_command("list", "/sys/devices/system/cpu/cpu0/cache"))
    for leaf in ("topology/core_id", "topology/physical_package_id",
                 "topology/thread_siblings_list", "cache/index0/level", "cache/index0/type",
                 "cache/index0/size", "cache/index0/coherency_line_size",
                 "cache/index0/number_of_sets", "cache/index0/ways_of_associativity",
                 "cache/index0/shared_cpu_list", "cache/index0/shared_cpu_map"):
        print(reader.dry_run_command("read", f"/sys/devices/system/cpu/cpu0/{leaf}"))
    for service in SAFE_DUMPSYS:
        print(f"# Bounded read-only diagnostic: dumpsys {service}")
    print("# Thread series repeats the fixed TID template 5 times with a 2-second interval.")
    print("# No command has been sent; dry-run performs no ADB device query and creates no files.")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", default="auto",
                        help="explicit existing ADB serial or auto (requires exactly one authorized device)")
    parser.add_argument("--phase", choices=("all", "baseline", "connected", "post-disconnect"), default="all",
                        help="all phases; baseline only; baseline+connected; or all through post-disconnect")
    parser.add_argument("--output-root", type=Path, default=Path.home())
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--vehicle-parked-confirmed", action="store_true")
    parser.add_argument("--iphone-disconnected-confirmed", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    if args.dry_run:
        if not args.serial:
            print("--serial SERIAL is required even for dry-run so commands are explicit", file=sys.stderr)
            return 2
        dry_run(FixedAdb(args.serial, resolve_auto=False))
        return 0
    if not args.serial:
        print("refusing: live collection requires explicit --serial", file=sys.stderr)
        return 2
    if not args.vehicle_parked_confirmed or not args.iphone_disconnected_confirmed:
        print("refusing: confirm --vehicle-parked-confirmed and --iphone-disconnected-confirmed", file=sys.stderr)
        return 2
    output_root = args.output_root.expanduser().resolve()
    try:
        output_root.relative_to(REPO_ROOT)
    except ValueError:
        pass
    else:
        print("refusing: raw capture output must be outside the Git worktree", file=sys.stderr)
        return 2
    capture_id = "CLARITY_RUNTIME_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    output = output_root / capture_id
    if output.exists():
        print("refusing: capture output already exists", file=sys.stderr)
        return 2
    try:
        reader = FixedAdb(args.serial)
    except (SafetyStop, ValueError) as exc:
        print(f"refusing: {exc}", file=sys.stderr)
        return 1
    output.mkdir(mode=0o700, parents=True)
    capture = Capture(reader, output)
    phases: list[str] = []
    try:
        target_identity = capture.verify_target_identity()
        print(f"Read-only target fingerprint passed: Android={target_identity['android_release']} "
              f"API={target_identity['android_sdk']}, board={target_identity['board']}, "
              f"device={target_identity['device']}, kernel=3.1.10 family.")
        identity = capture.collect_process_phase("baseline", full=True)
        phases.append("baseline")
        print(f"Baseline captured; process instance PID {identity.pid}, start time {identity.start_time_ticks}.")
        if args.phase in ("all", "connected", "post-disconnect"):
            input("Connect the iPhone normally and establish STOCK CarPlay, then press Enter (no ClarityLink/Type111): ")
            identity = capture.collect_process_phase("connected", full=False)
            phases.append("connected")
            capture.collect_connected_diagnostics()
            print(f"Stock-connected phase captured for PID {identity.pid}.")
            try_maps = input("Optional snapshot: is ordinary CarPlay Apple Maps open on the stock center screen? [y/N] ").strip().lower()
            if try_maps in ("y", "yes"):
                capture.assert_same_instance(identity)
                phases.append("connected_maps")
                capture.store("connected_maps", "snapshot", "task_listing", "list",
                              f"/proc/{identity.pid}/task", timeout=5, max_bytes=256 * 1024, pid=identity.pid)
                capture.store("connected_maps", "snapshot", "fd_links", "list",
                              f"/proc/{identity.pid}/fd", timeout=10, max_bytes=2 * 1024 * 1024, pid=identity.pid)
                capture.store("connected_maps", "snapshot", "tcp4", "read", "/proc/net/tcp",
                              timeout=10, max_bytes=2 * 1024 * 1024, pid=identity.pid)
                capture.store("connected_maps", "snapshot", "display", "dumpsys", "display",
                              timeout=15, max_bytes=4 * 1024 * 1024, pid=identity.pid)
                capture.assert_same_instance(identity)
        if args.phase in ("all", "post-disconnect"):
            input("Disconnect normal CarPlay through the ordinary user flow; do not kill processes. Press Enter when settled: ")
            identity = capture.collect_process_phase("post-disconnect", full=False)
            phases.append("post-disconnect")
        capture.finalize(phases)
        print(f"Capture finalized on host: {output}")
        print("==============================================")
        print("CAPTURE COMPLETE — YOU CAN TURN THE CAR OFF NOW")
        print("==============================================")
        return 0
    except (Exception, KeyboardInterrupt, EOFError) as exc:
        capture.stop_result = classify_stop_reason(str(exc)).value
        try:
            capture.finalize(phases)
        except Exception as finalize_error:
            print(f"Host finalization issue recorded: {type(finalize_error).__name__}.", file=sys.stderr)
        print(f"STOPPED safely; completed phase evidence retained at {output}: {exc}", file=sys.stderr)
        print("==============================================", file=sys.stderr)
        print("CAPTURE STOPPED — YOU CAN TURN THE CAR OFF NOW", file=sys.stderr)
        print("==============================================", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
