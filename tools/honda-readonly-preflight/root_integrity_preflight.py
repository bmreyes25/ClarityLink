"""Unprivileged, one-shot metadata preflight for the existing su binary.

This does not invoke su. It records a fixed target fingerprint, numeric file
metadata, and one optional SHA-256 read in a host-private capture directory.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

from collector import Capture, FixedAdb, REPO_ROOT, SafetyStop
from privileged import EXPECTED_SU_SHA256


DEFAULT_OUTPUT = Path.home() / "Library/Application Support/ClarityLink/comprehensive-runtime/root-integrity"
MAX_OUTPUT = 64 * 1024
EXPECTED_SU_PATH = "/system/xbin/su"


def parse_ls_numeric(raw: bytes) -> dict[str, int | str]:
    """Parse Android 4.2 toolbox `ls -n` for exactly one regular file."""
    lines = [line.split() for line in raw.decode("utf-8", "replace").splitlines() if line.strip()]
    if len(lines) != 1 or len(lines[0]) < 7:
        raise SafetyStop("numeric ls output did not identify exactly one su file")
    mode, uid, gid = lines[0][:3]
    if (len(mode) != 10 or mode[0] != "-" or not uid.isdecimal()
            or not gid.isdecimal() or lines[0][-1] != "su"):
        raise SafetyStop("numeric ls output has an unexpected file type, owner, or path")
    permissions = mode[1:]
    allowed = (set("r-"), set("w-"), set("xSs"),
               set("r-"), set("w-"), set("xSs"),
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
            "setuid": bool(bits & 0o4000), "setgid": bool(bits & 0o2000)}


def parse_sha256sum(raw: bytes) -> str:
    match = re.fullmatch(rb"([0-9a-fA-F]{64})\s+\*?/system/xbin/su\s*", raw)
    if not match:
        raise SafetyStop("sha256sum output was not a single expected su digest")
    return match.group(1).decode("ascii").lower()


def integrity_decision(metadata: dict[str, int | str] | None,
                       digest: str | None) -> tuple[bool, str]:
    if not metadata or not digest:
        return False, "INCOMPLETE_EVIDENCE"
    mode = int(metadata["mode_octal"], 8)
    passed = (metadata["uid"] == 0 and metadata["gid"] == 0
              and bool(mode & 0o4000) and not mode & 0o022
              and digest == EXPECTED_SU_SHA256)
    return passed, "NOT_READY_SIDE_EFFECTS_UNRESOLVED" if passed else "INELIGIBLE"


def _write_summary(path: Path, value: dict) -> None:
    encoded = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        # A hard link provides exclusive publication without replacing an
        # existing summary and only after the complete bytes are durable.
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


def verify_exact_endpoint(adb: FixedAdb) -> None:
    """Check the host ADB listing without contacting a target shell."""
    code, stdout, _stderr = adb.run("host-devices", timeout=5, max_bytes=4096)
    record = adb.records[-1]
    rows = []
    for line in stdout.decode("utf-8", "replace").splitlines():
        stripped = line.strip()
        if (not stripped or stripped == "List of devices attached"
                or (stripped.startswith("*") and stripped.endswith("*"))):
            continue
        rows.append(stripped.split())
    valid = (code == 0 and record.get("result") == "success" and len(rows) == 1 and len(rows[0]) >= 2
             and rows[0][0] == adb.serial and rows[0][1] == "device")
    record.update({"candidate_count": len(rows),
                   "states": [row[1] if len(row) > 1 else "MALFORMED" for row in rows],
                   "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                   "endpoint_result": "ok" if valid else "refused"})
    if not valid:
        raise SafetyStop("expected exactly the specified authorized ADB endpoint and no other devices")


def read_numeric_su_metadata(adb: FixedAdb, capture: Capture) -> tuple[int, bytes]:
    code, stdout, stderr = adb.run("ls-su-n", timeout=5, max_bytes=MAX_OUTPUT)
    capture.record_result("preflight", "root_integrity", "su_numeric_metadata",
                          "ls-su-n", (), code, stdout, stderr)
    return code, stdout


def run(serial: str, output_root: Path) -> Path:
    output_root = output_root.expanduser().resolve()
    if output_root == REPO_ROOT or REPO_ROOT in output_root.parents:
        raise SafetyStop("private preflight output must be outside the Git worktree")
    _create_private_directories(output_root)
    if stat.S_IMODE(output_root.stat().st_mode) & 0o077:
        raise SafetyStop("private output root has group/other permissions; refusing to change it")
    adb = FixedAdb(serial, resolve_auto=False)
    verify_exact_endpoint(adb)
    output = output_root / ("su-preflight-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"))
    output.mkdir(mode=0o700)
    capture = Capture(adb, output)
    try:
        target_identity = capture.verify_target_identity()
        capture.target_identity = target_identity
        meta_code, meta_raw = read_numeric_su_metadata(adb, capture)
        meta_record = adb.records[-1]
        if meta_record.get("result") in {"transport_failure", "timeout", "output_limit"}:
            raise SafetyStop(f"metadata command stopped: {meta_record.get('result')}")
        metadata_error = None
        if (meta_code != 0 or meta_record.get("result") != "success"):
            metadata = None
            metadata_error = f"metadata command result: {meta_record.get('result', 'unknown')}"
            digest = None
            hash_error = "not attempted because metadata command did not succeed"
        else:
            metadata = parse_ls_numeric(meta_raw)
            # Optional utility: one attempt only. Its absence is evidence, not a
            # reason to escalate, substitute a helper, or retry another pathway.
            hash_code, hash_raw = capture.store("preflight", "root_integrity", "su_sha256",
                                                "hash-su", timeout=5, max_bytes=MAX_OUTPUT)
            hash_record = adb.records[-1]
            if hash_code == 0 and hash_record.get("result") == "success":
                try:
                    digest, hash_error = parse_sha256sum(hash_raw), None
                except SafetyStop as exc:
                    digest, hash_error = None, str(exc)
            else:
                digest, hash_error = None, f"optional hash result: {hash_record.get('result', 'unknown')}"
        integrity_pass, execution_eligibility = integrity_decision(metadata, digest)
        summary = {
            "schema": "claritylink-su-integrity-preflight-v1",
            "execution_status": "COMPLETE" if metadata else "INCOMPLETE",
            "target_serial": serial,
            "target_identity": target_identity,
            "su_path": EXPECTED_SU_PATH,
            "existence": "PRESENT" if metadata else "ABSENT_OR_UNREADABLE",
            "metadata_status": "success" if metadata else "unavailable_or_unparseable",
            "metadata_error": metadata_error,
            "metadata": metadata,
            "sha256_status": "success" if digest else "unavailable_or_unparseable",
            "sha256_error": hash_error,
            "sha256": digest,
            "sha256_matches_archived_binary": digest == EXPECTED_SU_SHA256 if digest else None,
            "integrity_gate": "PASS" if integrity_pass else "FAIL_OR_INCOMPLETE",
            "root_execution_eligibility": execution_eligibility,
            "existing_root_authorization_change": "UNKNOWN_NOT_OBSERVED",
            "jmcs_process_identity": "NOT_COLLECTED_BY_UNPRIVILEGED_PREFLIGHT",
            "privileged_runtime_evidence": "NOT_COLLECTED",
            "restoration": "NOT_APPLICABLE_READ_ONLY_PREFLIGHT",
            "root_or_target_writes_performed": False,
            "captured_utc": datetime.now(timezone.utc).isoformat(),
        }
        _write_summary(output / "summary.json", summary)
    except Exception as exc:
        capture.stop_result = "safe_abort"
        failure = {"schema": "claritylink-su-integrity-preflight-v1",
                   "execution_status": "ABORTED", "stop_reason": type(exc).__name__,
                   "details": str(exc), "target_serial": serial,
                   "root_or_target_writes_performed": False,
                   "captured_utc": datetime.now(timezone.utc).isoformat()}
        summary_error = None
        try:
            _write_summary(output / "summary.json", failure)
        except OSError as write_exc:
            summary_error = type(write_exc).__name__
        try:
            capture.finalize(["preflight"])
        except OSError as finalize_exc:
            summary_error = f"capture finalization failed: {type(finalize_exc).__name__}"
        if summary_error:
            raise SafetyStop(f"preflight aborted; partial private capture at {output}; {summary_error}: {exc}") from exc
        raise SafetyStop(f"preflight aborted; partial private capture preserved at {output}: {exc}") from exc
    capture.finalize(["preflight"])
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="exact already-authorized ADB serial; no auto-selection")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT,
                        help="private host directory outside the repository")
    parser.add_argument("--dry-run", action="store_true", help="print fixed operations without ADB contact")
    parser.add_argument("--owner-confirmed", action="store_true",
                        help="owner confirms this one-shot unprivileged metadata check")
    parser.add_argument("--vehicle-parked-confirmed", action="store_true")
    parser.add_argument("--iphone-disconnected-confirmed", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not args.dry_run and not (args.owner_confirmed and args.vehicle_parked_confirmed
                                     and args.iphone_disconnected_confirmed):
            raise SafetyStop("owner, parked-vehicle, and disconnected-iPhone confirmations are required")
        adb = FixedAdb(args.serial, resolve_auto=False)
        if args.dry_run:
            print("Host endpoint check when collecting: adb devices -l (may start the host ADB daemon; no target shell command is run).")
            for operation, parameters in (
                ("read", ("/proc/version",)),
                ("property", ("ro.build.version.release",)),
                ("property", ("ro.build.version.sdk",)),
                ("property", ("ro.product.device",)),
                ("property", ("ro.product.board",)),
                ("property", ("ro.hardware",)),
                ("ls-su-n", ()), ("hash-su", ()),
            ):
                print(adb.dry_run_command(operation, *parameters))
            return 0
        print(run(args.serial, args.output_root))
        return 0
    except (SafetyStop, OSError, ValueError) as exc:
        print(f"preflight stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
