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
import subprocess
import sys
from typing import Callable, Protocol

from collector import FixedAdb, SafetyStop, REPO_ROOT
from privileged import PrivilegedRead, PrivilegedOperation

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

    def observe(self, operation: str, argument: str = "", *, timeout: int = 5,
                max_bytes: int = MAX_OUTPUT) -> Result:
        if operation == "state":
            adb = self._selected_adb()
            command = (adb.adb, "-s", self.serial, "get-state")
            code, out, err = adb._run_planned(command, "device-state", (),
                                               timeout=timeout, max_bytes=max_bytes)
            record = adb.records[-1] if adb.records else {}
            return Result(code, out, err, record.get("result") == "timeout",
                          record.get("result") == "output_limit")
        adb = self._selected_adb()
        if operation == "property" and argument == "ro.product.model":
            command = (adb.adb, "-s", self.serial, "shell", "getprop", "ro.product.model")
            code, out, err = adb._run_planned(command, "stage_a_model_identity", (),
                                                timeout=timeout, max_bytes=max_bytes)
        elif operation == "property" and argument in TARGET_PROPERTIES:
            code, out, err = adb.run("property", argument, timeout=timeout, max_bytes=max_bytes)
        elif operation == "mounts" and not argument:
            code, out, err = adb.run("read", "/proc/self/mounts", timeout=timeout, max_bytes=max_bytes)
        elif operation == "su-hash" and not argument:
            code, out, err = adb.run("hash-su", timeout=timeout, max_bytes=max_bytes)
        elif operation == "su-list" and not argument:
            code, out, err = adb.run("ls-su", timeout=timeout, max_bytes=max_bytes)
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
        subprocess.run((adb.adb, "disconnect", self.serial), stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=5, check=False)


