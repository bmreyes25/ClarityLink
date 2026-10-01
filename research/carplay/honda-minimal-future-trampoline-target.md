# Minimal future trampoline target — offline plan only

Selected site: `_connectionHandleMessage`'s existing call at `0x28afba`, Thumb-2 `BL _requestSendPlistResponse`.

| Property | Static value |
|---|---|
| Reference binary | SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` |
| Expected bytes | `fe f7 d1 ff` (little-endian instruction bytes) |
| Original target | `0x289f60`, `_requestSendPlistResponse` |
| Continuation | `0x28afbe` |
| Instruction mode | Thumb |
| Minimum whole-instruction span | 4 bytes (one BL instruction) |
| Displaced PC-relative operation | Existing BL uses PC-relative Thumb-2 range; wrapper must invoke original serializer exactly once, re-encoding its BL or using a reachable veneer |
| Caller ABI | `r0=connection`, `r1=HTTP message`, `r2=response`, `r3=&statusOut`; caller locals `[sp+0x1c]` request, `[sp+0x54]` response, `[sp+0x50]` status, session `[r10+0xf4]`; preserve `r4-r11`, SP and stock return/status |
| Project ordering | prepare/build/mutate before stock serializer; call stock exactly once; commit only for `r0==0xc8 && *statusOut==0`, otherwise rollback project resources |
| Risk gate | exact SHA and call bytes, branch reach/veneer, AAPCS state, caller-frame access, stock original exactly once, concurrent install/call safety, instruction-cache coherency, and fail-closed rollback must all be proven in a later offline design |

The displaced instruction itself has no extra literal/data dependency; no second instruction is overwritten in this plan. Generic relocation of arbitrary prologues is unnecessary for this callsite, but the BL's stock target must remain exact. Thumb BL reaches a signed ±16 MiB byte displacement (halfword aligned); out-of-range shim needs a validated veneer. Runtime mapping, W^X policy, patch activation, and hook install technique remain `UNKNOWN`. No patch bytes or modified Honda ELF are emitted. This is a deterministic planning target, not implementation approval.
