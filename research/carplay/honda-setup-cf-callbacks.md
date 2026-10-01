# Honda Setup CF callback tables — Step 43G update

**Artifact:** `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. Static-only. See [Step 43G ownership and cleanup](../../step-reports/43g-setup-cf-ownership-and-network-cleanup.md).

## Address recovery

The ELF is ELF32 little-endian ARM ET_DYN. `llvm-objdump --private-headers` reports a first `PT_LOAD` with `p_offset=p_vaddr=0`, and a second load with `p_offset=0x340988`, `p_vaddr=0x341988`; thus the second segment's file-backed VA-to-file mapping is `file_offset = VA - 0x1000`. `tools/elf_va_map.py` implements the PT_LOAD range mapping and rejects non-file-backed BSS addresses. `llvm-objdump -R` is used separately to confirm dynamic relocation sites; `nm -n` resolves function/table symbols. All three relevant GOT slots have `R_ARM_RELATIVE` entries.

## Setup response constructor (`0x28557e`)

```text
0x28556a ldr r6, [pc, #0x20c]   ; literal at 0x285778 = 0x000c1370
0x285570 add r6, pc             ; GOT slot 0x3468e4
0x285572 ldr r6, [r6]           ; relocated value 0x3428fc
0x28556e ldr r5, [pc, #0x20c]   ; literal at 0x28577c = 0x000c136e
0x285576 add r5, pc             ; GOT slot 0x3468e8
0x285578 ldr r5, [r5]           ; relocated value 0x342914
0x28556c movs r0, #0            ; allocator = NULL
0x285574 mov r1, r0             ; capacity = 0
0x28557a mov r2, r6             ; key callbacks
0x28557c mov r3, r5             ; value callbacks
0x28557e bl CFDictionaryCreateMutable
```

The wrapper at `0x28e4b0` forwards r0-r3 to `CFLDictionaryCreate` and supplies a stack output pointer. `CFLDictionaryCreate` copies six callback words for keys and five for values; NULL callback structures are zeroed. The callback structure slots are:

| Item | Creation-site argument | Resolved address | Target/table | Meaning | Evidence |
|---|---:|---:|---|---|---|
| Allocator | r0 = 0 | NULL | none | default allocator | HONDA_CONFIRMED |
| Capacity | r1 = 0 | 0 | none | default capacity path | HONDA_CONFIRMED |
| Key callbacks | r2 = [GOT] | `0x3428fc` | `kCFLDictionaryKeyCallBacksCFLTypes` | CFType-style key table | HONDA_CONFIRMED |
| Key version | table word 0 | 0 | scalar | callback version | HONDA_CONFIRMED |
| Key retain | table word 1 | `0x28ebc5` | `__CFLContainerRetain` → `CFLRetain` | retaining callback | HONDA_CONFIRMED |
| Key release | table word 2 | `0x28ec49` | `__CFLContainerRelease` → `CFLRelease` | releasing callback | HONDA_CONFIRMED |
| Key description | table word 3 | NULL | none | no description callback | HONDA_CONFIRMED |
| Key equality | table word 4 | `0x28ecd9` | `__CFLContainerEqual` → `CFLEqual` | equality callback | HONDA_CONFIRMED |
| Key hash | table word 5 | `0x28ed25` | `__CFLContainerHash` → `CFLHash` | hash callback | HONDA_CONFIRMED |
| Value callbacks | r3 = [GOT] | `0x342914` | `kCFLDictionaryValueCallBacksCFLTypes` | CFType-style value table | HONDA_CONFIRMED |
| Value retain/release/description/equal | table words 1–4 | `0x28ebc5`, `0x28ec49`, NULL, `0x28ecd9` | wrappers above | retains/releases values; no description; equality | HONDA_CONFIRMED |

`CFDictionaryCreateMutable` has no options/flags argument. The custom-looking Honda symbol names are wrappers, but their direct branch targets establish the retain/release/equality/hash implementations.

## `streams` array constructor (`_AddResponseStream`, `0x284db8`)

On the no-existing-array path, `CFDictionaryGetTypedValue` returns NULL in r0; r1 is set to NULL capacity; the GOT slot at `0x3468ec` resolves to `0x342858`; r2 receives that pointer; the wrapper at `0x28e346` forwards allocator/capacity/callbacks to `CFLArrayCreate` and supplies a NULL `copyDescription` argument.

| Array property | Value | Address/source | Meaning | Evidence |
|---|---|---|---|---|
| Allocator | NULL | r0 = 0 | default allocator | HONDA_CONFIRMED |
| Capacity | 0 | r1 = 0 | default capacity | HONDA_CONFIRMED |
| Callback pointer | `0x342858` | GOT slot `0x3468ec`, `R_ARM_RELATIVE` | `kCFLArrayCallBacksCFLTypes` | HONDA_CONFIRMED |
| Version | 0 | table word 0 | callback version | HONDA_CONFIRMED |
| Retain | `0x28ebc5` | table word 1 | `CFLRetain` wrapper | HONDA_CONFIRMED |
| Release | `0x28ec49` | table word 2 | `CFLRelease` wrapper | HONDA_CONFIRMED |
| Copy description | NULL | table word 3 | no callback | HONDA_CONFIRMED |
| Equality | `0x28ecd9` | table word 4 | `CFLEqual` wrapper | HONDA_CONFIRMED |

`CFLArrayCreate` copies five callback words into its array object. The constructor-site callback table is therefore `CF_TYPE`/retaining.
