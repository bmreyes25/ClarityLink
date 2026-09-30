"""Fixed-operation reads through the already installed Honda `su` facility.

This module never accepts a shell command. Every path is assembled from a
small enum plus validated numeric PID/TID/FD values. It is not permission to
run privileged commands during offline development.
"""

from __future__ import annotations

from enum import StrEnum
import re
import shlex
from typing import Any

from collector import FixedAdb, SafetyStop, COMMAND_TIMEOUT, MAX_COMMAND_OUTPUT


class PrivilegedOperation(StrEnum):
    IDENTITY = "identity"
    PS = "ps"
    PROCESS_READ = "process_read"
    THREAD_LIST = "thread_list"
    THREAD_READ = "thread_read"
    FD_LIST = "fd_list"
    FD_LINK = "fd_link"
    NETWORK_READ = "network_read"
    CONFIG_BASE64 = "config_base64"


PROCESS_LEAVES = frozenset(("cmdline", "stat", "statm", "status", "limits",
                            "maps", "smaps", "wchan", "mountinfo", "mounts",
                            "sched", "schedstat", "oom_score", "oom_score_adj", "cgroup"))
THREAD_LEAVES = frozenset(("comm", "status", "stat", "wchan"))
NETWORK_PATHS = {
    "tcp": "/proc/net/tcp", "tcp6": "/proc/net/tcp6",
    "udp": "/proc/net/udp", "udp6": "/proc/net/udp6", "unix": "/proc/net/unix",
}
EXPECTED_SU_SHA256 = "d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26"


def validate_su_fingerprint(hash_output: bytes, ls_output: bytes) -> None:
    """Refuse a changed or writable setuid binary before privileged execution."""
    digest = re.search(rb"\b([0-9a-fA-F]{64})\s+", hash_output)
    listing = ls_output.decode("utf-8", "replace").strip().split()
    if digest is None or digest.group(1).decode().lower() != EXPECTED_SU_SHA256:
        raise SafetyStop("installed su does not match the reviewed immutable firmware binary")
    if len(listing) < 3 or not listing[0].startswith("-") or len(listing[0]) < 10:
        raise SafetyStop("installed su mode/owner metadata was not readable")
    mode, owner, group = listing[:3]
    if owner != "root" or mode[3] != "s" or mode[5] == "w" or mode[8] == "w":
        raise SafetyStop("installed su is not root-owned with setuid and non-writable group/other permissions")


