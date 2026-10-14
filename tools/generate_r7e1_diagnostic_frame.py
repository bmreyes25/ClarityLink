#!/usr/bin/env python3
"""Generate the fixed, text-free 800x480 R7E1 offline diagnostic frame."""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

WIDTH = 800
HEIGHT = 480


def pixel(x: int, y: int) -> tuple[int, int, int, int]:
    if x < 12 or x >= WIDTH - 12 or y < 12 or y >= HEIGHT - 12:
        return (0, 0, 0, 255)
    if x < 24 or x >= WIDTH - 24 or y < 24 or y >= HEIGHT - 24:
        return (48, 180, 166, 255)
    if 96 <= x < 256 and 96 <= y < 384:
        return (44, 92, 122, 255)
    if 544 <= x < 704 and 96 <= y < 384:
        return (190, 112, 48, 255)
    if 320 <= x < 480 and 208 <= y < 272:
        return (226, 226, 218, 255)
    return (24, 32, 40, 255)


def chunk(name: bytes, data: bytes) -> bytes:
    payload = name + data
    return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)


def main() -> None:
    rows = bytearray()
    for y in range(HEIGHT):
        rows.append(0)  # PNG filter: None
        for x in range(WIDTH):
            rows.extend(pixel(x, y))
    png = (b"\x89PNG\r\n\x1a\n" +
           chunk(b"IHDR", struct.pack(">2I5B", WIDTH, HEIGHT, 8, 6, 0, 0, 0)) +
           chunk(b"IDAT", zlib.compress(bytes(rows), 9)) +
           chunk(b"IEND", b""))
    output = Path(__file__).resolve().parents[1] / "android/r7e1-display/assets/r7e1-diagnostic-frame.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(png)
    print(f"{output} {len(png)} bytes")


if __name__ == "__main__":
    main()
