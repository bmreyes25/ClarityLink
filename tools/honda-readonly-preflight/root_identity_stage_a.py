#!/usr/bin/env python3
"""Single-operation, owner-supervised Stage A root identity diagnostic.

No arbitrary command interface is exposed. Tests inject an offline transport;
the live adapter is deliberately limited to fixed ADB observations and one
fixed ``/system/xbin/su -c id`` invocation.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from typing import Callable, Protocol

from collector import FixedAdb, SafetyStop, REPO_ROOT
from privileged import PrivilegedRead, PrivilegedOperation, validate_su_fingerprint
from root_integrity_preflight import covering_mount, parse_ls_numeric

EXPECTED_SU_SHA256 = "d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26"
EXPECTED_SU_SIZE = 75348
ROOT_COMMAND = "/system/xbin/su -c id"
ROOT_TIMEOUT = 5
MAX_OUTPUT = 16 * 1024
TARGET_PROPERTIES = {
    "ro.build.version.release": "4.2.2",
    "ro.build.version.sdk": "17",
    "ro.product.model": "MY16ADA",
    "ro.product.device": "vcm30t30a",
    "ro.product.board": "Andromeda",
    "ro.hardware": "vcm30t30",
}


@dataclass(frozen=True)
class Result:
    code: int
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    output_limited: bool = False


class Transport(Protocol):
    serial: str
    def observe(self, operation: str, argument: str = "", *, timeout: int = 5,
                max_bytes: int = MAX_OUTPUT) -> Result: ...
    def root_identity_once(self) -> Result: ...
    def disconnect(self) -> None: ...


class AdbTransport:
    """Fixed operation adapter over the existing API-17 ADB collector."""
    def __init__(self):
        self.adb: FixedAdb | None = None
        self.serial = ""
        self.root_calls = 0

    def set_serial(self, serial: str) -> None:
        self.adb = FixedAdb(serial, resolve_auto=False)
        self.serial = self.adb.serial

    def _selected_adb(self) -> FixedAdb:
        if self.adb is None:
            raise SafetyStop("exact ADB serial has not been selected")
        return self.adb

    def _fixed_host_plan(self, operation: str, argument: str = "") -> tuple[str, ...]:
        """Stage A's only host-side plans not exposed by the older collector."""
        adb = self._selected_adb()
        if operation == "state" and not argument:
            return (adb.adb, "-s", self.serial, "get-state")
        raise SafetyStop("operation is outside the Stage A host-command allowlist")

    def _run_stage_a_plan(self, operation: str, *, timeout: int, max_bytes: int) -> Result:
        adb = self._selected_adb()
        command = self._fixed_host_plan(operation)
        code, out, err = adb._run_planned(command, f"stage_a_{operation}", (),
                                           timeout=timeout, max_bytes=max_bytes)
        record = adb.records[-1] if adb.records else {}
        return Result(code, out, err, record.get("result") == "timeout",
                      record.get("truncated", False))

    def observe(self, operation: str, argument: str = "", *, timeout: int = 5,
                max_bytes: int = MAX_OUTPUT) -> Result:
        if operation == "state":
            return self._run_stage_a_plan("state", timeout=timeout, max_bytes=max_bytes)
        adb = self._selected_adb()
        if operation == "property" and argument in TARGET_PROPERTIES:
            code, out, err = adb.run("property", argument, timeout=timeout, max_bytes=max_bytes)
        elif operation == "mounts" and not argument:
            code, out, err = adb.run("read", "/proc/self/mounts", timeout=timeout, max_bytes=max_bytes)
        elif operation == "su-binary" and not argument:
            # Use the API-17-compatible fixed-path adb sync pull already used
            # by the integrity preflight. The destination lives briefly in an
            # owner-only temporary directory and is removed after host hashing.
            with tempfile.TemporaryDirectory(prefix="claritylink-stage-a-") as temp:
                directory = Path(temp)
                os.chmod(directory, 0o700)
                destination = directory / "system_xbin_su.bin"
                command = (adb.adb, "-s", self.serial, "pull", "/system/xbin/su", str(destination))
                code, out, err = adb._run_planned(command, "stage_a_su_binary_pull",
                                                  ("/system/xbin/su", "<private-temp-file>"),
                                                  timeout=timeout, max_bytes=MAX_OUTPUT)
                record = adb.records[-1] if adb.records else {}
                timed_out = record.get("result") == "timeout"
                output_limited = record.get("truncated", False)
                if (code or timed_out or output_limited or record.get("result") != "success"
                        or not destination.is_file()):
                    return Result(code or 1, out, err, timed_out, output_limited)
                os.chmod(destination, 0o600)
                size = destination.stat().st_size
                if size > EXPECTED_SU_SIZE:
                    return Result(1, b"", b"pulled file exceeded expected size", False, True)
                with destination.open("rb") as stream:
                    payload = stream.read(EXPECTED_SU_SIZE + 1)
                if len(payload) != size:
                    return Result(1, b"", b"pulled file changed while being read", False, True)
                return Result(code, payload, err, timed_out, output_limited)
        elif operation == "su-list" and not argument:
            code, out, err = adb.run("ls-su-n", timeout=timeout, max_bytes=max_bytes)
        else:
            raise SafetyStop("operation is outside the Stage A observation allowlist")
        last = adb.records[-1]
        return Result(code, out, err, last.get("result") == "timeout", last.get("truncated", False))

    def root_identity_once(self) -> Result:
        if self.root_calls:
            raise SafetyStop("root identity operation already invoked")
        self.root_calls += 1
        adb = self._selected_adb()
        reader = PrivilegedRead(adb)
        command = reader.plan(PrivilegedOperation.IDENTITY)
        if command[-3:] != ("/system/xbin/su", "-c", "id"):
            raise SafetyStop("fixed root command construction changed")
        code, out, err = adb._run_planned(command, "stage_a_root_identity", (),
                                                timeout=ROOT_TIMEOUT, max_bytes=MAX_OUTPUT)
        record = adb.records[-1] if adb.records else {}
        return Result(code, out, err, record.get("result") == "timeout", record.get("truncated", False))

    def disconnect(self) -> None:
        # This is a host-side endpoint disconnect after the operator confirms
        # factory shutdown; it sends no shell command to the target.
        adb = self._selected_adb()
        result = subprocess.run((adb.adb, "disconnect", self.serial), capture_output=True,
                                timeout=5, check=False)
        expected = f"disconnected {self.serial}".encode()
        if result.returncode != 0 or expected not in result.stdout:
            raise SafetyStop("host ADB endpoint disconnection was not confirmed")


