#!/usr/bin/env python3
"""Normalize API17 adb-shell PNG output and validate dimensions/chunk CRCs."""
import binascii
import hashlib
import struct
import sys
from pathlib import Path


def valid_png(data):
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 33:
        return None
    width, height = struct.unpack(">II", data[16:24])
    offset = 8
    seen_header = False
    while offset + 12 <= len(data):
        size = struct.unpack(">I", data[offset:offset + 4])[0]
        end = offset + 12 + size
        if end > len(data):
            return None
        kind = data[offset + 4:offset + 8]
        body = data[offset + 4:offset + 8 + size]
        expected = struct.unpack(">I", data[offset + 8 + size:end])[0]
        if binascii.crc32(body) & 0xffffffff != expected:
            return None
        if offset == 8:
            if kind != b"IHDR" or size != 13:
                return None
            seen_header = True
        offset = end
        if kind == b"IEND":
            return (width, height) if seen_header and offset == len(data) else None
    return None


def normalize(data):
    normalized = bytearray()
    index = 0
    while index < len(data):
        if data[index] == 13:
            start = index
            while index < len(data) and data[index] == 13:
                index += 1
            count = index - start
            if index < len(data) and data[index] == 10:
                normalized.extend(b"\r" * (count - 1))
                normalized.append(10)
                index += 1
            else:
                normalized.extend(b"\r" * count)
        else:
            normalized.append(data[index])
            index += 1
    return bytes(normalized)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: normalize_api17_png.py PATH")
    path = Path(sys.argv[1])
    data = path.read_bytes()
    dimensions = valid_png(data)
    if dimensions is None:
        data = normalize(data)
        dimensions = valid_png(data)
    if dimensions is None:
        raise SystemExit("invalid PNG after API17 shell normalization: " + str(path))
    path.write_bytes(data)
    print("PNG_VALID", str(path), "dimensions=%dx%d" % dimensions,
          "bytes=%d" % len(data), "sha256=" + hashlib.sha256(data).hexdigest())


if __name__ == "__main__":
    main()
