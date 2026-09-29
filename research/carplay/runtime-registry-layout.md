# `mc_devs` runtime registry layout (known fields only)

Date: 2026-09-29. Static evidence review; no live process memory read.

The ELF is ARM ELF32, so pointers/words are 4 bytes. “Size” below means proven allocation/minimum accessed extent, not an invented complete C type. Unknown fields remain unknown. The design depends on offline confirmation of the node's `+0x04` field before treating it as registration context.

## Structures

### Manager (`devmgr_h`)

| Property | Finding |
|---|---|
| Struct | `devmgr_h` (DWARF type name) |
| Size | **Unknown**; minimum proven accessed extent is `0x14` bytes because manager `+0x10` is loaded in `dev_attach` (with `+0x0c` used in a subsequent comparison-key access). This does not establish full size. |
| `+0x08` | 4-byte pointer to first registry/list node; `dev_attach` starts traversal here. Purpose: list head. Confidence: high/confirmed use. |
| `+0x0c` | 4-byte pointer to the current tail-link location. `devmgr_app_register` loads it, writes the new node through that address, then updates this field to the new node (whose `+0x00` is its next-link word). Purpose: append state. Confidence: confirmed from instructions at `0x830ec..0x830f4`. |
| `+0x10` | 4-byte word/pointer-like value loaded in `dev_attach`; downstream use includes `+0x0c`. Purpose/type: unknown. Not needed to locate the registry. Confidence: confirmed access, semantics unknown. |
| Other offsets | Unknown; do not read. |

The `mc_devs` cell is a separate global pointer cell, not part of this manager layout: ELF VA `0x35acbc`; prior live base `0x4008f000` yielded cell `0x403e9cbc`. Confidence: high (DWARF plus prior mapping calculation); runtime address must be recalculated from current mappings.

### Registry/list node

| Property | Finding |
|---|---|
| Struct | Registration/list node; C type/name unknown |
| Size | Allocation size `0x0c` bytes in `devmgr_app_register`; high confidence for allocator request. This is the only complete size currently established. |
| `+0x00` | 4-byte next-node pointer; followed by `dev_attach`. High confidence. |
| `+0x04` | 4-byte pointer to the incoming link location used when this node is appended (`[manager+0x0c]` before append). This is registration/list bookkeeping, **not candidate context**. Confidence: confirmed store at `0x830ee`; downstream unlink role is strongly indicated by the field but should not be described more narrowly absent unregister disassembly. |
| `+0x08` | 4-byte candidate interface pointer, stored by registration and loaded by scan. High confidence. |

The head is stored at manager `+0x08`. Registration order (head insertion versus tail insertion) is not documented; the observation must call ordinal “traversal order” until offline review establishes its relationship to chronological insertion.

### Candidate interface

| Property | Finding |
|---|---|
| Struct | Callback interface; C type/name not established |
| Size | Registration validates three 4-byte words at offsets `+0x00`, `+0x04`, `+0x08`; minimum validated extent `0x0c`. Complete type size otherwise unknown. |
| `+0x00` | 4-byte function pointer called during candidate scan; ranking/match callback. High confidence. |
| `+0x04` | 4-byte function pointer called for selected entry by `dev_attach_to_app`; attach callback. High confidence. |
| `+0x08` | Third interface word checked by registration validation; semantic use in this traversal not identified. Type/purpose unknown; not required for requested slot `+0/+4` recovery. |

### Context pointer

The exact `devmgr_app_register` disassembly clarifies its ABI: `r0=manager`, `r1=interface`, `r2=output registration-handle pointer`. It allocates 12 bytes, stores the interface at node `+0x08`, initializes node `+0x00`, and stores the previous manager tail-link value at node `+0x04`. Registration callbacks receive the interface pointer as their second argument, so the callback context pointer requested by the observation is the interface pointer itself (same address as `interface`); there is no separate context word in this node layout. Confidence: high from ARM instructions `0x83080`, `0x8308a`, `0x8308c`, `0x830e6..0x830f6` and scan call dataflow. The manager tail-link update appends nodes; therefore list traversal order is chronological registration order, and is the tie order used by the strict-greater scan.

## Minimum read shape

Confirmed required bytes for registry and callback recovery: global cell 4; manager head 4; each allocated node 12; each unique interface's slots `+0/+4` 8. For `N` nodes and `U` unique tables the bound is `8 + 12N + 8U` bytes. Worst case `U=N`: `8 + 20N` (2,568 bytes for cap 128). Callback context is the interface pointer already read at node `+0x08`; no additional word is required. Any further context dereference requires separate static justification and an explicit new byte budget.

## Evidence references

- [device-registration.md](device-registration.md): node allocation/access and manager traversal.
- [device-match-semantics.md](device-match-semantics.md): strict unsigned max selection and interface validation.
- [mc-dev-attach.md](mc-dev-attach.md): manager call path and callback dispatch.
- [runtime-device-registry.md](runtime-device-registry.md): bounded capture design and decision gate.
