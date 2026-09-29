# CarPlay device registration trace

**Status: generic registration/dispatch recovered; the `CarPlay Screen` winning entry is not yet proven.** Static offline analysis of the exact local `jmcs` ELF recorded in [the address map](jmcs-address-map.md). No vehicle or ADB session was used.

## Registry traversal and inferred layouts

`dev_attach` (`0x81FF4`) starts at manager `+0x08`, follows a linked list, and for each candidate loads an interface pointer from entry `+0x08`. It calls interface slot `+0x00` with the allocated/request key and entry interface. The callback result is compared against the current best score; the entry whose result is strictly greater is retained. A selected entry is passed to `dev_attach_to_app` (`0x81E64`).

| Object | Offset | Observed use | Confidence |
|---|---:|---|---|
| Manager | `+0x08` | First registry/list entry used by `dev_attach` | Confirmed use; C type unknown |
| Manager | `+0x10` | Loaded in `dev_attach`, then `+0x0c` is used as the comparison key | Confirmed access; field meaning beyond dataflow unknown |
| Registry entry | `+0x00` | Next entry in scan | Confirmed linked traversal |
| Registry entry | `+0x08` | Interface pointer | Confirmed |
| Entry interface | `+0x00` | Comparator/ranker called during scan | Confirmed slot use; function for CarPlay unresolved |
| Entry interface | `+0x04` | Attach callback invoked by `dev_attach_to_app` | Confirmed slot use; function for CarPlay unresolved |
| Allocated device | `+0x08` | Selected entry stored after successful attach | Confirmed |
| Allocated device | `+0x0c` | Value passed as attach callback argument 0 | Confirmed dataflow; semantic type unknown |
| Allocated device | `+0x14` | Address passed as attach callback argument 1 | Confirmed dataflow; out/context semantics not proven |

`devmgr_dev_alloc` allocates a `0x20`-byte record, calls `j_secure_ptr_create` (`0x123DB4`) with its manager context and that record, stores the returned pointer at record `+0x0c`, and writes that pointer through its third argument. Thus the second argument to `mc_dev_attach` is used as output storage by the generic allocator; its API-level type/name and owning stream field remain unknown. `dev_attach_to_app` passes `[device +0x0c]`, `device +0x14`, and the interface pointer in r0-r2.

This is an observed-use table, not a complete C structure definition. The entry does not expose a proven name field. The selection is a maximum positive callback score, not a direct `strcmp` loop established from `dev_attach` itself.

## Registration API and storage

`devmgr_app_register` (`0x8307C`) is called by `mc_media_dev_register_devmgr` (`0x3CF7C`) and `mc_iodev_set_cbs` (`0x4B99C`). `mc_media_dev_register_devmgr` maintains a media registration object and calls `devmgr_app_register`; `mc_media_dev_alloc_and_register` is used by `mc_ipod_attach` (`0x23FEE4`) in three places. These establish generic app-registration plumbing, but do not identify which entry accepts the screen key.

| Question | Result |
|---|---|
| Registration API | `devmgr_app_register` (`0x8307C`) — confirmed call target |
| Registry storage | Manager linked list traversed from `+0x08`; entry interface pointer at `+0x08` — confirmed observed use |
| Initialization time | Registration is runtime callable; exact startup/lazy timing for the `CarPlay Screen` entry is unknown |
| Candidate callbacks | Generic media (`media_dev_attach`, `media_dev_attach_cb`) exist, but no proven edge from the screen key to either |
| Exact registration identity / compare callback | Unknown |

## Comparator proof boundary

`dev_attach` calls each entry's interface slot 0, passes its return value through a strict greater-than comparison, and invokes the selected entry's slot 1. This confirms callback-based ranked selection. No recovered code/dataflow in this slice proves the registered identity, alias, string comparison, or winning result for the literal `"CarPlay Screen"`. Proximity of media helpers and strings is not sufficient evidence.

See [device-manager.md](device-manager.md), [mc-dev-attach.md](mc-dev-attach.md), and [Step 16](../../step-reports/16-carplay-registration-match.md).

## Step 17 status — winner remains unresolved (2026-09-28)

The offline pass confirms generic registration and ranking only. `dev_attach` selects the strictly highest unsigned slot `+0` result (initial best 0; ties retain the earlier node), then dispatches slot `+4`. The concrete list entry/interface/context installed for `"CarPlay Screen"` is not statically recoverable from the local `jmcs` artifact. Therefore this note does not assign an active backend, sink, decoder, or Surface. See [device-match-semantics.md](device-match-semantics.md) and [Step 17](../../step-reports/17-carplay-registration-winner.md). The exact blocker is runtime registration state (or its producer), not absent `jmcs`/DWARF. Display-B readiness remains **No**.

## Step 18 status — saved runtime captures insufficient (2026-09-28)

The offline capture audit found `/system/bin/jmcs` process/maps/status/fd snapshots and older CarPlay logs, but no registry head, candidate nodes, callback tables, contexts, or match results. `media_dev_attach` log messages are generic and are not proven to come from `mc_dev_attach("CarPlay Screen", ...)`. Registry owner is `jmcs`; known list-head field is manager `+0x08`, but its absolute runtime address and list contents are unavailable. Live observation is required to continue. See [runtime registry audit](runtime-device-registry.md) and [Step 18](../../step-reports/18-runtime-registration-resolution.md). No live action was performed.

## Step 18 live result (2026-09-29)

Read-only ADB confirmed `jmcs` PID `26577`, load base `0x4008f000`, and 45 mapped shared libraries. Current relevant logcat queries were empty. DWARF maps `mc_devs` static `0x35acbc` to candidate runtime cell `0x403e9cbc`; reading four bytes from `/proc/26577/mem` was denied (`Operation not permitted`). Manager pointer/list, winner, and slot `+4` remain unresolved. iPhone stayed disconnected. See [runtime registry evidence](runtime-device-registry.md) and [Step 18](../../step-reports/18-runtime-registration-resolution.md).
