"""Host-only parsers for bounded read-only Android proc captures."""

from __future__ import annotations

from dataclasses import dataclass, field
import ipaddress
import re
from typing import Iterable


@dataclass(frozen=True)
class Mapping:
    start: int
    end: int
    permissions: str
    offset: int
    device: str
    inode: int
    pathname: str = ""


def parse_maps(text: str) -> tuple[Mapping, ...]:
    result: list[Mapping] = []
    for line in text.splitlines():
        parts = line.split(None, 5)
        if len(parts) < 5:
            raise ValueError("malformed maps row")
        try:
            lo_text, hi_text = parts[0].split("-", 1)
            lo, hi = int(lo_text, 16), int(hi_text, 16)
            offset = int(parts[2], 16)
            inode = int(parts[4], 10)
        except (ValueError, IndexError) as exc:
            raise ValueError("malformed maps address/metadata") from exc
        if lo < 0 or hi <= lo or len(parts[1]) != 4:
            raise ValueError("invalid maps interval or permission field")
        result.append(Mapping(lo, hi, parts[1], offset, parts[3], inode,
                              parts[5] if len(parts) == 6 else ""))
    return tuple(result)


@dataclass(frozen=True)
class SmapsEntry:
    mapping: Mapping
    fields: dict[str, str] = field(default_factory=dict)


def parse_smaps(text: str) -> tuple[SmapsEntry, ...]:
    entries: list[SmapsEntry] = []
    current_map: list[str] | None = None
    current_fields: dict[str, str] = {}

    def finish() -> None:
        if current_map is None:
            return
        header = " ".join(current_map)
        parsed = parse_maps(header)
        if len(parsed) != 1:
            raise ValueError("invalid smaps header")
        entries.append(SmapsEntry(parsed[0], dict(current_fields)))

    for line in text.splitlines():
        if re.match(r"^[0-9a-fA-F]+-[0-9a-fA-F]+\s", line):
            finish()
            current_map = line.split()
            current_fields = {}
        elif current_map is not None and ":" in line:
            name, value = line.split(":", 1)
            current_fields[name.strip()] = value.strip()
    finish()
    return tuple(entries)


