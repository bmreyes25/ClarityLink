#!/usr/bin/env python3
"""Read-only host clock evidence collector. Never sets the system clock.

Queries ordinary NTP servers and, when installed, reads chronyc tracking.
Unauthenticated NTP data is explicitly conditional and never creates an
attestation, trusted bound, reviewer approval, or Phase S authorization.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import socket
import stat
import struct
import subprocess
import sys
import time
from typing import Callable

NTP_EPOCH = 2_208_988_800
NTP_ERA = 1 << 32
NTP_PACKET_SIZE = 48
DEFAULT_SERVERS = ("time.apple.com", "time.cloudflare.com", "time.google.com")
MAX_QUERY_SECONDS = 3.0
CLOCK_STEP_TOLERANCE_SECONDS = 0.050


class EvidenceError(ValueError):
    pass


def utc_from_ns(value: int) -> str:
    return dt.datetime.fromtimestamp(value / 1_000_000_000, dt.timezone.utc).isoformat()


def to_ntp_timestamp(unix_ns: int) -> bytes:
    seconds, ns = divmod(unix_ns, 1_000_000_000)
    ntp_seconds = seconds + NTP_EPOCH
    fraction = (ns << 32) // 1_000_000_000
    return struct.pack("!II", ntp_seconds & 0xFFFFFFFF, fraction & 0xFFFFFFFF)


def from_ntp_timestamp(raw: bytes, pivot_unix_ns: int) -> float:
    if len(raw) != 8:
        raise EvidenceError("NTP timestamp must be 8 bytes")
    seconds, fraction = struct.unpack("!II", raw)
    if seconds == 0 and fraction == 0:
        raise EvidenceError("NTP timestamp is zero")
    pivot_ntp = pivot_unix_ns / 1_000_000_000 + NTP_EPOCH
    era = round((pivot_ntp - seconds) / NTP_ERA)
    expanded_seconds = seconds + era * NTP_ERA
    return expanded_seconds - NTP_EPOCH + fraction / 2**32


def signed_fixed_16_16(raw: bytes) -> float:
    value = struct.unpack("!i", raw)[0]
    return value / 65536.0


def unsigned_fixed_16_16(raw: bytes) -> float:
    value = struct.unpack("!I", raw)[0]
    return value / 65536.0


def parse_response(packet: bytes, request_transmit: bytes, t1_unix_ns: int,
                   t4_unix_ns: int, monotonic_rtt_ns: int,
                   server_identity: dict[str, str]) -> dict[str, object]:
    if len(packet) < NTP_PACKET_SIZE:
        raise EvidenceError("short NTP response")
    leap, version, mode = packet[0] >> 6, (packet[0] >> 3) & 7, packet[0] & 7
    stratum = packet[1]
    if version not in (3, 4) or mode != 4:
        raise EvidenceError("unexpected NTP version or server mode")
    if leap == 3 or stratum == 0 or stratum > 15:
        raise EvidenceError("server is unsynchronized or returned Kiss-o'-Death")
    if packet[24:32] != request_transmit:
        raise EvidenceError("origin timestamp does not match request")
    t1 = t1_unix_ns / 1_000_000_000
    t2 = from_ntp_timestamp(packet[32:40], t1_unix_ns)
    t3 = from_ntp_timestamp(packet[40:48], t1_unix_ns)
    t4 = t4_unix_ns / 1_000_000_000
    server_processing = t3 - t2
    if server_processing < 0 or server_processing > monotonic_rtt_ns / 1_000_000_000:
        raise EvidenceError("server timestamps conflict with observed monotonic round trip")
    delay = (t4 - t1) - server_processing
    if delay < -0.001:
        raise EvidenceError("computed NTP network delay is negative")
    delay = max(0.0, delay)
    offset = ((t2 - t1) + (t3 - t4)) / 2.0  # server time minus host time
    root_delay = signed_fixed_16_16(packet[4:8])
    root_dispersion = unsigned_fixed_16_16(packet[8:12])
    precision_exp = struct.unpack("!b", packet[3:4])[0]
    precision_seconds = 2.0 ** precision_exp if -30 <= precision_exp <= 30 else None
    # NTP synchronization distance + half the measured host-side round trip.
    # Root fields and endpoint are unauthenticated, so this is conditional data,
    # not an externally trusted absolute-error bound.
    rtt = monotonic_rtt_ns / 1_000_000_000
    uncertainty = root_dispersion + abs(root_delay) / 2.0 + rtt / 2.0
    if precision_seconds is not None:
        uncertainty += precision_seconds
    return {
        "server": server_identity,
        "authentication": "UNAUTHENTICATED_ORDINARY_NTP",
        "leap_indicator": leap,
        "version": version,
        "mode": mode,
        "stratum": stratum,
        "reference_id_hex": packet[12:16].hex(),
        "reference_timestamp_unix": (None if packet[16:24] == b"\0" * 8
                                      else from_ntp_timestamp(packet[16:24], t1_unix_ns)),
        "server_receive_utc_unix": t2,
        "server_transmit_utc_unix": t3,
        "offset_server_minus_host_seconds": offset,
        "network_delay_estimate_seconds": delay,
        "monotonic_round_trip_seconds": rtt,
        "root_delay_seconds": root_delay,
        "root_dispersion_seconds": root_dispersion,
        "precision_exponent": precision_exp,
        "precision_seconds": precision_seconds,
        "conditional_uncertainty_seconds": uncertainty,
        "uncertainty_method": "root_dispersion + abs(root_delay)/2 + observed_monotonic_rtt/2 + server_precision; conditional on genuine response and NTP assumptions",
        "raw_response_hex": packet[:NTP_PACKET_SIZE].hex(),
        "raw_response_sha256": hashlib.sha256(packet[:NTP_PACKET_SIZE]).hexdigest(),
    }


def query(server: str, timeout: float = MAX_QUERY_SECONDS,
          socket_factory: Callable[..., socket.socket] = socket.socket,
          wall_ns: Callable[[], int] = time.time_ns,
          monotonic_ns: Callable[[], int] = time.monotonic_ns) -> dict[str, object]:
    addresses = socket.getaddrinfo(server, 123, type=socket.SOCK_DGRAM)
    if not addresses:
        raise EvidenceError("NTP hostname has no UDP address")
    family, socktype, proto, _canon, sockaddr = addresses[0]
    sock = socket_factory(family, socktype, proto)
    try:
        sock.settimeout(timeout)
        sock.connect(sockaddr)
        wall_before_send = wall_ns()
        mono_before_send = monotonic_ns()
        request_transmit = to_ntp_timestamp(wall_before_send)
        request = bytearray(NTP_PACKET_SIZE)
        request[0] = (0 << 6) | (4 << 3) | 3
        request[40:48] = request_transmit
        sock.send(request)
        mono_after_send = monotonic_ns()
        wall_after_send = wall_ns()
        packet = sock.recv(512)
        wall_before_recv = wall_ns()
        mono_before_recv = monotonic_ns()
        wall_after_recv = wall_ns()
        mono_after_recv = monotonic_ns()
        # recv() return and these samples are bracketed; the entire measured
        # monotonic RTT contributes to the uncertainty allowance above.
        send_bracket_ns = max(0, wall_after_send - wall_before_send)
        receive_bracket_ns = max(0, wall_after_recv - wall_before_recv)
        t1 = wall_before_send
        t4 = (wall_before_recv + wall_after_recv) // 2
        rtt_ns = max(0, mono_after_recv - mono_before_send)
        identity = {"hostname": server, "resolved_address": str(sockaddr[0]),
                    "port": "123", "transport": "UDP"}
        result = parse_response(packet, request_transmit, t1, t4, rtt_ns, identity)
        result["request_transmit_hex"] = request_transmit.hex()
        result["send_timestamp_bracket_ns"] = send_bracket_ns
        result["receive_timestamp_bracket_ns"] = receive_bracket_ns
        result["conditional_uncertainty_seconds"] = (
            float(result["conditional_uncertainty_seconds"])
            + (send_bracket_ns + receive_bracket_ns) / 2_000_000_000
        )
        result["send_syscall_elapsed_monotonic_ns"] = max(0, mono_after_send - mono_before_send)
        result["host_receive_sample_utc"] = utc_from_ns(wall_before_recv)
        result["host_receive_sample_monotonic_ns"] = mono_before_recv
        return result
    finally:
        sock.close()


def evaluate(samples: list[dict[str, object]], failures: list[dict[str, str]],
             clock_step_detected: bool) -> dict[str, object]:
    if clock_step_detected:
        status = "INCONCLUSIVE_HOST_CLOCK_STEP"
    elif not samples:
        status = "INCONCLUSIVE_NO_VALID_SOURCE"
    else:
        left = max(float(row["offset_server_minus_host_seconds"]) -
                   float(row["conditional_uncertainty_seconds"]) for row in samples)
        right = min(float(row["offset_server_minus_host_seconds"]) +
                    float(row["conditional_uncertainty_seconds"]) for row in samples)
        if left > right:
            status = "INCONCLUSIVE_CONFLICTING_MEASUREMENTS"
        elif len(samples) == 1:
            status = "CONDITIONAL_SINGLE_UNAUTHENTICATED_SOURCE"
        else:
            status = "CONDITIONAL_CONSISTENT_UNAUTHENTICATED_SOURCES"
    return {
        "decision": status,
        "authenticated_time_source_available": False,
        "trusted_absolute_clock_bound_established": False,
        "samples": samples,
        "source_failures": failures,
        "limitations": [
            "NTP responses are unauthenticated and can be spoofed or modified.",
            "Root delay and root dispersion are server-reported, not independently authenticated.",
            "Agreement does not establish independent upstreams or UTC accuracy.",
            "The uncertainty estimate is conditional on source integrity and the documented path-delay assumptions.",
            "No final attestation or independent reviewer approval is created.",
        ],
    }


def collect(servers: list[str] | tuple[str, ...] = DEFAULT_SERVERS,
            query_fn: Callable[[str], dict[str, object]] = query,
            wall_ns: Callable[[], int] = time.time_ns,
            monotonic_ns: Callable[[], int] = time.monotonic_ns) -> dict[str, object]:
    start_wall, start_mono = wall_ns(), monotonic_ns()
    samples: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []
    for server in servers:
        try:
            samples.append(query_fn(server))
        except (OSError, EvidenceError, subprocess.SubprocessError, ValueError) as exc:
            failures.append({"server": server, "error_type": type(exc).__name__,
                              "message": str(exc)[:256]})
    end_mono, end_wall = monotonic_ns(), wall_ns()
    wall_elapsed = (end_wall - start_wall) / 1e9
    monotonic_elapsed = (end_mono - start_mono) / 1e9
    step_delta = wall_elapsed - monotonic_elapsed
    step_detected = abs(step_delta) > CLOCK_STEP_TOLERANCE_SECONDS
    result = evaluate(samples, failures, step_detected)
    result.update({
        "schema_version": "R7E7I-HOST-TIME-EVIDENCE-1",
        "collector": "tools/r7e7i_host_time_evidence.py",
        "measurement_started_utc": utc_from_ns(start_wall),
        "measurement_finished_utc": utc_from_ns(end_wall),
        "measurement_started_monotonic_ns": start_mono,
        "measurement_finished_monotonic_ns": end_mono,
        "wall_elapsed_seconds": wall_elapsed,
        "monotonic_elapsed_seconds": monotonic_elapsed,
        "wall_minus_monotonic_elapsed_seconds": step_delta,
        "clock_step_detected_by_bracket_check": step_detected,
        "clock_step_tolerance_seconds": CLOCK_STEP_TOLERANCE_SECONDS,
        "chrony_tracking": collect_chrony_tracking(),
    })
    return result


def collect_chrony_tracking() -> dict[str, object]:
    executable = shutil.which("chronyc")
    if not executable:
        return {"available": False, "status": "NOT_INSTALLED", "raw": None}
    try:
        proc = subprocess.run([executable, "tracking"], capture_output=True,
                              text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": True, "status": "QUERY_FAILED", "error_type": type(exc).__name__}
    raw = proc.stdout[-8192:]
    fields: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    required = {"Reference ID", "Stratum", "System time", "Last offset",
                "Root delay", "Root dispersion", "Leap status"}
    if proc.returncode != 0 or not required.issubset(fields):
        status = "INCOMPLETE_TRACKING_OUTPUT"
    elif fields.get("Leap status") != "Normal":
        status = "NOT_SYNCHRONIZED"
    else:
        status = "RAW_TRACKING_AVAILABLE_REQUIRES_INDEPENDENT_REVIEW"
    return {"available": True, "status": status, "returncode": proc.returncode,
            "fields": fields, "raw": raw,
            "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "authentication": "not established by chronyc tracking output alone"}


def save_private(result: dict[str, object], destination: Path) -> tuple[Path, str]:
    if destination.exists() and destination.is_symlink():
        raise EvidenceError("output path must not be a symlink")
    parent = destination.parent
    parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if parent.is_symlink():
        raise EvidenceError("output directory must not be a symlink")
    parent.chmod(0o700)
    payload = json.dumps(result, sort_keys=True, indent=2).encode() + b"\n"
    digest = hashlib.sha256(payload).hexdigest()
    document = dict(result, evidence_sha256=digest)
    final = json.dumps(document, sort_keys=True, indent=2).encode() + b"\n"
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(final)
    return destination, hashlib.sha256(final).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", action="append", dest="servers")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.dry_run:
        print(json.dumps({"decision": "DRY_RUN_NO_NETWORK_NO_CLOCK_CHANGE",
                          "servers": args.servers or list(DEFAULT_SERVERS)}, indent=2))
        return 0
    result = collect(args.servers or DEFAULT_SERVERS)
    destination = args.output or (Path(__file__).resolve().parents[1] /
                                  "build/r7e7i/host-time-evidence" /
                                  f"measurement-{time.time_ns()}.json")
    path, digest = save_private(result, destination)
    print(json.dumps({"decision": result["decision"], "evidence_path": str(path),
                      "evidence_sha256": digest,
                      "trusted_absolute_clock_bound_established": False}, sort_keys=True))
    return 0 if result["samples"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
