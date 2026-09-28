# Step 15 — CarPlay device attachment trace

Date: 2026-09-28

## Scope

Offline-only analysis of the local `jmcs` ELF and available symbols/DWARF. No vehicle, ADB, firmware modification, Display-B implementation, or packet fabrication.

## Findings

1. **Exact active call confirmed.** `mc_ScreenStreamStart` (`0xBD628`) calls `mc_dev_attach` at `0xBDC06`.
2. **Device identity confirmed.** The first argument resolves to the exact string `"CarPlay Screen"` at ELF VA `0x2E0340`.
3. **Context observed, type unresolved.** The second argument is `r8`, loaded from `[r6 + 0x78]` in the stream-start path. The local context's source is screen-stream-related; its exact declared type and ownership meaning are not established.
4. **Manager dispatch and lookup shape confirmed.** `mc_dev_attach` (`0x81630`) forwards to `devmgr_dev_attach` (`0x82858`), which invokes `devmgr_dev_alloc` (`0x825F0`) and internal `dev_attach` (`0x81FF4`) under manager synchronization/locking. `dev_attach` walks registered entries and calls each entry's first interface operation as a comparator against the device key, then passes the selected entry to `dev_attach_to_app` (`0x81E64`).
5. **Registration and media continuation unresolved.** The matching registry entry, attach callback, concrete sink, active vtable, H.264 edge, decoder ownership/cardinality, and Surface host were not established. Candidate symbols/strings were not treated as proof.

## Decision gate

| Question | Verdict |
|---|---|
| CarPlay device ID | `CarPlay Screen` |
| Device registration / attach callback | Unknown |
| Active sink / process_data target | Unknown |
| H.264 and active decoder | Unknown |
| Decoder cardinality | Unknown |
| Surface / host | Unknown |
| Device context | Stream-associated argument at `[r6+0x78]`; exact type unknown |
| Two device instances | Unknown |
| Two sinks / decoders / Surfaces | Unknown |
| Display-B media path structurally possible | Unknown |
| Ready for Display-B implementation | No |

**Biggest blocker:** identify the exact registry entry selected by internal `dev_attach` for the name `"CarPlay Screen"`, including its attach callback.

## Evidence limits and next action

`devmgr_dev_detach` exists at `0x82D28`, but its relationship to this stream's successful attach and exact cleanup objects has not been traced. No two-instance conclusion follows from the generic manager allocation path. Next, decode `dev_attach` and the narrowly relevant registration path, then follow the matched callback to sink construction.

See the focused notes under `research/carplay/` and `primary-screen-end-to-end.md`.