def parse_status(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


_SIGNALS = {
    1: "HUP", 2: "INT", 3: "QUIT", 4: "ILL", 5: "TRAP", 6: "ABRT",
    7: "BUS", 8: "FPE", 9: "KILL", 10: "USR1", 11: "SEGV", 12: "USR2",
    13: "PIPE", 14: "ALRM", 15: "TERM", 16: "STKFLT", 17: "CHLD",
    18: "CONT", 19: "STOP", 20: "TSTP", 21: "TTIN", 22: "TTOU",
    23: "URG", 24: "XCPU", 25: "XFSZ", 26: "VTALRM", 27: "PROF",
    28: "WINCH", 29: "IO", 30: "PWR", 31: "SYS",
}


def decode_signal_mask(mask: str | int) -> tuple[str, ...]:
    """Decode Linux/ARM signal bits 1..64; retain target numbering, not host ABI."""
    value = int(mask, 16) if isinstance(mask, str) else mask
    if value < 0 or value >= (1 << 64):
        raise ValueError("signal mask must fit 64 bits")
    names = []
    for number in range(1, 65):
        if value & (1 << (number - 1)):
            name = _SIGNALS.get(number, f"RTMIN+{number - 32}" if number >= 32 else f"SIG{number}")
            names.append(f"{number}:{name}")
    return tuple(names)


def parse_proc_stat_start_time(text: str) -> int:
    """Return field 22 despite spaces and parentheses in comm (field 2)."""
    right = text.rfind(")")
    if right < 0:
        raise ValueError("malformed proc stat comm")
    fields_from_3 = text[right + 1:].split()
    if len(fields_from_3) <= 19:
        raise ValueError("proc stat lacks start-time field")
    try:
        return int(fields_from_3[19])
    except ValueError as exc:
        raise ValueError("invalid proc stat start time") from exc


def parse_task_listing(text: str) -> tuple[int, ...]:
    tids = []
    for item in text.split():
        if item.isdecimal():
            tids.append(int(item))
    if len(tids) != len(set(tids)):
        raise ValueError("duplicate task id")
    return tuple(sorted(tids))


def parse_thread_status(text: str) -> dict[str, str]:
    values = parse_status(text)
    return {key: values[key] for key in
            ("Name", "State", "Tgid", "Pid", "PPid", "SigPnd", "ShdPnd", "SigBlk", "SigIgn", "SigCgt")
            if key in values}


@dataclass(frozen=True)
class TcpSocket:
    protocol: str
    local_hex: str
    local_port: int
    remote_hex: str
    remote_port: int
    state: str
    inode: int


def parse_proc_net_unix(text: str) -> tuple[dict[str, str], ...]:
    rows = []
    for line in text.splitlines()[1:]:
        columns = line.split(None, 7)
        if len(columns) < 7:
            continue
        try:
            inode = int(columns[6], 10)
        except ValueError as exc:
            raise ValueError("malformed proc unix socket inode") from exc
        rows.append({"number": columns[0], "refcount": columns[1], "protocol": columns[2],
                     "flags": columns[3], "type": columns[4], "state": columns[5],
                     "inode": str(inode), "path": columns[7] if len(columns) > 7 else ""})
    return tuple(rows)


def _decode_proc_address(value: str, family: int) -> str:
    raw = bytes.fromhex(value)
    if family == 4:
        raw = raw[::-1]
    elif family == 6:
        if len(raw) != 16:
            raise ValueError("invalid IPv6 proc address")
        raw = b"".join(raw[i:i + 4][::-1] for i in range(0, 16, 4))
    return str(ipaddress.ip_address(raw))


def parse_proc_net(text: str, protocol: str, family: int = 4) -> tuple[TcpSocket, ...]:
    """Parse Linux /proc/net/{tcp,tcp6,udp,udp6}; socket data remains observational."""
    result = []
    for line in text.splitlines()[1:]:
        columns = line.split()
        if len(columns) < 10:
            continue
        try:
            local_hex, local_port_hex = columns[1].split(":")
            remote_hex, remote_port_hex = columns[2].split(":")
            result.append(TcpSocket(protocol, _decode_proc_address(local_hex, family),
                                    int(local_port_hex, 16),
                                    _decode_proc_address(remote_hex, family),
                                    int(remote_port_hex, 16), columns[3], int(columns[9])))
        except (ValueError, IndexError) as exc:
            raise ValueError("malformed proc network row") from exc
    return tuple(result)


@dataclass(frozen=True)
class Gap:
    start: int
    end: int
    info_distance: int
    setup_distance: int

    @property
    def size(self) -> int:
        return self.end - self.start


def thumb_bl_range(callsite: int) -> tuple[int, int]:
    """Inclusive even target-address range for Thumb BL at an even callsite."""
    if callsite < 0 or callsite > 0xFFFFFFFF or callsite & 1:
        raise ValueError("callsite must be an even ARM32 address")
    pc = callsite + 4
    lo = max(0, pc - (1 << 24))
    hi = min(0xFFFFFFFE, pc + (1 << 24) - 2)
    if lo & 1:
        lo += 1
    if hi & 1:
        hi -= 1
    return lo, hi


def address_distance(address: int, callsite: int) -> int:
    return abs(address - (callsite + 4))


def mapping_gaps(mappings: Iterable[Mapping], lo: int, hi_inclusive: int) -> tuple[tuple[int, int], ...]:
    """Return half-open unmapped gaps clipped to an inclusive ARM32 reach range."""
    if lo < 0 or hi_inclusive < lo or hi_inclusive > 0xFFFFFFFF:
        raise ValueError("invalid address interval")
    end_limit = hi_inclusive + 1
    occupied = sorted((max(lo, m.start), min(end_limit, m.end)) for m in mappings
                      if m.end > lo and m.start < end_limit)
    gaps = []
    cursor = lo
    for start, end in occupied:
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < end_limit:
        gaps.append((cursor, end_limit))
    return tuple(gaps)


def aligned_candidate(gap: tuple[int, int], page_size: int) -> tuple[int, int] | None:
    if page_size <= 0:
        raise ValueError("page size must be positive")
    start, end = gap
    aligned = ((start + page_size - 1) // page_size) * page_size
    if aligned + page_size <= end:
        return aligned, aligned + page_size
    return None


def load_bias_from_mapping(mapping: Mapping, *, segment_offset: int, segment_vaddr: int,
                           page_size: int) -> int:
    if page_size <= 0:
        raise ValueError("page size must be positive")
    off_page = segment_offset // page_size * page_size
    va_page = segment_vaddr // page_size * page_size
    if mapping.offset != off_page or "x" not in mapping.permissions:
        raise ValueError("mapping does not match executable PT_LOAD file offset/permissions")
    bias = mapping.start - va_page
    if not 0 <= bias <= 0xFFFFFFFF:
        raise ValueError("invalid ARM32 load bias")
    return bias


def runtime_address(static_va: int, bias: int, mappings: Iterable[Mapping]) -> int:
    if static_va & 1:
        raise ValueError("static instruction VA must be even")
    address = bias + static_va
    if address > 0xFFFFFFFF:
        raise ValueError("runtime address overflows ARM32")
    if not any(m.start <= address < m.end and "x" in m.permissions for m in mappings):
        raise ValueError("runtime callsite is outside executable mapping")
    return address


def sanitize_summary_text(text: str) -> str:
    """Redact common personal/device identifiers before prose enters Git.

    This is defense in depth only. Raw data stays outside Git and summaries
    still require human review because no finite pattern set catches every ID.
    """
    text = re.sub(r"(?i)\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b", "<MAC>", text)
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "<IP>", text)
    text = re.sub(r"(?i)\b[A-HJ-NPR-Z0-9]{17}\b", "<VIN_OR_DEVICE_ID>", text)
    text = re.sub(r"(?i)\b(phone|device|serial|ssid|password|token|secret|auth(?:entication)?[_ -]?key)"
                  r"(\s*[:=]\s*)[^\s,;]+", r"\1\2<REDACTED>", text)
    return text
