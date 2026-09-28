# `jmcs` address map

Binary analyzed: `extracted/system-vendor/system/bin/jmcs` (local ignored vendor artifact; do not stage).

| Property | Value |
|---|---|
| SHA-256 | `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` |
| Format / architecture | ELF32 little-endian ET_DYN, ARM EABI5, 32-bit ARM/Thumb code |
| ELF load base | 0; addresses in the disassembly/symbol table are ELF virtual addresses |
| Runtime load bias | `0x4005a000` in the saved 2026-09-25 `/proc/<pid>/maps` snapshot; ASLR/runtime-specific |
| `.text` | VA `0x13100..0x2b3c82`, file offset begins `0x13100`, size `0x2a0b82` |
| First PT_LOAD | VA `0`, file offset `0`, filesz/memsz `0x33fb50`; VA equals file offset for addresses in this segment |
| Symbol table | Present: `.symtab`, 33,662 symbols per native manifest; DWARF debug info present |
| Relocations | Present: `.rel.dyn`, `.rel.plt` |
| Decompiler project | No IDA/Ghidra project database found in the local project. ELF, symbols, DWARF and generated disassembly are available. |

For the listed VAs, file offset equals the even Thumb instruction address (`symbol_value & ~1`). Runtime address in the cited snapshot is runtime load bias plus ELF VA.

| Reference | Function/instruction VA | File offset | Snapshot runtime address |
|---|---:|---:|---:|
| Screen setup dispatch call | `0x28609c` | `0x28609c` | `0x402c009c` |
| `CFDictionaryGetValue` helper | `0x294598` | `0x294598` | `0x402ef598` |
| `ServerSocketOpen` | `0x2a0a34` (Thumb symbol `0x2a0a35`) | `0x2a0a34` | `0x402faa34` |
| `SocketAccept` | `0x2a0480` (Thumb symbol `0x2a0481`) | `0x2a0480` | `0x402fa480` |
| `mc_stream_alloc_buf` | `0x8e70c` (Thumb symbol `0x8e70d`) | `0x8e70c` | `0x400e770c` |

**Address map: VALID.** All addresses are within the first load segment, and the ELF file-offset/VA relationship is identity for these locations. The saved `jmcs` map confirms the runtime bias only for that captured process.
