# Honda session finalizer dataflow — 43L.2

Binary: `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`.

`_AirPlayHandleSessionFinalized` is Thumb at `0xae654`, size `0x41c`. CF runtime `_Finalize` (`0x284d24`) gets the callback from session `+0x20`, context from `+0x14`, and invokes it as `(session, context)` at `0x284d36`. It then calls `AirPlayReceiverSessionPlatformFinalize` (`0x28cd60`) at `0x284d3e`. The session pointer therefore reaches the Honda app handler and the platform finalizer, but no project registry is referenced.

The handler performs app-level finalization bookkeeping, clears/frees Honda context state, and calls `mc_carplay_screen_session_destroyed` (`0xc0c84`). At `0xae7fa`, it also loads `g_carplay_cbs.event_cb` from `0x355b6c` and calls it with an interface pointer and event value 2. DWARF names value 2 `MC_DEV_CARPLAY_SESSION_DESTROYED`. This notification does not carry the AirPlay session pointer or project generation.

Directly established finalization call path:

| Caller | Site | Arguments | Session available? | Context available? | Purpose | Confidence |
|---|---:|---|---|---|---|---|
| CF runtime `_Finalize` | `0x284d36` | `r0=session`, `r1=session+0x14` context | Yes | Yes | invoke installed Honda finalized callback | HONDA_CONFIRMED |
| `_AirPlayHandleSessionFinalized` | `0xae7fa` | `r0=CarPlay interface`, `r1=2` | No in callback ABI | No | notify interface consumer of destroyed event | HONDA_CONFIRMED |
| `_AirPlayHandleSessionFinalized` | `0xae7fc` | no meaningful session argument | No | No | clear screen-session app state | HONDA_CONFIRMED |
| CF runtime `_Finalize` | `0x284d3e` | `r0=session` | Yes | session-owned platform field | platform/resource finalization | HONDA_CONFIRMED |

The handler is not a general observer dispatcher. The indirect callback is one function pointer in a fixed global callback record, not an array or list.
