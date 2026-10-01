# Minimal future trampoline target — Step 43N offline model

Selected site: `_connectionHandleMessage`'s existing call at `0x28afba`, Thumb-2 `BL _requestSendPlistResponse`.

| Property | Static value |
|---|---|
| Reference binary | ELF32 little-endian ARM `ET_DYN`, EABI5; SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` |
| Expected bytes | `fe f7 d1 ff` (little-endian instruction bytes) |
| BL PC | `0x28afbe` (`callsite + 4`) |
| Decoded displacement | `-0x105e`; `0x28afbe - 0x105e = 0x289f60` |
| Original target | `0x289f60`, `_requestSendPlistResponse` |
| Continuation | `0x28afbe` |
| LR from old direct call | `0x28afbf` (Thumb tagged) |
| Instruction mode | Thumb |
| Minimum whole-instruction span | 4 bytes (one BL instruction) |
| Surrounding fingerprint | `0x28afb2` bytes `31 46 20 46 15 9a 14 ab fe f7 d1 ff 06 46 40 e0`; SHA-256 `edec335f1cd6f9d0d053a0d2b4a05f515c25e1a1524fccca2c4c0ebd610273df` |
| Caller prologue fingerprint | `0x28a30c` bytes `df f8 8c 24 2d e9 f0 4f 04 46 df f8`; SHA-256 `be9f272a09201f326e42c27962609add81149bbe1adb9e843bb8b8ff685d7878` |
| Caller stack | Prologue pushes nine words (36 bytes), then allocates `0x2b4` (692 bytes): total delta `0x2d8` (728 bytes). Given an 8-byte-aligned AAPCS function-entry SP, callsite SP remains 8-byte aligned. |
| Caller live state | `r0=connection`, `r1=HTTP message`, `r2=response`, `r3=&statusOut`; `r4=connection`, `r6=HTTP message`, `r10` carries session-bearing context; request `[sp+0x1c]`, status slot `[sp+0x50]`, response `[sp+0x54]`, session `[r10+0xf4]`. Preserve `r4-r11`; restore `r0-r3` before the stock call. `r12` is caller-saved; the next instruction does not consume flags. |
| LR contract | BL-to-shim enters with saved caller LR `0x28afbf`. To regain control after the serializer, the adapter must call it with an adapter-local LR; the serializer then returns to the adapter. The adapter saves/restores caller LR and exits to `0x28afbe` in Thumb state. The serializer prologue saves its incoming LR for an ordinary return; no return-address inspection was found in the bounded function. Its LR therefore differs from the old direct call and this remains an explicit runtime compatibility risk. |
| Caller ABI | `r0=connection`, `r1=HTTP message`, `r2=response`, `r3=&statusOut`; preserve caller `r4-r11`, SP and Honda's returned `r0`; post-processing reads `statusOut` without rewriting it. |
| Project ordering | prepare/build/mutate before stock serializer; call stock exactly once; commit only for `r0==0xc8 && *statusOut==0`, otherwise rollback project resources |
| Thumb BL reach | PC-relative signed displacement `[-0x1000000, +0xfffffe]`, halfword aligned. For this low VA, the signed lower limit falls below address zero; address zero and near `0x28b000` remain directly reachable. The upper edge `0x128afbc` is reachable; `0x128afbe` requires a veneer. Thumb BL targets Thumb; ARM-state target requires separately validated interworking. |
| ABI model | `src/claritylink-negotiation/trampoline_contract.py` models save/restore flow and synthetic results; it emits no instructions and is not runtime proof. |
| Compatibility planner | `tools/jmcs_integration/callsite_plan.py` gates on full hash, ARM ELF identity, target BL bytes/decoded destination, caller context bytes/hash, prologue bytes/hash, and continuation. It emits a plan only. |
| Risk gate | exact SHA and call/context/prologue bytes, branch/veneer, AAPCS state, caller-frame access, changed serializer-entry LR, stock original exactly once, concurrent install/call safety, instruction-cache coherency, and fail-closed rollback must all be addressed before any runtime-specific design. |

The displaced instruction itself has no extra literal/data dependency; no second instruction is displaced in this conceptual callsite design. This is not a generic prologue hook. The relocated operation is the existing BL to Honda's serializer. Runtime mapping, W^X policy, patch activation, interworking veneer implementation, and hook install technique remain `HONDA_UNKNOWN`. No patch bytes or modified Honda ELF are emitted. This is a deterministic offline model, not implementation approval.