def _positive_decimal(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0 or value > 2_147_483_647:
        raise SafetyStop(f"{label} must be a positive 32-bit decimal integer")
    return value


class PrivilegedRead:
    """A privileged reader with an enumerated API and no arbitrary-command path."""

    def __init__(self, adb: FixedAdb):
        self.adb = adb
        self.serial = adb.serial
        self.records = adb.records

    def plan(self, operation: PrivilegedOperation, *, pid: int | None = None,
             tid: int | None = None, fd: int | None = None,
             leaf: str | None = None, table: str | None = None) -> tuple[str, ...]:
        if not isinstance(operation, PrivilegedOperation):
            raise SafetyStop("privileged operation must be an enum value")
        if operation is PrivilegedOperation.IDENTITY:
            remote = "id"
        elif operation is PrivilegedOperation.PS:
            remote = "ps"
        elif operation is PrivilegedOperation.PROCESS_READ:
            pid = _positive_decimal(pid, "PID")
            if leaf not in PROCESS_LEAVES:
                raise SafetyStop("process read leaf is not allowlisted")
            remote = f"cat /proc/{pid}/{leaf}"
        elif operation is PrivilegedOperation.THREAD_LIST:
            pid = _positive_decimal(pid, "PID")
            remote = f"ls /proc/{pid}/task"
        elif operation is PrivilegedOperation.THREAD_READ:
            pid = _positive_decimal(pid, "PID")
            tid = _positive_decimal(tid, "TID")
            if leaf not in THREAD_LEAVES:
                raise SafetyStop("thread read leaf is not allowlisted")
            remote = f"cat /proc/{pid}/task/{tid}/{leaf}"
        elif operation is PrivilegedOperation.FD_LIST:
            pid = _positive_decimal(pid, "PID")
            remote = f"ls -l /proc/{pid}/fd"
        elif operation is PrivilegedOperation.FD_LINK:
            pid = _positive_decimal(pid, "PID")
            fd = _positive_decimal(fd, "FD")
            remote = f"ls -l /proc/{pid}/fd/{fd}"
        elif operation is PrivilegedOperation.NETWORK_READ:
            if table not in NETWORK_PATHS:
                raise SafetyStop("network table is not allowlisted")
            remote = f"cat {NETWORK_PATHS[table]}"
        elif operation is PrivilegedOperation.CONFIG_BASE64:
            # Base64 avoids legacy adb shell newline conversion corrupting gzip.
            remote = "busybox base64 /proc/config.gz"
        else:  # pragma: no cover - exhaustive enum guard
            raise SafetyStop("privileged operation is not implemented")
        return (self.adb.adb, "-s", self.serial, "shell", "/system/xbin/su", "-c", remote)

    def dry_run_command(self, operation: PrivilegedOperation, **kwargs: Any) -> str:
        return shlex.join(self.plan(operation, **kwargs))

    def run(self, operation: PrivilegedOperation | str, *args: str,
            timeout: int = COMMAND_TIMEOUT, max_bytes: int = MAX_COMMAND_OUTPUT,
            **kwargs: Any) -> tuple[int, bytes, bytes]:
        """Reader-compatible fixed path API used by existing identity parsers."""
        if isinstance(operation, str):
            if operation == "id" and not args:
                operation = PrivilegedOperation.IDENTITY
            elif operation == "ps" and not args:
                operation = PrivilegedOperation.PS
            elif operation == "read" and len(args) == 1:
                path = args[0]
                process = re.fullmatch(r"/proc/([0-9]+)/([A-Za-z_]+)", path)
                thread = re.fullmatch(r"/proc/([0-9]+)/task/([0-9]+)/([A-Za-z_]+)", path)
                if process:
                    kwargs.update(pid=int(process.group(1)), leaf=process.group(2))
                    operation = PrivilegedOperation.PROCESS_READ
                elif thread:
                    kwargs.update(pid=int(thread.group(1)), tid=int(thread.group(2)), leaf=thread.group(3))
                    operation = PrivilegedOperation.THREAD_READ
                elif path in NETWORK_PATHS.values():
                    kwargs["table"] = next(k for k, v in NETWORK_PATHS.items() if v == path)
                    operation = PrivilegedOperation.NETWORK_READ
                else:
                    raise SafetyStop("privileged read path is not allowlisted")
            elif operation == "list" and len(args) == 1:
                match = re.fullmatch(r"/proc/([0-9]+)/(task|fd)", args[0])
                if not match:
                    raise SafetyStop("privileged directory listing is not allowlisted")
                kwargs["pid"] = int(match.group(1))
                operation = (PrivilegedOperation.THREAD_LIST if match.group(2) == "task"
                             else PrivilegedOperation.FD_LIST)
            elif operation == "readlink" and len(args) == 1:
                match = re.fullmatch(r"/proc/([0-9]+)/fd/([0-9]+)", args[0])
                if not match:
                    raise SafetyStop("privileged symlink listing is not allowlisted")
                kwargs.update(pid=int(match.group(1)), fd=int(match.group(2)))
                operation = PrivilegedOperation.FD_LINK
            else:
                raise SafetyStop("privileged operation is not allowlisted")
        if args:
            raise SafetyStop("unexpected positional arguments for privileged operation")
        command = self.plan(operation, **kwargs)
        safe_args = {key: value for key, value in kwargs.items() if value is not None}
        return self.adb._run_planned(command, f"privileged_{operation.value}",
                                     tuple(f"{key}={value}" for key, value in sorted(safe_args.items())),
                                     timeout=timeout, max_bytes=max_bytes)

    def verify_root(self) -> tuple[int, bytes, bytes]:
        code, stdout, stderr = self.run(PrivilegedOperation.IDENTITY, timeout=5,
                                       max_bytes=16 * 1024)
        text = (stdout + b"\n" + stderr).decode("utf-8", "replace")
        match = re.search(r"(?:^|\s)uid=(\d+)(?:\([^)]*\))?(?:\s|$)", text)
        if code != 0 or match is None or match.group(1) != "0":
            raise SafetyStop("existing su identity check did not return exactly UID 0")
        return code, stdout, stderr


def decode_config_base64(raw: bytes) -> bytes:
    import base64
    try:
        encoded = re.sub(rb"\s+", b"", raw)
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise SafetyStop("optional kernel config response was not valid base64") from exc
    if not decoded.startswith(b"\x1f\x8b"):
        raise SafetyStop("optional kernel config response was not gzip data")
    return decoded
