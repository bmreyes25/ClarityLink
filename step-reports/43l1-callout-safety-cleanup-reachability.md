# Step 43L.1 — callout safety and project-child cleanup reachability

**Base:** `04efee78e8e88d9fd1d3058389ad4488a0997076` (clean main). **Binary:** `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` (MATCH). Offline static audit only. No runtime, patch, Type111 implementation, deployment mechanism, vehicle, ADB, or live work.

## 1. Callout safety

Caller `_connectionHandleMessage` is Thumb. Prologue pushes 9 words (`r4-r11,lr`) then reserves `0x2b4`; total stack adjustment is 728 bytes, a multiple of 8. At all candidate boundaries SP remains 8-byte aligned. Setup returns at `0x28af76`; flags from `cmp` are consumed by `bne` at `0x28af7c`. On the success path, Honda writes session fields and calls `CFObjectSetProperty` at `0x28afae`. At `0x28afb2` the caller begins re-staging serializer args; no branch uses flags after the property call. Stack locals remain `[sp+0x1c]` request, `[sp+0x50]` status/body result, `[sp+0x54]` response. `r4` connection, `r6` request message, and `r10` session base are callee-saved/live. A helper must preserve all `r4-r11`, restore SP, return normally, and treat `r0-r3/r12/lr/flags` as volatile.

Thumb-2 BL displacement is PC-relative (`PC+4`), signed and halfword-aligned, within approximately ±16 MiB (`-2^24..2^24-2`). Candidate destination/address is not chosen, so actual reach is unknown. All candidate sites are occupied instructions; no spare call slot, patch procedure, or safe replacement span is claimed.

| SITE | ADDRESS RANGE | INSTRUCTION BYTES | LIVE INPUTS | LIVE OUTPUTS | MUST SURVIVE | FLAGS | STACK | SAFE CALLOUT? |
|---|---|---|---|---|---|---|---|---|
| after successful Setup branch | `0x28af7e` | `f8df e0b8` | session `[r10+f4]`, request `[sp+1c]`, status `[sp+50]`, response `[sp+54]` | none yet | AAPCS `r4-r11`; stock metadata still pending | none | 8 aligned | CANDIDATE_ONLY |
| after stock metadata, before serializer loads | `0x28afb2` | `4631` | session reload `[r10+f4]`, request `[sp+1c]`, response `[sp+54]`, status `[sp+50]`; `r4` conn, `r6` message | helper-owned project state only; serializer args are staged afterward | `r4-r11`; preserve Honda object ownership; original following loads must execute | none | 8 aligned | CANDIDATE_ONLY; BEST STRUCTURAL CANDIDATE |
| serializer BL | `0x28afba` | `f7fe ffd1` | args already staged in `r0-r3` | response/body status on return | `r4-r11`; helper must restage `r0-r3` exactly | none | 8 aligned | CANDIDATE_ONLY; more fragile |
| after serializer | `0x28afbe–0x28afc0` | `4606; e040` | `r0` HTTP status; `[sp+50]` setter result; response still live | commit/rollback decision | `r6`, `r4-r11` | none | 8 aligned | CANDIDATE_ONLY; cannot mutate response |
| common cleanup entry | `0x28b044` | `9d07` | request/response/status still live before releases; serializer result `r6` | cleanup only | status and `r4-r11` | later local tests set own flags | 8 aligned | UNKNOWN; shared paths and too late to mutate |

At the best structural point, a void helper could safely have its return ignored only if every failure self-rolls back project resources and leaves Honda request/response untouched. It must not throw/unwind, take ownership of the stock response, replace the response object, edit request fields, touch stock Type110/audio entries, or mutate after serializer entry. This exact ABI discipline is statically specifiable; absence of a Honda callout/thread/reentrancy contract prevents `PROVEN_SAFE`.

**CALLOUT SAFETY: CANDIDATE_ONLY.** **HELPER ABI CONTRACT: PARTIAL.** **BEST STATIC CALLOUT CANDIDATE: `0x28afb2` (structural only).** Detailed tables: [callout safety](../research/carplay/honda-post-setup-callout-safety.md), [helper ABI](../research/carplay/honda-post-setup-helper-abi-contract.md).

## 2. Serializer success predicate correction

At `0x289fe6`, `_requestSendPlistResponse` returns `0xc8` (HTTP 200) when `HTTPMessageSetBody` returned zero; it returns `0x1f4` (HTTP 500) when body setting failed. It writes the body-set result through caller's statusOut at `0x289ff6`. Header initialization/plist creation failure also routes to 500 with a nonzero error result in that output. Therefore a local success observer must require **`r0 == 0xc8 && [sp+0x50] == 0`**. The earlier description “successful helper return” is refined to this exact predicate; it is not `OSStatus == 0` and not phone receipt. The response graph is released at `0x28b052` before HTTP send at `0x28b790`.

Candidate after return is `0x28afbe` (before `mov r6,r0`) or after that instruction and before the branch at `0x28afc0`; it can observe success/failure but cannot mutate the already serialized graph. This still requires an integration callout and does not itself establish cleanup reachability.

