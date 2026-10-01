# Honda post-Setup callout safety — Step 43L.1

**Artifact:** hash-matched `jmcs` (`cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`). Static ARM/Thumb disassembly only. No injection or patch design.

## Exact caller state

`_connectionHandleMessage` is Thumb at `0x28a30c`. Prologue at `0x28a310` pushes nine words (`r4-r11,lr`, 36 bytes), then `0x28a31a` subtracts `0x2b4` (692 bytes). From an AAPCS32 8-byte-aligned entry SP, current SP remains 8-byte aligned: 36 + 692 = 728 = 91×8. Caller stores HTTP connection in `r4`, original HTTP message in `r6`, keeps its saved session context in callee-saved `r10`, request dictionary at `[sp+0x1c]`, status at `[sp+0x50]`, and responseOut at `[sp+0x54]`.

At Setup return, `0x28af76–0x28af7c` saves/tests status and branches on nonzero. The condition flags are consumed by that `bne`. Success begins at `0x28af7e`, performs three session byte stores and calls `CFObjectSetProperty` at `0x28afae`. The return from that call is ignored. At the next instruction `0x28afb2`, the caller stages the serializer's `r1/r0/r2/r3` from `r6/r4/[sp+0x54]/sp+0x50`; there is no intervening branch. No flags from the earlier `cmp` remain live or are tested after the branch.

## Candidate sites

Thumb-2 `BL` uses PC+4 and a signed even displacement of approximately ±16 MiB (architectural range `-2^24` through `2^24-2` bytes). Existing Setup call at `0x28af72` encodes a 32-bit Thumb BL. Candidate helper addresses are not selected, so reachability to any future helper is unknown. Every listed site is an occupied instruction boundary; no spare bytes or safe replacement sequence is established.

| SITE | ADDRESS RANGE / BYTES | LIVE INPUTS / OUTPUTS | MUST SURVIVE / FLAGS | STACK | SAFE CALLOUT? / confidence |
|---|---|---|---|---|---|
| Immediately after successful Setup branch | `0x28af7e`, `f8df e0b8` (ldr.w) | session `[r10+f4]`, request `[sp+1c]`, status `[sp+50]`, response `[sp+54]`; Honda metadata writes still pending | preserve `r4-r11` by AAPCS; no flags live | 8-byte aligned | CANDIDATE_ONLY; would run before remaining stock metadata side effects |
| After stock metadata call, before serializer staging | `0x28afb2`, `4631` (`mov r1,r6`) | request/message `r6`, conn `r4`, session reload `[r10+f4]`, request dict `[sp+1c]`, response `[sp+54]`, status `[sp+50]` | preserve `r4-r11`; no flags live; `r0-r3` are restaged by following original instructions | 8-byte aligned | CANDIDATE_ONLY; best point for prepare/mutate, but insertion requires occupying/replacing code and no callout safety/race contract is proven |
| Immediately before serializer call | `0x28afba`, `f7fe ffd1` (BL serializer) | serializer args already staged: `r0=conn`, `r1=request message`, `r2=response`, `r3=&status` | `r4-r11` live/saved; caller-saved staged args must be reconstructed after helper; no flags live | 8-byte aligned | CANDIDATE_ONLY; helper must restage exact original serializer args |
| Immediately after serializer return | `0x28afbe–0x28afc0`, `4606; e040` | `r0` is HTTP status (`0xc8` success, `0x1f4` helper error); `[sp+0x50]` is body-set result; response still live until `0x28b052` | `r6` receives return at `0x28afbe`; preserve status and callee-saved regs; no flags needed | 8-byte aligned | CANDIDATE_ONLY; viable commit/rollback observer, too late for response mutation |
| Common cleanup entry | `0x28b044`, `9d07` (ldr request) | response/request still live until releases; serializer result held in `r6`; status `[sp+50]` | preserve status and `r4-r11`; no needed flags | 8-byte aligned | UNKNOWN; shared success/error cleanup, and mutation is too late |

No candidate is `PROVEN_SAFE`. Exact ABI requirements can be stated, but there is no Honda contract establishing that an arbitrary project helper can run here without reentrancy, lock, thread-affinity, or session-transition hazards. Nor is there an unused call slot; branch placement and control transfer depend on a future mechanism, deliberately out of scope.

```text
CALLOUT SAFETY: CANDIDATE_ONLY
BEST STATIC CALLOUT CANDIDATE: 0x28afb2 (structural only)
```

The helper would have to be a non-throwing, normally returning AAPCS32 Thumb-callable function; preserve `r4-r11`; keep SP 8-byte aligned; treat `r0-r3/r12/lr/flags` as volatile; reload request/session/response/status from the named locations; return a status that caller may ignore only if all failure handling is internal; and leave Honda response untouched on every failure. It must never transfer ownership of the stock response, replace that response object, alter the request, change stock Type110/audio entries, or mutate after serializer entry. After a helper at `0x28afb2`, the stock serializer args are loaded again by `0x28afb2–0x28afb8` (the inserted operation would have to execute before those original loads). Exact operational helper ABI remains PARTIAL because no callable integration mechanism exists.
