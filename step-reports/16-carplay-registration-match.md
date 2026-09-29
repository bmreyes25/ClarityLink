# Step 16 — CarPlay device registration match

Date: 2026-09-28

## Scope

Offline-only static analysis of the local ignored `jmcs` ELF, its symbols, DWARF availability, and disassembly. No vehicle or ADB use, firmware changes, Display-B implementation, or protocol-field fabrication.

## Findings

1. **Caller reconfirmed.** `mc_ScreenStreamStart` calls `mc_dev_attach` at `0xBDC06` with the exact literal `"CarPlay Screen"` (VA `0x2E0340`) and a stream-associated second argument loaded from `[r6 + 0x78]`.
2. **Registry traversal decoded.** `dev_attach` (`0x81FF4`) traverses the manager list starting at `+0x08`; entries expose an interface pointer at `+0x08`. The callback at interface slot `+0x00` is called during scanning. Its positive return is ranked using a strict-greater-than comparison, retaining the best candidate.
3. **Attach dispatch decoded.** The selected entry is passed to `dev_attach_to_app` (`0x81E64`). This invokes interface slot `+0x04` with `[device +0x0c]`, `device +0x14`, and the interface pointer in r0-r2. On successful attach, the selected entry is stored at device `+0x08`. `devmgr_dev_alloc` creates a secure pointer to its `0x20`-byte record via `j_secure_ptr_create` (`0x123DB4`) and writes that pointer through the caller-supplied second argument; the stream-associated field at the callsite is therefore used as output storage in the generic path, though its API type/owner is unknown.
4. **Generic registration API found.** `devmgr_app_register` (`0x8307C`) is called by `mc_media_dev_register_devmgr` (`0x3CF7C`) and `mc_iodev_set_cbs` (`0x4B99C`). Generic media attach helpers also exist (`media_dev_attach` at `0x3E03C`, `media_dev_attach_cb` at `0x24380C`). No evidence joins their registration object to the CarPlay key.
5. **Exact match remains unresolved.** The callback-based ranking mechanism is recovered, but the candidate whose comparator accepts `"CarPlay Screen"`, the match key/rule, initializer, and its attach callback have not been proven. Nearby strings/symbols were not used as attribution evidence.
6. **Downstream media path remains unresolved.** No active sink, sink `process_data`, H.264 edge, decoder owner/cardinality, Surface, or matching detach callback was recovered. Generic allocation proves a manager record is allocated per attach request; it does not prove independent media pipelines or that duplicate keys are accepted.

## Decision gate

| Item | Verdict |
|---|---|
| CarPlay registration / registered identity | Unknown |
| Comparator mechanism | Callback at interface +0, ranked by positive score; specific comparator unknown |
| Attach callback | Unknown for this key |
| Attach context | Caller field `[r6+0x78]` is output storage for a newly created secure pointer; semantic owner/type unknown |
| Device instance | Generic `0x20`-byte manager record per request; concrete object unknown |
| Active sink / process_data | Unknown |
| H.264 / active decoder | Unknown |
| Decoder cardinality | Unknown |
| Surface | Unknown |
| Multiple device instances | Unknown |
| Two sinks / decoders / Surfaces | Unknown |
| Display-B media path | Unknown |
| Ready for Display-B | No |

**Biggest remaining blocker:** prove which registered interface's slot-0 callback wins for the exact key `"CarPlay Screen"`, and recover that entry's slot-4 attach target.

## Next action

Trace relevant `devmgr_app_register` callers and their registration-interface initializers narrowly around screen/media registration; evaluate candidate comparator callbacks against the exact key, then follow only the proven winning attach callback.