## 3. Cleanup reachability

HTTP send flow is `HTTPConnectionSendResponse` (`0x29dbe4`) → connection write state → `_HTTPConnectionRunStateMachine` (`0x29d698`) → `SocketWriteData` (`0x2a01c0`) → `writev`. Terminal HTTP handler/commit/write failures close the connection. `_connectionFinalize` (`0x289d90`) invokes `AirPlayReceiverSessionTearDown` (`0x2852ec`) only if private context `[+0xf4]` contains a non-null session. The relation is conditional; it does not prove every request failure causes teardown, nor that every connection has a unique session.

Normal `tearDownStreams` reaches PlatformControl, which handles stock 100/101/110 and skips unknown 111. It does not dispatch that stream branch to the Honda delegate. Full CF session finalization runs Honda `_AirPlayHandleSessionFinalized`, then PlatformFinalize. The callback table is existing Honda-owned state; SetDelegate copies the whole table and replacing it would erase callbacks. No project child subscription/chaining API was found. PlatformFinalize is an internal finalizer sink, but project child state is not reachable from it without another integration seam. No stable Honda session-generation field was found; only an opaque pointer is available in observed caller/finalizer paths.

| FAILURE / FINALIZATION EVENT | HONDA FUNCTION | SESSION POINTER? | CHILD REACHABLE? | ATTACH WITHOUT NEW HOOK? | CONFIDENCE |
|---|---|---|---|---|---|
| Setup failure | `_connectionHandleMessage` / Setup | yes in handler frame | no project child should yet exist | n/a | HONDA_CONFIRMED stock path |
| Plist/body failure | serializer + handler cleanup | caller still has session; response soon released | no through response graph | no known callback | HONDA_CONFIRMED lifetime; project edge HONDA_UNKNOWN |
| HTTP commit failure | send → state machine close | conditional connection context session | no child lookup | no | HONDA_CONFIRMED conditional edge |
| terminal socket failure | `SocketWriteData` → close → `_connectionFinalize` | conditional `+0xf4` | no child lookup | no | HONDA_CONFIRMED conditional edge |
| normal `tearDownStreams` | `AirPlayReceiverSessionTearDown` → PlatformControl | session argument | Type111 skipped; delegate not notified on this branch | no | HONDA_CONFIRMED |
| object finalization | `_Finalize` → app callback/PlatformFinalize | session argument | Honda context only | no supported project chaining | Honda finalizer HONDA_CONFIRMED; project link NOT_PROVEN |
| pointer reuse/generation | across session lifetimes | raw pointer could be reused | only project generation distinguishes it | synthetic registry only | HONDA_UNKNOWN / SYNTHETIC_TEST_VALUE |

**HONDA CLEANUP REACHABILITY: PARTIAL. PROJECT CHILD CLEANUP VIA HONDA: NOT_PROVEN.** Full discussion: [cleanup reachability](../research/carplay/honda-project-child-cleanup-reachability.md).

## 4. Project-owned generation guard

Required if any child is prepared. Use `(opaque session pointer, monotonic project generation)` and validate the generation on every cleanup/commit; stale cleanup may touch only its generation. Listener and child state belong to the project transaction/registry. A preparation lease expires and rolls back if successful serializer predicate is not observed. Only `0xc8` plus zero body-set result crosses local response-ready; it does not imply network delivery. Duplicate Setup for an already prepared/active generation fails open unless a replacement protocol is explicitly modeled. Mutation failure cleans the project child and preserves stock response if graph was not changed; uncertain partial append is not treated as removable. Serialization failure rolls back project resources. HTTP delivery failure and normal Honda teardown need a proven notification or watchdog cleanup; Honda alone is insufficient.

Because no Honda child callback exists, a project activity/inactivity watchdog would be needed after activation. Timeout duration and renewal signals are unknown; a guessed timeout could kill a valid quiet session. The existing 43K registry provides generation safety, idempotence, and finalization adapter semantics synthetically, but has no proven Honda timer/event integration. **GENERATION GUARD REQUIRED: YES. GENERATION GUARD MODEL: PARTIAL.**

## 5. Readiness and verification

Callout safety is candidate-only and Honda child cleanup linkage is not proven; therefore **JMCS INTEGRATION DESIGN: NEEDS_MORE_STATIC_PROOF**. `JMCS IMPLEMENTATION`, live test, Type111 live, and ExternalDisplay live render remain NOT READY; LD_PRELOAD stays PARKED. No live gate advances.

The existing synthetic tests cover transaction ready/rollback, duplicate cleanup, stale generations, pointer reuse, finalization races, Type110/audio preservation, request immutability, and listener/serializer failure twins. No model changes were needed in 43L.1.

**NEXT STATIC QUESTION:** Is there a Honda-supported way to extend or chain `_AirPlayHandleSessionFinalized` so a project-owned `(session,generation)` child is reachable without replacing the Honda delegate table?
