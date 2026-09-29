# Device manager match semantics

## Evidence boundary (Step 17, 2026-09-28)

Analyzed the ignored local artifact `extracted/system-vendor/system/bin/jmcs` (SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`). It is ELF32 ARM with `.symtab`, DWARF, and relocation sections. The exact CarPlay caller passes the literal `"CarPlay Screen"` to `mc_dev_attach` (`0x81630`, call at `mc_ScreenStreamStart` `0xBDC06`).

`dev_attach` (`0x81FF4`) has these proven operations:

1. Receives the allocated device record and request key. It loads the candidate-list head from manager `+0x08`.
2. For each linked entry, loads interface pointer at entry `+0x08`, loads function pointer at interface `+0x00`, and calls it with the allocated record's key (`[device +0x0c]`) and the interface/context pointer.
3. Compares callback result with current best using unsigned `HI` (strict greater-than); only a strictly greater result replaces the selected entry and best value.
4. If a candidate is retained, dispatches it through `dev_attach_to_app` (`0x81E64`).

Therefore the observable rule in this function is **maximum unsigned callback result, strict greater-than, initial best zero**. A zero result cannot win; positive values can become the current best; ties preserve the earlier entry. The callback's C return type, intended score domain, and what individual values mean are not established. In particular, no proof says a positive result is necessarily an exact string match, nor that a particular score means weak/exact.

## Interface and registration evidence

`devmgr_app_register` (`0x8307C`) validates a three-pointer interface at offsets `+0x00`, `+0x04`, and `+0x08`, allocates a `0x0c`-byte list node, stores the passed interface pointer at node `+0x08`, and inserts the node into the manager list. The manager scan later uses the first two interface words as match and attach callbacks. This establishes the minimum accessed layout, not a complete C type.

There are two direct call sites to `devmgr_app_register` in the function-symbol/disassembly sweep of this ELF:

| Route | Call site | Data supplied to registration | Result |
|---|---:|---|---|
| `mc_media_dev_register_devmgr` (`0x3CF7C`) | `0x3CFC8` | Interface address `r5+8`; private/context `r5` | Generic media registration path; not keyed statically to `CarPlay Screen` |
| `mc_iodev_set_cbs` (`0x4B99C`) | `0x4B9CE` | Interface address `r4`; private/context loaded from a global | Generic I/O-device callback registration path |

The interface supplied by media route is populated through `mc_media_dev_set_cbs` (`0x3D5A4`), reached from `main` (`0x131C0`) and `handle_media_dev_set_cbs` (`0x25A20`). The I/O route is reached from `main` and `handle_iodev_set_cbs` (`0x23AB8`). These are runtime setup paths; this static pass did not recover the concrete installed callback values/context corresponding to the CarPlay request.

## Match result for `CarPlay Screen`

**Unknown.** No statically recovered entry instance links a candidate's slot `+0` code/context to the literal request. Consequently no exact candidate result can be evaluated and no winner can be named. A registry list node is allocated and linked at runtime; the two generic API call paths do not prove which one registered the winning entry, whether there are additional indirect registration paths, or the insertion order/runtime contents at the CarPlay attach.

The ELF includes symbols, DWARF, relocations, and the manager implementation. `.init_array` exists but its unsymbolized entry is not attributable to device registration; available `.rodata`/code references do not bind the request literal to a concrete comparator. The failure is not missing `jmcs`, a decompiler limitation, or absence of debug information. The missing evidence is the actual runtime registration construction/state: concrete callback table/context and registration order present when `mc_ScreenStreamStart` calls `mc_dev_attach`. Static data in the current artifacts does not bind that runtime state to the key.

## Decision

| Question | Finding |
|---|---|
| Match arguments | device key from `[device +0x0c]`, interface/context in the second argument; exact ABI interpretation beyond observed registers is unknown |
| Return comparison | unsigned strict `>` against current best, initialized to zero |
| No-match behavior | no candidate selected if all callbacks return zero (observed control flow) |
| Weak/exact match values | unknown; callback semantics are candidate-defined and unavailable |
| Winner for `CarPlay Screen` | unresolved from current static artifacts |
| Exact next evidence needed | saved runtime memory/registration trace of the manager list and each candidate interface/context at the attach, or the missing producer/module/source that constructs those exact entries |

Do not infer a winner from function/string proximity or generic media naming.
