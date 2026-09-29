# Honda `jmcs` acquisition and identity verification

## Source preservation

Source is the immutable complete forensic acquisition at `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_ORIGINAL`. The filesystem archive is `filesystems/system.tar`, read-only. The archive SHA-256 recorded by its acquisition manifest is `74f61a07df79fe6e1e63c938b7799b9e1638090ab1e350859391101465b212c9`; that value matches the archive checksum in `/SHA256SUMS`. The tar member is exactly `system/bin/jmcs` (13,406,720 bytes; archived mode 0755). The source directory has no write permission and the archive has mode 0400. No source file was changed.

## Analysis copy

Only the requested tar member was extracted to the offline analysis copy:

`/Users/bmreyes24/ClarityLab/clarity-analysis/extracted/system/system/bin/jmcs`

SHA-256: `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`

The copy hash matches the earlier analyzed binary at `extracted/system-vendor/system/bin/jmcs` and the hash recorded in `research/carplay/jmcs-address-map.md`. The `extracted/` tree is ignored/local and was not staged.

## ELF and address verification

| Property | Verified value |
|---|---|
| ELF | ELF32, little-endian, ET_DYN |
| Machine/ABI | ARM, EABI5, Thumb code |
| Interpreter | `/system/bin/linker` |
| `.text` VA/file offset | starts `0x13100`; matching VA/file-offset layout |
| First PT_LOAD | VA 0, file offset 0, size `0x33fb50` |
| Debug/symbol data | `.symtab`, `.debug_info`, `.rel.dyn`, `.rel.plt` present |

The following symbol addresses agree with the existing static evidence (Thumb symbol values shown):

| Symbol | ELF address |
|---|---:|
| `AirPlayReceiverSessionSetup` | `0x2854e1` |
| `_connectionHandleMessage` | `0x28a30d` |
| `_requestSendPlistResponse` | `0x289f61` |
| `AirPlayReceiverSessionScreen_CopyDisplaysInfo` | `0x287ae1` |
| `ScreenCopyMain` | `0x2a17fd` |

Saved runtime map evidence uses load bias `0x4005a000` for the captured 2026-09-25 process. Representative VA-to-runtime pairs are recorded in `jmcs-address-map.md`; the same analyzed binary hash and VA/file-offset layout underpin those mappings. Checked call-site addresses `0x287ae0`, `0x2854e0`, `0x28a30c`, `0x289f60`, and `0x2a17fc` resolve to matching file offsets. This verifies identity against the known analyzed image; the historical process-specific load bias is not claimed as a current runtime fact.

**Gate:** binary identity verified; offline analysis may proceed.
