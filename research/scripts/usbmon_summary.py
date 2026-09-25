#!/usr/bin/env python3
"""Summarize Linux usbmon text bulk events; no iAP2 interpretation is attempted."""
import argparse
from dataclasses import dataclass
import json
import pathlib
import re

ADDRESS = re.compile(r"^B([io]):(\d+):(\d+):(\d+)$")
HEX = re.compile(r"^[0-9a-fA-F]+$")


@dataclass(frozen=True)
class BulkEvent:
    tag: str
    timestamp_us: int
    event: str
    bus: int
    device: int
    endpoint: int
    direction: str
    declared_length: int
    payload: bytes | None
    truncated: bool


def parse_bulk_line(line):
    fields = line.split()
    if len(fields) < 7 or fields[2] not in ("S", "C", "E"):
        return None
    address = ADDRESS.fullmatch(fields[3])
    if not address:
        return None
    try:
        timestamp = int(fields[1])
        declared = int(fields[5])
    except ValueError:
        return None
    if declared < 0 or fields[6] not in ("=", ">", "<"):
        return None
    payload = None
    if fields[6] == "=":
        joined = "".join(fields[7:])
        if not joined or len(joined) % 2 or HEX.fullmatch(joined) is None:
            return None
        payload = bytes.fromhex(joined)
        if len(payload) > declared:
            payload = payload[:declared]
    return BulkEvent(fields[0], timestamp, fields[2], int(address[2]),
                     int(address[3]), int(address[4]),
                     "in" if address[1] == "i" else "out", declared, payload,
                     payload is not None and len(payload) < declared)


def summarize(events):
    events = list(events)
    endpoints = {}
    for item in events:
        key = f"bus{item.bus}:device{item.device}:ep{item.endpoint}:{item.direction}"
        row = endpoints.setdefault(key, {"events": 0, "declaredBytes": 0,
                                         "capturedBytes": 0, "omitted": 0, "truncated": 0})
        row["events"] += 1
        row["declaredBytes"] += item.declared_length
        if item.payload is None:
            row["omitted"] += 1
        else:
            row["capturedBytes"] += len(item.payload)
            row["truncated"] += int(item.truncated)
    return {"events": len(events),
            "payloadOmitted": sum(item.payload is None for item in events),
            "payloadTruncated": sum(item.truncated for item in events),
            "endpoints": endpoints,
            "interpretation": "USB bulk event summary only; no iAP2 or CarPlay capability decoded"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=pathlib.Path)
    args = parser.parse_args()
    with args.trace.open(errors="replace") as source:
        events = [event for line in source if (event := parse_bulk_line(line)) is not None]
    print(json.dumps(summarize(events), indent=2))


if __name__ == "__main__":
    main()
