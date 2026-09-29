# Step 17 — CarPlay registration winner (offline static pass)

Date: 2026-09-28
Base: `8f5823f`
Artifact: ignored local `extracted/system-vendor/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`.

## Scope and method

Offline-only analysis. Inspected prior call-chain evidence, ELF symbols and code, DWARF compile units, `.rel.dyn`/`.rel.plt`, `.init_array`, and direct code references to registration APIs and the request literal. `.init_array` is present but its unsymbolized entry was not attributable to device registration. No vehicle, ADB, firmware modification, or unrelated registration audit.

## Proven

- `mc_ScreenStreamStart` calls `mc_dev_attach` with the exact key `"CarPlay Screen"` (call at `0xBDC06`).
- `dev_attach` (`0x81FF4`) traverses the registry list rooted at manager `+0x08`. Each node's `+0x08` is an interface pointer. Slot `+0x00` is invoked with the device key and interface/context. The unsigned result replaces the best only when strictly greater (`HI`); best begins at zero, so zero cannot win and equal scores preserve the earlier node.
- The selected node is passed to `dev_attach_to_app` (`0x81E64`), which invokes interface slot `+0x04` with arguments derived from the allocated record and interface. On success it stores the registration node in the allocated device record.
- `devmgr_app_register` (`0x8307C`) validates interface pointers at `+0`, `+4`, `+8`, allocates a 12-byte node, stores interface at node `+8`, and links the node into the manager list.
- The two direct calls to that function in the symbolized function bodies are `mc_media_dev_register_devmgr` (`0x3CF7C`, call `0x3CFC8`) and `mc_iodev_set_cbs` (`0x4B99C`, call `0x4B9CE`). The media route uses interface storage at `r5+8` and private/context `r5`; the I/O route uses interface `r4` and context loaded from a global.
- Media callback setup includes `mc_media_dev_set_cbs` (`0x3D5A4`), reached from `main` and `handle_media_dev_set_cbs`; I/O callback setup includes `mc_iodev_set_cbs`, reached from `main` and `handle_iodev_set_cbs`. This is runtime callback registration/setup.
- Generic device allocation is a 0x20-byte record. `devmgr_dev_alloc` (`0x825F0`) calls `j_secure_ptr_create` (`0x123DB4`), stores its return at record `+0x0c`, then writes that pointer through its third argument. The API-level secure-pointer type/owner remains unknown.

## Unresolved — exact runtime construction boundary

The local ELF contains the generic manager and registration paths, with symbols and DWARF. The relocation/constructor review and the available `.rodata`/code references did not statically bind a concrete slot `+0`/slot `+4` table and context to the request `"CarPlay Screen"`, nor expose the candidate list's actual contents/order at that call. The generic media and I/O registration entry points are not proof that either route wins this request. Callback return semantics beyond unsigned max selection are candidate-defined and unavailable; exact/prefix/type/rank interpretation is therefore unknown.

This is not a missing `jmcs` binary, absent DWARF, relocation omission, or disassembler limitation. The exact missing evidence is runtime registration state (candidate interface pointers, context, and list order) at attach, or the producer/module input that constructs that state. The current workspace has no artifact identifying that producer. A specific additional binary cannot be named from available evidence; asking for the vehicle is not the next step.

## Decision gate

| Item | Verdict |
|---|---|
| Winning registration | Unresolved |
| Match callback/result | Unknown; generic comparison rule confirmed |
| Attach slot +4 callback | Unknown for this request |
| `mc_dev_attach` output | secure pointer stored in generic record and written through caller's output slot; semantic type/ownership unknown |
| Concrete device instance | Generic manager record is per allocation; attached backend unknown |
| Active sink / process_data | Unknown |
| Decoder / Surface | Unknown |
| Multi-attach, unique handles, two devices/sinks/decoders/Surfaces | Unknown |
| Display-B media path | Unknown |
| Ready for Display-B | No |

**Biggest remaining blocker:** capture or recover the actual manager-list registration state at `mc_dev_attach("CarPlay Screen", ...)`, including each candidate's interface table, context, and insertion order, or identify the runtime producer that installs those entries.

## Next action

Search the existing offline process/memory snapshots for the manager registry head and candidate callback tables at the attach epoch; if snapshots do not retain them, identify the IPC/service setup artifact that supplies callback registrations. Do not proceed downstream until the winning node and its slot `+4` target are proven.
