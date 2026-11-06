#!/usr/bin/env python3
"""Owner-gated fixed-operation CL-STAGEB-JMCS-CONNECTED-DELTA reader.

Live collection is available only through the named experiment-specific CLI
activation and an interactive owner YES decision. Offline tests use a scripted
transport and never access ADB or a vehicle. Python module internals are not an
OS sandbox; only the reviewed CLI path is supported for collection.
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
import shutil
import stat
import sys
from typing import Callable, Protocol

from collector import FixedAdb, ProcessIdentity, SafetyStop, parse_ps_jmcs
from parsers import (parse_maps, parse_proc_net, parse_proc_net_unix,
                     parse_proc_stat_start_time, parse_status)
from privileged import PrivilegedOperation, PrivilegedRead
import root_identity_stage_a as stage_a


LIVE_COLLECTION_ENABLED = True
EXPERIMENT = "CL-STAGEB-JMCS-CONNECTED-DELTA"
LIVE_STAGE_B_ACTIVATION = "--live-stage-b-connected-delta"
EXPECTED_JMCS_SHA256 = "cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232"
JMCS_STATIC_PATH = "/system/bin/jmcs"
STATIC_CALLSITES = {
    "info_capability_builder_call": 0x28A158,
    "setup_dispatch_call": 0x28AF72,
    "setup_response_serializer_call": 0x28AFBA,
}
# The analyzed ELF's first executable PT_LOAD has p_offset=0 and p_vaddr=0.
# Therefore the offset-zero executable mapping anchors load bias directly;
# no guessed target page size is needed.
JMCS_RX_PT_LOAD_OFFSET = 0
JMCS_RX_PT_LOAD_VADDR = 0
MAX_OPERATION_BYTES = 512 * 1024
MAX_SMALL_OPERATION_BYTES = 64 * 1024
MAX_FD_ROWS = 256
MAX_TIMEOUT_SECONDS = 5
NETWORK_TABLES = ("tcp", "tcp6", "udp", "udp6", "unix")
NETWORK_HEADERS = {
    "tcp": ("sl", "local_address", "rem_address", "st", "tx_queue", "rx_queue",
            "tr", "tm->when", "retrnsmt", "uid", "timeout", "inode"),
    "tcp6": ("sl", "local_address", "rem_address", "st", "tx_queue", "rx_queue",
             "tr", "tm->when", "retrnsmt", "uid", "timeout", "inode"),
    "udp": ("sl", "local_address", "rem_address", "st", "tx_queue", "rx_queue",
            "tr", "tm->when", "retrnsmt", "uid", "timeout", "inode"),
    "udp6": ("sl", "local_address", "rem_address", "st", "tx_queue", "rx_queue",
             "tr", "tm->when", "retrnsmt", "uid", "timeout", "inode"),
    "unix": ("Num", "RefCount", "Protocol", "Flags", "Type", "St", "Inode", "Path"),
}


def owner_disclosure(serial: str) -> str:
    return (f"CLARITYLINK — STAGE B READ-ONLY RECEIVER DELTA\n\nExact ADB endpoint: {serial}. Is the Honda ready for this experiment? Confirm it is stationary outdoors, in Park, the parking brake is engaged, you are present, factory displays and warnings are normal, and CarPlay is disconnected. This fixed reader verifies MY16ADA / Android 4.2.2 and this exact disconnectable TCP/IP endpoint, rechecks target identity, su fingerprint and the read-only mounts covering both su and jmcs before preflight and each collection phase, then performs one final eligibility check after the post-disconnect snapshot. It binds jmcs by ps/stat/status plus transient cmdline and reads bounded FD links, fixed proc network tables and connected-state maps. The private capture includes complete `ps` output and system-wide `/proc/net` tables, which can contain unrelated process names and network endpoints. Important: the su binary is mode 06777 and group/world writable. A complete successful run performs 35 sequential fixed `/system/xbin/su -c` reads, plus five bounded temporary su binary pulls for eligibility. Stage A only authorized one `id` invocation; this new Stage B authorization separately covers those repeated root reads. The helper hash and metadata are checked at eligibility boundaries, but legacy ADB cannot atomically bind the copied bytes to the executable used by each `su` invocation; the read-only mount check is a separate condition and does not prove that binding. This residual integrity race is part of the authorization. Generic su integrity is not a normal PASS. SuperSU may show a prompt or create authorization/log/daemon state. Never approve a late SuperSU prompt after a timeout; a timed-out remote read may still be running. Stop on identity or eligibility mismatch, timeout, permission surprise, process change, unexpected vehicle behavior, or unclear prompt. Factory controls are the restoration route; if behavior is abnormal, stop and use your safety judgment. Type YES to authorize; NOT YET defers without target access; CANCEL declines this session.")


def is_disconnectable_tcp_endpoint(serial: str) -> bool:
    match = re.fullmatch(r"[A-Za-z0-9.-]+:([1-9][0-9]{0,4})", serial)
    return bool(match and 1 <= int(match.group(1)) <= 65535)


@dataclass(frozen=True)
class ReadResult:
    code: int
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    output_limited: bool = False


class Transport(Protocol):
    serial: str
    records: list[dict[str, object]]

    def enumerate_devices(self) -> ReadResult: ...
    def set_serial(self, serial: str) -> None: ...
    def observe(self, operation: str, argument: str = "", *, timeout: int = 5,
                max_bytes: int = MAX_SMALL_OPERATION_BYTES) -> stage_a.Result: ...
    def root_identity_once(self) -> ReadResult: ...
    def read_process(self, operation: str, pid: int) -> ReadResult: ...
    def read_ps(self) -> ReadResult: ...
    def hash_jmcs(self) -> ReadResult: ...
    def read_fd_links(self, pid: int) -> ReadResult: ...
    def read_network(self, table: str) -> ReadResult: ...
    def disconnect(self) -> bool: ...


def _decode_strict(raw: bytes, label: str) -> str:
    try:
        return raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise SafetyStop(f"{label} was not valid UTF-8") from exc


def _require_complete_text(raw: bytes, label: str) -> str:
    if not raw or not raw.endswith(b"\n"):
        raise SafetyStop(f"{label} is empty or incomplete")
    return _decode_strict(raw, label)


def parse_process_identity(ps_raw: bytes, stat_raw: bytes, status_raw: bytes) -> ProcessIdentity:
    """Identify one root-owned jmcs process and bind it to /proc stat start time."""
    ps_text = _require_complete_text(ps_raw, "ps listing")
    pids = parse_ps_jmcs(ps_text)
    if len(pids) != 1:
        raise SafetyStop(f"expected one jmcs process candidate, found {len(pids)}")
    pid = pids[0]
    stat_text = _require_complete_text(stat_raw, "jmcs stat")
    status_text = _require_complete_text(status_raw, "jmcs status")
    values = parse_status(status_text)
    try:
        start = parse_proc_stat_start_time(stat_text)
        stat_prefix = re.match(r"^(\d+) \((.*)\)\s", stat_text, re.DOTALL)
        if stat_prefix is None or int(stat_prefix.group(1)) != pid or stat_prefix.group(2) != "jmcs":
            raise ValueError("stat PID/comm mismatch")
        status_pid = int(values["Pid"])
        name = values["Name"]
        uid = values["Uid"].split()[0]
        gid = values["Gid"].split()[0]
        ppid = values.get("PPid", "")
    except (KeyError, ValueError, IndexError) as exc:
        raise SafetyStop("jmcs process identity fields are incomplete or malformed") from exc
    if status_pid != pid or name != "jmcs" or uid != "0" or gid != "0":
        raise SafetyStop("selected PID is not the root-owned jmcs process")
    return ProcessIdentity(pid, start, JMCS_STATIC_PATH, "", uid, gid, ppid)


def parse_cmdline(raw: bytes) -> tuple[str, ...]:
    if not raw or len(raw) > MAX_SMALL_OPERATION_BYTES or not raw.endswith(b"\x00"):
        raise SafetyStop("jmcs cmdline is empty, oversized, or incomplete")
    try:
        values = tuple(item.decode("utf-8", "strict") for item in raw[:-1].split(b"\x00"))
    except UnicodeDecodeError as exc:
        raise SafetyStop("jmcs cmdline was not valid UTF-8") from exc
    if not values or values[0] != JMCS_STATIC_PATH or any(not item for item in values):
        raise SafetyStop("jmcs cmdline does not identify the pinned native receiver")
    return values


def parse_fd_links(raw: bytes) -> dict[str, dict[str, object]]:
    """Parse a bounded `ls -l /proc/PID/fd` listing without guessing row shape."""
    text = _require_complete_text(raw, "jmcs FD symlink inventory")
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("total ")]
    if not lines or len(lines) > MAX_FD_ROWS:
        raise SafetyStop("jmcs FD inventory is empty or exceeds the row limit")
    result: dict[str, dict[str, object]] = {}
    for line in lines:
        if " -> " not in line:
            raise SafetyStop("jmcs FD inventory contains a malformed symlink row")
        before, target = line.rsplit(" -> ", 1)
        fields = before.split()
        # Android 4.2 toolbox `ls -l` omits GNU's link-count and byte-size fields.
        if len(fields) < 6 or not fields[0].startswith("l") or not target:
            raise SafetyStop("jmcs FD inventory contains a malformed symlink row")
        fd = fields[-1]
        if not fd.isdecimal() or fd in result or "\x00" in target:
            raise SafetyStop("jmcs FD inventory contains an invalid or duplicate descriptor")
        match = re.fullmatch(r"socket:\[(\d+)\]", target)
        if target.startswith("socket:") and match is None:
            raise SafetyStop("jmcs FD inventory contains a malformed socket inode")
        result[fd] = ({"kind": "socket", "socket_inode": int(match.group(1))}
                      if match else {"kind": "other"})
    return result


def parse_network_table(table: str, raw: bytes) -> tuple[dict[str, object], ...]:
    if table not in NETWORK_TABLES:
        raise SafetyStop("network table is outside the fixed allowlist")
    text = _require_complete_text(raw, f"/proc/net/{table}")
    lines = text.splitlines()
    header = tuple(lines[0].split())
    expected = NETWORK_HEADERS[table]
    if table != "unix":
        normalized = header
        if table in ("tcp6", "udp6") and len(header) > 2 and header[2] == "remote_address":
            normalized = header[:2] + ("rem_address",) + header[3:]
        # Kernel versions append ref/pointer/drops columns after inode.
        # The required prefix remains stable and the row parser uses inode at
        # its fixed standard position.
        if normalized[:len(expected)] != expected:
            raise SafetyStop(f"/proc/net/{table} header is malformed or incomplete")
    elif table == "unix" and header not in (expected, expected[:-1]):
        raise SafetyStop("/proc/net/unix header is malformed or incomplete")
    rows: list[dict[str, object]] = []
    for line in lines[1:]:
        columns = line.split(None, 7 if table == "unix" else 12)
        if table == "unix":
            if len(columns) not in (7, 8):
                raise SafetyStop("/proc/net/unix contains a malformed row")
            try:
                inode = int(columns[6], 10)
            except ValueError as exc:
                raise SafetyStop("/proc/net/unix contains an invalid inode") from exc
            rows.append({"table": table, "inode": inode, "state": columns[5],
                         "path_present": len(columns) == 8})
            continue
        if len(columns) < 10:
            raise SafetyStop(f"/proc/net/{table} contains a malformed or incomplete row")
        try:
            local, remote = columns[1], columns[2]
            local_address, local_port = local.rsplit(":", 1)
            remote_address, remote_port = remote.rsplit(":", 1)
            inode = int(columns[9], 10)
            local_port_number = int(local_port, 16)
            remote_port_number = int(remote_port, 16)
            if table in ("tcp6", "udp6"):
                if len(bytes.fromhex(local_address)) != 16 or len(bytes.fromhex(remote_address)) != 16:
                    raise ValueError("IPv6 width")
            else:
                if len(bytes.fromhex(local_address)) != 4 or len(bytes.fromhex(remote_address)) != 4:
                    raise ValueError("IPv4 width")
            if not re.fullmatch(r"[0-9A-Fa-f]{2}", columns[3]):
                raise ValueError("socket state")
        except ValueError as exc:
            raise SafetyStop(f"/proc/net/{table} contains malformed address, port, state, or inode") from exc
        rows.append({"table": table, "local_hex": local, "local_port": local_port_number,
                     "remote_hex": remote, "remote_port": remote_port_number,
                     "state_hex": columns[3].upper(), "inode": inode})
    # The existing vetted parsers decode Linux's little-endian address words.
    # Apply their IPv4/IPv6 semantics only after the stricter completeness and
    # row-shape checks above, then require a one-to-one result.
    if table == "unix":
        try:
            parsed = parse_proc_net_unix(text)
        except ValueError as exc:
            raise SafetyStop("/proc/net/unix could not be parsed") from exc
        if len(parsed) != len(rows):
            raise SafetyStop("/proc/net/unix parser did not account for every row")
        for row, source in zip(rows, parsed):
            row["socket_type"] = source["type"]
            row["path_present"] = bool(source["path"])
    else:
        family = 6 if table.endswith("6") else 4
        try:
            parsed = parse_proc_net(text, table, family)
        except ValueError as exc:
            raise SafetyStop(f"/proc/net/{table} addresses could not be decoded") from exc
        if len(parsed) != len(rows):
            raise SafetyStop(f"/proc/net/{table} parser did not account for every row")
        for row, source in zip(rows, parsed):
            # TcpSocket's legacy field names say *_hex, but parse_proc_net
            # returns its decoded dotted/colon-form addresses in those fields.
            row["local_address"] = source.local_hex
            row["remote_address"] = source.remote_hex
    return tuple(rows)


def attribute_sockets(fd_links: dict[str, dict[str, object]],
                      network: dict[str, tuple[dict[str, object], ...]]) -> tuple[dict[str, object], ...]:
    by_inode: dict[int, list[dict[str, object]]] = {}
    for rows in network.values():
        for row in rows:
            inode = row.get("inode")
            if isinstance(inode, int):
                by_inode.setdefault(inode, []).append(row)
    matches: list[dict[str, object]] = []
    for fd, target in sorted(fd_links.items(), key=lambda item: int(item[0])):
        inode = target.get("socket_inode")
        if not isinstance(inode, int):
            continue
        for row in by_inode.get(inode, ()):
            state = row.get("state_hex")
            matches.append({"fd": int(fd), "socket_inode": inode,
                            "ownership": "jmcs_fd_symlink_inode_exact_match",
                            "state": "LISTEN" if state == "0A" else
                                     "ESTABLISHED" if state == "01" else "OTHER_OR_UNKNOWN",
                            "endpoint": dict(row)})
    return tuple(matches)


def compare_socket_snapshots(before: dict[str, object], after: dict[str, object]) -> dict[str, object]:
    """Report exact observed owned-socket row changes; do not assign protocol roles."""
    def keyed(snapshot: dict[str, object]) -> dict[str, dict[str, object]]:
        matches = snapshot.get("owned_socket_matches")
        if not isinstance(matches, list):
            raise SafetyStop("socket snapshot is incomplete")
        result: dict[str, dict[str, object]] = {}
        for row in matches:
            if not isinstance(row, dict) or not isinstance(row.get("fd"), int) or not isinstance(row.get("socket_inode"), int):
                raise SafetyStop("socket snapshot row is malformed")
            key = f"{row['fd']}:{row['socket_inode']}:{json.dumps(row.get('endpoint', {}), sort_keys=True)}"
            result[key] = row
        return result
    old, new = keyed(before), keyed(after)
    return {"added_owned_socket_rows": [new[key] for key in sorted(new.keys() - old.keys())],
            "removed_owned_socket_rows": [old[key] for key in sorted(old.keys() - new.keys())],
            "unchanged_owned_socket_row_count": len(old.keys() & new.keys()),
            "interpretation_limit": "observed FD/inode/table row changes only; no stream role is inferred"}


def calculate_runtime_callsites(maps_raw: bytes) -> dict[str, object]:
    text = _require_complete_text(maps_raw, "connected jmcs maps")
    try:
        mappings = parse_maps(text)
    except ValueError as exc:
        raise SafetyStop("connected jmcs maps are malformed") from exc
    if not mappings:
        raise SafetyStop("connected jmcs maps are empty")
    ordered = sorted(mappings, key=lambda item: item.start)
    for previous, current in zip(ordered, ordered[1:]):
        if previous.end > current.start:
            raise SafetyStop("connected jmcs maps contain overlapping intervals")
    anchors = [m for m in mappings if m.pathname == JMCS_STATIC_PATH
               and m.offset == JMCS_RX_PT_LOAD_OFFSET and "x" in m.permissions]
    if len(anchors) != 1:
        raise SafetyStop("connected maps do not identify one offset-zero executable jmcs mapping")
    anchor = anchors[0]
    bias = anchor.start - JMCS_RX_PT_LOAD_VADDR
    if bias < 0 or bias > 0xFFFFFFFF:
        raise SafetyStop("connected jmcs load bias is outside ARM32")
    calls: dict[str, object] = {}
    for name, static_va in STATIC_CALLSITES.items():
        if static_va & 1:
            raise SafetyStop("static Thumb callsite must be represented as an even instruction VA")
        runtime_even = bias + static_va
        if runtime_even > 0xFFFFFFFF or not any(
                m.pathname == JMCS_STATIC_PATH and "x" in m.permissions
                and m.start <= runtime_even < m.end for m in mappings):
            raise SafetyStop("connected jmcs mapping does not cover a static candidate callsite")
        calls[name] = {"static_instruction_va": f"0x{static_va:08x}",
                       "runtime_instruction_address_even": f"0x{runtime_even:08x}",
                       "runtime_thumb_function_pointer_odd": f"0x{runtime_even | 1:08x}"}
    return {"load_bias": f"0x{bias:08x}",
            "anchor": "prior-static-analysis ELF assertion: p_offset=0 and p_vaddr=0; runtime maps row is path-correlated at file offset 0; controller does not rederive ELF headers, and process image inode is not independently matched",
            "thumb_distinction": "instruction addresses are even; callable Thumb pointers set bit 0",
            "callsites": calls}


class AdbTransport:
    """Fixed ADB transport; only the operation table below reaches the target."""
    def __init__(self, *, activation: str | None = None) -> None:
        if (not LIVE_COLLECTION_ENABLED or activation != LIVE_STAGE_B_ACTIVATION
                or not (sys.stdin.isatty() and sys.stdout.isatty())):
            raise SafetyStop("fixed live transport requires the named interactive Stage B activation")
        self._activation_enabled = True
        self._adb_path = shutil.which("adb")
        if not self._adb_path:
            raise SafetyStop("adb executable was not found")
        self._serial = ""
        self._fixed: FixedAdb | None = None
        self._stage_a_transport = stage_a.AdbTransport()
        self._owner_authorized = False
        self._authorization_attempted = False
        self.interrupted_operation_kind: str | None = None

    @property
    def owner_authorized(self) -> bool:
        return self._owner_authorized

    @property
    def activation_enabled(self) -> bool:
        return self._activation_enabled

    @property
    def serial(self) -> str:
        return self._serial

    def _revoke_owner_authorization(self) -> None:
        self._owner_authorized = False

    def _require_enabled(self) -> None:
        if not LIVE_COLLECTION_ENABLED or not self.activation_enabled:
            raise SafetyStop("live Stage B transport is not activated for this fixed experiment")

    def _require_live(self) -> None:
        self._require_enabled()
        if not self.owner_authorized:
            raise SafetyStop("live transport operations require the Stage B owner YES authorization")

    def authorize_owner(self) -> str:
        self._require_enabled()
        if self._authorization_attempted:
            raise SafetyStop("owner authorization is single-use for this Stage B invocation")
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            raise SafetyStop("live owner authorization requires an interactive terminal")
        if not is_disconnectable_tcp_endpoint(self.serial):
            raise SafetyStop("the exact TCP/IP ADB endpoint must be bound before owner authorization")
        self._authorization_attempted = True
        print(owner_disclosure(self.serial))
        try:
            answer = input("Do you authorize CL-STAGEB-JMCS-CONNECTED-DELTA? Type YES, NOT YET, or CANCEL: ").strip()
        except (EOFError, KeyboardInterrupt):
            answer = "CANCEL"
        if answer not in {"YES", "NOT YET", "CANCEL"}:
            answer = "CANCEL"
        self._owner_authorized = answer == "YES"
        return answer

    def enumerate_devices(self) -> ReadResult:
        self._require_live()
        host_reader = FixedAdb("stage-b-host-operations", resolve_auto=False)
        command = host_reader.plan("host-devices", ())
        try:
            code, stdout, stderr = host_reader._run_planned(
                command, "stage_b_adb_devices", (), timeout=MAX_TIMEOUT_SECONDS,
                max_bytes=MAX_SMALL_OPERATION_BYTES)
        except KeyboardInterrupt:
            self.interrupted_operation_kind = "host"
            raise
        record = host_reader.records[-1] if host_reader.records else {}
        return ReadResult(code, stdout, stderr, record.get("result") == "timeout",
                          bool(record.get("truncated")) or record.get("result") == "output_limit")

    def set_serial(self, serial: str) -> None:
        # Binding the checked serial only builds local fixed plans; it makes no ADB call.
        self._require_enabled()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", serial) or serial.lower() == "auto":
            raise SafetyStop("exact ADB serial syntax is invalid")
        if self.owner_authorized and serial != self.serial:
            raise SafetyStop("the ADB endpoint cannot change after owner authorization")
        self._serial = serial
        self._fixed = FixedAdb(serial, resolve_auto=False)
        self._stage_a_transport.set_serial(serial)

    def _reader(self) -> FixedAdb:
        if self._fixed is None:
            raise SafetyStop("exact ADB serial has not been selected")
        return self._fixed

    def observe(self, operation: str, argument: str = "", *, timeout: int = 5,
                max_bytes: int = MAX_SMALL_OPERATION_BYTES) -> stage_a.Result:
        self._require_live()
        try:
            result = self._stage_a_transport.observe(operation, argument,
                                                     timeout=min(max(timeout, 1), MAX_TIMEOUT_SECONDS),
                                                     max_bytes=min(max(max_bytes, 1), MAX_SMALL_OPERATION_BYTES))
        except KeyboardInterrupt:
            self.interrupted_operation_kind = "target_metadata"
            raise
        return result

    def _read(self, label: str, plan: tuple[str, ...], *, timeout: int = MAX_TIMEOUT_SECONDS,
              limit: int = MAX_OPERATION_BYTES, params: tuple[str, ...] = ()) -> ReadResult:
        self._require_live()
        reader = self._reader()
        try:
            code, stdout, stderr = reader._run_planned(plan, f"stage_b_{label}", params,
                                                       timeout=timeout, max_bytes=limit)
        except KeyboardInterrupt:
            self.interrupted_operation_kind = (
                "privileged" if "/system/xbin/su" in plan else "target")
            raise
        record = reader.records[-1] if reader.records else {}
        return ReadResult(code, stdout, stderr,
                          record.get("result") == "timeout",
                          bool(record.get("truncated")) or record.get("result") == "output_limit")

    def root_identity_once(self) -> ReadResult:
        self._require_live()
        try:
            result = self._stage_a_transport.root_identity_once()
        except KeyboardInterrupt:
            self.interrupted_operation_kind = "privileged"
            raise
        return ReadResult(result.code, result.stdout, result.stderr, result.timed_out,
                          result.output_limited)

    def hash_jmcs(self) -> ReadResult:
        reader = self._reader()
        return self._read("jmcs_hash", reader.plan("hash-jmcs", ()), limit=MAX_SMALL_OPERATION_BYTES)

    def _privileged(self) -> PrivilegedRead:
        return PrivilegedRead(self._reader())

    def _proc(self, pid: int, leaf: str) -> ReadResult:
        operation = PrivilegedOperation.PROCESS_READ
        plan = self._privileged().plan(operation, pid=pid, leaf=leaf)
        return self._read(f"process_{leaf}", plan, limit=MAX_OPERATION_BYTES,
                          params=(f"pid={pid}", f"leaf={leaf}"))

    def read_process(self, operation: str, pid: int) -> ReadResult:
        leaf_by_operation = {"stat": "stat", "status": "status", "cmdline": "cmdline", "maps": "maps"}
        if operation not in leaf_by_operation or isinstance(pid, bool) or pid <= 0:
            raise SafetyStop("process operation is outside the Stage B allowlist")
        return self._proc(pid, leaf_by_operation[operation])

    def read_ps(self) -> ReadResult:
        reader = self._reader()
        return self._read("ps", reader.plan("ps", ()), limit=MAX_SMALL_OPERATION_BYTES)

    def read_fd_links(self, pid: int) -> ReadResult:
        if isinstance(pid, bool) or pid <= 0:
            raise SafetyStop("invalid PID for FD inventory")
        plan = self._privileged().plan(PrivilegedOperation.FD_LIST, pid=pid)
        return self._read("fd_links", plan, limit=MAX_OPERATION_BYTES, params=(f"pid={pid}",))

    def read_network(self, table: str) -> ReadResult:
        if table not in NETWORK_TABLES:
            raise SafetyStop("network table is outside the Stage B allowlist")
        plan = self._privileged().plan(PrivilegedOperation.NETWORK_READ, table=table)
        return self._read(f"network_{table}", plan, limit=MAX_OPERATION_BYTES,
                          params=(f"table={table}",))

    def disconnect(self) -> bool:
        self._require_live()
        # `adb disconnect` only detaches TCP/IP endpoints. Refuse USB and
        # ambiguous serial forms rather than claiming host-side cleanup.
        if not is_disconnectable_tcp_endpoint(self.serial):
            return False
        reader = self._reader()
        result = self._read("adb_disconnect", (self._adb_path, "disconnect", self.serial),
                            limit=MAX_SMALL_OPERATION_BYTES)
        return (result.code == 0 and not result.timed_out and not result.output_limited
                and not result.stderr.strip()
                and f"disconnected {self.serial}".encode() in result.stdout)


class StageBCapture:
    def __init__(self, reader: FixedAdb | None, output: Path, serial: str):
        self.reader = reader
        self.output = output
        self.serial = serial
        self.created_utc = datetime.now(timezone.utc).isoformat()
        self.files: list[dict[str, object]] = []
        self.commands: list[dict[str, object]] = []
        self.identities: dict[str, dict[str, object]] = {}
        self.phases: list[str] = []
        self.stop_reason: str | None = None
        self.owner_authorized = False
        self.owner_decision: str | None = None
        self.analysis: dict[str, object] = {}

    def record(self, phase: str, name: str, result: ReadResult, *, pid: int | None = None,
               persist: bool = True, params: tuple[str, ...] = ()) -> None:
        oversized = (len(result.stdout) > MAX_OPERATION_BYTES
                     or len(result.stderr) > MAX_SMALL_OPERATION_BYTES)
        redact_stdout = name == "process_cmdline"
        row: dict[str, object] = {
            "phase": phase, "operation": name, "parameters": list(params),
            "exit_code": result.code, "timed_out": result.timed_out,
            "output_limited": result.output_limited,
            "stdout_bytes": None if redact_stdout else len(result.stdout),
            "stderr_bytes": len(result.stderr),
            "stdout_sha256": None if redact_stdout else hashlib.sha256(result.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(), "pid": pid,
            "rejected_oversize": oversized, "stdout_redacted": redact_stdout,
        }
        self.commands.append(row)
        if oversized:
            # Preserve integrity metadata for partial captures without writing
            # an output that exceeded the reviewed storage ceiling.
            raise SafetyStop("operation output exceeded the host-side capture ceiling")
        if persist:
            relative = Path(phase) / f"{name}.raw"
            target = self.output / relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            target.write_bytes(result.stdout)
            target.chmod(0o600)
            self.files.append({"path": relative.as_posix(), "bytes": len(result.stdout),
                               "sha256": hashlib.sha256(result.stdout).hexdigest(), "pid": pid})
            if result.stderr:
                error = target.with_suffix(".stderr.raw")
                error.write_bytes(result.stderr)
                error.chmod(0o600)
                self.files.append({"path": error.relative_to(self.output).as_posix(),
                                   "bytes": len(result.stderr),
                                   "sha256": hashlib.sha256(result.stderr).hexdigest(), "pid": pid})

    def finalize(self, result: str) -> None:
        self.output.mkdir(mode=0o700, parents=True, exist_ok=True)
        manifest = {
            "experiment": EXPERIMENT, "result": result,
            "created_utc": self.created_utc, "finalized_utc": datetime.now(timezone.utc).isoformat(),
            "adb_serial": self.serial, "phases_captured": self.phases,
            "owner_authorization_accepted": self.owner_authorized,
            "owner_decision": self.owner_decision,
            "process_identities": self.identities, "commands": self.commands,
            "artifacts": self.files, "analysis": self.analysis,
            "stop_reason": self.stop_reason,
            "privacy": {"raw_evidence_private_only": True, "media_or_keys_captured": False,
            "process_memory_read": False, "target_code_or_files_modified": False,
                        "potential_su_side_effects_acknowledged": self.owner_authorized},
        }
        data = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        manifest_path = self.output / "manifest.json"
        manifest_path.write_bytes(data)
        manifest_path.chmod(0o600)
        entries = []
        for path in sorted(self.output.rglob("*")):
            if path.is_file() and path.name != "sha256.txt":
                entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(self.output)}")
        sums_path = self.output / "sha256.txt"
        sums_path.write_text("\n".join(entries) + "\n", encoding="ascii")
        sums_path.chmod(0o600)
        self.output.chmod(0o700)


def verify_private_root(root: Path, repo_root: Path) -> Path:
    expanded = root.expanduser()
    if expanded.is_symlink():
        raise SafetyStop("private evidence root may not be a symlink")
    resolved = expanded.resolve()
    if any((ancestor / ".git").exists() for ancestor in (resolved, *resolved.parents)):
        raise SafetyStop("private evidence root must be outside every Git checkout/worktree")
    if resolved.is_relative_to(repo_root.resolve()):
        raise SafetyStop("private evidence root must be outside the Git worktree")
    existing = resolved
    missing: list[Path] = []
    while not existing.exists():
        missing.append(existing)
        existing = existing.parent
    if not existing.is_dir():
        raise SafetyStop("private evidence parent is not a directory")
    for path in reversed(missing):
        path.mkdir(mode=0o700)
    info = resolved.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise SafetyStop("private evidence root must be owner-owned with mode 0700")
    return resolved


def _require_read(result: ReadResult, label: str) -> bytes:
    if result.code != 0 or result.timed_out or result.output_limited or result.stderr.strip():
        diagnostic = (result.stderr + b"\n" + result.stdout).decode("utf-8", "replace").lower()
        if "permission denied" in diagnostic or "operation not permitted" in diagnostic:
            raise SafetyStop(f"permission denied during fixed {label} read")
        raise SafetyStop(f"fixed {label} read failed, timed out, or was incomplete")
    return result.stdout


class StageB:
    def __init__(self, transport: Transport, *, input_fn: Callable[[str], str] = input,
                 output_fn: Callable[[str], None] = print,
                 evidence_root: Path | None = None, repo_root: Path | None = None,
                 offline_simulation: bool = False):
        if not isinstance(transport, AdbTransport) and not offline_simulation:
            raise SafetyStop("non-ADB transports are permitted only for explicit offline simulation")
        if isinstance(transport, AdbTransport) and offline_simulation:
            raise SafetyStop("live ADB transports cannot use the offline-simulation path")
        if isinstance(transport, AdbTransport) and not transport.activation_enabled:
            raise SafetyStop("live Stage B controller requires the explicit fixed-experiment activation")
        self.transport = transport
        self.offline_simulation = offline_simulation
        self.input = input_fn
        self.output = output_fn
        self.repo_root = repo_root or Path(__file__).resolve().parents[2]
        self.evidence_root = evidence_root or Path.home() / "Library/Application Support/ClarityLink/comprehensive-runtime/evidence"
        self.capture: StageBCapture | None = None
        self.identity: ProcessIdentity | None = None
        self.root_authorized = False
        self.phase_count = 0
        self.target_ops_started = False

    def _record(self, phase: str, name: str, result: ReadResult, *, pid: int | None = None,
                params: tuple[str, ...] = (), persist: bool = True) -> bytes:
        assert self.capture is not None
        self.capture.record(phase, name, result, pid=pid, params=params, persist=persist)
        return _require_read(result, name)

    def _enumerate_and_bind(self, serial: str) -> None:
        assert self.capture is not None
        result = self.transport.enumerate_devices()
        self.capture.record("preflight", "adb_devices", result, params=(), persist=False)
        data = _require_read(result, "ADB device enumeration")
        lines = data.decode("utf-8", "strict").splitlines()
        if not lines or lines[0].strip() != "List of devices attached":
            raise SafetyStop("ADB device list header was malformed")
        rows = [line.split() for line in lines[1:] if line.strip()]
        if (len(rows) != 1 or len(rows[0]) < 2 or rows[0][0] != serial
                or rows[0][1] != "device" or any(token.lower().startswith("usb:") for token in rows[0][2:])):
            raise SafetyStop("exact ADB endpoint is wrong, USB-backed, unauthorized, or ambiguous")
        self.transport.set_serial(serial)
        self.capture.serial = serial

    def _check_stage_a_eligibility(self) -> None:
        assert self.capture is not None
        mount_bytes: bytes | None = None
        # Reuse the separately reviewed controlled-diagnostic procedure. The
        # generic validator is unchanged and still rejects mode 06777.
        def observe(operation: str, argument: str = "", *, timeout: int = 5,
                    max_bytes: int = stage_a.MAX_OUTPUT) -> stage_a.Result:
            nonlocal mount_bytes
            result = self.transport.observe(operation, argument, timeout=timeout, max_bytes=max_bytes)
            if operation == "mounts":
                mount_bytes = result.stdout
            persist = operation != "su-binary"
            raw = ReadResult(result.code, result.stdout, result.stderr,
                             result.timed_out, result.output_limited)
            self.capture.record("preflight", f"eligibility_{operation}_{len(self.capture.commands):02d}",
                                raw, params=tuple(x for x in (argument,) if x), persist=persist)
            if (result.code != 0 or result.timed_out or result.output_limited
                    or (operation != "su-binary" and result.stderr.strip())):
                raise SafetyStop(f"fixed controlled-eligibility read failed or was incomplete: {operation}")
            if operation == "su-binary":
                # Never retain a system binary; only the reviewed hash/size
                # result is retained by the Stage A eligibility row.
                self.capture.analysis["su_binary_sha256"] = hashlib.sha256(result.stdout).hexdigest()
                self.capture.analysis["su_binary_bytes"] = len(result.stdout)
            return result

        class EligibilityTransport:
            serial = self.transport.serial
            def observe(_self, operation: str, argument: str = "", **kwargs: object) -> stage_a.Result:
                return observe(operation, argument, **kwargs)  # type: ignore[arg-type]

        # candidate() has no prompt today; refuse automatically if a future revision adds one.
        checker = stage_a.StageA(EligibilityTransport(), input_fn=lambda _: "CANCEL", output_fn=lambda _: None)
        if not checker.candidate():
            raise SafetyStop("controlled root eligibility did not pass")
        if mount_bytes is None:
            raise SafetyStop("mount table was not retained for the jmcs executable mount check")
        jmcs_mount = stage_a.covering_mount(mount_bytes, JMCS_STATIC_PATH)
        if (not jmcs_mount.get("complete") or jmcs_mount.get("read_only") is not True
                or jmcs_mount.get("read_write") is not False or jmcs_mount.get("overlay_uncertainty")):
            raise SafetyStop("the complete covering mount for /system/bin/jmcs is not uniquely read-only")
        self.capture.analysis["jmcs_mount_eligibility"] = {
            "mount_point": jmcs_mount.get("mount_point"),
            "read_only": jmcs_mount.get("read_only"),
            "overlay_uncertainty": jmcs_mount.get("overlay_uncertainty", []),
        }
        eligibility = dict(checker.records[-1])
        eligibility["exception"] = (
            "Stage B-specific multi-read controlled diagnostic; current mode 06777 remains group/world writable; generic integrity is not PASS")
        eligibility["fingerprint_binding"] = (
            "copied su bytes are fingerprinted at each eligibility pass, but legacy ADB cannot atomically bind those bytes to every later executable invocation; the covering read-only mount is separately verified")
        self.capture.analysis["root_eligibility"] = eligibility
        self.capture.analysis["stage_b_scope"] = (
            "separate owner-authorized Stage B controlled diagnostic: 35 fixed read-only /system/xbin/su -c reads in a complete run across the three collection phases and preflight; five bounded temporary su binary pulls support eligibility, including one final post-snapshot check; Stage A's id-only scope is not reused; generic su integrity is not PASS")

    def _read_one(self, phase: str, operation: str, pid: int) -> bytes:
        result = self.transport.read_process(operation, pid)
        return self._record(phase, f"process_{operation}", result, pid=pid,
                            params=(f"pid={pid}", f"leaf={operation}"))

    def _identity_snapshot(self, phase: str, *, expected: ProcessIdentity | None = None,
                           cmdline: bool = False) -> ProcessIdentity:
        assert self.capture is not None
        ps_method = getattr(self.transport, "read_ps", None)
        if not callable(ps_method):
            raise SafetyStop("transport lacks the fixed ps operation")
        ps_raw = self._record(phase, "ps", ps_method())
        pids = parse_ps_jmcs(_require_complete_text(ps_raw, "ps listing"))
        if len(pids) != 1:
            raise SafetyStop(f"expected one jmcs process candidate, found {len(pids)}")
        pid = pids[0]
        stat_raw = self._read_one(phase, "stat", pid)
        status_raw = self._read_one(phase, "status", pid)
        identity = parse_process_identity(ps_raw, stat_raw, status_raw)
        if expected is not None and (identity.pid != expected.pid or identity.start_time_ticks != expected.start_time_ticks):
            raise SafetyStop("jmcs process epoch changed; refusing cross-process differential")
        if cmdline:
            cmd_result = self.transport.read_process("cmdline", pid)
            cmd_raw = self._record(phase, "process_cmdline", cmd_result, pid=pid,
                                   params=(f"pid={pid}", "leaf=cmdline"), persist=False)
            args = parse_cmdline(cmd_raw)
            self.capture.analysis[f"{phase}_cmdline_argument_count"] = len(args)
            self.capture.analysis[f"{phase}_cmdline_raw_persisted"] = False
        self.capture.identities[phase] = {"pid": identity.pid,
                                          "start_time_ticks": identity.start_time_ticks,
                                          "uid": identity.uid, "gid": identity.gid,
                                          "expected_executable_path": identity.executable,
                                          "cmdline_argv0_verified": cmdline}
        return identity

    def _fd_and_socket_snapshot(self, phase: str, identity: ProcessIdentity) -> dict[str, object]:
        assert self.capture is not None
        fd_result = self.transport.read_fd_links(identity.pid)
        fd_raw = self._record(phase, "fd_links", fd_result, pid=identity.pid,
                              params=(f"pid={identity.pid}",))
        fd_links = parse_fd_links(fd_raw)
        network: dict[str, tuple[dict[str, object], ...]] = {}
        for table in NETWORK_TABLES:
            result = self.transport.read_network(table)
            raw = self._record(phase, f"network_{table}", result, pid=identity.pid,
                               params=(f"table={table}",))
            network[table] = parse_network_table(table, raw)
        owned = attribute_sockets(fd_links, network)
        summary = {"fd_count": len(fd_links),
                   "socket_fd_count": sum(item.get("kind") == "socket" for item in fd_links.values()),
                   "owned_socket_matches": list(owned),
                   "unmatched_socket_fd_count": sum(
                       item.get("kind") == "socket" and not any(
                           entry["fd"] == int(fd) for entry in owned)
                       for fd, item in fd_links.items()),
                   "role_limit": "FD/inode ownership only; an endpoint is not called a Type110 or Type111 stream without correlated code/protocol evidence"}
        self.capture.analysis.setdefault("socket_snapshots", {})[phase] = summary
        return summary

    def _baseline(self) -> None:
        assert self.capture is not None
        identity = self._identity_snapshot("baseline", cmdline=True)
        self.identity = identity
        hash_reader = getattr(self.transport, "hash_jmcs", None)
        if not callable(hash_reader):
            raise SafetyStop("transport lacks the fixed jmcs file hash operation")
        digest_raw = self._record("baseline", "jmcs_file_hash", hash_reader(),
                                  params=(JMCS_STATIC_PATH,))
        match = re.fullmatch(rb"([0-9a-fA-F]{64})\s+/system/bin/jmcs\s*\n?", digest_raw)
        if not match or match.group(1).decode().lower() != EXPECTED_JMCS_SHA256:
            raise SafetyStop("current jmcs file hash does not match the analyzed receiver ELF")
        self.capture.analysis["jmcs_file_sha256"] = match.group(1).decode().lower()
        self.capture.analysis["executable_binding"] = (
            "ps, proc stat PID/comm, status PID/name, and transient cmdline argv0 agree; current /system/bin/jmcs hash and its covering mount are checked; /proc/PID/exe is not exposed by the archived API-17 toolbox evidence, so the running image inode is not independently asserted")
        self._fd_and_socket_snapshot("baseline", identity)
        end = self._identity_snapshot("baseline_epoch_end", expected=identity)
        self.identity = end
        self.capture.phases.append("baseline_disconnected")

    def _connected(self) -> None:
        assert self.capture is not None and self.identity is not None
        identity = self._identity_snapshot("connected", expected=self.identity, cmdline=True)
        hash_result = getattr(self.transport, "hash_jmcs", None)
        if not callable(hash_result):
            raise SafetyStop("transport lacks the fixed jmcs file hash operation")
        digest_raw = self._record("connected", "jmcs_file_hash", hash_result(),
                                  params=(JMCS_STATIC_PATH,))
        match = re.fullmatch(rb"([0-9a-fA-F]{64})\s+/system/bin/jmcs\s*\n?", digest_raw)
        if not match or match.group(1).decode().lower() != EXPECTED_JMCS_SHA256:
            raise SafetyStop("current jmcs file hash does not match the analyzed receiver ELF")
        self.capture.analysis["jmcs_file_sha256"] = match.group(1).decode().lower()
        maps_raw = self._read_one("connected", "maps", identity.pid)
        self.capture.analysis["connected_runtime_callsites"] = calculate_runtime_callsites(maps_raw)
        self._fd_and_socket_snapshot("connected", identity)
        end = self._identity_snapshot("connected_epoch_end", expected=identity)
        self.identity = end
        self.capture.phases.append("connected_factory_carplay")

    def _post_disconnect(self) -> None:
        assert self.capture is not None and self.identity is not None
        identity = self._identity_snapshot("post_disconnect", expected=self.identity, cmdline=True)
        hash_result = getattr(self.transport, "hash_jmcs", None)
        if not callable(hash_result):
            raise SafetyStop("transport lacks the fixed jmcs file hash operation")
        digest_raw = self._record("post_disconnect", "jmcs_file_hash", hash_result(),
                                  params=(JMCS_STATIC_PATH,))
        match = re.fullmatch(rb"([0-9a-fA-F]{64})\s+/system/bin/jmcs\s*\n?", digest_raw)
        if not match or match.group(1).decode().lower() != EXPECTED_JMCS_SHA256:
            raise SafetyStop("current jmcs file hash does not match the analyzed receiver ELF")
        self._fd_and_socket_snapshot("post_disconnect", identity)
        end = self._identity_snapshot("post_disconnect_epoch_end", expected=identity)
        self.identity = end
        self.capture.phases.append("post_disconnect")

    def _owner_gate(self) -> str:
        if not self.offline_simulation and not (sys.stdin.isatty() and sys.stdout.isatty()):
            raise SafetyStop("live owner authorization requires an interactive terminal")
        if isinstance(self.transport, AdbTransport):
            return self.transport.authorize_owner()
        disclosure = owner_disclosure(self.transport.serial)
        self._emit(disclosure)
        try:
            answer = self.input("Do you authorize CL-STAGEB-JMCS-CONNECTED-DELTA? Type YES, NOT YET, or CANCEL: ").strip()
            return answer if answer in {"YES", "NOT YET", "CANCEL"} else "CANCEL"
        except (EOFError, KeyboardInterrupt):
            return "CANCEL"

    def _shutdown(self, endpoint_selected: bool, *, after_abort: bool = False) -> bool:
        privileged_operations = {
            "root_identity", "process_stat", "process_status", "process_cmdline",
            "process_maps", "fd_links", *(f"network_{table}" for table in NETWORK_TABLES),
        }
        timed_out = bool(self.capture and any(
            row.get("timed_out") and row.get("operation") in privileged_operations
            for row in self.capture.commands))
        interrupted = getattr(self.transport, "interrupted_operation_kind", None) == "privileged"
        if timed_out or interrupted:
            assert self.capture is not None
            self.capture.analysis["remote_operation_may_still_be_running"] = True
            if timed_out:
                self._emit("A privileged read timed out; the remote operation may still be running. Do not approve any late SuperSU prompt. No retry will run.")
            else:
                self._emit("A read was interrupted; the remote operation may still be running. Do not approve any late SuperSU prompt. No retry will run.")
        self._emit("No more target reads will run. Check factory displays, audio, warnings, and vehicle behavior.")
        if after_abort:
            try:
                normal = self.input("Is factory behavior normal and stable? Type NORMAL only if yes; otherwise STOP: ").strip()
            except (EOFError, KeyboardInterrupt):
                normal = "STOP"
            if normal != "NORMAL":
                self._emit("Stop here. Do not attempt power-off or ADB disconnect through this controller; use your safety judgment.")
                return False
        self._emit("If factory behavior is normal, turn the Honda off with factory controls and reply CAR POWERED OFF only after shutdown.")
        try:
            ack = self.input("Vehicle shutdown acknowledgment: ").strip()
        except (EOFError, KeyboardInterrupt):
            ack = ""
        if ack != "CAR POWERED OFF":
            self._emit("ADB was not disconnected because power-off was not acknowledged.")
            return False
        if endpoint_selected:
            try:
                disconnected = self.transport.disconnect()
            except (Exception, KeyboardInterrupt):
                disconnected = False
            if not disconnected:
                self._emit("ADB disconnect was not confirmed; stop here and do not start another experiment.")
                return False
        return True

    def _phase_gate(self, expected: str, prompt: str) -> bool:
        try:
            return self.input(prompt).strip() == expected
        except (EOFError, KeyboardInterrupt):
            return False

    def _emit(self, message: str) -> None:
        try:
            self.output(message)
        except (OSError, KeyboardInterrupt):
            pass

    def run(self, serial: str) -> str:
        status = "INCOMPLETE"
        endpoint_selected = False
        if not self.offline_simulation and (not isinstance(self.transport, AdbTransport)
                                            or not LIVE_COLLECTION_ENABLED
                                            or not getattr(self.transport, "activation_enabled", False)):
            raise SafetyStop("live Stage B collection is disabled in this source revision")
        if self.offline_simulation and isinstance(self.transport, AdbTransport):
            raise SafetyStop("live ADB transports cannot use the offline-simulation path")
        if not self.offline_simulation and not (sys.stdin.isatty() and sys.stdout.isatty()):
            raise SafetyStop("live owner authorization requires an interactive terminal")
        evidence_root = verify_private_root(self.evidence_root, self.repo_root)
        output = evidence_root / f"{EXPERIMENT}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')}"
        output.mkdir(mode=0o700)
        self.capture = StageBCapture(None, output, serial)
        try:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", serial) or serial.lower() == "auto" or not is_disconnectable_tcp_endpoint(serial):
                raise SafetyStop("an exact serial naming a disconnectable IPv4/hostname TCP/IP ADB endpoint is required; USB/IPv6/ambiguous endpoints are unsupported")
            self.transport.set_serial(serial)
            decision = self._owner_gate()
            self.capture.owner_decision = decision
            if decision != "YES":
                status = "NOT_YET" if decision == "NOT YET" else "CANCELLED"
                self.capture.stop_reason = f"owner selected {decision} before target access"
                return status
            self.capture.owner_authorized = True
            if not self.offline_simulation and not self.transport.owner_authorized:
                raise SafetyStop("live transport did not record interactive Stage B owner authorization")
            self._enumerate_and_bind(serial)
            endpoint_selected = True
            self.target_ops_started = True
            self._check_stage_a_eligibility()
            root = self.transport.root_identity_once()
            self._record("preflight", "root_identity", ReadResult(root.code, root.stdout, root.stderr,
                         root.timed_out, root.output_limited))
            if not stage_a.root_is_uid_zero(root):
                raise SafetyStop("fresh controlled root identity did not return exactly UID 0")
            self.capture.analysis["root_identity"] = "UID 0 verified; no other identity fields retained"
            state_method = getattr(self.transport, "observe")
            state = state_method("state")
            self._record("preflight", "adb_state", ReadResult(state.code, state.stdout, state.stderr,
                         state.timed_out, state.output_limited))
            if state.code or state.stdout.strip() != b"device":
                raise SafetyStop("exact ADB endpoint is no longer authorized and online")
            if not self._phase_gate("DISCONNECTED", "Confirm iPhone remains disconnected and factory state is normal. Type DISCONNECTED: "):
                raise SafetyStop("owner did not confirm disconnected baseline")
            self._check_stage_a_eligibility()
            self._baseline()
            if not self._phase_gate("CONNECTED", "Now connect the iPhone through normal wired factory CarPlay, wait for normal center-display operation, and type CONNECTED: "):
                raise SafetyStop("owner did not confirm normal connected CarPlay")
            self._check_stage_a_eligibility()
            self._connected()
            if not self._phase_gate("DISCONNECTED", "Now disconnect CarPlay normally, wait for factory behavior to return, and type DISCONNECTED: "):
                raise SafetyStop("owner did not confirm normal CarPlay disconnect")
            self._check_stage_a_eligibility()
            self._post_disconnect()
            # Close the final interval in which the writable helper could
            # have changed after the preceding phase eligibility checks.
            self._check_stage_a_eligibility()
            self.capture.analysis["differential"] = {
                "baseline_to_connected": compare_socket_snapshots(
                    self.capture.analysis["socket_snapshots"]["baseline"],
                    self.capture.analysis["socket_snapshots"]["connected"]),
                "connected_to_post_disconnect": compare_socket_snapshots(
                    self.capture.analysis["socket_snapshots"]["connected"],
                    self.capture.analysis["socket_snapshots"]["post_disconnect"]),
                "newly_observed": "current same-epoch jmcs FD/socket ownership and connected maps/runtime callsites",
                "protocol_role_limit": "maps and FD/socket correlations do not identify a socket as Type110 or Type111 without independent code/protocol correlation",
                "loader_limit": "a maps pathname/hash correlation can identify current mapped jmcs, but cannot prove an extension ABI or observe unsupported runtime state",
            }
            status = "COMPLETE_OFFLINE_REVIEW_REQUIRED"
            if not self._shutdown(endpoint_selected):
                status = "INCOMPLETE_SHUTDOWN_OR_DISCONNECT_ACK"
                self.capture.stop_reason = "owner power-off acknowledgment or host ADB disconnect was not confirmed"
                self.capture.analysis["shutdown_ack"] = "not_confirmed"
            else:
                self.capture.analysis["shutdown_ack"] = "confirmed"
                self.capture.analysis["adb_disconnect_ack"] = "confirmed" if endpoint_selected else "not_required"
            return status
        except Exception as exc:
            assert self.capture is not None
            self.capture.stop_reason = f"{type(exc).__name__}: {exc}"
            status = "SAFE_ABORT"
            self._emit(f"Stage B stopped: {type(exc).__name__}: {exc}. No retry or fallback will run.")
            if self.target_ops_started:
                if not self._shutdown(endpoint_selected, after_abort=True):
                    self.capture.analysis["shutdown_ack"] = "not_confirmed"
                else:
                    self.capture.analysis["shutdown_ack"] = "confirmed"
            return status
        except KeyboardInterrupt:
            assert self.capture is not None
            self.capture.stop_reason = "KeyboardInterrupt: interrupted"
            status = "SAFE_ABORT"
            self._emit("Stage B interrupted. No retry or fallback will run.")
            if self.target_ops_started:
                if not self._shutdown(endpoint_selected, after_abort=True):
                    self.capture.analysis["shutdown_ack"] = "not_confirmed"
                else:
                    self.capture.analysis["shutdown_ack"] = "confirmed"
            return status
        finally:
            assert self.capture is not None
            try:
                self.capture.finalize(status)
            finally:
                if isinstance(self.transport, AdbTransport):
                    self.transport._revoke_owner_authorization()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="exact current ADB serial supplied by the owner")
    parser.add_argument("--output-root", type=Path,
                        default=Path.home() / "Library/Application Support/ClarityLink/comprehensive-runtime/evidence")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="print fixed operation templates without ADB")
    modes.add_argument(LIVE_STAGE_B_ACTIVATION, dest="live_stage_b", action="store_true",
                       help="run only CL-STAGEB-JMCS-CONNECTED-DELTA after interactive owner authorization")
    args = parser.parse_args(argv)
    if args.dry_run:
        print("Offline only; no ADB enumeration or target command was sent. Fixed host and target operation plan:")
        for operation, tail in (
                ("endpoint", "adb devices -l; exact selected TCP/IP serial only"),
                ("identity", "fixed MY16ADA/Android properties; /proc/self/mounts; su metadata and exact binary fingerprint"),
                ("root", "adb -s <serial> shell /system/xbin/su -c id (once)"),
                ("baseline process", "adb shell ps; su -c cat /proc/<pid>/{stat,status,cmdline}; sha256sum /system/bin/jmcs"),
                ("baseline sockets", "su -c ls -l /proc/<pid>/fd; cat /proc/net/{tcp,tcp6,udp,udp6,unix}"),
                ("connected", "cat /proc/<pid>/maps once; repeat bounded FD/socket snapshot and epoch checks"),
                ("post-disconnect", "repeat process identity plus transient cmdline validation and jmcs hash, then bounded FD/socket snapshot"),
                ("host shutdown", "adb disconnect <exact TCP/IP serial> only after owner confirms CAR POWERED OFF")):
            print(f"{operation}: {tail}")
        print("successful full-session totals: exactly 35 fixed /system/xbin/su -c reads and five bounded temporary su binary pulls")
        print(f"Live execution requires {LIVE_STAGE_B_ACTIVATION} and interactive owner authorization.")
        return 0
    if not args.live_stage_b:
        print(f"No live experiment selected. Use --dry-run, or explicitly select {LIVE_STAGE_B_ACTIVATION}.", file=sys.stderr)
        return 2
    if not LIVE_COLLECTION_ENABLED:
        print("Live Stage B collection is disabled in this source revision.", file=sys.stderr)
        return 2
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("Live Stage B collection requires an interactive terminal for owner authorization.", file=sys.stderr)
        return 2
    try:
        transport = AdbTransport(activation=(LIVE_STAGE_B_ACTIVATION if args.live_stage_b else None))
        status = StageB(transport, evidence_root=args.output_root).run(args.serial)
    except (SafetyStop, OSError, ValueError) as exc:
        print(f"Stage B could not start: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0 if status == "COMPLETE_OFFLINE_REVIEW_REQUIRED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
