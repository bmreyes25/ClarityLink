# Honda post-Setup integration contract — Step 43L

**Status: PARTIAL.** Evidence is offline static disassembly of `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. No loading, patch, Type111 implementation, or live work was performed.

## Confirmed caller sequence

At `0x28af72`, `_connectionHandleMessage` calls Setup with `r0=[r10+0xf4]`, request `r1=[sp+0x1c]`, and response output pointer `r2=sp+0x54`. At `0x28af76` it saves the return; `0x28af7a` tests it and `0x28af7c` branches on nonzero to the stock error path. Success falls through `0x28af7e–0x28afae`, including three session byte stores at `+0xa4..+0xa6` and `CFObjectSetProperty` at `0x28afae` (not passed the response). At `0x28afb2–0x28afb8`, the caller stages original message `r6`, connection `r4`, exact response `[sp+0x54]`, and status output `[sp+0x50]`; `0x28afba` calls the serializer. `0x28afbe` stores its return and `0x28afc0` joins cleanup. Request and response are released at `0x28b048` and `0x28b052`; HTTP send is called later at `0x28b790`. No intervening handler branch exists between Setup success and serializer call, but arbitrary project callout/reentrancy safety is not established.

| Address | Instruction/call | Relevant values | Failure edge | Transaction implication |
|---|---|---|---|---|
| 0x28af6a–0x28af72 | Setup args; BL | session, request, `&responseOut` | Setup return | Original request/session are live |
| 0x28af76–0x28af7c | save/status compare | status `[sp+0x50]` | nonzero → 0x28b040 | No project preparation should precede success |
| 0x28af7e–0x28afae | Honda success metadata | session `[r10+0xf4]`; response untouched | no local branch | Must preserve stock ordering; CFObjectSetProperty callout present |
| 0x28afb2–0x28afba | stage and serializer BL | same response `[sp+0x54]` | serializer's own failure | Last structural pre-serialization interval |
| 0x28afbe–0x28b052 | save result; cleanup | serializer return in `r6`; release request/response | common return path | Response graph lifetime ends after synchronous helper |
| 0x28b790 | HTTPConnectionSendResponse | handler HTTP status/result | nonzero commit status | Later network lifecycle, not graph rollback |

## Serializer barrier (`0x289f60`)

The helper checks/initializes response headers, then for non-null plist input calls `CFPropertyListCreateData` at `0x289fb2` (format `0xc8`). Null data branches to `0x289ffc`, sets HTTP status `0x1f4`, sets result `r7` from constant `0xffffe5d4`, and returns through common cleanup. Successful data yields byte pointer (`0x289fbc`) and length (`0x289fc4`), then `HTTPMessageSetBody` at `0x289fdc`. It maps body-set return zero to status `0xc8` and nonzero to `0x1f4`; writes that setter result through statusOut at `0x289ff6`, releases temporary CFData at `0x289ff0`, and returns status at `0x289ff8`. Header initialization failure at `0x289f9a` branches to 500 path before plist creation. The helper reads the response graph synchronously and creates a separate CFData. Its local success predicate is `r0 == 0xc8` with statusOut zero; this is not an OSStatus-zero convention.

`HTTPMessageSetBody` sets body length, uses `memmove` when the source differs from the HTTP body's current buffer (`0x29d046`), then sets content-length/content-type headers. The data copy is statically visible. Its mutation is to HTTP message state, not the CF response graph. Serializer success therefore proves local serialization and body installation only; it does not prove HTTP state-machine acceptance or socket delivery.

`HTTPConnectionSendResponse` (`0x29dbe4`) commits headers and establishes send state; commit errors propagate through `_connectionHandleMessage` to the state machine and its stop/close callback (43H). The close/finalize path conditionally tears down the receiver session; `AirPlayReceiverSessionPlatformFinalize` provides the project lifecycle's planned full-session cleanup safety net (43J/43K). Static proof does not establish that a future project child will be bound to that callback in Honda.

## Mutation, rollback, and policy

Honda constructs a mutable response dictionary and mutable streams array. Type110 is appended in stock Setup; exact callback ownership is documented in [Type110 ledger](honda-type110-ownership-ledger.md). `_AddResponseStream` appends in construction order. Current Setup produces screen Type110 through the type-110 branch; do not assume fixed index in future mixed responses: locate by type. Request inspection can be read-only: scan `request.streams[*].type == 111`, preserving order, unknown fields, and all stock descriptors. This is a generic project rule, not Honda Type111 semantics.

ELF symbols show `CFArrayGetCount`, `CFArrayGetValueAtIndex`, `CFArrayCreateCopy`, `CFArrayCreateMutable`, `CFArrayAppendValue`; no public `CFArrayRemoveValueAtIndex` or `CFArraySetValueAtIndex` wrapper is present. `CFDictionaryGetValue`, SetValue, RemoveValue exist. Array remove-all exists internally but cannot selectively roll back. Cloning a stream array and swapping it through dictionary SetValue is mechanically plausible but would require preserving mutable semantics and exact callback/ownership behavior; a whole-response clone is not established. Preferred model is **LAST_MUTATION**: prepare all resources and fully construct the project entry first; append it as the final local response mutation immediately before the serializer call. Do not depend on append-then-remove rollback. Append API has no status result at its public wrapper. If construction/append behavior cannot be trusted, abort project augmentation before touching Honda's graph.

Project preparation can occur after stock Setup success and before response mutation, and listener bind/listen → actual local port → `dataPort` is the only safe ordering (`OFFLINE_PROJECT_IMPLEMENTATION` design; listener is not Honda). Exact helper call safety, arbitrary observer/race absence, and listener-failure behavior in Honda remain unproven. Thus response mutation is structurally supported, while integration callout safety is only a candidate.

Pre-serialization project failures can fail open by discarding project-only state and invoking the unmodified stock serializer. If the serializer itself fails after append, stock Type110 remains present in the CF graph, but there is no proof the same request can be retried using the original graph; helper returns an HTTP error. Roll back project resources and let Honda's ordinary error/session path proceed. The preferred policy is conditional fail-open before serialization, not a guarantee that every serializer failure sends Type110.

`RESPONSE_READY` is best mapped to `_requestSendPlistResponse` returning `0xc8` with statusOut zero at `0x28afbe`: data exists and body installation succeeded, so local graph rollback is no longer needed. This is not delivery. It is the earliest candidate for PREPARED→ACTIVE, but project child cleanup linkage on every later Honda failure is not proven from this static audit; mark commit point CANDIDATE, not PROVEN. Do not activate on append or before serializer success. HTTPConnectionSendResponse acceptance is later and its error path closes/finalizes; first socket write is later still.

## Honda evidence boundaries / decision

| Topic | Result |
|---|---|
| Post-Setup structural mutation window | PROVEN: `0x28af7e–0x28afba`; usable direct callout safety PARTIAL |
| Prepare point | CANDIDATE: after status check (`0x28af7e`) and before serializer (`0x28afba`); honor Honda metadata update before acting |
| Type111 detection | READY as generic read-only scan; Honda Type111 meaning UNKNOWN |
| Response identity | Preserve same response dictionary; replacement is not proven preferable/safe |
| Type110 index | SEARCH_BY_TYPE |
| Rollback strategy | LAST_MUTATION |
| Serialization barrier | PROVEN for synchronous plist→CFData→HTTP body path; return status handling proven |
| Response-ready | `r0==0xc8 && statusOut==0` at `0x28afbe`, candidate event |
| Child commit | CANDIDATE after successful helper return; Honda cleanup subscription remains unproven |
| Project failures | CONDITIONAL fail-open before serialization; serializer failure follows Honda error path |
| Transaction model | PARTIAL; no runtime integration mechanism decision in this step |

The six-function neutral inventory, including VA/mode/symbol/callers/prologue fingerprints, is recorded in the [43L report](../../step-reports/43l-post-setup-transaction-seam.md). No deployment mechanism has been selected. `jmcs` implementation and live validation remain NOT READY.
