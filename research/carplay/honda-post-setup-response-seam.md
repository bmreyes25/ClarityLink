**Step 43H update:** HTTP header commit failure is no longer an unknown effect: its nonzero status propagates through the request handler and state machine, which closes the HTTP connection; connection finalization reaches receiver-session teardown conditionally when the private session pointer exists. A supported child subscription across all parent teardown sources is still unproven, so seam readiness remains `NEEDS_MORE_STATIC_PROOF`. See [Step 43H](../../step-reports/43h-http-commit-and-session-cleanup.md).

**Step 43G correction:** Exact callback tables and stock Type110 nested ownership are now proven from the hash-matched ELF. This upgrades container lifetime confidence, but does not establish safe arbitrary caller-side mutation, race freedom, queue-failure cleanup, or a project-owned lifecycle callback. The post-serialization response graph is already released before network failures. The post-Setup seam remains `NEEDS_MORE_STATIC_PROOF`. See [Step 43G](../../step-reports/43g-setup-cf-ownership-and-network-cleanup.md).

# Honda post-Setup / pre-serialization response seam — Step 43E

**Step 43H update:** Setup response and `streams` constructor callback arguments remain unresolved, so container retention and safe project ownership cannot be promoted. Successful serialization ends the CF response graph's required lifetime; post-serialization queue/write failures are a separate project lifecycle concern. See [Step 43H](../../step-reports/43h-cf-callback-fingerprint.md).

**Step 43F refinement:** Instruction-level disassembly now confirms caller locations and direct serializer input. The response and streams array are classified `CONFIRMED_MUTABLE` as constructed by stock Honda; this does not prove arbitrary caller-side mutation safety. CF callback ownership and project cleanup after serializer/HTTP failure remain incomplete. See [Step 43F caller liveness and cleanup](honda-post-setup-caller-liveness.md).

**Step 43G refinement:** CFL callback table symbols and wrapper semantics are identified, but Setup's dictionary constructor arguments and the Type110 entry's callback/release ledger remain unresolved. Serializer creation failure reaches caller cleanup; body-setter failure may leave HTTP message state partially changed. HTTP queue/write failures occur after the response graph is released, and the connection failure callback's session/project cleanup relationship is unknown. See [Step 43G callback and cleanup audit](honda-cf-callback-ownership.md).

**Scope:** offline static audit of the identity-verified Honda `jmcs` ELF and synthetic response-preservation model. No vehicle, ADB, Honda runtime, binary modification, hook, Type111 implementation, or live render test was used.

## Finding

`_connectionHandleMessage` calls `AirPlayReceiverSessionSetup(session, request, &response)` at `0x28af72`. On `OSStatus == 0`, it passes that exact response value at caller stack `sp+0x54` to `_requestSendPlistResponse` at `0x28afba`; the caller later releases it at `0x28b052`. The serializer synchronously creates binary-plist `CFData`, installs its bytes in the HTTP message, releases the temporary data, and returns before the response is released. This proves a synchronous post-Setup/pre-serialization interval in this caller.

The response is created as a mutable CF-style dictionary in Setup (`0x28557e`); `_AddResponseStream` (`0x284db8`) creates a mutable array when needed and appends entries. The Type-110 response entry is added before Setup publishes the response at `0x286260`. This is strong static evidence of mutability during stock construction and a structural append candidate at the caller. It does **not** directly prove that a third-party mutation at the caller is safe under Honda's runtime, exact toll-free/CF implementation semantics, or concurrency/reentrancy conditions. The serializer does not appear to freeze or reuse the CF response: serialization produces a separate byte object, and the caller releases the original after return.

On Setup failure, its local response is released and the caller takes the nonzero-status path without serialization. On project-only append failure after successful stock Setup, Honda has no project resource knowledge; the project must discard its own temporary state and hand the original stock response to the existing serializer. Do not invoke Honda teardown or rewrite the stock response. A failure in serialization itself is outside the append seam and project cleanup linkage is not proven.

## Lifetime and access table