def parse_su_listing(output: bytes) -> tuple[int, str] | None:
    try:
        metadata = parse_ls_numeric(output)
    except (SafetyStop, UnicodeError, ValueError):
        return None
    if metadata.get("file_type") != "regular" or metadata.get("uid") != 0 or metadata.get("gid") != 0:
        return None
    return int(str(metadata["mode_octal"]), 8), str(metadata["size_bytes"])


def root_is_uid_zero(result: Result) -> bool:
    if result.code != 0 or result.timed_out or result.output_limited or result.stderr.strip():
        return False
    if len(result.stdout) + len(result.stderr) > MAX_OUTPUT:
        return False
    try:
        text = result.stdout.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return False
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return len(lines) == 1 and re.fullmatch(
        r"uid=0(?:\([^\r\n)]*\))?\s+gid=\d+(?:\([^\r\n)]*\))?"
        r"(?:\s+groups=\d+(?:\([^\r\n)]*\))?(?:,\d+(?:\([^\r\n)]*\))?)*)?",
        lines[0]) is not None


class StageA:
    def __init__(self, transport: Transport, *, input_fn: Callable[[str], str] = input,
                 output_fn: Callable[[str], None] = print, evidence_root: Path | None = None):
        self.transport, self.input, self.output = transport, input_fn, output_fn
        self.evidence_root = evidence_root or Path.home() / "Library/Application Support/ClarityLink/comprehensive-runtime/evidence"
        self.records: list[dict[str, object]] = []
        self.command_count = 0
        self.eligibility_state = "NOT_EVALUATED"
        self.output_dir: Path | None = None
        self.authorization_accepted = False
        self.last_root_result: Result | None = None

    def record(self, name: str, result: Result) -> None:
        self.records.append({"name": name, "exit_code": result.code,
                             "timed_out": result.timed_out, "output_limited": result.output_limited,
                             "stdout": result.stdout.decode("utf-8", "replace")[:MAX_OUTPUT],
                             "stderr": result.stderr.decode("utf-8", "replace")[:MAX_OUTPUT]})

    def emit(self, message: str) -> None:
        try:
            self.output(message)
        except OSError:
            # A closed terminal must not bypass cleanup or the shutdown prompt.
            pass

    def candidate(self) -> bool:
        self.eligibility_state = "NOT_ELIGIBLE"
        for name, expected in TARGET_PROPERTIES.items():
            result = self.transport.observe("property", name)
            self.record("identity:" + name, result)
            if result.code or result.stdout.decode("utf-8", "replace").strip() != expected:
                raise SafetyStop("target identity did not match MY16ADA / Android 4.2.2 / API 17")
        mounts = self.transport.observe("mounts", max_bytes=MAX_OUTPUT)
        self.record("mounts", mounts)
        mount = covering_mount(mounts.stdout)
        if (mounts.code or mounts.timed_out or mounts.output_limited or not mount.get("complete")
                or mount.get("read_only") is not True or mount.get("read_write") is not False
                or mount.get("overlay_uncertainty")):
            raise SafetyStop("the complete covering mount for /system/xbin/su is not uniquely read-only")
        self.records.append({"name": "covering-mount-decision", **mount})
        listing = self.transport.observe("su-list")
        self.record("su-list", listing)
        parsed = parse_su_listing(listing.stdout)
        if listing.code or listing.timed_out or listing.output_limited or parsed != (0o6777, str(EXPECTED_SU_SIZE)):
            raise SafetyStop("current su mode or size differs from the documented candidate")
        binary = self.transport.observe("su-binary", timeout=5, max_bytes=MAX_OUTPUT)
        if (binary.code or binary.timed_out or binary.output_limited
                or len(binary.stdout) != EXPECTED_SU_SIZE):
            self.records.append({"name": "su-host-fingerprint", "exit_code": binary.code,
                                 "timed_out": binary.timed_out, "output_limited": binary.output_limited,
                                 "size_bytes": len(binary.stdout), "sha256": None})
            raise SafetyStop("bounded host-side su binary read did not return the expected exact size")
        digest = hashlib.sha256(binary.stdout).hexdigest()
        self.records.append({"name": "su-host-fingerprint", "exit_code": binary.code,
                             "timed_out": binary.timed_out, "output_limited": binary.output_limited,
                             "size_bytes": len(binary.stdout), "sha256": digest})
        if digest != EXPECTED_SU_SHA256:
            raise SafetyStop("host-side su binary SHA-256 differs from the archived binary")
        # The unchanged generic integrity validator must continue rejecting the
        # documented anomalous mode. Stage A records a narrow diagnostic
        # exception only after fresh owner acceptance and current evidence.
        mode_text = str(parse_ls_numeric(listing.stdout)["mode_string"])
        try:
            validate_su_fingerprint(
                f"{digest}  /system/xbin/su\n".encode(),
                f"{mode_text} root root\n".encode())
        except SafetyStop as exc:
            if str(exc) != ("installed su is not root-owned with setuid and non-writable "
                            "group/other permissions"):
                raise
            generic_integrity_pass = False
        else:
            raise SafetyStop("the documented controlled-mode exception no longer applies")
        self.eligibility_state = "CONTROLLED_ROOT_IDENTITY_CANDIDATE"
        self.records.append({"name": "eligibility-decision", "state": self.eligibility_state,
                             "generic_integrity_pass": generic_integrity_pass,
                             "exception": "06777 is group/world writable; limited to one owner-authorized id invocation",
                             "fingerprint_binding": "host fingerprint is observed immediately before id; legacy ADB cannot atomically bind the copied bytes to the executable at invocation"})
        return True

    def run(self) -> str:
        self.emit("CLARITYLINK — STAGE A ROOT TEST\n\nQuestion: Does the one fixed root identity check return UID 0 on the currently verified MY16ADA target? Please turn on the Honda using its normal controls. Ensure it is stationary outdoors, in Park, with the parking brake engaged. Verify normal factory displays and warnings. Disconnect the iPhone from CarPlay. Connect ADB using the authorized head-unit endpoint. Ensure no other experiment is active.")
        self.emit("This procedure verifies the current endpoint and MY16ADA / Android 4.2.2 identity, checks /system mount state and /system/xbin/su metadata, and copies that fixed binary to a temporary owner-only host file for SHA-256 comparison. It then executes `/system/xbin/su -c id` once with a five-second host timeout. The binary's archived mode 06777 includes group/world write bits; this is a narrow diagnostic candidate and never a normal integrity PASS. SuperSU may create logs, authorization records, daemon state, or display a grant prompt. If a grant prompt appears, approve only if it clearly identifies this single `id` request and do so before the timeout; do not approve a late prompt after timeout. Stop if the serial or target identity differs, ADB is unavailable, the mount is writable or uncertain, the binary metadata/hash differs, any other prompt or behavior appears, or the vehicle behaves abnormally. A timeout is INCOMPLETE: the remote process may still exist and is not independently verified stopped. No receiver modification or additional privileged collection is authorized. If vehicle behavior is normal, factory power-off is the restoration route; report an abnormal state instead of assuming ordinary shutdown is appropriate.")
        try:
            authorization = self.input("Is the Honda ready for this experiment, and do you authorize this one-command Stage A diagnostic and accept the stated possible SuperSU side effects? Type YES to continue, NOT YET to stop for later, or CANCEL: ").strip()
        except (KeyboardInterrupt, EOFError):
            authorization = ""
        if authorization != "YES":
            if authorization == "NOT YET":
                self.emit("Not started. No target access or commands were made; run this procedure later when ready.")
                return "NOT_YET"
            self.emit("Cancelled before target access; no device commands were sent.")
            return "CANCELLED"
        self.authorization_accepted = True
        try:
            serial = self.input("Current exact ADB serial: ").strip()
        except (KeyboardInterrupt, EOFError):
            serial = ""
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", serial) or serial.lower() == "auto":
            result = "FAIL"
            self.emit("Stopped: invalid ADB serial syntax.")
            self.records.append({"name": "stop", "reason": "invalid ADB serial syntax"})
            try:
                self.finalize("FAIL")
            except Exception as exc:
                self.emit(f"Private evidence finalization failed: {type(exc).__name__}: {exc}")
                result = "INCOMPLETE"
            self.shutdown_prompt(disconnect=False)
            return result
        set_serial = getattr(self.transport, "set_serial", None)
        result = "FAIL"
        endpoint_selected = False
        try:
            self.emit("Readiness scope: this procedure checks the exact serial, MY16ADA/API 17 identity properties, /system mount state, numeric /system/xbin/su metadata, and copies that fixed binary to a temporary owner-only host file for SHA-256 comparison. The pull may read the binary contents; no target file is written.")
            if callable(set_serial):
                set_serial(serial)
            else:
                self.transport.serial = serial
            endpoint_selected = True
            # Validate private evidence storage before sending any target command,
            # especially before the one root invocation.
            self.prepare_evidence_root()
            state = self.transport.observe("state")
            self.record("device-state", state)
            if state.code or state.stdout.strip() != b"device":
                raise SafetyStop("selected ADB transport is not currently authorized and online")
            self.candidate()
            self.emit("Eligibility: CONTROLLED_ROOT_IDENTITY_CANDIDATE. Existing binary identity matches; this is not universal trust or deployment approval.")
            self.command_count += 1
            if self.command_count != 1:
                raise SafetyStop("at-most-once root operation guard rejected invocation")
            root = self.transport.root_identity_once()
            self.last_root_result = root
            self.record("root-identity", root)
            result = "PASS" if root_is_uid_zero(root) else "INCOMPLETE" if root.timed_out else "FAIL"
        except (Exception, KeyboardInterrupt) as exc:
            self.records.append({"name": "stop", "reason": type(exc).__name__ + ": " + str(exc)})
            if self.command_count:
                result = "INCOMPLETE"
            self.emit(f"Stage A stopped: {type(exc).__name__}: {exc}")
        finally:
            try:
                self.finalize(result)
            except Exception as exc:
                result = "INCOMPLETE"
                self.emit(f"Private evidence finalization failed: {type(exc).__name__}: {exc}")
                root_result = getattr(self, "last_root_result", None)
                if root_result is not None:
                    self.emit("The one-command `id` output could not be finalized: "
                              + (root_result.stdout + root_result.stderr).decode("utf-8", "replace")[:MAX_OUTPUT])
        if result == "INCOMPLETE":
            self.emit("Stage A result: INCOMPLETE. No retry or other root command will run. If the five-second root command timed out, remote termination is unverified; do not approve a late SuperSU prompt.")
        else:
            self.emit(f"Stage A result: {result}. No further vehicle commands will run.")
        self.shutdown_prompt(disconnect=endpoint_selected)
        return result

    def shutdown_prompt(self, *, disconnect: bool) -> None:
        self.emit("CLARITYLINK — ROOT TEST COMPLETE\n\nNo further vehicle diagnostic commands are scheduled. Please verify that the factory center display, instrument cluster, audio and warning indicators appear normal. If everything is normal, turn the Honda OFF using its factory controls. If a SuperSU dialog or any other abnormal state remains, report it instead of assuming ordinary shutdown is appropriate; do not approve a late prompt after timeout. If the vehicle state is normal, factory power-off is the restoration route. Reply `CAR POWERED OFF` only after factory shutdown.")
        try:
            ack = self.input("Vehicle shutdown acknowledgment: ").strip()
        except (KeyboardInterrupt, EOFError):
            ack = ""
        if ack == "CAR POWERED OFF":
            if disconnect:
                try:
                    self.transport.disconnect()
                except Exception:
                    self.emit("The host could not confirm ADB disconnection; do not reconnect or start another experiment.")
        else:
            self.emit("Host ADB endpoint was not disconnected because power-off was not acknowledged.")

    def finalize(self, result: str) -> None:
        resolved_root = self.prepare_evidence_root()
        folder = resolved_root / ("CL-STAGEA-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"))
        folder.mkdir(mode=0o700)
        payload = {"result": result, "adb_serial": self.transport.serial,
                   "eligibility_state": self.eligibility_state,
                   "command_count": self.command_count, "root_command": ROOT_COMMAND if self.command_count else None,
                   "owner_authorization_accepted": self.authorization_accepted,
                   "commands": self.records, "created_utc": datetime.now(timezone.utc).isoformat(),
                   "timeout_remote_termination_verified": False}
        path = folder / "manifest.json"
        data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
        sums = folder / "sha256.txt"
        manifest_tmp = folder / ".manifest.json.tmp"
        sums_tmp = folder / ".sha256.txt.tmp"
        try:
            os.chmod(folder, 0o700)
            for target, temp, encoded in (
                    (sums, sums_tmp, f"{hashlib.sha256(data).hexdigest()}  manifest.json\n".encode()),
                    (path, manifest_tmp, data)):
                fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temp, 0o600)
            os.replace(sums_tmp, sums)
            os.replace(manifest_tmp, path)
        except Exception:
            manifest_tmp.unlink(missing_ok=True)
            sums_tmp.unlink(missing_ok=True)
            if not path.exists():
                sums.unlink(missing_ok=True)
            raise
        self.output_dir = folder
        self.emit(f"Private evidence finalized: {folder}")

    def prepare_evidence_root(self) -> Path:
        requested_root = self.evidence_root.expanduser()
        if requested_root.is_symlink():
            raise SafetyStop("private evidence root may not be a symlink")
        resolved_root = requested_root.resolve()
        try:
            resolved_root.relative_to(REPO_ROOT.resolve())
        except ValueError:
            pass
        else:
            raise SafetyStop("private evidence storage must be outside the Git worktree")
        missing: list[Path] = []
        current = resolved_root
        while not current.exists():
            missing.append(current)
            current = current.parent
        if not current.is_dir():
            raise SafetyStop("private evidence root parent is not a directory")
        for directory in reversed(missing):
            directory.mkdir(mode=0o700)
            if stat.S_IMODE(directory.stat().st_mode) & 0o077:
                raise SafetyStop("new private evidence directory has unsafe permissions")
        root_info = resolved_root.stat()
        if (not stat.S_ISDIR(root_info.st_mode) or root_info.st_uid != os.geteuid()
                or stat.S_IMODE(root_info.st_mode) & 0o077):
            raise SafetyStop("private evidence root must be an owner-owned directory with mode 0700")
        return resolved_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="show the fixed operation plan without ADB access")
    args = parser.parse_args(argv)
    if args.dry_run:
        print("Offline only; no ADB query or target command is sent.")
        print("Fixed identity operation (only after fresh authorization):", ROOT_COMMAND)
        return 0
    try:
        status = StageA(AdbTransport()).run()
    except (SafetyStop, OSError, subprocess.TimeoutExpired) as exc:
        print(f"Stage A could not start: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
