# CarPlay `mc_dev_attach` trace

**Status: attachment call and requested name confirmed; backend selection unresolved.** Offline analysis of the local `jmcs` ELF at the base commit. The local binary is ignored and is not included in Git.

## Exact CarPlay call

| Field | Finding |
|---|---|
| Caller | `mc_ScreenStreamStart` (`0xBDC06`) |
| Binary | `extracted/system-vendor/system/bin/jmcs`, SHA-256 in `jmcs-address-map.md` |
| Call | `bl 0x81630 <mc_dev_attach>` |
| First argument | Pointer to exact NUL-terminated string `"CarPlay Screen"` (literal at ELF VA `0x2E0340`) |
| Second argument | `r8`, loaded from the screen-stream-related object at `[r6 + 0x78]`; exact C type/semantic role unresolved |
| Extra mode/config | No third argument at this wrapper call. Nearby value `1` initializes the stream object and is not passed in a register to `mc_dev_attach` |
| Return | Zero/nonzero status convention at this call site; nonzero takes the error path |
| Return storage | On success, zero is stored at `[r6]`; the attached device output, if any, is not established from this store |

The stream object is populated with related pointers before the call. That is evidence of a per-stream context, but not proof that the manager/device/sink/decoder are per-stream.

## Wrapper and manager path

`mc_dev_attach` (`0x81630`) loads the MediaCore device-manager global and tail-calls `devmgr_dev_attach` (`0x82858`) with the manager plus the two caller arguments. `devmgr_dev_attach` checks manager state and the second argument, calls `devmgr_dev_alloc` (`0x825F0`), then calls internal `dev_attach` (`0x81FF4`) under the manager lock. `dev_attach` walks registered entries, invokes each entry's first interface operation as a comparator against the secure device key, and passes the selected entry into `dev_attach_to_app` (`0x81E64`). The winning comparator, registration entry, and callback target remain unresolved.

## Signature confidence

The wrapper-level ABI is consistent with `mc_dev_attach(arg0, arg1)`; the manager implementation receives `(manager, arg0, arg1)`. No reliable DWARF prototype was recovered in this pass, so source-level types, ownership semantics, and an `out` parameter interpretation remain unknown. Do not rename the arguments beyond their observed values.

## Decision

The requested device name is **CarPlay Screen**. The highest-priority unresolved edge is the `dev_attach` registry lookup from this name to a registration entry and callback. See `device-manager.md`, `active-carplay-sink.md`, and `step-reports/15-carplay-device-attach.md`.
