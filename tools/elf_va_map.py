#!/usr/bin/env python3
"""Small, deterministic ELF load-segment address mapper (ELF32/64, LE)."""
from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path


class ELFMapError(ValueError):
    pass


@dataclass(frozen=True)
class LoadSegment:
    file_offset: int
    virtual_address: int
    file_size: int
    memory_size: int
    flags: int


class ELFAddressMap:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        if len(self.data) < 16 or self.data[:4] != b"\x7fELF":
            raise ELFMapError("not an ELF file")
        elf_class, encoding = self.data[4], self.data[5]
        if encoding != 1 or elf_class not in (1, 2):
            raise ELFMapError("only little-endian ELF32/ELF64 is supported")
        self.elf_class = elf_class
        if elf_class == 1:
            fmt, hdr_size, ph_fmt, ph_size = "<16sHHIIIIIHHHHHH", 52, "<IIIIIIII", 32
        else:
            fmt, hdr_size, ph_fmt, ph_size = "<16sHHIQQQIHHHHHH", 64, "<IIQQQQQQ", 56
        if len(self.data) < hdr_size:
            raise ELFMapError("truncated ELF header")
        header = struct.unpack_from(fmt, self.data)
        phoff, phentsize, phnum = header[5], header[9], header[10]
        if phentsize < ph_size or phoff + phentsize * phnum > len(self.data):
            raise ELFMapError("invalid or truncated program-header table")
        self.load_segments: list[LoadSegment] = []
        for i in range(phnum):
            raw = struct.unpack_from(ph_fmt, self.data, phoff + i * phentsize)
            if elf_class == 1:
                p_type, p_offset, p_vaddr, _paddr, p_filesz, p_memsz, p_flags, _align = raw
            else:
                p_type, p_flags, p_offset, p_vaddr, _paddr, p_filesz, p_memsz, _align = raw
            if p_type == 1:
                if p_offset + p_filesz > len(self.data) or p_filesz > p_memsz:
                    raise ELFMapError("invalid PT_LOAD bounds")
                self.load_segments.append(LoadSegment(p_offset, p_vaddr, p_filesz, p_memsz, p_flags))
        if not self.load_segments:
            raise ELFMapError("ELF has no PT_LOAD segments")

    def file_offset_to_va(self, offset: int, size: int = 1) -> int:
        if offset < 0 or size < 0:
            raise ELFMapError("offset and size must be nonnegative")
        for seg in self.load_segments:
            if seg.file_offset <= offset and offset + size <= seg.file_offset + seg.file_size:
                return seg.virtual_address + offset - seg.file_offset
        raise ELFMapError(f"file range 0x{offset:x}+0x{size:x} is outside file-backed PT_LOAD segments")

    def va_to_file_offset(self, address: int, size: int = 1, *, thumb: bool = False) -> int:
        if thumb:
            address &= ~1
        if address < 0 or size < 0:
            raise ELFMapError("address and size must be nonnegative")
        for seg in self.load_segments:
            if seg.virtual_address <= address and address + size <= seg.virtual_address + seg.file_size:
                return seg.file_offset + address - seg.virtual_address
        raise ELFMapError(f"VA range 0x{address:x}+0x{size:x} is outside file-backed PT_LOAD segments")

    def read_va(self, address: int, size: int, *, thumb: bool = False) -> bytes:
        offset = self.va_to_file_offset(address, size, thumb=thumb)
        return self.data[offset:offset + size]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file-offset", type=lambda x: int(x, 0))
    group.add_argument("--va", type=lambda x: int(x, 0))
    parser.add_argument("--size", type=lambda x: int(x, 0), default=1)
    parser.add_argument("--thumb", action="store_true", help="normalize a Thumb function VA by clearing bit 0")
    args = parser.parse_args()
    mapper = ELFAddressMap(args.elf)
    for seg in mapper.load_segments:
        print(f"PT_LOAD off=0x{seg.file_offset:x} va=0x{seg.virtual_address:x} "
              f"filesz=0x{seg.file_size:x} memsz=0x{seg.memory_size:x} flags=0x{seg.flags:x}")
    if args.file_offset is not None:
        print(f"VA=0x{mapper.file_offset_to_va(args.file_offset, args.size):x}")
    else:
        print(f"FILE_OFFSET=0x{mapper.va_to_file_offset(args.va, args.size, thumb=args.thumb):x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