def parse_su_listing(output: bytes) -> tuple[int, str] | None:
    text = output.decode("utf-8", "replace").strip()
    match = re.fullmatch(r"(-[rwxstST-]{9})\s+(root|0)\s+(root|0)\s+(\d+)\s+.+\s+/system/xbin/su", text)
    if not match:
        return None
    mode_text, _, _, size_text = match.groups()
    bits = 0
    for index, char in enumerate(mode_text[1:]):
        if char in "rwxst":
            bits |= (0o400 >> ((index // 3) * 3)) if char == "r" else 0
            if char == "w": bits |= (0o200 >> ((index // 3) * 3))
            if char in "xs": bits |= (0o100 >> ((index // 3) * 3))
            if char in "st": bits |= 0o4000 if index == 2 else 0o2000 if index == 5 else 0
    return bits, int(size_text)


def root_is_uid_zero(result: Result) -> bool:
    if result.code != 0 or result.timed_out or result.output_limited or result.stderr.strip():
        return False
    if len(result.stdout) + len(result.stderr) > MAX_OUTPUT:
        return False
    text = result.stdout.decode("utf-8", "strict")
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

    def record(self, name: str, result: Result) -> None:
        self.records.append({"name": name, "exit_code": result.code,
                             "timed_out": result.timed_out, "output_limited": result.output_limited,
                             "stdout": result.stdout.decode("utf-8", "replace")[:MAX_OUTPUT],
                             "stderr": result.stderr.decode("utf-8", "replace")[:MAX_OUTPUT]})

    def candidate(self) -> bool:
        self.eligibility_state = "NOT_ELIGIBLE"
        for name, expected in TARGET_PROPERTIES.items():
            result = self.transport.observe("property", name)
            self.record("identity:" + name, result)
            if result.code or result.stdout.decode("utf-8", "replace").strip() != expected:
                raise SafetyStop("target identity did not match MY16ADA / Android 4.2.2 / API 17")
        mounts = self.transport.observe("mounts", max_bytes=MAX_OUTPUT)
        self.record("mounts", mounts)
        if mounts.code or mounts.timed_out or not re.search(r"(?m)^/dev/\S+ /system ext4 ro(?:,|\s)", mounts.stdout.decode("utf-8", "replace")):
            raise SafetyStop("current /system mount is not verified ext4 read-only")
        digest = self.transport.observe("su-hash")
        self.record("su-hash", digest)
        if digest.code or not re.match(rb"^" + EXPECTED_SU_SHA256.encode() + rb"\s+/system/xbin/su\s*$", digest.stdout.strip()):
            raise SafetyStop("current su binary does not match the archived SHA-256")
        listing = self.transport.observe("su-list")
        self.record("su-list", listing)
        parsed = parse_su_listing(listing.stdout)
        if listing.code or parsed != (0o6777, EXPECTED_SU_SIZE):
            raise SafetyStop("current su mode or size differs from the documented candidate")
        self.eligibility_state = "CONTROLLED_ROOT_IDENTITY_CANDIDATE"
        self.records.append({"name": "eligibility-decision", "state": self.eligibility_state,
                             "generic_integrity_pass": False})
        return True

    def run(self) -> str:
        self.output("CLARITYLINK — STAGE A ROOT TEST\n\nPlease turn on the Honda using its normal controls. Ensure it is stationary outdoors, in Park, with the parking brake engaged. Verify normal factory displays and warnings. Disconnect the iPhone from CarPlay. Connect ADB using the authorized head-unit endpoint. Ensure no other experiment is active, then provide the current exact ADB serial.")
        self.output("This experiment executes `/system/xbin/su -c id` exactly once to determine whether existing root access still works. SuperSU may create logs, authorization records, or daemon state. No receiver modification or additional privileged collection is authorized.")
        try:
            authorization = self.input("I authorize this one-command Stage A diagnostic and accept the stated possible side effects. Type YES to continue; anything else cancels: ").strip()
        except (KeyboardInterrupt, EOFError):
            authorization = ""
        if authorization != "YES":
            self.output("Cancelled before target access; no device commands were sent.")
            self.shutdown_prompt(disconnect=False)
            return "CANCELLED"
        try:
            serial = self.input("Current exact ADB serial: ").strip()
        except (KeyboardInterrupt, EOFError):
            serial = ""
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", serial):
            self.output("Stopped: invalid ADB serial syntax.")
            self.records.append({"name": "stop", "reason": "invalid ADB serial syntax"})
            self.finalize("FAIL")
            self.shutdown_prompt(disconnect=False)
            return "FAIL"
        set_serial = getattr(self.transport, "set_serial", None)
        result = "FAIL"
        endpoint_selected = False
        try:
            if callable(set_serial):
                set_serial(serial)
            else:
                self.transport.serial = serial
            endpoint_selected = True
            state = self.transport.observe("state")
            self.record("device-state", state)
            if state.code or state.stdout.strip() != b"device":
                raise SafetyStop("selected ADB transport is not currently authorized and online")
            self.candidate()
            self.output("Eligibility: CONTROLLED_ROOT_IDENTITY_CANDIDATE. Existing binary identity matches; this is not universal trust or deployment approval.")
            self.command_count += 1
            if self.command_count != 1:
                raise SafetyStop("at-most-once root operation guard rejected invocation")
            root = self.transport.root_identity_once()
            self.record("root-identity", root)
            result = "PASS" if root_is_uid_zero(root) else "INCOMPLETE" if root.timed_out else "FAIL"
        except (SafetyStop, OSError, subprocess.TimeoutExpired, KeyboardInterrupt, EOFError) as exc:
            self.records.append({"name": "stop", "reason": type(exc).__name__ + ": " + str(exc)})
            self.output(f"Stage A stopped: {type(exc).__name__}: {exc}")
        finally:
            try:
                self.finalize(result)
            except (OSError, SafetyStop) as exc:
                result = "INCOMPLETE"
                self.output(f"Private evidence finalization failed: {type(exc).__name__}: {exc}")
        self.shutdown_prompt(disconnect=endpoint_selected)
        return result

    def shutdown_prompt(self, *, disconnect: bool) -> None:
        self.output("CLARITYLINK — ROOT TEST COMPLETE\n\nNo further vehicle diagnostic commands are scheduled. Please verify that the factory center display, instrument cluster, audio and warning indicators appear normal. If everything is normal, turn the Honda OFF using its factory controls. Reply `CAR POWERED OFF`. If anything is abnormal, report it instead of assuming ordinary shutdown is appropriate.")
        try:
            ack = self.input("Vehicle shutdown acknowledgment: ").strip()
        except (KeyboardInterrupt, EOFError):
            ack = ""
        if ack == "CAR POWERED OFF":
            if disconnect:
                try:
                    self.transport.disconnect()
                except (OSError, subprocess.TimeoutExpired, SafetyStop):
                    self.output("The host could not confirm ADB disconnection; do not reconnect or start another experiment.")
        else:
            self.output("Host ADB endpoint was not disconnected because power-off was not acknowledged.")

    def finalize(self, result: str) -> None:
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
        resolved_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(resolved_root, 0o700)
        folder = resolved_root / ("CL-STAGEA-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
        folder.mkdir(mode=0o700)
        payload = {"result": result, "adb_serial": self.transport.serial,
                   "eligibility_state": self.eligibility_state,
                   "command_count": self.command_count, "root_command": ROOT_COMMAND if self.command_count else None,
                   "commands": self.records, "created_utc": datetime.now(timezone.utc).isoformat(),
                   "timeout_remote_termination_verified": False}
        path = folder / "manifest.json"
        data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
        path.write_bytes(data); os.chmod(path, 0o600); os.chmod(folder, 0o700)
        sums = folder / "sha256.txt"
        sums.write_text(f"{hashlib.sha256(data).hexdigest()}  manifest.json\n")
        os.chmod(sums, 0o600)
        self.output_dir = folder
        self.output(f"Private evidence finalized: {folder}")


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
