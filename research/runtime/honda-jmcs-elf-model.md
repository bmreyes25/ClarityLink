# Honda jmcs ELF model

Exact archived `extracted/system/system/bin/jmcs`: SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; ELF32, little-endian ARM EABI5, `ET_DYN`, interpreter `/system/bin/linker`, Android API 17 identification, no GNU build-id (prior verified Step 40 evidence). Treat as PIE-style dynamically relocated main executable. Not executed.

Existing static evidence records two `PT_LOAD` segments, RX and RW, `p_align=0x1000`; executable segment begins at file offset/VA zero. Thus for the executable segment, `load_bias = runtime_mapping_start - align_down(p_vaddr,page_size)` (at zero-offset segment, mapping start is load bias); `runtime = load_bias + (static_va & ~1)`, restoring bit zero only for a Thumb callable pointer. Historical live base `0x4008f000` is validation only, never a deployment constant.

Known preferred internal call sites: Thumb `AirPlayCopyServerInfo` call-site VA `0x28a158`, branch target `0x282cd4`; Setup call-site VA `0x28af72`, target `0x2854e0`. Full program-header/dynamic/relocation tables are in local symbol/disassembly evidence; this report does not restate unverified counts. No host `readelf` utility was available during this pass, so complete dynamic-section, GOT/PLT, RELRO, export, and exact entry-point recensus is deferred; prior reports establish local binding and `AirPlayCopyServerInfo` is `.symtab` global but not `.dynsym`.

Do not use historical capture values as runtime assumptions. Exact target descriptor must include the whole-file digest and instruction bytes from `research/carplay/honda-hook-fingerprints.md` before any future runtime validation.
