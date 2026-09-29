# CarPlay `mc_dev_attach` trace

**Status: caller, manager traversal, and callback ABI dataflow partially recovered; exact registry winner unresolved.** Offline analysis only.

## Exact caller

| Field | Finding |
|---|---|
| Caller | `mc_ScreenStreamStart` (`0xBD628` function start) |
| Call instruction | `0xBDC06` -> `mc_dev_attach` (`0x81630`) |
| Argument 0 | Exact string `"CarPlay Screen"`, literal VA `0x2E0340` |
| Argument 1 | Stream-associated pointer loaded from `[r6 + 0x78]`; `devmgr_dev_alloc` writes a newly created secure pointer through this value, so the generic path treats it as output storage. API-level type and owner remain unknown |
| Return handling | Zero follows success path; nonzero is error path |

## Dispatch dataflow

`mc_dev_attach` loads the global manager and tail-calls `devmgr_dev_attach(manager, key, context)`. `devmgr_dev_attach` calls `devmgr_dev_alloc`, then invokes internal `dev_attach` while holding manager synchronization. The manager scan starts at `manager +0x08`; each list entry has an interface pointer at `+0x08`. Interface slot `+0x00` is called as a candidate scoring/comparison callback. A strict greater-than comparison keeps the highest-scoring entry. The selected entry is passed to `dev_attach_to_app`.

`devmgr_dev_alloc` creates a `0x20`-byte record and calls `j_secure_ptr_create` (`0x123DB4`), stores the returned pointer at record `+0x0c`, and writes it through the caller-supplied output slot. Thus the second argument to `mc_dev_attach` is used as output storage in the generic manager path. `dev_attach_to_app(device, entry)` loads the entry interface, invokes slot `+0x04`, and supplies `[device +0x0c]`, `device +0x14`, and the interface pointer in r0-r2. On successful attach it stores the selected entry at `device +0x08`. The concrete output/context meaning and selected callback remain unknown.

## Registration API evidence

`devmgr_app_register` (`0x8307C`) is the registration call used by `mc_media_dev_register_devmgr` (`0x3CF7C`) and `mc_iodev_set_cbs` (`0x4B99C`). The generic media callbacks `media_dev_attach` (`0x3E03C`) and `media_dev_attach_cb` (`0x24380C`) exist, but static evidence does not connect their registration entry to this exact key.

## Unresolved

- Entry whose comparison callback returns the selected score for `"CarPlay Screen"`.
- Comparator implementation and matching identity/alias.
- Concrete attach callback and meaning/ownership of context argument.
- Concrete sink, active `process_data`, decoder, Surface, and detach callback.

Do not infer the match from nearby strings or generic media symbol names. See [Step 16](../../step-reports/16-carplay-registration-match.md).