| Object | Owner before Setup | Owner after Setup | Mutable before serialize? | Release site | Failure path | Confidence |
|---|---|---|---|---|---|---|
| Setup response dictionary | Setup creates/owns local +1 | Caller receives the published +1 on success | `INDIRECT_CANDIDATE`: mutable CF dictionary construction confirmed; direct post-return mutability not dynamically validated | Caller `CFRelease` at `0x28b052`, after serializer returns | Setup releases local response and returns error; caller skips serializer | `HONDA_CONFIRMED` for dataflow/ownership in this call path; post-return mutation safety remains candidate |
| `streams` array | Setup response owns it after `CFDictionarySetValue`; helper may hold temporary +1 | Nested response value; caller can reach through response | `INDIRECT_CANDIDATE`: mutable CFArray and append helper confirmed during Setup; direct caller-side mutation not dynamically validated | Helper releases local array reference after setting; response retains it; response releases after serialization | Setup's own error cleanup releases response graph | `HONDA_CONFIRMED` for construction and append behavior |
| Parsed request dictionary | `_connectionHandleMessage` local owns parsed request | Remains in caller scope after Setup returns | Not mutated in inspected post-Setup path; available as input | Caller cleanup follows handler lifetime; exact release instruction not needed for seam conclusion | Setup failure branches away; success path continues | `HONDA_CONFIRMED` for availability at call boundary; retain semantics beyond caller scope not generalized |
| Receiver/session pointer | Caller-held receiver/session object passed in `r0` | Caller retains pointer across call and subsequent send path | Not claimed mutable by the proposed append | Owned/managed by surrounding handler/session lifecycle; exact release not inferred here | Setup's stock failure cleanup remains Honda-authored | `HONDA_CONFIRMED` for pointer availability in caller path; project state binding is not permitted by this audit |
| Serialized body `CFData` | Created inside serializer | HTTP message owns/copies body bytes after `HTTPMessageSetBody` | No longer the response object | Serializer releases temporary data before return | Serializer/body construction error behavior is separate and incompletely connected to project cleanup | `HONDA_CONFIRMED` for synchronous conversion/dataflow |

## Mutability assessment

```text
RESPONSE_MUTABILITY: INDIRECT_CANDIDATE
STREAMS_ARRAY_MUTABILITY: INDIRECT_CANDIDATE
APPEND_HELPERS: _AddResponseStream (0x284db8), Honda-owned construction helper; no approved external append helper identified
SERIALIZER_COPY/FREEZE: separate binary-plist CFData is produced synchronously; no response-object reuse/freeze observed
CF RETAIN REQUIREMENT: an inserted entry is retained by CFArrayAppendValue; a replaced/set array is retained by CFDictionarySetValue; caller's response +1 must remain owned by caller
```

## Caller context and Type111 boundary

The same caller still has its parsed request and receiver/session argument after Setup returns. Request `streams[]` is independently inspectable, and Honda's Setup default branch logs/skips unsupported stream type 111 without setting failure status or removing already accumulated supported entries. Thus the static detection model is `ORIGINAL_REQUEST_AFTER_STOCK`; splitting/filtering the request is not indicated by Honda's observed control flow and would introduce unnecessary semantic changes.

This is a static caller-liveness result, not approval to mutate from an injected hook. Exact stack/local liveness at every candidate instruction, hook ABI/relocation, thread/reentrancy behavior, and lifetime under unusual serializer failure remain implementation prerequisites. Honda evidence shows mixed Type110/Type111 can still succeed if recognized setup and final PlatformControl succeed; Type111 itself adds no stock response entry. Honda's UUID-to-stream identity and any Type111 response schema remain unknown.

## Rollback contract and failure matrix

Contract for a future optional append experiment: only proceed after stock Setup returns success. Preserve a deep/value-exact snapshot of the stock response for the model; in a real implementation, keep the original object untouched until a complete candidate response is ready. On any project failure, close the project listener, erase/discard project crypto and stream state, clear any project session association, expose no partial candidate entry, and return the original stock response to the ordinary serializer. Do not invoke stock teardown, alter stock session ownership, or change stock error behavior. This contract is a design requirement, not Honda-confirmed implementation behavior.

