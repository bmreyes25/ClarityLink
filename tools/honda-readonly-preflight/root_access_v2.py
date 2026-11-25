"""CL-HONDA-ROOT-ACCESS-V2 fixed diagnostic runner and legacy-su assessment.

This runner uses one exact, already-authorized ADB serial and a fixed operation
enum. It does not scan devices, accept arbitrary shell text, retry, or modify
the receiver. A successful local readiness check is not live authorization.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import time
import uuid

from collector import (FixedAdb, SafetyStop, parse_ps_jmcs,
                       parse_ls_symlink_target,
                       EXPECTED_PRODUCT_DEVICE, EXPECTED_ANDROID_RELEASE,
                       EXPECTED_ANDROID_SDK, EXPECTED_PRODUCT_BOARD,
                       EXPECTED_HARDWARE, REPO_ROOT)
from root_integrity_preflight import (EXPECTED_SU_PATH, EXPECTED_SU_SIZE,
                                      EXPECTED_SU_SHA256, covering_mount,
                                      parse_ls_numeric, parse_api17_ls_numeric_line)
from parsers import parse_proc_stat_start_time

SCHEMA = "claritylink-honda-root-access-authorization-v2.1"
CAMPAIGN = "CL-HONDA-ROOT-ACCESS-V2"
PROFILE_REVISION = "2.1"
HERE = Path(__file__).resolve().parent
PROFILE_PATH = HERE / "root_access_v2_profile.json"
SOURCE_LOCK_PATH = HERE / "root_access_v2_source_lock.json"
MAX_SECONDS = 900
MAX_OUTPUT = 12 * 1024 * 1024
MAX_COMMANDS = 141
MAX_FDS = 192
PROCESS_LEAVES = frozenset({"stat", "status", "cmdline", "maps"})
NETWORK_TABLES = {"tcp": "/proc/net/tcp", "tcp6": "/proc/net/tcp6",
                  "udp": "/proc/net/udp", "udp6": "/proc/net/udp6",
                  "unix": "/proc/net/unix"}
EXPECTED_ROOT_RISK = "I accept that this SuperSU invocation may prompt, start or contact a daemon, update policy/request/log state, and cause target-side persistent writes."
V2_TARGET_IDENTITY = {
    "ro.product.model": "MY16ADA",
    "ro.build.version.release": EXPECTED_ANDROID_RELEASE,
    "ro.build.version.sdk": EXPECTED_ANDROID_SDK,
    "ro.product.device": EXPECTED_PRODUCT_DEVICE,
    "ro.product.board": EXPECTED_PRODUCT_BOARD,
    "ro.hardware": EXPECTED_HARDWARE,
}


class V2Stop(RuntimeError):
    pass


def _mode_bits(mode_text: str) -> int:
    if not isinstance(mode_text, str) or not re.fullmatch(r"0o[0-7]{4}", mode_text):
        raise V2Stop("legacy-su mode is not a parsed four-digit octal value")
    return int(mode_text, 8)


def parse_su_digest(raw: bytes) -> str:
    match = re.fullmatch(rb"([0-9a-fA-F]{64})\s+/system/xbin/su\s*", raw)
    if not match:
        raise V2Stop("su digest output did not identify exactly /system/xbin/su")
    return match.group(1).decode("ascii").lower()


def parse_su_path_chain(raw: bytes) -> dict[str, tuple[int, int, int]]:
    """Parse exact `ls -ldn` results and reject links or substituted paths."""
    expected = ("/", "/system", "/system/xbin", EXPECTED_SU_PATH)
    expected_names = ("", "system", "xbin", "su")
    rows = [line for line in raw.splitlines() if line.strip()]
    if len(rows) != len(expected):
        raise V2Stop("su path chain metadata is incomplete")
    result: dict[str, tuple[int, int, int]] = {}
    for path, name, row in zip(expected, expected_names, rows):
        if b" -> " in row:
            raise V2Stop("su path contains a symlink")
        metadata = parse_api17_ls_numeric_line(row, expected_name=name)
        if (metadata["file_type"] != "regular" if path == EXPECTED_SU_PATH
                else metadata["file_type"] != "directory"):
            raise V2Stop("su path has an unexpected filesystem object type")
        result[path] = (int(metadata["uid"]), int(metadata["gid"]),
                        int(str(metadata["mode_octal"]), 8))
    if any(uid != 0 for uid, _gid, _mode in result.values()):
        raise V2Stop("su path is not root-owned throughout")
    return result


def assess_legacy_su(metadata: dict, digest: str, size: int,
                     mount: dict, resolved_path: str,
                     parent_modes: dict[str, tuple[int, int, int]]) -> dict:
    """Assess actual path/mount protection without equating hash with integrity.

    parent_modes maps each fixed path component to (uid, gid, mode). A `ro`
    covering mount is required; writable or uncertain path components fail.
    The historical 06777 mode remains an explicit risk in every accepted result.
    """
    risks = ["archived mode 06777 grants write bits to group and other",
             "setuid/setgid executable can elevate the invoking shell",
             "SuperSU may prompt, start/contact a daemon, update policy/request state, or log"]
    if metadata.get("file_type") != "regular" or metadata.get("uid") != 0 or metadata.get("gid") != 0:
        return {"eligible": False, "status": "REJECT_FILE_TYPE_OR_OWNER", "risks": risks}
    mode = _mode_bits(str(metadata.get("mode_octal", "")))
    if mode != 0o6777 or not metadata.get("setuid") or not metadata.get("setgid"):
        return {"eligible": False, "status": "REJECT_MODE_DIFFERS_FROM_ARCHIVE", "risks": risks,
                "observed_mode_octal": f"0o{mode:04o}"}
    if digest != EXPECTED_SU_SHA256 or size != EXPECTED_SU_SIZE or metadata.get("size_bytes") != EXPECTED_SU_SIZE:
        return {"eligible": False, "status": "REJECT_EXECUTABLE_IDENTITY_MISMATCH", "risks": risks}
    if resolved_path != EXPECTED_SU_PATH:
        return {"eligible": False, "status": "REJECT_PATH_OR_SYMLINK_MISMATCH", "risks": risks,
                "resolved_path": resolved_path}
    if not mount.get("complete") or mount.get("read_only") is not True or mount.get("overlay_uncertainty"):
        return {"eligible": False, "status": "REJECT_MOUNT_NOT_PROVEN_READ_ONLY", "risks": risks}
    for path in ("/", "/system", "/system/xbin"):
        item = parent_modes.get(path)
        if not item or len(item) != 3:
            return {"eligible": False, "status": "REJECT_PARENT_METADATA_INCOMPLETE", "risks": risks}
        uid, gid, bits = item
        if bits & 0o022:
            return {"eligible": False, "status": "REJECT_UNPRIVILEGED_REPLACEMENT_POSSIBLE", "risks": risks,
                    "writable_parent": path}
        if uid != 0:
            return {"eligible": False, "status": "REJECT_PARENT_OWNER_MISMATCH", "risks": risks,
                    "unexpected_parent": path}
    return {"eligible": True, "status": "ELIGIBLE_FOR_EXACT_OWNER_APPROVED_SESSION_ONLY",
            "observed_mode_octal": "0o6777", "risk_severity": "HIGH_ACCEPTED_RESIDUAL",
            "risks": risks,
            "integrity_limit": "hash/path/mount checks reduce replacement risk but do not prove race-free immutable execution or zero-write su behavior"}


def fixed_root_argv(serial: str, operation: str, *, pid: int | None = None,
                    leaf: str | None = None, table: str | None = None) -> tuple[str, ...]:
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", serial) or serial.lower() == "auto":
        raise V2Stop("exact ADB endpoint required")
    if operation == "identity":
        remote = "id"
    elif operation == "ps":
        remote = "ps"
    elif operation == "process":
        if type(pid) is not int or not (1 <= pid <= 2_147_483_647) or leaf not in PROCESS_LEAVES:
            raise V2Stop("process path is outside the fixed PID/leaf allowlist")
        remote = f"cat /proc/{pid}/{leaf}"
    elif operation == "exe":
        if type(pid) is not int or not (1 <= pid <= 2_147_483_647):
            raise V2Stop("invalid process id for executable link")
        remote = f"ls -l /proc/{pid}/exe"
    elif operation == "fds":
        if type(pid) is not int or not (1 <= pid <= 2_147_483_647):
            raise V2Stop("invalid process id for descriptor listing")
        remote = f"ls -l /proc/{pid}/fd"
    elif operation == "network":
        if table not in NETWORK_TABLES:
            raise V2Stop("network table is outside the fixed allowlist")
        remote = f"cat {NETWORK_TABLES[table]}"
    else:
        raise V2Stop("root operation is outside the fixed allowlist")
    return ("adb", "-s", serial, "shell", EXPECTED_SU_PATH, "-c", remote)


def source_binding() -> tuple[str, str]:
    """Validate every V2 source pin and return current lock/profile digests."""
    if PROFILE_PATH.is_symlink() or SOURCE_LOCK_PATH.is_symlink():
        raise V2Stop("V2 profile/source lock cannot be a symlink")
    try:
        profile_raw = PROFILE_PATH.read_bytes()
        profile = json.loads(profile_raw.decode("utf-8"))
        lock = json.loads(SOURCE_LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise V2Stop("V2 profile/source lock is unavailable or malformed") from exc
    expected_files = {"root_access_v2.py", "root_access_v2_profile.json",
                      "collector.py", "root_integrity_preflight.py", "parsers.py",
                      "privileged.py"}
    if not isinstance(lock, dict) or set(lock) != expected_files:
        raise V2Stop("V2 source lock file set changed")
    if (profile.get("schema") != "claritylink-honda-root-access-profile-v2.1"
            or profile.get("campaign") != CAMPAIGN
            or profile.get("revision") != PROFILE_REVISION
            or profile.get("target", {}).get("model") != "MY16ADA"
            or profile.get("target", {}).get("android_release") != EXPECTED_ANDROID_RELEASE
            or profile.get("target", {}).get("android_sdk") != EXPECTED_ANDROID_SDK
            or profile.get("target", {}).get("product_device") != EXPECTED_PRODUCT_DEVICE
            or profile.get("target", {}).get("product_board") != EXPECTED_PRODUCT_BOARD
            or profile.get("target", {}).get("hardware") != EXPECTED_HARDWARE
            or profile.get("legacy_su", {}).get("path") != EXPECTED_SU_PATH
            or profile.get("legacy_su", {}).get("sha256") != EXPECTED_SU_SHA256
            or profile.get("legacy_su", {}).get("archived_mode_octal") != "06777"
            or profile.get("legacy_su", {}).get("archived_size_bytes") != EXPECTED_SU_SIZE
            or profile.get("phases") != ["disconnected_baseline",
                                          "normal_stock_carplay_connected",
                                          "normal_post_disconnect"]
            or profile.get("fixed_root_operations") != [
                "id", "ps", "/proc/<jmcs-pid>/{stat,status,cmdline,exe,maps}",
                "/proc/<jmcs-pid>/fd listing", "/proc/net/{tcp,tcp6,udp,udp6,unix}"]
            or profile.get("fixed_unprivileged_operations") != [
                "exact target identity properties", "/proc/mounts", "su file and path-chain metadata",
                "dumpsys display", "dumpsys window", "dumpsys SurfaceFlinger",
                "dumpsys activity services", "/proc/net/dev"]
            or profile.get("limits", {}).get("active_session_seconds") != MAX_SECONDS
            or profile.get("limits", {}).get("commands") != MAX_COMMANDS
            or profile.get("limits", {}).get("command_budget_basis") != (
                "exact three-phase total: 24 identity + 16 su assessment + "
                "86 root/digest + 15 display/network = 141")
            or profile.get("limits", {}).get("combined_stdout_stderr_bytes") != MAX_OUTPUT
            or profile.get("limits", {}).get("per_command_seconds") != 10
            or profile.get("limits", {}).get("per_command_bytes") != 2 * 1024 * 1024
            or profile.get("limits", {}).get("max_jmcs_fd_rows") != MAX_FDS
            or profile.get("limits", {}).get("retry") is not False
            or profile.get("limits", {}).get("fallback") is not False):
        raise V2Stop("V2 profile does not match the reviewed fixed command contract")
    for name, expected in lock.items():
        path = HERE / name
        if path.is_symlink() or not path.is_file() or not re.fullmatch(r"[0-9a-f]{64}", str(expected)):
            raise V2Stop("V2 source lock contains an invalid entry")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise V2Stop("V2 source integrity mismatch: " + name)
    return hashlib.sha256(SOURCE_LOCK_PATH.read_bytes()).hexdigest(), hashlib.sha256(profile_raw).hexdigest()


def validate_authorization(value: object, *, endpoint: str, now: datetime | None = None,
                           source_lock_sha256: str | None = None,
                           profile_sha256: str | None = None) -> dict:
    if not isinstance(value, dict) or value.get("schema") != SCHEMA or value.get("campaign") != CAMPAIGN:
        raise V2Stop("authorization schema/campaign mismatch")
    if (not isinstance(endpoint, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", endpoint)
            or endpoint.startswith("OWNER_") or value.get("endpoint") != endpoint
            or value.get("target_properties") != V2_TARGET_IDENTITY):
        raise V2Stop("authorization endpoint or target identity mismatch")
    run_id = value.get("run_id")
    if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise V2Stop("authorization needs one fresh 128-bit run_id")
    if value.get("risk_acceptance") != EXPECTED_ROOT_RISK:
        raise V2Stop("specific SuperSU side-effect acceptance is missing")
    if value.get("scope") != ["root_process_socket_metadata", "normal_stock_carplay_transitions"]:
        raise V2Stop("authorization scope is not the fixed V2 diagnostic")
    allowed_fields = {"schema", "campaign", "endpoint", "target_properties", "run_id",
                      "risk_acceptance", "scope", "owner_approved", "parked",
                      "parking_brake_set", "owner_present", "approved_power_state",
                      "power_state", "factory_display_cluster_audio_normal", "expires_utc",
                      "source_lock_sha256", "profile_sha256"}
    if set(value) != allowed_fields:
        raise V2Stop("authorization contains missing or unrecognized fields")
    for flag in ("owner_approved", "parked", "parking_brake_set", "owner_present",
                 "approved_power_state", "factory_display_cluster_audio_normal"):
        if value.get(flag) is not True:
            raise V2Stop(f"owner authorization prerequisite missing: {flag}")
    if value.get("power_state") != "PARKED_ON_READY_ABSENT":
        raise V2Stop("V2 root diagnostics require the reviewed parked ON / READY-absent power state")
    if (source_lock_sha256 is not None and value.get("source_lock_sha256") != source_lock_sha256) or (
            profile_sha256 is not None and value.get("profile_sha256") != profile_sha256):
        raise V2Stop("authorization source/profile binding does not match the current reviewed files")
    expires = value.get("expires_utc")
    try:
        expiry = datetime.fromisoformat(expires.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise V2Stop("authorization expiry is invalid") from exc
    current = now or datetime.now(timezone.utc)
    if expiry.tzinfo is None or expiry <= current or (expiry - current).total_seconds() > MAX_SECONDS:
        raise V2Stop("authorization is expired or exceeds the 15-minute active-session bound")
    return value


def consume_run_id(run_id: str, ledger: Path) -> None:
    if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise V2Stop("ledger run ID must be one 128-bit lowercase hex token")
    ledger = ledger.expanduser().absolute()
    if ledger.is_symlink() or any(parent.is_symlink() for parent in ledger.parents):
        raise V2Stop("authorization ledger path ancestry cannot contain symlinks")
    if ledger == REPO_ROOT or REPO_ROOT in ledger.parents:
        raise V2Stop("authorization ledger must be outside the repository")
    ledger.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if stat.S_IMODE(ledger.parent.stat().st_mode) & 0o077:
        raise V2Stop("authorization ledger parent must be owner-only")
    try:
        fd = os.open(ledger, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise V2Stop("run-id ledger already exists; authorization replay refused")
    with os.fdopen(fd, "w", encoding="ascii") as output:
        output.write(run_id + "\n")
        output.flush()
        os.fsync(output.fileno())
    parent_fd = os.open(ledger.parent, os.O_RDONLY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def _read_auth(path: Path, endpoint: str) -> dict:
    candidate = path.expanduser().absolute()
    if (candidate == REPO_ROOT or REPO_ROOT in candidate.parents
            or candidate.is_symlink() or not candidate.is_file()
            or any(parent.is_symlink() for parent in candidate.parents)
            or stat.S_IMODE(candidate.stat().st_mode) != 0o600):
        raise V2Stop("authorization file must be a regular owner-only 0600 file")
    source_hash, profile_hash = source_binding()
    return validate_authorization(json.loads(path.read_text(encoding="utf-8")),
                                  endpoint=endpoint, source_lock_sha256=source_hash,
                                  profile_sha256=profile_hash)


def write_authorization_draft(path: Path, endpoint: str | None) -> Path:
    """Write a non-authorizing, non-expiring draft for completion at the car."""
    if endpoint is None:
        endpoint = "OWNER_FILL_EXACT_ALREADY_AUTHORIZED_ENDPOINT"
    elif (not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", endpoint)
          or endpoint.lower() == "auto"):
        raise V2Stop("draft endpoint must be exact or omitted; auto-selection is forbidden")
    requested = path.expanduser().absolute()
    if (requested == REPO_ROOT or REPO_ROOT in requested.parents
            or requested.exists() or requested.is_symlink()
            or not requested.parent.is_dir() or requested.parent.is_symlink()
            or any(parent.is_symlink() for parent in requested.parent.parents)
            or stat.S_IMODE(requested.parent.stat().st_mode) & 0o077):
        raise V2Stop("draft path must be new inside an existing owner-only directory outside Git")
    lock_hash, profile_hash = source_binding()
    draft = {
        "schema": SCHEMA, "campaign": CAMPAIGN, "endpoint": endpoint,
        "target_properties": V2_TARGET_IDENTITY, "run_id": uuid.uuid4().hex,
        "risk_acceptance": "", "scope": ["root_process_socket_metadata",
                                           "normal_stock_carplay_transitions"],
        "owner_approved": False, "parked": False, "parking_brake_set": False,
        "owner_present": False, "approved_power_state": False,
        "power_state": "",
        "factory_display_cluster_audio_normal": False,
        "expires_utc": None,
        "source_lock_sha256": lock_hash, "profile_sha256": profile_hash,
    }
    fd = os.open(requested, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(draft, stream, sort_keys=True, indent=2)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
    return requested


def _private_output(path: Path) -> Path:
    requested = path.expanduser()
    if requested.is_symlink():
        raise V2Stop("raw Honda evidence path cannot be a symlink")
    path = requested.absolute()
    if any(parent.is_symlink() for parent in (path.parent, *path.parent.parents)):
        raise V2Stop("raw Honda evidence directory ancestry cannot contain symlinks")
    if path == REPO_ROOT or REPO_ROOT in path.parents:
        raise V2Stop("raw Honda evidence must be stored outside Git")
    if (not path.parent.is_dir() or path.parent.is_symlink()
            or stat.S_IMODE(path.parent.stat().st_mode) & 0o077):
        raise V2Stop("evidence parent must be an existing owner-only directory")
    path.mkdir(mode=0o700, exist_ok=False)
    if stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise V2Stop("evidence directory is not owner-only")
    return path


class Session:
    def __init__(self, endpoint: str, output: Path, *, source_lock_sha256: str,
                 profile_sha256: str, expires_utc: str):
        self.endpoint = endpoint
        self.output = output
        self.started = time.monotonic()
        self.started_utc = datetime.now(timezone.utc).isoformat()
        self.commands = 0
        self.used = 0
        self.files: list[dict] = []
        self.adb = FixedAdb(endpoint, resolve_auto=False)
        self.process_binding: tuple[int, int] | None = None
        self.su_environment: dict | None = None
        self.expected_source_lock_sha256 = source_lock_sha256
        self.expected_profile_sha256 = profile_sha256
        self.authorization_expires_utc = expires_utc

    def _check_budget(self, *, next_bytes: int = 0) -> None:
        if time.monotonic() - self.started >= MAX_SECONDS:
            raise V2Stop("15-minute session bound reached")
        if self.commands >= MAX_COMMANDS or self.used + next_bytes > MAX_OUTPUT:
            raise V2Stop("session command/output budget exhausted")
        expires_text = getattr(self, "authorization_expires_utc", None)
        if expires_text:
            expiry = datetime.fromisoformat(expires_text.replace("Z", "+00:00"))
            if expiry.tzinfo is None or expiry <= datetime.now(timezone.utc):
                raise V2Stop("owner authorization expired during session")
        expected_lock = getattr(self, "expected_source_lock_sha256", None)
        expected_profile = getattr(self, "expected_profile_sha256", None)
        if expected_lock is not None and expected_profile is not None:
            current_lock, current_profile = source_binding()
            if current_lock != expected_lock or current_profile != expected_profile:
                raise V2Stop("V2 source/profile changed during session")

    def _ordinary(self, operation: str, *args: str, timeout: int = 5,
                  maximum: int = 128 * 1024) -> bytes:
        self._check_budget()
        code, out, err = self.adb.run(operation, *args, timeout=timeout,
                                      max_bytes=min(maximum, MAX_OUTPUT - self.used))
        self.commands += 1
        self.used += len(out) + len(err)
        if code == 124:
            raise V2Stop(f"unprivileged {operation} timed out; stop without retry")
        if code == 125:
            raise V2Stop(f"unprivileged {operation} exceeded its output ceiling; stop without retry")
        if code != 0 or self.used > MAX_OUTPUT or self.commands > MAX_COMMANDS:
            raise V2Stop(f"unprivileged {operation} failed or exceeded session bounds")
        self._persist("preflight", operation + "_" + str(self.commands), out, err)
        return out

    def verify_target(self) -> None:
        for prop, expected in V2_TARGET_IDENTITY.items():
            value = self._ordinary("property", prop).decode("utf-8", "replace").strip()
            if value != expected:
                raise V2Stop(f"target identity mismatch for {prop}")

    def assess_su(self) -> dict:
        """Re-read path, mount, mode and hash before first root use."""
        mount_raw = self._ordinary("read", "/proc/mounts")
        mount = covering_mount(mount_raw)
        metadata_raw = self._ordinary("ls-su-n")
        metadata = parse_ls_numeric(metadata_raw)
        digest_raw = self._ordinary("hash-su")
        digest = parse_su_digest(digest_raw)
        path_argv = (self.adb.adb, "-s", self.endpoint, "shell", "ls", "-ldn",
                     "/", "/system", "/system/xbin", EXPECTED_SU_PATH)
        paths_raw = self._ordinary_direct("su-path-chain", path_argv)
        path_modes = parse_su_path_chain(paths_raw)
        parent_modes = {path: path_modes[path] for path in ("/", "/system", "/system/xbin")}
        result = assess_legacy_su(metadata, digest, int(metadata["size_bytes"]),
                                  mount, EXPECTED_SU_PATH, parent_modes)
        if not result["eligible"]:
            raise V2Stop("legacy-su integrity assessment: " + result["status"])
        environment = {"digest": digest, "metadata": metadata,
                       "mount": mount, "resolved_path": EXPECTED_SU_PATH,
                       "parent_modes": parent_modes}
        if self.su_environment is None:
            self.su_environment = environment
        elif environment != self.su_environment:
            raise V2Stop("legacy-su mount/path/metadata differs from the reviewed baseline")
        result["observed_environment"] = environment
        return result

    def _ordinary_direct(self, name: str, argv: tuple[str, ...]) -> bytes:
        return self.call("preflight", name, argv, 5, 128 * 1024)

    def _validate_fixed_argv(self, argv: tuple[str, ...]) -> None:
        if (len(argv) < 5 or argv[0] != self.adb.adb
                or argv[1:4] != ("-s", self.endpoint, "shell")):
            raise V2Stop("command is not bound to the selected ADB executable and endpoint")
        remote = argv[4:]
        if remote[:2] == (EXPECTED_SU_PATH, "-c") and len(remote) in (3, 4):
            command = " ".join(remote[2:])
            if command in ("id", "ps"):
                return
            if re.fullmatch(r"cat /proc/[1-9][0-9]*/(stat|status|cmdline|maps)", command):
                return
            if re.fullmatch(r"ls -l /proc/[1-9][0-9]*/exe", command):
                return
            if re.fullmatch(r"ls -l /proc/[1-9][0-9]*/fd", command):
                return
            if command in {f"cat {path}" for path in NETWORK_TABLES.values()}:
                return
            raise V2Stop("privileged shell command is outside the fixed V2 manifest")
        if remote == ("ls", "-ldn", "/", "/system", "/system/xbin", EXPECTED_SU_PATH):
            return
        if remote == ("cat", "/proc/net/dev"):
            return
        allowed = {self.adb.plan("hash-su", ()), self.adb.plan("ls-su-n", ()),
                   self.adb.plan("read", ("/proc/mounts",))}
        if argv in allowed:
            return
        if any(argv == self.adb.plan("property", (prop,)) for prop in V2_TARGET_IDENTITY):
            return
        if any(argv == self.adb.plan("dumpsys", (service,))
               for service in ("display", "window", "SurfaceFlinger")):
            return
        if argv == self.adb.plan("dumpsys", ("activity", "services")):
            return
        raise V2Stop("operation is not in the fixed V2 ADB command manifest")

    def call(self, phase: str, name: str, argv: tuple[str, ...], timeout: int = 10,
             maximum: int = 512 * 1024) -> bytes:
        self._validate_fixed_argv(argv)
        self._check_budget()
        code, out, err = self.adb._run_planned(
            argv, name, (), timeout=timeout,
            max_bytes=min(maximum, MAX_OUTPUT - self.used))
        if len(out) + len(err) > min(maximum, MAX_OUTPUT - self.used):
            raise V2Stop("fixed diagnostic operation exceeded its output bound")
        self.commands += 1
        self.used += len(out) + len(err)
        rel = Path(phase) / (name + ".raw")
        path = self.output / rel
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(out)
        path.chmod(0o600)
        self.files.append({"path": str(rel), "sha256": hashlib.sha256(out).hexdigest(),
                           "bytes": len(out), "exit_code": code, "argv": list(argv)})
        if err:
            err_path = path.with_suffix(".stderr.raw")
            err_path.write_bytes(err)
            err_path.chmod(0o600)
            self.files.append({"path": str(err_path.relative_to(self.output)),
                               "sha256": hashlib.sha256(err).hexdigest(), "bytes": len(err),
                               "kind": "stderr"})
        if code == 124:
            raise V2Stop(f"fixed operation timed out in {phase}/{name}; no retry")
        if code == 125:
            raise V2Stop(f"fixed operation exceeded its output ceiling in {phase}/{name}; no retry")
        if code != 0:
            raise V2Stop(f"fixed operation failed in {phase}/{name}; no retry")
        return out

    def root(self, phase: str, name: str, operation: str, **kwargs) -> bytes:
        # Mount/path/mode are assessed once per phase. The digest is the final
        # target read before each individual privileged invocation.
        digest = self.call(phase, name + "_su_sha256", self.adb.plan("hash-su", ()), 5, 4096)
        if parse_su_digest(digest) != EXPECTED_SU_SHA256:
            raise V2Stop("legacy-su digest changed immediately before invocation")
        argv = fixed_root_argv(self.endpoint, operation, **kwargs)
        argv = (self.adb.adb, *argv[1:])
        return self.call(phase, name, argv, 10, 2 * 1024 * 1024)

    def collect_phase(self, phase: str) -> None:
        assessment = self.assess_su()
        self._persist(phase, "legacy_su_assessment",
                      json.dumps(assessment, sort_keys=True, indent=2).encode() + b"\n")
        if phase == "disconnected_baseline":
            root_id = self.root(phase, "su_identity", "identity")
            if not re.search(rb"(?:^|\s)uid=0(?:\(|\s)", root_id):
                raise V2Stop("existing SuperSU did not return UID 0")
        before = self.root(phase, "ps_before", "ps")
        pids = parse_ps_jmcs(before.decode("utf-8", "replace"))
        if len(pids) != 1:
            raise V2Stop("expected exactly one jmcs process; stop on ambiguity")
        pid = pids[0]
        identity = {}
        for leaf in ("stat", "status", "cmdline"):
            identity[leaf] = self.root(phase, "jmcs_" + leaf, "process", pid=pid, leaf=leaf)
        # Preserve exact process identity consistency across each snapshot.
        status = identity["status"].decode("utf-8", "replace")
        if (not re.search(r"(?m)^Uid:\s*0\s+0\s+0\s+0$", status)
                or not re.search(r"(?m)^Gid:\s*0\s+0\s+0\s+0$", status)
                or identity["cmdline"].replace(b"\x00", b"").strip() != b"/system/bin/jmcs"):
            raise V2Stop("jmcs UID/GID/cmdline did not match the stock receiver")
        exe = self.root(phase, "jmcs_executable_link", "exe", pid=pid)
        if parse_ls_symlink_target(exe) != "/system/bin/jmcs":
            raise V2Stop("jmcs executable link did not identify stock /system/bin/jmcs")
        start_time = parse_proc_stat_start_time(identity["stat"].decode("utf-8", "replace"))
        binding = (pid, start_time)
        if self.process_binding is not None and binding != self.process_binding:
            raise V2Stop("jmcs PID or start-time changed between session phases")
        self.process_binding = binding
        self.root(phase, "jmcs_executable_maps", "process", pid=pid, leaf="maps")
        fds = self.root(phase, "jmcs_fd_links", "fds", pid=pid)
        fd_pairs = [(int(fd), int(inode)) for fd, inode in re.findall(
            rb"(?m)([0-9]+)\s+->\s+socket:\[([0-9]+)\]", fds)]
        fd_count = len([line for line in fds.splitlines() if b" -> " in line])
        if fd_count > MAX_FDS:
            raise V2Stop("jmcs descriptor count exceeds the fixed per-process bound")
        network_rows: dict[str, list[str]] = {}
        for table in NETWORK_TABLES:
            raw = self.root(phase, "proc_net_" + table, "network", table=table)
            rows = []
            inode_column = 6 if table == "unix" else 9
            for line in raw.decode("utf-8", "replace").splitlines()[1:]:
                fields = line.split()
                if len(fields) > inode_column and fields[inode_column].isdecimal():
                    rows.append((fields[inode_column], line))
            network_rows[table] = [line for inode, line in rows
                                   if int(inode) in {item[1] for item in fd_pairs}]
        correlation = {
            "process_pid": pid, "process_start_time_ticks": start_time,
            "fd_socket_inode_count": len(fd_pairs),
            "fd_socket_pairs": [{"fd": fd, "inode": inode} for fd, inode in fd_pairs],
            "matched_proc_net_rows": network_rows,
            "interpretation": "inode matches show process-owned socket correlation only; traffic role/CarPlay meaning is not inferred without phase evidence",
        }
        self._persist(phase, "jmcs_socket_inode_correlation",
                      json.dumps(correlation, sort_keys=True, indent=2).encode() + b"\n")
        # System display inventory is unprivileged and restricted to existing
        # Android diagnostics. No display service calls or window changes.
        for service in ("display", "window", "SurfaceFlinger"):
            self._check_budget()
            code, out, err = self.adb.run("dumpsys", service, timeout=10,
                                          max_bytes=min(2 * 1024 * 1024,
                                                        MAX_OUTPUT - self.used))
            self.commands += 1; self.used += len(out) + len(err)
            if code != 0 or self.used > MAX_OUTPUT or self.commands > MAX_COMMANDS:
                raise V2Stop("display inventory failed or exceeded bounds; no retry")
            self._persist(phase, "dumpsys_" + service, out, err)
        self._check_budget()
        code, out, err = self.adb.run("dumpsys", "activity", "services", timeout=10,
                                      max_bytes=min(2 * 1024 * 1024,
                                                    MAX_OUTPUT - self.used))
        self.commands += 1; self.used += len(out) + len(err)
        if code != 0 or self.used > MAX_OUTPUT or self.commands > MAX_COMMANDS:
            raise V2Stop("external-display service inventory failed; no retry")
        self._persist(phase, "dumpsys_activity_services", out, err)
        netdev_argv = (self.adb.adb, "-s", self.endpoint, "shell", "cat", "/proc/net/dev")
        self.call(phase, "network_interface_counters", netdev_argv, 5, 128 * 1024)
        after = self.root(phase, "ps_after", "ps")
        if parse_ps_jmcs(after.decode("utf-8", "replace")) != pids:
            raise V2Stop("jmcs process identity changed during snapshot")
        stat_after = self.root(phase, "jmcs_stat_after", "process", pid=pid, leaf="stat")
        if parse_proc_stat_start_time(stat_after.decode("utf-8", "replace")) != start_time:
            raise V2Stop("jmcs process start time changed during snapshot")

    def _persist(self, phase: str, name: str, out: bytes, err: bytes = b"") -> None:
        rel = Path(phase) / (name + ".raw")
        target = self.output / rel
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes(out); target.chmod(0o600)
        self.files.append({"path": str(rel), "sha256": hashlib.sha256(out).hexdigest(),
                           "bytes": len(out)})

    def finalize(self, run_id: str, stop: str, stop_reason: str | None = None) -> None:
        manifest = {"campaign": CAMPAIGN, "schema": 2, "run_id": run_id,
                    "endpoint": self.endpoint, "started_utc": self.started_utc,
                    "created_utc": datetime.now(timezone.utc).isoformat(),
                    "commands": self.commands, "output_bytes": self.used,
                    "stop_status": stop, "stop_reason": stop_reason,
                    "side_effects": ["SuperSU may create daemon/request/log state"],
                    "artifacts": self.files}
        path = self.output / "manifest.json"
        path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        path.chmod(0o600)
        (self.output / "sha256.txt").write_text("\n".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(self.output)}"
            for p in sorted(self.output.rglob("*")) if p.is_file() and p.name != "sha256.txt") + "\n")
        (self.output / "sha256.txt").chmod(0o600)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial")
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--make-authorization-draft", action="store_true")
    args = parser.parse_args(argv)
    session = None
    output = None
    run_id = "unknown"
    try:
        if args.make_authorization_draft:
            draft = write_authorization_draft(args.authorization, args.serial)
            print(f"Non-authorizing draft written: {draft}")
            print("Endpoint, risk acceptance, expiry, power state and owner/readiness gates require current owner input at the vehicle.")
            return 0
        if args.dry_run:
            if args.serial is None:
                raise V2Stop("dry-run command planning requires one exact endpoint")
            source_lock_hash, profile_hash = source_binding()
            print(shlex.join(fixed_root_argv(args.serial, "identity")))
            print("Three snapshots: disconnected baseline, normal CarPlay connected, post-disconnect.")
            print(f"Profile SHA-256: {profile_hash}")
            print(f"Source-lock SHA-256: {source_lock_hash}")
            print("Dry run sends no ADB command and consumes no authorization.")
            return 0
        if args.output is None:
            raise V2Stop("live execution requires a new private --output path")
        if args.serial is None:
            raise V2Stop("live execution requires one exact ADB endpoint")
        auth = _read_auth(args.authorization, args.serial)
        run_id = auth["run_id"]
        auth_digest = hashlib.sha256(args.authorization.read_bytes()).hexdigest()
        print("Confirm outdoors, stationary Park, parking brake set, approved electrical state, owner present, and normal factory display/cluster/audio. Type YES to consume this one-use session authorization.")
        if input().strip() != "YES":
            raise V2Stop("owner readiness confirmation declined")
        refreshed_auth = _read_auth(args.authorization, args.serial)
        if (hashlib.sha256(args.authorization.read_bytes()).hexdigest() != auth_digest
                or refreshed_auth["run_id"] != run_id):
            raise V2Stop("authorization changed or expired during readiness confirmation")
        home = Path.home()
        consume_run_id(auth["run_id"], home / "Library/Application Support/ClarityLink/root-access-v2/consumed" / auth["run_id"])
        output = _private_output(args.output)
        session = Session(args.serial, output,
                          source_lock_sha256=auth["source_lock_sha256"],
                          profile_sha256=auth["profile_sha256"],
                          expires_utc=auth["expires_utc"])
        # Refuse device identity drift before any `su` call.
        session.verify_target()
        session.assess_su()
        for phase, prompt in (("disconnected_baseline", "Verify CarPlay disconnected; type READY"),
                              ("normal_stock_carplay_connected", "Connect normal wired iPhone CarPlay; type READY"),
                              ("normal_post_disconnect", "Disconnect normally; type READY")):
            if input(prompt + ": ").strip() != "READY":
                raise V2Stop("owner stopped before next phase")
            session.verify_target()
            session.collect_phase(phase)
        session.finalize(auth["run_id"], "COMPLETE_FIXED_DIAGNOSTIC",
                         "All three owner-confirmed snapshots completed within the fixed profile.")
        print(f"Private evidence saved: {output}")
        return 0
    except (V2Stop, SafetyStop, OSError, ValueError, json.JSONDecodeError) as exc:
        if session is not None and output is not None and output.exists():
            try:
                session.finalize(run_id, "ABORTED_" + type(exc).__name__, str(exc))
            except OSError:
                pass
        print(f"Stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
