"""One-shot, unprivileged collection of su bytes, metadata, and mount state.

Only three target operations are permitted: read /proc/mounts, numeric ls of
/system/xbin/su, and adb pull of that file. This tool never invokes su.
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
import subprocess
import stat
import sys
import uuid

from collector import (Capture, FixedAdb, REPO_ROOT, SafetyStop,
                       validate_legacy_shell_output)
from privileged import EXPECTED_SU_SHA256


DEFAULT_OUTPUT = Path.home() / "Library/Application Support/ClarityLink/comprehensive-runtime/evidence"
MAX_OUTPUT = 128 * 1024
EXPECTED_SU_PATH = "/system/xbin/su"
EXPECTED_SU_SIZE = 75_348
MOUNT_OCTAL_ESCAPE = re.compile(r"\\([0-7]{3})")
OVERLAY_FILESYSTEMS = frozenset({"overlay", "aufs", "unionfs"})


def parse_ls_numeric(raw: bytes) -> dict[str, int | str]:
    """Parse Android 4.2 toolbox `ls -n` for exactly one regular file."""
    lines = [line.split() for line in raw.decode("utf-8", "replace").splitlines() if line.strip()]
    if len(lines) != 1 or len(lines[0]) < 7:
        raise SafetyStop("numeric ls output did not identify exactly one su file")
    mode, uid, gid = lines[0][:3]
    if (len(mode) != 10 or mode[0] != "-" or not uid.isdecimal()
            or not gid.isdecimal() or not lines[0][3].isdecimal() or lines[0][-1] != "su"):
        raise SafetyStop("numeric ls output has an unexpected file type, owner, or path")
    permissions = mode[1:]
    allowed = (set("r-"), set("w-"), set("xSs"), set("r-"), set("w-"), set("xSs"),
               set("r-"), set("w-"), set("xTt"))
    if any(char not in allowed[index] for index, char in enumerate(permissions)):
        raise SafetyStop("numeric ls output contains invalid permission characters")
    bits = (0o4000 if permissions[2] in "sS" else 0)
    bits |= 0o2000 if permissions[5] in "sS" else 0
    bits |= 0o1000 if permissions[8] in "tT" else 0
    for index, triplet in enumerate((permissions[0:3], permissions[3:6], permissions[6:9])):
        for offset, char in enumerate(triplet):
            if char in "rwx":
                bits |= 1 << (8 - index * 3 - offset)
            elif char in "st" and offset == 2:
                bits |= 1 << (8 - index * 3 - offset)
    return {"file_type": "regular", "uid": int(uid), "gid": int(gid),
            "mode_string": mode, "mode_octal": f"0o{bits:04o}",
            "setuid": bool(bits & 0o4000), "setgid": bool(bits & 0o2000),
            "size_bytes": int(lines[0][3])}


def _unescape_mount_field(value: str) -> str:
    return MOUNT_OCTAL_ESCAPE.sub(lambda match: chr(int(match.group(1), 8)), value)


def covering_mount(raw: bytes, target: str = EXPECTED_SU_PATH) -> dict[str, object]:
    """Resolve the longest /proc/mounts mountpoint covering target; fail closed."""
    text = raw.decode("utf-8", "replace")
    entries: list[dict[str, str]] = []
    malformed = False
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 4:
            malformed = True
            continue
        source, mountpoint, filesystem, options = (_unescape_mount_field(item) for item in fields[:4])
        if mountpoint == "/" or target == mountpoint or target.startswith(mountpoint.rstrip("/") + "/"):
            entries.append({"source": source, "mount_point": mountpoint,
                            "filesystem_type": filesystem, "options": options})
    if not entries:
        return {"complete": False, "reason": "no mount entry covers /system/xbin/su"}
    longest = max(len(str(item["mount_point"])) for item in entries)
    closest = [item for item in entries if len(str(item["mount_point"])) == longest]
    if malformed or len(closest) != 1:
        return {"complete": False, "reason": "mount table is malformed or has ambiguous covering entries",
                "covering_entries": closest}
    entry = closest[0]
    flags = set(str(entry["options"]).split(","))
    read_only = "ro" in flags and "rw" not in flags
    read_write = "rw" in flags and "ro" not in flags
    if not read_only and not read_write:
        return {"complete": False, "reason": "covering mount entry has no unique ro/rw flag",
                **entry}
    fs = str(entry["filesystem_type"]).lower()
    options = str(entry["options"]).lower()
    uncertainty = []
    if fs in OVERLAY_FILESYSTEMS or any(token in options for token in ("lowerdir=", "upperdir=", "workdir=")):
        uncertainty.append("overlay or union mount indicated by filesystem/options")
    if "bind" in flags:
        uncertainty.append("bind mount is indicated; underlying source writeability is not shown")
    return {"complete": True, **entry, "read_only": read_only, "read_write": read_write,
            "overlay_uncertainty": uncertainty,
            "mount_view": "ADB shell process /proc/mounts namespace; mount layering beyond this table is not independently verified"}


def controlled_candidate(metadata: dict[str, int | str] | None,
                         digest: str | None, size_bytes: int | None,
                         mount: dict[str, object]) -> tuple[bool, str]:
    if not mount.get("complete"):
        return False, "INCOMPLETE_EVIDENCE"
    if mount.get("read_write") is True:
        return False, "INELIGIBLE_SYSTEM_MOUNT_READ_WRITE"
    if not metadata or not digest:
        return False, "INCOMPLETE_EVIDENCE"
    mode = int(str(metadata["mode_octal"]), 8)
    if (metadata.get("file_type") != "regular" or metadata.get("uid") != 0
            or metadata.get("gid") != 0 or not mode & 0o4000):
        return False, "INELIGIBLE_FILE_METADATA"
    if digest != EXPECTED_SU_SHA256:
        return False, "INELIGIBLE_BINARY_HASH_MISMATCH"
    if size_bytes != EXPECTED_SU_SIZE or metadata.get("size_bytes") != EXPECTED_SU_SIZE:
        return False, "INELIGIBLE_BINARY_SIZE_MISMATCH"
    if mount.get("read_only") is not True:
        return False, "INELIGIBLE_SYSTEM_MOUNT_STATE_UNKNOWN"
    if mount.get("overlay_uncertainty"):
        return False, "INELIGIBLE_MOUNT_LAYERING_UNRESOLVED"
    return True, "CONTROLLED_IDENTITY_CHECK_CANDIDATE_PENDING_NEW_OWNER_DECISION"


def _write_summary(path: Path, value: dict) -> None:
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _create_private_directories(path: Path) -> None:
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    if not current.is_dir():
        raise SafetyStop("private output parent is not a directory")
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        if stat.S_IMODE(directory.stat().st_mode) & 0o077:
            raise SafetyStop("new private output directory inherited unsafe permissions")


def _store_mounts(adb: FixedAdb, capture: Capture) -> bytes:
    code, stdout, stderr = adb.run("read", "/proc/mounts", timeout=5, max_bytes=MAX_OUTPUT)
    capture.record_result("preflight", "root_integrity", "mounts", "read",
                          ("/proc/mounts",), code, stdout, stderr)
    validate_legacy_shell_output("read", ("/proc/mounts",), code, stdout, stderr)
    if adb.records[-1].get("result") != "success":
        raise SafetyStop("/proc/mounts read did not complete successfully")
    return stdout


def _store_metadata(adb: FixedAdb, capture: Capture) -> tuple[int, bytes]:
    code, stdout, stderr = adb.run("ls-su-n", timeout=5, max_bytes=MAX_OUTPUT)
    capture.record_result("preflight", "root_integrity", "su_numeric_metadata",
                          "ls-su-n", (), code, stdout, stderr)
    if code != 0 or adb.records[-1].get("result") != "success":
        raise SafetyStop("numeric su metadata read did not complete successfully")
    return code, stdout


def plan_su_pull(adb: FixedAdb, destination: Path) -> tuple[str, ...]:
    """Plan only adb pull of the fixed su path into a new owner-only file."""
    destination = destination.expanduser().resolve()
    if destination == REPO_ROOT or REPO_ROOT in destination.parents:
        raise SafetyStop("su pull destination must be outside the Git worktree")
    if (not destination.parent.is_dir() or destination.exists() or destination.is_symlink()
            or destination.parent.stat().st_mode & 0o077):
        raise SafetyStop("su pull destination must be new inside an existing owner-only directory")
    return (adb.adb, "-s", adb.serial, "pull", EXPECTED_SU_PATH, str(destination))


def _pull_binary(adb: FixedAdb, capture: Capture, destination: Path) -> tuple[int, bytes, bytes]:
    command = plan_su_pull(adb, destination)
    result = adb._run_planned(command, "pull-su", ("/system/xbin/su", str(destination)),
                              timeout=20, max_bytes=MAX_OUTPUT)
    code, stdout, stderr = result
    capture.record_result("preflight", "root_integrity", "adb_pull_result", "pull-su",
                          ("/system/xbin/su", str(destination)), code, stdout, stderr)
    if code != 0 or adb.records[-1].get("result") != "success" or not destination.is_file():
        raise SafetyStop("ADB pull did not produce the expected host file")
    destination.chmod(0o600)
    size = destination.stat().st_size
    if not 0 < size <= 1024 * 1024:
        raise SafetyStop("pulled su file has an implausible size")
    return code, stdout, stderr


def _host_sha256(capture: Capture, binary: Path) -> str:
    command = ("/usr/bin/shasum", "-a", "256", str(binary))
    try:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                                timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SafetyStop("macOS shasum could not hash the pulled file") from exc
    capture.record_result("preflight", "root_integrity", "host_shasum", "host-shasum",
                          command, result.returncode, result.stdout, result.stderr)
    match = re.fullmatch(rb"([0-9a-fA-F]{64})\s+[^\r\n]+\s*", result.stdout)
    if result.returncode != 0 or not match:
        raise SafetyStop("macOS shasum output was not one digest and file path")
    external_digest = match.group(1).decode("ascii").lower()
    internal_digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    if external_digest != internal_digest:
        raise SafetyStop("macOS shasum and independent host digest disagree")
    return external_digest


def run(serial: str, output_root: Path) -> Path:
    if not serial or serial.lower() == "auto":
        raise SafetyStop("an exact already-authorized serial is required; auto-selection is disabled")
    output_root = output_root.expanduser().resolve()
    if output_root == REPO_ROOT or REPO_ROOT in output_root.parents:
        raise SafetyStop("private preflight output must be outside the Git worktree")
    _create_private_directories(output_root)
    if stat.S_IMODE(output_root.stat().st_mode) & 0o077:
        raise SafetyStop("private output root has group/other permissions; refusing to change it")
    adb = FixedAdb(serial, resolve_auto=False)
    output = output_root / ("su-preflight-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"))
    output.mkdir(mode=0o700)
    if stat.S_IMODE(output.stat().st_mode) != 0o700:
        raise SafetyStop("new evidence directory is not owner-only")
    capture = Capture(adb, output)
    binary = output / "system_xbin_su.bin"
    mount: dict[str, object] | None = None
    metadata: dict[str, int | str] | None = None
    digest: str | None = None
    pulled_size: int | None = None
    host_file_written = False
    try:
        mounts_raw = _store_mounts(adb, capture)
        mount = covering_mount(mounts_raw)
        # A writable or unresolvable mount is a hard stop: do not copy a
        # world-writable setuid binary while its backing mount is uncertain.
        if not mount.get("complete") or mount.get("read_write") is True:
            capture.stop_result = "safe_abort_before_metadata_or_pull"
            _write_summary(output / "summary.json", _summary(serial, mount, None, None, None,
                                                               "STOPPED_MOUNT_NOT_READ_ONLY"))
            capture.finalize(["preflight"])
            return output
        code, metadata_raw = _store_metadata(adb, capture)
        metadata = parse_ls_numeric(metadata_raw)
        if int(metadata["size_bytes"]) <= 0 or int(metadata["size_bytes"]) > 1024 * 1024:
            capture.stop_result = "safe_abort_before_pull"
            _write_summary(output / "summary.json", _summary(serial, mount, metadata, None, None,
                                                               "STOPPED_IMPLAUSIBLE_FILE_SIZE"))
            capture.finalize(["preflight"])
            return output
        _pull_binary(adb, capture, binary)
        host_file_written = True
        pulled_size = binary.stat().st_size
        digest = _host_sha256(capture, binary)
        summary = _summary(serial, mount, metadata, digest, pulled_size, "COMPLETE", host_file_written)
        capture.target_identity = "exact owner-approved endpoint only"
        _write_summary(output / "summary.json", summary)
    except Exception as exc:
        capture.stop_result = "safe_abort"
        failure = _summary(serial, mount, metadata, digest, pulled_size, "ABORTED", host_file_written)
        failure["stop_reason"] = type(exc).__name__
        failure["details"] = str(exc)
        try:
            _write_summary(output / "summary.json", failure)
        finally:
            capture.finalize(["preflight"])
        raise SafetyStop(f"preflight aborted; private partial capture preserved at {output}: {exc}") from exc
    capture.finalize(["preflight"])
    return output


def _summary(serial: str, mount: dict[str, object] | None,
             metadata: dict[str, int | str] | None, digest: str | None,
             pulled_size: int | None, status: str, host_file_written: bool = False) -> dict[str, object]:
    archived_match = digest == EXPECTED_SU_SHA256 if digest else None
    size_match = pulled_size == EXPECTED_SU_SIZE if pulled_size is not None else None
    candidate, eligibility = controlled_candidate(metadata, digest, pulled_size, mount or {})
    mode = int(str(metadata["mode_octal"]), 8) if metadata else None
    return {
        "schema": "claritylink-su-live-integrity-preflight-v2",
        "execution_status": status,
        "target_serial": serial,
        "target_identity_basis": "exact owner-approved ADB serial; no target properties queried",
        "su_path": EXPECTED_SU_PATH,
        "target_metadata": metadata,
        "archived_size_bytes": EXPECTED_SU_SIZE,
        "pulled_size_bytes": pulled_size,
        "size_matches_archive": size_match,
        "expected_sha256": EXPECTED_SU_SHA256,
        "observed_sha256": digest,
        "sha256_matches_archive": archived_match,
        "covering_mount": mount,
        "conventional_integrity_status": "NOT_A_CONVENTIONAL_INTEGRITY_PASS",
        "permission_mode_assessment": (
            "NONCONVENTIONAL_GROUP_OR_OTHER_WRITABLE" if mode is not None and mode & 0o022
            else "GROUP_AND_OTHER_WRITE_BITS_CLEAR" if mode is not None
            else "UNKNOWN"
        ),
        "controlled_root_identity_candidate": candidate,
        "root_execution_eligibility": eligibility,
        "stage_a": "NOT_EXECUTED_REQUIRES_A_SEPARATE_NEW_OWNER_DECISION",
        "possible_su_side_effects": ["authorization or policy record", "SuperSU logs", "daemon activity"],
        "root_or_target_writes_performed": False,
        "adb_host_file_written": host_file_written,
        "captured_utc": datetime.now(timezone.utc).isoformat(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="exact already-authorized ADB serial; no discovery")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT,
                        help="new owner-only host directory outside the repository")
    parser.add_argument("--dry-run", action="store_true", help="print only the fixed plan; no ADB contact")
    parser.add_argument("--owner-confirmed", action="store_true")
    parser.add_argument("--vehicle-outdoors-confirmed", action="store_true")
    parser.add_argument("--vehicle-parked-confirmed", action="store_true")
    parser.add_argument("--parking-brake-confirmed", action="store_true")
    parser.add_argument("--factory-behavior-normal-confirmed", action="store_true")
    parser.add_argument("--power-state-confirmed", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not args.serial or args.serial.lower() == "auto":
            raise SafetyStop("an exact already-authorized ADB serial is required; auto-selection is disabled")
        if args.dry_run:
            adb = FixedAdb(args.serial, resolve_auto=False)
            for operation, parameters in (("read", ("/proc/mounts",)), ("ls-su-n", ())):
                print(adb.dry_run_command(operation, *parameters))
            print(shlex.join(plan_su_pull(adb, DEFAULT_OUTPUT / ".dry-run-su.bin")))
            print("Host SHA-256: shasum -a 256 <private-copied-file>")
            return 0
        confirmations = (args.owner_confirmed, args.vehicle_outdoors_confirmed,
                         args.vehicle_parked_confirmed, args.parking_brake_confirmed,
                         args.factory_behavior_normal_confirmed, args.power_state_confirmed)
        if not all(confirmations):
            raise SafetyStop("all one-shot owner and vehicle readiness confirmations are required")
        output = run(args.serial, args.output_root)
        print(f"Private evidence captured: {output}")
        return 0
    except (SafetyStop, OSError, ValueError) as exc:
        print(f"preflight stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