| Failure point | Expected rollback | Stock response preserved? | Project state cleared? | Type110 impact | Confidence |
|---|---|---|---|---|---|
| Stock Setup returns error | Follow stock path; do not allocate project resources | No successful response is serialized; stock error behavior stays intact | No project state should exist | None from project path | `HONDA_CONFIRMED` stock branch; project constraint is `HYPOTHESIS` |
| Type111 request invalid/ambiguous | Return exact stock response; allocate nothing or clear prior temporary state | Yes | Yes | None | `SYNTHETIC_TEST_VALUE`; Honda Type111 validation unknown |
| Project listener allocation fails | Close any partially allocated listener; discard state/security material; return exact stock response | Yes | Yes | None | `SYNTHETIC_TEST_VALUE` |
| Project state/security preparation fails | Zero temporary security material; close listener; discard state; return exact stock response | Yes | Yes | None | `SYNTHETIC_TEST_VALUE` |
| Dictionary/array clone or append fails | Discard candidate containers/entry; return original response, with no partial entry visible | Yes | Yes | None | `SYNTHETIC_TEST_VALUE` |
| Serialization fails after augmentation was selected | Project cleanup association and response fallback are not proven; do not claim stock fallback here | Unknown | Unknown without additional integration | Unknown | `HONDA_UNKNOWN` |
| Stock Type110 setup fails | Preserve stock-authored failure and its cleanup; no project response | No success response | No project state should exist | Stock behavior unchanged | `HONDA_CONFIRMED` for stock path |

## Stock invariants

1. On no Type111 request, return the exact stock response without project writes.
2. On project failure, serialize the exact stock response object/value, with the original stock stream order and fields.
3. Never rebuild or normalize Type110. Its `{type: 110, dataPort: assigned_port}` entry and all opaque stock fields remain value-for-value unchanged.
4. Append at most one independently owned optional entry only after complete candidate construction; no partial candidate is visible.
5. Project listener, key/IV material, parser state, and session association have project-only ownership and deterministic rollback.
6. Never trigger stock teardown to clean project-only resources.

## Synthetic model status

Existing `src/claritylink-negotiation/setup_transaction.py` and `setup_augmentor.py` model a successful stock call followed by optional clone/append; `tests/negotiation/test_setup_contract.py` exercises preserved stock values/order/opaque fields, no-request pass-through, stock-first ordering, prepare failure, malformed response container, and rollback. These results are `SYNTHETIC_TEST_VALUE`. They do not prove Honda dictionaries can be safely changed from a hook, Honda Type111 schema acceptance, or binary/wire equivalence. The model's `streamID=111` and cloned descriptor shape are explicitly `EXTERNAL_PRIOR_ART` from MHI2, not Honda facts.

## External prior-art comparison

| MHI2 source-pinned behavior | Honda static finding | Boundary |
|---|---|---|
| Call stock Setup first with original request | Honda caller naturally invokes stock Setup before the candidate window | Similar shape only; no Honda hook is designed or approved |
| Preserve stock response and clone unknown descriptor fields | Honda response and stream array are built mutably; same response reaches serializer | Honda response contents are known only for stock fields; clone policy is a model choice |
| Append project-owned Type111 `dataPort` response | Honda exposes a structural post-Setup/pre-serialize window | MHI2 schema/field names are not Honda-confirmed |
| Fail closed when hook/lifecycle prerequisites are unproven | Honda runtime hook ABI, concurrency, and project cleanup through serializer failure remain unproven | Keep implementation and live gates closed |

Classification: `EXTERNAL_PRIOR_ART` for MHI2, `HONDA_CONFIRMED` for Honda static control/ownership dataflow, `HONDA_INDIRECT_CANDIDATE` for caller-side mutability, `SYNTHETIC_TEST_VALUE` for the offline model, and `HYPOTHESIS` for any later optional append design.

## Remaining static proof before implementation design

- Obtain exact machine-level caller disassembly/register and stack-liveness evidence for the response, request, and session from Setup return through serializer call, with instructions and ELF identity attached to the report.
- Confirm all response/helper error branches, whether any serializer error can occur after project resource creation, and the ordinary session teardown edge available to a future project-owned listener.
- Determine whether CF mutability APIs and their ABI are available/compatible in the exact Honda process/runtime and whether any caller-side mutation can race with another reader. Current evidence establishes only stock construction-time mutability.
- Establish a project-only cleanup owner and prove candidate-container rollback preserves the original response object on allocation failure; the Python model cannot prove CF retain/release behavior.
- Keep schema, capability-token, UUID/stream correlation, crypto, and renderer requirements as separate unresolved layers.

**Step 43E decision:** `SAFE_STATIC_CANDIDATE` for studying the seam and running an offline model; `IMPLEMENTATION_DESIGN_READY: NO`. Step 43F refines caller liveness and mutability, but implementation design remains `NEEDS_MORE_STATIC_PROOF` pending callback ownership and cleanup-edge evidence. Live, jmcs, ExternalDisplay, and LD_PRELOAD gates remain closed/parked.
