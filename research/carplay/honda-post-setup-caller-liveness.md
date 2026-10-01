# Honda post-Setup caller liveness and CF cleanup — Step 43F

**Evidence binary:** `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. Static ARM/Thumb disassembly via LLVM objdump. No vehicle, ADB, runtime, patch, Type111 implementation, or live render test.

## Caller instruction trace

`_connectionHandleMessage` begins at `0x28a30c`; its prologue saves `r4-r11,lr` and reserves `0x2b4` stack bytes (`0x28a310–0x28a31a`). The incoming HTTP connection pointer is copied to `r4` at `0x28a314`; incoming request/message pointer is copied to `r6` at `0x28a326`. The parsed SETUP dictionary is stored in caller local `[sp+0x1c]` before the Setup call. The session pointer is loaded from `[r10+0xf4]`; `r10` is a saved/callee-preserved caller register.

At `0x28af6a–0x28af72`, caller reloads request into `r1`, session into `r0`, and constructs responseOut `r2 = sp+0x54`, then BLs to `AirPlayReceiverSessionSetup`. Return instructions:

```text
0x28af72  bl   AirPlayReceiverSessionSetup
0x28af76  mov  r1, r0              ; preserve returned OSStatus briefly
0x28af78  str  r0, [sp+0x50]       ; status/result slot
0x28af7a  cmp  r0, #0
0x28af7c  bne  0x28b040             ; stock error response branch
```

The success path does stock response-context work, including a call to `CFObjectSetProperty` at `0x28afae`; responseOut is not passed to that helper. Immediately before serialization:

```text
0x28afb2  mov  r1, r6              ; original HTTP request/message
0x28afb4  mov  r0, r4              ; HTTP connection
0x28afb6  ldr  r2, [sp+0x54]       ; exact Setup response object
0x28afb8  add  r3, sp, #0x50       ; serializer status output
0x28afba  bl   _requestSendPlistResponse
0x28afbe  mov  r6, r0              ; serializer return status
```

After the serializer returns, the handler reaches common cleanup. It releases the parsed request at `0x28b048–0x28b04a` and releases the responseOut value at `0x28b04e–0x28b052` if non-null. Stack locals and saved registers remain valid until handler epilogue. No release of the session pointer or response occurs between successful Setup return and serializer entry in this window.

### Liveness table

| Value | Location after Setup return | Location before serializer | Live? | Clobber risk | Confidence |
|---|---|---|---|---|---|
| Setup request dictionary | `[sp+0x1c]`; loaded into `r1` at `0x28af6a` | Stack slot remains within live handler frame; not a serializer argument | Yes, pointer remains available for an inserted helper to reload | Caller-saved `r1` is immediately overwritten with status at `0x28af76`; do not rely on it | `HONDA_CONFIRMED` dataflow |
| Receiver/session | `[r10+0xf4]` loaded into `r0` at `0x28af6c` | Re-loadable from `[r10+0xf4]`; `r10` preserved across Setup and other calls by ARM callee-save convention | Yes, pointer location remains available | `r0-r3`, `r12`, flags are call-clobbered; helper must not assume prior `r0` survives | `HONDA_CONFIRMED` for dataflow; underlying lifetime beyond caller scope is not generalized |
| ResponseOut slot | Address `sp+0x54` passed in `r2` | Response value read from `[sp+0x54]` into `r2` at `0x28afb6` | Yes on Setup success; null checked/released on common cleanup | `r2` is call-clobbered; reload slot after any helper | `HONDA_CONFIRMED` |
| Response dictionary object | Setup writes `*responseOut` at `0x286260` | Same pointer is serializer `r2` at `0x28afb6` | Yes through synchronous serializer call | Must preserve exact object identity/value; no stock copy before serializer | `HONDA_CONFIRMED` |
| HTTP request/message | Incoming pointer in `r6` from `0x28a326` | Loaded into serializer `r1` at `0x28afb2` | Yes | Callee-saved `r6`; handler later reuses it, so any shim must preserve it | `HONDA_CONFIRMED` |
| HTTP connection | Incoming pointer in `r4` from `0x28a314` | Loaded into serializer `r0` at `0x28afb4` | Yes | Callee-saved `r4`; preserve according to ABI | `HONDA_CONFIRMED` |
| Setup OSStatus / response status slot | `r0` returned, stored `[sp+0x50]` at `0x28af78` | Address `[sp+0x50]` passed in `r3` at `0x28afb8` | Yes | `r0` is repurposed; helper return later overwrites `r6` | `HONDA_CONFIRMED` |
| Caller stack frame | Allocated in prologue through `0x28a31a` | Still active at `0x28afba`; response/request released before epilogue | Yes | Any callout must maintain 8-byte AAPCS stack alignment and restore `sp` | `HONDA_CONFIRMED` for frame; alignment assumes ABI-conforming entry |

**CALLER_LIVENESS: COMPLETE** for the ordinary successful Setup path's pointer locations and serializer arguments. This does not prove a safe injected hook or that the same lifetime applies to other callers/threads.

## Serializer input and behavior

| Serializer input | Source | Copy / retain / direct | Sync / async | Release site | Confidence |
|---|---|---|---|---|---|
| Property-list object (`r2`) | `[sp+0x54]`, the Setup responseOut value | Direct same object; no caller-side copy or retain before helper | Synchronous function call | Caller `CFRelease` at `0x28b052`, after helper returns | `HONDA_CONFIRMED` |
| `CFData` output | `CFPropertyListCreateData` call inside serializer at `0x289fb2`, format `0xc8` | New serialized data object | Synchronous creation and body installation | Serializer `CFRelease` at `0x289ff0` | `HONDA_CONFIRMED` |
| HTTP body | `CFDataGetBytePtr` / `CFDataGetLength` then `HTTPMessageSetBody` at `0x289fdc` | Serialized bytes passed to HTTP body setter; ownership/copy details inside setter are not required for response object liveness | Body construction is synchronous | HTTP message/connection lifecycle owns subsequent send state | `HONDA_CONFIRMED` for call/dataflow; byte-buffer ownership internals not fully audited |

Serializer uses `CFPropertyListCreateData` -> `CFBinaryPlistV0CreateData`; the visible path reads the input graph and creates separate output data. No mutation of the response dictionary is observed. The handler later calls `HTTPConnectionSendResponse` at `0x28b790`. That commits/queues HTTP response state; `_HTTPConnectionRunStateMachine` later calls `SocketWriteData` -> `writev`. Therefore serialization/body installation is synchronous, while network send completion is an asynchronous/later state-machine phase. No response object is passed to the later write path.

```text
SERIALIZER_INPUT: DIRECT_SAME_OBJECT
SERIALIZATION_SYNC: YES
```

## Honda CF construction and ownership evidence

Setup calls `CFDictionaryCreateMutable` at `0x28557e` and stores its returned pointer in local `[sp+0x28]`; on success that exact pointer is published through `*outResponse` at `0x286260`. This confirms the response's mutable construction path.

`_AddResponseStream` at `0x284db8` retrieves `streams` through `CFDictionaryGetTypedValue`. If absent, it invokes `CFArrayCreateMutable` at `0x284de2`, calls `CFArrayAppendValue` at `0x284dea`, stores that array on the response with `CFDictionarySetValue` at `0x284df8`, then releases its local array reference at `0x284dfe`. If present, it calls `CFArrayAppendValue` at `0x284e10`. In stock Setup, the stream array is built through that mutable path; the helper is evidence that append is part of Honda's own construction.

The public wrappers are Honda's CFL-backed CF-style layer: `CFDictionaryCreateMutable` (`0x28e4b0`) delegates to `CFLDictionaryCreate` (`0x28f26c`); `CFArrayCreateMutable` (`0x28e346`) delegates to `CFLArrayCreate` (`0x28ed28`); `CFArrayAppendValue` delegates to `CFLArrayAppendValue` (`0x28eeac` -> `CFLArrayInsertValueAtIndex`); `CFDictionarySetValue` delegates to `CFLDictionarySetValue` (`0x28f420`); `CFRetain`/`CFRelease` delegate to `CFLRetain`/`CFLRelease` (`0x28eb70`/`0x28ebcc`). The array insert and dictionary set paths invoke configured callbacks for inserted objects/keys/values, but this audit did not resolve every callback pointer passed at construction to its concrete retain/release function. Thus an exact retain-count ledger for new objects is not yet Honda-proven.

| Operation/object | Observed Honda behavior | Ownership conclusion |
|---|---|---|
| Response dictionary | `CFDictionaryCreateMutable` returns a local object; Setup publishes the pointer on success; caller releases response after serialization | Caller owns the published response reference in this call path. Do not release or replace that reference in a future helper. |
| `streams` array | `CFArrayCreateMutable`; array set on response; helper releases local array ref; later stock entries append to existing array | Response graph owns the attached array under the observed callback behavior. Exact callback table identity/retain accounting remains partial. |
| Stream entry dictionary | Type-110 response dictionary is created, populated, appended | Array insertion invokes configured callback; exact new-entry retain count should be verified from callback table before using as implementation contract. |
| Keys/values | `CFDictionarySetValue` invokes configured key/value callbacks; `CFArrayAppendValue` invokes configured array callback | Use paired local ownership and release only after successful container insertion is proven for the specific callback set. |
| Temporary `CFData` | Serializer creates a separate data object and releases it after `HTTPMessageSetBody` | Serializer-owned temporary; not the Setup response. |
| Project listener/fd | No project listener exists in Honda path | Project must close exactly once on every post-allocation failure; no Honda cleanup can discover it. |
| Project stream/security state | No project state exists in Honda path | Project must erase secrets, drop all references, clear session association, and avoid Honda teardown. Exact crypto state is not designed here. |

```text
RESPONSE_MUTABILITY: CONFIRMED_MUTABLE (stock object construction)
STREAMS_ARRAY_MUTABILITY: CONFIRMED_MUTABLE when present (stock create/append path)
SAFE_CALLER_CONTEXT_MUTATION: UNKNOWN (no concurrency/reentrancy/type validation proof)
```

These classifications confirm object mutability in the static stock path, not that arbitrary new mutation is safe from an interposed caller. A future design must revalidate runtime type, distinguish absent from malformed `streams`, and prove no concurrent observer. No serializer freeze/copy before its call was observed; that is a synchronous ordering fact, not a general thread-safety guarantee.

## Hypothetical ownership and rollback contract

This is a requirement statement, not an implementation. Exact CF callback behavior and all actual cleanup sites must be proven before prototype design.

| Object | Created by | Owner on success | Owner on failure | Release required? | Failure cleanup | Confidence |
|---|---|---|---|---|---|---|
| Original response +1 | Honda Setup | Caller continues to own it; serializer receives borrowed/direct pointer | Caller still owns stock response | Caller releases once at existing `0x28b052` | Never release in helper; no stock mutation before candidate is ready | `HONDA_CONFIRMED` ownership path |
| Existing streams array | Honda Setup/helper | Attached to response; caller may borrow only | Still attached to original response | Do not release a borrowed getter result unless API returns +1 (not established) | Preserve original response/array on failure | Ownership relationship `HONDA_INDIRECT_CANDIDATE` pending callback proof |
| New Type111 response dictionary | Hypothetical project creator | Candidate container owns retained entry after append; project drops its local +1 only if callback proof confirms retain | Project owns and releases local +1 | Yes | Release on pre-append failure; after append, discard candidate graph or remove candidate before fallback | `HYPOTHESIS` |
| New/replacement streams array | Hypothetical project creator or Honda array | Candidate response owns it after set/replace, if callback semantics verified | Project owns temporary candidate | Yes | Release local temporary; do not mutate original graph until commit/swap succeeds | `HYPOTHESIS` |
| Cloned peer request descriptor | Hypothetical project copy | Project owns until copied into response entry | Project owns | Yes | Release on every branch after response-entry construction or failure | `EXTERNAL_PRIOR_ART` shape only; ownership `HYPOTHESIS` |
| Port/number/string objects | Project CF-style constructors | Containing candidate dictionary retains via configured callbacks if verified | Project owns temporary | Yes | Release each local +1 after successful set; otherwise release immediately | `HYPOTHESIS` |
| Listener fd | Project listener allocator | Project stream state owns until teardown | Project owns until closed | Close required | Close once; set fd sentinel; no Honda teardown | Project contract `HYPOTHESIS` |
| Project stream state and security bytes | Project allocator/KDF | Project-only session state | Project until erased | Destroy/zeroize required | Zero secrets, clear request/response linkage, free state and listener | Project contract `HYPOTHESIS` |
| Serializer `CFData` | Honda serializer | HTTP message body/send state after setter; local temporary released | Serializer handles its normal error path | Serializer-owned temporary released at `0x289ff0` | Project cleanup on later serializer failure is not linked/proven | `HONDA_CONFIRMED` serializer dataflow; project interaction `HONDA_UNKNOWN` |

**CLEANUP_CONTRACT: PARTIAL.** The rollback conditions for a project append are clearly stated, but Honda callback-based retain/release accounting, CF getter ownership, and the project cleanup edge after successful augmentation followed by serializer failure are unresolved.

## Insertion window and callout constraints

The stock post-Setup success branch runs at `0x28af7e` onward; stock request/session metadata updates occur through `CFObjectSetProperty` at `0x28afae`. The serializer arguments are staged at `0x28afb2–0x28afb8`, followed by its direct call at `0x28afba`. A hypothetical wrapper could only intervene after stock Setup success and before the serializer consumes `r2=[sp+0x54]`; the clean conceptual point is around the serializer call boundary, not inside stock Setup's Type-110 builder.

Values to preserve/reload: HTTP connection `r4`, HTTP request/message `r6`, session through `[r10+0xf4]`, parsed request dictionary `[sp+0x1c]`, responseOut `[sp+0x54]`, and serializer status slot `[sp+0x50]`. The stock response arguments `r0-r3` are loaded immediately before the call. A helper must preserve callee-saved `r4-r11`, restore `sp`, and maintain 8-byte AAPCS alignment; it must return the original serializer result in `r0` and not alter the status-out contract.

No safe unused inline code/data area or relocatable instruction window has been proven for inserting a call. Replacing the serializer call with a verified trampoline/shim is a theoretical route, but the existing code has not validated a shim, relocation, runtime branch range, thread rendezvous, or rollback. No live patching or hook design is approved.

```text
INSERTION_WINDOW: FOUND (structural caller interval, 0x28afae–0x28afba; helper must not disturb stock state)
CALLOUT_FEASIBILITY: NEEDS_TRAMPOLINE
```

## Failure path matrix

| Failure | Point in window | Cleanup | Return stock response? | Project state cleared? | Type110 impact | Confidence |
|---|---|---|---|---|---|---|
| No Type111 request | Before project allocation | Skip project path; serialize stock object directly | Yes, unchanged | No state allocated | None | `SYNTHETIC_TEST_VALUE` contract; original request available `HONDA_CONFIRMED` |
| Malformed Type111 request / missing or zero connection ID | Before listener/state allocation | Reject candidate; leave stock response untouched | Yes | Yes; ideally no allocation | None | Request validation rule is `HYPOTHESIS`; Honda Type111 fields unknown |
| Stock response object missing after status 0 | Before append | Treat as project/stock invariant failure; do not fabricate response; exact caller behavior must be recovered | Unknown | Yes | Unknown | `HONDA_UNKNOWN` impossible/invalid stock-state handling |
| `streams` missing | Before append | Build candidate array off to side only if response semantics permit; do not change original until commit | Yes on project failure | Yes | None | Honda helper can create array during construction; caller creation not validated |
| `streams` immutable/wrong type | Before append | Fail validation, preserve stock object | Yes | Yes | None | No caller type-validation path proven |
| Descriptor clone or dictionary creation failure | Before append | Release temporaries, close any listener, discard state/secrets | Yes | Yes | None | Contract `HYPOTHESIS`; allocation failure semantics need helper return audit |
| Listener allocation failure / no usable dataPort | Before append | Close partial fd if any, clear state/secrets | Yes | Yes | None | Project-only contract `HYPOTHESIS` |
| Crypto material unavailable | Before append | Erase partial key/IV bytes, close listener, free state | Yes | Yes | None | Project-only contract `HYPOTHESIS` |
| Array append or response set failure | During candidate construction | Discard candidate graph; if original was directly mutated, remove partial entry or cannot guarantee rollback | Yes only if original remained untouched | Yes | None if rollback succeeds | Model only `SYNTHETIC_TEST_VALUE`; Honda helper mutates in place and caller rollback unproven |
| Serializer fails after successful append | Inside `_requestSendPlistResponse` | Project resources need an independently owned failure cleanup edge; no proven call from serializer error to project state | Not proven | Not proven | Potentially none to Type110 response bytes, but project listener/state can leak | `HONDA_UNKNOWN` |
| Unexpected stock Setup failure | Setup call returns nonzero, branch to `0x28b040` | Follow Honda error branch; no project allocation before success | No successful response serialization | No project state should exist | Stock authored | `HONDA_CONFIRMED` |

## Readiness and remaining proof

- Exact caller register/stack liveness is complete for this direct call path.
- The serializer receives the same response pointer and serializes synchronously; later socket writing occurs through HTTP state machinery.
- Stock response and streams array are definitely created through mutable APIs; arbitrary caller mutation safety is still unknown.
- Callback tables for CF dictionary/array retain/release behavior and getter ownership need exact resolution.
- The external/project cleanup path after post-append serialization or HTTP send failure is not established.
- No checked caller type validation, concurrency exclusion, or safe injected callout/trampoline is proven.

Decision: `NEEDS_MORE_STATIC_PROOF`; implementation is not ready. The narrow next static question is: **Which exact callback functions are installed in the response dictionary/streams array, and what existing handler/session edge can clean project state if serialization or HTTP response queuing fails?**

Evidence tags: `HONDA_CONFIRMED` for the disassembled pointer/serializer/mutable-constructor dataflow; `HONDA_INDIRECT_CANDIDATE` for ownership not traced through callback tables; `HONDA_UNKNOWN` for caller-side mutation safety and project failure cleanup; `SYNTHETIC_TEST_VALUE` for offline rollback models; `EXTERNAL_PRIOR_ART` for MHI2 schema/approach; `HYPOTHESIS` for any future project ownership contract.

## Step 43G refinement — callbacks and later failures

See [Honda CF callback ownership — Step 43G](honda-cf-callback-ownership.md) for callback slots, stock ownership ledger, failure propagation, and rollback matrix. The ELF callback table symbols and CFL wrapper semantics are recorded, but the Setup dictionary constructor arguments at `0x28557e` are not yet mapped conclusively to the named tables; the Type110 entry constructor/release ledger is also incomplete. Therefore the stock ownership ledger and any project append ownership contract remain `PARTIAL`.

Serialization failure returns through the caller's common cleanup, which releases both parsed request and response. Property-list creation failure occurs before `HTTPMessageSetBody`; a body-setter failure can follow partial HTTP-message mutation. After serializer return, the CF response graph is released and independent HTTP message state is queued. A later queue/write failure cannot affect the response graph, but no connection-callback-to-session/project cleanup edge has been identified. The caller path shows no pre-serialization response escape, while threading/race freedom remains unproven.

```text
DICTIONARY CALLBACKS: PARTIAL
ARRAY CALLBACKS: PARTIAL
STOCK OWNERSHIP LEDGER: PARTIAL
PROJECT OWNERSHIP CONTRACT: PARTIAL
SERIALIZATION FAILURE CLEANUP: PARTIAL
HTTP QUEUE CLEANUP: PARTIAL
CALLER SIDE MUTATION RACE: NO_STATIC_EVIDENCE
```
